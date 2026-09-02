import React from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { RiskCenter } from "../components/risk/RiskCenter";
import { ShieldAlert, Cpu } from "lucide-react";

export const RiskPage: React.FC = () => {
  const { mlState } = useActiveWell();

  return (
    <div 
      className="min-h-screen pb-[48px] relative overflow-hidden"
      style={{ backgroundColor: "#050607", fontFamily: "'Space Grotesk', 'Inter', sans-serif" }}
    >
      {/* Absolute Ambient Background Lights */}
      <div className="absolute top-[5%] left-[20%] w-[60%] h-[30%] rounded-full opacity-[0.04] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[20%] right-[10%] w-[50%] h-[40%] rounded-full opacity-[0.03] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        {/* Header Banner - Premium Dark Glassmorphism */}
        <div 
          className="rounded-[20px] p-[28px] flex flex-col xl:flex-row xl:items-center justify-between gap-6 transition-all duration-300 relative overflow-hidden"
          style={{
            background: "rgba(18, 16, 14, 0.75)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 138, 0, 0.25)",
            boxShadow: "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)"
          }}
        >
          {/* Header internal glow */}
          <div className="absolute top-0 left-0 w-full h-[150%] rounded-full opacity-[0.04] blur-[60px] pointer-events-none" style={{ background: "#FF8A00" }}></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-4 flex-wrap">
              <div 
                className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                style={{ border: "1px solid rgba(255, 138, 0, 0.6)", background: "rgba(255, 138, 0, 0.1)", boxShadow: "0 0 15px rgba(255, 138, 0, 0.2)" }}
              >
                <Cpu className="w-5 h-5 text-[#FF9D1A]" />
              </div>
              <h1 className="text-[20px] sm:text-[24px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                REAL-TIME ML RISK & PREDICTION CENTER
              </h1>
              <span 
                className="text-[10px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider whitespace-nowrap"
                style={{ background: "rgba(18, 16, 14, 0.8)", color: "#FF8A00", border: "1px solid rgba(255, 138, 0, 0.4)", boxShadow: "0 0 10px rgba(255, 138, 0, 0.15)" }}
              >
                READINESS GATE ENFORCED
              </span>
            </div>
            <p className="text-[13px] text-[#A1A1AA] mt-3 font-['Inter',sans-serif] max-w-3xl leading-relaxed">
              Real-time causal isolation feature engineering and predictive gate verification.
            </p>
          </div>

          <div 
            className="relative z-10 flex items-center gap-3 px-[20px] py-[12px] rounded-[12px] transition-all duration-200"
            style={{
              background: "rgba(18, 16, 14, 0.8)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              boxShadow: "0 4px 15px rgba(0,0,0,0.3)"
            }}
          >
            <ShieldAlert className="w-4 h-4 text-[#FF8A00]" />
            <span className="text-[12px] text-[#E2E2E2] font-mono">ML Predictions Distinct From Historical Correlation</span>
          </div>
        </div>

        {/* Embedded RiskCenter Component */}
        <RiskCenter mlState={mlState} />
      </div>
    </div>
  );
};
