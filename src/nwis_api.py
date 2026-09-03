"""
Shim for IDE static analysis and type resolution.
Re-exports NWISHistoricalAPI from scripts/nwis_api.py.
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import importlib.util

_spec = importlib.util.spec_from_file_location("scripts_nwis_api", str(_SCRIPTS_DIR / "nwis_api.py"))
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    NWISHistoricalAPI = getattr(_mod, "NWISHistoricalAPI")
else:
    from scripts.nwis_api import NWISHistoricalAPI  # type: ignore

__all__ = ["NWISHistoricalAPI"]
