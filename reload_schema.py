import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_str = os.environ.get("DATABASE_URL")
try:
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("NOTIFY pgrst, 'reload schema';")
    conn.commit()
    print("Schema cache reloaded successfully!")
except Exception as e:
    print(f"Database error: {e}")
finally:
    if 'conn' in locals() and conn:
        cur.close()
        conn.close()
