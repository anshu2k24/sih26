import React, { useState, useEffect } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import {
  fetchAlerts, acknowledgeAlertApi, investigateAlertApi,
  assignAlertApi, resolveAlertApi, fetchAlertNotes, addAlertNoteApi,
} from "../services/api";
import type { AlertItem, AlertNoteItem } from "../types/api";
import {
  ShieldAlert, RefreshCw, X, UserCheck, Search,
  MessageSquare, CheckCircle2, AlertOctagon, Clock, Send, AlertTriangle,
} from "lucide-react";

// --- Design tokens ---
const orange = "#ff7a00";
const orangeLight = "#ff9b4a";

function getSeverityStyle(sev: string) {
  if (sev === "CRITICAL") return { bg: "rgba(244,63,94,0.15)", border: "rgba(244,63,94,0.4)", text: "#f43f5e" };
  if (sev === "HIGH")     return { bg: "rgba(255,122,0,0.15)", border: "rgba(255,122,0,0.4)", text: "#ff9b4a" };
  if (sev === "MEDIUM")   return { bg: "rgba(168,85,247,0.15)", border: "rgba(168,85,247,0.4)", text: "#c084fc" };
  return { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.15)", text: "rgba(255,255,255,0.6)" };
}

function getStatusStyle(s: string) {
  if (s === "ACTIVE")       return { bg: "rgba(244,63,94,0.15)", border: "rgba(244,63,94,0.4)", text: "#f43f5e" };
  if (s === "ACKNOWLEDGED") return { bg: "rgba(255,122,0,0.15)", border: "rgba(255,122,0,0.4)", text: "#ff9b4a" };
  if (s === "INVESTIGATING") return { bg: "rgba(99,102,241,0.15)", border: "rgba(99,102,241,0.4)", text: "#818cf8" };
  if (s === "RESOLVED")     return { bg: "rgba(16,185,129,0.15)", border: "rgba(16,185,129,0.4)", text: "#34d399" };
  return { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)", text: "rgba(255,255,255,0.4)" };
}

const GlassBtn = ({ children, onClick, style, disabled }: any) => {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: hover ? "rgba(30, 30, 30, 0.8)" : "rgba(20, 20, 20, 0.6)",
        border: hover ? "1px solid rgba(255,255,255,0.25)" : "1px solid rgba(255,255,255,0.15)",
        color: hover ? "white" : "rgba(255,255,255,0.8)",
        borderRadius: "8px", padding: "8px 14px", fontSize: "10px", fontWeight: 700, fontFamily: "monospace", letterSpacing: "1px",
        cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, display: "flex", alignItems: "center", gap: "6px",
        transition: "all 0.2s ease", transform: hover && !disabled ? "translateY(-1px)" : "none",
        ...style
      }}
    >
      {children}
    </button>
  );
};

const ActionBtn = ({ label, icon: Icon, type, onClick, disabled }: { label: string, icon?: any, type: string, onClick: () => void, disabled?: boolean }) => {
  const [hover, setHover] = useState(false);
  
  let baseStyle: React.CSSProperties = { background: "rgba(10,10,10,0.7)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)", boxShadow: "none" };
  let hoverStyle: React.CSSProperties = { ...baseStyle };

  if (type === "ACTIVE") {
    baseStyle = { background: "rgba(20,5,5,0.7)", border: "1px solid rgba(244,63,94,0.4)", color: "#f43f5e", boxShadow: "0 0 10px rgba(244,63,94,0.1)" };
    hoverStyle = { ...baseStyle, border: "1px solid rgba(244,63,94,0.8)", boxShadow: "0 0 15px rgba(244,63,94,0.3)", transform: "translateY(-1px)", background: "rgba(30,5,5,0.8)" };
  } else if (type === "ACK") {
    baseStyle = { background: "rgba(15,10,5,0.7)", border: "1px solid rgba(255,122,0,0.4)", color: "#ff9b4a", boxShadow: "0 0 10px rgba(255,122,0,0.1)" };
    hoverStyle = { ...baseStyle, border: "1px solid rgba(255,122,0,0.8)", boxShadow: "0 0 15px rgba(255,122,0,0.3)", transform: "translateY(-1px)", background: "rgba(25,15,5,0.8)" };
  } else if (type === "INVESTIGATE") {
    baseStyle = { background: "rgba(5,10,15,0.7)", border: "1px solid rgba(99,102,241,0.4)", color: "#818cf8", boxShadow: "0 0 10px rgba(99,102,241,0.1)" };
    hoverStyle = { ...baseStyle, border: "1px solid rgba(99,102,241,0.8)", boxShadow: "0 0 15px rgba(99,102,241,0.3)", transform: "translateY(-1px)", background: "rgba(10,15,25,0.8)" };
  } else if (type === "DETAILS") {
    baseStyle = { background: "rgba(10,12,15,0.7)", border: "1px solid rgba(148,163,184,0.4)", color: "#cbd5e1", boxShadow: "0 0 10px rgba(148,163,184,0.1)" };
    hoverStyle = { ...baseStyle, border: "1px solid rgba(148,163,184,0.8)", boxShadow: "0 0 15px rgba(148,163,184,0.3)", transform: "translateY(-1px)", background: "rgba(15,20,25,0.8)" };
  }

  const currentStyle = hover && !disabled ? hoverStyle : baseStyle;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        borderRadius: "8px", padding: "6px 14px", fontSize: "10px", fontWeight: 700, fontFamily: "monospace", letterSpacing: "0.05em",
        cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, display: "flex", alignItems: "center", gap: "6px",
        transition: "all 0.25s ease", ...currentStyle,
      }}
    >
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {label}
    </button>
  );
};

const TabBtn = ({ tab, active, count, onClick }: { tab: string, active: boolean, count: number, onClick: () => void }) => {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: active ? "rgba(255, 122, 0, 0.15)" : (hover ? "rgba(30, 20, 10, 0.6)" : "rgba(10, 10, 10, 0.6)"),
        border: active ? "1px solid rgba(255, 122, 0, 0.8)" : (hover ? "1px solid rgba(255, 122, 0, 0.4)" : "1px solid rgba(255,255,255,0.1)"),
        color: active ? "white" : (hover ? "white" : "rgba(255,255,255,0.5)"),
        boxShadow: active ? "0 0 15px rgba(255,122,0,0.3)" : (hover ? "0 0 10px rgba(255,122,0,0.1)" : "none"),
        borderRadius: "8px", padding: "8px 16px", fontSize: "11px", fontWeight: 700, fontFamily: "monospace", letterSpacing: "0.05em",
        display: "flex", alignItems: "center", gap: "8px", transform: hover && !active ? "translateY(-1px)" : "none", transition: "all 0.25s ease",
      }}
    >
      {tab}
      <span style={{
        background: active ? "rgba(255, 122, 0, 0.3)" : "rgba(255,255,255,0.08)",
        borderRadius: "4px", padding: "2px 6px", fontSize: "10px",
      }}>{count}</span>
    </button>
  );
};

const RefreshBtn = ({ onClick, loading }: { onClick: () => void, loading: boolean }) => {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={loading}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: hover ? "rgba(35, 20, 5, 0.8)" : "rgba(15, 10, 5, 0.65)",
        border: hover ? "1px solid rgba(255, 150, 0, 0.6)" : "1px solid rgba(255, 122, 0, 0.4)",
        color: hover ? "white" : orangeLight,
        boxShadow: hover ? "0 0 20px rgba(255,122,0,0.3)" : "0 0 10px rgba(255,122,0,0.1)",
        borderRadius: "8px", padding: "10px 18px", fontSize: "11px", fontWeight: 700, fontFamily: "monospace", letterSpacing: "1px",
        display: "flex", alignItems: "center", gap: "8px", transform: hover ? "translateY(-1px)" : "none", transition: "all 0.25s ease",
      }}
    >
      <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
      REFRESH
    </button>
  );
};

const AlertCard = ({ alt, handleAcknowledge, handleStartInvestigation, setSelectedAlertModal }: any) => {
  const [hover, setHover] = useState(false);
  const sc = getSeverityStyle(alt.severity);

  return (
    <div 
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: hover ? "rgba(18, 15, 12, 0.75)" : "rgba(12, 10, 8, 0.65)",
        border: hover ? "1px solid rgba(255, 150, 0, 0.45)" : "1px solid rgba(255, 122, 0, 0.28)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        boxShadow: hover ? "0 12px 40px rgba(0,0,0,0.5), 0 0 25px rgba(255,122,0,0.18)" : "0 8px 30px rgba(0,0,0,0.45)",
        borderRadius: "18px",
        padding: "24px",
        transform: hover ? "translateY(-2px)" : "none",
        transition: "all 0.25s ease",
      }}
    >
      {/* Top row */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <div style={{ color: orange, textShadow: "0 0 10px rgba(255,122,0,0.5)", border: `1px solid rgba(255,122,0,0.3)`, borderRadius: "50%", padding: "4px" }}>
             <AlertTriangle className="w-4 h-4" />
          </div>
          <span style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.text, borderRadius: "6px", padding: "2px 10px", fontSize: "10px", fontWeight: 800, fontFamily: "monospace", letterSpacing: "1px", textShadow: `0 0 8px ${sc.text}` }}>
            {alt.severity}
          </span>
          <span className="text-white font-bold text-lg">{alt.title}</span>
          <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "12px", fontFamily: "monospace" }}>({alt.well_id})</span>
          <span style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,122,0,0.4)", color: orangeLight, borderRadius: "6px", padding: "2px 8px", fontSize: "10px", fontFamily: "monospace" }}>
            ML_PREDICTION
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-2 lg:mt-0">
          {alt.status === "ACTIVE" && (
             <ActionBtn type="ACTIVE" label="ACTIVE" onClick={() => {}} disabled />
          )}
          {alt.status === "ACTIVE" && (
             <ActionBtn type="ACK" label="ACK" icon={CheckCircle2} onClick={() => handleAcknowledge(alt.alert_id)} />
          )}
          {(alt.status === "ACTIVE" || alt.status === "ACKNOWLEDGED") && (
             <ActionBtn type="INVESTIGATE" label="INVESTIGATE" icon={Search} onClick={() => handleStartInvestigation(alt.alert_id)} />
          )}
          <ActionBtn type="DETAILS" label="DETAILS" icon={MessageSquare} onClick={() => setSelectedAlertModal(alt)} />
        </div>
      </div>

      {/* Evidence block */}
      <div style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "20px" }}>
        <p style={{ color: orangeLight, fontSize: "10px", fontWeight: 800, letterSpacing: "2px", marginBottom: "12px", fontFamily: "monospace" }}>
          EVIDENCE &amp; DIAGNOSIS
        </p>
        <pre style={{ color: "rgba(255,255,255,0.75)", fontSize: "12px", fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: "1.7", margin: 0 }}>
          {alt.evidence}
        </pre>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-5" style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", fontFamily: "monospace" }}>
        <div className="flex items-center gap-4">
          <span>MD: <strong style={{ color: orangeLight }}>{alt.current_md.toFixed(1)} m</strong></span>
          {alt.assigned_to && (
            <span className="flex items-center gap-1.5" style={{ color: "#818cf8" }}>
              <UserCheck className="w-3.5 h-3.5" /> {alt.assigned_to}
            </span>
          )}
        </div>
        <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{new Date(alt.created_at).toLocaleString()}</span>
      </div>
    </div>
  );
};

export const AlertsPage: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("ALL");
  const [selectedAlertModal, setSelectedAlertModal] = useState<AlertItem | null>(null);
  const [resolveNotes, setResolveNotes] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [newNoteText, setNewNoteText] = useState("");
  const [alertNotes, setAlertNotes] = useState<AlertNoteItem[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);

  const loadAlerts = () => {
    setLoading(true);
    fetchAlerts(selectedWell)
      .then((res) => { if (res?.alerts) setAlerts(res.alerts); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadAlerts(); }, [selectedWell]);

  useEffect(() => {
    const handler = (e: Event) => {
      const alert = (e as CustomEvent).detail as AlertItem;
      if (!alert) return;
      setAlerts((prev) => prev.some((a) => a.alert_id === alert.alert_id) ? prev : [alert, ...prev]);
    };
    window.addEventListener("ertmac:alert_created", handler);
    return () => window.removeEventListener("ertmac:alert_created", handler);
  }, []);

  useEffect(() => {
    if (selectedAlertModal) {
      setNotesLoading(true);
      fetchAlertNotes(selectedAlertModal.alert_id)
        .then(res => { if (res?.notes) setAlertNotes(res.notes); setNotesLoading(false); })
        .catch(() => setNotesLoading(false));
    } else {
      setAlertNotes([]);
    }
  }, [selectedAlertModal]);

  const handleAcknowledge = async (id: string) => {
    await acknowledgeAlertApi(id);
    loadAlerts();
  };
  const handleStartInvestigation = async (id: string) => {
    await investigateAlertApi(id);
    loadAlerts();
  };
  const handleAssign = async (id: string) => {
    await assignAlertApi(id, assigneeId);
    setAssigneeId("");
    loadAlerts();
    setSelectedAlertModal(null);
  };
  const handleAddNote = async (id: string) => {
    if (!newNoteText.trim()) return;
    const res = await addAlertNoteApi(id, newNoteText);
    if (res?.note) setAlertNotes(prev => [res.note, ...prev]);
    setNewNoteText("");
  };
  const handleResolve = async (id: string) => {
    await resolveAlertApi(id, resolveNotes);
    setResolveNotes("");
    loadAlerts();
    setSelectedAlertModal(null);
  };

  const tabs = ["ALL", "ACTIVE", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"];
  const counts = {
    ALL: alerts.length,
    ACTIVE: alerts.filter(a => a.status === "ACTIVE").length,
    ACKNOWLEDGED: alerts.filter(a => a.status === "ACKNOWLEDGED").length,
    INVESTIGATING: alerts.filter(a => a.status === "INVESTIGATING").length,
    RESOLVED: alerts.filter(a => a.status === "RESOLVED").length,
  };
  const filtered = activeTab === "ALL" ? alerts : alerts.filter(a => a.status === activeTab);

  return (
    <div 
      className="min-h-screen relative text-white pb-24"
      style={{ 
        backgroundColor: "#030405", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-network-orange.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        fontFamily: "'Inter', sans-serif" 
      }}
    >
      <div className="relative z-10 max-w-7xl mx-auto px-6 pt-10 space-y-8">
        
        {/* ── Header ── */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <h1 className="text-white font-bold text-4xl tracking-tight leading-tight uppercase font-mono">
              OPERATIONS ALERT CENTER
            </h1>
          </div>

          <div>
             <RefreshBtn onClick={loadAlerts} loading={loading} />
          </div>
        </div>

        {/* ── Tabs ── */}
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }} className="flex flex-wrap gap-3 pb-6">
          {tabs.map((tab) => (
            <TabBtn key={tab} tab={tab} active={activeTab === tab} count={counts[tab as keyof typeof counts]} onClick={() => setActiveTab(tab)} />
          ))}
        </div>

        {/* ── Alert Cards ── */}
        <div className="space-y-5">
          {filtered.length === 0 && !loading && (
            <div style={{ background: "rgba(12, 10, 8, 0.65)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "16px" }} className="p-12 text-center text-sm font-mono text-slate-500">
              No alerts in [{activeTab}] for {selectedWell}. System nominal.
            </div>
          )}

          {filtered.map((alt) => (
            <AlertCard 
              key={alt.alert_id} 
              alt={alt} 
              handleAcknowledge={handleAcknowledge} 
              handleStartInvestigation={handleStartInvestigation} 
              setSelectedAlertModal={setSelectedAlertModal} 
            />
          ))}
        </div>

        {/* ── Detail Modal ── */}
        {selectedAlertModal && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(3,4,5,0.85)", backdropFilter: "blur(10px)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
            <div style={{ background: "rgba(12, 10, 8, 0.95)", border: "1px solid rgba(255, 122, 0, 0.3)", boxShadow: "0 10px 50px rgba(0,0,0,0.7)", borderRadius: "20px", maxWidth: "680px", width: "100%", maxHeight: "90vh", overflowY: "auto", position: "relative", padding: "32px" }}>
              <button onClick={() => setSelectedAlertModal(null)}
                style={{ position: "absolute", top: "20px", right: "20px", color: "rgba(255,255,255,0.4)", background: "none", border: "none", cursor: "pointer" }}>
                <X className="w-5 h-5" />
              </button>

              {/* Modal header */}
              <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "16px", marginBottom: "24px" }}>
                <p style={{ color: orange, fontSize: "10px", fontWeight: 800, letterSpacing: "2px", marginBottom: "6px", fontFamily: "monospace" }}>ALERT LIFECYCLE OPERATIONS</p>
                <h2 className="text-white font-bold text-xl font-mono">{selectedAlertModal.title}</h2>
                <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "12px", marginTop: "4px", fontFamily: "monospace" }}>
                  {selectedAlertModal.well_id} · MD {selectedAlertModal.current_md.toFixed(1)}m · {new Date(selectedAlertModal.created_at).toLocaleString()}
                </p>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {[
                  { label: "SEVERITY", val: selectedAlertModal.severity, c: getSeverityStyle(selectedAlertModal.severity).text },
                  { label: "STATUS", val: selectedAlertModal.status, c: getStatusStyle(selectedAlertModal.status).text },
                  { label: "MD (m)", val: selectedAlertModal.current_md.toFixed(1), c: orangeLight },
                  { label: "ASSIGNED", val: selectedAlertModal.assigned_to || "—", c: "#818cf8" },
                ].map(({ label, val, c }) => (
                  <div key={label} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "10px", padding: "12px 14px" }}>
                    <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "9px", letterSpacing: "2px", marginBottom: "4px", fontFamily: "monospace" }}>{label}</p>
                    <p style={{ color: c, fontWeight: 800, fontFamily: "monospace", fontSize: "13px", textShadow: `0 0 10px ${c}` }}>{val}</p>
                  </div>
                ))}
              </div>

              {/* Full evidence */}
              <div style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "16px 20px", marginBottom: "20px" }}>
                <p style={{ color: orangeLight, fontSize: "10px", fontWeight: 800, letterSpacing: "2px", marginBottom: "12px", fontFamily: "monospace" }}>FULL EVIDENCE &amp; DIAGNOSIS</p>
                <pre style={{ color: "rgba(255,255,255,0.75)", fontSize: "12px", fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: "1.7", margin: 0 }}>
                  {selectedAlertModal.evidence}
                </pre>
              </div>

              {/* Assign */}
              {selectedAlertModal.status !== "RESOLVED" && (
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "16px", marginBottom: "20px" }}>
                  <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "10px", fontFamily: "monospace" }}>ASSIGN TO ENGINEER</p>
                  <div className="flex gap-3">
                    <input value={assigneeId} onChange={e => setAssigneeId(e.target.value)}
                      placeholder="engineer UUID or username"
                      style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.10)", color: "white", borderRadius: "8px", padding: "10px 14px", fontSize: "12px", outline: "none", fontFamily: "monospace" }} />
                    <GlassBtn onClick={() => handleAssign(selectedAlertModal.alert_id)} disabled={!assigneeId.trim()}
                      style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8", padding: "10px 20px" }}>
                      ASSIGN
                    </GlassBtn>
                  </div>
                </div>
              )}

              {/* Notes */}
              <div style={{ marginBottom: "20px" }}>
                <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "10px", fontFamily: "monospace" }}>OPERATIONAL NOTES THREAD</p>
                <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "12px", padding: "16px", maxHeight: "200px", overflowY: "auto", marginBottom: "12px" }}>
                  {notesLoading && <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "12px", fontFamily: "monospace" }}>Loading...</p>}
                  {!notesLoading && alertNotes.length === 0 && <p style={{ color: "rgba(255,255,255,0.25)", fontSize: "12px", fontStyle: "italic", fontFamily: "monospace" }}>No notes yet.</p>}
                  {alertNotes.map(n => (
                    <div key={n.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", paddingBottom: "12px", marginBottom: "12px" }}>
                      <div className="flex justify-between" style={{ color: "rgba(255,255,255,0.3)", fontSize: "10px", marginBottom: "6px", fontFamily: "monospace" }}>
                        <span style={{ color: "#818cf8", fontWeight: 700 }}>{n.author_id}</span>
                        <span>{new Date(n.created_at).toLocaleString()}</span>
                      </div>
                      <p style={{ color: "rgba(255,255,255,0.85)", fontSize: "12px", margin: 0, fontFamily: "monospace" }}>{n.note_text}</p>
                    </div>
                  ))}
                </div>
                {selectedAlertModal.status !== "RESOLVED" && (
                  <div className="flex gap-3">
                    <input value={newNoteText} onChange={e => setNewNoteText(e.target.value)}
                      placeholder="Add investigation note..."
                      style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.10)", color: "white", borderRadius: "8px", padding: "10px 14px", fontSize: "12px", outline: "none", fontFamily: "monospace" }} />
                    <GlassBtn onClick={() => handleAddNote(selectedAlertModal.alert_id)} disabled={!newNoteText.trim()}
                      style={{ padding: "10px 20px" }}>
                      <Send className="w-4 h-4 text-blue-400" /> ADD
                    </GlassBtn>
                  </div>
                )}
              </div>

              {/* Resolve */}
              {selectedAlertModal.status !== "RESOLVED" && (
                <div style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.20)", borderRadius: "12px", padding: "20px" }}>
                  <p style={{ color: "#34d399", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "10px", fontFamily: "monospace" }}>RESOLUTION SUMMARY</p>
                  <textarea value={resolveNotes} onChange={e => setResolveNotes(e.target.value)}
                    placeholder="Enter resolution actions taken..."
                    style={{ width: "100%", boxSizing: "border-box", background: "rgba(0,0,0,0.4)", border: "1px solid rgba(16,185,129,0.3)", color: "rgba(255,255,255,0.9)", borderRadius: "8px", padding: "12px 14px", fontSize: "12px", fontFamily: "monospace", resize: "none", height: "80px", outline: "none" }} />
                  <button onClick={() => handleResolve(selectedAlertModal.alert_id)} disabled={!resolveNotes.trim()}
                    style={{ marginTop: "12px", width: "100%", padding: "14px", background: "linear-gradient(135deg, #10b981, #059669)", border: "none", borderRadius: "8px", color: "white", fontWeight: 700, fontSize: "12px", fontFamily: "monospace", letterSpacing: "1px", cursor: resolveNotes.trim() ? "pointer" : "not-allowed", opacity: resolveNotes.trim() ? 1 : 0.5, boxShadow: "0 6px 25px rgba(16,185,129,0.25)", transition: "all 0.2s ease" }}>
                    ✓ CONFIRM RESOLUTION &amp; CLOSE ALERT
                  </button>
                </div>
              )}

              {selectedAlertModal.status === "RESOLVED" && (
                <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "12px", padding: "20px" }}>
                  <p style={{ color: "#34d399", fontWeight: 800, fontSize: "14px", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px", fontFamily: "monospace" }}>
                    <CheckCircle2 className="w-5 h-5" /> RESOLVED
                  </p>
                  <p style={{ color: "rgba(255,255,255,0.8)", fontSize: "13px", fontFamily: "monospace" }}>{selectedAlertModal.resolution_notes || "No notes recorded."}</p>
                  <div className="flex justify-between mt-4 pt-4" style={{ borderTop: "1px solid rgba(16,185,129,0.2)", color: "rgba(255,255,255,0.4)", fontSize: "11px", fontFamily: "monospace" }}>
                    <span>By: <strong style={{ color: "white" }}>{selectedAlertModal.resolved_by || "System"}</strong></span>
                    <span>{selectedAlertModal.resolved_at}</span>
                  </div>
                </div>
              )}

              <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: "20px", marginTop: "24px", display: "flex", justifyContent: "flex-end" }}>
                <GlassBtn onClick={() => setSelectedAlertModal(null)}>CLOSE</GlassBtn>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertsPage;
