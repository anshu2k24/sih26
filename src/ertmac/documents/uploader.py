"""
PS26121 eRTMAC-NWIS — Document Uploader Module
Handles document storage, SHA-256 checksum calculation, deduplication check,
and database record creation for uploaded drilling reports and logs.
"""

import os
import uuid
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin

logger = logging.getLogger("ertmac.documents.uploader")

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_in_memory_docs: Dict[str, Dict[str, Any]] = {}


def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 checksum of file bytes for deduplication."""
    return hashlib.sha256(content).hexdigest()


def upload_document(
    filename: str,
    file_bytes: bytes,
    user_id: str,
    organization_id: str = "00000000-0000-0000-0000-000000000001",
) -> Tuple[Dict[str, Any], bool]:
    """
    Saves document file, calculates checksum, checks for duplicate upload,
    and returns (doc_dict, is_duplicate).
    """
    checksum = compute_sha256(file_bytes)
    ext = Path(filename).suffix.lstrip(".").upper() or "TXT"

    # 1. Check deduplication in DB
    db = get_supabase_admin()
    if db:
        try:
            res = db.table("documents").select("*").eq("checksum", checksum).execute()
            if res.data and len(res.data) > 0:
                logger.info(f"Duplicate document upload detected via SHA-256 checksum: {checksum}")
                return res.data[0], True
        except Exception as e:
            logger.warning(f"Deduplication check failed in DB: {e}")

    # Check in-memory deduplication
    for doc in _in_memory_docs.values():
        if doc.get("checksum") == checksum:
            return doc, True

    doc_id = f"DOC_{uuid.uuid4().hex[:8].upper()}"
    saved_filename = f"{doc_id}_{Path(filename).name}"
    storage_path = f"documents/{organization_id}/{saved_filename}"

    # Try saving locally as cached copy if directory exists/writable
    local_path = None
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        local_target = UPLOAD_DIR / saved_filename
        local_target.write_bytes(file_bytes)
        local_path = str(local_target)
    except Exception as e:
        logger.debug(f"Local file caching skipped: {e}")

    # Upload to Supabase Storage
    if db:
        try:
            db.storage.from_("documents").upload(
                path=f"{organization_id}/{saved_filename}",
                file=file_bytes,
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
            storage_path = f"documents/{organization_id}/{saved_filename}"
            logger.info(f"Uploaded file to Supabase Storage: {storage_path}")
        except Exception as e:
            logger.warning(f"Supabase Storage upload warning (using fallback path): {e}")
            if local_path:
                storage_path = local_path

    now = datetime.now(timezone.utc).isoformat()
    doc_record = {
        "id": doc_id,
        "organization_id": organization_id,
        "filename": filename,
        "storage_path": storage_path,
        "document_type": ext,
        "uploaded_by": user_id if len(user_id) == 36 and user_id != "00000000-0000-0000-0000-000000000001" else None,
        "checksum": checksum,
        "processing_status": "COMPLETED",
        "extraction_status": "PENDING",
        "verification_status": "PENDING",
        "source_metadata": {
            "file_size_bytes": len(file_bytes),
            "original_filename": filename,
            "uploaded_at": now,
        },
        "created_at": now,
        "updated_at": now,
    }

    _in_memory_docs[doc_id] = doc_record

    # Persist to Supabase DB if available
    if db:
        try:
            db_payload = {
                "organization_id": organization_id,
                "filename": filename,
                "storage_path": storage_path,
                "document_type": ext,
                "checksum": checksum,
                "processing_status": "COMPLETED",
                "extraction_status": "PENDING",
                "verification_status": "PENDING",
                "source_metadata": doc_record["source_metadata"],
            }
            if doc_record["uploaded_by"]:
                db_payload["uploaded_by"] = doc_record["uploaded_by"]

            res = db.table("documents").insert(db_payload).execute()
            if res.data and len(res.data) > 0:
                doc_record = res.data[0]
                doc_id = str(doc_record["id"])
                _in_memory_docs[doc_id] = doc_record
        except Exception as e:
            logger.error(f"Failed to insert document record into Supabase: {e}")

    return doc_record, False


def get_documents(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns list of uploaded documents."""
    db = get_supabase_admin()
    if db:
        try:
            res = db.table("documents").select("*").order("created_at", desc=True).limit(limit).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            logger.warning(f"Failed to fetch documents from DB: {e}")

    return list(reversed(list(_in_memory_docs.values())))[:limit]


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetches single document by ID."""
    if doc_id in _in_memory_docs:
        return _in_memory_docs[doc_id]

    db = get_supabase_admin()
    if db:
        try:
            res = db.table("documents").select("*").eq("id", doc_id).single().execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Failed to fetch document {doc_id} from DB: {e}")

    return None
