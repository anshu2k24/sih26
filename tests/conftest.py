import os
import pytest

# Ensure tests default to AUTH_REQUIRED=false unless a test explicitly tests AUTH_REQUIRED=true
os.environ["AUTH_REQUIRED"] = "false"
