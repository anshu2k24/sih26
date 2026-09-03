import os
import asyncio
from dotenv import load_dotenv
from ertmac.notes.repository import NoteRepository

load_dotenv()
repo = NoteRepository()

record = repo.create_note({
    "title": "Test Note",
    "raw_ocr_text": "hello",
    "verified_text": "hello",
})

print(f"Created note in repository. Note ID: {record['id']}")

notes = repo.list_notes()
print(f"Notes returned by list_notes: {len(notes)}")
