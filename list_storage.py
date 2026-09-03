import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

res = supabase.storage.from_("documents").list()
print(f"Files in 'documents' bucket: {len(res)}")
for f in res:
    print(f['name'])
