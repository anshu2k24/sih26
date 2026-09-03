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
  const [showAll, setShowAll] = useState<boolean>(false);

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


  return (
    <div 
      className="rounded-3xl p-6 font-mono h-full transition-all duration-500 flex flex-col gap-5"
      style={{
        background: "linear-gradient(145deg, rgba(255, 155, 47, 0.12) 0%, rgba(20, 27, 42, 0.8) 30%, rgba(9, 14, 25, 0.95) 100%)",
        border: "1px solid rgba(255, 155, 47, 0.2)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        boxShadow: "0 25px 70px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 155, 47, 0.15)"
      }}
    >
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              LIVE TELEMETRY FEED
            </h2>
          </div>
        </div>

        <button
          onClick={loadTimeline}
          className="self-start md:self-center bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded-lg border border-slate-700 font-bold transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* Add Shift Note Box */}
      <div 
        className="p-4 rounded-xl space-y-2 transition-all shrink-0"
        style={{
          background: "rgba(255, 255, 255, 0.055)",
          border: "1px solid rgba(255, 255, 255, 0.12)",
        }}
      >
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
            className="flex-1 text-white rounded-lg px-3.5 py-2 text-xs focus:outline-none transition-all"
            style={{
              background: "rgba(255, 255, 255, 0.055)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
            }}
          />
          <button
            onClick={handleAddShiftNote}
            disabled={submittingNote || !noteText.trim()}
            className="disabled:opacity-50 text-white font-bold px-4 py-2 rounded-lg text-xs transition-all flex items-center gap-1.5 hover:-translate-y-0.5"
            style={{
              background: "linear-gradient(135deg, #ff9b2f, #ff7a18)",
              boxShadow: "0 10px 25px rgba(255, 122, 24, 0.25)"
            }}
          >
            <Send className="w-3.5 h-3.5" /> POST NOTE
          </button>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold shrink-0">
        {(["ALL", "NOTE", "ALERT", "AUDIT", "DOCUMENT"] as const).map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 rounded-full border transition-all ${
              activeCategory === cat
                ? "bg-blue-600 text-white border-blue-500"
                : "bg-slate-900/50 text-slate-400 border-slate-800 hover:text-white hover:bg-slate-800"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Vertical Timeline Feed (Scrollable) */}
      <div className="space-y-2.5 flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-2">
        {events.length === 0 && !loading && (
          <div className="text-xs text-slate-500 italic py-6">
            No operational timeline events recorded for category [{activeCategory}].
          </div>
        )}

        {events.map((evt) => (
          <div key={evt.timeline_id} className="flex items-start gap-2.5 border-b border-slate-800/50 pb-2.5 last:border-0">
            <div className="flex-shrink-0 mt-0.5">
              {getCategoryIcon(evt.event_category)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-0.5">
                  <span className={`text-[9px] font-bold uppercase tracking-wider ${
                    evt.event_category === 'ALERT' ? 'text-rose-400' :
                    evt.event_category === 'NOTE' ? 'text-amber-400' :
                    evt.event_category === 'AUDIT' ? 'text-emerald-400' :
                    evt.event_category === 'DOCUMENT' ? 'text-cyan-400' : 'text-slate-400'
                  }`}>
                    {evt.event_category}
                  </span>
                  <p className="text-[11px] text-white font-bold leading-tight">{evt.title}</p>
                  <p className="text-[10.5px] text-slate-400 font-sans break-words whitespace-pre-wrap leading-snug">{evt.description}</p>
                </div>
                
                <div className="flex flex-col items-end text-[9px] text-slate-500 flex-shrink-0 whitespace-nowrap gap-0.5">
                  {evt.md_depth > 0 && (
                    <span className="font-mono text-slate-300">
                      MD: {evt.md_depth.toFixed(1)} m
                    </span>
                  )}
                  <span className="font-mono">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
