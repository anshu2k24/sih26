import type { MLStatusState } from "./ml";

export interface SensorRecord {
  well_id: string;
  timestamp: string;
  md: number;
  tvd?: number | null;
  rop?: number | null;
  wob?: number | null;
  rpm?: number | null;
  torque?: number | null;
  hookload?: number | null;
  spp?: number | null;
  flow_in?: number | null;
  mud_density?: number | null;
}

export type StreamConnectionStatus = "LIVE" | "STREAM DISCONNECTED" | "CONNECTING";

export interface WellStreamState {
  well_id: string;
  stream_status: StreamConnectionStatus;
  data_source: string;
  current_md: number;
  tvd?: number | null;
  last_timestamp: string;
  samples_received: number;
  latest_sensor: SensorRecord | null;
  ml: MLStatusState;
}
