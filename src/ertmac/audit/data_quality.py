"""
ertmac.audit.data_quality
==========================
Assess data quality of the raw Volve DDR parquet file.

Covers:
- Top-level field null / sentinel rates
- Nested array coverage per parent row
- Type consistency within nested structs
- Date / timestamp parseability

This module is READ-ONLY with respect to the raw dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from ertmac.utils.logging_setup import get_logger
from ertmac.audit.schema_inspector import NESTED_ARRAY_COLS, SENTINEL_VALUES

log = get_logger(__name__)

SENTINEL_SQL = "'-999.99'"  # primary sentinel to detect in string fields


def assess_top_level_quality(parquet_path: Path) -> pd.DataFrame:
    """Assess null and sentinel rates for all top-level scalar/string columns.

    Returns
    -------
    DataFrame with columns:
        column, dtype, total_rows, null_count, null_pct,
        sentinel_count, sentinel_pct, unique_count
    """
    con = duckdb.connect()
    total = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()[0]

    describe = con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").df()
    scalar_cols = [
        r["column_name"]
        for _, r in describe.iterrows()
        if not r["column_type"].startswith("STRUCT") and "[]" not in r["column_type"]
    ]

    rows = []
    for col in scalar_cols:
        col_type = describe.loc[describe["column_name"] == col, "column_type"].values[0]

        null_count = con.execute(
            f"SELECT COUNT(*) FROM '{parquet_path}' WHERE {col} IS NULL"
        ).fetchone()[0]

        # Sentinel check only meaningful for VARCHAR columns
        sentinel_count = 0
        if "VARCHAR" in col_type.upper():
            sentinel_count = con.execute(
                f"SELECT COUNT(*) FROM '{parquet_path}' WHERE {col} = {SENTINEL_SQL}"
            ).fetchone()[0]

        try:
            unique_count = con.execute(
                f"SELECT COUNT(DISTINCT {col}) FROM '{parquet_path}'"
            ).fetchone()[0]
        except Exception:
            unique_count = None

        rows.append(
            {
                "column": col,
                "dtype": col_type,
                "total_rows": total,
                "null_count": null_count,
                "null_pct": round(null_count / total * 100, 2),
                "sentinel_count": sentinel_count,
                "sentinel_pct": round(sentinel_count / total * 100, 2),
                "unique_count": unique_count,
            }
        )

    con.close()
    df = pd.DataFrame(rows)
    log.info("Top-level quality assessment: %d columns assessed over %d rows.", len(df), total)
    return df


def assess_nested_coverage(parquet_path: Path) -> pd.DataFrame:
    """Assess how many parent rows have populated vs empty nested arrays.

    Returns
    -------
    DataFrame with columns:
        column, total_rows, nonempty_rows, empty_rows,
        nonempty_pct, total_nested_records, avg_records_per_row
    """
    con = duckdb.connect()
    total = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()[0]

    rows = []
    for col in NESTED_ARRAY_COLS:
        nonempty = con.execute(
            f"SELECT COUNT(*) FROM '{parquet_path}' WHERE len({col}) > 0"
        ).fetchone()[0]
        total_nested = con.execute(
            f"SELECT COALESCE(SUM(len({col})), 0) FROM '{parquet_path}'"
        ).fetchone()[0]

        rows.append(
            {
                "column": col,
                "total_rows": total,
                "nonempty_rows": nonempty,
                "empty_rows": total - nonempty,
                "nonempty_pct": round(nonempty / total * 100, 2),
                "total_nested_records": int(total_nested),
                "avg_records_per_nonempty_row": round(
                    total_nested / nonempty if nonempty > 0 else 0, 2
                ),
            }
        )

    con.close()
    df = pd.DataFrame(rows)
    log.info("Nested coverage assessed for %d nested columns.", len(df))
    return df


def assess_statusinfo_sentinels(parquet_path: Path) -> pd.DataFrame:
    """Inspect sentinel (-999.99) prevalence in key statusInfo numeric-as-string fields.

    Returns
    -------
    DataFrame with columns: field, total_records, sentinel_count, sentinel_pct,
    null_count, null_pct, valid_count, valid_pct
    """
    numeric_fields = [
        "md", "tvd", "distDrill", "ropCurrent", "waterDepth",
        "mdPlanned", "mdKickoff", "mdCsgLast", "mdPlugTop",
        "elevKelly", "wellheadElevation",
    ]

    con = duckdb.connect()
    total_nested = con.execute(
        f"SELECT SUM(len(statusInfo)) FROM '{parquet_path}'"
    ).fetchone()[0] or 0

    rows = []
    for field in numeric_fields:
        try:
            result = con.execute(f"""
                WITH unnested AS (
                    SELECT UNNEST(statusInfo) AS s FROM '{parquet_path}'
                )
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE s.{field} = '-999.99') AS sentinel_cnt,
                    COUNT(*) FILTER (WHERE s.{field} IS NULL) AS null_cnt
                FROM unnested
            """).fetchone()
            total_r, sentinel_cnt, null_cnt = result
            valid = total_r - sentinel_cnt - null_cnt
            rows.append(
                {
                    "field": f"statusInfo.{field}",
                    "total_records": total_r,
                    "sentinel_count": sentinel_cnt,
                    "sentinel_pct": round(sentinel_cnt / total_r * 100, 2) if total_r else 0,
                    "null_count": null_cnt,
                    "null_pct": round(null_cnt / total_r * 100, 2) if total_r else 0,
                    "valid_count": valid,
                    "valid_pct": round(valid / total_r * 100, 2) if total_r else 0,
                }
            )
        except Exception as exc:
            log.warning("Could not assess statusInfo.%s: %s", field, exc)

    con.close()
    df = pd.DataFrame(rows)
    log.info("StatusInfo sentinel assessment: %d fields checked.", len(df))
    return df


def assess_date_parseability(parquet_path: Path) -> pd.DataFrame:
    """Check whether dTimStart and dTimEnd parse successfully as timestamps.

    Returns
    -------
    DataFrame with columns: column, total, parse_ok, parse_fail, fail_pct
    """
    con = duckdb.connect()
    total = con.execute(f"SELECT COUNT(*) FROM '{parquet_path}'").fetchone()[0]

    rows = []
    for col in ("dTimStart", "dTimEnd", "createDate"):
        try:
            fail = con.execute(f"""
                SELECT COUNT(*) FROM '{parquet_path}'
                WHERE TRY_CAST({col} AS TIMESTAMPTZ) IS NULL AND {col} IS NOT NULL
            """).fetchone()[0]
            ok = total - fail
        except Exception as exc:
            log.warning("Date parse check failed for %s: %s", col, exc)
            fail, ok = None, None

        rows.append({"column": col, "total": total, "parse_ok": ok,
                     "parse_fail": fail,
                     "fail_pct": round(fail / total * 100, 2) if fail is not None else None})

    con.close()
    return pd.DataFrame(rows)


def run_data_quality_assessment(parquet_path: Path) -> dict[str, pd.DataFrame]:
    """Run all data quality checks and return results keyed by check name.

    Returns
    -------
    dict with keys:
        - ``top_level``: :func:`assess_top_level_quality` result
        - ``nested_coverage``: :func:`assess_nested_coverage` result
        - ``statusinfo_sentinels``: :func:`assess_statusinfo_sentinels` result
        - ``date_parseability``: :func:`assess_date_parseability` result
    """
    log.info("=== DATA QUALITY ASSESSMENT START ===")
    result = {
        "top_level": assess_top_level_quality(parquet_path),
        "nested_coverage": assess_nested_coverage(parquet_path),
        "statusinfo_sentinels": assess_statusinfo_sentinels(parquet_path),
        "date_parseability": assess_date_parseability(parquet_path),
    }
    log.info("=== DATA QUALITY ASSESSMENT COMPLETE ===")
    return result
