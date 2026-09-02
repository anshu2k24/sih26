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
              {/* Eyebrow */}
              <p style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[11px] font-bold uppercase mb-1">
                NEARBY WELLS INTELLIGENCE SYSTEM
              </p>
              <h1 className="text-white font-bold text-xl tracking-tight leading-tight drop-shadow-sm">
                ML Risk &amp; Prediction Center
              </h1>
              <p className="mt-1 text-sm drop-shadow-sm" style={{ color: "rgba(255,255,255,0.7)" }}>
                Real-time causal feature engineering → Isolation Forest anomaly scoring → live alert dispatch
              </p>
              {/* Orange line */}
              <div
                style={{ width: "36px", height: "3px", background: orange, boxShadow: "0 0 12px rgba(255,138,31,0.5)", borderRadius: "10px", marginTop: "12px" }}
              />
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
