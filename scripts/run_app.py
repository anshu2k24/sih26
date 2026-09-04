#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
FRONTEND_DIR = REPO_ROOT / "frontend"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from ertmac.streaming import SCIENTIFIC_LABEL

def get_env():
    env = dict(os.environ)
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{SRC_DIR}{os.pathsep}{existing_pp}" if existing_pp else str(SRC_DIR)
    return env

def main():
    parser = argparse.ArgumentParser(description=f"SIH 2026 PS121 Application Stack Launcher — {SCIENTIFIC_LABEL}")
    parser.add_argument("--well", type=str, default="15/9-F-15", help="Well ID to stream (default: 15/9-F-15)")
    parser.add_argument("--speed", type=float, default=50.0, help="Replay speed multiplier (default: 50.0x)")
    parser.add_argument("--autostart", action="store_true", default=True, help="Start drilling immediately on boot (default: True)")
    parser.add_argument("--backend-only", action="store_true", help="Launch FastAPI backend only")
    parser.add_argument("--stream-only", action="store_true", help="Launch sensor stream simulator only")
    parser.add_argument("--frontend-only", action="store_true", help="Launch React frontend only")
    args = parser.parse_args()

    python_bin = sys.executable
    env = get_env()

    print(f"=== SIH 2026 PS121 — eRTMAC-NWIS Application Stack ===")
    print(f"Scientific Label: {SCIENTIFIC_LABEL}")

    cmd_stream = [python_bin, "scripts/run_sensor_stream.py", "--well", args.well, "--speed", str(args.speed), "--autostart"]

    if args.stream_only:
        print(f"Starting Sensor Stream Simulator for well '{args.well}' (autostart={args.autostart})...")
        subprocess.run(cmd_stream, cwd=REPO_ROOT, env=env)
        return

    if args.backend_only:
        print("Starting FastAPI Orchestration Backend on http://localhost:8000 ...")
        cmd = [python_bin, "-m", "uvicorn", "ertmac.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        subprocess.run(cmd, cwd=REPO_ROOT, env=env)
        return

    if args.frontend_only:
        print("Starting React + Vite Frontend on http://localhost:5173 ...")
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        cmd = [npm_cmd, "run", "dev"]
        subprocess.run(cmd, cwd=FRONTEND_DIR)
        return

    print(f"\n[1/3] Starting Sensor Stream Simulator on ws://localhost:8765 (Standby mode, wait for user START)...")
    p_stream = subprocess.Popen(
        cmd_stream,
        cwd=REPO_ROOT,
        env=env
    )

    print("[2/3] Starting FastAPI Orchestration Backend on http://localhost:8000 (Hot Reloading src/)...")
    p_backend = subprocess.Popen(
        [
            python_bin, "-m", "uvicorn", "ertmac.api.server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--reload-dir", str(SRC_DIR),
        ],
        cwd=REPO_ROOT,
        env=env
    )

    print("[3/3] Starting React + Vite Frontend Console on http://localhost:5173 (Hot Module Replacement)...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    p_frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR
    )

    print("\n=== PS121 Application Stack Running with Nodemon-style Hot Reloading! ===")
    print("  - React Operational Console: http://localhost:5173")
    print("  - FastAPI OpenAPI Docs     : http://localhost:8000/docs")
    print("  - Sensor WebSocket Stream  : ws://localhost:8765")
    print("  - Application WebSocket GW : ws://localhost:8000/api/ws/wells/15/9-F-14")
    print("  - Backend Auto-Reload      : Active on src/ (Nodemon style)")
    print("  - Frontend HMR             : Active via Vite\n")
    print("Press Ctrl+C to terminate all services.\n")

    try:
        while True:
            time.sleep(1)
            # Auto-restart backend if unexpectedly exited
            if p_backend.poll() is not None:
                print("\n[Supervisor] Backend process exited. Auto-restarting FastAPI backend...")
                p_backend = subprocess.Popen(
                    [
                        python_bin, "-m", "uvicorn", "ertmac.api.server:app",
                        "--host", "0.0.0.0",
                        "--port", "8000",
                        "--reload",
                        "--reload-dir", str(SRC_DIR),
                    ],
                    cwd=REPO_ROOT,
                    env=env
                )

            # Auto-restart sensor stream if unexpectedly exited
            if p_stream.poll() is not None:
                print("\n[Supervisor] Stream simulator exited. Auto-restarting stream...")
                p_stream = subprocess.Popen(
                    cmd_stream,
                    cwd=REPO_ROOT,
                    env=env
                )

            # Check frontend process
            if p_frontend.poll() is not None:
                print("\n[Supervisor] Frontend process exited. Auto-restarting Vite dev server...")
                p_frontend = subprocess.Popen(
                    [npm_cmd, "run", "dev"],
                    cwd=FRONTEND_DIR
                )

    except KeyboardInterrupt:
        print("\nShutting down PS121 Application Stack gracefully...")
        for p in [p_frontend, p_backend, p_stream]:
            try:
                p.terminate()
            except Exception:
                pass
        sys.exit(0)

if __name__ == "__main__":
    main()
