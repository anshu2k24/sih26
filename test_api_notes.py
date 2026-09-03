import requests

try:
    res = requests.get("http://localhost:8000/api/v1/notes", timeout=5)
    print(res.status_code)
    print(res.json())
except Exception as e:
    print(e)
