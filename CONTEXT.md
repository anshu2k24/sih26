# SIH 2026 PS26121 — eRTMAC-NWIS
## Data Science / ML Project Context

## Objective

Build a production-grade PoC for SIH 2026 Problem Statement PS26121:
"eRTMAC-NWIS (Nearby Wells Intelligence System)"

The system should eventually support:
- historical offset-well intelligence
- drilling-risk prediction
- nearby-well comparison
- drilling-event retrieval
- document/RAG search
- evidence-backed recommendations
- map-based visualization
- future ingestion of OIL/eRTMAC data

IMPORTANT:
The current prototype dataset is NOT OIL India data.

Current validation dataset:
Equinor Volve Open Dataset / derived Daily Drilling Report dataset.

Original authoritative source:
Equinor Volve Data Sharing.

Current derived dataset:
bengsoon/volve_daily_drilling_report

Local file:
volve_ddr.parquet

The Bengsoon dataset is a derived/reformatted representation of Volve data.
Do not treat Bengsoon as the original data owner.

---

# CURRENT DATASET

File:
volve_ddr.parquet

Observed size:
1,759 rows
17 top-level columns

Observed columns:

1. docName
2. nameWell
3. nameWellbore
4. name
5. dTimStart
6. dTimEnd
7. versionKind
8. createDate
9. wellAlias
10. wellboreAlias
11. wellboreInfo
12. statusInfo
13. fluid
14. porePressure
15. surveyStation
16. activity
17. lithShowInfo

---

# TOP-LEVEL FIELD MEANINGS

docName
- Daily report/document identifier.

nameWell
- WITSML well identifier/name.

nameWellbore
- WITSML wellbore identifier/name.

name
- Report/object name field.

dTimStart
- Report start timestamp.

dTimEnd
- Report end timestamp.

versionKind
- WITSML version status.

createDate
- Record creation timestamp.

wellAlias
- Structured well aliases such as NPD code.

wellboreAlias
- Structured wellbore aliases such as NPD code and NPD number.

wellboreInfo
- Nested wellbore metadata.
- Observed fields include:
  - dTimSpud
  - dateDrillComplete
  - daysBehind
  - operator
  - rigAlias

statusInfo
- Nested daily drilling status information.
- Observed fields include:
  - avgPresBH
  - avgTempBH
  - dTim
  - dTimDiaHoleStart
  - diaHole
  - diaPilot
  - distDrill
  - elevKelly
  - fixedRig
  - forecast24Hr
  - hpht
  - md
  - mdCsgLast
  - mdKickoff
  - mdPlanned
  - mdPlugTop
  - mdStrengthForm
  - presTestType
  - reportNo
  - ropCurrent
  - strengthForm
  - sum24Hr
  - tightWell
  - tvd
  - tvdCsgLast
  - tvdStrengthForm
  - waterDepth
  - wellheadElevation

fluid
- Nested drilling-fluid / mud records.
- Observed fields include:
  - type
  - density
  - visFunnel
  - pv
  - yp
  - and other WITSML fluid properties where present.

porePressure
- Nested pore-pressure information.
- Must inspect exact nested schema before modeling.

surveyStation
- Directional survey records.
- Observed fields:
  - azi
  - dTim
  - incl
  - md
  - tvd

activity
- Nested operational activity/time-log records.
- Must inspect full schema before modeling.
- Observed/identified concepts include:
  - phase
  - state
  - proprietaryCode
  - stateDetailActivity
  - comments / engineering descriptions where present.

lithShowInfo
- Nested lithology / hydrocarbon-show information.
- Observed concepts include:
  - lithology
  - show
  - interval/depth information where available.

---

# IMPORTANT DATA QUALITY RULES

The dataset contains sentinel values.

Example:
- "-999.99"

These are NOT valid measurements and must be converted to missing values.

Never silently treat sentinel values as real measurements.

Nested arrays/structs must be normalized carefully.

Never discard raw data.

Raw source:
volve_ddr.parquet

Processed data must be stored separately.

Every transformation must be logged/documented.

---

# CURRENT DATA LIMITATION

The current Daily Drilling Report dataset is NOT by itself a complete high-frequency drilling telemetry dataset.

Do NOT assume that the following exist as clean top-level columns:

- WOB
- RPM
- torque
- hookload
- flow rate
- standpipe pressure
- mud weight
- continuous ROP
- high-frequency time-series measurements

Some related information may exist inside other Volve/WITSML datasets or report structures.

Before ML training:
1. determine exactly which features are available;
2. determine their sampling granularity;
3. determine their depth/time alignment;
4. determine event-label availability.

Do not fabricate missing data.

---

# ML PRINCIPLES

The goal is NOT to achieve artificially high metrics.

The evaluation must represent:
"Can historical wells help predict risk in an unseen/new well?"

Therefore:
- split by well/wellbore, not random rows;
- prevent temporal leakage;
- prevent depth-window leakage;
- preserve an untouched final test set;
- document every split;
- report class balance.

Accuracy alone is unacceptable.

Required metrics where applicable:
- Precision
- Recall
- F1
- PR-AUC
- ROC-AUC
- Confusion Matrix
- False Positive Rate
- per-well metrics
- calibration if probabilities are produced
- detection lead time for early-warning tasks

---

# PRODUCTION-GRADE REQUIREMENTS

No throwaway scripts.

Use:
- modular Python package structure
- configuration files
- reproducible pipelines
- type hints where practical
- logging
- validation
- tests
- deterministic seeds where possible
- artifact versioning
- clear README/documentation
- raw/processed/features/models/reports separation

Hardware:
- Ubuntu
- RTX 3050 6GB VRAM
- 16 GB RAM
- Intel i5 13th Gen HX

Prefer efficient models appropriate for this hardware.

Do not use unnecessarily large deep-learning models.

---

# MANDATORY CHECKPOINT RULE

The agent MUST stop after each major stage.

Never automatically:
data cleaning → feature engineering → training → evaluation

without user approval.

Required checkpoints:

CHECKPOINT 1: Raw data audit (COMPLETE)
CHECKPOINT 2: DDR/event extraction + semantic labeling (COMPLETE)
CHECKPOINT 3: Event episode validation/leakage audit (COMPLETE)
CHECKPOINT 4: Sensor/event causal integration audit (COMPLETE)
CHECKPOINT 5: ML dataset/readiness investigation (COMPLETE)
CHECKPOINT 6: LOWO/model pipeline architecture (COMPLETE, Execution BLOCKED)
CHECKPOINT 7: NWIS historical intelligence engine (FUNCTIONAL)
CHECKPOINT 8: Minimal frontend/API (FUNCTIONAL)
CHECKPOINT 9: Production data ingestion & normalization (COMPLETE)
CHECKPOINT 10: Predictive ML training (BLOCKED - AWAITING OIL/eRTMAC DATA)

**ML RESUME POINT:**
When real OIL/eRTMAC data arrives in `data/raw/`, run:
`python scripts/ingest_oil_ertmac.py`
If it passes the readiness gate (>= 5 independent positive well groups), ML will unblock.

---

# VISUAL ANALYSIS REQUIREMENT

Every relevant stage must generate useful visualizations.

At minimum investigate and visualize:

- missingness
- report counts by well/wellbore
- report timeline
- depth distribution
- MD vs TVD
- inclination/azimuth
- ROP distribution
- mud/fluid properties
- pore pressure
- lithology distribution
- activity distribution
- drilling activity over time/depth
- inter-well comparisons
- event distributions if events are extracted
- feature distributions before/after preprocessing
- correlations where statistically appropriate
- model confusion matrix
- PR curve
- ROC curve
- feature importance
- calibration curve where applicable
- per-well performance
- prediction timeline / early-warning visualization

All graphs must be saved as reproducible artifacts.

---

# SCIENTIFIC RULE

Before adding a feature, answer:

1. What is its source?
2. What does it physically represent?
3. What is its sampling frequency?
4. How is it aligned to depth/time?
5. Could it leak future information?
6. Why should it help prediction?

If these cannot be answered, do not use the feature.

---

# CURRENT TASK

Start with DATA AUDIT ONLY.

Do not train ML.

Do not generate synthetic data.

Do not invent missing drilling parameters.

Produce:
- schema report
- nested-schema report
- data-quality report
- missingness report
- well/wellbore report
- depth/time coverage report
- initial visualization report

Then STOP and ask for approval.