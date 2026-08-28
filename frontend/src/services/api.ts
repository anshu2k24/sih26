import type { WellsResponse, WellItem } from "../types/api";
import type { WellStreamState, SensorRecord } from "../types/sensor";
import type { EventsResponse } from "../types/events";
import type { MLStatusState } from "../types/ml";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchWells(): Promise<WellItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/wells`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: WellsResponse = await res.json();
    return data.wells;
  } catch (err) {
    console.error("fetchWells error:", err);
    return [
      { well_id: "15/9-F-15", status: "available" },
      { well_id: "15/9-F-14", status: "available" },
      { well_id: "15/9-F-9 A", status: "available" }
    ];
  }
}

export async function fetchWellState(wellId: string): Promise<WellStreamState | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const res = await fetch(`${API_BASE_URL}/api/wells/${encodedWell}/state`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchWellState error:", err);
    return null;
  }
}

export async function fetchSensorHistory(wellId: string, cutoffMd?: number): Promise<SensorRecord[]> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    let url = `${API_BASE_URL}/api/wells/${encodedWell}/sensors/history`;
    if (cutoffMd !== undefined) {
      url += `?cutoff_md=${cutoffMd}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.records || [];
  } catch (err) {
    console.error("fetchSensorHistory error:", err);
    return [];
  }
}

export async function fetchOffsetEvents(
  wellId: string,
  currentMd: number = 3000.0,
  radius: number = 100.0
): Promise<EventsResponse | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const url = `${API_BASE_URL}/api/wells/${encodedWell}/events?current_md=${currentMd}&radius=${radius}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchOffsetEvents error:", err);
    return null;
  }
}

export async function fetchRiskStatus(wellId: string): Promise<MLStatusState | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const res = await fetch(`${API_BASE_URL}/api/wells/${encodedWell}/risk`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchRiskStatus error:", err);
    return null;
  }
}
