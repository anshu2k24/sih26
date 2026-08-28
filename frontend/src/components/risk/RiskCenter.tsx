import React from "react";
import type { MLStatusState } from "../../types/ml";
import { AlertOctagon, CheckCircle2, Cpu, HelpCircle } from "lucide-react";

interface RiskCenterProps {
  mlState: MLStatusState;
}

export const RiskCenter: React.FC<RiskCenterProps> = ({ mlState }) => {
  const isBlocked = mlState.is_blocked || mlState.status === "ML_NOT_READY";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            Predictive Risk Center (ML Interface)
          </h2>
          <span
            className={`text-xs px-2.5 py-1 rounded font-mono font-bold ${
              !isBlocked
                ? "bg-emerald-950/80 text-emerald-400 border border-emerald-500/40"
                : "bg-rose-950/80 text-rose-400 border border-rose-500/40"
            }`}
          >
            {!isBlocked ? "ML ACTIVE" : "ML BLOCKED — NEED REAL DATA"}
          </span>
        </div>

        {/* Predictive Status Card */}
        <div
          className={`p-4 rounded-lg border mb-4 ${
            !isBlocked
              ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-300"
              : "bg-rose-950/30 border-rose-500/30 text-rose-300"
          }`}
        >
          <div className="flex items-start gap-3">
            {!isBlocked ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertOctagon className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="text-sm font-bold tracking-wide">
                {!isBlocked ? "LEGITIMATE PREDICTION ACTIVE" : "Prediction: UNAVAILABLE"}
              </div>
              <div className="text-xs text-slate-300 mt-1 font-mono leading-relaxed">
                {!isBlocked
                  ? `Causal Risk Probability: ${(mlState.risk_score || 0).toFixed(4)}`
                  : `Gate Block Reason: ${mlState.gate_reason}`}
              </div>
            </div>
          </div>
        </div>

        {/* Explanatory Readiness Rules */}
        {isBlocked && (
          <div className="bg-slate-850/60 p-4 rounded-lg border border-slate-800 space-y-2 text-xs">
            <div className="font-semibold text-slate-300 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-blue-400" />
              Scientific Gate Activation Requirements:
            </div>
            <ul className="list-disc list-inside text-slate-400 space-y-1 font-mono text-[11px]">
              <li>Must ingest `data/raw/oil_ertmac_events.parquet`</li>
              <li>Must ingest `data/raw/oil_ertmac_sensors.parquet`</li>
              <li>Minimum 5 independent positive well groups with verified events and overlapping pre-onset telemetry</li>
            </ul>
            <div className="text-[11px] text-amber-400/90 font-sans italic pt-1">
              Note: Zero risk scores or probabilities are fabricated when the ML readiness gate blocks inference.
            </div>
          </div>
        )}
      </div>

      {mlState.features_constructed ? (
        <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 font-mono flex items-center justify-between">
          <span>Causal Feature Builder:</span>
          <span className="text-purple-400 font-bold">{mlState.features_constructed} features constructed</span>
        </div>
      ) : null}
    </div>
  );
};
