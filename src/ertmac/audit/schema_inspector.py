"""
ertmac.audit.schema_inspector
==============================
Inspect the top-level and nested schema of the raw Volve DDR parquet file.

This module is READ-ONLY with respect to the raw dataset.
It never writes to data/raw/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import duckdb

from ertmac.utils.logging_setup import get_logger

log = get_logger(__name__)

# Sentinel values that must NOT be treated as real measurements
SENTINEL_VALUES: set[str] = {"-999.99", "-999", "None", "none", "NULL", "null", ""}

# Nested array columns identified in the schema
NESTED_ARRAY_COLS: list[str] = [
    "wellboreAlias",
    "wellboreInfo",
    "statusInfo",
    "fluid",
    "porePressure",
    "surveyStation",
    "activity",
    "lithShowInfo",
]

# Top-level scalar/struct columns
SCALAR_COLS: list[str] = [
    "docName",
    "nameWell",
    "nameWellbore",
    "name",
    "dTimStart",
    "dTimEnd",
    "versionKind",
    "createDate",
    "wellAlias",
]


def load_arrow_schema(parquet_path: Path) -> dict[str, Any]:
    """Read the PyArrow schema from a parquet file without loading all data.

    Parameters
    ----------
    parquet_path:
        Path to the raw parquet file.

    Returns
    -------
    dict with keys:
        - ``columns``: list of {name, pa_type, logical_type} dicts
        - ``num_rows``: total row count
        - ``num_row_groups``: number of parquet row groups
        - ``metadata``: raw file-level metadata (bytes decoded to str)
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"Raw parquet not found: {parquet_path}")

    pf = pq.ParquetFile(parquet_path)
    schema = pf.schema_arrow
    meta = pf.metadata

    columns = []
    for i, field in enumerate(schema):
        columns.append(
            {
                "index": i,
                "name": field.name,
                "pa_type": str(field.type),
                "nullable": field.nullable,
            }
        )

    raw_meta: dict[str, str] = {}
    if meta.metadata:
        for k, v in meta.metadata.items():
            try:
                raw_meta[k.decode()] = v.decode()
            except Exception:
                raw_meta[str(k)] = str(v)

    result = {
        "num_rows": meta.num_rows,
        "num_row_groups": meta.num_row_groups,
        "num_columns": meta.num_columns,
        "serialized_size_bytes": meta.serialized_size,
        "columns": columns,
        "file_metadata": raw_meta,
    }

    log.info(
        "Schema loaded: %d rows × %d columns, %d row group(s)",
        result["num_rows"],
        result["num_columns"],
        result["num_row_groups"],
    )
    return result


def get_duckdb_schema(parquet_path: Path) -> list[dict[str, str]]:
    """Return DuckDB's DESCRIBE output for the parquet file.

    Parameters
    ----------
    parquet_path:
        Path to the raw parquet file.

    Returns
    -------
    List of dicts with keys: column_name, column_type, null, key, default, extra.
    """
    con = duckdb.connect()
    df = con.execute(f"DESCRIBE SELECT * FROM '{parquet_path}'").df()
    con.close()
    records = df.to_dict(orient="records")
    log.info("DuckDB DESCRIBE returned %d column entries.", len(records))
    return records


def inspect_nested_column(parquet_path: Path, col: str, sample_rows: int = 5) -> dict[str, Any]:
    """Inspect a single nested array column: count records, identify sub-fields.

    Parameters
    ----------
    parquet_path:
        Path to the raw parquet file.
    col:
        Name of the nested column to inspect.
    sample_rows:
        Number of non-empty parent rows to sample for sub-field discovery.

    Returns
    -------
    dict with keys:
        - ``column``: column name
        - ``total_parent_rows``: rows in the parquet
        - ``rows_with_nonempty_array``: rows where the array has ≥1 element
        - ``rows_with_empty_array``: rows where array is empty
        - ``total_nested_records``: sum of all array lengths
        - ``sub_fields``: list of discovered sub-field names
        - ``sample_records``: up to ``sample_rows`` raw sample dicts
    """
    con = duckdb.connect()

    # Total parent rows
    total = con.execute(
        f"SELECT COUNT(*) FROM '{parquet_path}'"
    ).fetchone()[0]

    # Rows with non-empty arrays
    nonempty = con.execute(
        f"SELECT COUNT(*) FROM '{parquet_path}' WHERE len({col}) > 0"
    ).fetchone()[0]

    # Total nested records
    total_nested = con.execute(
        f"SELECT SUM(len({col})) FROM '{parquet_path}'"
    ).fetchone()[0] or 0

    # Sample unnested records for sub-field discovery
    try:
        sample_df = con.execute(f"""
            SELECT UNNEST({col}) AS rec
            FROM '{parquet_path}'
            WHERE len({col}) > 0
            LIMIT {sample_rows * 3}
        """).df()
        sample_records: list[dict] = []
        if not sample_df.empty and "rec" in sample_df.columns:
            for val in sample_df["rec"].dropna().head(sample_rows):
                if isinstance(val, dict):
                    sample_records.append(val)
        sub_fields = sorted(sample_records[0].keys()) if sample_records else []
    except Exception as exc:
        log.warning("Could not unnest column %s for sub-field discovery: %s", col, exc)
        sample_records = []
        sub_fields = []

    con.close()

    return {
        "column": col,
        "total_parent_rows": total,
        "rows_with_nonempty_array": nonempty,
        "rows_with_empty_array": total - nonempty,
        "total_nested_records": int(total_nested),
        "sub_fields": sub_fields,
        "sample_records": sample_records[:sample_rows],
    }


def run_schema_inspection(parquet_path: Path) -> dict[str, Any]:
    """Run the full schema inspection and return a unified result dict.

    Parameters
    ----------
    parquet_path:
        Path to the raw parquet file (data/raw/volve_ddr.parquet).

    Returns
    -------
    dict with keys:
        - ``arrow_schema``: output of :func:`load_arrow_schema`
        - ``duckdb_schema``: output of :func:`get_duckdb_schema`
        - ``nested_columns``: dict mapping column name → inspection result
    """
    log.info("=== SCHEMA INSPECTION START ===")

    arrow_schema = load_arrow_schema(parquet_path)
    duckdb_schema = get_duckdb_schema(parquet_path)

    nested_results: dict[str, Any] = {}
    for col in NESTED_ARRAY_COLS:
        log.info("Inspecting nested column: %s", col)
        nested_results[col] = inspect_nested_column(parquet_path, col)

    log.info("=== SCHEMA INSPECTION COMPLETE ===")
    return {
        "arrow_schema": arrow_schema,
        "duckdb_schema": duckdb_schema,
        "nested_columns": nested_results,
    }
