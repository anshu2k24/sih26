import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("--- Checking Tables ---")
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name IN ('rag_documents', 'rag_chunks')
    ORDER BY table_name;
""")
for row in cur.fetchall():
    print(f"Table: {row[0]}")

print("\n--- Checking Indexes ---")
cur.execute("""
    SELECT tablename, indexname, indexdef
    FROM pg_indexes 
    WHERE schemaname = 'public' AND tablename IN ('rag_documents', 'rag_chunks')
    ORDER BY tablename, indexname;
""")
for row in cur.fetchall():
    print(f"Index [{row[0]}]: {row[1]}")

cur.close()
conn.close()
