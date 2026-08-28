"""
PS26121 — Create High-Privilege Admin User in Supabase
Role: ADMIN
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()

from ertmac.auth.supabase_client import get_supabase_admin

def create_admin_account(email: str = None, password: str = None):
    if not email:
        email = os.getenv("ADMIN_EMAIL", "admin@company.com")
    if not password:
        password = os.getenv("ADMIN_PASSWORD", "123456")

    client = get_supabase_admin()
    if not client:
        print("ERROR: Supabase admin client unavailable. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        return


    print(f"Creating/updating high-privilege ADMIN account for '{email}' in Supabase...")

    try:
        # Check if user already exists in auth
        res = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": "Jayanth (Principal Admin)",
                "role": "ADMIN"
            }
        })
        user_id = res.user.id
        print(f"[SUCCESS] Supabase Auth user created! User ID: {user_id}")
    except Exception as e:
        err_msg = str(e)
        if "already" in err_msg.lower() or "registered" in err_msg.lower():
            print(f"User '{email}' already exists in Supabase Auth. Updating password and profile role to ADMIN...")
            try:
                # Find user ID
                users = client.auth.admin.list_users()
                target_user = next((u for u in users if u.email == email), None)
                if target_user:
                    user_id = target_user.id
                    client.auth.admin.update_user_by_id(user_id, {
                        "password": password,
                        "user_metadata": {"role": "ADMIN", "full_name": "Jayanth (Principal Admin)"}
                    })
                    print(f"[SUCCESS] Password and metadata updated for user ID: {user_id}")
                else:
                    print("Could not find user in list_users.")
                    return
            except Exception as ex:
                print(f"Update failed: {ex}")
                return
        else:
            print(f"Auth user creation error: {e}")
            return

    # Update profile in database table `profiles`
    try:
        org_res = client.table("organizations").select("id").limit(1).execute()
        org_id = org_res.data[0]["id"] if org_res.data else "00000000-0000-0000-0000-000000000001"

        client.table("profiles").upsert({
            "id": user_id,
            "organization_id": org_id,
            "email": email,
            "full_name": "Jayanth (Principal Admin)",
            "role": "ADMIN",
            "is_active": True
        }, on_conflict="id").execute()
        print(f"[SUCCESS] User profile in 'profiles' table set to ADMIN privilege for user {user_id}!")

    except Exception as e:
        print(f"Profile upsert warning: {e}")

if __name__ == "__main__":
    create_admin_account()
