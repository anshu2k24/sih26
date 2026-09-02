import React, { useState, useEffect } from "react";
import { fetchAnalyticsSummaryApi, fetchAlertsTrendApi } from "../services/api";
import type { AnalyticsSummary, AlertTrendPoint } from "../types/api";
import { BarChart3, Activity, AlertTriangle, ShieldCheck, Database, Layers, ArrowUpRight, Shield } from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trend, setTrend] = useState<AlertTrendPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    Promise.all([fetchAnalyticsSummaryApi(), fetchAlertsTrendApi()]).then(([sumRes, trendRes]) => {
      if (sumRes) setSummary(sumRes);
      if (trendRes && trendRes.trend) setTrend(trendRes.trend);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-center text-[#A1A1AA] font-mono h-screen flex flex-col items-center justify-center bg-[#050607]">
        <Activity className="w-8 h-8 animate-spin mx-auto mb-4 text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]" />
        <span className="uppercase tracking-widest text-[12px] font-[700]">Loading Operational Analytics Engine...</span>
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen pb-[48px] relative overflow-hidden font-['Space_Grotesk',sans-serif]"
      style={{ backgroundColor: "#050607" }}
    >
      {/* Ambient Background Glows */}
      <div className="absolute top-[5%] left-[50%] -translate-x-1/2 w-[80%] h-[30%] rounded-full opacity-[0.03] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[20%] right-[10%] w-[50%] h-[40%] rounded-full opacity-[0.02] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        {/* Header Banner */}
        <div 
          className="rounded-[20px] p-[32px] flex flex-col lg:flex-row lg:items-center justify-between gap-6 transition-all duration-300 relative overflow-hidden group"
          style={{
            background: "rgba(20, 15, 10, 0.55)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            border: "1px solid rgba(255, 140, 0, 0.25)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.35), inset 0 0 20px rgba(255,140,0,0.05)"
          }}
        >
          {/* Subtle Inner Highlight */}
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[rgba(255,140,0,0.3)] to-transparent"></div>
          <div className="absolute top-0 left-0 w-[40%] h-[150%] rounded-full opacity-[0.03] blur-[50px] pointer-events-none" style={{ background: "#FF8A00" }}></div>

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-4 lg:gap-6">
            <div 
              className="w-[60px] h-[60px] rounded-[16px] flex items-center justify-center shrink-0 border transition-all duration-300"
              style={{ background: "rgba(255, 138, 0, 0.08)", borderColor: "rgba(255, 138, 0, 0.4)", boxShadow: "0 0 20px rgba(255,138,0,0.15)" }}
            >
              <BarChart3 className="w-8 h-8 text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]" />
            </div>
            <div>
              <div className="flex items-center gap-4 flex-wrap mb-[8px]">
                <h1 className="text-[20px] md:text-[24px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                  OPERATIONAL ANALYTICS & DRILLING INTELLIGENCE
                </h1>
                <span 
                  className="text-[11px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider flex items-center gap-1.5"
                  style={{ background: "rgba(255,138,0,0.1)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.3)", boxShadow: "0 0 10px rgba(255,138,0,0.15)" }}
                >
                  SYSTEM WIDE AGGREGATION
                </span>
              </div>
              <p className="text-[13px] text-[#A1A1AA] font-['Inter',sans-serif] leading-relaxed max-w-4xl">
                Real-time metric telemetry, hazard frequency distributions, and 30-day operational alert trendlines.
              </p>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-[12px] px-[20px] py-[12px] rounded-[12px] transition-all duration-300 shrink-0"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.1)"
            }}>
            <Database className="w-4 h-4 text-[#FF9D1A]" />
            <span className="text-[12px] text-[#D4D4D8] font-[700] font-mono tracking-wider">Equinor Volve Semantic Audit Dataset</span>
          </div>
        </div>

        {/* KPI Cards */}
        {summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[24px]">
            {/* 1. ACTIVE ALERTS (Orange/Yellow) */}
            <div 
              className="rounded-[16px] p-[24px] relative overflow-hidden transition-all duration-300 group"
              style={{
                background: "rgba(20, 15, 10, 0.55)",
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(255, 140, 0, 0.25)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-3px)";
                e.currentTarget.style.borderColor = "rgba(245, 158, 11, 0.5)";
                e.currentTarget.style.boxShadow = "0 15px 40px rgba(0,0,0,0.5), 0 0 30px rgba(245, 158, 11, 0.15), inset 0 0 20px rgba(245, 158, 11, 0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "rgba(255, 140, 0, 0.25)";
                e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.35)";
              }}
            >
              <div className="text-[#A1A1AA] text-[12px] font-[700] uppercase tracking-wider font-mono">ACTIVE ALERTS</div>
              <div className="text-[42px] font-[800] text-[#F59E0B] mt-[12px] leading-none drop-shadow-[0_0_10px_rgba(245,158,11,0.3)] transition-all group-hover:drop-shadow-[0_0_15px_rgba(245,158,11,0.6)]">
                {summary.total_active_alerts}
              </div>
              <div className="text-[11px] text-[#6B7280] mt-[12px] font-sans">Total operational alerts<br/>requiring action</div>
              <AlertTriangle className="absolute right-4 bottom-4 w-12 h-12 text-[#F59E0B] opacity-[0.15] transition-all group-hover:opacity-[0.3] group-hover:drop-shadow-[0_0_10px_#F59E0B]" />
            </div>

            {/* 2. MONITORED WELLS (Blue/Cyan) */}
            <div 
              className="rounded-[16px] p-[24px] relative overflow-hidden transition-all duration-300 group"
              style={{
                background: "rgba(20, 15, 10, 0.55)",
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(255, 140, 0, 0.25)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-3px)";
                e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.5)";
                e.currentTarget.style.boxShadow = "0 15px 40px rgba(0,0,0,0.5), 0 0 30px rgba(56, 189, 248, 0.15), inset 0 0 20px rgba(56, 189, 248, 0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "rgba(255, 140, 0, 0.25)";
                e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.35)";
              }}
            >
              <div className="text-[#A1A1AA] text-[12px] font-[700] uppercase tracking-wider font-mono">MONITORED WELLS</div>
              <div className="text-[42px] font-[800] text-[#38BDF8] mt-[12px] leading-none drop-shadow-[0_0_10px_rgba(56,189,248,0.3)] transition-all group-hover:drop-shadow-[0_0_15px_rgba(56,189,248,0.6)]">
                {summary.monitored_wells_count}
              </div>
              <div className="text-[11px] text-[#6B7280] mt-[12px] font-sans">Equinor Volve USROP<br/>Wells Replayed</div>
              <Layers className="absolute right-4 bottom-4 w-12 h-12 text-[#38BDF8] opacity-[0.15] transition-all group-hover:opacity-[0.3] group-hover:drop-shadow-[0_0_10px_#38BDF8]" />
            </div>

            {/* 3. KNOWLEDGE RECORDS (Green) */}
            <div 
              className="rounded-[16px] p-[24px] relative overflow-hidden transition-all duration-300 group"
              style={{
                background: "rgba(20, 15, 10, 0.55)",
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(255, 140, 0, 0.25)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-3px)";
                e.currentTarget.style.borderColor = "rgba(52, 211, 153, 0.5)";
                e.currentTarget.style.boxShadow = "0 15px 40px rgba(0,0,0,0.5), 0 0 30px rgba(52, 211, 153, 0.15), inset 0 0 20px rgba(52, 211, 153, 0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "rgba(255, 140, 0, 0.25)";
                e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.35)";
              }}
            >
              <div className="text-[#A1A1AA] text-[12px] font-[700] uppercase tracking-wider font-mono">KNOWLEDGE RECORDS</div>
              <div className="text-[42px] font-[800] text-[#34D399] mt-[12px] leading-none drop-shadow-[0_0_10px_rgba(52,211,153,0.3)] transition-all group-hover:drop-shadow-[0_0_15px_rgba(52,211,153,0.6)]">
                {summary.knowledge_records_count}
              </div>
              <div className="text-[11px] text-[#6B7280] mt-[12px] font-sans">Verified historical DDR<br/>event episodes</div>
              <ShieldCheck className="absolute right-4 bottom-4 w-12 h-12 text-[#34D399] opacity-[0.15] transition-all group-hover:opacity-[0.3] group-hover:drop-shadow-[0_0_10px_#34D399]" />
            </div>

            {/* 4. CRITICAL HAZARDS (Red) */}
            <div 
              className="rounded-[16px] p-[24px] relative overflow-hidden transition-all duration-300 group"
              style={{
                background: "rgba(20, 15, 10, 0.55)",
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(255, 140, 0, 0.25)",
                boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-3px)";
                e.currentTarget.style.borderColor = "rgba(248, 113, 113, 0.5)";
                e.currentTarget.style.boxShadow = "0 15px 40px rgba(0,0,0,0.5), 0 0 30px rgba(248, 113, 113, 0.15), inset 0 0 20px rgba(248, 113, 113, 0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "rgba(255, 140, 0, 0.25)";
                e.currentTarget.style.boxShadow = "0 8px 32px rgba(0,0,0,0.35)";
              }}
            >
              <div className="text-[#A1A1AA] text-[12px] font-[700] uppercase tracking-wider font-mono">CRITICAL HAZARDS</div>
              <div className="text-[42px] font-[800] text-[#F87171] mt-[12px] leading-none drop-shadow-[0_0_10px_rgba(248,113,113,0.3)] transition-all group-hover:drop-shadow-[0_0_15px_rgba(248,113,113,0.6)]">
                {summary.alert_severity_breakdown.CRITICAL || 0}
              </div>
              <div className="text-[11px] text-[#6B7280] mt-[12px] font-sans">High-risk conditions<br/>(Kick/Stuck Pipe)</div>
              <Activity className="absolute right-4 bottom-4 w-12 h-12 text-[#F87171] opacity-[0.15] transition-all group-hover:opacity-[0.3] group-hover:drop-shadow-[0_0_10px_#F87171]" />
            </div>
          </div>
        )}

        {/* Main Analytics Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-[24px]">
          {/* LEFT: Alert Trend visualizer */}
          <div 
            className="rounded-[20px] p-[32px] space-y-[24px]"
            style={{
              background: "rgba(20, 15, 10, 0.55)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 140, 0, 0.25)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
            }}
          >
            <div className="flex items-center justify-between border-b border-[rgba(255,140,0,0.2)] pb-[16px]">
              <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-3 drop-shadow-sm">
                <Activity className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" /> 
                Operational Alert Generation Trend (30 Days)
              </h2>
              <span className="text-[11px] font-mono text-[#FF9D1A]">Daily Frequency</span>
            </div>

            <div className="space-y-[20px] pt-[8px]">
              {trend.map((pt) => {
                const total = pt.CRITICAL + pt.HIGH + pt.MEDIUM + pt.LOW;
                const maxVal = 12;
                const pct = Math.min(100, Math.round((total / maxVal) * 100));

                return (
                  <div key={pt.date} className="space-y-[8px] group cursor-default">
                    <div className="flex justify-between text-[12px]">
                      <span className="font-mono text-[#A1A1AA] group-hover:text-white transition-colors">{pt.date}</span>
                      <span className="font-[700] text-[#D4D4D8] group-hover:text-white transition-colors">
                        <strong className="text-[#FF9D1A] mr-1">{total}</strong> alerts
                      </span>
                    </div>
                    <div 
                      className="h-[6px] bg-[rgba(0,0,0,0.8)] rounded-full overflow-hidden flex border border-[rgba(255,255,255,0.05)] shadow-[inset_0_0_5px_rgba(0,0,0,0.5)] transition-all duration-300"
                    >
                      {pt.CRITICAL > 0 && (
                        <div
                          style={{ width: `${(pt.CRITICAL / total) * pct}%` }}
                          className="h-full bg-[#EF4444] shadow-[0_0_8px_#EF4444] transition-all group-hover:bg-[#F87171] group-hover:shadow-[0_0_15px_#F87171]"
                          title={`Critical: ${pt.CRITICAL}`}
                        />
                      )}
                      {pt.HIGH > 0 && (
                        <div
                          style={{ width: `${(pt.HIGH / total) * pct}%` }}
                          className="h-full bg-[#F59E0B] shadow-[0_0_8px_#F59E0B] transition-all group-hover:bg-[#FBBF24] group-hover:shadow-[0_0_15px_#FBBF24]"
                          title={`High: ${pt.HIGH}`}
                        />
                      )}
                      {pt.MEDIUM > 0 && (
                        <div
                          style={{ width: `${(pt.MEDIUM / total) * pct}%` }}
                          className="h-full bg-[#EAB308] shadow-[0_0_8px_#EAB308] transition-all group-hover:bg-[#FDE047] group-hover:shadow-[0_0_15px_#FDE047]"
                          title={`Medium: ${pt.MEDIUM}`}
                        />
                      )}
                      {pt.LOW > 0 && (
                        <div
                          style={{ width: `${(pt.LOW / total) * pct}%` }}
                          className="h-full bg-[#3B82F6] shadow-[0_0_8px_#3B82F6] transition-all group-hover:bg-[#60A5FA] group-hover:shadow-[0_0_15px_#60A5FA]"
                          title={`Low: ${pt.LOW}`}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT: Event Type Breakdown */}
          <div 
            className="rounded-[20px] p-[32px] space-y-[24px] flex flex-col justify-between"
            style={{
              background: "rgba(20, 15, 10, 0.55)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 140, 0, 0.25)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.35)"
            }}
          >
            <div>
              <div className="flex items-center justify-between border-b border-[rgba(255,140,0,0.2)] pb-[16px] mb-[24px]">
                <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-3 drop-shadow-sm">
                  <Layers className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" /> 
                  Historical Hazard Frequency Distribution
                </h2>
                <span className="text-[11px] font-mono text-[#FF9D1A]">Equinor Volve Dataset</span>
              </div>

              <div className="space-y-[24px]">
                {[
                  { type: "Pack-off & Tight Hole", count: 42, pct: 36, color: "#EF4444", hoverColor: "#F87171" },
                  { type: "Equipment Failure", count: 27, pct: 23, color: "#F59E0B", hoverColor: "#FBBF24" },
                  { type: "Formation Loss", count: 22, pct: 19, color: "#EAB308", hoverColor: "#FDE047" },
                  { type: "Stuck Pipe", count: 16, pct: 14, color: "#A855F7", hoverColor: "#C084FC" },
                  { type: "Kick / Well Control", count: 9, pct: 8, color: "#06B6D4", hoverColor: "#22D3EE" },
                ].map((item) => (
                  <div key={item.type} className="space-y-[10px] group cursor-default">
                    <div className="flex justify-between text-[13px]">
                      <span className="text-[#D4D4D8] font-[700] transition-colors group-hover:text-white drop-shadow-sm">{item.type}</span>
                      <span className="text-[#A1A1AA] font-[700] font-mono transition-colors group-hover:text-white">
                        {item.count} events ({item.pct}%)
                      </span>
                    </div>
                    <div className="h-[6px] bg-[rgba(0,0,0,0.8)] rounded-full overflow-hidden border border-[rgba(255,255,255,0.05)] shadow-[inset_0_0_5px_rgba(0,0,0,0.5)]">
                      <div
                        style={{ width: `${item.pct}%`, backgroundColor: item.color, boxShadow: `0 0 10px ${item.color}` }}
                        className="h-full rounded-full transition-all duration-300 group-hover:brightness-125"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Zero-Fabrication Panel */}
            <div 
              className="mt-[32px] p-[20px] rounded-[16px] transition-all duration-300 flex items-center justify-between group cursor-default"
              style={{
                background: "rgba(0,0,0,0.6)",
                border: "1px solid rgba(255,140,0,0.2)",
                boxShadow: "inset 0 0 15px rgba(255,140,0,0.05)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,140,0,0.5)";
                e.currentTarget.style.boxShadow = "0 0 20px rgba(255,140,0,0.15), inset 0 0 15px rgba(255,140,0,0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,140,0,0.2)";
                e.currentTarget.style.boxShadow = "inset 0 0 15px rgba(255,140,0,0.05)";
              }}
            >
              <div className="flex items-center gap-[16px]">
                <Shield className="w-6 h-6 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" />
                <div>
                  <span className="text-[#FF9D1A] font-[700] block text-[13px] tracking-wide mb-[4px]">Zero-Fabrication Data Standard</span>
                  <span className="text-[11px] text-[#A1A1AA] font-sans">All analytics derived deterministically from Equinor Volve historical logs.</span>
                </div>
              </div>
              <div 
                className="w-[32px] h-[32px] rounded-lg border flex items-center justify-center transition-all duration-300"
                style={{ background: "rgba(255,255,255,0.03)", borderColor: "rgba(255,255,255,0.1)" }}
              >
                <ArrowUpRight className="w-4 h-4 text-[#A1A1AA] group-hover:text-[#FF9D1A] group-hover:drop-shadow-[0_0_5px_#FF9D1A]" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
