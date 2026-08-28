import React, { useState, useEffect, useMemo } from "react";
import type { WellIntelligenceResponse, HistoricalEventEpisode } from "../types/api";
import { fetchWellFullIntelligence } from "../services/api";
import {
  ArrowLeft,
  Database,
  FileText,
  Filter,
  Shield,
  Layers,
  MapPin,
  Clock,
  AlertTriangle,
  Info,
  X
} from "lucide-react";

interface OffsetWellIntelligenceProps {
  activeWellId: string;
  offsetWellId?: string;
  wellIdParam?: string;
  currentMd?: number;
  onBackToMap?: () => void;
  onSelectWell?: (wellId: string) => void;
  onOpenEventDetail?: (event: HistoricalEventEpisode) => void;
}

export const OffsetWellIntelligence: React.FC<OffsetWellIntelligenceProps> = ({
  activeWellId,
  offsetWellId,
  wellIdParam,
  currentMd = 1509.1,
  onBackToMap,
  onSelectWell,
  onOpenEventDetail,
}) => {
  const targetWellId = wellIdParam || offsetWellId || "15/9-F-1 C";
  const [data, setData] = useState<WellIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [selectedEventType, setSelectedEventType] = useState<string>("ALL");
  const [minMdFilter, setMinMdFilter] = useState<number>(0);
  const [maxMdFilter, setMaxMdFilter] = useState<number>(5000);
  const [selectedEventModal, setSelectedEventModal] = useState<HistoricalEventEpisode | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchWellFullIntelligence(targetWellId, activeWellId)
      .then((res) => {
        if (res) {
          setData(res);
          // Set min/max MD slider boundaries based on events if available
          if (res.events && res.events.length > 0) {
            const mds = res.events.map((e) => e.onset_md);
            setMinMdFilter(Math.floor(Math.min(...mds) / 100) * 100);
            setMaxMdFilter(Math.ceil(Math.max(...mds) / 100) * 100 + 200);
          }
        } else {
          setError(`Unable to load offset well intelligence profile for '${targetWellId}'.`);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError(`Error loading intelligence profile for '${targetWellId}'.`);
        setLoading(false);
      });
  }, [targetWellId, activeWellId]);

  // Filtered events computation
  const filteredEvents = useMemo(() => {
    if (!data?.events) return [];
    return data.events.filter((ev) => {
      const matchType = selectedEventType === "ALL" || ev.event_type === selectedEventType;
      const matchDepth = ev.onset_md >= minMdFilter && ev.onset_md <= maxMdFilter;
      return matchType && matchDepth;
    });
  }, [data, selectedEventType, minMdFilter, maxMdFilter]);

  // Event category badge color helper
  const getEventBadgeStyle = (eventType: string) => {
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

  const formatDistance = (distKm?: number | null, distM?: number | null) => {
    if (distKm == null && distM == null) return "Same Platform Complex";
    if (distKm && distKm >= 1.0) return `${distKm.toFixed(2)} km`;
    if (distM != null) return `${distM.toFixed(0)} m`;
    return "N/A";
  };

  const metadata = data?.well_metadata;
  const availableEventTypes = useMemo(() => {
    if (!data?.event_counts) return [];
    return Object.keys(data.event_counts);
  }, [data]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans pb-16 selection:bg-blue-500 selection:text-white">
      {/* Top Banner Navigation */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 sticky top-0 z-50 shadow-xl">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBackToMap}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 px-3.5 py-1.5 rounded-lg border border-slate-700 font-mono text-xs font-bold transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Nearby Wells Map
            </button>

            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-400" />
                  OFFSET WELL INTELLIGENCE: <span className="text-emerald-400">{offsetWellId}</span>
                </h1>
                <span className="text-xs px-2.5 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-500/30 font-mono">
                  HISTORICAL DDR / NWIS INTELLIGENCE
                </span>
              </div>
            </div>
          </div>

          {/* Active Drilling Well vs Historical Offset Well Comparison Banner */}
          <div className="flex items-center gap-3 bg-slate-950/90 px-4 py-2 rounded-lg border border-slate-800 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-amber-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
              <span>ACTIVE: <strong>{activeWellId}</strong> ({currentMd.toFixed(1)}m)</span>
            </div>
            <span className="text-slate-600">➔</span>
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <MapPin className="w-3.5 h-3.5 text-emerald-400" />
              <span>OFFSET: <strong>{offsetWellId}</strong></span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="text-slate-300 font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              Dist: {formatDistance(data?.distance_km, data?.distance_m)}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Loading State */}
        {loading && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center font-mono text-sm text-slate-400 animate-pulse space-y-2">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <div>Loading historical DDR offset intelligence for <strong>{offsetWellId}</strong>...</div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-6 text-rose-300 text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={onBackToMap}
              className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 rounded border border-slate-700"
            >
              Return to Map
            </button>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* Section 1: Well Summary & Provenance Banner */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center gap-2">
                    <Info className="w-4 h-4 text-blue-400" />
                    Well Summary & Metadata
                  </h2>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    Deterministic intelligence extracted from Equinor Volve historical drilling records.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {onSelectWell && (
                    <button
                      onClick={() => onSelectWell(targetWellId)}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-mono font-bold px-3.5 py-1.5 rounded-lg border border-emerald-500/40 transition-all flex items-center gap-1.5"
                    >
                      Set as Active Well in Telemetry Console ➔
                    </button>
                  )}
                </div>
              </div>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 text-xs font-mono">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">WELL ID</span>
                  <strong className="text-white text-sm">{offsetWellId}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">STATUS</span>
                  <strong className="text-emerald-400">{metadata?.status || "Historical Wellbore"}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">FIELD</span>
                  <strong className="text-slate-200">{metadata?.field || "Volve (Block 15/9)"}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">OPERATOR</span>
                  <strong className="text-slate-200">{metadata?.operator || "Equinor"}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">WATER DEPTH</span>
                  <strong className="text-slate-200">{metadata?.water_depth_m ? `${metadata.water_depth_m} m` : "84.0 m"}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">SLOT</span>
                  <strong className="text-slate-200">{metadata?.slot_name || "Platform Slot"}</strong>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-850">
                  <span className="text-slate-400 block text-[10px]">TOTAL EVENTS</span>
                  <strong className="text-amber-400 text-sm">{data.total_events} Verified Episodes</strong>
                </div>
              </div>
            </div>

            {/* Section 2: Event Summary Breakdown Cards */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                Historical Event Breakdown ({data.total_events} Total)
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 font-mono">
                {availableEventTypes.map((type) => {
                  const count = data.event_counts[type];
                  return (
                    <div
                      key={type}
                      onClick={() => setSelectedEventType(selectedEventType === type ? "ALL" : type)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer ${
                        selectedEventType === type
                          ? "bg-purple-950/60 border-purple-500/60 text-white shadow-md shadow-purple-500/10"
                          : "bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300"
                      }`}
                    >
                      <div className="text-[11px] text-slate-400 truncate">{type}</div>
                      <div className="text-lg font-bold text-amber-400 mt-0.5">{count}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Section 3: Filter & Control Toolbar */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-emerald-400" />
                <span className="font-bold text-slate-300">Filter Events:</span>
              </div>

              <div className="flex flex-wrap items-center gap-4">
                {/* Event Type Filter */}
                <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Type:</span>
                  <select
                    value={selectedEventType}
                    onChange={(e) => setSelectedEventType(e.target.value)}
                    className="bg-slate-900 text-white font-mono text-xs px-2 py-1 rounded border border-slate-700 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ALL">All Event Types ({data.total_events})</option>
                    {availableEventTypes.map((t) => (
                      <option key={t} value={t}>
                        {t} ({data.event_counts[t]})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Depth Range Controls */}
                <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Min MD:</span>
                  <input
                    type="number"
                    value={minMdFilter}
                    onChange={(e) => setMinMdFilter(Number(e.target.value))}
                    className="w-20 bg-slate-900 text-white text-xs font-mono px-2 py-1 rounded border border-slate-700 focus:outline-none"
                  />
                  <span className="text-slate-400">m — Max MD:</span>
                  <input
                    type="number"
                    value={maxMdFilter}
                    onChange={(e) => setMaxMdFilter(Number(e.target.value))}
                    className="w-20 bg-slate-900 text-white text-xs font-mono px-2 py-1 rounded border border-slate-700 focus:outline-none"
                  />
                  <span className="text-slate-400">m</span>
                </div>

                {(selectedEventType !== "ALL" || minMdFilter > 0 || maxMdFilter < 5000) && (
                  <button
                    onClick={() => {
                      setSelectedEventType("ALL");
                      setMinMdFilter(0);
                      setMaxMdFilter(5000);
                    }}
                    className="text-xs text-rose-400 hover:underline font-bold"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>

            {/* Section 4: Main Content — Vertical Depth Timeline (1/3) + Historical Events List (2/3) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Depth Timeline Column */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col h-[600px]">
                <div className="border-b border-slate-800 pb-3 mb-4">
                  <h3 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider flex items-center gap-2">
                    <Clock className="w-4 h-4 text-emerald-400" />
                    Vertical Depth Timeline
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    Events plotted chronologically by Measured Depth (MD).
                  </p>
                </div>

                {filteredEvents.length > 0 ? (
                  <div className="relative flex-1 overflow-y-auto pr-2 pl-4">
                    {/* Continuous vertical line */}
                    <div className="absolute left-6 top-3 bottom-3 w-0.5 bg-slate-800"></div>

                    <div className="space-y-6 relative z-10">
                      {filteredEvents.map((ev, idx) => (
                        <div
                          key={ev.event_episode_id || idx}
                          onClick={() => setSelectedEventModal(ev)}
                          className="flex items-start gap-4 cursor-pointer group"
                        >
                          {/* Node Badge */}
                          <div className="w-5 h-5 rounded-full bg-slate-900 border-2 border-emerald-400 flex items-center justify-center shrink-0 shadow-md group-hover:scale-110 group-hover:border-amber-400 transition-all">
                            <div className="w-2 h-2 rounded-full bg-emerald-400 group-hover:bg-amber-400"></div>
                          </div>

                          {/* Event Timeline Content Item */}
                          <div className="bg-slate-950 border border-slate-800 group-hover:border-emerald-500/50 p-3 rounded-lg flex-1 space-y-1 transition-all shadow-sm">
                            <div className="flex items-center justify-between font-mono">
                              <span className="font-bold text-emerald-400 text-xs">
                                {ev.onset_md.toFixed(1)} m
                              </span>
                              <span className="text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                                {ev.primary_source_record}
                              </span>
                            </div>
                            <div className="text-xs font-bold text-slate-200 truncate">
                              {ev.event_type}
                            </div>
                            <div className="text-[11px] text-slate-400 line-clamp-2 leading-tight">
                              {ev.primary_evidence}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-center p-6 text-slate-400 font-mono text-xs border border-dashed border-slate-850 rounded-lg">
                    No historical events fall within the current depth filter range.
                  </div>
                )}
              </div>

              {/* Event Cards & Details Column */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-400" />
                    Historical DDR Events ({filteredEvents.length})
                  </span>
                  <span className="text-slate-400">
                    Source: Verified Equinor Volve DDR Records
                  </span>
                </div>

                {filteredEvents.length > 0 ? (
                  <div className="space-y-3 max-h-[550px] overflow-y-auto pr-1">
                    {filteredEvents.map((ev, idx) => (
                      <div
                        key={ev.event_episode_id || idx}
                        className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg space-y-3 hover:border-slate-700 transition-all"
                      >
                        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-xs px-2.5 py-1 rounded font-mono font-bold border ${getEventBadgeStyle(
                                ev.event_type
                              )}`}
                            >
                              {ev.event_type}
                            </span>
                            <span className="text-xs font-mono font-bold text-emerald-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                              MD: {ev.onset_md.toFixed(1)} m
                            </span>
                            {ev.onset_tvd && (
                              <span className="text-xs font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                                TVD: {ev.onset_tvd.toFixed(1)} m
                              </span>
                            )}
                          </div>

                          <span className="text-[11px] font-mono text-slate-400">
                            {ev.onset_timestamp}
                          </span>
                        </div>

                        {/* Primary Evidence Excerpt */}
                        <div className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-950/60 p-3 rounded-lg border border-slate-850">
                          <strong className="text-slate-400 font-mono uppercase text-[11px] block mb-1">
                            Primary Evidence:
                          </strong>
                          {ev.primary_evidence}
                        </div>

                        {/* Mitigation & Resolution */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-sans">
                          {ev.mitigation_text && ev.mitigation_text !== "None recorded" && (
                            <div className="bg-amber-950/20 border border-amber-500/20 p-2.5 rounded-lg text-amber-200/90">
                              <strong className="text-amber-400 font-mono text-[11px] block mb-0.5">
                                Mitigation Action:
                              </strong>
                              {ev.mitigation_text}
                            </div>
                          )}

                          {ev.resolution_text && ev.resolution_text !== "None recorded" && (
                            <div className="bg-emerald-950/20 border border-emerald-500/20 p-2.5 rounded-lg text-emerald-200/90">
                              <strong className="text-emerald-400 font-mono text-[11px] block mb-0.5">
                                Resolution / Status:
                              </strong>
                              {ev.resolution_text}
                            </div>
                          )}
                        </div>

                        {/* Source Traceability Badge & Detail Trigger */}
                        <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono">
                          <div className="flex items-center gap-1.5 text-slate-400">
                            <Shield className="w-3.5 h-3.5 text-blue-400" />
                            <span>Source Record:</span>
                            <code className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-200">
                              {ev.source_label}
                            </code>
                          </div>

                          <button
                            onClick={() => {
                              if (onOpenEventDetail) {
                                onOpenEventDetail(ev);
                              } else {
                                setSelectedEventModal(ev);
                              }
                            }}
                            className="text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1 hover:underline"
                          >
                            View Full Provenance →
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl text-slate-400 text-xs font-mono bg-slate-900/50">
                    No historical DDR events match the current filter criteria for {offsetWellId}.
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>

      {/* Event Full Detail Modal */}
      {selectedEventModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-2xl relative">
            <button
              onClick={() => setSelectedEventModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg bg-slate-800 hover:bg-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <span
                className={`text-xs px-2.5 py-1 rounded font-mono font-bold border ${getEventBadgeStyle(
                  selectedEventModal.event_type
                )}`}
              >
                {selectedEventModal.event_type}
              </span>
              <h3 className="text-base font-bold text-white font-mono">
                Event Provenance & DDR Evidence Details
              </h3>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-850">
                <div>
                  <span className="text-slate-400 block text-[10px]">WELLBORE</span>
                  <strong className="text-emerald-400">{selectedEventModal.wellbore_id}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">ONSET DEPTH (MD)</span>
                  <strong className="text-amber-400">{selectedEventModal.onset_md.toFixed(1)} m</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">ONSET TVD</span>
                  <strong className="text-slate-200">
                    {selectedEventModal.onset_tvd ? `${selectedEventModal.onset_tvd.toFixed(1)} m` : "Data unavailable"}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">TIMESTAMP</span>
                  <strong className="text-slate-200">{selectedEventModal.onset_timestamp}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">EVENT DOMAIN</span>
                  <strong className="text-slate-200">{selectedEventModal.event_domain}</strong>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">SOURCE RECORD</span>
                  <strong className="text-blue-400">{selectedEventModal.primary_source_record}</strong>
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="font-bold text-slate-300 uppercase text-[11px]">
                  Verified Primary DDR Text:
                </span>
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-850 text-slate-200 leading-relaxed font-sans text-xs font-medium">
                  {selectedEventModal.primary_evidence}
                </div>
              </div>

              {selectedEventModal.mitigation_text && selectedEventModal.mitigation_text !== "None recorded" && (
                <div className="space-y-1">
                  <span className="font-bold text-amber-400 uppercase text-[11px]">
                    Recorded Mitigation:
                  </span>
                  <div className="bg-amber-950/30 p-3 rounded-lg border border-amber-500/30 text-amber-200 font-sans text-xs">
                    {selectedEventModal.mitigation_text}
                  </div>
                </div>
              )}

              {selectedEventModal.resolution_text && selectedEventModal.resolution_text !== "None recorded" && (
                <div className="space-y-1">
                  <span className="font-bold text-emerald-400 uppercase text-[11px]">
                    Recorded Resolution:
                  </span>
                  <div className="bg-emerald-950/30 p-3 rounded-lg border border-emerald-500/30 text-emerald-200 font-sans text-xs">
                    {selectedEventModal.resolution_text}
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-slate-800 text-[10px] text-slate-400 flex items-center justify-between">
                <span>Dataset: Equinor Volve verified_event_episodes_v2.csv</span>
                <span className="text-emerald-400 font-bold">100% Verified DDR Record</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
