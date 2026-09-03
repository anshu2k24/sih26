"""
PS121 Handwritten Notes OCR — REST API Router
Exposes endpoints for:
- Upload & OCR Transcription (/api/v1/notes/ocr)
- Review & Verification (/api/v1/notes/:id/verify)
- OCR Retry (/api/v1/notes/:id/retry)
- Provenance & Processing History (/api/v1/notes/:id/ocr-runs)
- Search & Retrieval (/api/v1/notes)
- Export (/api/v1/notes/:id/export)
- Dashboard Metrics (/api/v1/notes/metrics)
- Image Streaming (/api/v1/notes/images/:filename)
"""

import os
import io
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    UserSession,
    Permission,
)
from ertmac.notes.service import HandwrittenNotesService, global_handwritten_notes_service
from ertmac.notes.validator import FileValidationError

logger = logging.getLogger("ertmac.api.notes")

router = APIRouter(prefix="/api/v1/notes", tags=["PS121 Handwritten Notes OCR"])


class DraftUpdateRequest(BaseModel):
    title: Optional[str] = None
    verified_text: str


class VerifyNoteRequest(BaseModel):
    title: Optional[str] = None
    verified_text: str


@router.post("/ocr", summary="Upload handwritten note image and perform OCR")
async def upload_handwritten_note_ocr(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    user: UserSession = Depends(require_permission(Permission.UPLOAD_NOTES)),
):
    """
    Receives handwritten image file (JPEG, PNG, WEBP, HEIC, PDF),
    validates magic bytes and size, stores original for provenance,
    runs OCR preprocessing, executes selected OCR model, extracts structured entities,
    and returns initial draft transcription.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = file.filename or "handwritten_note.jpg"

    try:
        result = await global_handwritten_notes_service.ingest_handwritten_note(
            file_bytes=contents,
            filename=filename,
            user_id=user.user_id,
            organization_id=user.organization_id,
            title_override=title,
            ocr_model=model,
        )
        return result
    except FileValidationError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during note OCR ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR ingestion failed: {str(e)}")


@router.get("", summary="List handwritten notes")
def list_handwritten_notes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status (NEEDS_REVIEW, VERIFIED, FAILED, PROCESSING)"),
    q: Optional[str] = Query(None, description="Search term in title, text, or tags"),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Retrieves paginated list of handwritten notes with optional search and status filtering."""
    notes = global_handwritten_notes_service.repo.list_notes(
        limit=limit,
        offset=offset,
        status_filter=status,
        search_query=q,
    )
    return {
        "count": len(notes),
        "limit": limit,
        "offset": offset,
        "notes": notes,
    }


@router.get("/metrics", summary="Get OCR dashboard metrics")
def get_notes_metrics(
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Returns aggregated stats: Total Notes, Needs Review, Verified, Failed, Processing."""
    return global_handwritten_notes_service.get_dashboard_metrics()


@router.get("/{note_id}", summary="Get single handwritten note details")
def get_handwritten_note_detail(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Fetches complete note details including raw OCR, verified text, structured data, and provenance."""
    note = global_handwritten_notes_service.repo.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    
    ocr_runs = global_handwritten_notes_service.repo.get_ocr_runs(note_id)
    return {
        "note": note,
        "ocr_runs": ocr_runs,
        "provenance": {
            "source_file_id": note.get("source_file_id"),
            "storage_path": note.get("storage_path"),
            "checksum": note.get("metadata", {}).get("checksum"),
            "created_by": note.get("created_by"),
            "verified_by": note.get("verified_by"),
            "verified_at": note.get("verified_at"),
        },
    }


@router.patch("/{note_id}", summary="Save draft corrections to OCR text")
def update_note_draft(
    note_id: str,
    payload: DraftUpdateRequest,
    user: UserSession = Depends(require_permission(Permission.UPLOAD_NOTES)),
):
    """Saves intermediate reviewer edits without finalizing verification."""
    updated = global_handwritten_notes_service.save_draft(
        note_id=note_id,
        draft_text=payload.verified_text,
        user_id=user.user_id,
        title=payload.title,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    return {"status": "DRAFT_SAVED", "note": updated}


@router.post("/{note_id}/verify", summary="Verify and promote handwritten note")
async def verify_handwritten_note(
    note_id: str,
    payload: VerifyNoteRequest,
    user: UserSession = Depends(require_permission(Permission.VERIFY_NOTES)),
):
    """
    Finalizes human verification:
    - Saves verified text
    - Preserves raw OCR text intact
    - Updates structured entities
    - Marks status as VERIFIED with verifier ID and timestamp
    """
    verified_note = await global_handwritten_notes_service.verify_note(
        note_id=note_id,
        verified_text=payload.verified_text,
        user_id=user.user_id,
        title=payload.title,
    )
    if not verified_note:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    return {"status": "VERIFIED", "note": verified_note}


@router.post("/{note_id}/reject", summary="Reject handwritten note")
async def reject_handwritten_note(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VERIFY_NOTES)),
):
    """
    Marks a handwritten note as rejected if OCR is unsalvageable.
    """
    rejected_note = await global_handwritten_notes_service.reject_note(
        note_id=note_id,
        user_id=user.user_id,
    )
    if not rejected_note:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    return {"status": "REJECTED", "note": rejected_note}


@router.post("/{note_id}/retry", summary="Retry OCR processing on existing image")
async def retry_note_ocr(
    note_id: str,
    model: Optional[str] = Query(None),
    user: UserSession = Depends(require_permission(Permission.UPLOAD_NOTES)),
):
    """Reruns OCR on stored original image creating a new run attempt in history."""
    res = await global_handwritten_notes_service.retry_ocr(
        note_id=note_id,
        user_id=user.user_id,
        ocr_model=model,
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Retry failed"))
    return res


@router.delete("/{note_id}", summary="Delete handwritten note")
def delete_handwritten_note(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.UPLOAD_NOTES)),
):
    """Soft deletes a handwritten note."""
    ok = global_handwritten_notes_service.repo.delete_note(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    return {"status": "DELETED", "id": note_id}


@router.get("/{note_id}/ocr-runs", summary="Get OCR run processing history")
def get_note_ocr_runs(
    note_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Retrieves immutable list of all OCR attempts, provider responses, and errors for this note."""
    runs = global_handwritten_notes_service.repo.get_ocr_runs(note_id)
    return {"note_id": note_id, "count": len(runs), "ocr_runs": runs}


@router.get("/{note_id}/export", summary="Export note as TXT or JSON")
def export_handwritten_note(
    note_id: str,
    format: str = Query("json", pattern="^(json|txt)$"),
    user: UserSession = Depends(require_permission(Permission.VIEW_HISTORICAL_DATA)),
):
    """Exports verified note in requested format."""
    content, media_type = global_handwritten_notes_service.export_note(note_id, export_format=format)
    if content is None:
        raise HTTPException(status_code=404, detail="Handwritten note not found.")
    
    filename = f"note_{note_id[:8]}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/images/{filename:path}", summary="Serve note image file")
def serve_note_image(filename: str):
    """Streams stored image file to browser for side-by-side verification preview with robust path resolution."""
    import urllib.parse
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    
    decoded_filename = urllib.parse.unquote(filename)
    clean_name = decoded_filename.split("/")[-1].split("\\")[-1]
    
    # Check candidates
    candidates = [
        repo_root / "data" / "notes_images" / clean_name,
        repo_root / "data" / "uploads" / clean_name,
        repo_root / "data" / "notes_images" / filename,
        repo_root / "data" / "uploads" / filename,
        Path(decoded_filename),
        Path(filename),
    ]

    # Search in notes_images and uploads by prefix or partial match
    for search_dir in [repo_root / "data" / "notes_images", repo_root / "data" / "uploads"]:
        if search_dir.exists():
            for f in search_dir.iterdir():
                if f.is_file():
                    # Match by full name, prefix (like note id), or partial filename
                    name_no_ext = clean_name.split(".")[0]
                    if clean_name == f.name or (len(name_no_ext) >= 8 and name_no_ext in f.name):
                        candidates.append(f)

    img_path = None
    for c in candidates:
        if c.exists() and c.is_file():
            img_path = c
            break

    # If not on local disk, try downloading directly from Supabase Storage bucket
    if not img_path:
        from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured
        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                if client:
                    data = client.storage.from_("notes_storage").download(clean_name)
                    if data:
                        target = repo_root / "data" / "notes_images" / clean_name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                        img_path = target
            except Exception as e:
                logger.debug(f"Supabase storage note image download attempt failed: {e}")

    # If still not found, check if there is an image in notes_images as fallback
    if not img_path:
        notes_images_dir = repo_root / "data" / "notes_images"
        if notes_images_dir.exists():
            existing = [f for f in notes_images_dir.iterdir() if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
            if existing:
                img_path = existing[0]

    if not img_path or not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Image '{filename}' not found.")

    ext = img_path.suffix.lower()
    media_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    return FileResponse(path=str(img_path), media_type=media_map.get(ext, "image/jpeg"))
