import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { LiveSensorCharts } from "../components/charts/LiveSensorCharts";
import { OperationalTimelineView } from "../components/timeline/OperationalTimelineView";
import { Radio } from "lucide-react";

export const LivePage: React.FC = () => {
  const { selectedWell, currentMd, status, samplesReceived, latestSensor, history } = useActiveWell();

  return (
    <div className="relative min-h-[calc(100vh-6rem)] -m-4 sm:-m-6 p-4 sm:p-6 overflow-hidden">
      {/* Background Image scoped only to this page */}
      <div
        className="absolute inset-0 z-0 bg-cover bg-no-repeat"
        style={{ 
          backgroundImage: 'url("/src/assets/hero.png")',
          backgroundPosition: 'center 65%',
          filter: 'brightness(1.15) contrast(1.1)'
        }}
      >
        <div 
          className="absolute inset-0 z-0" 
          style={{
            background: "linear-gradient(90deg, rgba(3, 8, 18, 0.60) 0%, rgba(3, 8, 18, 0.20) 40%, transparent 70%, transparent 100%)"
          }} 
        />
      </div>

      <div className="relative z-10 space-y-6 max-w-7xl mx-auto font-mono">
        {/* Top Banner */}
        <div 
          className="rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
          style={{
            background: "linear-gradient(145deg, rgba(20, 27, 42, 0.72), rgba(9, 14, 25, 0.60))",
            border: "1px solid rgba(255, 255, 255, 0.12)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            boxShadow: "0 25px 70px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)"
          }}
        >
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

      {/* 2-Column Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Sensor History Charts (Left Column, wider) */}
        <div className="xl:col-span-8">
          <LiveSensorCharts history={history} />
        </div>

        {/* Operational Shift Timeline (Right Column, narrower) */}
        <div className="xl:col-span-4">
          <OperationalTimelineView wellId={selectedWell} currentMd={currentMd} />
        </div>
      </div>
      </div>
    </div>
  );
};
