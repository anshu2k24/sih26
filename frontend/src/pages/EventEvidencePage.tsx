import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { searchKnowledgeRepository } from "../services/api";
import type { HistoricalEventEpisode, KnowledgeSearchResponse } from "../types/api";
import {
  ArrowLeft,
  Shield,
  AlertTriangle,
  FileText,
  CheckCircle2,
  Database,
  MapPin,
  Gauge,
  Clock,
  ChevronRight,
  Activity,
  Layers,
  ExternalLink
} from "lucide-react";

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
          const match =
            res.results.find((e: HistoricalEventEpisode) => e.event_episode_id === decodedId) ||
            res.results[0];
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

  const getEventBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case "FORMATION_MUD_LOSS":
      case "CEMENTING/OPERATIONAL_LOSS":
        return {
          color: "#FF5E5E",
          background: "rgba(255, 94, 94, 0.08)",
          border: "1px solid rgba(255, 94, 94, 0.35)",
        };
      case "Tight Hole":
      case "Pack-off":
        return {
          color: "#FF9A3D",
          background: "rgba(255, 154, 61, 0.08)",
          border: "1px solid rgba(255, 154, 61, 0.35)",
        };
      case "Stuck Pipe":
      case "Kick":
        return {
          color: "#D946EF",
          background: "rgba(217, 70, 239, 0.08)",
          border: "1px solid rgba(217, 70, 239, 0.35)",
        };
      case "Equipment Failure":
        return {
          color: "#38BDF8",
          background: "rgba(56, 189, 248, 0.08)",
          border: "1px solid rgba(56, 189, 248, 0.35)",
        };
      default:
        return {
          color: "#F5F5F5",
          background: "rgba(255, 255, 255, 0.04)",
          border: "1px solid rgba(255, 255, 255, 0.18)",
        };
    }
  };

  const glassPanelStyle: React.CSSProperties = {
    background: "rgba(15, 10, 5, 0.70)",
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: "1px solid rgba(255, 122, 0, 0.3)",
    borderRadius: "20px",
    boxShadow: "0 10px 40px rgba(0,0,0,0.6), inset 0 0 20px rgba(255,122,0,0.04), 0 0 20px rgba(255,122,0,0.08)",
  };

  const glassMetricCardStyle: React.CSSProperties = {
    background: "rgba(18, 14, 10, 0.55)",
    border: "1px solid rgba(255, 122, 0, 0.15)",
    borderRadius: "12px",
    padding: "14px 16px",
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12 selection:bg-[#FF7A00] selection:text-white">
      {/* 1. Header & Breadcrumb Trail */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2 sm:gap-3 text-xs font-mono">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all hover:bg-[rgba(255,122,0,0.15)] group"
            style={{
              background: "rgba(255, 122, 0, 0.08)",
              border: "1px solid rgba(255, 122, 0, 0.3)",
              color: "#FF9A3D",
            }}
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back</span>
          </button>

          <span className="text-slate-600">/</span>

          <Link
            to="/dashboard"
            className="text-slate-400 hover:text-white transition-colors"
          >
            Dashboard
          </Link>

          <span className="text-slate-600">/</span>

          <Link
            to="/knowledge"
            className="text-slate-400 hover:text-white transition-colors"
          >
            Knowledge Repository
          </Link>

          <span className="text-slate-600">/</span>

          <span className="px-2.5 py-0.5 rounded font-mono font-bold text-xs bg-[#FF7A00]/10 border border-[#FF7A00]/30 text-[#FF7A00]">
            {eventId}
          </span>
        </div>

        {/* Right Audit Seal Badge */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium"
          style={{
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#10B981",
          }}
        >
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Equinor Volve Verified DDR Audit Record</span>
        </div>
      </div>

      {/* 2. Loading Skeleton */}
      {loading && (
        <div
          className="p-16 text-center font-mono text-xs text-slate-400 space-y-3"
          style={glassPanelStyle}
        >
          <div className="w-9 h-9 border-2 border-[#FF7A00] border-t-transparent rounded-full animate-spin mx-auto shadow-[0_0_15px_rgba(255,122,0,0.5)]"></div>
          <div className="text-slate-300 text-sm font-semibold">Loading verified DDR event evidence...</div>
          <p className="text-[#737373] text-xs">Retrieving semantic incident records from Equinor Volve repository</p>
        </div>
      )}

      {/* 3. Error Banner */}
      {error && !loading && (
        <div
          className="p-6 text-rose-300 text-xs font-mono flex items-center gap-3 rounded-2xl"
          style={{
            background: "rgba(255, 94, 94, 0.08)",
            border: "1px solid rgba(255, 94, 94, 0.4)",
          }}
        >
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
          <span className="font-semibold">{error}</span>
        </div>
      )}

      {/* 4. Main Event Detail View */}
      {!loading && !error && eventData && (
        <div className="space-y-6">
          {/* Scientific Disclaimer Banner */}
          <div
            className="p-4 rounded-xl flex items-center justify-between font-mono text-xs"
            style={{
              background: "rgba(255, 122, 0, 0.06)",
              border: "1px solid rgba(255, 122, 0, 0.35)",
              boxShadow: "0 0 20px rgba(255, 122, 0, 0.06)",
            }}
          >
            <div className="flex items-center gap-2.5 font-bold text-[#FF9A3D] tracking-wide">
              <AlertTriangle className="w-4 h-4 text-[#FF7A00] shrink-0 animate-pulse" />
              <span>HISTORICAL OFFSET EVENT — NOT A PREDICTION</span>
            </div>
            <span className="text-[#A1A1A1] text-[11px] hidden sm:inline">
              Observed Equinor Volve Daily Drilling Report Record
            </span>
          </div>

          {/* Master Glass Panel */}
          <div className="p-6 sm:p-8 space-y-6" style={glassPanelStyle}>
            {/* Card Header Banner */}
            <div
              className="flex flex-col md:flex-row md:items-center justify-between gap-5 pb-6"
              style={{ borderBottom: "1px solid rgba(255, 122, 0, 0.18)" }}
            >
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] tracking-tight">
                    {eventData.event_type}
                  </h1>
                  <span
                    className="text-xs px-3 py-1 rounded-md font-semibold tracking-wide"
                    style={getEventBadgeStyle(eventData.event_type)}
                  >
                    {eventData.event_domain || "DRILLING_RISK"}
                  </span>
                  <span
                    className="text-[11px] px-2.5 py-0.5 rounded font-mono font-medium flex items-center gap-1"
                    style={{
                      background: "rgba(16, 185, 129, 0.1)",
                      border: "1px solid rgba(16, 185, 129, 0.3)",
                      color: "#10B981",
                    }}
                  >
                    <CheckCircle2 className="w-3 h-3" /> VERIFIED DDR EPISODE
                  </span>
                </div>

                <div className="text-xs text-[#A1A1A1] font-mono flex flex-wrap items-center gap-3">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[#FF7A00]" />
                    <span>Wellbore:</span>
                    <strong className="text-white">{eventData.well_id}</strong>
                  </span>
                  <span className="text-slate-600">•</span>
                  <span className="flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5 text-[#FF7A00]" />
                    <span>Onset MD:</span>
                    <strong className="text-[#FF7A00]">{eventData.onset_md.toFixed(1)} m</strong>
                  </span>
                  <span className="text-slate-600">•</span>
                  <span>
                    TVD:{" "}
                    <strong className="text-white">
                      {eventData.onset_tvd ? `${eventData.onset_tvd.toFixed(1)} m` : "Data unavailable"}
                    </strong>
                  </span>
                </div>
              </div>

              {/* View Well Intelligence Button */}
              <div className="flex items-center">
                <button
                  onClick={() => navigate(`/wells/${encodeURIComponent(eventData.well_id)}`)}
                  className="px-5 py-2.5 rounded-xl font-bold text-xs tracking-wider uppercase flex items-center gap-2 transition-all duration-200 group"
                  style={{
                    background: "linear-gradient(135deg, rgba(255, 122, 0, 0.9) 0%, rgba(255, 94, 0, 1) 100%)",
                    boxShadow: "0 0 25px rgba(255, 122, 0, 0.35)",
                    border: "1px solid rgba(255, 200, 150, 0.3)",
                    color: "#050608",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = "0 0 35px rgba(255, 122, 0, 0.55)";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = "0 0 25px rgba(255, 122, 0, 0.35)";
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <FileText className="w-4 h-4 text-black" />
                  <span>View Well Intelligence</span>
                  <ChevronRight className="w-4 h-4 text-black group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>

            {/* 6-Metric Metadata Card Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  WELLBORE
                </span>
                <span className="text-[#F2F2F2] font-[600] text-[13px] truncate block">
                  {eventData.well_id}
                </span>
              </div>

              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  ONSET DEPTH (MD)
                </span>
                <span className="text-[#FF7A00] font-mono font-[700] text-[14px] block">
                  {eventData.onset_md.toFixed(1)} m
                </span>
              </div>

              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  ONSET TVD
                </span>
                <span className="text-[#F2F2F2] font-mono font-[600] text-[13px] block">
                  {eventData.onset_tvd ? `${eventData.onset_tvd.toFixed(1)} m` : "Unavailable"}
                </span>
              </div>

              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  TIMESTAMP
                </span>
                <span className="text-[#F2F2F2] font-mono text-[12px] truncate block">
                  {eventData.onset_timestamp || "Historical Volve"}
                </span>
              </div>

              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  EVENT DOMAIN
                </span>
                <span className="text-[#F2F2F2] text-[12px] truncate block font-medium">
                  {eventData.event_domain || "Drilling Operations"}
                </span>
              </div>

              <div style={glassMetricCardStyle}>
                <span className="text-[#737373] text-[10px] uppercase font-[600] tracking-wider block mb-1">
                  SOURCE RECORD
                </span>
                <span className="text-[#FF7A00] text-[13px] font-mono font-[600] block truncate">
                  {eventData.primary_source_record}
                </span>
              </div>
            </div>

            {/* Observed Evidence Text Callout */}
            <div className="space-y-2 font-mono">
              <span className="text-xs font-bold uppercase tracking-wider text-[#FF7A00] flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[#FF7A00]" />
                VERIFIED PRIMARY DDR EVIDENCE TEXT:
              </span>
              <div
                className="p-5 rounded-r-xl font-sans text-[#F2F2F2] text-[14px] leading-relaxed select-text"
                style={{
                  background: "rgba(10, 10, 10, 0.65)",
                  border: "1px solid rgba(255, 122, 0, 0.2)",
                  borderLeft: "4px solid #FF7A00",
                }}
              >
                {eventData.primary_evidence}
              </div>
            </div>

            {/* Mitigation & Resolution 2-Column Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono text-xs">
              <div
                className="p-5 rounded-xl space-y-2.5 flex flex-col justify-between"
                style={{
                  background: "rgba(255, 122, 0, 0.035)",
                  border: "1px solid rgba(255, 122, 0, 0.2)",
                }}
              >
                <div>
                  <span className="text-[#FF9A3D] font-bold uppercase tracking-wider block text-[11px] mb-1 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-[#FF9A3D]" />
                    Historical Mitigation Response
                  </span>
                  <p className="font-sans text-[#D4D4D8] text-xs leading-relaxed mt-2">
                    {eventData.mitigation_text || "None recorded in primary DDR text"}
                  </p>
                </div>
              </div>

              <div
                className="p-5 rounded-xl space-y-2.5 flex flex-col justify-between"
                style={{
                  background: "rgba(255, 122, 0, 0.035)",
                  border: "1px solid rgba(255, 122, 0, 0.2)",
                }}
              >
                <div>
                  <span className="text-[#FF9A3D] font-bold uppercase tracking-wider block text-[11px] mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#FF9A3D]" />
                    Historical Resolution Outcome
                  </span>
                  <p className="font-sans text-[#D4D4D8] text-xs leading-relaxed mt-2">
                    {eventData.resolution_text || "None recorded in primary DDR text"}
                  </p>
                </div>
              </div>
            </div>

            {/* Provenance & Dataset Verification Footer */}
            <div
              className="p-4 rounded-xl font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[#A1A1A1]"
              style={{
                background: "rgba(10, 10, 10, 0.5)",
                border: "1px solid rgba(255, 122, 0, 0.15)",
              }}
            >
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-[#FF7A00] shrink-0" />
                <span>
                  Primary Source Record:{" "}
                  <strong className="text-white font-mono">{eventData.primary_source_record}</strong>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-slate-300">Equinor Volve Daily Drilling Report Verified Dataset</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
