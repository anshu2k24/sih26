import { useState, useEffect, useRef, useCallback } from "react";
import type { SensorRecord, StreamConnectionStatus } from "../types/sensor";
import type { MLStatusState } from "../types/ml";
import type { WSEventMessage } from "../types/api";
import { fetchWellState, fetchSensorHistory } from "../services/api";
import { supabase } from "../lib/supabase";

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  (typeof window !== "undefined" && window.location.protocol === "https:"
    ? `wss://${window.location.host}`
    : "ws://localhost:8000");

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
    let isSubscribed = true;
    let isIntentionalClose = false;

    setStatus("CONNECTING");
    loadInitialState(selectedWell);

    const connectWebSocket = async () => {
      // Clear any pending reconnect timers
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }

      // Close existing socket cleanly without triggering error reconnect loop
      if (wsRef.current) {
        isIntentionalClose = true;
        wsRef.current.close(1000, "Switching well or refreshing session");
        wsRef.current = null;
      }

      const encodedWell = encodeURIComponent(selectedWell);
      let wsUrl = `${WS_BASE_URL}/api/ws/wells/${encodedWell}`;

      try {
        const { data } = await supabase.auth.getSession();
        if (data?.session?.access_token) {
          wsUrl += `?token=${encodeURIComponent(data.session.access_token)}`;
        } else if (import.meta.env.VITE_SUPABASE_URL) {
          // Waiting for user login
          if (isSubscribed) setStatus("STREAM DISCONNECTED");
          return;
        }
      } catch (err) {
        console.warn("[WebSocket] Could not retrieve Supabase session:", err);
      }

      if (!isSubscribed) return;

      isIntentionalClose = false;
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

      ws.onerror = () => {
        if (!isSubscribed) return;
        setStatus("STREAM DISCONNECTED");
      };

      ws.onclose = (event) => {
        if (!isSubscribed || isIntentionalClose) return;
        setStatus("STREAM DISCONNECTED");
        setMlState((prev) => ({
          ...prev,
          status: "ML_NOT_READY",
          is_blocked: true,
          gate_reason: "Application WebSocket disconnected.",
        }));

        // Only schedule reconnect if closed unexpectedly and still subscribed
        if (event.code !== 1000 && !reconnectTimerRef.current) {
          reconnectTimerRef.current = window.setTimeout(() => {
            reconnectTimerRef.current = null;
            if (isSubscribed) {
              connectWebSocket();
            }
          }, 3000);
        }
      };
    };

    connectWebSocket();

    return () => {
      isSubscribed = false;
      isIntentionalClose = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
        wsRef.current = null;
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
