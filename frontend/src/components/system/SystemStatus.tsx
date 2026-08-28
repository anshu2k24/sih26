import React, { useState, useEffect } from "react";
import { Server, Radio, Cpu, Database, Monitor, CheckCircle, AlertTriangle } from "lucide-react";
import type { StreamConnectionStatus } from "../../types/sensor";
import type { MLStatusState } from "../../types/ml";

interface SystemStatusProps {
  streamStatus: StreamConnectionStatus;
  mlState: MLStatusState;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ streamStatus, mlState }) => {
  const [backendStatus, setBackendStatus] = useState<"CONNECTED" | "DISCONNECTED">("DISCONNECTED");

  useEffect(() => {
    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? setBackendStatus("CONNECTED") : setBackendStatus("DISCONNECTED")))
      .catch(() => setBackendStatus("DISCONNECTED"));
  }, []);

  const items = [
    {
      name: "Sensor Stream Simulator",
      url: "ws://localhost:8765",
      status: streamStatus === "LIVE" ? "CONNECTED" : "DISCONNECTED",
      icon: Radio,
    },
    {
      name: "FastAPI Orchestration Backend",
      url: "http://localhost:8000",
      status: backendStatus,
      icon: Server,
    },
    {
      name: "Application WebSocket Gateway",
      url: "/api/ws/wells/{well_id}",
      status: streamStatus === "LIVE" ? "CONNECTED" : "DISCONNECTED",
      icon: Radio,
    },
    {
      name: "ML Readiness Gate & Inference",
      url: "ertmac.ml.ingestion",
      status: mlState.is_blocked ? "NOT READY (GATE BLOCKED)" : "READY",
      icon: Cpu,
    },
    {
      name: "NWIS & DDR Intelligence API",
      url: "/api/wells/{well_id}/events",
      status: "READY",
      icon: Database,
    },
    {
      name: "React Frontend Console",
      url: "http://localhost:5173",
      status: "CONNECTED",
      icon: Monitor,
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        <Server className="w-4 h-4 text-indigo-400" />
        System Infrastructure & Health Status
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {items.map((item, idx) => {
          const IconComp = item.icon;
          const isOk = item.status === "CONNECTED" || item.status === "READY";
          return (
            <div
              key={idx}
              className="p-3.5 rounded-lg bg-slate-850/60 border border-slate-800 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  <IconComp className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-slate-200">{item.name}</div>
                  <div className="text-[11px] font-mono text-slate-400">{item.url}</div>
                </div>
              </div>

              <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold">
                {isOk ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> OK
                  </span>
                ) : (
                  <span className="text-amber-400 flex items-center gap-1" title={item.status}>
                    <AlertTriangle className="w-3.5 h-3.5" /> {item.status.split(" ")[0]}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
