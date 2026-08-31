# RAG Module — Architecture

## System Overview

```
Original Handwritten Image
        ↓
Uploaded File
        ↓
File Validation
        ↓
Image Preprocessing
        ↓
OCR (Mistral Vision)
        ↓
Raw OCR Result
        ↓
Normalized Text
        ↓
Structured Information Extraction
        ↓
Human Verification ← TRUST BOUNDARY
        ↓
Verified Note (VERIFIED status)
        ↓
┌───────────────────────────────────────────┐
│         RAG INGESTION PIPELINE            │
│  (new — src/ertmac/rag/)                  │
│                                           │
│  NotesAdapter (read-only)                 │
│      ↓                                    │
│  ChunkingService                          │
│  (structure-aware: sections→paragraphs)   │
│      ↓                                    │
│  EmbeddingService                         │
│  (sentence-transformers / Mistral)        │
│      ↓                                    │
│  VectorStore                              │
│  (pgvector / local numpy fallback)        │
└───────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│         RAG RETRIEVAL PIPELINE            │
│                                           │
│  User Query                               │
│      ↓                                    │
│  SemanticSearch + KeywordSearch           │
│      ↓                                    │
│  MetadataFilter                           │
│      ↓                                    │
│  HybridRanking (weighted combination)     │
│      ↓                                    │
│  ProvenanceEnrichment                     │
│      ↓                                    │
│  SearchResults (with traceability)        │
│      ↓ (optional)                         │
│  AnswerGenerationService (Mistral)        │
│      ↓                                    │
│  Answer + Source Citations                │
└───────────────────────────────────────────┘
```

## Component Architecture

```
src/ertmac/rag/
│
├── __init__.py                   Package root — exports rag_router
├── .env.example                  All RAG environment variables
│
├── models/                       Pure data models
│   ├── rag_document.py           Note indexing state (RAGDocument)
│   ├── rag_chunk.py              Searchable text unit (RAGChunk)
│   ├── search_result.py          Retrieval result + ProvenanceInfo
│   └── query_model.py            Search request + filters
│
├── adapters/                     Isolation from existing OCR pipeline
│   ├── notes_adapter.py          READ-ONLY access to NoteRepository
│   └── provenance_adapter.py     Builds chunk → note → image chain
│
├── embeddings/                   Text → vector conversion
│   ├── base.py                   Abstract EmbeddingProvider interface
│   ├── sentence_transformer_provider.py  all-MiniLM-L6-v2 (default)
│   ├── mistral_provider.py       Mistral embedding API (optional)
│   └── factory.py                get_embedding_provider()
│
├── vectorstore/                  Vector similarity storage
│   ├── base.py                   Abstract VectorStore interface
│   ├── pgvector_store.py         PostgreSQL + pgvector (production)
│   ├── local_store.py            numpy cosine fallback (dev only)
│   └── factory.py                get_vector_store()
│
├── repositories/                 Persistence layer
│   ├── document_index_repository.py   RAG indexing state tracking
│   └── rag_audit_repository.py        Write-only audit log
│
├── database/                     Additive SQL migrations
│   ├── migrations/
│   │   └── 001_rag_schema.sql    Creates rag_documents + rag_chunks
│   └── migrate.py                Migration runner script
│
├── services/                     Core business logic
│   ├── chunking_service.py       Structure-aware document chunking
│   ├── embedding_service.py      Batch embedding with error handling
│   ├── ingestion_service.py      Full index pipeline (idempotent)
│   ├── keyword_search_service.py  Full-text / exact search
│   ├── semantic_search_service.py Vector similarity search
│   ├── metadata_search_service.py Structured filter application
│   ├── hybrid_search_service.py  Orchestrates all three signals
│   ├── context_builder_service.py Assembles LLM context + citations
│   └── answer_generation_service.py Optional LLM Q&A
│
├── llm/                          Optional LLM providers
│   ├── base.py                   Abstract LLMProvider interface
│   ├── mistral_llm.py            Mistral chat completion
│   └── factory.py                get_llm_provider()
│
├── api/                          FastAPI router (self-contained)
│   ├── rag_schemas.py            Pydantic request/response models
│   ├── rag_controller.py         Business logic handlers
│   └── rag_router.py             APIRouter + route definitions
│
├── tests/                        Full unit test suite
│   ├── test_chunking.py
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_provenance.py
│   └── test_answer_generation.py
│
├── docs/                         Documentation
│   ├── architecture.md           This file
│   ├── integration.md            Server.py + App.tsx integration steps
│   └── api.md                    API reference
│
└── README.md                     Module README
```

## Data Flow: Ingestion

```
note_id
    ↓ NotesAdapter.get_verified_note()
    ↓ [GATE: verification_status == "VERIFIED"]
    ↓ [GATE: verified_text.strip() is not empty]
    ↓ content_hash = SHA-256(verified_text)
    ↓ [IDEMPOTENCY: same hash → skip]
    ↓ delete_existing_chunks(note_id)
    ↓ chunk_note() → List[RAGChunk]
    ↓ embed_chunks() → List[RAGChunk with embeddings]
    ↓ vector_store.upsert_chunks()
    ↓ document_index_repo.upsert(INDEXED)
    ↓ audit_log(INDEX_COMPLETED)
```

## Data Flow: Retrieval (Hybrid)

```
query_text + filters
    ↓
    ├── SemanticSearch: embed_query() → vector_store.similarity_search()
    ├── KeywordSearch:  fulltext_search(query)
    └── MetadataSearch: filter_by_date/tags/identifiers
    ↓
    merge_results(semantic, keyword)
    ↓
    min-max normalize scores
    ↓
    weighted_combination(semantic*0.6 + keyword*0.4)
    ↓
    deduplicate_by_chunk_id
    ↓
    sort_by_score
    ↓
    enrich_provenance
    ↓
    SearchResult[] (with chunk→note→ocr→image chain)
```

## Design Principles

| Principle | Implementation |
|---|---|
| **Additive only** | Zero modifications to existing files |
| **Trust boundary** | Only VERIFIED notes ever enter the index |
| **Idempotent** | SHA-256 hash prevents duplicate indexing |
| **Provenance** | Every chunk → note → OCR run → image |
| **No hallucination** | LLM answers from retrieved context only |
| **Fallback** | Local numpy store when pgvector unavailable |
| **Auditability** | Every RAG operation is logged with timestamps |
