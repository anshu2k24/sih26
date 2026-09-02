import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

try:
    supabase: Client = create_client(url, key)
    res = supabase.table("handwritten_notes").select("*").execute()
    print("Fetched notes count:", len(res.data))
    if len(res.data) > 0:
        print("Sample:", res.data[0])
except Exception as e:
    print("Supabase Error:", e)
