import asyncio
import json
import logging
from typing import Set, Optional, Any
import websockets

from ertmac.streaming.simulator import SensorStreamSimulator
from ertmac.streaming.schemas import SensorRecord, SCIENTIFIC_LABEL

logger = logging.getLogger("SensorWebSocketServer")

class SensorWebSocketServer:
    """
    WebSocket Server for Streaming Sensor Telemetry.
    Emits ONE JSON SensorRecord payload per WebSocket message.
    Handles client connection/disconnection cleanly without crashing simulator.
    """
    def __init__(self, simulator: SensorStreamSimulator, host: str = "localhost", port: int = 8765):
        self.simulator = simulator
        self.host = host
        self.port = port
        self.clients: Set[Any] = set()
        self.server = None

    async def register(self, websocket: Any) -> None:
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}. Total clients: {len(self.clients)}")
        # Send initial status banner
        welcome_msg = {
            "status": "CONNECTED",
            "stream_mode": "STREAMING" if not self.simulator.is_paused else "STANDBY",
            "is_streaming": not self.simulator.is_paused,
            "data_source_label": SCIENTIFIC_LABEL,
            "message": "Connected to Volve USROP Historical Replay Stream"
        }
        await websocket.send(json.dumps(welcome_msg))

    async def unregister(self, websocket: Any) -> None:
        self.clients.discard(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}. Remaining clients: {len(self.clients)}")

    async def broadcast_status(self, status_payload: dict) -> None:
        """Broadcasts a status update event to all connected WebSocket clients."""
        payload_str = json.dumps(status_payload)
        for client in list(self.clients):
            try:
                await client.send(payload_str)
            except Exception:
                pass

    async def ws_handler(self, websocket: Any, path: str = "/") -> None:
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    action = data.get("action")
                    if action == "start":
                        well_id = data.get("well_id")
                        speed = data.get("speed")
                        self.simulator.start_streaming(well_id=well_id, speed=speed)
                        await self.broadcast_status({
                            "type": "STREAM_STATUS",
                            "status": "STREAMING",
                            "is_streaming": True,
                            "well_id": well_id or self.simulator.active_well_id
                        })
                    elif action == "pause":
                        self.simulator.pause_streaming()
                        await self.broadcast_status({
                            "type": "STREAM_STATUS",
                            "status": "PAUSED",
                            "is_streaming": False,
                            "well_id": self.simulator.active_well_id
                        })
                    elif action == "resume":
                        self.simulator.resume_streaming()
                        await self.broadcast_status({
                            "type": "STREAM_STATUS",
                            "status": "STREAMING",
                            "is_streaming": True,
                            "well_id": self.simulator.active_well_id
                        })
                    elif action == "get_state":
                        state = self.simulator.state
                        resp = {
                            "well_id": state.well_id,
                            "current_md": state.current_md,
                            "last_timestamp": state.last_timestamp,
                            "emitted_count": state.emitted_count,
                            "is_streaming": not self.simulator.is_paused,
                            "data_label": SCIENTIFIC_LABEL
                        }
                        await websocket.send(json.dumps(resp))
                except Exception as ex:
                    logger.error(f"Error handling WebSocket client action: {ex}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def broadcast_record(self, record: SensorRecord) -> None:
        if not self.clients:
            return
        
        payload_str = json.dumps(record.to_dict())
        # Broadcast to all connected clients
        disconnected = set()
        for client in list(self.clients):
            try:
                await client.send(payload_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client.remote_address}: {e}")
                disconnected.add(client)

        for client in disconnected:
            self.clients.discard(client)

    async def run_stream(
        self,
        well_id: str,
        speed: float = 1.0,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> None:
        """
        Runs async stream generator from simulator and broadcasts each record via WebSocket.
        """
        self.simulator.start_streaming(well_id=well_id, speed=speed)
        async for record in self.simulator.stream_async(
            well_id=well_id, speed=speed, start_md=start_md, end_md=end_md
        ):
            await self.broadcast_record(record)

    async def start(self) -> None:
        self.server = await websockets.serve(self.ws_handler, self.host, self.port, ping_interval=20.0, ping_timeout=20.0)
        logger.info(f"Sensor WebSocket Server running on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        if self.clients:
            for ws in list(self.clients):
                try:
                    await ws.close()
                except Exception:
                    pass
            self.clients.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Sensor WebSocket Server stopped.")
