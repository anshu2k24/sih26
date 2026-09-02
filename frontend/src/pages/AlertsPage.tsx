import React, { useState, useEffect } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import {
  fetchAlerts,
  acknowledgeAlertApi,
  investigateAlertApi,
  assignAlertApi,
  resolveAlertApi,
  fetchAlertNotes,
  addAlertNoteApi,
} from "../services/api";
import type { AlertItem, AlertNoteItem } from "../types/api";
import {
  ShieldAlert,
  RefreshCw,
  X,
  UserCheck,
  Search,
  MessageSquare,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Send,
  TriangleAlert
} from "lucide-react";

export const AlertsPage: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [selectedAlertModal, setSelectedAlertModal] = useState<AlertItem | null>(null);

  // Modal interaction state
  const [resolveNotes, setResolveNotes] = useState<string>("");
  const [assigneeId, setAssigneeId] = useState<string>("");
  const [newNoteText, setNewNoteText] = useState<string>("");
  const [alertNotes, setAlertNotes] = useState<AlertNoteItem[]>([]);
  const [notesLoading, setNotesLoading] = useState<boolean>(false);

  const loadAlerts = () => {
    setLoading(true);
    fetchAlerts(selectedWell)
      .then((res) => {
        if (res && res.alerts) {
          setAlerts(res.alerts);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadAlerts();
  }, [selectedWell]);

  useEffect(() => {
    if (selectedAlertModal) {
      setNotesLoading(true);
      fetchAlertNotes(selectedAlertModal.alert_id)
        .then((notes) => {
          setAlertNotes(notes);
          setNotesLoading(false);
        })
        .catch(() => setNotesLoading(false));
    } else {
      setAlertNotes([]);
      setResolveNotes("");
      setNewNoteText("");
      setAssigneeId("");
    }
  }, [selectedAlertModal]);

  const handleAcknowledge = async (alertId: string) => {
    await acknowledgeAlertApi(alertId);
    loadAlerts();
    if (selectedAlertModal?.alert_id === alertId) {
      setSelectedAlertModal(null);
    }
  };

  const handleStartInvestigation = async (alertId: string) => {
    await investigateAlertApi(alertId);
    loadAlerts();
    if (selectedAlertModal?.alert_id === alertId) {
      setSelectedAlertModal(null);
    }
  };

  const handleAssign = async (alertId: string) => {
    if (!assigneeId.trim()) return;
    await assignAlertApi(alertId, assigneeId);
    loadAlerts();
    setAssigneeId("");
  };

  const handleAddNote = async (alertId: string) => {
    if (!newNoteText.trim()) return;
    const res = await addAlertNoteApi(alertId, newNoteText);
    if (res) {
      setNewNoteText("");
      const updatedNotes = await fetchAlertNotes(alertId);
      setAlertNotes(updatedNotes);
    }
  };

  const handleResolve = async (alertId: string) => {
    if (!resolveNotes.trim()) return;
    await resolveAlertApi(alertId, resolveNotes);
    setResolveNotes("");
    setSelectedAlertModal(null);
    loadAlerts();
  };

  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return {
          background: "rgba(225, 29, 72, 0.15)",
          color: "#FB7185",
          border: "1px solid rgba(225, 29, 72, 0.5)",
          boxShadow: "0 0 10px rgba(225, 29, 72, 0.2)"
        };
      case "HIGH":
        return {
          background: "rgba(234, 88, 12, 0.15)",
          color: "#FB923C",
          border: "1px solid rgba(234, 88, 12, 0.5)",
          boxShadow: "0 0 10px rgba(234, 88, 12, 0.2)"
        };
      case "MEDIUM":
        return {
          background: "rgba(168, 85, 247, 0.15)",
          color: "#C084FC",
          border: "1px solid rgba(168, 85, 247, 0.5)",
          boxShadow: "0 0 10px rgba(168, 85, 247, 0.2)"
        };
      default:
        return {
          background: "rgba(148, 163, 184, 0.1)",
          color: "#94A3B8",
          border: "1px solid rgba(148, 163, 184, 0.3)",
          boxShadow: "none"
        };
    }
  };

  const filteredAlerts = alerts.filter((alt) => {
    if (activeTab === "ALL") return true;
    return alt.status === activeTab;
  });

  const counts = {
    ALL: alerts.length,
    ACTIVE: alerts.filter((a) => a.status === "ACTIVE").length,
    ACKNOWLEDGED: alerts.filter((a) => a.status === "ACKNOWLEDGED").length,
    INVESTIGATING: alerts.filter((a) => a.status === "INVESTIGATING").length,
    RESOLVED: alerts.filter((a) => a.status === "RESOLVED").length,
  };

  return (
    <div 
      className="min-h-screen pb-[48px] relative overflow-hidden"
      style={{ backgroundColor: "#050607", fontFamily: "'Space Grotesk', 'Inter', sans-serif" }}
    >
      {/* Absolute Ambient Background Lights */}
      <div className="absolute top-[5%] left-[20%] w-[60%] h-[40%] rounded-full opacity-[0.04] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[20%] right-[10%] w-[50%] h-[40%] rounded-full opacity-[0.03] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        
        {/* Page Header */}
        <div 
          className="rounded-[20px] p-[28px] flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all duration-300 relative overflow-hidden"
          style={{
            background: "rgba(18, 16, 14, 0.75)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
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
                <ShieldAlert className="w-5 h-5 text-[#FF9D1A]" />
              </div>
              <h1 className="text-[20px] sm:text-[24px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                REAL-TIME OPERATIONS ALERT CENTER
              </h1>
              <span 
                className="text-[10px] px-[10px] py-[4px] rounded-[6px] font-[700] uppercase tracking-wider whitespace-nowrap"
                style={{ background: "rgba(18, 16, 14, 0.8)", color: "#FF8A00", border: "1px solid rgba(255, 138, 0, 0.4)", boxShadow: "0 0 10px rgba(255, 138, 0, 0.15)" }}
              >
                FULL LIFECYCLE MANAGED
              </span>
            </div>
            <p className="text-[13px] text-[#A1A1AA] mt-3 font-['Inter',sans-serif] max-w-3xl leading-relaxed">
              Real-time operational dispatches, assignment tracking, investigation notes, and immutable resolution audit log.
            </p>
          </div>

          <button
            onClick={loadAlerts}
            className="group relative z-10 inline-flex items-center gap-2 px-[24px] py-[12px] rounded-[12px] font-[700] text-[12px] tracking-wide text-white transition-all duration-200"
            style={{
              background: "rgba(18, 16, 14, 0.8)",
              border: "1px solid rgba(255, 138, 0, 0.4)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "radial-gradient(circle at top right, rgba(255,138,0,0.25), rgba(255,138,0,0.1) 70%)";
              e.currentTarget.style.borderColor = "#FF9D1A";
              e.currentTarget.style.boxShadow = "0 6px 20px rgba(255, 138, 0, 0.3), inset 0 0 15px rgba(255, 138, 0, 0.2)";
              e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(18, 16, 14, 0.8)";
              e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
              e.currentTarget.style.boxShadow = "none";
              e.currentTarget.style.transform = "none";
            }}
          >
            <RefreshCw className={`w-4 h-4 text-[#FF8A00] group-hover:brightness-125 ${loading ? "animate-spin" : ""}`} />
            REFRESH
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-[12px] border-b border-[#2A2A2A] pb-[16px]">
          {(["ALL", "ACTIVE", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"] as const).map((tab) => {
            const isSelected = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className="px-[20px] py-[10px] rounded-[10px] text-[11px] font-[700] tracking-wider whitespace-nowrap transition-all duration-200 flex items-center gap-2.5"
                style={
                  isSelected
                    ? {
                        background: "radial-gradient(circle at top, rgba(255,138,0,0.35), rgba(255,138,0,0.15))",
                        color: "#FFFFFF",
                        border: "1px solid rgba(255, 138, 0, 0.8)",
                        boxShadow: "0 4px 20px rgba(255, 138, 0, 0.25), inset 0 0 15px rgba(255,138,0,0.2)",
                        textShadow: "0 0 8px rgba(255,138,0,0.5)"
                      }
                    : {
                        background: "rgba(20, 20, 20, 0.5)",
                        color: "#A1A1AA",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
                      }
                }
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = "rgba(255, 138, 0, 0.08)";
                    e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.3)";
                    e.currentTarget.style.color = "#FF9D1A";
                    e.currentTarget.style.boxShadow = "0 4px 15px rgba(255,138,0,0.1)";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  } else {
                    e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,138,0,0.45), rgba(255,138,0,0.2))";
                    e.currentTarget.style.boxShadow = "0 6px 25px rgba(255, 138, 0, 0.35), inset 0 0 20px rgba(255,138,0,0.3)";
                    e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = "rgba(20, 20, 20, 0.5)";
                    e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
                    e.currentTarget.style.color = "#A1A1AA";
                    e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
                    e.currentTarget.style.transform = "none";
                  } else {
                    e.currentTarget.style.background = "radial-gradient(circle at top, rgba(255,138,0,0.35), rgba(255,138,0,0.15))";
                    e.currentTarget.style.boxShadow = "0 4px 20px rgba(255, 138, 0, 0.25), inset 0 0 15px rgba(255,138,0,0.2)";
                    e.currentTarget.style.transform = "none";
                  }
                }}
              >
                <span>{tab}</span>
                <span
                  className="text-[10px] px-[6px] py-[2px] rounded-[4px] font-[700] transition-colors"
                  style={
                    isSelected 
                      ? { background: "rgba(18,16,14,0.6)", color: "#FF9D1A" }
                      : { background: "rgba(0,0,0,0.5)", color: "#686868" }
                  }
                >
                  {counts[tab]}
                </span>
              </button>
            );
          })}
        </div>

        {/* Alerts List */}
        <div className="space-y-[20px]">
          {filteredAlerts.length === 0 && !loading && (
            <div 
              className="rounded-[20px] p-[60px] text-center transition-all duration-300"
              style={{
                background: "rgba(18, 16, 14, 0.6)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(255, 255, 255, 0.05)",
                boxShadow: "inset 0 0 40px rgba(0,0,0,0.5)"
              }}
            >
              <CheckCircle2 className="w-[48px] h-[48px] text-[#34D399] opacity-30 mx-auto mb-4" />
              <p className="text-[14px] text-[#686868] font-mono tracking-widest uppercase">
                No alerts found in category [{activeTab}] for well {selectedWell}. System nominal.
              </p>
            </div>
          )}

          {filteredAlerts.map((alt) => (
            <div 
              key={alt.alert_id} 
              className="rounded-[20px] p-[24px] flex flex-col gap-[16px] transition-all duration-300 group"
              style={{
                background: "rgba(18, 16, 14, 0.75)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                border: "1px solid rgba(255, 138, 0, 0.15)",
                boxShadow: "0 10px 40px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,138,0,0.02)"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
                e.currentTarget.style.boxShadow = "0 15px 50px rgba(0,0,0,0.4), 0 0 25px rgba(255,138,0,0.15), 0 0 60px rgba(255,138,0,0.06), inset 0 0 30px rgba(255,138,0,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.15)";
                e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.3), inset 0 0 20px rgba(255,138,0,0.02)";
              }}
            >
              {/* Alert Header */}
              <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
                <div className="flex items-center gap-[12px] flex-wrap">
                  <span 
                    className="text-[10px] px-[12px] py-[4px] rounded-[6px] font-[700] tracking-wider uppercase" 
                    style={getSeverityStyle(alt.severity)}
                  >
                    {alt.severity}
                  </span>
                  <span className="text-white font-[700] text-[16px] tracking-wide drop-shadow-sm">
                    {alt.title}
                  </span>
                  <span className="text-[#9A9A9A] text-[14px] font-mono">
                    ({alt.well_id})
                  </span>
                  <span className="text-[10px] px-[10px] py-[4px] rounded-[6px] font-mono uppercase tracking-wider" style={{ background: "rgba(20,20,20,0.8)", border: "1px solid rgba(255,255,255,0.1)", color: "#9A9A9A" }}>
                    SOURCE: {alt.source}
                  </span>
                </div>

                {/* Lifecycle Actions */}
                <div className="flex items-center gap-[12px] flex-wrap">
                  <span 
                    className="px-[12px] py-[6px] rounded-[8px] border text-[10px] font-[700] tracking-wider uppercase"
                    style={{ background: "rgba(255,255,255,0.03)", borderColor: "rgba(255,255,255,0.1)", color: "#A1A1AA" }}
                  >
                    {alt.status}
                  </span>

                  {alt.status === "ACTIVE" && (
                    <button
                      onClick={() => handleAcknowledge(alt.alert_id)}
                      className="px-[16px] py-[8px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider flex items-center gap-2"
                      style={{ background: "rgba(255, 138, 0, 0.15)", color: "#FF9D1A", border: "1px solid rgba(255, 138, 0, 0.4)" }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "rgba(255, 138, 0, 0.3)";
                        e.currentTarget.style.borderColor = "#FF9D1A";
                        e.currentTarget.style.boxShadow = "0 0 20px rgba(255, 138, 0, 0.3)";
                        e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "rgba(255, 138, 0, 0.15)";
                        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
                        e.currentTarget.style.boxShadow = "none";
                        e.currentTarget.style.transform = "none";
                      }}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> ACKNOWLEDGE
                    </button>
                  )}

                  {(alt.status === "ACTIVE" || alt.status === "ACKNOWLEDGED") && (
                    <button
                      onClick={() => handleStartInvestigation(alt.alert_id)}
                      className="px-[16px] py-[8px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider flex items-center gap-2"
                      style={{ background: "rgba(59, 130, 246, 0.15)", color: "#60A5FA", border: "1px solid rgba(59, 130, 246, 0.4)" }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "rgba(59, 130, 246, 0.3)";
                        e.currentTarget.style.borderColor = "#93C5FD";
                        e.currentTarget.style.boxShadow = "0 0 20px rgba(59, 130, 246, 0.3)";
                        e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "rgba(59, 130, 246, 0.15)";
                        e.currentTarget.style.borderColor = "rgba(59, 130, 246, 0.4)";
                        e.currentTarget.style.boxShadow = "none";
                        e.currentTarget.style.transform = "none";
                      }}
                    >
                      <Search className="w-3.5 h-3.5" /> INVESTIGATE
                    </button>
                  )}

                  <button
                    onClick={() => setSelectedAlertModal(alt)}
                    className="px-[16px] py-[8px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider flex items-center gap-2"
                    style={{ background: "rgba(255, 255, 255, 0.05)", color: "#F2F2F2", border: "1px solid rgba(255, 255, 255, 0.15)" }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(255, 138, 0, 0.1)";
                      e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.5)";
                      e.currentTarget.style.color = "#FF9D1A";
                      e.currentTarget.style.boxShadow = "0 0 15px rgba(255, 138, 0, 0.15)";
                      e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                      e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.15)";
                      e.currentTarget.style.color = "#F2F2F2";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.transform = "none";
                    }}
                  >
                    <MessageSquare className="w-3.5 h-3.5 opacity-80" /> DETAILS & NOTES
                  </button>
                </div>
              </div>

              {/* Evidence Panel */}
              <div 
                className="rounded-[12px] p-[20px] relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between"
                style={{
                  background: "rgba(5, 7, 9, 0.75)",
                  backdropFilter: "blur(10px)",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                {/* Vertical Orange Accent Line */}
                <div className="absolute top-0 left-0 w-[4px] h-full bg-[#FF8A00] opacity-80 shadow-[0_0_10px_#FF8A00]"></div>
                
                <div className="flex-1 pr-6 z-10">
                  <span className="text-[#FF8A00] font-mono block text-[11px] font-[700] uppercase mb-2 tracking-wider drop-shadow-sm">
                    Evidence & Context:
                  </span>
                  <p className="text-[13px] text-[#E2E2E2] font-mono leading-relaxed whitespace-pre-wrap">
                    {alt.evidence}
                  </p>
                </div>

                {/* Decorative Warning Element (Right side) */}
                <div className="hidden md:flex shrink-0 relative w-[120px] h-[120px] items-center justify-center opacity-80 z-0">
                  {/* Faint Radar Rings */}
                  <div className="absolute inset-0 rounded-full border border-[#FF3250] opacity-10 scale-[0.6]"></div>
                  <div className="absolute inset-0 rounded-full border border-[#FF3250] opacity-5 scale-[0.8]"></div>
                  <div className="absolute inset-0 rounded-full border border-[#FF3250] opacity-5 scale-100"></div>
                  {/* Core Icon */}
                  <TriangleAlert className="w-[48px] h-[48px] text-[#FF3250] drop-shadow-[0_0_15px_rgba(255,50,80,0.6)]" strokeWidth={1.5} />
                  {/* Subtle Radial Glow */}
                  <div className="absolute inset-0 rounded-full bg-[#FF3250] opacity-[0.03] blur-[20px]"></div>
                </div>
              </div>

              {/* Alert Footer */}
              <div className="flex flex-col md:flex-row md:items-center justify-between text-[11px] font-mono tracking-wider pt-[8px]">
                <div className="flex items-center gap-[16px]">
                  <span className="text-[#686868]">
                    MD: <strong className="text-white text-[12px]">{alt.current_md.toFixed(1)} m</strong>
                  </span>
                  {alt.assigned_to && (
                    <span className="flex items-center gap-1.5 text-[#60A5FA] font-[700] bg-[rgba(59,130,246,0.1)] px-[8px] py-[4px] rounded-[6px] border border-[rgba(59,130,246,0.3)]">
                      <UserCheck className="w-3.5 h-3.5" /> Assigned: {alt.assigned_to}
                    </span>
                  )}
                </div>
                
                <span className="text-[#FF9D1A] font-[700] uppercase tracking-widest drop-shadow-[0_0_5px_rgba(255,157,26,0.5)] my-3 md:my-0">
                  {alt.disclaimer}
                </span>
                
                <span className="flex items-center gap-1.5 text-[#9A9A9A]">
                  <Clock className="w-3.5 h-3.5 opacity-70" /> {new Date(alt.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal: Details, Notes & Resolution */}
        {selectedAlertModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 font-mono">
            {/* Modal Backdrop */}
            <div 
              className="absolute inset-0 bg-[#000000] opacity-80 backdrop-blur-md"
              onClick={() => setSelectedAlertModal(null)}
            ></div>
            
            {/* Modal Panel */}
            <div 
              className="relative z-10 rounded-[20px] max-w-3xl w-full p-[32px] space-y-[20px] max-h-[90vh] overflow-y-auto custom-scrollbar transition-all duration-300"
              style={{
                background: "rgba(18, 16, 14, 0.9)",
                backdropFilter: "blur(24px)",
                border: "1px solid rgba(255, 138, 0, 0.3)",
                boxShadow: "0 25px 80px rgba(0,0,0,0.8), inset 0 0 30px rgba(255,138,0,0.05)"
              }}
            >
              <button
                onClick={() => setSelectedAlertModal(null)}
                className="absolute top-[24px] right-[24px] text-[#A1A1AA] hover:text-[#FF8A00] transition-colors p-2"
              >
                <X className="w-6 h-6" />
              </button>

              <div className="flex items-center gap-4 border-b border-[rgba(255,255,255,0.1)] pb-[16px]">
                <AlertOctagon className="w-6 h-6 text-[#FF9D1A] drop-shadow-[0_0_10px_#FF9D1A]" />
                <div>
                  <h2 className="text-[18px] font-[700] text-white uppercase tracking-wider font-sans">
                    Alert Lifecycle Operations ({selectedAlertModal.alert_id})
                  </h2>
                  <p className="text-[12px] text-[#9A9A9A] mt-1">Wellbore: {selectedAlertModal.well_id} | Created: {selectedAlertModal.created_at}</p>
                </div>
              </div>

              {/* Alert Overview */}
              <div 
                className="grid grid-cols-2 md:grid-cols-4 gap-[12px] p-[16px] rounded-[12px]"
                style={{ background: "rgba(5,7,9,0.7)", border: "1px solid rgba(255,255,255,0.05)" }}
              >
                <div>
                  <span className="text-[#686868] text-[10px] block mb-1 tracking-wider">SEVERITY</span>
                  <strong 
                    className="px-[8px] py-[4px] rounded-[4px] inline-block text-[10px] font-[700]" 
                    style={getSeverityStyle(selectedAlertModal.severity)}
                  >
                    {selectedAlertModal.severity}
                  </strong>
                </div>
                <div>
                  <span className="text-[#686868] text-[10px] block mb-1 tracking-wider">STATUS</span>
                  <strong 
                    className="px-[8px] py-[4px] rounded-[4px] inline-block text-[10px] font-[700] border"
                    style={{ background: "rgba(255,255,255,0.05)", borderColor: "rgba(255,255,255,0.15)", color: "#F2F2F2" }}
                  >
                    {selectedAlertModal.status}
                  </strong>
                </div>
                <div>
                  <span className="text-[#686868] text-[10px] block mb-1 tracking-wider">MEASURED DEPTH</span>
                  <strong className="text-white text-[14px]">{selectedAlertModal.current_md.toFixed(1)} m</strong>
                </div>
                <div>
                  <span className="text-[#686868] text-[10px] block mb-1 tracking-wider">ASSIGNED TO</span>
                  <strong className="text-[#60A5FA] text-[12px]">{selectedAlertModal.assigned_to || "Unassigned"}</strong>
                </div>
              </div>

              {/* Assignment Section */}
              {selectedAlertModal.status !== "RESOLVED" && (
                <div 
                  className="p-[16px] rounded-[12px] space-y-[12px]"
                  style={{ background: "rgba(5,7,9,0.7)", border: "1px solid rgba(255,255,255,0.05)" }}
                >
                  <span className="text-[#F2F2F2] font-[700] block text-[11px] uppercase tracking-wider">Assign Alert to Engineer</span>
                  <div className="flex gap-[12px]">
                    <input
                      type="text"
                      value={assigneeId}
                      onChange={(e) => setAssigneeId(e.target.value)}
                      placeholder="Enter engineer UUID / username"
                      className="flex-1 rounded-[8px] px-[16px] py-[10px] text-[12px] text-white outline-none transition-all placeholder:text-[#686868]"
                      style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.1)" }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = "rgba(59,130,246,0.6)";
                        e.currentTarget.style.boxShadow = "0 0 15px rgba(59,130,246,0.2)";
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    />
                    <button
                      onClick={() => handleAssign(selectedAlertModal.alert_id)}
                      disabled={!assigneeId.trim()}
                      className="px-[24px] py-[10px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider disabled:opacity-50"
                      style={{ background: "rgba(59, 130, 246, 0.15)", color: "#60A5FA", border: "1px solid rgba(59, 130, 246, 0.4)" }}
                      onMouseEnter={(e) => {
                        if (e.currentTarget.disabled) return;
                        e.currentTarget.style.background = "rgba(59, 130, 246, 0.3)";
                        e.currentTarget.style.boxShadow = "0 0 20px rgba(59, 130, 246, 0.3)";
                      }}
                      onMouseLeave={(e) => {
                        if (e.currentTarget.disabled) return;
                        e.currentTarget.style.background = "rgba(59, 130, 246, 0.15)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    >
                      ASSIGN
                    </button>
                  </div>
                </div>
              )}

              {/* Notes Thread */}
              <div className="space-y-[12px]">
                <span className="text-[11px] font-[700] text-[#A1A1AA] uppercase tracking-wider block">Operational Notes Thread</span>
                <div 
                  className="p-[16px] rounded-[12px] space-y-[12px] max-h-[180px] overflow-y-auto custom-scrollbar"
                  style={{ background: "rgba(5,7,9,0.7)", border: "1px solid rgba(255,255,255,0.05)" }}
                >
                  {notesLoading && <p className="text-[12px] text-[#686868] italic">Loading notes...</p>}
                  {!notesLoading && alertNotes.length === 0 && (
                    <p className="text-[12px] text-[#686868] italic">No notes added yet for this alert.</p>
                  )}
                  {alertNotes.map((n) => (
                    <div key={n.id} className="border-b border-[rgba(255,255,255,0.05)] pb-[12px] text-[12px] space-y-[4px]">
                      <div className="flex items-center justify-between text-[#9A9A9A] text-[10px] uppercase tracking-wider">
                        <span className="font-[700] text-[#FF9D1A]">{n.author_id}</span>
                        <span>{new Date(n.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-[#E2E2E2] leading-relaxed">{n.note_text}</p>
                    </div>
                  ))}
                </div>

                {/* Add Note Input */}
                {selectedAlertModal.status !== "RESOLVED" && (
                  <div className="flex gap-[12px]">
                    <input
                      type="text"
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      placeholder="Add operational investigation note..."
                      className="flex-1 rounded-[8px] px-[16px] py-[10px] text-[12px] text-white outline-none transition-all placeholder:text-[#686868]"
                      style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.1)" }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
                        e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.2)";
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    />
                    <button
                      onClick={() => handleAddNote(selectedAlertModal.alert_id)}
                      disabled={!newNoteText.trim()}
                      className="px-[20px] py-[10px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider flex items-center gap-2 disabled:opacity-50"
                      style={{ background: "rgba(255,255,255,0.05)", color: "#F2F2F2", border: "1px solid rgba(255,255,255,0.15)" }}
                      onMouseEnter={(e) => {
                        if (e.currentTarget.disabled) return;
                        e.currentTarget.style.background = "rgba(255, 138, 0, 0.1)";
                        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.5)";
                        e.currentTarget.style.color = "#FF9D1A";
                        e.currentTarget.style.boxShadow = "0 0 15px rgba(255, 138, 0, 0.15)";
                      }}
                      onMouseLeave={(e) => {
                        if (e.currentTarget.disabled) return;
                        e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                        e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)";
                        e.currentTarget.style.color = "#F2F2F2";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    >
                      <Send className="w-3.5 h-3.5" /> ADD NOTE
                    </button>
                  </div>
                )}
              </div>

              {/* Resolution Form */}
              {selectedAlertModal.status !== "RESOLVED" && (
                <div 
                  className="p-[20px] rounded-[12px] space-y-[16px]"
                  style={{ background: "rgba(5,7,9,0.7)", border: "1px solid rgba(255,255,255,0.05)" }}
                >
                  <label className="text-[#FF8A00] font-[700] block text-[11px] uppercase tracking-wider drop-shadow-sm">
                    Final Operational Resolution Summary:
                  </label>
                  <textarea
                    value={resolveNotes}
                    onChange={(e) => setResolveNotes(e.target.value)}
                    placeholder="Enter engineer investigation summary and resolution actions taken..."
                    className="w-full rounded-[10px] p-[16px] text-[13px] text-white outline-none transition-all placeholder:text-[#686868] resize-none h-[100px]"
                    style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.1)" }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = "rgba(16,185,129,0.5)";
                      e.currentTarget.style.boxShadow = "0 0 15px rgba(16,185,129,0.2)";
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  />
                  <button
                    onClick={() => handleResolve(selectedAlertModal.alert_id)}
                    disabled={!resolveNotes.trim()}
                    className="w-full py-[14px] rounded-[10px] font-[700] transition-all text-[12px] uppercase tracking-wider disabled:opacity-50"
                    style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34D399", border: "1px solid rgba(16, 185, 129, 0.4)" }}
                    onMouseEnter={(e) => {
                      if (e.currentTarget.disabled) return;
                      e.currentTarget.style.background = "rgba(16, 185, 129, 0.3)";
                      e.currentTarget.style.boxShadow = "0 0 25px rgba(16, 185, 129, 0.3)";
                      e.currentTarget.style.transform = "translateY(-1px) scale(1.01)";
                    }}
                    onMouseLeave={(e) => {
                      if (e.currentTarget.disabled) return;
                      e.currentTarget.style.background = "rgba(16, 185, 129, 0.15)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.transform = "none";
                    }}
                  >
                    CONFIRM RESOLUTION & CLOSE ALERT
                  </button>
                </div>
              )}

              {/* Resolved Summary View */}
              {selectedAlertModal.status === "RESOLVED" && (
                <div 
                  className="p-[20px] rounded-[12px] space-y-[12px]"
                  style={{ background: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)" }}
                >
                  <span className="text-[12px] font-[700] text-[#34D399] block uppercase tracking-wider flex items-center gap-2 drop-shadow-sm">
                    <CheckCircle2 className="w-5 h-5" /> RESOLVED OPERATIONAL SUMMARY
                  </span>
                  <p className="text-[13px] text-[#E2E2E2] leading-relaxed">{selectedAlertModal.resolution_notes || "No notes recorded."}</p>
                  <div className="text-[10px] text-[#9A9A9A] flex justify-between border-t border-[rgba(16,185,129,0.2)] pt-[12px] mt-[12px]">
                    <span className="uppercase tracking-wider">Resolved By: <strong className="text-white">{selectedAlertModal.resolved_by || "System"}</strong></span>
                    <span className="uppercase tracking-wider">Resolved At: {selectedAlertModal.resolved_at}</span>
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-[20px] border-t border-[rgba(255,255,255,0.1)]">
                <button
                  onClick={() => setSelectedAlertModal(null)}
                  className="px-[24px] py-[10px] rounded-[8px] font-[700] transition-all text-[11px] uppercase tracking-wider"
                  style={{ background: "rgba(255,255,255,0.05)", color: "#A1A1AA", border: "1px solid transparent" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.1)";
                    e.currentTarget.style.color = "#FFFFFF";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                    e.currentTarget.style.color = "#A1A1AA";
                  }}
                >
                  CLOSE WINDOW
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
