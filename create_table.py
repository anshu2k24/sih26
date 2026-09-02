import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_str = os.environ.get("DATABASE_URL")
try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS handwritten_notes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT,
        raw_ocr_text TEXT,
        verified_text TEXT,
        source TEXT,
        source_file_id TEXT,
        storage_path TEXT,
        public_url TEXT,
        ocr_status TEXT,
        verification_status TEXT,
        confidence FLOAT,
        confidence_level TEXT,
        latest_ocr_run_id TEXT,
        structured_data JSONB,
        metadata JSONB,
        created_by TEXT,
        verified_by TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        verified_at TIMESTAMPTZ,
        is_deleted BOOLEAN DEFAULT FALSE
    );
    """)
    conn.commit()
    print("Table handwritten_notes created successfully!")
except Exception as e:
    print(f"Database error: {e}")
finally:
    if 'conn' in locals() and conn:
        cur.close()
        conn.close()
