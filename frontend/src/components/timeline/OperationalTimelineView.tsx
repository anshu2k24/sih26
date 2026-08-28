import React, { useState, useEffect } from "react";
import { fetchWellTimeline, postShiftNoteApi } from "../../services/api";
import {
  Clock,
  Send,
  RefreshCw,
  ShieldAlert,
  FileText,
  ShieldCheck,
  Radio,
  MessageSquare,
} from "lucide-react";

interface OperationalTimelineViewProps {
  wellId: string;
  currentMd?: number;
}

export const OperationalTimelineView: React.FC<OperationalTimelineViewProps> = ({
  wellId,
  currentMd = 2500.0,
}) => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeCategory, setActiveCategory] = useState<string>("ALL");
  const [noteText, setNoteText] = useState<string>("");
  const [submittingNote, setSubmittingNote] = useState<boolean>(false);

  const loadTimeline = () => {
    setLoading(true);
    fetchWellTimeline(wellId, activeCategory)
      .then((res) => {
        if (res && res.timeline_events) {
          setEvents(res.timeline_events);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadTimeline();
  }, [wellId, activeCategory]);

  const handleAddShiftNote = async () => {
    if (!noteText.trim()) return;
    setSubmittingNote(true);
    const res = await postShiftNoteApi(wellId, noteText, currentMd);
    setSubmittingNote(false);
    if (res) {
      setNoteText("");
      loadTimeline();
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "ALERT":
        return <ShieldAlert className="w-4 h-4 text-rose-400" />;
      case "NOTE":
        return <MessageSquare className="w-4 h-4 text-blue-400" />;
      case "AUDIT":
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case "DOCUMENT":
        return <FileText className="w-4 h-4 text-cyan-400" />;
      default:
        return <Radio className="w-4 h-4 text-amber-400" />;
    }
  };

  const getCategoryBadgeStyle = (category: string) => {
    switch (category) {
      case "ALERT":
        return "bg-rose-950/80 text-rose-400 border-rose-500/30";
      case "NOTE":
        return "bg-blue-950/80 text-blue-400 border-blue-500/30";
      case "AUDIT":
        return "bg-emerald-950/80 text-emerald-400 border-emerald-500/30";
      case "DOCUMENT":
        return "bg-cyan-950/80 text-cyan-400 border-cyan-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-5 font-mono">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              OPERATIONAL SHIFT TIMELINE — WELL {wellId}
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Aggregated chronological & depth-correlated timeline of shift notes, alerts, document events, and audit logs.
          </p>
        </div>

        <button
          onClick={loadTimeline}
          className="self-start md:self-center bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded-lg border border-slate-700 font-bold transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* Add Shift Note Box */}
      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-blue-400" /> Post Shift Log Entry
          </span>
          <span className="text-slate-400 text-[11px]">
            MD: <strong className="text-emerald-400">{currentMd.toFixed(1)} m</strong>
          </span>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Enter operator shift log entry or drilling observation..."
            className="flex-1 bg-slate-900 border border-slate-700 text-white rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleAddShiftNote}
            disabled={submittingNote || !noteText.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold px-4 py-2 rounded-lg text-xs transition-all flex items-center gap-1.5 shadow-lg shadow-blue-500/20"
          >
            <Send className="w-3.5 h-3.5" /> POST NOTE
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
        {(["ALL", "NOTE", "ALERT", "AUDIT", "DOCUMENT"] as const).map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1.5 rounded-lg border transition-all ${
              activeCategory === cat
                ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/20"
                : "bg-slate-950 text-slate-400 border-slate-800 hover:text-white"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Vertical Timeline Feed */}
      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {events.length === 0 && !loading && (
          <div className="text-xs text-slate-500 italic py-6">
            No operational timeline events recorded for category [{activeCategory}].
          </div>
        )}

        {events.map((evt) => (
          <div key={evt.timeline_id} className="relative group">
            {/* Dot marker */}
            <div className="absolute -left-[23px] top-1 bg-slate-900 border border-slate-700 rounded-full p-1 shadow-md">
              {getCategoryIcon(evt.event_category)}
            </div>

            <div className="bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-xl p-3.5 transition-all space-y-2">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-1 border-b border-slate-850 pb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getCategoryBadgeStyle(evt.event_category)}`}>
                    {evt.event_category}
                  </span>
                  <strong className="text-white font-bold text-xs">{evt.title}</strong>
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-400">
                  {evt.md_depth > 0 && (
                    <span className="text-emerald-400 font-bold">
                      MD: {evt.md_depth.toFixed(1)} m
                    </span>
                  )}
                  <span>{new Date(evt.timestamp).toLocaleString()}</span>
                </div>
              </div>

              <p className="text-xs text-slate-300 font-sans">{evt.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
