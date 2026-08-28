"""
PS26121 — Resend Safe Real Delivery Test Script
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()

# Override from_email to verified sandbox sender for test
os.environ["RESEND_FROM_EMAIL"] = "onboarding@resend.dev"

from ertmac.notifications.delivery import NotificationDeliveryEngine

def test_resend():
    resend_key = os.getenv("RESEND_API_KEY")
    if not resend_key:
        print("[RESEND TEST] RESEND_API_KEY is MISSING from environment.")
        return

    print(f"[RESEND TEST] RESEND_API_KEY is CONFIGURED (Key length: {len(resend_key)})")
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    print(f"[RESEND TEST] RESEND_FROM_EMAIL: {from_email}")

    alert_payload = {
        "id": "00000000-0000-0000-0000-000000000001",
        "well_id": "15/9-F-14",
        "severity": "CRITICAL",
        "title": "Production Hardening Resend Delivery Verification Test",
        "description": "Empirical validation of Resend API email dispatch pipeline for PS26121 eRTMAC-NWIS.",
        "current_md": 1509.1,
        "evidence": {"torque_nm": 28500, "wob_kN": 185.2},
    }

    try:
        result = NotificationDeliveryEngine.dispatch_alert_email(
            alert_dict=alert_payload,
            recipient_email="delivered@resend.dev",
        )
        print(f"[RESEND TEST] Delivery Dispatch Result: {result}")
        if result.get("resend_id"):
            print(f"[PASS] Real Resend Email Dispatched! Resend Email ID: {result['resend_id']}")
        elif result.get("status") == "SENT":
            print(f"[PASS] Resend Dispatch Succeeded (Status: SENT)")
        else:
            print(f"[WARN] Resend status: {result.get('status')} | Details: {result.get('error_message')}")
    except Exception as e:
        print(f"[FAIL] Resend Delivery Exception: {e}")

if __name__ == "__main__":
    test_resend()
