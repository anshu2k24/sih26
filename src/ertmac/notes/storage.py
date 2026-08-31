"""
PS121 Handwritten Notes OCR — Image Storage Manager
Preserves original uploaded handwritten document images:
- Calculates immutable SHA-256 checksums for provenance & deduplication
- Stores original images in local persistent storage directory
- Integrates with Supabase Storage when configured
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured

logger = logging.getLogger("ertmac.notes.storage")

# Root directory for local handwritten note files
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
STORAGE_DIR = REPO_ROOT / "data" / "notes_images"


class NoteStorageManager:
    """
    Manages physical storage of uploaded handwritten documents and maintains SHA-256 provenance.
    """

    def __init__(self, base_dir: Optional[Path] = None, bucket_name: str = "notes_storage"):
        self.base_dir = base_dir or STORAGE_DIR
        self.bucket_name = bucket_name
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_file(
        self,
        file_bytes: bytes,
        filename: str,
        note_id: str,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Saves file bytes to disk and computes SHA-256 checksum.
        
        Returns:
            Dict with 'file_id', 'storage_path', 'checksum', 'size_bytes', 'filename'.
        """
        checksum = hashlib.sha256(file_bytes).hexdigest()
        
        # Preserve original extension
        ext = Path(filename).suffix or ".jpg"
        stored_filename = f"{note_id}_{checksum[:12]}{ext}"
        target_path = self.base_dir / stored_filename

        # Write to local disk
        target_path.write_bytes(file_bytes)
        try:
            relative_path = str(target_path.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            relative_path = str(target_path).replace("\\", "/")

        supabase_url: Optional[str] = None
        if is_supabase_configured():
            try:
                client = get_supabase_admin()
                # Optional upload to Supabase storage bucket
                client.storage.from_(self.bucket_name).upload(
                    stored_filename,
                    file_bytes,
                    {"content-type": mime_type, "upsert": "true"}
                )
                supabase_url = client.storage.from_(self.bucket_name).get_public_url(stored_filename)
            except Exception as e:
                logger.debug(f"Supabase storage upload skipped/failed: {e}")

        return {
            "file_id": f"file_{checksum[:16]}",
            "filename": filename,
            "stored_filename": stored_filename,
            "storage_path": relative_path,
            "absolute_path": str(target_path),
            "checksum": checksum,
            "size_bytes": len(file_bytes),
            "mime_type": mime_type,
            "public_url": supabase_url or f"/api/v1/notes/images/{stored_filename}",
        }

    def get_file_bytes(self, storage_path: str) -> Optional[bytes]:
        """Retrieves raw image bytes from storage path."""
        p = REPO_ROOT / storage_path if not Path(storage_path).is_absolute() else Path(storage_path)
        if p.exists():
            return p.read_bytes()
        return None


# Global singleton instance
global_storage_manager = NoteStorageManager()
