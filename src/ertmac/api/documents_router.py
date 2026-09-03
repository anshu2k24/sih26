"""
PS26121 eRTMAC-NWIS — Document Ingestion & Verification Router
Provides endpoints for report upload, text extraction, event parsing, and engineer verification.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    UserSession,
    Permission,
)
from ertmac.documents.uploader import (
    upload_document,
    get_documents,
    get_document_by_id,
)
from ertmac.documents.extractor import extract_text_from_file
from ertmac.documents.parser import parse_extracted_events
from ertmac.documents.verifier import DocumentVerificationEngine
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.api.documents")

router = APIRouter(prefix="/api/documents", tags=["Document Ingestion & Knowledge"])


@router.post("/upload")
async def upload_and_process_document(
    file: UploadFile = File(...),
    well_id: str = Query("15/9-F-14", description="Associated wellbore ID"),
    user: UserSession = Depends(require_permission(Permission.UPLOAD_DOCUMENTS)),
):
    """
    Uploads a drilling report / log file (PDF, TXT, CSV, DOCX),
    calculates SHA-256 checksum for deduplication, extracts text (with OCR fallback),
    parses event episodes with confidence scores, and stores records for review.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = file.filename or "uploaded_report.pdf"

    # 1. Upload & Deduplicate Check
    doc_record, is_duplicate = upload_document(
        filename=filename,
        file_bytes=contents,
        user_id=user.user_id,
        organization_id=user.organization_id,
    )

    doc_id = str(doc_record["id"])

    if is_duplicate:
        global_audit_service.log_event(
            actor_id=user.user_id,
            actor_role=user.role.value,
            action="DOCUMENT_UPLOAD_DUPLICATE",
            resource_type="DOCUMENT",
            resource_id=doc_id,
            organization_id=user.organization_id,
            payload={"filename": filename, "checksum": doc_record.get("checksum")},
        )
        events = DocumentVerificationEngine.get_events_for_document(doc_id, organization_id=user.organization_id)
        return {
            "status": "DUPLICATE",
            "message": "Document with identical SHA-256 checksum has already been uploaded.",
            "document": doc_record,
            "extracted_events": events,
        }

    # 2. Extract Text
    file_path = doc_record["storage_path"]
    doc_type = doc_record["document_type"]

    text_content, extraction_status, error_msg = extract_text_from_file(file_path, doc_type)

    doc_record["extraction_status"] = extraction_status
    if error_msg:
        doc_record["source_metadata"]["error_message"] = error_msg

    # 2.5 Extract important metadata details
    if text_content:
        meta = doc_record["source_metadata"]
        
        # 1. Deterministic baseline extraction (fast & guaranteed)
        deterministic_meta = extract_document_metadata(text_content, default_well_id=well_id)
        for k, v in deterministic_meta.items():
            if v and str(v).strip().lower() not in ("none", "n/a", "null", ""):
                meta[k] = str(v).strip()

        # 2. Semantic enhancement via LLM
        try:
            from ertmac.rag.llm.gemini_llm import GeminiLLMProvider
            import json
            
            llm = GeminiLLMProvider()
            sys_prompt = (
                "You are an expert data extractor for drilling reports. "
                "Extract the following fields from the given text: "
                "well_id, depth, water_depth, current_operation, report_period, abnormal_remarks. "
                "Even if the details are in different wording or embedded in paragraphs, analyze the text and find them. "
                "Return ONLY a valid JSON dictionary with these exact keys. Use null if a field is completely missing."
            )
            
            # Use only the first portion of text to avoid token limits for metadata extraction
            context_text = text_content[:12000]
            
            res_text = llm.generate_answer(
                question="Extract the requested fields as JSON.",
                context=context_text,
                system_prompt=sys_prompt,
                temperature=0.1
            )
            
            # Clean and parse JSON response
            cleaned_json = res_text.strip()
            if cleaned_json.startswith("```json"):
                cleaned_json = cleaned_json.split("```json")[1]
            if cleaned_json.endswith("```"):
                cleaned_json = cleaned_json.rsplit("```", 1)[0]
                
            extracted_meta = json.loads(cleaned_json.strip())
            
            # Update meta with extracted values
            for k, v in extracted_meta.items():
                if v is not None and str(v).strip().lower() not in ("none", "n/a", "null", ""):
                    meta[k] = str(v).strip()
                    
        except Exception as e:
            logger.debug(f"LLM metadata extraction skipped / fallback used: {e}")

        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if db:
                db.table("documents").update({
                    "extraction_status": extraction_status,
                    "source_metadata": doc_record["source_metadata"]
                }).eq("id", doc_id).execute()
        except Exception as e:
            logger.error(f"Failed to update document metadata in DB: {e}")

    # 3. Parse Event Episodes if text extracted
    extracted_events: List[Dict[str, Any]] = []
    if extraction_status == "EXTRACTED" and text_content:
        extracted_events = parse_extracted_events(
            document_id=doc_id,
            text=text_content,
            default_well_id=well_id,
            organization_id=user.organization_id,
        )
        DocumentVerificationEngine.save_extracted_events(doc_id, extracted_events)

        # 4. Auto-index digital document text into RAG Vector Store
        try:
            from ertmac.rag.services.ingestion_service import global_ingestion_service
            global_ingestion_service.index_note(doc_id, user_id=user.user_id, force_reindex=True)
        except Exception as e:
            logger.info(f"RAG indexing notice for document {doc_id}: {e}")

    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="DOCUMENT_UPLOADED",
        resource_type="DOCUMENT",
        resource_id=doc_id,
        organization_id=user.organization_id,
        payload={
            "filename": filename,
            "extraction_status": extraction_status,
            "events_count": len(extracted_events),
        },
    )

    return {
        "status": "SUCCESS",
        "document": doc_record,
        "extraction_status": extraction_status,
        "error_message": error_msg,
        "extracted_events_count": len(extracted_events),
        "extracted_events": extracted_events,
    }


@router.get("")
def list_uploaded_documents(
    limit: int = Query(50, ge=1, le=200),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Lists all uploaded documents."""
    docs = get_documents(organization_id=user.organization_id, limit=limit)
    return {"count": len(docs), "documents": docs}


@router.get("/{doc_id}")
def get_document_details(
    doc_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Returns details for a single uploaded document."""
    doc = get_document_by_id(doc_id, organization_id=user.organization_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    events = DocumentVerificationEngine.get_events_for_document(doc_id, organization_id=user.organization_id)
    return {"document": doc, "extracted_events": events}


@router.get("/{doc_id}/extracted-events")
def get_document_extracted_events(
    doc_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Returns extracted events for a specific document."""
    events = DocumentVerificationEngine.get_events_for_document(doc_id, organization_id=user.organization_id)
    return {"document_id": doc_id, "count": len(events), "events": events}


@router.post("/{doc_id}/events/{event_id}/verify")
def verify_extracted_event_endpoint(
    doc_id: str,
    event_id: str,
    user: UserSession = Depends(require_permission(Permission.VERIFY_KNOWLEDGE)),
):
    """
    Verifies an extracted event episode, marking it VERIFIED and promoting it to
    verified historical DDR knowledge database. Requires VERIFY_KNOWLEDGE permission.
    """
    evt = DocumentVerificationEngine.verify_event(
        event_id=event_id,
        verifier_user_id=user.user_id,
        verifier_role=user.role.value,
        organization_id=user.organization_id,
    )
    if not evt:
        raise HTTPException(status_code=404, detail="Extracted event not found.")
    return {"status": "VERIFIED", "event": evt}


@router.post("/{doc_id}/events/{event_id}/reject")
def reject_extracted_event_endpoint(
    doc_id: str,
    event_id: str,
    user: UserSession = Depends(require_permission(Permission.VERIFY_KNOWLEDGE)),
):
    """Rejects an extracted event episode."""
    evt = DocumentVerificationEngine.reject_event(
        event_id=event_id,
        verifier_user_id=user.user_id,
        verifier_role=user.role.value,
        organization_id=user.organization_id,
    )
    if not evt:
        raise HTTPException(status_code=404, detail="Extracted event not found.")
    return {"status": "REJECTED", "event": evt}


@router.get("/{doc_id}/content")
def get_document_content(
    doc_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Streams the document file content for preview."""
    doc = get_document_by_id(doc_id, organization_id=user.organization_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage_path = doc.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=404, detail="Document file not found.")

    # Normalize path if it contains data/uploads/ but is from a different machine
    normalized_path = storage_path
    import os
    if "data\\uploads\\" in storage_path:
        normalized_path = os.path.join(os.getcwd(), "data", "uploads", storage_path.split("data\\uploads\\")[-1])
    elif "data/uploads/" in storage_path:
        normalized_path = os.path.join(os.getcwd(), "data", "uploads", storage_path.split("data/uploads/")[-1])

    from pathlib import Path
    path = Path(normalized_path)

    if not path.exists():
        # Fallback to Supabase download if possible
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            import tempfile
            db = get_supabase_admin()
            if db:
                clean_name = Path(storage_path).name
                org_id = doc.get("organization_id") or "00000000-0000-0000-0000-000000000001"
                
                # Try multiple path patterns in Supabase bucket
                candidates_sb = [
                    storage_path.replace("documents/", ""),
                    f"{org_id}/{clean_name}",
                    clean_name,
                    storage_path,
                ]
                data = None
                for sb_path in candidates_sb:
                    try:
                        data = db.storage.from_("documents").download(sb_path)
                        if data:
                            break
                    except Exception:
                        continue

                if data:
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=f".{doc.get('document_type', 'TXT').lower()}")
                    tfile.write(data)
                    tfile.close()
                    path = Path(tfile.name)
        except Exception as e:
            logger.debug(f"Storage download attempt failed: {e}")

    if not path.exists():
        raise HTTPException(status_code=404, detail="File content could not be found locally or remotely.")

    from fastapi.responses import FileResponse
    ext = path.suffix.lower()
    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".csv": "text/csv",
    }
    return FileResponse(path=str(path), media_type=media_map.get(ext, "application/octet-stream"))

