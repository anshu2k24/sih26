import React, { useState } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { LiveSensorCharts } from "../components/charts/LiveSensorCharts";
import { OperationalTimelineView } from "../components/timeline/OperationalTimelineView";
import { Radio, Play, Pause } from "lucide-react";

export const LivePage: React.FC = () => {
  const {
    selectedWell,
    currentMd,
    status,
    isStreaming,
    startStream,
    pauseStream,
    samplesReceived,
    latestSensor,
    history,
  } = useActiveWell();

  const [speedMultiplier, setSpeedMultiplier] = useState<number>(50);
  const [isTriggering, setIsTriggering] = useState<boolean>(false);

  const handleToggleStream = async () => {
    setIsTriggering(true);
    try {
      if (isStreaming) {
        await pauseStream();
      } else {
        await startStream(selectedWell, speedMultiplier);
      }
    } finally {
      setIsTriggering(false);
    }
  };

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
        {/* Top Header - Transparent */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
          <div>
            <div className="flex items-center gap-3">
              <Radio className={`w-5 h-5 ${isStreaming ? "text-[#FF7A00] animate-pulse" : "text-slate-500"}`} />
              <h1 className="text-lg font-bold text-white uppercase tracking-wider">
                REAL-TIME TELEMETRY CONSOLE
              </h1>
              <span className={`text-xs px-2.5 py-0.5 rounded font-bold border ${
                isStreaming
                  ? "bg-[#FF7A00]/20 text-[#FF7A00] border-[#FF7A00]/40 animate-pulse"
                  : "bg-amber-950/60 text-amber-400 border-amber-500/30"
              }`}>
                {isStreaming ? "🟢 DRILLING ACTIVE" : "⏸️ STANDBY (CLICK START)"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Active Well: <strong className="text-white">{selectedWell}</strong> | Samples Received: <strong>{samplesReceived.toLocaleString()}</strong> | MD: <strong>{currentMd.toFixed(1)} m</strong>
            </p>
          </div>

          {/* Interactive Stream Controller Bar */}
          <div className="flex items-center gap-3 self-start md:self-auto">
            {/* Speed Multiplier Quick Buttons */}
            <div className="flex items-center gap-1 bg-black/60 border border-white/10 px-2.5 py-1.5 rounded-[12px] text-[11px]">
              <span className="text-slate-400 text-[10px] uppercase font-bold mr-1">SPEED:</span>
              {[10, 50, 100].map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setSpeedMultiplier(s);
                    if (isStreaming) startStream(selectedWell, s);
                  }}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-all ${
                    speedMultiplier === s
                      ? "bg-[#FF7A00] text-black shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>

            {/* Primary START / PAUSE Drilling Button */}
            <button
              onClick={handleToggleStream}
              disabled={isTriggering}
              className="px-5 py-2.5 rounded-[12px] font-bold text-xs uppercase tracking-wider flex items-center gap-2 cursor-pointer transition-all shadow-lg active:scale-95 disabled:opacity-50"
              style={
                isStreaming
                  ? {
                      background: "rgba(239, 68, 68, 0.2)",
                      border: "1px solid rgba(239, 68, 68, 0.4)",
                      color: "#FCA5A5",
                    }
                  : {
                      background: "linear-gradient(145deg, #FF7A00, #FF5A00)",
                      boxShadow: "0 0 20px rgba(255,122,0,0.45)",
                      color: "#FFFFFF",
                      border: "none",
                    }
              }
            >
              {isStreaming ? (
                <>
                  <Pause className="w-4 h-4 fill-current" />
                  <span>PAUSE DRILLING</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>START DRILLING</span>
                </>
              )}
            </button>
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
