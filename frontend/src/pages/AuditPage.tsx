import React, { useState, useEffect } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import { fetchAuditLogs } from "../services/api";
import type { AuditEvent } from "../types/api";
import {
  ShieldCheck,
  RefreshCw,
  Search,
  Download,
  Lock,
  ChevronDown,
  ChevronRight,
  Filter,
  CheckCircle2,
  FileSearch,
} from "lucide-react";

export const AuditPage: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null);

  const loadAuditLogs = () => {
    setLoading(true);
    fetchAuditLogs(selectedWell, 100)
      .then((res) => {
        if (res && res.events) {
          setEvents(res.events);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadAuditLogs();
  }, [selectedWell]);

  const toggleExpand = (id: string) => {
    setExpandedAuditId((prev) => (prev === id ? null : id));
  };

  const exportCSV = () => {
    if (events.length === 0) return;
    const headers = ["Audit ID", "Timestamp", "Actor ID", "Actor Role", "Action", "Resource Type", "Resource ID", "Well ID"];
    const rows = events.map((e) => [
      e.audit_id,
      e.timestamp,
      e.actor_id,
      e.actor_role || "N/A",
      e.action,
      e.resource_type,
      e.resource_id,
      e.well_id || "N/A",
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.map((c) => `"${c}"`).join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `audit_trail_${selectedWell.replace(/\//g, "_")}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredEvents = events.filter((evt) => {
    if (actionFilter !== "ALL" && !evt.action.includes(actionFilter)) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchAction = evt.action.toLowerCase().includes(q);
      const matchActor = evt.actor_id.toLowerCase().includes(q);
      const matchResource = (evt.resource_type + ":" + evt.resource_id).toLowerCase().includes(q);
      return matchAction || matchActor || matchResource;
    }
    return true;
  });

  const getActionBadgeStyle = (action: string) => {
    if (action.includes("ALERT")) return "bg-[rgba(255,138,0,0.1)] text-[#FF9D1A] border-[rgba(255,138,0,0.3)] shadow-[0_0_10px_rgba(255,138,0,0.15)]";
    if (action.includes("VERIF") || action.includes("DOCUMENT")) return "bg-[rgba(56,189,248,0.1)] text-[#38BDF8] border-[rgba(56,189,248,0.3)] shadow-[0_0_10px_rgba(56,189,248,0.15)]";
    if (action.includes("REPORT")) return "bg-[rgba(192,132,252,0.1)] text-[#C084FC] border-[rgba(192,132,252,0.3)] shadow-[0_0_10px_rgba(192,132,252,0.15)]";
    if (action.includes("AUTH") || action.includes("USER")) return "bg-[rgba(161,161,170,0.1)] text-[#D4D4D8] border-[rgba(161,161,170,0.3)] shadow-[0_0_10px_rgba(161,161,170,0.15)]";
    return "bg-[rgba(255,255,255,0.05)] text-[#A1A1AA] border-[rgba(255,255,255,0.1)]";
  };

  return (
    <div 
      className="min-h-screen pb-[48px] relative overflow-hidden font-['Space_Grotesk',sans-serif]"
      style={{ backgroundColor: "#050607" }}
    >
      {/* Ambient Glow */}
      <div className="absolute top-[10%] left-[15%] w-[40%] h-[30%] rounded-full opacity-[0.03] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[20%] right-[10%] w-[50%] h-[40%] rounded-full opacity-[0.02] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        {/* Header Banner */}
        <div 
          className="rounded-[20px] p-[32px] flex flex-col lg:flex-row lg:items-center justify-between gap-6 transition-all duration-300 relative overflow-hidden group"
          style={{
            background: "rgba(10, 10, 10, 0.72)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            border: "1px solid rgba(255, 138, 0, 0.35)",
            boxShadow: "0 0 30px rgba(255, 138, 0, 0.08), inset 0 0 20px rgba(255,138,0,0.05)"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = "0 10px 40px rgba(255, 138, 0, 0.12), inset 0 0 30px rgba(255,138,0,0.08)";
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.45)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "0 0 30px rgba(255, 138, 0, 0.08), inset 0 0 20px rgba(255,138,0,0.05)";
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.35)";
          }}
        >
          {/* Header internal glow */}
          <div className="absolute top-0 left-0 w-[40%] h-[150%] rounded-full opacity-[0.03] blur-[50px] pointer-events-none" style={{ background: "#FF8A00" }}></div>

          <div className="relative z-10 flex items-center gap-[24px]">
            <div 
              className="w-[60px] h-[60px] rounded-[16px] flex items-center justify-center shrink-0 border transition-all duration-300"
              style={{ background: "rgba(255, 138, 0, 0.08)", borderColor: "rgba(255, 138, 0, 0.4)", boxShadow: "0 0 20px rgba(255,138,0,0.15)" }}
            >
              <ShieldCheck className="w-8 h-8 text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]" />
            </div>
            <div>
              <div className="flex items-center gap-4 flex-wrap mb-[8px]">
                <h1 className="text-[24px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                  IMMUTABLE OPERATIONAL AUDIT LOGS
                </h1>
                <span 
                  className="text-[11px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider flex items-center gap-1.5"
                  style={{ background: "rgba(16,185,129,0.1)", color: "#34D399", border: "1px solid rgba(16,185,129,0.3)", boxShadow: "0 0 10px rgba(16,185,129,0.15)" }}
                >
                  <Lock className="w-3.5 h-3.5" /> APPEND-ONLY RLS ENFORCED
                </span>
              </div>
              <p className="text-[13px] text-[#A1A1AA] font-['Inter',sans-serif] max-w-3xl leading-relaxed">
                Tamper-proof compliance log capturing engineer decisions, alert acknowledgments, document verifications, and report dispatches.
              </p>
            </div>
          </div>

          <div className="relative z-10 flex items-center gap-[16px] shrink-0">
            <button
              onClick={exportCSV}
              disabled={events.length === 0}
              className="flex items-center gap-[8px] px-[24px] py-[12px] rounded-[12px] font-[700] text-[13px] uppercase tracking-wider transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
              style={{ background: "rgba(255,138,0,0.15)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.4)" }}
              onMouseEnter={(e) => {
                if(events.length > 0) {
                  e.currentTarget.style.background = "rgba(255,138,0,0.25)";
                  e.currentTarget.style.borderColor = "#FF9D1A";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.25)";
                  e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                }
              }}
              onMouseLeave={(e) => {
                if(events.length > 0) {
                  e.currentTarget.style.background = "rgba(255,138,0,0.15)";
                  e.currentTarget.style.borderColor = "rgba(255,138,0,0.4)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.transform = "none";
                }
              }}
            >
              <Download className="w-4 h-4" /> EXPORT CSV
            </button>

            <button
              onClick={loadAuditLogs}
              className="flex items-center gap-[8px] px-[20px] py-[12px] rounded-[12px] font-[700] text-[13px] uppercase tracking-wider transition-all duration-200"
              style={{ background: "rgba(255,255,255,0.03)", color: "#D4D4D8", border: "1px solid rgba(255,255,255,0.1)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,138,0,0.1)";
                e.currentTarget.style.borderColor = "rgba(255,138,0,0.4)";
                e.currentTarget.style.color = "#FF9D1A";
                e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.15)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                e.currentTarget.style.color = "#D4D4D8";
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
              }}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> REFRESH
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-col lg:flex-row items-center gap-[24px]">
          {/* Search Field */}
          <div 
            className="flex-1 w-full flex items-center gap-[12px] px-[20px] py-[16px] rounded-[16px] transition-all duration-300 group"
            style={{
              background: "rgba(10, 10, 10, 0.72)",
              backdropFilter: "blur(18px)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              boxShadow: "0 5px 20px rgba(0,0,0,0.4)"
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
              e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.15)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
              e.currentTarget.style.boxShadow = "0 5px 20px rgba(0,0,0,0.4)";
            }}
          >
            <Search className="w-5 h-5 text-[#FF8A00] drop-shadow-[0_0_5px_rgba(255,138,0,0.6)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search action, actor ID, or resource..."
              className="bg-transparent border-none text-[#F5F5F5] font-['Inter',sans-serif] text-[14px] w-full focus:outline-none placeholder:text-[#6B7280]"
            />
          </div>

          {/* Filter Controls */}
          <div 
            className="flex items-center gap-[12px] px-[24px] py-[14px] rounded-[16px] w-full lg:w-auto overflow-x-auto custom-scrollbar"
            style={{
              background: "rgba(10, 10, 10, 0.72)",
              backdropFilter: "blur(18px)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            <div className="flex items-center gap-[8px] mr-[8px]">
              <Filter className="w-4 h-4 text-[#FF8A00]" />
              <span className="text-[12px] text-white font-[700] uppercase tracking-wider">Filter:</span>
            </div>
            {(["ALL", "ALERT", "DOCUMENT", "REPORT", "USER"] as const).map((category) => {
              const isActive = actionFilter === category;
              return (
                <button
                  key={category}
                  onClick={() => setActionFilter(category)}
                  className="px-[16px] py-[8px] rounded-[8px] text-[11px] font-[700] uppercase tracking-wider transition-all duration-200 shrink-0"
                  style={
                    isActive
                      ? {
                          background: "rgba(255, 138, 0, 0.2)",
                          color: "#FF9D1A",
                          border: "1px solid rgba(255, 138, 0, 0.5)",
                          boxShadow: "0 0 15px rgba(255, 138, 0, 0.2)"
                        }
                      : {
                          background: "rgba(255, 255, 255, 0.03)",
                          color: "#A1A1AA",
                          border: "1px solid rgba(255, 255, 255, 0.08)",
                          boxShadow: "none"
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "rgba(255, 138, 0, 0.08)";
                      e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.3)";
                      e.currentTarget.style.color = "#FF9D1A";
                      e.currentTarget.style.boxShadow = "0 0 10px rgba(255, 138, 0, 0.1)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
                      e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
                      e.currentTarget.style.color = "#A1A1AA";
                      e.currentTarget.style.boxShadow = "none";
                    }
                  }}
                >
                  {category}
                </button>
              );
            })}
          </div>
        </div>

        {/* Audit Log Table Container */}
        <div 
          className="rounded-[20px] overflow-hidden flex flex-col transition-all duration-300 group relative"
          style={{
            background: "rgba(10, 10, 10, 0.72)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 138, 0, 0.25)",
            boxShadow: "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)"
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
            e.currentTarget.style.boxShadow = "0 15px 50px rgba(0,0,0,0.5), 0 0 30px rgba(255,138,0,0.08), inset 0 0 30px rgba(255,138,0,0.08)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
            e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)";
          }}
        >
          {/* Header Row */}
          <div className="p-[24px] border-b border-[rgba(255,138,0,0.15)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <span className="text-[14px] font-[700] text-white font-['Space_Grotesk',sans-serif] uppercase tracking-wider">
              Audit Records <span className="text-[#FF9D1A]">({filteredEvents.length} shown)</span>
            </span>
            <span 
              className="text-[11px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider flex items-center gap-1.5"
              style={{ background: "rgba(16,185,129,0.05)", color: "#34D399", border: "1px solid rgba(16,185,129,0.2)" }}
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> DB RLS Policy: UPDATE & DELETE Blocked
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[1000px]">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.2)]">
                  <th className="p-[16px] w-[40px]"></th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">AUDIT ID</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">TIMESTAMP</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">ACTOR</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">ROLE</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">ACTION</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">RESOURCE</th>
                  <th className="p-[16px] text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-widest font-mono">WELL ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.03)] font-mono text-[12px]">
                {filteredEvents.length === 0 && !loading && (
                  <tr>
                    <td colSpan={8} className="p-[80px]">
                      <div className="flex flex-col items-center justify-center space-y-[20px]">
                        <div className="relative flex items-center justify-center">
                          <div className="absolute inset-0 bg-[#FF8A00] opacity-[0.05] blur-[40px] rounded-full"></div>
                          <div 
                            className="w-[80px] h-[80px] rounded-full flex items-center justify-center border relative z-10"
                            style={{ background: "rgba(255,138,0,0.05)", borderColor: "rgba(255,138,0,0.3)", boxShadow: "0 0 30px rgba(255,138,0,0.15), inset 0 0 20px rgba(255,138,0,0.05)" }}
                          >
                            <FileSearch className="w-[32px] h-[32px] text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]" strokeWidth={1.5} />
                          </div>
                        </div>
                        <div className="text-center space-y-[8px]">
                          <div className="text-[18px] font-[700] text-white font-sans tracking-wide">No operational audit events found</div>
                          <div className="text-[13px] text-[#6B7280] font-sans">No events match the current filters.</div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
                {filteredEvents.map((evt) => {
                  const isExpanded = expandedAuditId === evt.audit_id;
                  return (
                    <React.Fragment key={evt.audit_id}>
                      <tr
                        onClick={() => toggleExpand(evt.audit_id)}
                        className="cursor-pointer transition-all duration-200 group"
                        style={{ background: "transparent" }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = "rgba(255,138,0,0.03)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = "transparent";
                        }}
                      >
                        <td className="p-[16px]">
                          <div className="w-[24px] h-[24px] rounded-[6px] flex items-center justify-center border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.03)] group-hover:border-[#FF8A00] group-hover:text-[#FF8A00] transition-colors">
                            {isExpanded ? <ChevronDown className="w-4 h-4 text-[#FF9D1A]" /> : <ChevronRight className="w-4 h-4 text-[#A1A1AA]" />}
                          </div>
                        </td>
                        <td className="p-[16px] font-[700] text-[#FF9D1A] tracking-wider">{evt.audit_id}</td>
                        <td className="p-[16px] text-[#D4D4D8]">{new Date(evt.timestamp).toLocaleString()}</td>
                        <td className="p-[16px] text-white font-[700]">{evt.actor_id}</td>
                        <td className="p-[16px]">
                          <span className="px-[8px] py-[4px] rounded-[6px] bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-[#D4D4D8] font-[700] text-[10px] uppercase tracking-wider">
                            {evt.actor_role || "SYSTEM"}
                          </span>
                        </td>
                        <td className="p-[16px]">
                          <span className={`px-[8px] py-[4px] rounded-[6px] text-[10px] font-[700] uppercase tracking-wider border ${getActionBadgeStyle(evt.action)}`}>
                            {evt.action}
                          </span>
                        </td>
                        <td className="p-[16px] text-[#A1A1AA]">{evt.resource_type}:{evt.resource_id}</td>
                        <td className="p-[16px] text-white font-[700]">{evt.well_id || "N/A"}</td>
                      </tr>

                      {/* State Diff & Payload Inspector */}
                      {isExpanded && (
                        <tr style={{ background: "rgba(0,0,0,0.4)" }} className="border-b border-[rgba(255,138,0,0.15)]">
                          <td colSpan={8} className="p-[24px]">
                            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.05)] pb-[12px] mb-[16px]">
                              <span className="text-[12px] font-[700] text-[#E2E2E2] uppercase tracking-widest font-sans flex items-center gap-[8px]">
                                <FileSearch className="w-4 h-4 text-[#FF8A00]" />
                                Payload & State Diff Inspector <span className="text-[#A1A1AA]">({evt.audit_id})</span>
                              </span>
                              <span className="text-[10px] text-[#6B7280] uppercase tracking-widest">Organization: {evt.organization_id}</span>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-[16px]">
                              <div className="p-[16px] rounded-[12px] border border-[rgba(255,255,255,0.05)] bg-[rgba(5,5,5,0.6)] backdrop-blur-md">
                                <span className="text-[10px] text-[#A1A1AA] font-[700] block uppercase tracking-widest mb-[12px]">BEFORE STATE</span>
                                <pre className="text-[11px] text-[#D4D4D8] overflow-x-auto custom-scrollbar">
                                  {evt.before_state ? JSON.stringify(evt.before_state, null, 2) : "None (New Creation)"}
                                </pre>
                              </div>

                              <div className="p-[16px] rounded-[12px] border border-[rgba(16,185,129,0.2)] bg-[rgba(16,185,129,0.05)] backdrop-blur-md shadow-[inset_0_0_20px_rgba(16,185,129,0.02)]">
                                <span className="text-[10px] text-[#34D399] font-[700] block uppercase tracking-widest mb-[12px] drop-shadow-sm">AFTER STATE</span>
                                <pre className="text-[11px] text-[#D4D4D8] overflow-x-auto custom-scrollbar">
                                  {evt.after_state ? JSON.stringify(evt.after_state, null, 2) : "Recorded Action"}
                                </pre>
                              </div>

                              <div className="p-[16px] rounded-[12px] border border-[rgba(255,138,0,0.2)] bg-[rgba(255,138,0,0.05)] backdrop-blur-md shadow-[inset_0_0_20px_rgba(255,138,0,0.02)]">
                                <span className="text-[10px] text-[#FF9D1A] font-[700] block uppercase tracking-widest mb-[12px] drop-shadow-sm">EVENT PAYLOAD METADATA</span>
                                <pre className="text-[11px] text-[#D4D4D8] overflow-x-auto custom-scrollbar">
                                  {evt.payload ? JSON.stringify(evt.payload, null, 2) : "{}"}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
