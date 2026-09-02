import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
try:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.rag_documents');")
    res = cur.fetchone()[0]
    print("Table rag_documents exists:", res is not None)
    
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
    ext = cur.fetchone()
    print("pgvector installed:", ext is not None)
    
except Exception as e:
    print("Error:", e)
