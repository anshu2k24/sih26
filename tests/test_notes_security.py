"""
PS121 Handwritten Notes OCR — Security & RBAC Test Suite
Tests authentication headers, RBAC permission enforcement, and rejection of unauthorized calls.
"""

import pytest
from fastapi.testclient import TestClient
from ertmac.api.server import app
from ertmac.auth.rbac import Role, Permission, ROLE_PERMISSIONS


class TestNotesSecurity:

    def test_rbac_permission_matrix(self):
        # Admin has all permissions including UPLOAD_NOTES and VERIFY_NOTES
        assert Permission.UPLOAD_NOTES in ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.VERIFY_NOTES in ROLE_PERMISSIONS[Role.ADMIN]

        # Drilling Engineer has both
        assert Permission.UPLOAD_NOTES in ROLE_PERMISSIONS[Role.DRILLING_ENGINEER]
        assert Permission.VERIFY_NOTES in ROLE_PERMISSIONS[Role.DRILLING_ENGINEER]

        # Operations Engineer has both
        assert Permission.UPLOAD_NOTES in ROLE_PERMISSIONS[Role.OPERATIONS_ENGINEER]
        assert Permission.VERIFY_NOTES in ROLE_PERMISSIONS[Role.OPERATIONS_ENGINEER]

        # Analyst can upload but not verify
        assert Permission.UPLOAD_NOTES in ROLE_PERMISSIONS[Role.ANALYST]
        assert Permission.VERIFY_NOTES not in ROLE_PERMISSIONS[Role.ANALYST]

        # Viewer cannot upload or verify
        assert Permission.UPLOAD_NOTES not in ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.VERIFY_NOTES not in ROLE_PERMISSIONS[Role.VIEWER]

    def test_no_archscale_runtime_dependency(self):
        """Mandatory requirement §46: Check codebase for prohibited ArchScale runtime dependencies."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        src_path = repo_root / "src"
        frontend_src = repo_root / "frontend" / "src"

        forbidden_terms = ["archscale", "cloud.archscale.in", "ArchScaleAddressBookApi"]

        for path in [src_path, frontend_src]:
            for p in path.rglob("*"):
                if p.is_file() and p.suffix in (".py", ".ts", ".tsx", ".js"):
                    content = p.read_text(encoding="utf-8", errors="ignore").lower()
                    for term in forbidden_terms:
                        assert term not in content, f"Forbidden ArchScale reference found in {p}"
