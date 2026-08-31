"""
PS121 Handwritten Notes Module
"""

from ertmac.notes.validator import FileValidator, FileValidationError
from ertmac.notes.normalizer import TextNormalizer
from ertmac.notes.extractor import StructuredExtractor
from ertmac.notes.storage import NoteStorageManager, global_storage_manager
from ertmac.notes.repository import NoteRepository, global_note_repository
from ertmac.notes.service import HandwrittenNotesService, global_handwritten_notes_service

__all__ = [
    "FileValidator",
    "FileValidationError",
    "TextNormalizer",
    "StructuredExtractor",
    "NoteStorageManager",
    "global_storage_manager",
    "NoteRepository",
    "global_note_repository",
    "HandwrittenNotesService",
    "global_handwritten_notes_service",
]
