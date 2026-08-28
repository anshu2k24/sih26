import { useState, useEffect, useRef, useCallback } from "react";
import type { SensorRecord, StreamConnectionStatus } from "../types/sensor";
import type { MLStatusState } from "../types/ml";
import type { WSEventMessage } from "../types/api";
import { fetchWellState, fetchSensorHistory } from "../services/api";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";
const MAX_HISTORY = 2000;

export function useSensorStream(selectedWell: string) {
  const [status, setStatus] = useState<StreamConnectionStatus>("STREAM DISCONNECTED");
  const [currentMd, setCurrentMd] = useState<number>(0);
  const [tvd, setTvd] = useState<number | null>(null);
  const [lastTimestamp, setLastTimestamp] = useState<string>("N/A");
  const [samplesReceived, setSamplesReceived] = useState<number>(0);
  const [latestSensor, setLatestSensor] = useState<SensorRecord | null>(null);
  const [history, setHistory] = useState<SensorRecord[]>([]);
  const [mlState, setMlState] = useState<MLStatusState>({
    status: "ML_NOT_READY",
    is_blocked: true,
    gate_reason: "Initializing stream listener...",
    risk_score: null,
    features_constructed: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  // Fetch initial REST state and history on well change
  const loadInitialState = useCallback(async (wellId: string) => {
    const initialState = await fetchWellState(wellId);
    if (initialState) {
      setCurrentMd(initialState.current_md);
      setTvd(initialState.tvd || null);
      setLastTimestamp(initialState.last_timestamp || "N/A");
      setSamplesReceived(initialState.samples_received);
      setLatestSensor(initialState.latest_sensor);
      if (initialState.ml) {
        setMlState(initialState.ml);
      }
    }

    const initialHistory = await fetchSensorHistory(wellId);
    if (initialHistory && initialHistory.length > 0) {
      setHistory(initialHistory);
    } else {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    // 1. Reset state on well change
    setStatus("CONNECTING");
    setCurrentMd(0);
    setTvd(null);
    setLastTimestamp("N/A");
    setSamplesReceived(0);
    setLatestSensor(null);
    setHistory([]);

    loadInitialState(selectedWell);

    let isSubscribed = true;

    const connectWebSocket = () => {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const encodedWell = encodeURIComponent(selectedWell);
      const wsUrl = `${WS_BASE_URL}/api/ws/wells/${encodedWell}`;
      console.log(`[WebSocket] Connecting to ${wsUrl}...`);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isSubscribed) return;
        console.log(`[WebSocket] Connected for well '${selectedWell}'`);
        setStatus("LIVE");
      };

      ws.onmessage = (event) => {
        if (!isSubscribed) return;
        try {
          const msg: WSEventMessage = JSON.parse(event.data);

          if (msg.type === "sensor_update" && msg.data) {
            const rec: SensorRecord = msg.data;
            setLatestSensor(rec);
            setCurrentMd(rec.md);
            if (rec.tvd !== undefined) setTvd(rec.tvd);
            if (rec.timestamp) setLastTimestamp(rec.timestamp);

            setSamplesReceived((prev) => prev + 1);

            // Append strictly emitted record to history
            setHistory((prev) => {
              // Reset history if well reset or regressive stream position
              if (prev.length > 0 && rec.md < prev[prev.length - 1].md) {
                return [rec];
              }
              const updated = [...prev, rec];
              return updated.length > MAX_HISTORY ? updated.slice(updated.length - MAX_HISTORY) : updated;
            });
          } else if (msg.type === "ml_update" && msg.data) {
            setMlState(msg.data);
          } else if (msg.type === "stream_status" && msg.data) {
            if (msg.data.status === "LIVE") {
              setStatus("LIVE");
            }
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      ws.onerror = (err) => {
        if (!isSubscribed) return;
        console.warn("[WebSocket] Error encountered:", err);
        setStatus("STREAM DISCONNECTED");
      };

      ws.onclose = () => {
        if (!isSubscribed) return;
        console.warn("[WebSocket] Connection closed. Attempting reconnect in 1.5s...");
        setStatus("STREAM DISCONNECTED");
        setMlState((prev) => ({
          ...prev,
          status: "ML_NOT_READY",
          is_blocked: true,
          gate_reason: "Application WebSocket disconnected.",
        }));

        reconnectTimerRef.current = window.setTimeout(() => {
          if (isSubscribed) {
            connectWebSocket();
          }
        }, 1500);
      };
    };

    connectWebSocket();

    return () => {
      isSubscribed = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [selectedWell, loadInitialState]);

  return {
    status,
    currentMd,
    tvd,
    lastTimestamp,
    samplesReceived,
    latestSensor,
    history,
    mlState,
  };
}
