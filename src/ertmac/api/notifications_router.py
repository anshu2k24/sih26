"""
PS26121 eRTMAC-NWIS — Notification & Email Dispatch Router
Provides API endpoints for notification feeds, preferences, email delivery history, and escalation evaluation.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ertmac.auth.rbac import (
    get_current_user,
    require_permission,
    UserSession,
    Permission,
)
from ertmac.notifications.preferences import (
    get_user_preferences,
    update_user_preferences,
)
from ertmac.notifications.delivery import NotificationDeliveryEngine
from ertmac.notifications.escalation import EscalationEngine
from ertmac.audit.logger import global_audit_service

logger = logging.getLogger("ertmac.api.notifications")

router = APIRouter(prefix="/api/notifications", tags=["Notifications & Dispatch"])


class NotificationPreferencesRequest(BaseModel):
    email_enabled: Optional[bool] = None
    critical_alerts: Optional[bool] = None
    high_alerts: Optional[bool] = None
    medium_alerts: Optional[bool] = None
    historical_alerts: Optional[bool] = None
    system_notifications: Optional[bool] = None
    report_notifications: Optional[bool] = None


@router.get("/preferences")
def fetch_preferences(user: UserSession = Depends(require_permission(Permission.VIEW_NOTIFICATIONS))):
    """Returns the authenticated user's notification preferences."""
    prefs = get_user_preferences(user.user_id)
    return {"user_id": user.user_id, "preferences": prefs}


@router.put("/preferences")
def save_preferences(
    body: NotificationPreferencesRequest,
    user: UserSession = Depends(require_permission(Permission.MANAGE_NOTIFICATIONS)),
):
    """Updates the authenticated user's notification preferences."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = update_user_preferences(user.user_id, updates)
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="NOTIFICATION_PREFERENCES_UPDATED",
        resource_type="NOTIFICATION_PREFERENCES",
        resource_id=user.user_id,
        organization_id=user.organization_id,
        payload=updates,
    )
    return {"status": "updated", "user_id": user.user_id, "preferences": updated}


@router.get("")
def get_notification_feed(
    limit: int = Query(50, ge=1, le=200),
    user: UserSession = Depends(require_permission(Permission.VIEW_NOTIFICATIONS)),
):
    """Returns the in-app notification feed for the current user."""
    events = NotificationDeliveryEngine.get_in_app_notifications(user.user_id, limit=limit)
    unread_count = sum(1 for e in events if not e.get("is_read"))
    return {
        "count": len(events),
        "unread_count": unread_count,
        "notifications": events,
    }


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    user: UserSession = Depends(require_permission(Permission.VIEW_NOTIFICATIONS)),
):
    """Marks a single notification as read."""
    success = NotificationDeliveryEngine.mark_as_read(notification_id)
    return {"status": "success" if success else "failed", "notification_id": notification_id}


@router.post("/read-all")
def mark_all_notifications_read(
    user: UserSession = Depends(require_permission(Permission.VIEW_NOTIFICATIONS)),
):
    """Marks all notifications as read for the user."""
    success = NotificationDeliveryEngine.mark_all_as_read(user.user_id)
    return {"status": "success" if success else "failed", "user_id": user.user_id}


@router.get("/deliveries")
def get_delivery_history(
    limit: int = Query(50, ge=1, le=200),
    user: UserSession = Depends(require_permission(Permission.VIEW_NOTIFICATIONS)),
):
    """Returns email delivery log audit history (Resend dispatches)."""
    deliveries = NotificationDeliveryEngine.get_delivery_history(limit=limit)
    return {"count": len(deliveries), "deliveries": deliveries}


@router.post("/escalate/evaluate")
def evaluate_escalation_rules(
    timeout_minutes: int = Query(30, ge=1, le=1440),
    user: UserSession = Depends(require_permission(Permission.MANAGE_NOTIFICATIONS)),
):
    """Manually triggers evaluation of escalation SLA rules for unacknowledged alerts."""
    escalated = EscalationEngine.evaluate_escalations(timeout_minutes=timeout_minutes)
    global_audit_service.log_event(
        actor_id=user.user_id,
        actor_role=user.role.value,
        action="ESCALATION_EVALUATED",
        resource_type="ALERT_ESCALATION",
        resource_id="ALL",
        organization_id=user.organization_id,
        payload={"timeout_minutes": timeout_minutes, "escalated_count": len(escalated)},
    )
    return {"status": "success", "timeout_minutes": timeout_minutes, "escalated": escalated}
