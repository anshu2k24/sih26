import React, { useEffect, useRef } from "react";
import type { MLStatusState } from "../../types/ml";
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Activity,
  ShieldOff,
  Zap,
  BarChart2,
  Radio,
} from "lucide-react";

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

    // Background arc
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.65, Math.PI, 0, false);
    ctx.lineWidth = 14;
    ctx.strokeStyle = "#1e293b";
    ctx.stroke();

    // Colored fill arc
    const color = score >= 1.0 ? "#f43f5e" : score >= 0.5 ? "#f59e0b" : "#10b981";
    const endAngle = Math.PI + score * Math.PI;
    ctx.beginPath();
    ctx.arc(w / 2, h * 0.78, h * 0.65, Math.PI, endAngle, false);
    ctx.lineWidth = 14;
    ctx.strokeStyle = color;
    ctx.lineCap = "round";
    ctx.stroke();

    // Center label
    ctx.fillStyle = color;
    ctx.font = `bold ${h * 0.28}px monospace`;
    ctx.textAlign = "center";
    ctx.fillText(score >= 1.0 ? "ANOMALY" : score === 0.0 ? "NORMAL" : `${(score * 100).toFixed(0)}%`, w / 2, h * 0.68);
  }, [score]);

  return <canvas ref={canvasRef} width={200} height={110} className="mx-auto" />;
}

export const RiskCenter: React.FC<RiskCenterProps> = ({ mlState }) => {
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;
  const isNormal = isActive && mlState.risk_score === 0.0;

  const riskScore = mlState.risk_score ?? 0;

  const statusColor = isAnomaly
    ? "border-rose-500/50 bg-rose-950/30"
    : isNormal
    ? "border-emerald-500/40 bg-emerald-950/20"
    : isActive
    ? "border-amber-500/40 bg-amber-950/20"
    : "border-slate-700 bg-slate-950/50";

  const badgeClass = isAnomaly
    ? "bg-rose-950 text-rose-400 border-rose-500/40"
    : isNormal
    ? "bg-emerald-950 text-emerald-400 border-emerald-500/40"
    : isActive
    ? "bg-amber-950 text-amber-400 border-amber-500/40"
    : "bg-slate-900 text-slate-400 border-slate-700";

  const badgeLabel = isAnomaly
    ? "⚠ ANOMALY DETECTED"
    : isNormal
    ? "✓ NOMINAL — PASS"
    : isActive
    ? "◎ ACTIVE"
    : mlState.status === "ML_NOT_READY"
    ? "WARMING UP..."
    : mlState.status;

  return (
    <div className={`rounded-xl border p-5 shadow-lg space-y-5 transition-all duration-500 ${statusColor}`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-purple-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest">
            Predictive Risk Center
          </h2>
          {isActive && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-bold">
              <Radio className="w-3 h-3 animate-pulse" /> LIVE
            </span>
          )}
        </div>
        <span className={`text-xs px-3 py-1 rounded-full border font-bold font-mono ${badgeClass}`}>
          {badgeLabel}
        </span>
      </div>

      {/* Gauge + Status */}
      {isActive ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 items-center">
          {/* Gauge */}
          <div className="flex flex-col items-center gap-2">
            <RiskGauge score={riskScore} />
            <div className="flex gap-4 text-[10px] font-mono text-slate-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />NORMAL</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />ANOMALY</span>
            </div>
          </div>

          {/* Details */}
          <div className="space-y-3">
            {/* Model verdict */}
            <div className={`p-3 rounded-lg border flex items-start gap-3 ${isAnomaly ? "bg-rose-950/50 border-rose-500/40" : "bg-emerald-950/30 border-emerald-500/30"}`}>
              {isAnomaly
                ? <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />}
              <div>
                <div className={`text-sm font-bold font-mono ${isAnomaly ? "text-rose-300" : "text-emerald-300"}`}>
                  {isAnomaly ? "ANOMALOUS TELEMETRY" : "NOMINAL OPERATION"}
                </div>
                <div className="text-xs text-slate-400 mt-0.5 font-sans">
                  {isAnomaly
                    ? "Isolation Forest flagged this sample as outside normal operational envelope."
                    : "All telemetry channels within expected operational bounds."}
                </div>
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5">
                <div className="text-slate-500 text-[10px] uppercase">Model</div>
                <div className="text-purple-300 font-bold mt-0.5">Isolation Forest</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5">
                <div className="text-slate-500 text-[10px] uppercase">Verdict</div>
                <div className={`font-bold mt-0.5 ${isAnomaly ? "text-rose-400" : "text-emerald-400"}`}>
                  {isAnomaly ? "ANOMALY" : "NORMAL"}
                </div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5">
                <div className="text-slate-500 text-[10px] uppercase">Contamination</div>
                <div className="text-amber-300 font-bold mt-0.5">2.0%</div>
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-2.5">
                <div className="text-slate-500 text-[10px] uppercase">Estimators</div>
                <div className="text-blue-300 font-bold mt-0.5">100</div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Warming-up state */
        <div className="flex flex-col items-center gap-4 py-8">
          <div className="relative">
            <div className="w-16 h-16 rounded-full border-2 border-slate-700 flex items-center justify-center">
              <Zap className="w-7 h-7 text-slate-600" />
            </div>
            <div className="absolute inset-0 rounded-full border-2 border-purple-500/30 animate-ping" />
          </div>
          <div className="text-center space-y-1">
            <div className="text-sm font-bold text-slate-400 font-mono uppercase tracking-wider">
              {mlState.status === "ML_NOT_READY" ? "Building Causal Feature Window..." : mlState.status}
            </div>
            <div className="text-xs text-slate-500 font-sans max-w-xs">
              {mlState.gate_reason || "Waiting for sufficient causal telemetry history to begin inference."}
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
            <ShieldOff className="w-3.5 h-3.5" />
            <span>Inference gated until feature window is populated</span>
          </div>
        </div>
      )}

      {/* Feature count footer */}
      <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono text-slate-500">
        <span className="flex items-center gap-1.5">
          <BarChart2 className="w-3.5 h-3.5 text-purple-500" />
          Causal Feature Builder
        </span>
        <span className="flex items-center gap-1">
          <Activity className="w-3 h-3 text-purple-400" />
          <span className="text-purple-400 font-bold">{mlState.features_constructed ?? 0}</span>
          <span className="text-slate-600">features constructed</span>
        </span>
      </div>
    </div>
  );
};
