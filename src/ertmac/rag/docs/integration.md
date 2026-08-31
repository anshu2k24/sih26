# RAG Module — Minimal Integration Steps

This document records the **exact two-file modifications** required to activate the RAG module in the running application. These modifications are minimal and additive.

> **Per the project spec, these modifications are documented here but not applied automatically.**
> Apply them when ready to activate RAG in the application.

---

## Step 1: Mount the RAG Router in `server.py`

**File:** `src/ertmac/api/server.py`

Add these two lines to the router registration section (after existing routers are included):

```python
# RAG Intelligent Search — PS121 RAG Module
from ertmac.rag.api.rag_router import router as rag_router
app.include_router(rag_router)
```

The RAG router uses prefix `/api/v1/rag` and is completely self-contained.
It reuses the existing `require_permission` / `get_current_user` auth dependencies with zero modifications.

---

## Step 2: Add RAG Page Route to Frontend

**File:** `frontend/src/App.tsx` (or wherever your routes are defined)

```tsx
// Add this import
import { RAGSearchPage } from "./pages/RAGSearchPage";

// Add this route inside your protected Routes
<Route path="/rag" element={<RAGSearchPage />} />
```

---

## Step 3: Add Sidebar Navigation Link

**File:** `frontend/src/components/layout/Sidebar.tsx`

Add a RAG Search navigation item to the `navItems` array:

```tsx
{ to: "/rag", label: "RAG SEARCH", icon: Search },
```

The `Search` icon is already available from `lucide-react` which is used throughout the existing Sidebar.

---

## Step 4: Run Database Migration

```bash
# From the project root
python src/ertmac/rag/database/migrate.py
```

This creates the `rag_documents` and `rag_chunks` tables with pgvector support.
**Additive only — no existing tables are modified.**

---

## Step 5: Set Environment Variables

Add to your `.env` file (reference `.env.example` in `src/ertmac/rag/`):

```env
RAG_ENABLED=true
RAG_EMBEDDING_PROVIDER=sentence_transformers
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_VECTOR_STORE=pgvector  # or "local" for development
RAG_LLM_ENABLED=false      # set true to enable AI answers
```

---

## Verification

After applying the above:

```bash
# Run RAG tests
python -m pytest src/ertmac/rag/tests/ -v

# Start backend
python src/ertmac/api/server.py  # or your existing start command

# Health check
curl http://localhost:8000/api/v1/rag/health

# Index a verified note
curl -X POST http://localhost:8000/api/v1/rag/index \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note_id": "your-verified-note-id"}'

# Search
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "pump vibration", "top_k": 5}'
```
