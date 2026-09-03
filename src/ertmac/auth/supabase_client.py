"""
PS26121 eRTMAC-NWIS — Supabase Client Module
Provides a singleton Supabase client initialized from environment variables.

IMPORTANT:
- SUPABASE_SERVICE_ROLE_KEY is used ONLY in backend code.
- SUPABASE_ANON_KEY may be used for operations that should respect RLS.
- NEVER expose SUPABASE_SERVICE_ROLE_KEY to frontend bundles.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("ertmac.auth.supabase_client")

# Lazy-imported to avoid hard dependency when Supabase is not configured
_supabase_client = None
_supabase_anon_client = None


def get_supabase_admin():
    """
    Returns a Supabase client using the SERVICE_ROLE_KEY.
    This client bypasses RLS — use only for trusted backend operations
    such as writing audit logs, creating alerts, resolving user profiles.
    
    Returns None (with a warning) if Supabase is not configured.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not supabase_url or not service_role_key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. "
            "Supabase persistence is DISABLED. System will operate in in-memory mode."
        )
        return None

    try:
        from supabase import create_client, Client, ClientOptions
        options = ClientOptions(postgrest_client_timeout=10, storage_client_timeout=10)
        _supabase_client = create_client(supabase_url, service_role_key, options=options)
        logger.info("Supabase admin client initialized successfully.")
        return _supabase_client
    except ImportError:
        logger.error(
            "supabase-py package not installed. Run: pip install supabase"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {e}")
        return None


def get_supabase_anon():
    """
    Returns a Supabase client using the ANON_KEY.
    This client respects Row-Level Security policies.
    
    Returns None if Supabase is not configured.
    """
    global _supabase_anon_client

    if _supabase_anon_client is not None:
        return _supabase_anon_client

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not anon_key:
        return None

    try:
        from supabase import create_client, ClientOptions
        options = ClientOptions(postgrest_client_timeout=10, storage_client_timeout=10)
        _supabase_anon_client = create_client(supabase_url, anon_key, options=options)
        return _supabase_anon_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase anon client: {e}")
        return None


def is_supabase_configured() -> bool:
    """Returns True if Supabase environment variables are present."""
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )
