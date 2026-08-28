"""
PS26121 — Deploy schema.sql to Supabase safely.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

schema_path = Path(__file__).parent / "schema.sql"
if not schema_path.exists():
    print(f"ERROR: {schema_path} does not exist")
    sys.exit(1)

print(f"Connecting to Supabase PostgreSQL...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print(f"Reading {schema_path}...")
    sql_script = schema_path.read_text(encoding="utf-8")

    print("Deploying schema to Supabase...")
    cur.execute(sql_script)
    print("Schema deployed successfully.")

    cur.close()
    conn.close()
    print("Done.")
except Exception as e:
    print(f"Deployment error: {e}")
    sys.exit(1)

