import React, { useEffect, useRef } from "react";
import type { MLStatusState } from "../../types/ml";
import { Activity, BarChart2, Radio, Zap, AlertTriangle, CheckCircle2 } from "lucide-react";

interface RiskCenterProps {
  mlState: MLStatusState;
}

function RiskGauge({ score }: { score: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Track arc
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.62, Math.PI, 0, false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = "rgba(255,255,255,0.07)";
    ctx.stroke();

    // Glow + fill arc
    const endAngle = Math.PI + score * Math.PI;
    const color = score >= 1.0 ? "#f43f5e" : score === 0.0 ? "#10b981" : "#f59e0b";
    ctx.shadowColor = color;
    ctx.shadowBlur = 18;
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.62, Math.PI, endAngle, false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = color;
    ctx.lineCap = "round";
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Label
    ctx.fillStyle = color;
    ctx.font = `bold ${h * 0.22}px 'Space Grotesk', monospace`;
    ctx.textAlign = "center";
    const label = score >= 1.0 ? "ANOMALY" : "NORMAL";
    ctx.fillText(label, w / 2, h * 0.65);
  }, [score]);

  return <canvas ref={canvasRef} width={220} height={120} className="mx-auto" />;
}

const StatChip = ({ label, value, accent }: { label: string; value: string; accent: string }) => (
  <div
    style={{ borderColor: "rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.035)" }}
    className="rounded-xl border p-3 backdrop-blur-sm"
  >
    <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: "rgba(255,255,255,0.4)" }}>
      {label}
    </div>
    <div className="font-bold text-sm font-mono" style={{ color: accent }}>
      {value}
    </div>
  </div>
);

export const RiskCenter: React.FC<RiskCenterProps> = ({ mlState }) => {
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;
  const riskScore = mlState.risk_score ?? 0;

  // Brand colors from login design language
  const orange = "#ff8a1f";
  const orangeLight = "#ff9b4a";
  const anomalyRed = "#f43f5e";
  const normalGreen = "#10b981";

  const verdictColor = isAnomaly ? anomalyRed : isActive ? normalGreen : orangeLight;

  return (
    <div
      style={{
        background: "linear-gradient(145deg, rgba(20,27,42,0.72), rgba(9,14,25,0.60))",
        border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.35)" : isActive ? "rgba(16,185,129,0.25)" : "rgba(255,255,255,0.08)"}`,
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        boxShadow: isAnomaly
          ? "0 25px 70px rgba(244,63,94,0.15), inset 0 1px 0 rgba(255,255,255,0.06)"
          : "0 25px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
        transition: "all 0.5s ease",
      }}
      className="rounded-2xl p-6 space-y-6"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div
            style={{ background: "linear-gradient(135deg, #ff9b2f, #ff7a18)", boxShadow: "0 6px 20px rgba(255,122,24,0.3)" }}
            className="w-8 h-8 rounded-lg flex items-center justify-center"
          >
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[10px] font-bold uppercase">
              PREDICTIVE RISK CENTER
            </p>
            <h2 className="text-white font-bold text-sm leading-tight">
              Isolation Forest · Real-Time Inference
            </h2>
          </div>
        </div>

        <div
          style={{
            background: isAnomaly ? "rgba(244,63,94,0.12)" : isActive ? "rgba(16,185,129,0.10)" : "rgba(255,138,31,0.10)",
            border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.35)" : isActive ? "rgba(16,185,129,0.3)" : "rgba(255,138,31,0.25)"}`,
            color: verdictColor,
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold font-mono"
        >
          {isActive ? (
            <>
              <Radio className="w-3 h-3 animate-pulse" />
              {isAnomaly ? "ANOMALY ACTIVE" : "NOMINAL — PASS"}
            </>
          ) : (
            <>
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: orange }} />
              WARMING UP
            </>
          )}
        </div>
      </div>

      {/* ── Content ── */}
      {isActive ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          {/* Gauge */}
          <div className="flex flex-col items-center gap-3">
            <RiskGauge score={riskScore} />
            <div className="flex gap-5 text-[10px] font-mono" style={{ color: "rgba(255,255,255,0.4)" }}>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: normalGreen }} />NORMAL
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full" style={{ background: anomalyRed }} />ANOMALY
              </span>
            </div>
          </div>

          {/* Verdict + stats */}
          <div className="space-y-4">
            {/* Verdict card */}
            <div
              style={{
                background: isAnomaly ? "rgba(244,63,94,0.08)" : "rgba(16,185,129,0.08)",
                border: `1px solid ${isAnomaly ? "rgba(244,63,94,0.3)" : "rgba(16,185,129,0.25)"}`,
              }}
              className="p-4 rounded-xl flex items-start gap-3"
            >
              {isAnomaly
                ? <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: anomalyRed }} />
                : <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" style={{ color: normalGreen }} />}
              <div>
                <div className="font-bold text-white text-sm">
                  {isAnomaly ? "ANOMALOUS TELEMETRY" : "NOMINAL OPERATION"}
                </div>
                <div className="text-xs mt-1 leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
                  {isAnomaly
                    ? "Isolation Forest classified this sample outside the normal operational envelope. Check the Alerts page for the specific hazard diagnosis."
                    : "All telemetry channels within expected drilling bounds. No action required."}
                </div>
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-2">
              <StatChip label="Model" value="Isolation Forest" accent={orangeLight} />
              <StatChip label="Verdict" value={isAnomaly ? "ANOMALY" : "NORMAL"} accent={verdictColor} />
              <StatChip label="Contamination" value="2.0%" accent={orange} />
              <StatChip label="Estimators" value="100" accent="#818cf8" />
            </div>
          </div>
        </div>
      ) : (
        /* Warming-up state */
        <div className="flex flex-col items-center gap-5 py-10">
          <div className="relative">
            <div
              style={{ border: "2px solid rgba(255,138,31,0.2)", background: "rgba(255,138,31,0.05)" }}
              className="w-16 h-16 rounded-full flex items-center justify-center"
            >
              <Activity className="w-7 h-7" style={{ color: orange }} />
            </div>
            <div className="absolute inset-0 rounded-full border-2 animate-ping" style={{ borderColor: "rgba(255,138,31,0.2)" }} />
          </div>
          <div className="text-center space-y-2">
            <p style={{ color: orangeLight, letterSpacing: "1px" }} className="text-sm font-bold uppercase font-mono">
              Building Causal Feature Window...
            </p>
            <p className="text-xs max-w-xs" style={{ color: "rgba(255,255,255,0.45)" }}>
              {mlState.gate_reason || "Waiting for sufficient causal telemetry history to begin inference."}
            </p>
          </div>
          {/* Orange bar */}
          <div style={{ width: "48px", height: "3px", background: orange, boxShadow: "0 0 12px rgba(255,138,31,0.5)", borderRadius: "10px" }} />
        </div>
      )}

      {/* ── Footer ── */}
      <div
        style={{ borderTopColor: "rgba(255,255,255,0.07)" }}
        className="pt-4 border-t flex items-center justify-between text-[11px] font-mono"
      >
        <span className="flex items-center gap-1.5" style={{ color: "rgba(255,255,255,0.35)" }}>
          <BarChart2 className="w-3.5 h-3.5" style={{ color: orange }} />
          Causal Feature Builder
        </span>
        <span className="flex items-center gap-1.5" style={{ color: "rgba(255,255,255,0.35)" }}>
          <Activity className="w-3 h-3" style={{ color: orange }} />
          <span style={{ color: orange }} className="font-bold">{mlState.features_constructed ?? 0}</span>
          <span>features</span>
        </span>
      </div>
    </div>
  );
};
