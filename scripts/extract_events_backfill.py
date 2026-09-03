import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath('src'))

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.documents.extractor import extract_text_from_file
from ertmac.documents.parser import parse_extracted_events
from ertmac.documents.verifier import DocumentVerificationEngine

logging.basicConfig(level=logging.INFO)

def main():
    print("Starting Extracted Events Backfill for historical digital documents...")
    db = get_supabase_admin()
    if not db:
        print("No supabase admin, cannot fetch data.")
        return

    docs_res = db.table("documents").select("*").execute()
    docs = docs_res.data
    
    success = 0
    print(f"Found {len(docs)} documents to process.")
    
    for doc in docs:
        doc_id = doc["id"]
        storage_path = doc.get("storage_path")
        doc_type = doc.get("document_type", "TXT")
        organization_id = doc.get("organization_id", "00000000-0000-0000-0000-000000000001")
        well_id = doc.get("source_metadata", {}).get("well_id", "15/9-F-14")
        
        if not storage_path:
            continue
            
        try:
            print(f"Extracting text for {doc_id}...")
            text_content, status, err = extract_text_from_file(storage_path, doc_type)
            if status == "EXTRACTED" and text_content:
                events = parse_extracted_events(
                    document_id=doc_id,
                    text=text_content,
                    default_well_id=well_id,
                    organization_id=organization_id,
                )
                if events:
                    DocumentVerificationEngine.save_extracted_events(doc_id, events)
                    print(f"  -> Saved {len(events)} events for {doc_id}")
                    success += 1
                else:
                    print(f"  -> No events found in {doc_id}")
            else:
                print(f"  -> Extraction failed or no text: {status} {err}")
        except Exception as e:
            print(f"Error {doc_id}: {e}")

    print(f"Successfully extracted events for {success} documents.")

if __name__ == "__main__":
    main()
