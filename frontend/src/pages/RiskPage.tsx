import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { RiskCenter } from "../components/risk/RiskCenter";
import { Activity, Brain, Radio } from "lucide-react";

export const RiskPage: React.FC = () => {
  const { mlState, selectedWell, latestSensor, currentMd } = useActiveWell();
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;

  const orange = "#ff8a1f";
  const orangeLight = "#ff9b4a";

  return (
    <div 
      className="min-h-screen relative pb-12"
      style={{ 
        backgroundColor: "#050505", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed"
      }}
    >
      <div className="relative z-10 p-6 space-y-6">
        {/* ── Header banner ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2">
          <div className="flex items-start gap-4">
            <div>
              {/* Header Title */}
              <h1 className="text-white font-bold text-3xl tracking-tight leading-tight drop-shadow-sm">
                ML Risk &amp; Prediction Center
              </h1>

            </div>
          </div>

          {/* Status pill */}
          <div
            style={{
              background: isAnomaly ? "rgba(244,63,94,0.12)" : isActive ? "rgba(16,185,129,0.10)" : "rgba(255,138,31,0.10)",
              border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.35)" : isActive ? "rgba(16,185,129,0.3)" : "rgba(255,138,31,0.25)"}`,
              color: isAnomaly ? "#f43f5e" : isActive ? "#10b981" : orangeLight,
              backdropFilter: "blur(8px)"
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold font-mono whitespace-nowrap shadow-lg"
          >
            {isActive ? (
              <><Radio className="w-3.5 h-3.5 animate-pulse" />{isAnomaly ? "⚠ ANOMALY ACTIVE" : "✓ MODEL LIVE"}</>
            ) : (
              <><Activity className="w-3.5 h-3.5 animate-pulse" />WARMING UP — {selectedWell}</>
            )}
          </div>
        </div>

        {/* ── Risk Center ── */}
        <RiskCenter mlState={mlState} latestSensor={latestSensor} currentMd={currentMd} />
      </div>
    </div>
  );
};
