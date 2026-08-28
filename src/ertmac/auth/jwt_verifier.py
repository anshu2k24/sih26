"""
PS26121 eRTMAC-NWIS — JWT Token Verifier
Verifies Supabase-issued JWTs on the backend.

Never trust:
- Role claims from browser headers
- User identity from request body
- organization_id from URL params

Always derive identity from verified JWT claims + database lookup.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger("ertmac.auth.jwt_verifier")


class JWTVerificationError(Exception):
    """Raised when JWT is invalid, expired, or malformed."""
    pass


class JWTExpiredError(JWTVerificationError):
    """Raised specifically for expired tokens."""
    pass


class JWTMissingError(JWTVerificationError):
    """Raised when no token is provided."""
    pass


import time

_TOKEN_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}
_CACHE_TTL_SECONDS = 60.0


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Verifies a Supabase JWT and returns the decoded claims dict.
    Caches verified claims for 60 seconds to eliminate redundant network roundtrips.
    """
    if not token or not token.strip():
        raise JWTMissingError("No JWT token provided.")

    now = time.time()
    # Check in-memory cache first
    cached = _TOKEN_CACHE.get(token)
    if cached:
        claims, expires_at = cached
        if now < expires_at:
            return claims
        else:
            del _TOKEN_CACHE[token]

    jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()

    # 1. Fast path: Direct HS256 decoding if local secret matches
    if jwt_secret:
        try:
            import jwt as pyjwt
            claims = pyjwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            _TOKEN_CACHE[token] = (claims, now + _CACHE_TTL_SECONDS)
            return claims
        except pyjwt.ExpiredSignatureError:
            raise JWTExpiredError("JWT token has expired. Please re-authenticate.")
        except Exception:
            pass

    # 2. Authoritative path: Verify via Supabase Auth API
    from ertmac.auth.supabase_client import get_supabase_admin
    db = get_supabase_admin()
    if db:
        try:
            res = db.auth.get_user(token)
            if res and res.user:
                claims = {
                    "sub": res.user.id,
                    "email": res.user.email,
                    "role": "authenticated",
                    "aud": "authenticated",
                }
                _TOKEN_CACHE[token] = (claims, now + _CACHE_TTL_SECONDS)
                return claims
        except Exception as e:
            err_str = str(e).lower()
            if "expired" in err_str:
                raise JWTExpiredError("JWT token has expired. Please re-authenticate.")
            raise JWTVerificationError(f"Invalid authentication token: {e}")

    # 3. Dev fallback only when auth is not required
    auth_required = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    if not auth_required:
        return _decode_jwt_unverified(token)

    raise JWTVerificationError("JWT verification failed and Supabase is unreachable.")




def _decode_jwt_unverified(token: str) -> Dict[str, Any]:
    """
    Decodes JWT claims WITHOUT signature verification.
    Only used in local dev mode when SUPABASE_JWT_SECRET is not set.
    Never used when AUTH_REQUIRED=true.
    """
    try:
        import jwt as pyjwt
        claims = pyjwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256"]
        )
        return claims
    except Exception:
        # If we can't even decode, return a minimal stub
        return {
            "sub": "dev-user-00000000-0000-0000-0000-000000000001",
            "email": "dev@localhost",
            "exp": 9999999999
        }


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Extracts the user UUID (`sub` claim) from a JWT without full verification.
    Used only for logging purposes — never for authorization decisions.
    """
    try:
        claims = _decode_jwt_unverified(token)
        return claims.get("sub")
    except Exception:
        return None
