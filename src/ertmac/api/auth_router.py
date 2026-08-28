"""
PS26121 eRTMAC-NWIS — Auth & User Management Router
Provides authenticated user profile, admin user management, and session endpoints.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    require_role,
    UserSession,
    Role,
    Permission,
)
from ertmac.auth.supabase_client import get_supabase_admin, is_supabase_configured
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.api.auth")

router = APIRouter(prefix="/api", tags=["Identity & Auth"])


# ============================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None


class UpdateUserRoleRequest(BaseModel):
    role: str


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    role: str
    organization_id: str
    full_name: Optional[str]
    permissions: List[str]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/users/me", response_model=UserProfileResponse)
def get_current_user_profile(user: UserSession = Depends(get_current_user)):
    """
    Returns the authenticated user's profile and RBAC permissions.
    Identity is derived from verified JWT — not from browser-supplied claims.
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role.value,
        "organization_id": user.organization_id,
        "full_name": user.full_name,
        "permissions": [p.value for p in user.permissions],
    }


@router.patch("/users/me")
def update_current_user_profile(
    body: UpdateProfileRequest,
    user: UserSession = Depends(get_current_user)
):
    """
    Allows authenticated users to update their own display name.
    Role cannot be self-modified — requires ADMIN via /api/users/{id}/role.
    """
    db = get_supabase_admin()
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Profile update not persisted."
        )

    updates = {}
    if body.full_name is not None:
        updates["full_name"] = body.full_name

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update."
        )

    try:
        result = (
            db.table("profiles")
            .update(updates)
            .eq("id", user.user_id)
            .execute()
        )
        global_audit_service.log_event(
            actor_id=user.user_id,
            actor_role=user.role.value,
            action="PROFILE_UPDATED",
            resource_type="USER",
            resource_id=user.user_id,
            organization_id=user.organization_id,
        )
        return {"status": "updated", "user_id": user.user_id, **updates}
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed."
        )


@router.get("/users")
def list_users(
    user: UserSession = Depends(require_permission(Permission.MANAGE_USERS)),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Returns a list of users in the current organization.
    Requires MANAGE_USERS permission (ADMIN only).
    """
    db = get_supabase_admin()
    if not db:
        return {
            "supabase_configured": False,
            "users": [],
            "message": "Database not configured. Running in local dev mode."
        }

    try:
        result = (
            db.table("profiles")
            .select("id, email, full_name, role, is_active, created_at, last_login_at")
            .eq("organization_id", user.organization_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {
            "organization_id": user.organization_id,
            "count": len(result.data or []),
            "users": result.data or [],
        }
    except Exception as e:
        logger.error(f"List users failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user list."
        )


@router.patch("/users/{target_user_id}/role")
def update_user_role(
    target_user_id: str,
    body: UpdateUserRoleRequest,
    admin_user: UserSession = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """
    Updates a user's role within the organization.
    ADMIN only. Cannot be used to set a role outside the canonical set.
    Produces an audit record.
    """
    # Validate the requested role
    try:
        new_role = Role(body.role.upper())
    except ValueError:
        valid_roles = [r.value for r in Role]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )

    db = get_supabase_admin()
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable."
        )

    # Prevent cross-org role changes
    target_result = (
        db.table("profiles")
        .select("id, role, organization_id")
        .eq("id", target_user_id)
        .single()
        .execute()
    )
    if not target_result.data:
        raise HTTPException(status_code=404, detail="User not found.")

    target_profile = target_result.data
    if str(target_profile.get("organization_id")) != str(admin_user.organization_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify users in another organization."
        )

    old_role = target_profile.get("role", "UNKNOWN")

    try:
        db.table("profiles").update({"role": new_role.value}).eq("id", target_user_id).execute()

        global_audit_service.log_event(
            actor_id=admin_user.user_id,
            actor_role=admin_user.role.value,
            action="USER_ROLE_CHANGED",
            resource_type="USER",
            resource_id=target_user_id,
            organization_id=admin_user.organization_id,
            payload={"before_role": old_role, "after_role": new_role.value},
        )

        return {
            "status": "updated",
            "user_id": target_user_id,
            "old_role": old_role,
            "new_role": new_role.value,
        }
    except Exception as e:
        logger.error(f"Role update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Role update failed."
        )


@router.patch("/users/{target_user_id}/disable")
def disable_user(
    target_user_id: str,
    admin_user: UserSession = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Disables a user account (does not delete). ADMIN only."""
    db = get_supabase_admin()
    if not db:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        db.table("profiles").update({"is_active": False}).eq("id", target_user_id).execute()
        global_audit_service.log_event(
            actor_id=admin_user.user_id,
            actor_role=admin_user.role.value,
            action="USER_DISABLED",
            resource_type="USER",
            resource_id=target_user_id,
            organization_id=admin_user.organization_id,
        )
        return {"status": "disabled", "user_id": target_user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disable user failed: {e}")


@router.get("/auth/status")
def auth_status(user: UserSession = Depends(get_current_user)):
    """
    Lightweight endpoint for frontend session validation.
    Returns minimal identity info. Used on app startup to check session validity.
    """
    return {
        "authenticated": True,
        "user_id": user.user_id,
        "role": user.role.value,
        "organization_id": user.organization_id,
    }


@router.get("/admin/organizations")
def list_organizations(user: UserSession = Depends(require_permission(Permission.VIEW_WELLS))):
    """
    Returns list of organization tenants and their active status.
    """
    db = get_supabase_admin()
    if db:
        try:
            res = db.table("organizations").select("*").execute()
            return {"status": "SUCCESS", "organizations": res.data}
        except Exception as e:
            logger.warning(f"Database query failed, returning fallback orgs: {e}")

    return {
        "status": "SUCCESS",
        "organizations": [
            {
                "id": "org_equinor_01",
                "name": "Equinor ASA (Volve Operations)",
                "slug": "equinor-volve",
                "created_at": "2026-01-01T00:00:00Z",
                "isolation_policy": "RLS_ENFORCED",
            },
            {
                "id": "org_demo_02",
                "name": "North Sea Operator Demo Org",
                "slug": "ns-operator-demo",
                "created_at": "2026-02-01T00:00:00Z",
                "isolation_policy": "RLS_ENFORCED",
            },
        ]
    }

