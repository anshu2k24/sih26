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
