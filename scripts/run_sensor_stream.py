#!/usr/bin/env python3
import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path

# Ensure src directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ertmac.streaming import (
    VolveReplaySensorSource,
    SensorStreamSimulator,
    SensorWebSocketServer,
    SCIENTIFIC_LABEL
)
from ertmac.ml.streaming_adapter import StreamInferenceAdapter
from ertmac.ml.inference import load_production_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_sensor_stream")


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Sensor Streaming Layer CLI — {SCIENTIFIC_LABEL}"
    )
    parser.add_argument(
        "--well",
        type=str,
        default="15/9-F-15",
        help="Well ID to stream (e.g. 15/9-F-15, 15/9-F-14, 15/9-F-9 A)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=50.0,
        help="Replay speed multiplier (wall-clock delay scaling factor)"
    )
    parser.add_argument(
        "--start-md",
        type=float,
        default=None,
        help="Optional start Measured Depth (MD) cutoff in meters"
    )
    parser.add_argument(
        "--end-md",
        type=float,
        default=None,
        help="Optional end Measured Depth (MD) cutoff in meters"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="WebSocket server host binding (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port binding (default: 8765)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run replay simulation synchronously and print records to console without WebSocket server"
    )
    parser.add_argument(
        "--inference",
        action="store_true",
        help="Invoke StreamInferenceAdapter on each stream step to connect buffer to existing ML architecture"
    )
    parser.add_argument(
        "--autostart",
        action="store_true",
        default=False,
        help="Start stream digging immediately (default: False, wait for START button)"
    )
    parser.add_argument(
        "--list-wells",
        action="store_true",
        help="List all available wells in the source dataset and exit"
    )
    return parser.parse_args()


async def run_async_server(args, source, adapter=None):
    simulator = SensorStreamSimulator(source=source, autostart=args.autostart)
    server = SensorWebSocketServer(simulator=simulator, host=args.host, port=args.port)

    await server.start()
    logger.info(f"[{SCIENTIFIC_LABEL}] Sensor stream initialized for well '{args.well}' (autostart={args.autostart})")
    logger.info(f"WebSocket endpoint: ws://{args.host}:{args.port}")

    try:
        async for record in simulator.stream_async(
            well_id=args.well,
            speed=args.speed,
            start_md=args.start_md,
            end_md=args.end_md
        ):
            await server.broadcast_record(record)
            if adapter:
                inf_result = adapter.process_causal_position(simulator.buffer)
                if simulator.state.emitted_count % 100 == 0:
                    logger.info(
                        f"[ML ADAPTER] status={inf_result['status']} | "
                        f"is_blocked={inf_result['is_blocked']} | "
                        f"gate_reason='{inf_result['gate_reason']}' | "
                        f"features_built={len(inf_result.get('features', {}))}"
                    )
        logger.info(
            f"Replay complete! Total messages emitted: {simulator.state.emitted_count}. "
            f"Final MD: {simulator.state.current_md}m."
        )
    except KeyboardInterrupt:
        logger.info("Stream interrupted by user.")
    finally:
        await server.stop()


def main():
    args = parse_args()
    logger.info(f"=== {SCIENTIFIC_LABEL} ===")

    try:
        source = VolveReplaySensorSource()
    except Exception as e:
        logger.error(f"Failed to load Volve replay source: {e}")
        sys.exit(1)

    available_wells = source.get_available_wells()

    if args.list_wells:
        print("\nAvailable Volve Wells:")
        for w in available_wells:
            print(f"  - {w}")
        sys.exit(0)

    if args.well not in available_wells:
        logger.error(f"Invalid well ID '{args.well}'. Available wells: {available_wells}")
        sys.exit(1)

    if args.inference:
        try:
            model = load_production_model('models/volve_research_v1.joblib')
            adapter = StreamInferenceAdapter(model=model)
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            sys.exit(1)
    else:
        adapter = None

    if args.dry_run:
        logger.info(f"Running DRY RUN for well '{args.well}' at {args.speed}x speed...")
        simulator = SensorStreamSimulator(source=source)
        count = 0
        for record in simulator.stream_sync(
            well_id=args.well,
            speed=args.speed,
            start_md=args.start_md,
            end_md=args.end_md
        ):
            count += 1
            if args.inference:
                inf_res = adapter.process_causal_position(simulator.buffer)
                if count <= 3 or count % 200 == 0:
                    print(
                        f"[{count:05d}] {record.well_id} @ MD {record.md:.2f}m | "
                        f"ML Status: {inf_res['status']} (is_blocked={inf_res['is_blocked']}) | "
                        f"Gate Reason: '{inf_res['gate_reason']}' | "
                        f"Features Built: {len(inf_res.get('features', {}))}"
                    )
            else:
                if count <= 3 or count % 500 == 0:
                    print(f"[{count:05d}] {json.dumps(record.to_dict())}")

        print(f"\nDry Run Complete. Total records replayed: {count}. Final MD: {simulator.state.current_md}m.")
        sys.exit(0)

    # Async WebSocket mode
    try:
        asyncio.run(run_async_server(args, source, adapter))
    except KeyboardInterrupt:
        logger.info("Exiting on Ctrl+C")


if __name__ == "__main__":
    main()
