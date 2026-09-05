import { useState, useEffect, useRef, useCallback } from "react";
import type { SensorRecord, StreamConnectionStatus } from "../types/sensor";
import type { MLStatusState } from "../types/ml";
import type { WSEventMessage } from "../types/api";
import { fetchWellState, fetchSensorHistory, startStreamApi, pauseStreamApi } from "../services/api";
import { supabase } from "../lib/supabase";

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  (typeof window !== "undefined"
    ? (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? "ws://localhost:8000"
        : "wss://ertmac-backend.onrender.com")
    : "ws://localhost:8000");

const MAX_HISTORY = 2000;

export function useSensorStream(selectedWell: string) {
  const [status, setStatus] = useState<StreamConnectionStatus>("STREAM DISCONNECTED");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
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
  // Tracks whether the user explicitly paused — prevents loadInitialState race from overwriting it
  const userPausedRef = useRef<boolean>(false);

  // Fetch initial REST state and history on well change (no streaming status — that comes from WS onopen)
  const loadInitialState = useCallback(async (wellId: string) => {
    const initialState = await fetchWellState(wellId);
    if (initialState && initialState.well_id === wellId) {
      setCurrentMd(initialState.current_md);
      setTvd(initialState.tvd || null);
      setLastTimestamp(initialState.last_timestamp || "N/A");
      setSamplesReceived(initialState.samples_received);
      setLatestSensor(initialState.latest_sensor);
      if (initialState.ml) {
        setMlState(initialState.ml);
      }
    }

    // NOTE: fetchStreamStatusApi is intentionally NOT called here.
    // isStreaming is driven exclusively by ws.onopen (start) and pauseStream() (pause).
    // Calling fetchStreamStatusApi here creates a race condition that overwrites user-initiated pauses.

    const initialHistory = await fetchSensorHistory(wellId);
    if (initialHistory && initialHistory.length > 0 && (!initialHistory[0].well_id || initialHistory[0].well_id === wellId)) {
      setHistory(initialHistory);
    } else {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    let isSubscribed = true;
    let isIntentionalClose = false;

    setStatus("CONNECTING");
    setIsStreaming(false);  // Reset on every well change — ws.onopen will set it back to true
    userPausedRef.current = false; // Reset intentional-pause protection on well change
    sessionStorage.removeItem('ertmac_stream_paused'); // Clear persisted pause on well switch (new well auto-starts)
    // Immediately clear telemetry from previous well for instant, clean transition
    setHistory([]);
    setLatestSensor(null);
    setCurrentMd(0);
    setTvd(null);
    setSamplesReceived(0);
    setLastTimestamp("N/A");
    setMlState({
      status: "ML_NOT_READY",
      is_blocked: true,
      gate_reason: `Initializing stream listener for ${selectedWell}...`,
      risk_score: null,
      features_constructed: 0,
    });

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
        let session = (await supabase.auth.getSession()).data.session;
        if (!session?.access_token && import.meta.env.VITE_SUPABASE_URL) {
          const refreshed = await supabase.auth.refreshSession();
          session = refreshed.data?.session || null;
        }
        if (session?.access_token) {
          wsUrl += `?token=${encodeURIComponent(session.access_token)}`;
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
        // Don't auto-start if the user explicitly paused (survives page refresh via sessionStorage)
        const isPersistentlyPaused = sessionStorage.getItem('ertmac_stream_paused') === '1';
        if (userPausedRef.current || isPersistentlyPaused) {
          setStatus("LIVE");
          setIsStreaming(false);
          return;
        }
        console.log(`[WebSocket] Connected for well '${selectedWell}'`);
        setStatus("LIVE");
        // Auto-start stream immediately on connect — no button click required
        startStreamApi(selectedWell).then((ok) => {
          if (ok && isSubscribed && !userPausedRef.current) setIsStreaming(true);
        }).catch(() => {});
      };

      ws.onmessage = (event) => {
        if (!isSubscribed) return;
        try {
          const msg: WSEventMessage = JSON.parse(event.data);

          if (msg.type === "sensor_update" && msg.data) {
            const rec: SensorRecord = msg.data;
            // Ignore residual packets from prior wells
            if (rec.well_id && rec.well_id !== selectedWell) {
              return;
            }

            setLatestSensor(rec);
            setCurrentMd(rec.md);
            if (rec.tvd !== undefined) setTvd(rec.tvd);
            if (rec.timestamp) setLastTimestamp(rec.timestamp);

            setSamplesReceived((prev) => prev + 1);

            // Append strictly emitted record to history
            setHistory((prev) => {
              if (prev.length > 0 && prev[0].well_id && prev[0].well_id !== rec.well_id) {
                return [rec];
              }
              if (prev.length > 0 && rec.md < prev[prev.length - 1].md) {
                return [rec];
              }
              const updated = [...prev, rec];
              return updated.length > MAX_HISTORY ? updated.slice(updated.length - MAX_HISTORY) : updated;
            });
          } else if (msg.type === "ml_update" && msg.data) {
            setMlState(msg.data);
          } else if (msg.type === "alert_created" && msg.data) {
            // Dispatch custom DOM event so AlertsPage prepends the card
            window.dispatchEvent(new CustomEvent("ertmac:alert_created", { detail: msg.data }));
            // Dispatch toast event for global notification
            window.dispatchEvent(new CustomEvent("ertmac:toast", {
              detail: {
                severity: msg.data.severity,
                title: msg.data.title,
                description: `Well ${msg.data.well_id} @ MD ${msg.data.current_md?.toFixed(1)}m`,
              }
            }));
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
          reconnectTimerRef.current = window.setTimeout(async () => {
            reconnectTimerRef.current = null;
            if (isSubscribed) {
              try {
                await supabase.auth.refreshSession();
              } catch {
                // Non-blocking
              }
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

  const startStream = useCallback(async (wellId?: string, speed?: number) => {
    const targetWell = wellId || selectedWell;
    userPausedRef.current = false; // User explicitly starting — clear pause protection
    sessionStorage.removeItem('ertmac_stream_paused'); // Clear persisted pause
    setIsStreaming(true);
    const ok = await startStreamApi(targetWell, speed);
    if (!ok) {
      setIsStreaming(false);
    }
    return ok;
  }, [selectedWell]);

  const pauseStream = useCallback(async () => {
    userPausedRef.current = true; // User explicitly paused — protect from being overwritten
    sessionStorage.setItem('ertmac_stream_paused', '1'); // Persist across page refresh
    setIsStreaming(false);
    const ok = await pauseStreamApi();
    if (!ok) {
      userPausedRef.current = false;
      sessionStorage.removeItem('ertmac_stream_paused');
      setIsStreaming(true);
    }
    return ok;
  }, []);

  return {
    status,
    isStreaming,
    startStream,
    pauseStream,
    currentMd,
    tvd,
    lastTimestamp,
    samplesReceived,
    latestSensor,
    history,
    mlState,
  };
}
