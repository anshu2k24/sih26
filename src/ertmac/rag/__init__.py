"""
SIH 2026 PS121 — RAG Intelligent Search Module
===============================================

Retrieval-Augmented Generation system for the Handwritten Notes OCR Pipeline.

Architecture principle:
  OCR extracts information.
  Humans verify information.
  RAG makes verified information intelligently searchable.

This module is ADDITIVE ONLY — it does not modify any existing OCR pipeline files.

Usage (after integration):
    from ertmac.rag.api.rag_router import router as rag_router
    app.include_router(rag_router)
"""

from ertmac.rag.api.rag_router import router as rag_router

__all__ = ["rag_router"]
__version__ = "1.0.0"
