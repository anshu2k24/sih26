import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { RiskCenter } from "../components/risk/RiskCenter";
import { Brain, Activity, Radio } from "lucide-react";

export const RiskPage: React.FC = () => {
  const { mlState, selectedWell } = useActiveWell();
  const isActive = mlState.status === "SUCCESS" && !mlState.is_blocked;
  const isAnomaly = isActive && mlState.risk_score === 1.0;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <Brain className="w-5 h-5 text-purple-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              ML RISK &amp; PREDICTION CENTER
            </h1>
            {isAnomaly ? (
              <span className="text-xs px-2.5 py-0.5 rounded bg-rose-950/80 text-rose-400 border border-rose-500/30 font-bold animate-pulse">
                ⚠ ANOMALY ACTIVE
              </span>
            ) : isActive ? (
              <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-bold flex items-center gap-1">
                <Radio className="w-3 h-3 animate-pulse" /> MODEL LIVE
              </span>
            ) : (
              <span className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-bold">
                WARMING UP
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time causal isolation feature engineering → Isolation Forest anomaly detection → live alert dispatch.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs bg-slate-950 px-3.5 py-2 rounded-lg border border-slate-800 text-slate-400">
          <Activity className="w-4 h-4 text-purple-400" />
          <span>Well: <strong className="text-slate-200">{selectedWell}</strong></span>
        </div>
      </div>

      {/* Embedded RiskCenter Component */}
      <RiskCenter mlState={mlState} />
    </div>
  );
};
