#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def main():
    repo_root = Path(__file__).resolve().parent.parent
    app_path = repo_root / "app.py"
    
    if not app_path.exists():
        print("Error: app.py not found.")
        sys.exit(1)
        
    print("Starting eRTMAC-NWIS Application...")
    try:
        subprocess.run(["streamlit", "run", str(app_path)], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped.")
    except Exception as e:
        print(f"Failed to run app: {e}")

if __name__ == "__main__":
    main()
