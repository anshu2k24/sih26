"""
PS26121 eRTMAC-NWIS — Role-Based Access Control (RBAC) & Identity Module

Security model:
- Identity is derived from the verified Supabase JWT (server-side).
- Role is derived from the `profiles` table in Supabase, NOT from any browser header.
- Permissions are derived from the canonical role → permission matrix.
- Browser cannot escalate its own privileges.

NEVER:
- Trust X-User-Role header from browser
- Trust role from request body
- Trust user_id from URL parameters
"""

import os
import logging
from enum import Enum
from typing import Set, Optional, Dict, Any
from fastapi import Header, HTTPException, Depends, status

from ertmac.auth.jwt_verifier import (
    verify_supabase_jwt,
    JWTMissingError,
    JWTExpiredError,
    JWTVerificationError,
)
from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured

logger = logging.getLogger("ertmac.auth.rbac")

# ============================================================
# CANONICAL ROLE MODEL
# Must match: schema.sql profiles.role CHECK constraint
# ============================================================
class Role(str, Enum):
    ADMIN                = "ADMIN"
    DRILLING_ENGINEER    = "DRILLING_ENGINEER"
    OPERATIONS_ENGINEER  = "OPERATIONS_ENGINEER"
    ANALYST              = "ANALYST"
    VIEWER               = "VIEWER"


# ============================================================
# CANONICAL PERMISSION SET
# ============================================================
class Permission(str, Enum):
    VIEW_TELEMETRY      = "VIEW_TELEMETRY"
    VIEW_WELLS          = "VIEW_WELLS"
    VIEW_HISTORICAL_DATA = "VIEW_HISTORICAL_DATA"
    VIEW_ALERTS         = "VIEW_ALERTS"
    ACKNOWLEDGE_ALERT   = "ACKNOWLEDGE_ALERT"
    INVESTIGATE_ALERT   = "INVESTIGATE_ALERT"
    RESOLVE_ALERT       = "RESOLVE_ALERT"
    VIEW_PREDICTIONS    = "VIEW_PREDICTIONS"
    RUN_ANALYSIS        = "RUN_ANALYSIS"
    VIEW_AUDIT          = "VIEW_AUDIT"
    MANAGE_USERS        = "MANAGE_USERS"
    MANAGE_SYSTEM       = "MANAGE_SYSTEM"
    GENERATE_REPORTS    = "GENERATE_REPORTS"
    VIEW_REPORTS        = "VIEW_REPORTS"
    UPLOAD_DOCUMENTS    = "UPLOAD_DOCUMENTS"
    VERIFY_KNOWLEDGE    = "VERIFY_KNOWLEDGE"
    VIEW_NOTIFICATIONS  = "VIEW_NOTIFICATIONS"
    MANAGE_NOTIFICATIONS = "MANAGE_NOTIFICATIONS"


# ============================================================
# ROLE → PERMISSION MATRIX
# ============================================================
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions

    Role.DRILLING_ENGINEER: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_WELLS,
        Permission.VIEW_HISTORICAL_DATA,
        Permission.VIEW_ALERTS,
        Permission.ACKNOWLEDGE_ALERT,
        Permission.INVESTIGATE_ALERT,
        Permission.RESOLVE_ALERT,
        Permission.VIEW_PREDICTIONS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_AUDIT,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VERIFY_KNOWLEDGE,
        Permission.VIEW_NOTIFICATIONS,
        Permission.MANAGE_NOTIFICATIONS,
    },

    Role.OPERATIONS_ENGINEER: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_WELLS,
        Permission.VIEW_HISTORICAL_DATA,
        Permission.VIEW_ALERTS,
        Permission.ACKNOWLEDGE_ALERT,
        Permission.INVESTIGATE_ALERT,
        Permission.VIEW_PREDICTIONS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_AUDIT,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_NOTIFICATIONS,
    },

    Role.ANALYST: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_WELLS,
        Permission.VIEW_HISTORICAL_DATA,
        Permission.VIEW_ALERTS,
        Permission.VIEW_PREDICTIONS,
        Permission.RUN_ANALYSIS,
        Permission.VIEW_AUDIT,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_NOTIFICATIONS,
    },

    Role.VIEWER: {
        Permission.VIEW_TELEMETRY,
        Permission.VIEW_WELLS,
        Permission.VIEW_HISTORICAL_DATA,
        Permission.VIEW_ALERTS,
        Permission.VIEW_PREDICTIONS,
        Permission.VIEW_REPORTS,
        Permission.VIEW_NOTIFICATIONS,
    },
}


# ============================================================
# USER SESSION (Verified server-side identity)
# ============================================================
class UserSession:
    def __init__(
        self,
        user_id: str,
        email: str,
        role: Role,
        organization_id: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.organization_id = organization_id or "00000000-0000-0000-0000-000000000001"
        self.full_name = full_name
        self.permissions: Set[Permission] = ROLE_PERMISSIONS.get(role, set())

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role.value,
            "organization_id": self.organization_id,
            "full_name": self.full_name,
            "permissions": [p.value for p in self.permissions],
        }


# ============================================================
# DEV STUB SESSION
# Used ONLY when AUTH_REQUIRED=false (local dev without Supabase)
# ============================================================
_DEV_SESSION = UserSession(
    user_id="00000000-0000-0000-0000-000000000001",
    email="dev.engineer@localhost",
    role=Role.DRILLING_ENGINEER,
    organization_id="00000000-0000-0000-0000-000000000001",
    full_name="Dev Engineer (Local)",
)


# ============================================================
# PROFILE LOOKUP
# ============================================================
import time

_PROFILE_CACHE: Dict[str, Tuple[Optional[Dict[str, Any]], float]] = {}
_PROFILE_TTL = 60.0

def _lookup_profile_from_db(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Looks up user in Supabase `profiles` table.
    Caches profile for 60 seconds to eliminate redundant database queries.
    """
    now = time.time()
    cached = _PROFILE_CACHE.get(user_id)
    if cached:
        prof, expires_at = cached
        if now < expires_at:
            return prof
        else:
            del _PROFILE_CACHE[user_id]

    db = get_supabase_admin()
    if not db:
        return None

    try:
        result = (
            db.table("profiles")
            .select("id, email, full_name, role, organization_id, is_active")
            .eq("id", user_id)
            .single()
            .execute()
        )
        data = result.data if result.data else None
        _PROFILE_CACHE[user_id] = (data, now + _PROFILE_TTL)
        return data
    except Exception as e:
        logger.error(f"Profile DB lookup failed for user {user_id}: {e}")
        return None


# ============================================================
# FASTAPI DEPENDENCY: get_current_user
# ============================================================
def get_current_user(
    authorization: Optional[str] = Header(None),
) -> UserSession:
    """
    FastAPI dependency that extracts and verifies the authenticated user.

    Flow:
    1. Read Authorization: Bearer <token> header
    2. If AUTH_REQUIRED=false → return dev stub (local dev only)
    3. Verify JWT using SUPABASE_JWT_SECRET
    4. Look up user profile in Supabase `profiles` table
    5. Derive role from DB (not from JWT claims)
    6. Return verified UserSession

    Raises:
        401: Missing token, invalid token, expired token, inactive user
        403: Insufficient permissions (checked downstream via require_permission)
    """
    auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

    # ── Dev bypass mode ──────────────────────────────────────
    if not auth_required:
        if not authorization:
            logger.debug("AUTH_REQUIRED=false: returning dev stub session.")
            return _DEV_SESSION

        # If a token IS provided in dev mode, still attempt to decode it
        # so real Supabase tokens work during dev testing
        try:
            token = _extract_bearer_token(authorization)
            claims = verify_supabase_jwt(token)
            user_id = claims.get("sub")
            if user_id:
                profile = _lookup_profile_from_db(user_id)
                if profile:
                    return _session_from_profile(profile, user_id, claims)
        except Exception:
            pass  # Fall through to dev stub
        return _DEV_SESSION

    # ── Production mode ──────────────────────────────────────
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = _extract_bearer_token(authorization)

    try:
        claims = verify_supabase_jwt(token)
    except JWTMissingError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity (sub claim).",
        )

    # Derive role from DB — not from JWT claims or browser headers
    profile = _lookup_profile_from_db(user_id)
    if not profile:
        if not is_supabase_configured():
            # Supabase not configured in production = misconfiguration
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Identity service unavailable. Contact system administrator.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User profile not found. Account may not be provisioned.",
        )

    if not profile.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled.",
        )

    return _session_from_profile(profile, user_id, claims)


def _extract_bearer_token(authorization: str) -> str:
    """Extracts token from 'Bearer <token>' header value."""
    if not authorization.startswith("Bearer "):
        raise JWTVerificationError("Authorization header must use Bearer scheme.")
    token = authorization[len("Bearer "):].strip()
    if not token:
        raise JWTMissingError("Bearer token is empty.")
    return token


def _session_from_profile(
    profile: Dict[str, Any],
    user_id: str,
    claims: Dict[str, Any]
) -> UserSession:
    """Constructs a verified UserSession from the database profile."""
    raw_role = profile.get("role", "VIEWER")
    try:
        role = Role(raw_role)
    except ValueError:
        logger.warning(f"Unknown role '{raw_role}' for user {user_id}. Defaulting to VIEWER.")
        role = Role.VIEWER

    return UserSession(
        user_id=user_id,
        email=profile.get("email") or claims.get("email", ""),
        role=role,
        organization_id=str(profile.get("organization_id", "")),
        full_name=profile.get("full_name"),
    )


# ============================================================
# FASTAPI DEPENDENCY: require_permission
# ============================================================
def require_permission(perm: Permission):
    """
    FastAPI dependency factory.
    Usage: `user: UserSession = Depends(require_permission(Permission.RESOLVE_ALERT))`
    """
    def _dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if not user.has_permission(perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. This action requires the '{perm.value}' permission. "
                    f"Your role '{user.role.value}' does not include this permission."
                ),
            )
        return user
    return _dependency


def require_role(required_role: Role):
    """
    FastAPI dependency factory for role-level gates (stricter than permission).
    Usage: `user: UserSession = Depends(require_role(Role.ADMIN))`
    """
    def _dependency(user: UserSession = Depends(get_current_user)) -> UserSession:
        if user.role != required_role and user.role != Role.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. This endpoint requires role '{required_role.value}'. "
                    f"Your role is '{user.role.value}'."
                ),
            )
        return user
    return _dependency


def authenticate_websocket_session(websocket: Any, well_id: str = "") -> Optional[UserSession]:
    """
    WebSocket authentication & organization validation helper.
    When AUTH_REQUIRED=true:
    - Extracts token from query params (`?token=...`) or headers.
    - Validates JWT and profile using SUPABASE_JWT_SECRET.
    - Validates user session permissions (VIEW_TELEMETRY).
    - Returns None if unauthenticated or unauthorized.
    """
    auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    if not auth_required:
        return _DEV_SESSION

    token = websocket.query_params.get("token") if hasattr(websocket, "query_params") else None
    if not token and hasattr(websocket, "headers"):
        auth_hdr = websocket.headers.get("authorization")
        if auth_hdr:
            try:
                token = _extract_bearer_token(auth_hdr)
            except Exception:
                token = None

    if not token:
        logger.warning("WebSocket auth failed: missing token parameter or authorization header.")
        return None

    try:
        claims = verify_supabase_jwt(token)
        user_id = claims.get("sub")
        if not user_id:
            return None
        profile = _lookup_profile_from_db(user_id)
        if profile and not profile.get("is_active", True):
            return None
        if profile:
            session = _session_from_profile(profile, user_id, claims)
        else:
            session = UserSession(
                user_id=user_id,
                email=claims.get("email", ""),
                role=Role.VIEWER,
                organization_id=claims.get("organization_id", ""),
            )
        
        if not session.has_permission(Permission.VIEW_TELEMETRY):
            logger.warning(f"WebSocket auth failed: role '{session.role.value}' lacks VIEW_TELEMETRY permission.")
            return None

        return session
    except Exception as e:
        logger.warning(f"WebSocket JWT validation failed: {e}")
        return None

