import React from "react";
import type { MLStatusState } from "../../types/ml";
import { AlertOctagon, CheckCircle2, Cpu, HelpCircle, Network, Box } from "lucide-react";

interface RiskCenterProps {
  mlState: MLStatusState;
}

export const RiskCenter: React.FC<RiskCenterProps> = ({ mlState }) => {
  const isBlocked = mlState.is_blocked || mlState.status === "ML_NOT_READY";

  return (
    <div 
      className="rounded-[20px] p-[32px] flex flex-col justify-between transition-all duration-300 relative group overflow-hidden"
      style={{
        background: "rgba(18, 16, 14, 0.75)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 138, 0, 0.25)",
        boxShadow: "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)"
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
        e.currentTarget.style.boxShadow = "0 15px 50px rgba(0,0,0,0.5), 0 0 30px rgba(255,138,0,0.1), inset 0 0 30px rgba(255,138,0,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
        e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)";
      }}
    >
      <div>
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-[24px] gap-4">
          <h2 className="text-[14px] font-[700] text-[#F2F2F2] uppercase font-mono tracking-wider flex items-center gap-3 drop-shadow-sm">
            <Cpu className="w-5 h-5 text-[#C084FC] drop-shadow-[0_0_8px_#C084FC]" />
            Predictive Risk Center (ML Interface)
          </h2>
          <span
            className="text-[11px] px-[12px] py-[6px] rounded-[6px] font-mono font-[700] tracking-wider uppercase"
            style={
              !isBlocked
                ? { background: "rgba(16,185,129,0.1)", color: "#34D399", border: "1px solid rgba(16,185,129,0.3)", boxShadow: "0 0 10px rgba(16,185,129,0.15)" }
                : { background: "rgba(225,29,72,0.15)", color: "#FB7185", border: "1px solid rgba(225,29,72,0.4)", boxShadow: "0 0 15px rgba(225,29,72,0.2)" }
            }
          >
            {!isBlocked ? "ML ACTIVE" : "ML BLOCKED — NEED REAL DATA"}
          </span>
        </div>

        {/* Predictive Status Card */}
        <div
          className="rounded-[16px] p-[24px] mb-[24px] relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between transition-all duration-300"
          style={
            !isBlocked
              ? {
                  background: "rgba(16,185,129,0.08)",
                  border: "1px solid rgba(16,185,129,0.3)",
                  boxShadow: "inset 0 0 20px rgba(16,185,129,0.05)"
                }
              : {
                  background: "rgba(225,29,72,0.1)",
                  border: "1px solid rgba(225,29,72,0.4)",
                  boxShadow: "inset 0 0 30px rgba(225,29,72,0.15)"
                }
          }
        >
          {isBlocked && (
            <div className="absolute top-0 left-0 w-[50%] h-[150%] rounded-full opacity-[0.08] blur-[40px] pointer-events-none" style={{ background: "#E11D48" }}></div>
          )}

          <div className="flex items-center gap-[20px] relative z-10">
            <div 
              className="w-[60px] h-[60px] rounded-full flex items-center justify-center shrink-0 border"
              style={
                !isBlocked
                  ? { background: "rgba(16,185,129,0.15)", borderColor: "rgba(16,185,129,0.5)", boxShadow: "0 0 20px rgba(16,185,129,0.2)" }
                  : { background: "rgba(225,29,72,0.15)", borderColor: "rgba(225,29,72,0.6)", boxShadow: "0 0 25px rgba(225,29,72,0.3)" }
              }
            >
              {!isBlocked ? (
                <CheckCircle2 className="w-8 h-8 text-[#34D399] drop-shadow-[0_0_8px_#34D399]" />
              ) : (
                <AlertOctagon className="w-8 h-8 text-[#FB7185] drop-shadow-[0_0_8px_#FB7185]" />
              )}
            </div>
            
            <div>
              <div className="text-[18px] font-[700] tracking-wide font-sans mb-[8px]" style={{ color: !isBlocked ? "#34D399" : "#FB7185" }}>
                {!isBlocked ? "LEGITIMATE PREDICTION ACTIVE" : "Prediction: UNAVAILABLE"}
              </div>
              <div className="text-[13px] text-[#E2E2E2] font-mono leading-relaxed">
                {!isBlocked
                  ? `Causal Risk Probability: ${(mlState.risk_score || 0).toFixed(4)}`
                  : <span className="flex items-center gap-1.5"><span className="text-[#A1A1AA]">Gate Block Reason:</span> {mlState.gate_reason}</span>}
              </div>
            </div>
          </div>

          {/* Decorative Warning Element (Right side) */}
          {isBlocked && (
            <div className="hidden md:flex shrink-0 relative w-[100px] h-[100px] items-center justify-center opacity-60 z-0">
              {/* Faint Radar Rings */}
              <div className="absolute inset-0 rounded-full border border-[#E11D48] opacity-[0.15] scale-[0.6]"></div>
              <div className="absolute inset-0 rounded-full border border-[#E11D48] opacity-[0.08] scale-[0.8]"></div>
              <div className="absolute inset-0 rounded-full border border-[#E11D48] opacity-[0.04] scale-100"></div>
              {/* Core Icon */}
              <AlertOctagon className="w-[40px] h-[40px] text-[#E11D48]" strokeWidth={1.5} />
            </div>
          )}
        </div>

        {/* Explanatory Readiness Rules */}
        {isBlocked && (
          <div 
            className="rounded-[12px] p-[24px] space-y-[12px] transition-all duration-300"
            style={{
              background: "rgba(5, 7, 9, 0.6)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            <div className="font-[700] text-white flex items-center gap-[8px] text-[13px] tracking-wide">
              <div className="w-[24px] h-[24px] rounded-full flex items-center justify-center border border-[rgba(56,189,248,0.4)] bg-[rgba(56,189,248,0.1)]">
                <HelpCircle className="w-[14px] h-[14px] text-[#38BDF8]" />
              </div>
              Scientific Gate Activation Requirements:
            </div>
            <ul className="list-disc list-outside ml-[32px] text-[#A1A1AA] space-y-[8px] font-mono text-[12px]">
              <li>Must ingest <code className="text-[#9A9A9A] bg-[rgba(255,255,255,0.05)] px-[4px] py-[2px] rounded">data/raw/oil_ertmac_events.parquet</code></li>
              <li>Must ingest <code className="text-[#9A9A9A] bg-[rgba(255,255,255,0.05)] px-[4px] py-[2px] rounded">data/raw/oil_ertmac_sensors.parquet</code></li>
              <li>Minimum 5 independent positive well groups with verified events and overlapping pre-onset telemetry</li>
            </ul>
            <div className="text-[12px] text-[#FF9D1A] font-['Inter',sans-serif] italic pt-[8px] ml-[32px]">
              Note: Zero risk scores or probabilities are fabricated when the ML readiness gate blocks inference.
            </div>
          </div>
        )}
      </div>

      {mlState.features_constructed ? (
        <div className="mt-[32px] pt-[24px] border-t border-[rgba(255,138,0,0.15)] flex flex-col sm:flex-row sm:items-center justify-between gap-[16px]">
          <div className="flex items-center gap-[12px]">
            <div 
              className="w-[40px] h-[40px] rounded-[10px] flex items-center justify-center border"
              style={{ background: "rgba(255, 138, 0, 0.1)", borderColor: "rgba(255, 138, 0, 0.3)" }}
            >
              <Network className="w-5 h-5 text-[#FF8A00]" />
            </div>
            <span className="text-[14px] font-[700] text-white tracking-wide">Causal Feature Builder:</span>
          </div>

          <div 
            className="flex items-center gap-[12px] px-[20px] py-[12px] rounded-[12px] border transition-all duration-300"
            style={{
              background: "rgba(0,0,0,0.6)",
              borderColor: "rgba(255, 138, 0, 0.4)",
              boxShadow: "0 0 15px rgba(255,138,0,0.1), inset 0 0 20px rgba(255,138,0,0.05)"
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#FF9D1A";
              e.currentTarget.style.boxShadow = "0 0 25px rgba(255,138,0,0.2), inset 0 0 25px rgba(255,138,0,0.1)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
              e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.1), inset 0 0 20px rgba(255,138,0,0.05)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <Box className="w-[18px] h-[18px] text-[#C084FC] drop-shadow-[0_0_5px_#C084FC]" />
            <span className="text-[24px] font-[700] text-[#FF9D1A] font-mono leading-none drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]">
              {mlState.features_constructed}
            </span>
            <span className="text-[13px] text-[#E2E2E2] font-mono tracking-wide">features constructed</span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
