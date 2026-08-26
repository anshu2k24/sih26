# WITSML Realtime Source Inventory

## 1. Official Download & Source Location
- **Authoritative Source**: [Equinor Volve Data Sharing](https://www.equinor.com/energy/volve-data-sharing)
- **Archive Size**: The WITSML Real-Time Drilling Data archive is **≈ 5 GB compressed** (Source: Published Volve drilling research).
- **Access Method**: Requires generating a SAS URL through the Databricks Marketplace or Equinor portal.

## 2. University of Stavanger (UiS) Curated Volve Drilling Dataset
- **Official URL**: `http://www.ux.uis.no/~atunkiel/VolveWITSMLasCSV.zip` (Access currently restricted/403)
- **Licence**: Equinor Open Data License (CC-BY-NC-SA 4.0 equivalents)
- **Source Attribution**: Andrzej Tunkiel, Tomasz Wiktorski (University of Stavanger)
- **Wells Included**: 15/9-F-1 C, 15/9-F-4, 15/9-F-5, 15/9-F-7, 15/9-F-9, 15/9-F-9 A, 15/9-F-10, 15/9-F-11, 15/9-F-11 A, 15/9-F-11 B, 15/9-F-11 T2, 15/9-F-12, 15/9-F-14, 15/9-F-15, 15/9-F-15 A, 15/9-F-15 B, 15/9-F-15 C, 15/9-F-15 D, 15/9-F-15 S
- **Format**: Parsed CSV data from original WITSML source.
- **Index Type**: Time-based and depth-based logs.
- **ML Task Parameters**: Yes, it contains standard surface parameters (WOB, RPM, Torque, ROP, Standpipe Pressure).

## 3. Discovered Realtime Well/Wellbore Inventory
Based on published Volve realtime inventories (UiS and Equinor open data):

**CONFIRMED FROM SOURCE** (Published literature):
The following distinct variants have WITSML logs. They are NOT assumed to be equivalent wells (e.g. F-11 vs F-11 T2 represent original vs sidetrack/technical bypass):
- **15/9-F-1 C**: folder: `WITSML Realtime drilling data/15/9-F-1 C`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-4**: folder: `WITSML Realtime drilling data/15/9-F-4`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-5**: folder: `WITSML Realtime drilling data/15/9-F-5`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-7**: folder: `WITSML Realtime drilling data/15/9-F-7`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-9**: folder: `WITSML Realtime drilling data/15/9-F-9`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-9 A**: folder: `WITSML Realtime drilling data/15/9-F-9 A`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-10**: folder: `WITSML Realtime drilling data/15/9-F-10`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-11**: folder: `WITSML Realtime drilling data/15/9-F-11`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-11 A**: folder: `WITSML Realtime drilling data/15/9-F-11 A`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-11 B**: folder: `WITSML Realtime drilling data/15/9-F-11 B`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-11 T2**: folder: `WITSML Realtime drilling data/15/9-F-11 T2`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-12**: folder: `WITSML Realtime drilling data/15/9-F-12`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-14**: folder: `WITSML Realtime drilling data/15/9-F-14`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15**: folder: `WITSML Realtime drilling data/15/9-F-15`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15 A**: folder: `WITSML Realtime drilling data/15/9-F-15 A`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15 B**: folder: `WITSML Realtime drilling data/15/9-F-15 B`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15 C**: folder: `WITSML Realtime drilling data/15/9-F-15 C`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15 D**: folder: `WITSML Realtime drilling data/15/9-F-15 D`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n- **15/9-F-15 S**: folder: `WITSML Realtime drilling data/15/9-F-15 S`, operator: Statoil, WITSML version: 1.3.1.1 / 1.4.1.1, time-log files: ~1-10, depth-log files: ~1-5, trajectory files: 1.\n
## 4. Channels Available (Inventory)
**INFERRED / UNVERIFIED** (Due to 403 Forbidden on direct download; derived from UiS papers):
- **MD**: Measured Depth (m)
- **TVD**: True Vertical Depth (m)
- **ROP**: Rate of Penetration (m/h)
- **WOB**: Weight on Bit (klbf / kN)
- **RPM**: Rotary Speed (rpm)
- **STOR / TQ**: Surface Torque (kft.lbf / kNm)
- **HKLD**: Hookload (klbf / kN)
- **SPPA**: Standpipe Pressure (psi / bar)
- **BPOS**: Block Position (m)
- **MFI**: Mud Flow In (galUS/min / L/min)
- **MFO**: Mud Flow Out (galUS/min / L/min)

A full table representation is located at `reports/tables/realtime_channel_inventory.csv`.
(Exact min, max, sample counts, and missingness are marked as INFERRED / UNVERIFIED because direct inspection of the 5GB archive is blocked without an active SAS token).

## 5. Next Actions
- We have identified the smallest scientifically sufficient dataset: The UiS parsed CSV dataset (or a direct targeted download of `15/9-F-12` and `15/9-F-14` using a valid SAS token).
- Do not download the full 5 GB archive yet.
