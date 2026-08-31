# OIL/eRTMAC Data Ingestion Audit

## Dataset Inspected
- Expected Events: `data/raw/oil_ertmac_events.parquet`
- Expected Sensors: `data/raw/oil_ertmac_sensors.parquet`

## Current ML Status
**BLOCKED**

### Reason
OIL/eRTMAC datasets not found in data/raw/. (Missing oil_ertmac_events.parquet or oil_ertmac_sensors.parquet)

### Readiness Requirements
To pass the scientific gate, the dataset must satisfy:
1. `FORMATION_MUD_LOSS` onset MD is available.
2. Contains `>=5` verified positive wells.
3. Telemetry strictly overlaps positive event wells.
4. Telemetry history reaches at least `onset_md - 25m` for `>=5` positive wells.
5. No impossible/non-monotonic depth joins.
6. Clean timestamps and MD synchronization.

*(No ML model has been trained. The Volve dataset was explicitly NOT substituted.)*
