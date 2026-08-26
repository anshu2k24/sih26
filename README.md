# eRTMAC-NWIS

**Nearby Wells Intelligence System** — SIH 2026 Problem Statement PS26121

## Overview

A production-grade proof-of-concept for drilling risk prediction, offset-well intelligence,
and evidence-backed recommendations using historical daily drilling report data.

**Current validation dataset**: Equinor Volve Open Dataset (NOT OIL India data).

---

## 🚨 CURRENT STATUS 🚨

**Historical NWIS Engine:** ✅ **FUNCTIONAL**
The application can query real historical DDR events by depth, extracting verified mitigations and evidence with exact provenance.

**Predictive ML Pipeline:** 🛑 **BLOCKED BY DATA**
The ML architecture (Feature Engineering, LOWO validation, Baseline Models) is 100% complete and tested. However, model training is hard-blocked because the public Equinor Volve dataset lacks sufficient independent wells with high-frequency sensor telemetry to support a scientifically valid test.

**To resume ML:**
We require real `oil_ertmac_events.parquet` and `oil_ertmac_sensors.parquet` data satisfying the minimum 5-well constraint. See `reports/next_data_requirements.md` for details.

---

## Setup

### Requirements

- Python 3.12+
- Ubuntu / Linux
- RTX 3050 6 GB VRAM, 16 GB RAM (for later ML stages)

### Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the package in editable mode
pip install -e ".[dev]"
```

---

## Directory Structure

```
.
├── data/
│   ├── raw/               # Raw, untouched source files — NEVER overwritten
│   ├── processed/         # Flattened/cleaned datasets (Checkpoint 2+)
│   └── features/          # ML-ready feature matrices (Checkpoint 3+)
│
├── src/ertmac/            # Main Python package
│   ├── audit/             # Checkpoint 1: raw data audit
│   ├── preprocessing/     # Checkpoint 2: flattening and cleaning
│   ├── features/          # Checkpoint 3: feature engineering
│   ├── models/            # Checkpoint 5-6: model definitions
│   ├── evaluation/        # Checkpoint 6-7: metrics and evaluation
│   └── utils/             # Shared utilities (logging, paths, config)
│
├── scripts/               # Reproducible entry-point scripts
│   └── run_audit.py       # Checkpoint 1: full data audit
│
├── reports/
│   ├── figures/           # PNG plots
│   └── tables/            # CSV summary tables
│
├── artifacts/             # Versioned model/pipeline artifacts (later stages)
│
├── tests/                 # Pytest test suite
│
├── pyproject.toml
├── CONTEXT.md
└── README.md
```

---

## Component Execution Status

- **FUNCTIONAL**: Actually executable against real available data.
- **BLOCKED**: Intentionally refuses execution because required real data is absent.

## Checkpoints

| Phase | Description | Status |
|---|---|---|
| 1 | Raw data audit | COMPLETE |
| 2 | DDR/event extraction + semantic labeling | COMPLETE |
| 3 | Event episode validation/leakage audit | COMPLETE |
| 4 | Sensor/event causal integration audit | COMPLETE |
| 5 | ML dataset/readiness investigation | COMPLETE |
| 6 | LOWO/model pipeline architecture | COMPLETE (Execution BLOCKED) |
| 7 | NWIS historical intelligence engine | FUNCTIONAL |
| 8 | Minimal frontend/API | FUNCTIONAL |
| 9 | Predictive ML training | BLOCKED (Awaiting OIL/eRTMAC data) |

---

## Running the Audit (Checkpoint 1)

```bash
source .venv/bin/activate
python scripts/run_audit.py
```

Outputs:
- `reports/audit_schema.md`
- `reports/audit_data_quality.md`
- `reports/audit_well_coverage.md`
- `reports/audit_report.html`
- `reports/figures/` — all PNG visualizations

---

## Data Rules

- **Never** modify `data/raw/` files
- **Never** silently drop rows/columns
- **Never** treat `-999.99` as a real measurement — convert to `NaN` first
- Document every transformation
- Split by well/wellbore — never random row splits for ML
