#!/usr/bin/env python3
"""
scripts/run_audit.py
====================
Checkpoint 1 — Raw Data Audit Entry Point

Run:
    source .venv/bin/activate
    python scripts/run_audit.py

Outputs:
    reports/audit_schema.md
    reports/audit_data_quality.md
    reports/audit_well_coverage.md
    reports/audit_report.html
    reports/figures/*.png
    reports/tables/*.csv
    reports/audit.log

This script is READ-ONLY with respect to data/raw/.
It does NOT flatten, clean, or modify the source dataset.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from ertmac.utils.paths import RAW_PARQUET, REPORTS_DIR, ensure_output_dirs
from ertmac.utils.logging_setup import get_logger
from ertmac.audit.schema_inspector import run_schema_inspection
from ertmac.audit.data_quality import run_data_quality_assessment
from ertmac.audit.well_coverage import run_well_coverage_assessment
from ertmac.audit.visualizations import run_all_visualizations
from ertmac.audit.report_writer import write_all_reports

log = get_logger(
    "ertmac.audit",
    log_file=REPORTS_DIR / "audit.log",
)


def derive_findings(schema_result: dict, dq: dict, wc: dict) -> list[str]:
    """Derive human-readable findings from audit results for the HTML report."""
    findings = []

    # Sentinels
    si = dq["statusinfo_sentinels"]
    high_sentinel = si[si["sentinel_pct"] > 50]
    if not high_sentinel.empty:
        cols = ", ".join(f"<code>{c}</code>" for c in high_sentinel["field"])
        findings.append(
            f"<span class='warn'>⚠️ HIGH SENTINEL RATE:</span> {cols} have >50% "
            f"sentinel (-999.99) values in <code>statusInfo</code>. "
            f"These fields carry little information for most reports."
        )

    # Nested coverage
    nc = dq["nested_coverage"]
    low_coverage = nc[nc["nonempty_pct"] < 30]
    for _, row in low_coverage.iterrows():
        findings.append(
            f"<span class='warn'>⚠️ LOW COVERAGE:</span> <code>{row['column']}</code> "
            f"is populated in only {row['nonempty_pct']:.1f}% of reports "
            f"({int(row['nonempty_rows']):,} of {int(row['total_rows']):,} rows)."
        )

    # Activity dominance
    act_row = nc[nc["column"] == "activity"]
    if not act_row.empty:
        findings.append(
            f"<span class='ok'>✅ ACTIVITY:</span> The <code>activity</code> column is the "
            f"richest nested sub-table with "
            f"{int(act_row['total_nested_records'].values[0]):,} records — "
            f"primary source for operational event labels."
        )

    # Date coverage
    rc = wc["report_counts"]
    findings.append(
        f"Data spans <strong>{str(rc['earliest_report'].min())}</strong> to "
        f"<strong>{str(rc['latest_report'].max())}</strong> across "
        f"<strong>{len(rc)} wellbores</strong>. "
        f"Wellbore <code>NO 15/9-F-12</code> has the most reports (165)."
    )

    # Numeric fields stored as VARCHAR
    findings.append(
        "<span class='warn'>⚠️ TYPE ISSUE:</span> All numeric fields inside "
        "<code>statusInfo</code>, <code>surveyStation</code>, <code>fluid</code>, "
        "and <code>porePressure</code> are stored as <code>VARCHAR</code> strings "
        "in the WITSML-derived parquet. They require sentinel removal and explicit "
        "<code>CAST</code> to float before any numerical analysis."
    )

    # No high-frequency data
    findings.append(
        "<span class='warn'>⚠️ DATA LIMITATION:</span> This DDR dataset contains "
        "<strong>one record per 24-hour period</strong> per wellbore. "
        "High-frequency drilling parameters (WOB, RPM, torque, hookload, standpipe pressure) "
        "are <strong>NOT present</strong> as clean columns. Do not assume their availability."
    )

    # ML split note
    findings.append(
        "🔬 <strong>ML NOTE:</strong> Splits must be by wellbore (not random rows) "
        "to prevent leakage. 26 wellbores available; recommend holding out ≥2 "
        "complete wellbores as final test set."
    )

    return findings


def main() -> None:
    t0 = time.time()
    log.info("=" * 60)
    log.info("eRTMAC-NWIS — CHECKPOINT 1: RAW DATA AUDIT")
    log.info("=" * 60)

    # Validate raw file
    if not RAW_PARQUET.exists():
        log.error("Raw parquet not found at: %s", RAW_PARQUET)
        log.error("Copy volve_ddr.parquet to data/raw/ first.")
        sys.exit(1)

    ensure_output_dirs()
    log.info("Raw parquet: %s (%.2f MB)", RAW_PARQUET, RAW_PARQUET.stat().st_size / 1e6)

    # --- Stage 1: Schema inspection ---
    log.info("[1/4] Running schema inspection...")
    schema_result = run_schema_inspection(RAW_PARQUET)

    # --- Stage 2: Data quality ---
    log.info("[2/4] Running data quality assessment...")
    dq = run_data_quality_assessment(RAW_PARQUET)

    # --- Stage 3: Well coverage ---
    log.info("[3/4] Running well coverage assessment...")
    wc = run_well_coverage_assessment(RAW_PARQUET)

    # --- Stage 4: Visualizations ---
    log.info("[4/4] Generating visualizations...")
    figure_paths = run_all_visualizations(
        parquet_path=RAW_PARQUET,
        report_counts_df=wc["report_counts"],
        nested_coverage_df=dq["nested_coverage"],
        sentinels_df=dq["statusinfo_sentinels"],
        depth_df=wc["depth_coverage"],
        top_level_df=dq["top_level"],
    )

    # --- Reports ---
    findings = derive_findings(schema_result, dq, wc)
    written = write_all_reports(schema_result, dq, wc, figure_paths, findings)

    elapsed = time.time() - t0
    log.info("=" * 60)
    log.info("CHECKPOINT 1 COMPLETE in %.1f seconds.", elapsed)
    log.info("Reports written:")
    for p in written:
        log.info("  %s", p)
    log.info("Figures saved: %d PNG files in %s", len(figure_paths), REPORTS_DIR / "figures")
    log.info("=" * 60)
    log.info("STOP — awaiting user approval before Checkpoint 2.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
