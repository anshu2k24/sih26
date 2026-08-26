"""
ertmac.utils.paths
==================
Centralised path constants for the project.

All paths are resolved relative to the repository root so scripts can be
run from any working directory without breaking imports.
"""

from pathlib import Path

# ── Repository root: two levels up from src/ertmac/utils/paths.py ──────────
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# ── Data directories (NEVER write to RAW) ──────────────────────────────────
DATA_DIR: Path = REPO_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
FEATURES_DIR: Path = DATA_DIR / "features"

# ── Source dataset (read-only) ──────────────────────────────────────────────
RAW_PARQUET: Path = RAW_DIR / "volve_ddr.parquet"

# ── Output directories ──────────────────────────────────────────────────────
REPORTS_DIR: Path = REPO_ROOT / "reports"
FIGURES_DIR: Path = REPORTS_DIR / "figures"
TABLES_DIR: Path = REPORTS_DIR / "tables"
ARTIFACTS_DIR: Path = REPO_ROOT / "artifacts"


def ensure_output_dirs() -> None:
    """Create all output directories if they do not already exist."""
    for directory in (PROCESSED_DIR, FEATURES_DIR, REPORTS_DIR, FIGURES_DIR, TABLES_DIR, ARTIFACTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
