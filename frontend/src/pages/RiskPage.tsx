import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { RiskCenter } from "../components/risk/RiskCenter";
import { Activity, Brain, Radio } from "lucide-react";

export const RiskPage: React.FC = () => {
  const { mlState, selectedWell } = useActiveWell();
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;

  const orange = "#ff8a1f";
  const orangeLight = "#ff9b4a";

  return (
    <div className="space-y-6">
      {/* ── Header banner (login-inspired) ── */}
      <div
        style={{
          background: "linear-gradient(145deg, rgba(20,27,42,0.72), rgba(9,14,25,0.60))",
          border: "1px solid rgba(255,255,255,0.10)",
          backdropFilter: "blur(18px)",
          WebkitBackdropFilter: "blur(18px)",
          boxShadow: "0 25px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
        }}
        className="rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div className="flex items-start gap-4">
          {/* Orange glow icon — login brand dot style */}
          <div
            style={{ background: "linear-gradient(135deg, #ff9b2f, #ff7a18)", boxShadow: "0 8px 25px rgba(255,122,24,0.35)" }}
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
          >
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            {/* Eyebrow — same as .eyebrow in Login.css */}
            <p style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[11px] font-bold uppercase mb-1">
              NEARBY WELLS INTELLIGENCE SYSTEM
            </p>
            <h1 className="text-white font-bold text-xl tracking-tight leading-tight">
              ML Risk &amp; Prediction Center
            </h1>
            <p className="mt-1 text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
              Real-time causal feature engineering → Isolation Forest anomaly scoring → live alert dispatch
            </p>
            {/* Orange line — login design */}
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
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold font-mono whitespace-nowrap"
        >
          {isActive ? (
            <><Radio className="w-3.5 h-3.5 animate-pulse" />{isAnomaly ? "⚠ ANOMALY ACTIVE" : "✓ MODEL LIVE"}</>
          ) : (
            <><Activity className="w-3.5 h-3.5 animate-pulse" />WARMING UP — {selectedWell}</>
          )}
        </div>
      </div>

      {/* ── Risk Center ── */}
      <RiskCenter mlState={mlState} />
    </div>
  );
};
