import time
import asyncio
import logging
from typing import Optional, Callable, AsyncIterator, Iterator, List

from ertmac.streaming.schemas import SensorRecord, CausalStreamBuffer, StreamState, SCIENTIFIC_LABEL
from ertmac.streaming.sources import BaseSensorSource, VolveReplaySensorSource

logger = logging.getLogger("SensorStreamSimulator")

class SensorStreamSimulator:
    """
    Deterministic Replay Engine for Volve USROP Sensor Data.
    Features:
    - Replays real Parquet rows sequentially.
    - `--speed` multiplier scales wall-clock delay between frames while preserving
      historical source timestamps unchanged.
    - Zero future-data leakage guarantee (enforced via CausalStreamBuffer).
    - Maintains state per well (latest record, current MD, last timestamp, message count).
    - Standby/Pause support: Defaults to waiting for user's START command.
    """
    def __init__(
        self,
        source: Optional[BaseSensorSource] = None,
        max_buffer_span_m: float = 200.0,
        autostart: bool = False,
    ):
        self.source = source if source is not None else VolveReplaySensorSource()
        self.buffer = CausalStreamBuffer(max_depth_span_m=max_buffer_span_m)
        self.is_running = False
        self.is_paused = not autostart
        self.speed = 50.0
        self.active_well_id: Optional[str] = None
        self._pause_event: Optional[asyncio.Event] = None
        self._autostart = autostart

    @property
    def state(self) -> StreamState:
        return self.buffer.state

    def reset(self) -> None:
        self.buffer.clear()
        self.is_running = False

    def start_streaming(self, well_id: Optional[str] = None, speed: Optional[float] = None) -> None:
        """Starts or unpauses well digging."""
        if speed is not None:
            self.speed = speed
        if well_id:
            self.active_well_id = well_id
        self.is_paused = False
        if self._pause_event:
            self._pause_event.set()
        logger.info(f"[{SCIENTIFIC_LABEL}] Digging started for well '{self.active_well_id}' at {self.speed}x speed")

    def pause_streaming(self) -> None:
        """Pauses well digging without resetting depth."""
        self.is_paused = True
        if self._pause_event:
            self._pause_event.clear()
        logger.info(f"[{SCIENTIFIC_LABEL}] Digging paused for well '{self.active_well_id}'")

    def resume_streaming(self) -> None:
        """Resumes a paused drilling stream."""
        self.is_paused = False
        if self._pause_event:
            self._pause_event.set()
        logger.info(f"[{SCIENTIFIC_LABEL}] Digging resumed for well '{self.active_well_id}'")

    def stream_sync(
        self,
        well_id: str,
        speed: float = 1.0,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None,
        callback: Optional[Callable[[SensorRecord, StreamState], None]] = None
    ) -> Iterator[SensorRecord]:
        """
        Synchronous replay generator for scripts and test harnesses.
        """
        self.reset()
        self.is_running = True
        self.active_well_id = well_id
        self.speed = speed
        logger.info(
            f"[{SCIENTIFIC_LABEL}] Starting stream for well='{well_id}', "
            f"speed={speed}x, MD range=[{start_md}, {end_md}]"
        )

        records_iter = self.source.stream_records(well_id, start_md, end_md)
        base_step_delay = 0.5 / max(0.001, speed)  # Default pacing scaled by speed multiplier

        for record in records_iter:
            if not self.is_running:
                break

            self.buffer.append(record)
            if callback:
                callback(record, self.state)

            yield record

            if speed > 0 and base_step_delay >= 0.005:
                time.sleep(base_step_delay)

        self.is_running = False

    async def stream_async(
        self,
        well_id: str,
        speed: float = 1.0,
        start_md: Optional[float] = None,
        end_md: Optional[float] = None
    ) -> AsyncIterator[SensorRecord]:
        """
        Asynchronous replay generator for WebSocket server broadcasting.
        Respects is_paused state so it only digs when commanded by user.
        """
        self.reset()
        self.is_running = True
        self.active_well_id = well_id
        self.speed = speed
        self._pause_event = asyncio.Event()

        if not self.is_paused:
            self._pause_event.set()
            logger.info(f"[{SCIENTIFIC_LABEL}] Starting async stream for well='{well_id}', speed={speed}x")
        else:
            self._pause_event.clear()
            logger.info(
                f"[{SCIENTIFIC_LABEL}] Sensor stream initialized in STANDBY mode for well='{well_id}'. "
                f"Digging will begin when user clicks START."
            )

        records_iter = self.source.stream_records(well_id, start_md, end_md)

        for record in records_iter:
            if not self.is_running:
                break

            # If paused, wait for user to click START/RESUME
            while self.is_paused and self.is_running:
                await self._pause_event.wait()
                if not self.is_running:
                    break

            self.buffer.append(record)
            yield record

            effective_speed = max(0.001, self.speed)
            base_step_delay = 0.5 / effective_speed
            if effective_speed > 0 and base_step_delay >= 0.005:
                await asyncio.sleep(base_step_delay)

        self.is_running = False

    def stop(self) -> None:
        self.is_running = False
        if self._pause_event:
            self._pause_event.set()
