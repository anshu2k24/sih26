import os
import sys
import traceback
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath('src'))
from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.rag.adapters.notes_adapter import global_notes_adapter
from ertmac.rag.services.ingestion_service import global_ingestion_service

def main():
    print("Starting RAG backfill...")
    db = get_supabase_admin()
    if not db:
        print("No supabase admin, cannot fetch data.")
        return

    success = 0

    print("Fetching VERIFIED handwritten notes...")
    notes = global_notes_adapter.list_verified_notes()
    print(f"Found {len(notes)} verified handwritten notes.")
    
    for doc_dto in notes:
        try:
            print(f"Indexing note: {doc_dto.note_id}")
            global_ingestion_service.index_note(doc_dto.note_id, force_reindex=True)
            success += 1
        except Exception as e:
            print(f"Failed to index note {doc_dto.note_id}: {e}")
            
    print("Fetching ALL digital documents...")
    docs_res = db.table("documents").select("*").execute()
    docs = docs_res.data
    print(f"Found {len(docs)} digital documents.")
    
    for doc in docs:
        try:
            print(f"Indexing document: {doc['id']}")
            global_ingestion_service.index_note(doc['id'], force_reindex=True)
            success += 1
        except Exception as e:
            print(f"Failed to index doc {doc.get('id')}: {e}")

    print(f"Successfully indexed {success} documents/notes into local RAG.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
