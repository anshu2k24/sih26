import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { LiveSensorCharts } from "../components/charts/LiveSensorCharts";
import { OperationalTimelineView } from "../components/timeline/OperationalTimelineView";
import { Radio } from "lucide-react";

export const LivePage: React.FC = () => {
  const { selectedWell, currentMd, status, samplesReceived, latestSensor, history } = useActiveWell();

  return (
    <div className="space-y-6 font-mono">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Radio className="w-5 h-5 text-emerald-400 animate-pulse" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              REAL-TIME TELEMETRY CONSOLE
            </h1>
            <span className={`text-xs px-2.5 py-0.5 rounded font-bold border ${
              status === "LIVE" ? "bg-emerald-950/80 text-emerald-400 border-emerald-500/40" : "bg-rose-950/80 text-rose-400 border-rose-500/40"
            }`}>
              {status === "LIVE" ? "🟢 STREAM LIVE" : "🔴 DISCONNECTED"}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time Equinor Volve USROP sensor stream. Samples Received: <strong>{samplesReceived.toLocaleString()}</strong> | MD: <strong>{currentMd.toFixed(1)} m</strong>
          </p>
        </div>
      </div>

      {/* Sensor Cards */}
      <TelemetryCards latestSensor={latestSensor} />

      {/* Sensor History Charts */}
      <LiveSensorCharts history={history} />

      {/* Operational Shift Timeline */}
      <OperationalTimelineView wellId={selectedWell} currentMd={currentMd} />
    </div>
  );
};
