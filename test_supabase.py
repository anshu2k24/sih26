import os
import json
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client, Client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

record = {
    "id": "00000000-0000-0000-0000-000000000001",
    "title": "Test",
    "raw_ocr_text": "",
    "verified_text": "",
    "source": "handwritten",
    "source_file_id": "",
    "storage_path": "",
    "public_url": "",
    "ocr_status": "UPLOADED",
    "verification_status": "NEEDS_REVIEW",
    "confidence": None,
    "confidence_level": "UNKNOWN",
    "latest_ocr_run_id": None,
    "structured_data": {},
    "metadata": {},
    "created_by": "system",
    "verified_by": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "verified_at": None,
    "is_deleted": False,
}

try:
    response = supabase.table('handwritten_notes').upsert(record).execute()
    print("Success:", response)
except Exception as e:
    print("Error:", e)
