import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
try:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("SELECT doc_id, chunk_index, text FROM public.rag_documents WHERE doc_id LIKE 'note:%' LIMIT 5;")
    res = cur.fetchall()
    print("Found notes in pgvector:", len(res))
    for r in res:
        print(f"Doc ID: {r[0]}, Chunk: {r[1]}, Text Preview: {r[2][:50]}")
    
except Exception as e:
    print("Error:", e)
