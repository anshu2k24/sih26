"""RAG Adapters — isolation layer between RAG module and existing OCR pipeline"""
from ertmac.rag.adapters.notes_adapter import NotesAdapter, VerifiedNoteDTO
from ertmac.rag.adapters.provenance_adapter import ProvenanceAdapter

__all__ = ["NotesAdapter", "VerifiedNoteDTO", "ProvenanceAdapter"]
