import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)
res = supabase.table("handwritten_notes").select("id, title, verification_status, structured_data, created_at").execute()
for r in res.data:
    print(r)
