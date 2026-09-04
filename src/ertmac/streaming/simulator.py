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
        self._switch_event: Optional[asyncio.Event] = None
        self._autostart = autostart

    @property
    def state(self) -> StreamState:
        return self.buffer.state

    def reset(self) -> None:
        self.buffer.clear()
        self.is_running = False

    def start_streaming(self, well_id: Optional[str] = None, speed: Optional[float] = None) -> None:
        """Starts or unpauses well digging."""
        well_changed = False
        if speed is not None:
            self.speed = float(speed)
        if well_id and well_id != "N/A" and well_id != self.active_well_id:
            logger.info(f"[{SCIENTIFIC_LABEL}] Instant well switch: '{self.active_well_id}' -> '{well_id}'")
            self.active_well_id = well_id
            self.buffer.clear()
            well_changed = True

        self.is_running = True
        self.is_paused = False
        if self._pause_event:
            self._pause_event.set()
        if well_changed and self._switch_event:
            self._switch_event.set()
        logger.info(f"[{SCIENTIFIC_LABEL}] Digging started for well '{self.active_well_id}' at {self.speed}x speed")

    def pause_streaming(self) -> None:
        """Pauses well digging without resetting depth."""
        self.is_paused = True
        if self._pause_event:
            self._pause_event.clear()
        if self._switch_event:
            self._switch_event.set()
        logger.info(f"[{SCIENTIFIC_LABEL}] Digging paused for well '{self.active_well_id}'")

    def resume_streaming(self) -> None:
        """Resumes a paused drilling stream."""
        self.is_running = True
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
        end_md: Optional[float] = None,
        loop: bool = True
    ) -> AsyncIterator[SensorRecord]:
        """
        Asynchronous replay generator for WebSocket server broadcasting.
        Respects is_paused state so it only digs when commanded by user.
        Dynamically handles well switches cleanly and IMMEDIATELY in real-time.
        """
        self.reset()
        self.is_running = True
        self.active_well_id = well_id
        self.speed = speed
        self._pause_event = asyncio.Event()
        self._switch_event = asyncio.Event()

        if not self.is_paused:
            self._pause_event.set()
            logger.info(f"[{SCIENTIFIC_LABEL}] Starting async stream for well='{well_id}', speed={speed}x")
        else:
            self._pause_event.clear()
            logger.info(
                f"[{SCIENTIFIC_LABEL}] Sensor stream initialized in STANDBY mode for well='{well_id}'. "
                f"Digging will begin when user clicks START."
            )

        while self.is_running:
            current_well = self.active_well_id
            self.reset()
            self.is_running = True
            self.active_well_id = current_well
            self.state.well_id = current_well
            self._switch_event.clear()

            try:
                records_iter = iter(self.source.stream_records(current_well, start_md, end_md))
            except Exception as e:
                logger.error(f"Failed to stream records for well '{current_well}': {e}")
                for _ in range(10):
                    if not self.is_running or self.active_well_id != current_well:
                        break
                    await asyncio.sleep(0.1)
                continue

            for record in records_iter:
                if not self.is_running or self.active_well_id != current_well:
                    break

                # If paused, wait for user to click START/RESUME
                while self.is_paused and self.is_running and self.active_well_id == current_well:
                    await self._pause_event.wait()
                    if not self.is_running or self.active_well_id != current_well:
                        break

                if not self.is_running or self.active_well_id != current_well:
                    break

                self.buffer.append(record)
                yield record

                effective_speed = max(0.001, self.speed)
                base_step_delay = max(0.04, 1.0 / effective_speed)
                if effective_speed > 0 and base_step_delay >= 0.005:
                    try:
                        await asyncio.wait_for(self._switch_event.wait(), timeout=base_step_delay)
                        # Switch requested during sleep: break old well immediately
                        self._switch_event.clear()
                        break
                    except asyncio.TimeoutError:
                        pass

            # If finished all records for this well
            if self.active_well_id == current_well:
                if loop and end_md is None:
                    logger.info(f"[{SCIENTIFIC_LABEL}] Completed well '{current_well}' stream sequence. Continuous rewinding active.")
                    await asyncio.sleep(0.2)
                    continue
                else:
                    break

        self.is_running = False

    def stop(self) -> None:
        self.is_running = False
        if self._pause_event:
            self._pause_event.set()
