import os
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# Ensure tests default to AUTH_REQUIRED=false unless a test explicitly tests AUTH_REQUIRED=true
os.environ["AUTH_REQUIRED"] = "false"

