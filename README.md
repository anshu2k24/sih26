# eRTMAC-NWIS

**Nearby Wells Intelligence System & Causal Sensor Streaming Architecture**  
*SIH 2026 Problem Statement PS121*

> **Scientific Data Label**: `REAL VOLVE DATA — HISTORICAL REPLAY`  
> **Dataset**: Equinor Volve Real USROP Telemetry Dataset (`data/processed/usrop/usrop_clean.parquet`)  
> **Test Suite**: **115 / 115 pytest tests passing**

---

## 🏛️ System Architecture Flowchart

```mermaid
flowchart TD
    subgraph Data Layer
        A[REAL Volve Parquet Data<br>data/processed/usrop/usrop_clean.parquet]
        B[Equinor Volve Semantic DDR Events<br>reports/tables/verified_event_episodes_v2.csv]
    end

    subgraph Streaming & Replay Engine
        C[VolveReplaySensorSource]
        D[SensorRecord Canonical Schema]
        E[SensorStreamSimulator<br>ws://localhost:8765]
        F[SensorStreamClient]
        G[CausalStreamBuffer<br>Max 200m Memory Span]
    end

    subgraph Analytics & Intelligence
        H[StreamInferenceAdapter]
        I[construct_causal_features<br>395 Rolling Features]
        J[IngestionValidator<br>ML Readiness Gate]
        K[NWISHistoricalAPI<br>Offset DDR Event Engine]
    end

    subgraph FastAPI Orchestration Backend
        L[FastAPI Server - http://localhost:8000]
        M[REST APIs<br>/health, /api/wells, /api/wells/{id}/state, etc.]
        N[Application WebSocket Gateway<br>/api/ws/wells/{well_id}]
    end

    subgraph React Operational Console
        O[React + TypeScript + Vite Console - http://localhost:5173]
        P[Current Drilling Position & Stream State]
        Q[8 Real-Time Telemetry Cards]
        R[8 Real-Time Recharts Line Charts]
        S[Predictive Risk Center - ML_NOT_READY Gate Block]
        T[Offset DDR Intelligence & Event Timeline]
        U[System Infrastructure Health Panel]
    end

    A --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    I --> J
    B --> K
    G --> L
    J --> L
    K --> L
    L --> M
    L --> N
    M --> O
    N --> O
    O --> P
    O --> Q
    O --> R
    O --> S
    O --> T
    O --> U
```

---

## 🚀 Running Commands

### 1. Launch Complete Application Stack (Single Command)

To launch the Sensor Stream Simulator, FastAPI Orchestration Backend, and React Operational Console together:

```bash
python scripts/run_app.py --well 15/9-F-15 --speed 50
```

#### Access Endpoints:
- **React Operational Console**: [http://localhost:5173](http://localhost:5173)
- **FastAPI OpenAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Sensor WebSocket Stream**: `ws://localhost:8765`
- **Application WebSocket Gateway**: `ws://localhost:8000/api/ws/wells/15/9-F-15`

---

### 2. Launch Services Individually

#### React Frontend Console (`http://localhost:5173`)
```bash
cd frontend
npm install
npm run dev
```

#### Production React Build
```bash
cd frontend
npm run build
```

#### FastAPI Orchestration Backend (`http://localhost:8000`)
```bash
python -m uvicorn ertmac.api.server:app --host 0.0.0.0 --port 8000
```

#### Sensor Stream Replay Simulator (`ws://localhost:8765`)
```bash
python scripts/run_sensor_stream.py --well 15/9-F-15 --speed 50
```

---

### 3. Run Automated Pytest Suite

```bash
python -m pytest
```

Output:
```text
======================= 115 passed, 1 warning in 50.63s =======================
```

---

## 🛠️ Technology Stack

| Layer | Technology | Function |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons | Operational drilling intelligence console, dynamic real-time line charts, event timeline. |
| **Backend** | Python 3.10+, FastAPI, Starlette, Uvicorn, Pydantic | Orchestration backend, REST routing, OpenAPI documentation, and WebSocket gateway. |
| **Streaming Replay** | Python Asyncio, `websockets`, Pandas, PyArrow | Causal historical replay from real Volve Parquet sensor dataset. |
| **Feature Engineering** | `construct_causal_features()` | 395 causal rolling window features (5m, 10m, 25m, 50m means/stds). |
| **ML Gate Enforcement** | `IngestionValidator.check_readiness()` | Enforces Leave-One-Well-Out $\ge 5$ group gate (`ML_NOT_READY`, zero risk score fabrication). |
| **NWIS Intelligence** | `NWISHistoricalAPI` | Deterministic geospatial search across Equinor Volve verified DDR semantic events. |

---

## 📡 REST & WebSocket API Contracts

### REST Endpoints
- `GET /health`: Health check status and dataset label.
- `GET /api/wells`: Returns available Volve wells (`15/9-F-15`, `15/9-F-14`, etc.).
- `GET /api/wells/{well_id}/state`: Current stream state, bit depth (MD/TVD), timestamp, and ML gate status.
- `GET /api/wells/{well_id}/sensors/latest`: Latest emitted sensor measurement.
- `GET /api/wells/{well_id}/sensors/history?cutoff_md={cutoff_md}`: Emitted causal history $\le cutoff\_md$ (zero future data leakage).
- `GET /api/wells/{well_id}/events`: Offset DDR events around current depth position.
- `GET /api/wells/{well_id}/risk`: ML risk result (`ML_NOT_READY`, zero risk score fabrication).

### Application WebSocket Gateway (`/api/ws/wells/{well_id}`)
- `sensor_update`: Real-time telemetry frames (`md`, `rop`, `wob`, `rpm`, `torque`, `hookload`, `spp`, `flow_in`, `mud_density`).
- `ml_update`: Real-time ML readiness gate state (`status`, `is_blocked`, `gate_reason`, `features_constructed`).
- `stream_status`: Replay stream state (`status`, `current_md`, `samples_received`).

---

## 📁 Repository Structure

```text
.
├── data/
│   └── processed/usrop/usrop_clean.parquet   <-- REAL Volve USROP sensor dataset
├── frontend/                                  <-- React + TypeScript + Vite Console
│   ├── src/
│   │   ├── components/                        <-- Operational Telemetry & Chart Components
│   │   ├── hooks/useSensorStream.ts           <-- WebSocket Listener & Stream State Hook
│   │   ├── services/api.ts                    <-- REST API Client
│   │   ├── pages/Dashboard.tsx                <-- Main Operational Console Page
│   │   └── styles/index.css                   <-- Tailwind CSS Styling
│   ├── vite.config.ts
│   └── package.json
├── src/ertmac/
│   ├── api/                                   <-- FastAPI Server, State, and Schemas
│   ├── ml/                                    <-- StreamInferenceAdapter, Features, Ingestion
│   ├── streaming/                             <-- VolveReplaySensorSource, CausalBuffer, Client
│   └── nwis/                                  <-- Nearby Wells Intelligence System
├── scripts/
│   ├── nwis_api.py                            <-- NWISHistoricalAPI
│   ├── run_sensor_stream.py                   <-- Stream Simulator CLI
│   └── run_app.py                             <-- Single-Command Stack Launcher
├── reports/
│   └── tables/verified_event_episodes_v2.csv  <-- Equinor Volve verified DDR semantic events
├── tests/                                     <-- Pytest Test Suite (115 passing tests)
├── pyproject.toml
└── README.md
```

---

## 🔬 Data Integrity & Scientific Rules

1. **Mandatory Classification Banner**: Prominently displays `REAL VOLVE DATA — HISTORICAL REPLAY`.
2. **Zero Data Fabrication**: Streams exclusively from real Volve Parquet telemetry rows without synthetic interpolation.
3. **Zero Prediction Fabrication**: When the ML readiness gate blocks inference (`ML_NOT_READY`), returns `risk_score = null` and displays `Prediction: UNAVAILABLE` with the exact gate reason.
4. **Causal Isolation**: Strictly prevents future data leakage; telemetry history is restricted to already-emitted samples $\le current\_md$.
