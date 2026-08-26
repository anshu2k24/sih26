# OIL/eRTMAC Data Requirements (Hand-off Document)

This document defines the strict data requirements for the `oil_ertmac_events.parquet` and `oil_ertmac_sensors.parquet` files required to unblock the Machine Learning pipeline.

## 1. Required DDR (Event) Fields
The `oil_ertmac_events.parquet` (or CSV) file must contain:
- `well_id` (String): Unique identifier for the wellbore.
- `timestamp` (Datetime/String): Exact time of the recorded event.
- `md` (Float): Measured depth at the time of the event (Onset MD).
- `event_type` (String): Standardized operational category (e.g., "FORMATION_MUD_LOSS", "Tight Hole").
- `primary_evidence` (String): Text description from the drilling report confirming the event.
- `mitigation` (String): Text describing the actions taken.

## 2. Required High-Frequency Telemetry (Sensor) Fields
The `oil_ertmac_sensors.parquet` (or CSV) file must contain continuous, time-series measurements at regular depth/time intervals:
- `well_id` (String)
- `timestamp` (Datetime/String)
- `md` (Float)
- `rop` (Float) - Rate of Penetration
- `wob` (Float) - Weight on Bit
- `rpm` (Float) - Rotary Speed
- `torque` (Float) - Surface Torque
- `hookload` (Float) - Hook Load
- `spp` (Float) - Standpipe Pressure
- `flow_in` (Float) - Mud Flow In
- `mud_density` (Float) - Mud Weight

## 3. Synchronization & Alignment
- **Temporal Alignment:** The sensor `timestamp` and `md` must correctly align with the event `timestamp` and `md`.
- **Causal Horizon:** Sensor data must exist continuously from at least 100m *before* the event onset. Sensor gaps larger than 5m within the target window are unacceptable.

## 4. Minimum Positive Well Groups
The dataset must contain **at least 5 independent well groups** that contain positive occurrences of the target event (e.g., Mud Loss) with corresponding sensor overlap. Sidetracks and parent wells from the same structure (e.g., Well 1 and Well 1-ST) count as a single independent group.

## 5. File Formats
- Formats accepted: `.parquet` (Preferred) or `.csv`.
- Files must be placed directly into the `data/raw/` directory.
