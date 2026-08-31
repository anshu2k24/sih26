#!/usr/bin/env python3
"""
eRTMAC-NWIS Cloud Migration — Phase 1 Seed Scripts
Seeds wellbores, historical_ddr_events, and telemetry_readings tables
from local data files into Supabase PostgreSQL.

Usage:
    python scripts/migrate_seed_data.py --all
    python scripts/migrate_seed_data.py --wellbores
    python scripts/migrate_seed_data.py --events
    python scripts/migrate_seed_data.py --telemetry
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Ensure src is on path and load environment variables
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

import pandas as pd
from ertmac.auth.supabase_client import get_supabase_admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_seed_data")

ORG_ID = "00000000-0000-0000-0000-000000000001"


def seed_wellbores():
    """Seed wellbores table from well_coordinates.json and verified events datasets."""
    db = get_supabase_admin()
    if not db:
        logger.error("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return False

    coords_path = REPO_ROOT / "data" / "processed" / "usrop" / "well_coordinates.json"
    wells = {}
    if coords_path.exists():
        with open(coords_path, "r", encoding="utf-8") as f:
            wells = json.load(f)

    # Also collect any wellbore IDs referenced in verified events
    event_csv = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    event_well_ids = set()
    if event_csv.exists():
        edf = pd.read_csv(event_csv)
        if "wellbore_id" in edf.columns:
            event_well_ids = set(edf["wellbore_id"].dropna().unique())

    logger.info("Seeding wellbores metadata into Supabase...")

    # 1. Insert known well coordinates
    for well_id, info in wells.items():
        payload = {
            "id": well_id,
            "organization_id": ORG_ID,
            "name": info.get("name", well_id),
            "slot_name": info.get("slot_name"),
            "latitude": info.get("latitude"),
            "longitude": info.get("longitude"),
            "status": info.get("status", "Historical"),
        }
        try:
            db.table("wellbores").upsert(payload, on_conflict="id").execute()
            logger.info(f"  [OK] Wellbore: {well_id}")
        except Exception as e:
            logger.error(f"  [FAIL] Wellbore {well_id}: {e}")

        # Also insert with "NO " prefix if not already present
        if not well_id.startswith("NO "):
            no_id = f"NO {well_id}"
            payload_no = dict(payload, id=no_id)
            try:
                db.table("wellbores").upsert(payload_no, on_conflict="id").execute()
            except Exception:
                pass

    # 2. Insert any remaining wellbore IDs from events
    for ew in event_well_ids:
        payload_ew = {
            "id": ew,
            "organization_id": ORG_ID,
            "name": f"Wellbore {ew}",
            "status": "Historical Offset",
            "latitude": 58.44168,
            "longitude": 1.88778,
        }
        try:
            db.table("wellbores").upsert(payload_ew, on_conflict="id").execute()
            logger.info(f"  [OK] Event Wellbore: {ew}")
        except Exception as e:
            logger.error(f"  [FAIL] Event Wellbore {ew}: {e}")

    logger.info("Wellbores seeding complete.")
    return True


def seed_historical_events():
    """Seed historical_ddr_events from verified_event_episodes_v2.csv."""
    db = get_supabase_admin()
    if not db:
        logger.error("Supabase not configured.")
        return False

    csv_path = REPO_ROOT / "reports" / "tables" / "verified_event_episodes_v2.csv"
    if not csv_path.exists():
        logger.error(f"Verified events CSV not found: {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    logger.info(f"Seeding {len(df)} historical DDR events from {csv_path.name}...")

    batch = []
    for _, row in df.iterrows():
        payload = {
            "id": str(row.get("event_episode_id", "")),
            "wellbore_id": str(row.get("wellbore_id", row.get("well_id", ""))),
            "organization_id": ORG_ID,
            "event_type": str(row.get("event_type", "Unknown")),
            "event_domain": str(row.get("event_domain", "DRILLING_OPERATIONS")),
            "onset_md": float(row["onset_md"]) if pd.notnull(row.get("onset_md")) else 0.0,
            "onset_tvd": float(row["onset_tvd"]) if pd.notnull(row.get("onset_tvd")) else None,
            "primary_evidence": str(row.get("primary_evidence", ""))[:2000] if pd.notnull(row.get("primary_evidence")) else "No evidence recorded",
            "mitigation_text": str(row.get("mitigation_text", "")) if pd.notnull(row.get("mitigation_text")) else None,
            "resolution_text": str(row.get("resolution_text", "")) if pd.notnull(row.get("resolution_text")) else None,
            "primary_source_record": str(row.get("primary_source_record", "")) if pd.notnull(row.get("primary_source_record")) else "N/A",
            "is_verified": bool(row.get("is_verified_positive", True)),
        }

        # Add onset_timestamp if available
        if pd.notnull(row.get("onset_timestamp")):
            payload["onset_timestamp"] = str(row["onset_timestamp"])

        batch.append(payload)

    # Insert in batches of 50
    batch_size = 50
    success_count = 0
    for i in range(0, len(batch), batch_size):
        chunk = batch[i : i + batch_size]
        try:
            db.table("historical_ddr_events").upsert(chunk, on_conflict="id").execute()
            success_count += len(chunk)
            logger.info(f"  ✓ Batch {i // batch_size + 1}: {len(chunk)} events")
        except Exception as e:
            logger.error(f"  ✗ Batch {i // batch_size + 1} failed: {e}")
            # Try individual inserts for failed batch
            for item in chunk:
                try:
                    db.table("historical_ddr_events").upsert(item, on_conflict="id").execute()
                    success_count += 1
                except Exception as e2:
                    logger.error(f"    ✗ Event {item['id']}: {e2}")

    logger.info(f"Historical events seeding complete: {success_count}/{len(batch)} events.")
    return True


def seed_telemetry():
    """Seed telemetry_readings from usrop_clean.parquet."""
    db = get_supabase_admin()
    if not db:
        logger.error("Supabase not configured.")
        return False

    parquet_path = REPO_ROOT / "data" / "processed" / "usrop" / "usrop_clean.parquet"
    if not parquet_path.exists():
        logger.error(f"USROP parquet not found: {parquet_path}")
        return False

    df = pd.read_parquet(parquet_path)
    logger.info(f"Seeding {len(df)} telemetry readings from {parquet_path.name} (this may take a few minutes)...")

    # Column mapping (same as VolveReplaySensorSource)
    col_map = {
        "measured depth m": "md",
        "hole depth (tvd) m": "tvd",
        "rate of penetration m/h": "rop",
        "weight on bit kkgf": "wob",
        "average rotary speed rpm": "rpm",
        "average surface torque kn.m": "torque",
        "average hookload kkgf": "hookload",
        "average standpipe pressure kpa": "spp",
        "mud flow in l/min": "flow_in",
        "mud density in g/cm3": "mud_density",
        "usrop gamma gapi": "gamma",
        "diameter mm": "diameter_mm",
    }

    # Lowercase and rename
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.rename(columns=col_map)

    # Build payloads
    batch_size = 500
    success_count = 0
    total = len(df)

    for i in range(0, total, batch_size):
        chunk_df = df.iloc[i : i + batch_size]
        batch = []

        for _, row in chunk_df.iterrows():
            payload = {
                "organization_id": ORG_ID,
                "well_id": str(row.get("well_id", "UNKNOWN")),
                "md": float(row["md"]) if pd.notnull(row.get("md")) else 0.0,
                "source": "VOLVE_USROP",
            }

            # Optional numeric columns
            for col in ["tvd", "rop", "wob", "rpm", "torque", "hookload", "spp", "flow_in", "mud_density", "gamma", "diameter_mm"]:
                if col in row and pd.notnull(row[col]):
                    val = float(row[col])
                    # Treat sentinel values as null
                    if val != -999.99 and val != -999.0:
                        payload[col] = val

            batch.append(payload)

        try:
            db.table("telemetry_readings").insert(batch).execute()
            success_count += len(batch)
            pct = (success_count / total) * 100
            if (i // batch_size) % 10 == 0:
                logger.info(f"  ✓ Progress: {success_count}/{total} ({pct:.1f}%)")
        except Exception as e:
            logger.error(f"  ✗ Batch at row {i} failed: {e}")

    logger.info(f"Telemetry seeding complete: {success_count}/{total} readings.")
    return True


def main():
    parser = argparse.ArgumentParser(description="eRTMAC-NWIS — Seed Supabase from local data files")
    parser.add_argument("--all", action="store_true", help="Seed all tables")
    parser.add_argument("--wellbores", action="store_true", help="Seed wellbores table")
    parser.add_argument("--events", action="store_true", help="Seed historical_ddr_events table")
    parser.add_argument("--telemetry", action="store_true", help="Seed telemetry_readings table")
    args = parser.parse_args()

    if not any([args.all, args.wellbores, args.events, args.telemetry]):
        parser.print_help()
        print("\nPlease specify at least one target: --all, --wellbores, --events, --telemetry")
        sys.exit(1)

    results = {}

    if args.all or args.wellbores:
        results["wellbores"] = seed_wellbores()

    if args.all or args.events:
        results["events"] = seed_historical_events()

    if args.all or args.telemetry:
        results["telemetry"] = seed_telemetry()

    print("\n=== Seed Results ===")
    for name, ok in results.items():
        status = "[SUCCESS]" if ok else "[FAILED]"
        print(f"  {status}: {name}")


if __name__ == "__main__":
    main()
