# eRTMAC-NWIS Multi-Cloud Deployment Guide
## Vercel + Render + Supabase + Hugging Face

This guide details the exact deployment sequence, platform configurations, and operational flows for running the eRTMAC-NWIS application in production.

```text
                    OPERATORS / USERS
                            │
                            ▼
              ┌───────────────────────────┐
              │          VERCEL           │
              │  React 19 + Vite 8 SPA    │
              │  Edge CDN & Static Assets │
              └─────────────┬─────────────┘
                            │ HTTPS / WSS API
                            ▼
              ┌───────────────────────────┐
              │          RENDER           │
              │   FastAPI + Uvicorn       │
              │   Orchestration & RBAC    │
              │   0.0.0.0:$PORT Binding   │
              └─────────────┬─────────────┘
                            │
             ┌──────────────┴───────────────┐
             ▼                              ▼
      ┌─────────────┐             ┌────────────────────┐
      │  SUPABASE   │             │    HUGGING FACE    │
      │ PostgreSQL  │             │ AI / ML Service    │
      │ Auth (JWT)  │             │ - TrOCR / Vision   │
      │ Storage     │             │ - SBERT Embeddings │
      │ pgvector    │             │ - RAG Inference    │
      │ RLS         │             │ Docker Space / API │
      └─────────────┘             └────────────────────┘
```

---

## Deployment Sequence

Follow the deployment order strictly to ensure downstream dependencies resolve cleanly:

```text
STEP 1: Verify Supabase (Database, Auth, Storage, pgvector)
   ↓
STEP 2: Deploy Hugging Face AI / ML Service (Docker Space or obtain HF_TOKEN)
   ↓
STEP 3: Deploy Render Backend (FastAPI Web Service)
   ↓
STEP 4: Retrieve Render Production URL (https://<your-backend>.onrender.com)
   ↓
STEP 5: Configure Vercel Frontend with Render URL
   ↓
STEP 6: Deploy Vercel Frontend
   ↓
STEP 7: Update Render CORS with Vercel Production Domain
   ↓
STEP 8: Run End-to-End Verification
```

---

## 1. Supabase (Database, Auth, Storage, pgvector)

* **Role**: Primary stateful persistence layer.
* **Status**: Live and verified. **DO NOT run migrations or modify schemas.**
* **Components in Use**:
  * **Database**: PostgreSQL 17.6 with 19 core tables and 298k+ telemetry rows.
  * **pgvector**: Vector extension enabled with `rag_chunks` HNSW index.
  * **Storage Buckets**: `documents` and `notes_storage` (both set to Public).
  * **Auth**: Supabase GoTrue authentication with `profiles` RBAC.

### Credentials Required for Render Backend
Obtain these from your Supabase Project Dashboard (`Project Settings -> API` & `Project Settings -> Database`):
* `SUPABASE_URL`: `https://<project-ref>.supabase.co`
* `SUPABASE_ANON_KEY`: `eyJhbGciOi...`
* `SUPABASE_SERVICE_ROLE_KEY`: `eyJhbGciOi...`
* `SUPABASE_JWT_SECRET`: `<jwt-secret>`
* `DATABASE_URL`: `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`

---

## 2. Hugging Face (AI, OCR & Embeddings)

Choose one of two implementation methods:

### Option A: Serverless Inference API (Zero Dedicated Hosting)
1. Go to [Hugging Face Settings -> Access Tokens](https://huggingface.co/settings/tokens).
2. Create a new token with **Read** access.
3. In Render, set:
   * `HF_TOKEN`: `hf_...`
   * `RAG_EMBEDDING_PROVIDER`: `huggingface`

### Option B: Dedicated Containerized Docker Space (Self-Hosted Microservice)
1. Create a new Space on Hugging Face:
   * **Space SDK**: `Docker`
   * **License**: Apache 2.0
   * **Hardware**: CPU basic (Free) or T4 small (GPU).
2. Push the contents of the `huggingface/` folder in this repository to your Space repository:
   ```bash
   cd huggingface
   git init
   git remote add origin https://huggingface.co/spaces/<your-username>/<your-space-name>
   git add .
   git commit -m "Deploy eRTMAC AI Inference Engine"
   git push -u origin main
   ```
3. Once running, copy your Space URL (`https://<your-username>-<your-space-name>.hf.space`).
4. In Render, set:
   * `HF_SPACE_URL`: `https://<your-username>-<your-space-name>.hf.space`
   * `RAG_EMBEDDING_PROVIDER`: `huggingface`
   * `OCR_PROVIDER`: `huggingface`

---

## 3. Render Backend (FastAPI Web Service)

1. Connect your GitHub repository to [Render](https://dashboard.render.com/).
2. Create a new **Web Service**:
   * **Runtime**: Python 3
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn ertmac.api.server:app --host 0.0.0.0 --port $PORT`
   * **Health Check Path**: `/health`
3. Configure Environment Variables in Render:

| Variable | Recommended Value / Source | Secret? |
| :--- | :--- | :---: |
| `PYTHONPATH` | `src` | No |
| `ENVIRONMENT` | `production` | No |
| `AUTH_REQUIRED` | `true` | No |
| `STREAM_IN_PROCESS` | `true` | No |
| `CORS_ORIGINS` | `https://ertmac-nwis.vercel.app,https://<your-app>.vercel.app` | No |
| `FRONTEND_URL` | `https://<your-app>.vercel.app` | No |
| `SUPABASE_URL` | From Supabase Project Settings | **YES** |
| `SUPABASE_ANON_KEY` | From Supabase Project Settings | **YES** |
| `SUPABASE_SERVICE_ROLE_KEY` | From Supabase Project Settings | **YES** |
| `SUPABASE_JWT_SECRET` | From Supabase Project Settings | **YES** |
| `DATABASE_URL` | Direct Pooler URI from Supabase | **YES** |
| `HF_TOKEN` | Hugging Face Access Token | **YES** |
| `HF_SPACE_URL` | (Optional) Hugging Face Space URL | **YES** |
| `RAG_EMBEDDING_PROVIDER` | `sentence_transformers` or `huggingface` | No |
| `OCR_PROVIDER` | `mistral` or `huggingface` | No |
| `MISTRAL_API_KEY` | (Optional) Mistral AI API Key | **YES** |
| `RESEND_API_KEY` | (Optional) Resend API Key | **YES** |
| `RESEND_FROM_EMAIL` | `alerts@ertmac-nwis.org` | No |

4. Deploy the service. Once deployed, note your service URL (e.g. `https://ertmac-backend.onrender.com`).
5. Test health: `curl https://<your-backend>.onrender.com/health` -> `{"status": "ok", "service": "ertmac-nwis-api"}`.

---

## 4. Vercel Frontend (React + Vite SPA)

1. Connect your repository to [Vercel](https://vercel.com/new).
2. Project Configuration:
   * **Framework Preset**: `Vite`
   * **Root Directory**: `frontend` (or leave as root `/` — root `vercel.json` will auto-delegate)
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
3. Configure Environment Variables in Vercel:

| Variable | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://<your-render-backend>.onrender.com` | HTTPS API endpoint |
| `VITE_WS_BASE_URL` | `wss://<your-render-backend>.onrender.com` | Secure WebSocket endpoint |
| `VITE_SUPABASE_URL` | `https://<your-project-ref>.supabase.co` | Supabase endpoint |
| `VITE_SUPABASE_ANON_KEY` | `eyJhbGciOi...` | Public Supabase client key |

4. Click **Deploy**.

---

## 5. Sync CORS on Render

Once Vercel assigns your production domain (e.g. `https://sih26.vercel.app`):
1. In the Render Dashboard, update `FRONTEND_URL` to `https://sih26.vercel.app`.
2. Ensure `CORS_ORIGINS` includes your domain.
3. Save changes (Render will trigger a zero-downtime rolling restart).

---

## 6. End-to-End Verification Checklist

| Test Item | Verification Command / Step | Expected Result |
| :--- | :--- | :--- |
| **Backend Health** | `curl https://<render-url>/health` | `HTTP 200: {"status": "ok"}` |
| **Backend Detailed Health** | `curl https://<render-url>/health/detailed` | Shows database connected, healthy |
| **Frontend Route Serving** | Open `https://<vercel-url>/` in browser | Lands on `/login` with background images |
| **Authentication Flow** | Log in with registered user | Successful JWT receipt, navigates to Dashboard |
| **Telemetry Stream** | Open `/live` and click "START DRILLING" | WebSocket connects, live depth counter increments |
| **Map & Wellbores** | Open `/wells` or `/map` | MapLibre loads 38 wellbore markers without worker error |
| **Handwritten OCR** | Upload note at `/notes` | OCR extraction completes with confidence score |
| **RAG Intelligent Search** | Query technical question at `/rag` | Vector retrieval executes against pgvector chunks |

---

## Known Platform Limitations (Free Tier)

1. **Render Free Tier Spin-Down**:
   * Free Render web services spin down after 15 minutes of inactivity.
   * The first request after spin-down incurs a cold-start latency of ~50 seconds.
   * *Mitigation*: For demonstration, ping the `/health` endpoint every 10 minutes or upgrade to Render Starter ($7/month).
2. **Hugging Face Inference Free Tier Rate Limits**:
   * Hugging Face Serverless Inference API enforces rate limits on bursts.
   * The backend implements local fallback to cached SentenceTransformers if HF API is busy.
3. **Supabase Free Tier Connection Pooling**:
   * Always connect via the Supabase Connection Pooler (`aws-0-region.pooler.supabase.com:5432`) in `DATABASE_URL` rather than the direct database port (5432) to avoid exhausting PostgreSQL client connections.
