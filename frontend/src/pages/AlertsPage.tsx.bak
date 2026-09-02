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

// ── Design tokens matching Login.css ────────────────────────────────────────
const glass = {
  background: "linear-gradient(145deg, rgba(20,27,42,0.72), rgba(9,14,25,0.60))",
  border: "1px solid rgba(255,255,255,0.09)",
  backdropFilter: "blur(18px)",
  WebkitBackdropFilter: "blur(18px)",
  boxShadow: "0 25px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
} as React.CSSProperties;

const orange = "#ff8a1f";
const orangeLight = "#ff9b4a";

function sevColor(sev: string) {
  if (sev === "CRITICAL") return { bg: "rgba(244,63,94,0.12)", border: "rgba(244,63,94,0.35)", text: "#f43f5e" };
  if (sev === "HIGH")     return { bg: "rgba(249,115,22,0.10)", border: "rgba(249,115,22,0.30)", text: "#fb923c" };
  if (sev === "MEDIUM")   return { bg: "rgba(168,85,247,0.10)", border: "rgba(168,85,247,0.30)", text: "#c084fc" };
  return { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.10)", text: "rgba(255,255,255,0.6)" };
}

function statusColor(s: string) {
  if (s === "ACTIVE")       return { bg: "rgba(244,63,94,0.12)", border: "rgba(244,63,94,0.30)", text: "#f43f5e" };
  if (s === "ACKNOWLEDGED") return { bg: "rgba(249,115,22,0.10)", border: "rgba(249,115,22,0.28)", text: "#fb923c" };
  if (s === "INVESTIGATING") return { bg: "rgba(99,102,241,0.10)", border: "rgba(99,102,241,0.28)", text: "#818cf8" };
  if (s === "RESOLVED")     return { bg: "rgba(16,185,129,0.10)", border: "rgba(16,185,129,0.28)", text: "#34d399" };
  return { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.08)", text: "rgba(255,255,255,0.4)" };
}

const GlassBtn = ({ children, onClick, style, disabled }: any) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      background: "rgba(255,255,255,0.06)",
      border: "1px solid rgba(255,255,255,0.10)",
      color: "rgba(255,255,255,0.75)",
      borderRadius: "8px",
      padding: "6px 12px",
      fontSize: "11px",
      fontWeight: 700,
      fontFamily: "monospace",
      letterSpacing: "0.05em",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      display: "flex",
      alignItems: "center",
      gap: "5px",
      transition: "all 0.2s ease",
      ...style,
    }}
  >
    {children}
  </button>
);

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
        .then((n) => { setAlertNotes(n); setNotesLoading(false); })
        .catch(() => setNotesLoading(false));
    } else {
      setAlertNotes([]); setResolveNotes(""); setNewNoteText(""); setAssigneeId("");
    }
  }, [selectedAlertModal]);

  const handleAcknowledge = async (id: string) => { await acknowledgeAlertApi(id); loadAlerts(); if (selectedAlertModal?.alert_id === id) setSelectedAlertModal(null); };
  const handleStartInvestigation = async (id: string) => { await investigateAlertApi(id); loadAlerts(); if (selectedAlertModal?.alert_id === id) setSelectedAlertModal(null); };
  const handleAssign = async (id: string) => { if (!assigneeId.trim()) return; await assignAlertApi(id, assigneeId); loadAlerts(); setAssigneeId(""); };
  const handleAddNote = async (id: string) => { if (!newNoteText.trim()) return; const r = await addAlertNoteApi(id, newNoteText); if (r) { setNewNoteText(""); setAlertNotes(await fetchAlertNotes(id)); } };
  const handleResolve = async (id: string) => { if (!resolveNotes.trim()) return; await resolveAlertApi(id, resolveNotes); setResolveNotes(""); setSelectedAlertModal(null); loadAlerts(); };

  const tabs = ["ALL", "ACTIVE", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"] as const;
  const counts: Record<string, number> = {
    ALL: alerts.length,
    ACTIVE: alerts.filter(a => a.status === "ACTIVE").length,
    ACKNOWLEDGED: alerts.filter(a => a.status === "ACKNOWLEDGED").length,
    INVESTIGATING: alerts.filter(a => a.status === "INVESTIGATING").length,
    RESOLVED: alerts.filter(a => a.status === "RESOLVED").length,
  };
  const filtered = alerts.filter(a => activeTab === "ALL" || a.status === activeTab);

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div style={glass} className="rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div style={{ background: "linear-gradient(135deg, #f43f5e, #c0392b)", boxShadow: "0 8px 25px rgba(244,63,94,0.30)" }}
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
            <ShieldAlert className="w-5 h-5 text-white" />
          </div>
          <div>
            <p style={{ color: orangeLight, letterSpacing: "2px" }} className="text-[11px] font-bold uppercase mb-1">
              NEARBY WELLS INTELLIGENCE SYSTEM
            </p>
            <h1 className="text-white font-bold text-xl tracking-tight leading-tight">Operations Alert Center</h1>
            <p className="mt-1 text-sm" style={{ color: "rgba(255,255,255,0.45)" }}>
              Real-time ML anomaly dispatches — full lifecycle management
            </p>
            <div style={{ width: "36px", height: "3px", background: "#f43f5e", boxShadow: "0 0 12px rgba(244,63,94,0.5)", borderRadius: "10px", marginTop: "12px" }} />
          </div>
        </div>
        <GlassBtn onClick={loadAlerts} style={{ border: `1px solid ${orange}40`, color: orangeLight }}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </GlassBtn>
      </div>

      {/* ── Tabs ── */}
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }} className="flex flex-wrap gap-2 pb-3">
        {tabs.map((tab) => {
          const active = activeTab === tab;
          return (
            <button key={tab} onClick={() => setActiveTab(tab)}
              style={{
                background: active ? "linear-gradient(135deg, #ff9b2f, #ff7a18)" : "rgba(255,255,255,0.05)",
                border: active ? "1px solid rgba(255,138,31,0.4)" : "1px solid rgba(255,255,255,0.08)",
                color: active ? "white" : "rgba(255,255,255,0.5)",
                boxShadow: active ? "0 4px 15px rgba(255,122,24,0.25)" : "none",
                borderRadius: "8px", padding: "6px 14px", fontSize: "11px", fontWeight: 700,
                fontFamily: "monospace", letterSpacing: "0.05em", cursor: "pointer",
                display: "flex", alignItems: "center", gap: "6px", transition: "all 0.2s ease",
              }}>
              {tab}
              <span style={{
                background: active ? "rgba(0,0,0,0.25)" : "rgba(255,255,255,0.07)",
                borderRadius: "4px", padding: "1px 6px", fontSize: "10px",
              }}>{counts[tab]}</span>
            </button>
          );
        })}
      </div>

      {/* ── Alert Cards ── */}
      <div className="space-y-3">
        {filtered.length === 0 && !loading && (
          <div style={{ ...glass, borderRadius: "16px" }} className="p-12 text-center text-xs" style={{ color: "rgba(255,255,255,0.3)" } as React.CSSProperties}>
            No alerts in [{activeTab}] for {selectedWell}. System nominal.
          </div>
        )}

        {filtered.map((alt) => {
          const sc = sevColor(alt.severity);
          const stc = statusColor(alt.status);
          const isCrit = alt.severity === "CRITICAL";
          return (
            <div key={alt.alert_id} style={{
              background: "linear-gradient(145deg, rgba(20,27,42,0.70), rgba(9,14,25,0.55))",
              border: `1px solid ${sc.border}`,
              backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)",
              boxShadow: isCrit ? `0 10px 40px rgba(244,63,94,0.12), inset 0 1px 0 rgba(255,255,255,0.05)` : "0 10px 40px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.04)",
              borderRadius: "16px", padding: "18px 20px",
            }}>
              {/* Top row */}
              <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                <div className="flex flex-wrap items-center gap-2">
                  {isCrit
                    ? <AlertTriangle className="w-4 h-4" style={{ color: sc.text }} />
                    : <AlertOctagon className="w-4 h-4" style={{ color: sc.text }} />}
                  <span style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.text, borderRadius: "6px", padding: "2px 10px", fontSize: "10px", fontWeight: 800, fontFamily: "monospace", letterSpacing: "1px" }}>
                    {alt.severity}
                  </span>
                  <span className="text-white font-bold text-sm">{alt.title}</span>
                  <span style={{ color: "rgba(255,255,255,0.35)", fontSize: "11px" }}>({alt.well_id})</span>
                  <span style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.35)", borderRadius: "4px", padding: "1px 8px", fontSize: "10px", fontFamily: "monospace" }}>
                    ML_PREDICTION
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span style={{ background: stc.bg, border: `1px solid ${stc.border}`, color: stc.text, borderRadius: "6px", padding: "2px 10px", fontSize: "10px", fontWeight: 800, fontFamily: "monospace" }}>
                    {alt.status}
                  </span>
                  {alt.status === "ACTIVE" && (
                    <GlassBtn onClick={() => handleAcknowledge(alt.alert_id)}
                      style={{ border: `1px solid rgba(249,115,22,0.3)`, color: "#fb923c" }}>
                      <CheckCircle2 className="w-3 h-3" /> ACK
                    </GlassBtn>
                  )}
                  {(alt.status === "ACTIVE" || alt.status === "ACKNOWLEDGED") && (
                    <GlassBtn onClick={() => handleStartInvestigation(alt.alert_id)}
                      style={{ border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8" }}>
                      <Search className="w-3 h-3" /> INVESTIGATE
                    </GlassBtn>
                  )}
                  <GlassBtn onClick={() => setSelectedAlertModal(alt)}>
                    <MessageSquare className="w-3 h-3 text-blue-400" /> DETAILS
                  </GlassBtn>
                </div>
              </div>

              {/* Evidence block */}
              <div style={{ background: "rgba(0,0,0,0.25)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "12px 14px" }}>
                <p style={{ color: orangeLight, fontSize: "9px", fontWeight: 800, letterSpacing: "2px", marginBottom: "6px", fontFamily: "monospace" }}>
                  EVIDENCE &amp; DIAGNOSIS
                </p>
                <pre style={{ color: "rgba(255,255,255,0.72)", fontSize: "11px", fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: "1.6", margin: 0 }}>
                  {alt.evidence}
                </pre>
              </div>

              {/* Footer */}
              <div className="flex flex-wrap items-center justify-between mt-3 gap-2" style={{ fontSize: "11px", color: "rgba(255,255,255,0.35)", fontFamily: "monospace" }}>
                <div className="flex items-center gap-3">
                  <span>MD: <strong style={{ color: orangeLight }}>{alt.current_md.toFixed(1)} m</strong></span>
                  {alt.assigned_to && (
                    <span className="flex items-center gap-1" style={{ color: "#818cf8" }}>
                      <UserCheck className="w-3 h-3" /> {alt.assigned_to}
                    </span>
                  )}
                </div>
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(alt.created_at).toLocaleString()}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Detail Modal ── */}
      {selectedAlertModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(3,8,18,0.85)", backdropFilter: "blur(8px)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
          <div style={{ ...glass, borderRadius: "20px", maxWidth: "640px", width: "100%", maxHeight: "90vh", overflowY: "auto", position: "relative", padding: "28px" }}>
            <button onClick={() => setSelectedAlertModal(null)}
              style={{ position: "absolute", top: "20px", right: "20px", color: "rgba(255,255,255,0.4)", background: "none", border: "none", cursor: "pointer" }}>
              <X className="w-5 h-5" />
            </button>

            {/* Modal header */}
            <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "16px", marginBottom: "20px" }}>
              <p style={{ color: orangeLight, fontSize: "10px", fontWeight: 800, letterSpacing: "2px", marginBottom: "6px" }}>ALERT LIFECYCLE OPERATIONS</p>
              <h2 className="text-white font-bold text-lg">{selectedAlertModal.title}</h2>
              <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "11px", marginTop: "4px", fontFamily: "monospace" }}>
                {selectedAlertModal.well_id} · MD {selectedAlertModal.current_md.toFixed(1)}m · {selectedAlertModal.created_at}
              </p>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
              {[
                { label: "SEVERITY", val: selectedAlertModal.severity, c: sevColor(selectedAlertModal.severity).text },
                { label: "STATUS", val: selectedAlertModal.status, c: statusColor(selectedAlertModal.status).text },
                { label: "MD (m)", val: selectedAlertModal.current_md.toFixed(1), c: orangeLight },
                { label: "ASSIGNED", val: selectedAlertModal.assigned_to || "—", c: "#818cf8" },
              ].map(({ label, val, c }) => (
                <div key={label} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "10px", padding: "10px 12px" }}>
                  <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "9px", letterSpacing: "2px", marginBottom: "4px" }}>{label}</p>
                  <p style={{ color: c, fontWeight: 800, fontFamily: "monospace", fontSize: "12px" }}>{val}</p>
                </div>
              ))}
            </div>

            {/* Full evidence */}
            <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px", padding: "14px 16px", marginBottom: "16px" }}>
              <p style={{ color: orangeLight, fontSize: "9px", fontWeight: 800, letterSpacing: "2px", marginBottom: "8px" }}>FULL EVIDENCE &amp; DIAGNOSIS</p>
              <pre style={{ color: "rgba(255,255,255,0.75)", fontSize: "11px", fontFamily: "monospace", whiteSpace: "pre-wrap", lineHeight: "1.7", margin: 0 }}>
                {selectedAlertModal.evidence}
              </pre>
            </div>

            {/* Assign */}
            {selectedAlertModal.status !== "RESOLVED" && (
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px", padding: "14px", marginBottom: "14px" }}>
                <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "8px" }}>ASSIGN TO ENGINEER</p>
                <div className="flex gap-2">
                  <input value={assigneeId} onChange={e => setAssigneeId(e.target.value)}
                    placeholder="engineer UUID or username"
                    style={{ flex: 1, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.10)", color: "white", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", outline: "none", fontFamily: "monospace" }} />
                  <GlassBtn onClick={() => handleAssign(selectedAlertModal.alert_id)} disabled={!assigneeId.trim()}
                    style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8", padding: "8px 14px" }}>
                    ASSIGN
                  </GlassBtn>
                </div>
              </div>
            )}

            {/* Notes */}
            <div style={{ marginBottom: "14px" }}>
              <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "8px" }}>OPERATIONAL NOTES THREAD</p>
              <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "10px", padding: "12px", maxHeight: "150px", overflowY: "auto", marginBottom: "8px" }}>
                {notesLoading && <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "11px" }}>Loading...</p>}
                {!notesLoading && alertNotes.length === 0 && <p style={{ color: "rgba(255,255,255,0.25)", fontSize: "11px", fontStyle: "italic" }}>No notes yet.</p>}
                {alertNotes.map(n => (
                  <div key={n.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "8px", marginBottom: "8px" }}>
                    <div className="flex justify-between" style={{ color: "rgba(255,255,255,0.3)", fontSize: "10px", marginBottom: "3px" }}>
                      <span style={{ color: "#818cf8", fontWeight: 700 }}>{n.author_id}</span>
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                    <p style={{ color: "rgba(255,255,255,0.8)", fontSize: "12px", margin: 0 }}>{n.note_text}</p>
                  </div>
                ))}
              </div>
              {selectedAlertModal.status !== "RESOLVED" && (
                <div className="flex gap-2">
                  <input value={newNoteText} onChange={e => setNewNoteText(e.target.value)}
                    placeholder="Add investigation note..."
                    style={{ flex: 1, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.10)", color: "white", borderRadius: "8px", padding: "8px 12px", fontSize: "12px", outline: "none" }} />
                  <GlassBtn onClick={() => handleAddNote(selectedAlertModal.alert_id)} disabled={!newNoteText.trim()}>
                    <Send className="w-3 h-3 text-blue-400" /> ADD
                  </GlassBtn>
                </div>
              )}
            </div>

            {/* Resolve */}
            {selectedAlertModal.status !== "RESOLVED" && (
              <div style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.20)", borderRadius: "12px", padding: "14px" }}>
                <p style={{ color: "#34d399", fontSize: "11px", fontWeight: 700, letterSpacing: "1px", marginBottom: "8px" }}>RESOLUTION SUMMARY</p>
                <textarea value={resolveNotes} onChange={e => setResolveNotes(e.target.value)}
                  placeholder="Enter resolution actions taken..."
                  style={{ width: "100%", boxSizing: "border-box", background: "rgba(0,0,0,0.2)", border: "1px solid rgba(16,185,129,0.2)", color: "rgba(255,255,255,0.85)", borderRadius: "8px", padding: "10px 12px", fontSize: "12px", fontFamily: "monospace", resize: "none", height: "80px", outline: "none" }} />
                <button onClick={() => handleResolve(selectedAlertModal.alert_id)} disabled={!resolveNotes.trim()}
                  style={{ marginTop: "10px", width: "100%", padding: "12px", background: "linear-gradient(135deg, #10b981, #059669)", border: "none", borderRadius: "10px", color: "white", fontWeight: 700, fontSize: "12px", fontFamily: "monospace", letterSpacing: "1px", cursor: resolveNotes.trim() ? "pointer" : "not-allowed", opacity: resolveNotes.trim() ? 1 : 0.5, boxShadow: "0 6px 20px rgba(16,185,129,0.25)", transition: "all 0.2s ease" }}>
                  ✓ CONFIRM RESOLUTION &amp; CLOSE ALERT
                </button>
              </div>
            )}

            {selectedAlertModal.status === "RESOLVED" && (
              <div style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "12px", padding: "16px" }}>
                <p style={{ color: "#34d399", fontWeight: 800, fontSize: "12px", marginBottom: "6px", display: "flex", alignItems: "center", gap: "6px" }}>
                  <CheckCircle2 className="w-4 h-4" /> RESOLVED
                </p>
                <p style={{ color: "rgba(255,255,255,0.7)", fontSize: "12px" }}>{selectedAlertModal.resolution_notes || "No notes recorded."}</p>
                <div className="flex justify-between mt-3" style={{ color: "rgba(255,255,255,0.35)", fontSize: "11px" }}>
                  <span>By: <strong style={{ color: "white" }}>{selectedAlertModal.resolved_by || "System"}</strong></span>
                  <span>{selectedAlertModal.resolved_at}</span>
                </div>
              </div>
            )}

            <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: "14px", marginTop: "14px", display: "flex", justifyContent: "flex-end" }}>
              <GlassBtn onClick={() => setSelectedAlertModal(null)}>CLOSE</GlassBtn>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
