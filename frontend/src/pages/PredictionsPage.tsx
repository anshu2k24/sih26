import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { RiskCenter } from "../components/risk/RiskCenter";
import { Cpu, ShieldAlert } from "lucide-react";

export const PredictionsPage: React.FC = () => {
  const { mlState } = useActiveWell();

  return (
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-amber-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              REAL-TIME ML RISK & PREDICTION CENTER
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-bold">
              READINESS GATE ENFORCED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time causal isolation feature engineering and predictive gate verification.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs bg-slate-950 px-3.5 py-2 rounded-lg border border-slate-800 text-slate-400">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span>ML Predictions Distinct From Historical Correlation</span>
        </div>
      </div>

      <RiskCenter mlState={mlState} />
    </div>
  );
};
