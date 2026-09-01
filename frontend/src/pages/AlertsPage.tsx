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

  // Listen for real-time ML-generated alerts over WS bridge
  useEffect(() => {
    const handler = (e: Event) => {
      const alert = (e as CustomEvent).detail as AlertItem;
      if (!alert) return;
      setAlerts((prev) => {
        if (prev.some((a) => a.alert_id === alert.alert_id)) return prev;
        return [alert, ...prev];
      });
    };
    window.addEventListener("ertmac:alert_created", handler);
    return () => window.removeEventListener("ertmac:alert_created", handler);
  }, []);

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
        return "bg-rose-950/80 text-rose-400 border-rose-500/40";
      case "HIGH":
        return "bg-amber-950/80 text-amber-400 border-amber-500/40";
      case "MEDIUM":
        return "bg-purple-950/80 text-purple-400 border-purple-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return "bg-rose-950 text-rose-400 border-rose-500/30";
      case "ACKNOWLEDGED":
        return "bg-amber-950 text-amber-400 border-amber-500/30";
      case "INVESTIGATING":
        return "bg-blue-950 text-blue-400 border-blue-500/30";
      case "RESOLVED":
        return "bg-emerald-950 text-emerald-400 border-emerald-500/30";
      default:
        return "bg-slate-950 text-slate-400 border-slate-700";
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
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              REAL-TIME OPERATIONS ALERT CENTER
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-bold">
              FULL LIFECYCLE MANAGED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time operational dispatches, assignment tracking, investigation notes, and immutable resolution audit log.
          </p>
        </div>

        <button
          onClick={loadAlerts}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3 text-xs font-bold">
        {(["ALL", "ACTIVE", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 rounded-lg border transition-all flex items-center gap-2 ${
              activeTab === tab
                ? "bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-500/20"
                : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white hover:bg-slate-850"
            }`}
          >
            <span>{tab}</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                activeTab === tab ? "bg-blue-800 text-white" : "bg-slate-950 text-slate-500"
              }`}
            >
              {counts[tab]}
            </span>
          </button>
        ))}
      </div>

      {/* Alerts Grid */}
      <div className="space-y-3">
        {filteredAlerts.length === 0 && !loading && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-xs text-slate-400">
            No alerts found in category [{activeTab}] for well {selectedWell}. System nominal.
          </div>
        )}

        {filteredAlerts.map((alt) => (
          <div key={alt.alert_id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs px-2.5 py-0.5 rounded font-bold border ${getSeverityStyle(alt.severity)}`}>
                  {alt.severity}
                </span>
                <span className="text-white font-bold text-sm">{alt.title}</span>
                <span className="text-slate-400 text-xs">({alt.well_id})</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 uppercase">
                  SOURCE: {alt.source}
                </span>
              </div>

              {/* Lifecycle Actions */}
              <div className="flex items-center gap-2 text-xs flex-wrap">
                <span className={`px-2 py-0.5 rounded border text-[11px] font-bold ${getStatusBadge(alt.status)}`}>
                  {alt.status}
                </span>

                {alt.status === "ACTIVE" && (
                  <button
                    onClick={() => handleAcknowledge(alt.alert_id)}
                    className="bg-amber-950/80 hover:bg-amber-900 text-amber-400 px-2.5 py-1 rounded border border-amber-500/30 font-bold transition-all text-xs flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> ACKNOWLEDGE
                  </button>
                )}

                {(alt.status === "ACTIVE" || alt.status === "ACKNOWLEDGED") && (
                  <button
                    onClick={() => handleStartInvestigation(alt.alert_id)}
                    className="bg-blue-950/80 hover:bg-blue-900 text-blue-400 px-2.5 py-1 rounded border border-blue-500/30 font-bold transition-all text-xs flex items-center gap-1"
                  >
                    <Search className="w-3.5 h-3.5" /> INVESTIGATE
                  </button>
                )}

                <button
                  onClick={() => setSelectedAlertModal(alt)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded font-bold transition-all text-xs flex items-center gap-1 border border-slate-700"
                >
                  <MessageSquare className="w-3.5 h-3.5 text-blue-400" /> DETAILS & NOTES
                </button>
              </div>
            </div>

            <div className="text-xs text-slate-300 font-sans bg-slate-950 p-3 rounded-lg border border-slate-850">
              <strong className="text-emerald-400 font-mono block text-[10px] uppercase mb-1">Evidence & Context:</strong>
              {alt.evidence}
            </div>

            <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 gap-2">
              <div className="flex items-center gap-3">
                <span>MD: <strong className="text-white">{alt.current_md.toFixed(1)} m</strong></span>
                {alt.assigned_to && (
                  <span className="flex items-center gap-1 text-indigo-400 font-bold">
                    <UserCheck className="w-3 h-3" /> Assigned: {alt.assigned_to}
                  </span>
                )}
              </div>
              <span className="text-amber-400/90 font-medium">{alt.disclaimer}</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" /> {new Date(alt.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Alert Detail, Notes & Resolution Modal */}
      {selectedAlertModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedAlertModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <AlertOctagon className="w-5 h-5 text-rose-400" />
              <div>
                <h2 className="text-base font-bold text-white uppercase tracking-wider">
                  Alert Lifecycle Operations ({selectedAlertModal.alert_id})
                </h2>
                <p className="text-xs text-slate-400">Wellbore: {selectedAlertModal.well_id} | Created: {selectedAlertModal.created_at}</p>
              </div>
            </div>

            {/* Alert Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 text-[10px] block">SEVERITY</span>
                <strong className={`px-2 py-0.5 rounded inline-block text-[10px] font-bold border ${getSeverityStyle(selectedAlertModal.severity)}`}>
                  {selectedAlertModal.severity}
                </strong>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">STATUS</span>
                <strong className={`px-2 py-0.5 rounded inline-block text-[10px] font-bold border ${getStatusBadge(selectedAlertModal.status)}`}>
                  {selectedAlertModal.status}
                </strong>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">MEASURED DEPTH</span>
                <strong className="text-emerald-400">{selectedAlertModal.current_md.toFixed(1)} m</strong>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">ASSIGNED TO</span>
                <strong className="text-indigo-400">{selectedAlertModal.assigned_to || "Unassigned"}</strong>
              </div>
            </div>

            {/* Assignment Section */}
            {selectedAlertModal.status !== "RESOLVED" && (
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-2">
                <span className="text-slate-300 font-bold block uppercase tracking-wider">Assign Alert to Engineer</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={assigneeId}
                    onChange={(e) => setAssigneeId(e.target.value)}
                    placeholder="Enter engineer UUID / username (e.g., engineer_01)"
                    className="flex-1 bg-slate-900 border border-slate-700 text-white rounded px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={() => handleAssign(selectedAlertModal.alert_id)}
                    disabled={!assigneeId.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded font-bold transition-all text-xs"
                  >
                    ASSIGN
                  </button>
                </div>
              </div>
            )}

            {/* Notes Thread */}
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Operational Notes Thread</span>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2 max-h-40 overflow-y-auto">
                {notesLoading && <p className="text-xs text-slate-500 italic">Loading notes...</p>}
                {!notesLoading && alertNotes.length === 0 && (
                  <p className="text-xs text-slate-500 italic">No notes added yet for this alert.</p>
                )}
                {alertNotes.map((n) => (
                  <div key={n.id} className="border-b border-slate-800 pb-2 text-xs space-y-0.5">
                    <div className="flex items-center justify-between text-slate-400 text-[10px]">
                      <span className="font-bold text-indigo-400">{n.author_id}</span>
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-slate-200">{n.note_text}</p>
                  </div>
                ))}
              </div>

              {/* Add Note Input */}
              {selectedAlertModal.status !== "RESOLVED" && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newNoteText}
                    onChange={(e) => setNewNoteText(e.target.value)}
                    placeholder="Add operational investigation note..."
                    className="flex-1 bg-slate-950 border border-slate-700 text-white rounded px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={() => handleAddNote(selectedAlertModal.alert_id)}
                    disabled={!newNoteText.trim()}
                    className="bg-slate-800 hover:bg-slate-700 text-blue-400 border border-slate-700 px-3 py-1.5 rounded font-bold transition-all text-xs flex items-center gap-1"
                  >
                    <Send className="w-3 h-3" /> ADD NOTE
                  </button>
                </div>
              )}
            </div>

            {/* Resolution Form */}
            {selectedAlertModal.status !== "RESOLVED" && (
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <label className="text-slate-300 font-bold block text-xs uppercase tracking-wider">
                  Final Operational Resolution Summary:
                </label>
                <textarea
                  value={resolveNotes}
                  onChange={(e) => setResolveNotes(e.target.value)}
                  placeholder="Enter engineer investigation summary and resolution actions taken..."
                  className="w-full bg-slate-900 text-slate-200 border border-slate-700 rounded-lg p-3 h-20 focus:outline-none focus:border-emerald-500 text-xs font-mono"
                />
                <button
                  onClick={() => handleResolve(selectedAlertModal.alert_id)}
                  disabled={!resolveNotes.trim()}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2 rounded-lg font-bold transition-all text-xs uppercase tracking-wider shadow-lg shadow-emerald-500/20"
                >
                  CONFIRM RESOLUTION & CLOSE ALERT
                </button>
              </div>
            )}

            {/* Resolved Summary View */}
            {selectedAlertModal.status === "RESOLVED" && (
              <div className="bg-emerald-950/40 border border-emerald-500/30 rounded-lg p-4 space-y-2">
                <span className="text-xs font-bold text-emerald-400 block uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> RESOLVED OPERATIONAL SUMMARY
                </span>
                <p className="text-xs text-slate-200">{selectedAlertModal.resolution_notes || "No notes recorded."}</p>
                <div className="text-[10px] text-slate-400 flex justify-between border-t border-emerald-900/50 pt-2">
                  <span>Resolved By: <strong className="text-white">{selectedAlertModal.resolved_by || "System"}</strong></span>
                  <span>Resolved At: {selectedAlertModal.resolved_at}</span>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setSelectedAlertModal(null)}
                className="bg-slate-800 text-slate-300 px-4 py-1.5 rounded-lg font-bold text-xs"
              >
                CLOSE WINDOW
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
