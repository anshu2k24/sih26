import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { searchKnowledgeRepository } from "../services/api";
import type { HistoricalEventEpisode, KnowledgeSearchResponse } from "../types/api";
import { ArrowLeft, Shield, AlertTriangle, FileText, CheckCircle2, Database } from "lucide-react";

export const EventEvidencePage: React.FC = () => {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();

  const [eventData, setEventData] = useState<HistoricalEventEpisode | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!eventId) return;
    setLoading(true);
    setError(null);

    const decodedId = decodeURIComponent(eventId);

    searchKnowledgeRepository({ q: decodedId, limit: 10 })
      .then((res: KnowledgeSearchResponse | null) => {
        if (res && res.results && res.results.length > 0) {
          const match = res.results.find((e: HistoricalEventEpisode) => e.event_episode_id === decodedId) || res.results[0];
          setEventData(match);
        } else {
          setError(`Verified DDR evidence record '${decodedId}' not found.`);
        }
        setLoading(false);
      })
      .catch((err: unknown) => {
        console.error(err);
        setError(`Error loading DDR evidence record '${decodedId}'.`);
        setLoading(false);
      });
  }, [eventId]);

  const getBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case "FORMATION_MUD_LOSS":
      case "CEMENTING/OPERATIONAL_LOSS":
        return "bg-rose-950/80 text-rose-400 border-rose-500/40";
      case "Tight Hole":
      case "Pack-off":
        return "bg-amber-950/80 text-amber-400 border-amber-500/40";
      case "Stuck Pipe":
      case "Kick":
        return "bg-purple-950/80 text-purple-400 border-purple-500/40";
      case "Equipment Failure":
        return "bg-blue-950/80 text-blue-400 border-blue-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb Header */}
      <div className="flex items-center justify-between font-mono text-xs border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Link to="/dashboard" className="text-slate-400 hover:text-white flex items-center gap-1 hover:underline">
            <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
          </Link>
          <span className="text-slate-600">/</span>
          <Link to="/knowledge" className="text-slate-400 hover:text-white hover:underline">
            Knowledge Repository
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-blue-400 font-bold">{eventId}</span>
        </div>

        <div className="flex items-center gap-2 text-slate-400">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Equinor Volve Verified DDR Audit Record</span>
        </div>
      </div>

      {loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center font-mono text-xs text-slate-400 animate-pulse space-y-2">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <div>Loading verified DDR event evidence...</div>
        </div>
      )}

      {error && !loading && (
        <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-6 text-rose-300 text-xs font-mono flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && eventData && (
        <div className="space-y-6">
          {/* Scientific Disclaimer Banner */}
          <div className="bg-amber-950/40 border border-amber-500/40 rounded-xl p-4 text-xs font-mono text-amber-300 flex items-center justify-between shadow-lg">
            <div className="flex items-center gap-2 font-bold tracking-wide">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>HISTORICAL OFFSET EVENT — NOT A PREDICTION</span>
            </div>
            <span className="text-amber-400/80 text-[11px]">
              Observed Equinor Volve Daily Drilling Report Record
            </span>
          </div>

          {/* Main Record Detail Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl space-y-6">
            {/* Header Banner */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5 font-mono">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-xl font-bold text-white tracking-wide">{eventData.event_type}</h1>
                  <span className={`text-xs px-3 py-1 rounded font-bold border ${getBadgeStyle(eventData.event_type)}`}>
                    {eventData.event_domain || "DRILLING_RISK"}
                  </span>
                </div>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-3">
                  <span>Well: <strong className="text-emerald-400">{eventData.well_id}</strong></span>
                  <span>•</span>
                  <span>Onset MD: <strong className="text-white">{eventData.onset_md} m</strong></span>
                  <span>•</span>
                  <span>TVD: <strong className="text-white">{eventData.onset_tvd ? `${eventData.onset_tvd} m` : "N/A"}</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(`/wells/${encodeURIComponent(eventData.well_id)}`)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-2 rounded-lg font-bold transition-all border border-slate-700 flex items-center gap-1.5"
                >
                  <FileText className="w-4 h-4 text-blue-400" />
                  VIEW WELL INTELLIGENCE ➔
                </button>
              </div>
            </div>

            {/* Observed Evidence Box */}
            <div className="space-y-2 font-mono">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                OBSERVED DDR EVIDENCE TEXT
              </span>
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 font-sans text-slate-200 text-sm leading-relaxed">
                {eventData.primary_evidence}
              </div>
            </div>

            {/* Mitigation & Resolution Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono text-xs">
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2">
                <span className="text-blue-400 font-bold uppercase tracking-wider block">Historical Mitigation Response</span>
                <p className="font-sans text-slate-300 text-xs">{eventData.mitigation_text || "None recorded in DDR"}</p>
              </div>

              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2">
                <span className="text-amber-400 font-bold uppercase tracking-wider block">Historical Resolution Outcome</span>
                <p className="font-sans text-slate-300 text-xs">{eventData.resolution_text || "None recorded in DDR"}</p>
              </div>
            </div>

            {/* Provenance & Source Metadata Footer */}
            <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-slate-400">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-400 shrink-0" />
                <span>Primary Source Record: <strong className="text-white">{eventData.primary_source_record}</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Equinor Volve Daily Drilling Report Verified Dataset</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
