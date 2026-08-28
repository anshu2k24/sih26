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
    """
    def __init__(self, source: Optional[BaseSensorSource] = None, max_buffer_span_m: float = 200.0):
        self.source = source if source is not None else VolveReplaySensorSource()
        self.buffer = CausalStreamBuffer(max_depth_span_m=max_buffer_span_m)
        self.is_running = False

    @property
    def state(self) -> StreamState:
        return self.buffer.state

    def reset(self) -> None:
        self.buffer.clear()
        self.is_running = False

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
        """
        self.reset()
        self.is_running = True
        logger.info(
            f"[{SCIENTIFIC_LABEL}] Starting async stream for well='{well_id}', "
            f"speed={speed}x, MD range=[{start_md}, {end_md}]"
        )

        records_iter = self.source.stream_records(well_id, start_md, end_md)
        base_step_delay = 0.5 / max(0.001, speed)

        for record in records_iter:
            if not self.is_running:
                break

            self.buffer.append(record)
            yield record

            if speed > 0 and base_step_delay >= 0.005:
                await asyncio.sleep(base_step_delay)

        self.is_running = False

    def stop(self) -> None:
        self.is_running = False
