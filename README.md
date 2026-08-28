# eRTMAC-NWIS

**Real-Time Monitoring & Advisory Console with Nearby Wells Intelligence System**  
*Smart India Hackathon (SIH 2026) — Problem Statement PS26121*

[![System Status](https://img.shields.io/badge/System_Status-OPERATIONAL_GO-emerald?style=for-the-badge)](http://localhost:8000/health)
[![Cloud Database](https://img.shields.io/badge/Database-Supabase_PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Auth & RBAC](https://img.shields.io/badge/Auth-Supabase_JWT_%2B_RBAC-blue?style=for-the-badge)](https://supabase.com)
[![Frontend](https://img.shields.io/badge/Frontend-React_18_%2B_Vite_%2B_TS-61DAFB?style=for-the-badge&logo=react)](http://localhost:5173)
[![Backend Engine](https://img.shields.io/badge/Backend-FastAPI_%2B_Uvicorn-009688?style=for-the-badge&logo=fastapi)](http://localhost:8000/docs)
[![Data Provenance](https://img.shields.io/badge/Dataset-Equinor_Volve_1Hz-amber?style=for-the-badge)](https://www.equinor.com/)
[![Email Gateway](https://img.shields.io/badge/Alerts-Resend_API-black?style=for-the-badge)](https://resend.com)

> **Scientific Data Classification**: `REAL VOLVE DATA — HISTORICAL REPLAY`  
> **Telemetry Source**: Equinor Volve Real USROP 1Hz Dataset (`data/Volve_USROP_1Hz.parquet`)  
> **Persistence**: Supabase Cloud Managed PostgreSQL with Multi-Tenant Row-Level Security (RLS)  
> **Security Guard**: Strict Server-Side JWT Verification & Authoritative Database-Derived RBAC  

---

## 📑 Table of Contents
1. [Executive Summary & Problem Statement](#-executive-summary--problem-statement)
2. [End-to-End System Architecture](#-end-to-end-system-architecture)
3. [Real-Time Telemetry & Spatial Sequence Flow](#-real-time-telemetry--spatial-sequence-flow)
4. [Core Mathematical & Spatial Formulations](#-core-mathematical--spatial-formulations)
5. [13 Integrated Operational Modules](#-13-integrated-operational-modules)
6. [Interactive Well Stream Controller](#-interactive-well-stream-controller)
7. [Cloud Database Schema & Multi-Tenant RLS](#-cloud-database-schema--multi-tenant-rls)
8. [Authentication, Token Caching & RBAC Guard](#-authentication-token-caching--rbac-guard)
9. [Complete REST & WebSocket API Specification](#-complete-rest--websocket-api-specification)
10. [Quick Start & Developer Workflow](#-quick-start--developer-workflow)
11. [Environment Variable Configuration](#-environment-variable-configuration)
12. [Automated Testing & Security Invariants](#-automated-testing--security-invariants)
13. [Production Deployment Guide](#-production-deployment-guide)
14. [Scientific Integrity & Anti-Hallucination Guarantees](#-scientific-integrity--anti-hallucination-guarantees)

---

## 🎯 Executive Summary & Problem Statement

In offshore exploration and development drilling, unexpected downhole incidents (such as severe mud loss, differential sticking, tight hole conditions, kicks, and pack-offs) account for millions of dollars in Non-Productive Time (NPT) and present major health, safety, and environmental (HSE) risks.

**eRTMAC-NWIS** solves **Smart India Hackathon 2026 Problem Statement PS26121** by creating a unified, real-time intelligence console that correlates live surface & downhole sensor streams with historical offset well records from adjacent platforms.

### Key Capabilities:
* **1Hz Real-Time Sensor Streaming**: High-fidelity replay of Equinor Volve North Sea drilling operations across 11 key drilling telemetry channels.
* **Nearby Wells Intelligence (NWIS)**: Dynamic geospatial proximity matching ($\le R\text{ km}$) and stratigraphic depth window correlation ($\pm \Delta\text{MD}$).
* **Proactive Hazard Mitigation**: Real-time cross-referencing of active bit depth against past Daily Drilling Report (DDR) incident logs from neighboring wellbores.
* **Zero-Hallucination ML Gate**: Strict safety enforcement (`ML_NOT_READY`) preventing unvalidated predictive models from emitting false automated interventions.
* **Document Ingestion & OCR**: Automated parsing of legacy PDF/TXT DDR logs with human-in-the-loop verification into structured database entities.
* **Per-User Cloud Isolation**: Individualized notification filters, search radiuses, and alert recipient settings persisted in Supabase Cloud PostgreSQL.

---

## 🏛️ End-to-End System Architecture

```mermaid
flowchart TD
    subgraph DataLayer ["1. Telemetry & Intelligence Sources"]
        A["Equinor Volve Parquet<br/>data/Volve_USROP_1Hz.parquet"]
        B["NWIS Knowledge SQLite<br/>data/nwis_knowledge.db"]
        C["Uploaded DDR Documents<br/>PDF / TXT / CSV"]
    end

    subgraph StreamingEngine ["2. Real-Time Causal Streaming Pipeline"]
        D["VolveReplaySensorSource<br/>1Hz Causal Generator"]
        E["SensorWebSocketServer<br/>ws://localhost:8765"]
        F["SensorStreamClient<br/>Local Replay Consumer"]
        G["CausalStreamBuffer<br/>Max 200m Window / No Future Leakage"]
    end

    subgraph CloudPersistence ["3. Cloud Infrastructure & Security"]
        H["Supabase Auth Engine<br/>GoTrue JWT Issuer"]
        I["Supabase PostgreSQL Cluster<br/>Multi-Tenant Profiles & Tables"]
        J["Resend Email Gateway<br/>Automated Alert Delivery"]
    end

    subgraph BackendOrchestrator ["4. FastAPI Orchestration Backend (Port 8000)"]
        K["Server-Side JWT Verifier & RBAC Guard<br/>In-Memory 60s Token & Profile Cache"]
        L["REST API Endpoints<br/>/api/wells, /api/alerts, /api/settings, etc."]
        M["Application WebSocket Gateway<br/>/api/ws/wells/:well_id?token=JWT"]
        N["ML Readiness Gate<br/>ertmac.ml.ingestion"]
        O["Audit Service<br/>Append-Only Compliance Trail"]
        P["OCR & Document Parser<br/>Local Tesseract Engine"]
    end

    subgraph FrontendConsole ["5. React 18 + TypeScript Console (Port 5173)"]
        Q["Persistent AppShell Layout & Outlet"]
        R["ActiveWellContext & WebSocket Listener"]
        S["13 Operational Feature Modules"]
        T["Recharts Live Telemetry Visualizer"]
        U["Leaflet Geospatial Map"]
    end

    A --> D
    D --> E
    E --> F
    F --> G
    G --> K
    B --> L
    C --> P
    P --> L
    
    H <--> K
    I <--> L
    L --> J
    
    K --> L
    K --> M
    L --> N
    L --> O
    
    L <--> S
    M <--> R
    R --> Q
    Q --> S
    S --> T
    S --> U
```

---

## 🔄 Real-Time Telemetry & Spatial Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Drilling Engineer
    participant Frontend as React Console (Vite)
    participant Backend as FastAPI Gateway (:8000)
    participant Stream as Sensor Simulator (:8765)
    participant Supabase as Supabase Cloud Postgres
    participant Resend as Resend Email API

    Operator->>Frontend: Login (email & password)
    Frontend->>Supabase: Authenticate & receive JWT
    Frontend->>Backend: Connect WebSocket /api/ws/wells/15/9-F-14?token=JWT
    Backend->>Backend: Verify JWT & verify role from Profile Cache
    Backend-->>Frontend: 101 Switching Protocols (WS Connected)

    Stream->>Backend: 1Hz Sensor Frame (MD: 1420.5m, WOB: 8.2, ROP: 14.1)
    Backend->>Backend: Ingest into CausalStreamBuffer (No future leakage)
    Backend->>Frontend: Push typed JSON {type: "sensor_update", data: {...}}
    Frontend->>Frontend: Recharts updates Live Depth Curve

    Note over Frontend,Backend: Spatial Proximity & Offset Check (25m depth threshold)
    Frontend->>Backend: GET /api/wells/15/9-F-14/historical-proximity?current_md=1420.5
    Backend->>Backend: Geospatial Haversine Filter (<= 5.0 km) + Depth Match (+-50m)
    Backend-->>Frontend: Return 2 Historical Matches (Offset Well 15/9-F-15: Mud Loss at 1418m)
    Frontend->>Frontend: Render Proactive Warning Card

    opt If Anomaly / Incident Threshold Breached
        Backend->>Supabase: Insert new Alert (SEVERITY: HIGH, MD: 1420.5m)
        Backend->>Resend: Dispatch Alert Notification to configured recipient
        Backend->>Frontend: Broadcast Alert state change
        Operator->>Frontend: Acknowledge & add mitigation note
        Frontend->>Backend: POST /api/alerts/{id}/acknowledge
        Backend->>Supabase: Append to immutable audit_logs table
    end
```

---

## 📐 Core Mathematical & Spatial Formulations

### 1. Geospatial Haversine Surface Distance
Given active wellhead coordinates $(\phi_1, \lambda_1)$ and an offset wellbore $(\phi_2, \lambda_2)$, surface distance $d$ is computed via the great-circle Haversine formulation:

$$\Delta\phi = \phi_2 - \phi_1, \quad \Delta\lambda = \lambda_2 - \lambda_1$$

$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)$$

$$d = 2 R_{\text{earth}} \arcsin\left(\sqrt{a}\right), \quad R_{\text{earth}} \approx 6371.0 \text{ km}$$

An offset well qualifies for intelligence correlation if and only if:

$$d \le R_{\text{search}} \quad (\text{default: } 5.0\text{ km})$$

---

### 2. Stratigraphic Depth Correlation Band
Historical incident episodes from qualified offset wells are projected onto the active drilling bit depth based on Measured Depth (MD) and True Vertical Depth (TVD):

$$|\text{MD}_{\text{historical}} - \text{MD}_{\text{current}}| \le \Delta h_{\text{window}} \quad (\text{default: } \pm 50.0\text{ m})$$

---

### 3. Causal Stream Invariant Formulation
To prevent future data contamination, any statistical or ML feature function $f(\cdot)$ at stream time $t_k$ with bit depth $\text{MD}_k$ must satisfy:

$$f(\mathcal{D}_{t_k}) = f\Big(\{ s_i \in \mathcal{D} \mid t_i \le t_k, \; \text{MD}_i \le \text{MD}_k \}\Big)$$

$$\forall s_j \text{ with } \text{MD}_j > \text{MD}_k \implies s_j \notin \text{FeatureBuffer}$$

---

## 🌟 13 Integrated Operational Modules

| # | Module | Route | Key Capabilities |
|---|---|---|---|
| 1 | **Command Center** | `/dashboard` | Executive operational cockpit displaying live bit depth, TVD, WOB, ROP, Torque, RPM, mud flow, active alarms, and offset proximity alerts. |
| 2 | **Live Telemetry** | `/live` | 1Hz real-time continuous sensor chart visualizer with depth curves, sample meters, and stream diagnostics. |
| 3 | **Geospatial Map** | `/map` | Interactive Leaflet GIS map with North Sea Volve platform wellhead coordinates, 5km search radii, and dynamic distance vectors. |
| 4 | **Well Assets** | `/wells` | Master wellbore catalog with slot names, coordinates, spud dates, status indicators, and direct **Stream / Select / Intel** controllers. |
| 5 | **Well Intelligence** | `/wells/:wellId` | Stratigraphic formation tops (Hordaland, Rogaland, Shetland, Cromer Knoll, Viking, Statfjord), offset events, and 3D trajectory profiles. |
| 6 | **Knowledge Base** | `/knowledge` | Searchable NWIS domain repository with semantic filters (`DRILLING`, `GEOLOGY`, `SAFETY`, `COMPLETION`) and verified incident case studies. |
| 7 | **Documents & OCR** | `/documents` | Drag-and-drop ingestion of Daily Drilling Reports (PDF/TXT/CSV), local Tesseract OCR text extraction, and human verification workflow. |
| 8 | **Alert Operations** | `/alerts` | Multi-stage alert state machine (`ACTIVE` $\to$ `ACKNOWLEDGED` $\to$ `INVESTIGATING` $\to$ `RESOLVED`), mitigation notes, and cooldown deduplication. |
| 9 | **ML Risk Center** | `/risk` | AI model readiness inspection, safety gating metrics, feature counters, and risk prediction explainability. |
| 10 | **Compliance Audit** | `/audit` | Immutable, append-only security log recording actor ID, role, timestamp, action type, and JSON payload for corporate compliance. |
| 11 | **Handover Reports** | `/reports` | Automated Daily Drilling Report (DDR) and Shift Handover document generator with NPT/NDT operational summaries and Markdown export. |
| 12 | **Analytics** | `/analytics` | KPI console featuring alert severity breakdown pie charts, 7-day incident trends, well risk profiles, and telemetry health meters. |
| 13 | **Settings** | `/settings` | Per-user Supabase cloud configuration: customizable alert dispatch email, search radius, depth window, notification filters, and reset action. |

---

## 🎮 Interactive Well Stream Controller

From the **Well Inventory** ([/wells](http://localhost:5173/wells)), operators can manage well telemetry directly from the web console:

* **`STREAM` Button (Green Play)**: Switches the global active stream to that wellbore and navigates to the Live Telemetry Console ([/live](http://localhost:5173/live)) with 1Hz streaming.
* **`SELECT` Button (Cyan)**: Sets that well as the active drilling well across all 13 operational modules without leaving the inventory page.
* **`INTEL` Button (Blue)**: Opens the well trajectory and formation tops intelligence dashboard ([/wells/:wellId](http://localhost:5173/wells/15%2F9-F-14)).
* **Active Stream Indicator**: Top banner displays the live wellbore (`15/9-F-14`), stream status (`LIVE`), and depth progress in meters.

---

## 🗄️ Cloud Database Schema & Multi-Tenant RLS

The system connects to **Supabase Cloud PostgreSQL** with complete Row-Level Security (RLS) enforcement:

```
├── organizations (id, name, slug, license_code, created_at)
├── profiles (id [FK auth.users], organization_id, email, full_name, role, is_active, last_login_at)
├── wellbores (id, organization_id, name, slot_name, latitude, longitude, spud_date, status)
├── historical_ddr_events (id, organization_id, well_id, event_type, onset_md, tvd, summary)
├── alerts (id, well_id, organization_id, severity, status, title, description, current_md, evidence)
├── alert_notes (id, alert_id, author_id, note_text, created_at)
├── alert_escalation_rules (id, organization_id, trigger_severity, escalation_timeout_minutes)
├── notification_preferences (id, user_id [UNIQUE], notification_recipient_email, search_radius_km_default, depth_window_m_default, email_enabled, critical_alerts, high_alerts, medium_alerts, historical_alerts, report_notifications)
├── notification_deliveries (id, organization_id, alert_id, recipient_email, subject, status, error_message)
├── notification_events (id, organization_id, user_id, alert_id, title, body, is_read)
├── documents (id, organization_id, filename, storage_path, processing_status, extraction_status)
├── extracted_events (id, document_id, organization_id, well_id, event_type, onset_md, confidence, verification_status)
├── timeline_events (id, organization_id, well_id, event_timestamp, event_type, source, md, title)
├── reports (id, organization_id, well_id, report_type, current_md, content_markdown, author_id)
└── audit_logs (id, actor_id, actor_role, action, resource_type, resource_id, organization_id, payload, created_at)
```

---

## 🔐 Authentication, Token Caching & RBAC Guard

### 1. Server-Side Security Model
* **Identity Proof**: Handled via Supabase GoTrue Auth issuing signed JWT tokens.
* **In-Memory Cache (60s TTL)**: Verified JWT claims and database user profiles are cached in memory. Subsequent API calls authenticate in **<0.1 ms** with **zero redundant external HTTPS round-trips to Supabase**.
* **Zero Browser Trust**: User role is derived exclusively from the verified profile in Supabase (`profiles.role`), ignoring any client-provided role headers or payloads.

### 2. Role-Based Access Control Matrix

| Role | Telemetry | Alerts | Resolve Alerts | Admin Org | Verify Docs | Settings CRUD |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`ADMIN`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`DRILLING_ENGINEER`** | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **`OPERATIONS_ENGINEER`** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **`ANALYST`** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **`VIEWER`** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 📡 Complete REST & WebSocket API Specification

### Authentication & User Endpoints
| Method | Route | Description | Auth Level |
|---|---|---|---|
| `GET` | `/api/users/me` | Fetches current user profile and RBAC permissions | Authenticated |
| `GET` | `/health` | System health check and backend diagnostic status | Public |
| `GET` | `/health/detailed` | Deep diagnostic of database, storage, stream, and memory | Public |

### Wellbores & Spatial Intelligence
| Method | Route | Description | Auth Level |
|---|---|---|---|
| `GET` | `/api/wells` | Returns list of available Volve well assets | `VIEW_WELLS` |
| `GET` | `/api/wells/{well_id}/state` | Returns real-time state, depth, and telemetry values | `VIEW_TELEMETRY` |
| `GET` | `/api/wells/{well_id}/history` | Returns historical sensor buffer up to current MD | `VIEW_TELEMETRY` |
| `GET` | `/api/wells/{well_id}/nearby` | Spatial search of nearby offset wellbores ($\le R\text{ km}$) | `VIEW_WELLS` |
| `GET` | `/api/wells/{well_id}/historical-proximity` | Proximity depth correlation of offset historical events | `VIEW_HISTORICAL_DATA` |
| `GET` | `/api/wells/{well_id}/trajectory` | 3D directional survey points (MD, Inc, Azi, TVD, N/S, E/W) | `VIEW_WELLS` |
| `GET` | `/api/wells/{well_id}/stratigraphy` | Formation tops and geological marker depths | `VIEW_WELLS` |

### Alert Lifecycle & Operations
| Method | Route | Description | Auth Level |
|---|---|---|---|
| `GET` | `/api/alerts` | Returns active operational alerts filtered by well/status | `VIEW_ALERTS` |
| `POST` | `/api/alerts/{alert_id}/acknowledge` | Transitions alert to `ACKNOWLEDGED` state | `ACKNOWLEDGE_ALERT` |
| `POST` | `/api/alerts/{alert_id}/investigate` | Transitions alert to `INVESTIGATING` state | `INVESTIGATE_ALERT` |
| `POST` | `/api/alerts/{alert_id}/resolve` | Resolves alert with resolution notes | `RESOLVE_ALERT` |
| `POST` | `/api/alerts/{alert_id}/notes` | Adds human engineer mitigation note to alert | `ACKNOWLEDGE_ALERT` |

### User Settings & Cloud Preferences (CRUD)
| Method | Route | Description | Auth Level |
|---|---|---|---|
| `GET` | `/api/settings` | **Read**: Fetches authenticated user's custom settings from Supabase | Authenticated |
| `PUT` | `/api/settings` | **Create / Update**: Upserts user configuration and alert triggers in Supabase | Authenticated |
| `DELETE` | `/api/settings` | **Delete / Reset**: Removes user custom record and resets to defaults | Authenticated |

### Real-Time WebSocket Gateway
| Protocol | Route | Description |
|---|---|---|
| `WSS` | `/api/ws/wells/{well_id}?token=JWT` | Full-duplex telemetry stream emitting `sensor_update`, `ml_update`, and `stream_status` events |

---

## 🚀 Quick Start & Developer Workflow

### 1. Launch Full Stack with One Command

```powershell
# Runs Sensor Stream Simulator, FastAPI Backend, and React Vite Console together
python scripts/run_app.py --well 15/9-F-14 --speed 50
```

#### Access URLs:
* **React Operational Console**: [http://localhost:5173](http://localhost:5173)
* **FastAPI Swagger OpenAPI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Detailed System Health**: [http://localhost:8000/health/detailed](http://localhost:8000/health/detailed)
* **WebSocket Stream Gateway**: `ws://localhost:8000/api/ws/wells/15/9-F-14`

---

### 2. Running Services Individually

#### React Frontend Console (`http://localhost:5173`)
```powershell
cd frontend
npm install
npm run dev
```

#### Production Bundle Build
```powershell
cd frontend
npm run build
```

#### FastAPI Orchestration Backend (`http://localhost:8000`)
```powershell
$env:PYTHONPATH="src"
python -m uvicorn ertmac.api.server:app --host 0.0.0.0 --port 8000 --reload --reload-dir src
```

#### Sensor Stream Simulator (`ws://localhost:8765`)
```powershell
$env:PYTHONPATH="src"
python scripts/run_sensor_stream.py --well 15/9-F-14 --speed 50
```

---

## ⚙️ Environment Variable Configuration

### Backend Configuration (`.env`)

```ini
# Server Settings
PORT=8000
HOST=0.0.0.0
AUTH_REQUIRED=true

# Supabase Cloud Project Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
DATABASE_URL=postgresql://postgres.your-ref:your-password@aws-0-region.pooler.supabase.com:5432/postgres

# Resend Email Notification Gateway
RESEND_API_KEY=re_your_resend_api_key
RESEND_FROM_EMAIL=alerts@ertmac-nwis.org
ALERT_NOTIFICATION_EMAIL=operator@company.com

# Frontend Local Base URLs
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### Frontend Configuration (`frontend/.env`)

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🧪 Automated Testing & Security Invariants

Run the automated `pytest` test suite to verify causal buffer invariants, RBAC security gates, and API workflows:

```powershell
$env:PYTHONPATH="src"
python -m pytest
```

---

## 🌐 Production Deployment Guide

For Linux VPS (Ubuntu 22.04/24.04 LTS) deployments, Caddy handles HTTPS/WSS auto-SSL and reverse proxying:

```mermaid
flowchart LR
    Client["Web Client / Browser"] -->|"HTTPS / WSS"| Proxy["Caddy Reverse Proxy with Auto-SSL"]
    Proxy -->|"Static Bundle /index.html"| Dist["frontend/dist"]
    Proxy -->|"REST API /api/*"| Backend["FastAPI Port 8000"]
    Proxy -->|"WebSocket /api/ws/*"| Backend
    Backend -->|"Stream Port 8765"| Simulator["Sensor Stream Replayer"]
    Backend -->|"Postgres / HTTPS"| Supabase["Supabase Cloud Postgres"]
    Backend -->|"REST HTTPS"| Resend["Resend Email API"]
```

### Caddy Configuration (`/etc/caddy/Caddyfile`)
```caddy
yourdomain.com {
    root * /opt/ertmac/frontend/dist
    file_server
    try_files {path} /index.html

    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle /health* {
        reverse_proxy localhost:8000
    }
}
```

---

## 🔬 Scientific Integrity & Anti-Hallucination Guarantees

1. **Mandatory Scientific Banner**: Displayed prominently across all interfaces: `REAL VOLVE DATA — HISTORICAL REPLAY`.
2. **Zero Synthetic Sensor Fabrication**: All telemetry channels ($MD, TVD, WOB, ROP, Torque, RPM, Flow Rate, Mud Weight$) stream real sensor measurements from the Equinor Volve field repository.
3. **Zero Prediction Fabrication**: When ML pipeline preconditions are unmet, `risk_score` is strictly returned as `null` with explicit gating reasons.
4. **Causal Stream Isolation**: Telemetry history and feature construction are strictly bounded by $\text{MD} \le current\_md$.
