"""
PS26121 eRTMAC-NWIS — Dynamic System Settings Manager
Manages runtime configuration settings including alert threshold parameters,
telemetry stream settings, and notification recipient email configuration.
"""

import os
from typing import Dict, Any

_SYSTEM_SETTINGS: Dict[str, Any] = {
    "search_radius_km_default": 5.0,
    "depth_window_m_default": 50.0,
    "telemetry_stream_url": "ws://localhost:8765",
    "notification_recipient_email": os.getenv("ALERT_NOTIFICATION_EMAIL", "operator@company.com"),
    "resend_notifications_enabled": bool(os.getenv("RESEND_API_KEY")),
    "supabase_persistence_enabled": bool(os.getenv("SUPABASE_URL")),
    "ml_readiness_gate_enforced": True,
    "auth_required": os.getenv("AUTH_REQUIRED", "false").lower() == "true",
}


def get_system_settings() -> Dict[str, Any]:
    """Returns the current system configuration settings."""
    _SYSTEM_SETTINGS["resend_notifications_enabled"] = bool(os.getenv("RESEND_API_KEY"))
    _SYSTEM_SETTINGS["supabase_persistence_enabled"] = bool(os.getenv("SUPABASE_URL"))
    _SYSTEM_SETTINGS["auth_required"] = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    return _SYSTEM_SETTINGS.copy()


def update_system_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates dynamic system settings in memory."""
    for key, val in updates.items():
        if key in _SYSTEM_SETTINGS:
            _SYSTEM_SETTINGS[key] = val
    return get_system_settings()


def get_notification_recipient_email() -> str:
    """Returns the configured notification recipient email address."""
    return _SYSTEM_SETTINGS.get("notification_recipient_email", os.getenv("ALERT_NOTIFICATION_EMAIL", "operator@company.com"))

