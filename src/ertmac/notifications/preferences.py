"""
PS26121 eRTMAC-NWIS — User Notification & Operational Preferences Module
Manages per-user configuration and notification settings with Supabase PostgreSQL persistence.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ertmac.auth.supabase_client import get_supabase_admin

logger = logging.getLogger("ertmac.notifications.preferences")

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "notification_recipient_email": "",
    "search_radius_km_default": 5.0,
    "depth_window_m_default": 50.0,
    "email_enabled": True,
    "critical_alerts": True,
    "high_alerts": True,
    "medium_alerts": False,
    "historical_alerts": False,
    "system_notifications": True,
    "report_notifications": False,
}

_in_memory_prefs: Dict[str, Dict[str, Any]] = {}


def get_user_preferences(user_id: str, default_email: str = "") -> Dict[str, Any]:
    """
    Fetches custom configuration and notification preferences for an individual user from Supabase.
    Returns default settings if no custom record exists.
    """
    db = get_supabase_admin()
    if db:
        try:
            res = (
                db.table("notification_preferences")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            if res.data:
                return {
                    "notification_recipient_email": res.data.get("notification_recipient_email") or default_email,
                    "search_radius_km_default": float(res.data.get("search_radius_km_default", 5.0) or 5.0),
                    "depth_window_m_default": float(res.data.get("depth_window_m_default", 50.0) or 50.0),
                    "email_enabled": res.data.get("email_enabled", True),
                    "critical_alerts": res.data.get("critical_alerts", True),
                    "high_alerts": res.data.get("high_alerts", True),
                    "medium_alerts": res.data.get("medium_alerts", False),
                    "historical_alerts": res.data.get("historical_alerts", False),
                    "system_notifications": res.data.get("system_notifications", True),
                    "report_notifications": res.data.get("report_notifications", False),
                    "updated_at": res.data.get("updated_at"),
                }
        except Exception as e:
            logger.debug(f"No custom preferences found in DB for user {user_id}: {e}")

    # Fallback to in-memory store or defaults
    prefs = _in_memory_prefs.get(user_id, DEFAULT_PREFERENCES.copy())
    if not prefs.get("notification_recipient_email") and default_email:
        prefs["notification_recipient_email"] = default_email
    return prefs


def update_user_preferences(user_id: str, updates: Dict[str, Any], default_email: str = "") -> Dict[str, Any]:
    """
    Creates or updates user preferences in Supabase PostgreSQL (Upsert CRUD).
    """
    current = get_user_preferences(user_id, default_email=default_email)
    new_prefs = {**current, **updates}

    db = get_supabase_admin()
    if db:
        try:
            now = datetime.now(timezone.utc).isoformat()
            db.table("notification_preferences").upsert(
                {
                    "user_id": user_id,
                    "notification_recipient_email": new_prefs.get("notification_recipient_email") or default_email,
                    "search_radius_km_default": float(new_prefs.get("search_radius_km_default", 5.0) or 5.0),
                    "depth_window_m_default": float(new_prefs.get("depth_window_m_default", 50.0) or 50.0),
                    "email_enabled": new_prefs.get("email_enabled", True),
                    "critical_alerts": new_prefs.get("critical_alerts", True),
                    "high_alerts": new_prefs.get("high_alerts", True),
                    "medium_alerts": new_prefs.get("medium_alerts", False),
                    "historical_alerts": new_prefs.get("historical_alerts", False),
                    "system_notifications": new_prefs.get("system_notifications", True),
                    "report_notifications": new_prefs.get("report_notifications", False),
                    "updated_at": now,
                },
                on_conflict="user_id"
            ).execute()
            new_prefs["updated_at"] = now
        except Exception as e:
            logger.error(f"Failed to upsert notification preferences in DB for {user_id}: {e}")

    _in_memory_prefs[user_id] = new_prefs
    return new_prefs


def delete_user_preferences(user_id: str, default_email: str = "") -> Dict[str, Any]:
    """
    Deletes user custom preferences from Supabase PostgreSQL (Delete CRUD) and resets to defaults.
    """
    db = get_supabase_admin()
    if db:
        try:
            db.table("notification_preferences").delete().eq("user_id", user_id).execute()
            logger.info(f"Deleted custom preferences for user {user_id} in Supabase")
        except Exception as e:
            logger.error(f"Failed to delete notification preferences for {user_id} in DB: {e}")

    if user_id in _in_memory_prefs:
        del _in_memory_prefs[user_id]

    defaults = DEFAULT_PREFERENCES.copy()
    if default_email:
        defaults["notification_recipient_email"] = default_email
    return defaults

