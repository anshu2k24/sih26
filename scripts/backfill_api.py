import os
import requests
from dotenv import load_dotenv

load_dotenv()
from ertmac.auth.supabase_client import get_supabase_admin

def main():
    print("Triggering RAG backfill via Backend API...")
    db = get_supabase_admin()
    if not db:
        print("No supabase admin, cannot fetch data.")
        return

    docs_res = db.table("documents").select("id").execute()
    docs = docs_res.data
    
    success = 0
    print(f"Triggering indexing for {len(docs)} documents over HTTP...")
    
    for doc in docs:
        doc_id = doc["id"]
        try:
            print(f"Indexing document: {doc_id}")
            res = requests.post(
                "http://localhost:8000/api/v1/rag/index",
                json={"note_id": doc_id, "force_reindex": True}
            )
            if res.status_code == 200:
                print(f"Success: {doc_id} -> {res.json()}")
                success += 1
            else:
                print(f"Failed {doc_id}: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"Error {doc_id}: {e}")

    print(f"Successfully triggered {success} documents.")

if __name__ == "__main__":
    main()
