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
    if (action.includes("ALERT")) return "bg-amber-950/80 text-amber-400 border-amber-500/30";
    if (action.includes("VERIF") || action.includes("DOCUMENT")) return "bg-cyan-950/80 text-cyan-400 border-cyan-500/30";
    if (action.includes("REPORT")) return "bg-indigo-950/80 text-indigo-400 border-indigo-500/30";
    if (action.includes("AUTH") || action.includes("USER")) return "bg-purple-950/80 text-purple-400 border-purple-500/30";
    return "bg-slate-800 text-slate-300 border-slate-700";
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              IMMUTABLE OPERATIONAL AUDIT LOGS
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-bold flex items-center gap-1">
              <Lock className="w-3 h-3" /> APPEND-ONLY RLS ENFORCED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-proof compliance log capturing engineer decisions, alert acknowledgments, document verifications, and report dispatches.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            disabled={events.length === 0}
            className="bg-emerald-950/80 hover:bg-emerald-900 disabled:opacity-50 text-emerald-400 border border-emerald-500/30 px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> EXPORT CSV
          </button>

          <button
            onClick={loadAuditLogs}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search action, actor ID, or resource..."
            className="bg-slate-950 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-xs w-full md:w-72 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-400">Filter:</span>
          {(["ALL", "ALERT", "DOCUMENT", "REPORT", "USER"] as const).map((category) => (
            <button
              key={category}
              onClick={() => setActionFilter(category)}
              className={`px-2.5 py-1 rounded text-[11px] font-bold border transition-all ${
                actionFilter === category
                  ? "bg-emerald-600 text-white border-emerald-500"
                  : "bg-slate-950 text-slate-400 border-slate-800 hover:text-white"
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-slate-300">
          <span>Audit Records ({filteredEvents.length} shown)</span>
          <span className="text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> DB RLS Policy: UPDATE & DELETE Blocked
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold">
                <th className="p-3.5 w-8"></th>
                <th className="p-3.5">AUDIT ID</th>
                <th className="p-3.5">TIMESTAMP</th>
                <th className="p-3.5">ACTOR</th>
                <th className="p-3.5">ROLE</th>
                <th className="p-3.5">ACTION</th>
                <th className="p-3.5">RESOURCE</th>
                <th className="p-3.5">WELL ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {filteredEvents.length === 0 && !loading && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500">
                    No operational audit events found matching current criteria.
                  </td>
                </tr>
              )}
              {filteredEvents.map((evt) => {
                const isExpanded = expandedAuditId === evt.audit_id;
                return (
                  <React.Fragment key={evt.audit_id}>
                    <tr
                      onClick={() => toggleExpand(evt.audit_id)}
                      className="hover:bg-slate-850/60 cursor-pointer transition-all"
                    >
                      <td className="p-3.5 text-slate-500">
                        {isExpanded ? <ChevronDown className="w-4 h-4 text-emerald-400" /> : <ChevronRight className="w-4 h-4" />}
                      </td>
                      <td className="p-3.5 font-bold text-emerald-400 font-mono text-[11px]">{evt.audit_id}</td>
                      <td className="p-3.5 text-slate-300 text-[11px]">{new Date(evt.timestamp).toLocaleString()}</td>
                      <td className="p-3.5 text-slate-200 font-bold">{evt.actor_id}</td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 font-bold text-[10px]">
                          {evt.actor_role || "SYSTEM"}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getActionBadgeStyle(evt.action)}`}>
                          {evt.action}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-400 text-[11px]">{evt.resource_type}:{evt.resource_id}</td>
                      <td className="p-3.5 text-white font-bold">{evt.well_id || "N/A"}</td>
                    </tr>

                    {/* State Diff & Payload Inspector */}
                    {isExpanded && (
                      <tr className="bg-slate-950/80 border-b border-slate-800">
                        <td colSpan={8} className="p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                              Payload & State Diff Inspector ({evt.audit_id})
                            </span>
                            <span className="text-[10px] text-slate-500">Organization: {evt.organization_id}</span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                            <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                              <span className="text-[10px] text-amber-400 font-bold block uppercase">BEFORE STATE</span>
                              <pre className="text-[11px] text-slate-300 overflow-x-auto font-mono">
                                {evt.before_state ? JSON.stringify(evt.before_state, null, 2) : "None (New Creation)"}
                              </pre>
                            </div>

                            <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                              <span className="text-[10px] text-emerald-400 font-bold block uppercase">AFTER STATE</span>
                              <pre className="text-[11px] text-slate-300 overflow-x-auto font-mono">
                                {evt.after_state ? JSON.stringify(evt.after_state, null, 2) : "Recorded Action"}
                              </pre>
                            </div>

                            <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1">
                              <span className="text-[10px] text-cyan-400 font-bold block uppercase">EVENT PAYLOAD METADATA</span>
                              <pre className="text-[11px] text-slate-300 overflow-x-auto font-mono">
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
  );
};
