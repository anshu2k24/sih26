import React, { useState, useEffect, useCallback } from "react";
import type { KnowledgeSearchResponse, HistoricalEventEpisode, WellItem } from "../types/api";
import { searchKnowledgeRepository } from "../services/api";
import {
  Search,
  Database,
  Filter,
  Shield,
  FileText,
  ArrowLeft,
  X,
  MapPin,
  AlertCircle,
  RotateCcw
} from "lucide-react";

interface KnowledgeRepositoryProps {
  wells?: WellItem[];
  activeWellId?: string;
  onBackToDashboard?: () => void;
  onOpenWellIntelligence?: (wellId: string) => void;
  onOpenEventDetail?: (event: HistoricalEventEpisode) => void;
}

export const KnowledgeRepository: React.FC<KnowledgeRepositoryProps> = ({
  wells = [],
  onBackToDashboard,
  onOpenWellIntelligence,
  onOpenEventDetail,
}) => {
  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedWell, setSelectedWell] = useState<string>("ALL");
  const [selectedEventType, setSelectedEventType] = useState<string>("ALL");
  const [selectedDomain, setSelectedDomain] = useState<string>("ALL");
  const [selectedDocumentSource, setSelectedDocumentSource] = useState<string>("ALL");
  const [minMd, setMinMd] = useState<string>("");
  const [maxMd, setMaxMd] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("depth_asc");

  // API State
  const [searchResponse, setSearchResponse] = useState<KnowledgeSearchResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Event Detail Modal State
  const [selectedEventModal, setSelectedEventModal] = useState<HistoricalEventEpisode | null>(null);

  // Known event taxonomy list
  const eventTaxonomyList = [
    "Tight Hole",
    "Equipment Failure",
    "Pack-off",
    "FORMATION_MUD_LOSS",
    "Stuck Pipe",
    "CEMENTING/OPERATIONAL_LOSS",
    "Cementing Problem",
    "Kick",
    "Fishing"
  ];

  const domainTaxonomyList = [
    "DRILLING_OPERATIONS",
    "WELLBORE_STABILITY",
    "EQUIPMENT_RELIABILITY",
    "FORMATION_FLUIDS"
  ];

  // Execute Search
  const handleExecuteSearch = useCallback(() => {
    setLoading(true);
    setError(null);

    searchKnowledgeRepository({
      q: searchQuery.trim() || undefined,
      well_id: selectedWell !== "ALL" ? selectedWell : undefined,
      event_type: selectedEventType !== "ALL" ? selectedEventType : undefined,
      domain: selectedDomain !== "ALL" ? selectedDomain : undefined,
      document_source: selectedDocumentSource !== "ALL" ? selectedDocumentSource : undefined,
      min_md: minMd ? Number(minMd) : undefined,
      max_md: maxMd ? Number(maxMd) : undefined,
      sort_by: sortBy,
      limit: 100,
    })
      .then((res) => {
        if (res) {
          setSearchResponse(res);
        } else {
          setError("Unable to search historical knowledge repository.");
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Error connecting to search backend.");
        setLoading(false);
      });
  }, [searchQuery, selectedWell, selectedEventType, selectedDomain, selectedDocumentSource, minMd, maxMd, sortBy]);


  // Initial load search (load all events by default)
  useEffect(() => {
    handleExecuteSearch();
  }, []);

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedWell("ALL");
    setSelectedEventType("ALL");
    setMinMd("");
    setMaxMd("");
    setSortBy("depth_asc");
  };

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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans pb-16 selection:bg-blue-500 selection:text-white">
      {/* Top Navigation Banner */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 sticky top-0 z-50 shadow-xl">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBackToDashboard}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 px-3.5 py-1.5 rounded-lg border border-slate-700 font-mono text-xs font-bold transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Telemetry & Map
            </button>

            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-lg font-bold tracking-tight text-white font-mono flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-400" />
                  HISTORICAL DRILLING KNOWLEDGE REPOSITORY
                </h1>
                <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-mono">
                  VERIFIED EQUINOR VOLVE DDR RECORDS
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Search verified Daily Drilling Report (DDR) event episodes, onset depths, evidence text, mitigations & resolutions.
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Search Bar Box */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleExecuteSearch();
            }}
            className="flex flex-col md:flex-row gap-3"
          >
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-slate-400 absolute left-3.5 top-3.5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search mud loss, tight hole, well ID (15/9-F-14), depth (2883), report code (STAT_26)..."
                className="w-full bg-slate-950 text-white font-mono text-sm pl-11 pr-4 py-3 rounded-xl border border-slate-800 focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-3 text-slate-500 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-500 text-white font-mono font-bold text-xs px-6 py-3 rounded-xl border border-blue-400/40 shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2"
            >
              <Search className="w-4 h-4" />
              SEARCH KNOWLEDGE
            </button>
          </form>

          {/* Filter Toolbar */}
          <div className="pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-slate-400 font-bold">
                <Filter className="w-3.5 h-3.5 text-emerald-400" />
                Filters:
              </div>

              {/* Well Filter */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Well:</span>
                <select
                  value={selectedWell}
                  onChange={(e) => setSelectedWell(e.target.value)}
                  className="bg-slate-900 text-white font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
                >
                  <option value="ALL">All Volve Wells</option>
                  {wells.map((w) => (
                    <option key={w.well_id} value={w.well_id}>
                      {w.well_id}
                    </option>
                  ))}
                  <option value="15/9-19 A">15/9-19 A</option>
                  <option value="15/9-19 S">15/9-19 S</option>
                </select>
              </div>

              {/* Event Type Filter */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Event Type:</span>
                <select
                  value={selectedEventType}
                  onChange={(e) => setSelectedEventType(e.target.value)}
                  className="bg-slate-900 text-white font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
                >
                  <option value="ALL">All Event Types</option>
                  {eventTaxonomyList.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              {/* Domain Filter */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Domain:</span>
                <select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  className="bg-slate-900 text-white font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
                >
                  <option value="ALL">All Domains</option>
                  {domainTaxonomyList.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>

              {/* Document Source Filter */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Source:</span>
                <select
                  value={selectedDocumentSource}
                  onChange={(e) => setSelectedDocumentSource(e.target.value)}
                  className="bg-slate-900 text-white font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
                >
                  <option value="ALL">All Sources</option>
                  <option value="DDR">Volve DDR Reports</option>
                  <option value="PDF">Ingested PDFs</option>
                  <option value="TXT">Shift Logs</option>
                </select>
              </div>


              {/* Depth Range Filter */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Min MD:</span>
                <input
                  type="number"
                  placeholder="0"
                  value={minMd}
                  onChange={(e) => setMinMd(e.target.value)}
                  className="w-16 bg-slate-900 text-white text-xs font-mono px-1.5 py-0.5 rounded border border-slate-700 focus:outline-none"
                />
                <span className="text-slate-400">m — Max MD:</span>
                <input
                  type="number"
                  placeholder="5000"
                  value={maxMd}
                  onChange={(e) => setMaxMd(e.target.value)}
                  className="w-16 bg-slate-900 text-white text-xs font-mono px-1.5 py-0.5 rounded border border-slate-700 focus:outline-none"
                />
                <span className="text-slate-400">m</span>
              </div>

              {/* Sort Order */}
              <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
                <span className="text-slate-400">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-slate-900 text-white font-mono text-xs px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
                >
                  <option value="depth_asc">Depth (Ascending)</option>
                  <option value="depth_desc">Depth (Descending)</option>
                  <option value="newest">Timestamp (Newest)</option>
                  <option value="oldest">Timestamp (Oldest)</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleResetFilters}
                className="text-slate-400 hover:text-slate-200 flex items-center gap-1 text-xs font-mono"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset Filters
              </button>
            </div>
          </div>
        </div>

        {/* Results Header Count */}
        <div className="flex items-center justify-between font-mono text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-200 uppercase tracking-wider">
              {loading
                ? "Searching Equinor Volve DDR records..."
                : error
                ? "Search Error"
                : searchResponse
                ? `${searchResponse.total_count} verified historical records found`
                : "Search Repository"}
            </span>
            {searchQuery && (
              <span className="bg-slate-900 px-2 py-0.5 rounded text-blue-400 border border-slate-800">
                q: "{searchQuery}"
              </span>
            )}
          </div>

          <span className="text-slate-400 flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            100% Deterministic Search (No LLM Generative Claims)
          </span>
        </div>

        {/* Loading Indicator */}
        {loading && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center font-mono text-xs text-slate-400 animate-pulse space-y-2">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
            <div>Querying verified Volve DDR event dataset...</div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-6 text-rose-300 text-xs font-mono flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Results Grid */}
        {!loading && !error && searchResponse && searchResponse.results.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {searchResponse.results.map((ev, idx) => (
              <div
                key={ev.event_episode_id || idx}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2.5 py-1 rounded font-mono font-bold border ${getEventBadgeStyle(
                          ev.event_type
                        )}`}
                      >
                        {ev.event_type}
                      </span>
                      <button
                        onClick={() => onOpenWellIntelligence && onOpenWellIntelligence(ev.well_id.replace("NO ", ""))}
                        className="text-xs font-mono font-bold text-emerald-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 hover:border-emerald-500/50 transition-all flex items-center gap-1"
                      >
                        <MapPin className="w-3 h-3" />
                        {ev.well_id}
                      </button>
                    </div>

                    <span className="text-xs font-mono font-bold text-amber-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      MD: {ev.onset_md.toFixed(1)} m
                    </span>
                  </div>

                  {/* Primary Evidence Excerpt */}
                  <div className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-950/60 p-3 rounded-lg border border-slate-850">
                    <strong className="text-slate-400 font-mono uppercase text-[10px] block mb-1">
                      Verified DDR Evidence:
                    </strong>
                    {ev.primary_evidence}
                  </div>

                  {/* Mitigation & Resolution */}
                  <div className="space-y-1.5 text-xs font-sans">
                    {ev.mitigation_text && ev.mitigation_text !== "None recorded" && (
                      <div className="bg-amber-950/20 border border-amber-500/20 p-2 rounded text-amber-200/90 text-[11px]">
                        <strong className="text-amber-400 font-mono text-[10px] block">
                          Mitigation:
                        </strong>
                        {ev.mitigation_text}
                      </div>
                    )}

                    {ev.resolution_text && ev.resolution_text !== "None recorded" && (
                      <div className="bg-emerald-950/20 border border-emerald-500/20 p-2 rounded text-emerald-200/90 text-[11px]">
                        <strong className="text-emerald-400 font-mono text-[10px] block">
                          Resolution:
                        </strong>
                        {ev.resolution_text}
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Footer & Action Buttons */}
                <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono mt-2">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <FileText className="w-3.5 h-3.5 text-blue-400" />
                    <span>{ev.source_label}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onOpenWellIntelligence && onOpenWellIntelligence(ev.well_id.replace("NO ", ""))}
                      className="text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-all text-[10px]"
                    >
                      View Well ➔
                    </button>
                      <button
                        onClick={() => {
                          if (onOpenEventDetail) {
                            onOpenEventDetail(ev);
                          } else {
                            setSelectedEventModal(ev);
                          }
                        }}
                        className="text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1 bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-500/30 transition-all"
                      >
                        View Event Details →
                      </button>
                    </div>
                  </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty Search State */}
        {!loading && !error && searchResponse && searchResponse.results.length === 0 && (
          <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/40 text-slate-400 text-xs font-mono space-y-2">
            <Search className="w-8 h-8 text-slate-600 mx-auto" />
            <div className="text-slate-300 font-bold">No historical records found matching query.</div>
            <div>Try adjusting your keywords, well filters, or depth range criteria.</div>
          </div>
        )}
      </main>

      {/* Step 2 Shared Event Detail Modal */}
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
                Verified DDR Event Evidence
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
                  Verified Primary DDR Activity Report:
                </span>
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-850 text-slate-200 leading-relaxed font-sans text-xs font-medium">
                  {selectedEventModal.primary_evidence}
                </div>
              </div>

              {selectedEventModal.mitigation_text && selectedEventModal.mitigation_text !== "None recorded" && (
                <div className="space-y-1">
                  <span className="font-bold text-amber-400 uppercase text-[11px]">
                    Recorded Mitigation Action:
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
