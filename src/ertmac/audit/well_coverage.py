"""
ertmac.audit.well_coverage
===========================
Compute per-well and per-wellbore coverage statistics from the raw Volve DDR parquet.

Covers:
- Report counts by well / wellbore
- Date range per wellbore
- Operator and rig information (unnested from wellboreInfo)
- Depth coverage (MD, TVD) from statusInfo
- Water depth

READ-ONLY: does not write to data/raw/.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ertmac.utils.logging_setup import get_logger

log = get_logger(__name__)


def get_wellbore_report_counts(parquet_path: Path) -> pd.DataFrame:
    """Count DDR reports per wellbore and compute date ranges.

    Returns
    -------
    DataFrame sorted descending by report_count with columns:
        nameWell, nameWellbore, report_count, earliest_report, latest_report,
        date_span_days
    """
    con = duckdb.connect()
    df = con.execute(f"""
        SELECT
            nameWell,
            nameWellbore,
            COUNT(*) AS report_count,
            MIN(CAST(dTimStart AS TIMESTAMPTZ))::DATE AS earliest_report,
            MAX(CAST(dTimEnd   AS TIMESTAMPTZ))::DATE AS latest_report,
            DATEDIFF('day',
                MIN(CAST(dTimStart AS TIMESTAMPTZ)),
                MAX(CAST(dTimEnd   AS TIMESTAMPTZ))
            ) AS date_span_days
        FROM '{parquet_path}'
        GROUP BY nameWell, nameWellbore
        ORDER BY report_count DESC
    """).df()
    con.close()
    log.info("Well/wellbore report counts: %d distinct wellbores.", len(df))
    return df


def get_operator_rig_info(parquet_path: Path) -> pd.DataFrame:
    """Extract operator and rig names by unnesting wellboreInfo.rigAlias.

    Returns
    -------
    DataFrame with columns: nameWellbore, operator, rig_name, rig_naming_system
    (deduplicated)
    """
    con = duckdb.connect()
    df = con.execute(f"""
        SELECT DISTINCT
            nameWellbore,
            w.operator AS operator,
            r.name     AS rig_name,
            r.namingSystem AS rig_naming_system
        FROM '{parquet_path}',
        UNNEST(wellboreInfo) AS t(w),
        UNNEST(w.rigAlias)   AS t2(r)
        WHERE r.name IS NOT NULL
        ORDER BY nameWellbore, rig_name
    """).df()
    con.close()
    log.info("Operator/rig info: %d unique wellbore-rig combinations.", len(df))
    return df


def get_depth_coverage(parquet_path: Path) -> pd.DataFrame:
    """Summarise MD and TVD coverage per wellbore from statusInfo.

    Excludes sentinel '-999.99' values.

    Returns
    -------
    DataFrame with columns:
        nameWellbore, valid_md_readings, max_md_m, max_tvd_m,
        water_depth_m, spud_date, drill_complete_date
    """
    con = duckdb.connect()
    df = con.execute(f"""
        WITH status AS (
            SELECT
                nameWellbore,
                UNNEST(statusInfo) AS s
            FROM '{parquet_path}'
        ),
        wellinfo AS (
            SELECT
                nameWellbore,
                UNNEST(wellboreInfo) AS w
            FROM '{parquet_path}'
        )
        SELECT
            s.nameWellbore,
            COUNT(s.s.md) FILTER (
                WHERE s.s.md IS NOT NULL AND s.s.md != '-999.99'
            ) AS valid_md_readings,
            MAX(TRY_CAST(s.s.md  AS DOUBLE)) FILTER (
                WHERE s.s.md IS NOT NULL AND s.s.md != '-999.99'
            ) AS max_md_m,
            MAX(TRY_CAST(s.s.tvd AS DOUBLE)) FILTER (
                WHERE s.s.tvd IS NOT NULL AND s.s.tvd != '-999.99'
            ) AS max_tvd_m,
            MAX(TRY_CAST(s.s.waterDepth AS DOUBLE)) AS water_depth_m
        FROM status s
        GROUP BY s.nameWellbore
        ORDER BY s.nameWellbore
    """).df()
    con.close()
    log.info("Depth coverage computed for %d wellbores.", len(df))
    return df


def get_spud_completion_dates(parquet_path: Path) -> pd.DataFrame:
    """Extract spud date and drill-complete date per wellbore from wellboreInfo.

    Returns
    -------
    DataFrame with columns: nameWellbore, spud_date, drill_complete_date, operator
    """
    con = duckdb.connect()
    df = con.execute(f"""
        SELECT DISTINCT
            nameWellbore,
            w.dTimSpud         AS spud_date,
            w.dateDrillComplete AS drill_complete_date,
            w.operator         AS operator
        FROM '{parquet_path}',
        UNNEST(wellboreInfo) AS t(w)
        WHERE w.dTimSpud IS NOT NULL
        ORDER BY nameWellbore
    """).df()
    con.close()
    log.info("Spud/completion dates: %d records.", len(df))
    return df


def run_well_coverage_assessment(parquet_path: Path) -> dict[str, pd.DataFrame]:
    """Run all well/wellbore coverage assessments.

    Returns
    -------
    dict with keys:
        - ``report_counts``: per-wellbore report counts and date ranges
        - ``operator_rig``: operator and rig info per wellbore
        - ``depth_coverage``: MD/TVD/water depth per wellbore
        - ``spud_completion``: spud and completion dates
    """
    log.info("=== WELL COVERAGE ASSESSMENT START ===")
    result = {
        "report_counts": get_wellbore_report_counts(parquet_path),
        "operator_rig": get_operator_rig_info(parquet_path),
        "depth_coverage": get_depth_coverage(parquet_path),
        "spud_completion": get_spud_completion_dates(parquet_path),
    }
    log.info("=== WELL COVERAGE ASSESSMENT COMPLETE ===")
    return result
