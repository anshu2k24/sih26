import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("summarize_digital_docs")

from ertmac.auth.supabase_client import get_supabase_admin
from ertmac.documents.extractor import extract_text_from_file
from ertmac.rag.llm.factory import get_llm_provider

# The system prompt to generate a JSON summary and tags
SUMMARY_PROMPT = """You are a technical analyst summarizing drilling reports and equipment logs.
Given the following raw text extracted from a document, generate a brief, professional summary (max 3 sentences) 
and a list of up to 5 relevant technical tags.

Return ONLY a valid JSON object with the following structure:
{
    "summary": "The brief summary of the document.",
    "tags": ["tag1", "tag2", "tag3"]
}

If the text appears to be placeholder or dummy text (e.g. 'Unique DDR Log Content'), generate a generic summary stating it is a placeholder log and use tags like 'Placeholder', 'DDR', 'Log'.
"""

async def process_documents():
    db = get_supabase_admin()
    if not db:
        logger.error("Failed to connect to Supabase.")
        return

    # Fetch digital documents
    response = db.table('documents').select('id, filename, storage_path, document_type, source_metadata').execute()
    docs = response.data
    logger.info(f"Found {len(docs)} documents.")

    llm = get_llm_provider()
    
    for doc in docs:
        doc_id = doc['id']
        filename = doc['filename']
        storage_path = doc['storage_path']
        doc_type = doc['document_type']
        source_metadata = doc.get('source_metadata') or {}
        
        # Skip if already summarized
        if 'summary' in source_metadata and source_metadata['summary']:
            logger.info(f"Skipping {doc_id} ({filename}) - already summarized.")
            continue
            
        logger.info(f"Processing {doc_id} ({filename})...")
        
        # Extract text
        text_content, status, err = extract_text_from_file(storage_path, doc_type)
        if not text_content:
            text_content = f"Placeholder content for {filename}. Failed to extract physical text."
        
        # Keep it within context limits
        if len(text_content) > 10000:
            text_content = text_content[:10000]
            
        try:
            # Generate summary
            result_text = llm.generate_answer(
                question="Extract summary and tags in JSON format.",
                context=text_content,
                system_prompt=SUMMARY_PROMPT,
                max_tokens=500
            )
            
            # Parse JSON
            # Sometimes LLMs wrap JSON in markdown blocks
            clean_text = result_text.replace("```json", "").replace("```", "").strip()
            result_json = json.loads(clean_text)
            
            summary = result_json.get("summary", "")
            tags = result_json.get("tags", [])
            
            # Update source_metadata
            source_metadata['summary'] = summary
            source_metadata['tags'] = tags
            
            db.table('documents').update({'source_metadata': source_metadata}).eq('id', doc_id).execute()
            logger.info(f"  -> Success! Tags: {tags}")
            
        except Exception as e:
            logger.error(f"  -> Failed to generate summary for {doc_id}: {e}")
            
if __name__ == "__main__":
    asyncio.run(process_documents())
