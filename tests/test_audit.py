"""
tests/test_audit.py
====================
Unit tests for Checkpoint-1 audit modules.

Run with:
    source .venv/bin/activate
    pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
import pandas as pd

# Ensure src/ is on the path when running without installation
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from ertmac.utils.paths import RAW_PARQUET, REPO_ROOT
from ertmac.audit.schema_inspector import (
    load_arrow_schema,
    get_duckdb_schema,
    NESTED_ARRAY_COLS,
    SENTINEL_VALUES,
)
from ertmac.audit.data_quality import assess_nested_coverage, assess_date_parseability
from ertmac.audit.well_coverage import get_wellbore_report_counts


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def parquet_path() -> Path:
    """Return path to raw parquet; skip tests if file not present."""
    if not RAW_PARQUET.exists():
        pytest.skip(f"Raw parquet not found at {RAW_PARQUET}. Run dataset.py first.")
    return RAW_PARQUET


# ── Schema tests ──────────────────────────────────────────────────────────────

class TestArrowSchema:
    def test_schema_loads(self, parquet_path: Path) -> None:
        result = load_arrow_schema(parquet_path)
        assert isinstance(result, dict)
        assert result["num_rows"] > 0
        assert result["num_columns"] > 0

    def test_expected_row_count(self, parquet_path: Path) -> None:
        result = load_arrow_schema(parquet_path)
        assert result["num_rows"] == 1759, (
            f"Expected 1759 rows, got {result['num_rows']}. "
            "Dataset may have changed."
        )

    def test_expected_column_count(self, parquet_path: Path) -> None:
        # PyArrow flattens nested struct sub-fields and reports 84.
        # The top-level column count (17) is correctly returned by DuckDB DESCRIBE.
        duckdb_schema = get_duckdb_schema(parquet_path)
        assert len(duckdb_schema) == 17, (
            f"Expected 17 top-level columns via DuckDB, got {len(duckdb_schema)}"
        )


    def test_required_top_level_columns_present(self, parquet_path: Path) -> None:
        result = load_arrow_schema(parquet_path)
        col_names = {c["name"] for c in result["columns"]}
        required = {"docName", "nameWell", "nameWellbore", "dTimStart", "dTimEnd", "statusInfo", "activity"}
        missing = required - col_names
        assert not missing, f"Missing required columns: {missing}"

    def test_nested_cols_in_schema(self, parquet_path: Path) -> None:
        result = load_arrow_schema(parquet_path)
        col_names = {c["name"] for c in result["columns"]}
        for col in NESTED_ARRAY_COLS:
            assert col in col_names, f"Expected nested column '{col}' not in schema"


class TestDuckDBSchema:
    def test_duckdb_schema_returns_list(self, parquet_path: Path) -> None:
        result = get_duckdb_schema(parquet_path)
        assert isinstance(result, list)
        assert len(result) == 17

    def test_all_column_names_present(self, parquet_path: Path) -> None:
        result = get_duckdb_schema(parquet_path)
        names = {r["column_name"] for r in result}
        assert "nameWell" in names
        assert "activity" in names


# ── Data quality tests ────────────────────────────────────────────────────────

class TestNestedCoverage:
    def test_returns_dataframe(self, parquet_path: Path) -> None:
        df = assess_nested_coverage(parquet_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(NESTED_ARRAY_COLS)

    def test_activity_has_records(self, parquet_path: Path) -> None:
        df = assess_nested_coverage(parquet_path)
        activity_row = df[df["column"] == "activity"].iloc[0]
        assert activity_row["total_nested_records"] > 10_000, (
            "activity[] should have >10,000 nested records"
        )

    def test_no_negative_counts(self, parquet_path: Path) -> None:
        df = assess_nested_coverage(parquet_path)
        assert (df["total_nested_records"] >= 0).all()
        assert (df["empty_rows"] >= 0).all()

    def test_nonempty_plus_empty_equals_total(self, parquet_path: Path) -> None:
        df = assess_nested_coverage(parquet_path)
        for _, row in df.iterrows():
            assert row["nonempty_rows"] + row["empty_rows"] == row["total_rows"], (
                f"Row counts do not add up for column '{row['column']}'"
            )


class TestDateParseability:
    def test_returns_dataframe(self, parquet_path: Path) -> None:
        df = assess_date_parseability(parquet_path)
        assert isinstance(df, pd.DataFrame)
        assert "column" in df.columns

    def test_dTimStart_parseable(self, parquet_path: Path) -> None:
        df = assess_date_parseability(parquet_path)
        row = df[df["column"] == "dTimStart"].iloc[0]
        assert row["parse_fail"] == 0, (
            f"dTimStart has {row['parse_fail']} unparseable values"
        )


# ── Well coverage tests ───────────────────────────────────────────────────────

class TestWellCoverage:
    def test_returns_dataframe(self, parquet_path: Path) -> None:
        df = get_wellbore_report_counts(parquet_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_total_reports_sums_correctly(self, parquet_path: Path) -> None:
        df = get_wellbore_report_counts(parquet_path)
        assert df["report_count"].sum() == 1759

    def test_expected_wellbore_count(self, parquet_path: Path) -> None:
        df = get_wellbore_report_counts(parquet_path)
        assert len(df) == 26, f"Expected 26 wellbores, got {len(df)}"

    def test_no_null_wellbore_names(self, parquet_path: Path) -> None:
        df = get_wellbore_report_counts(parquet_path)
        assert df["nameWellbore"].notna().all()

    def test_date_span_nonnegative(self, parquet_path: Path) -> None:
        df = get_wellbore_report_counts(parquet_path)
        assert (df["date_span_days"] >= 0).all()


# ── Sentinel value set ────────────────────────────────────────────────────────

class TestSentinelValues:
    def test_primary_sentinel_in_set(self) -> None:
        assert "-999.99" in SENTINEL_VALUES

    def test_sentinel_set_is_nonempty(self) -> None:
        assert len(SENTINEL_VALUES) > 0


# ── Path utilities ────────────────────────────────────────────────────────────

class TestPaths:
    def test_repo_root_exists(self) -> None:
        assert REPO_ROOT.is_dir()

    def test_raw_parquet_in_raw_dir(self) -> None:
        assert RAW_PARQUET.parent.name == "raw"

    def test_raw_dir_inside_data_dir(self) -> None:
        assert RAW_PARQUET.parent.parent.name == "data"
