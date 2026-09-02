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
    setSelectedDomain("ALL");
    setSelectedDocumentSource("ALL");
    setMinMd("");
    setMaxMd("");
    setSortBy("depth_asc");
  };

  const getEventBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case "Equipment Failure":
        return "bg-[#1A1105] text-[#FF8C00] border-[#FF7A00]/40";
      case "Stuck Pipe":
      case "Kick":
        return "bg-[#15101A] text-[#C48CFF] border-[#9333EA]/40";
      case "FORMATION_MUD_LOSS":
      case "CEMENTING/OPERATIONAL_LOSS":
      case "Cementing Problem":
        return "bg-[#1A1410] text-[#E0B084] border-[#8C6239]/40";
      case "Tight Hole":
      case "Pack-off":
      case "Fishing":
        return "bg-[#181308] text-[#FBBF24] border-[#D97706]/40";
      default:
        return "bg-[#111] text-[#9A9A9A] border-[#333]";
    }
  };

  // Shared Styles
  const glassPanelStyle = {
    background: "linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,122,0,0.018) 40%, rgba(22, 22, 22, 0.55))",
    backdropFilter: "blur(18px) saturate(120%)",
    WebkitBackdropFilter: "blur(18px) saturate(120%)",
    border: "1px solid rgba(255, 122, 0, 0.28)",
    boxShadow: "0 10px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.035)",
  };

  const glassCardStyle = {
    background: "linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,122,0,0.018) 40%, rgba(22, 22, 22, 0.55))",
    backdropFilter: "blur(18px) saturate(120%)",
    WebkitBackdropFilter: "blur(18px) saturate(120%)",
    border: "1px solid rgba(255, 122, 0, 0.28)",
    borderRadius: "14px",
    boxShadow: "0 5px 25px rgba(0,0,0,0.35)",
    transition: "transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease, background 200ms ease",
  };

  const evidencePanelStyle = {
    background: "rgba(5, 6, 7, 0.50)",
    border: "1px solid rgba(255, 122, 0, 0.20)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    borderRadius: "10px",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.02)",
  };

  const inputStyle = {
    background: "rgba(8, 9, 10, 0.65)",
    backdropFilter: "blur(10px)",
    WebkitBackdropFilter: "blur(10px)",
    border: "1px solid rgba(255, 122, 0, 0.20)",
    color: "#F2F2F2",
    transition: "all 150ms ease"
  };

  return (
    <div 
      className="min-h-screen text-[#F2F2F2] pb-24 relative overflow-hidden"
      style={{ 
        backgroundColor: "#050607", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-network-orange.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        fontFamily: "'Space Grotesk', 'Inter', sans-serif" 
      }}
    >
      {/* Subtle Ambient Glows */}
      <div className="absolute top-[-10%] left-[-5%] w-[40%] h-[40%] rounded-full opacity-[0.08] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>
      <div className="absolute top-[30%] right-[-10%] w-[50%] h-[50%] rounded-full opacity-[0.06] blur-[180px] pointer-events-none" style={{ background: "radial-gradient(circle, #FFA000 0%, transparent 70%)" }}></div>

      <div className="relative z-10">
        {/* Top Navigation Banner */}
        <header 
          className="px-[24px] py-[16px] sticky top-0 z-50 flex flex-col md:flex-row md:items-center gap-4"
          style={{ ...glassPanelStyle, borderTop: "none", borderLeft: "none", borderRight: "none" }}
        >
          <div className="max-w-[1500px] w-full mx-auto flex flex-col md:flex-row md:items-center gap-6">
            <button
              onClick={onBackToDashboard}
              className="flex items-center gap-2 px-[14px] py-[8px] rounded-[8px] text-[13px] font-[500] transition-all group shrink-0"
              style={{
                background: "rgba(18, 18, 18, 0.8)",
                border: "1px solid rgba(255, 122, 0, 0.3)",
                color: "#F2F2F2"
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "#FF7A00";
                e.currentTarget.style.boxShadow = "0 0 16px rgba(255,122,0,0.15)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.3)";
                e.currentTarget.style.boxShadow = "none";
                e.currentTarget.style.transform = "none";
              }}
            >
              <ArrowLeft className="w-4 h-4 text-[#FF7A00] group-hover:brightness-125" />
              <span className="group-hover:text-white">Back to Telemetry & Map</span>
            </button>

            <div>
              <div className="flex items-center gap-3">
                <Database className="w-5 h-5 text-[#FF7A00]" />
                <h1 className="text-[18px] font-[700] tracking-tight text-white uppercase">
                  HISTORICAL DRILLING KNOWLEDGE REPOSITORY
                </h1>
                <span 
                  className="text-[10px] px-[8px] py-[2px] rounded-[4px] uppercase tracking-wider font-mono font-[600]"
                  style={{ background: "rgba(255,122,0,0.1)", color: "#FF8C00", border: "1px solid rgba(255,122,0,0.3)" }}
                >
                  VERIFIED EQUINOR VOLVE DDR RECORDS
                </span>
              </div>
              <p className="text-[13px] text-[#9A9A9A] mt-1 font-['Inter',sans-serif]">
                Search verified Daily Drilling Report (DDR) event episodes, onset depths, evidence text, mitigations & resolutions.
              </p>
            </div>
          </div>
        </header>

        <main className="max-w-[1500px] mx-auto px-[24px] pt-[24px] space-y-[24px]">
          
          {/* Search & Filter Container */}
          <div 
            className="rounded-[16px] p-[20px] space-y-[16px]"
            style={glassPanelStyle}
          >
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleExecuteSearch();
              }}
              className="flex flex-col md:flex-row gap-[12px]"
            >
              <div className="relative flex-1 group">
                <Search className="w-5 h-5 text-[#FF7A00] absolute left-4 top-[14px] group-focus-within:brightness-125" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search mud loss, tight hole, well ID (15/9-F-14), depth (2883), report code (STAT_26)..."
                  className="w-full text-[#F2F2F2] text-[14px] pl-[44px] pr-[16px] py-[12px] rounded-[10px] focus:outline-none placeholder:text-[#686868]"
                  style={{ ...inputStyle, fontFamily: "'Inter', sans-serif" }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "rgba(255, 122, 0, 0.75)";
                    e.target.style.boxShadow = "0 0 14px rgba(255, 122, 0, 0.12)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255, 122, 0, 0.20)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-4 top-[14px] text-[#9A9A9A] hover:text-white transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>

              <button
                type="submit"
                className="text-white font-[600] text-[13px] px-[24px] py-[12px] rounded-[10px] flex items-center justify-center gap-2 uppercase tracking-wide group"
                style={{
                  background: "rgba(15, 15, 15, 0.65)",
                  border: "1px solid rgba(255, 122, 0, 0.55)",
                  transition: "all 180ms ease"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255, 122, 0, 0.12)";
                  e.currentTarget.style.borderColor = "#FF7A00";
                  e.currentTarget.style.boxShadow = "0 0 25px rgba(255,122,0,0.30)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(15, 15, 15, 0.65)";
                  e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.55)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.transform = "none";
                }}
                onMouseDown={(e) => {
                  e.currentTarget.style.boxShadow = "0 0 35px rgba(255,122,0,0.45)";
                }}
              >
                <Search className="w-4 h-4 text-[#FF7A00] group-hover:brightness-125" />
                SEARCH KNOWLEDGE
              </button>
            </form>

            {/* Filters */}
            <div 
              className="pt-[16px] flex flex-wrap items-center justify-between gap-4 text-[13px] font-['Inter',sans-serif]"
              style={{ borderTop: "1px solid rgba(255, 122, 0, 0.15)" }}
            >
              <div className="flex flex-wrap items-center gap-[12px]">
                <div className="flex items-center gap-1.5 text-[#FF7A00] font-[600]">
                  <Filter className="w-4 h-4" />
                  Filters:
                </div>

                {/* Well Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Well:</span>
                  <select
                    value={selectedWell}
                    onChange={(e) => setSelectedWell(e.target.value)}
                    className="px-2 py-1.5 rounded-[6px] focus:outline-none cursor-pointer appearance-none pr-8"
                    style={{ ...inputStyle, backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FF7A00%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 8px top 50%", backgroundSize: "10px auto" }}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
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
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Event Type:</span>
                  <select
                    value={selectedEventType}
                    onChange={(e) => setSelectedEventType(e.target.value)}
                    className="px-2 py-1.5 rounded-[6px] focus:outline-none cursor-pointer appearance-none pr-8"
                    style={{ ...inputStyle, backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FF7A00%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 8px top 50%", backgroundSize: "10px auto" }}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
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
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Domain:</span>
                  <select
                    value={selectedDomain}
                    onChange={(e) => setSelectedDomain(e.target.value)}
                    className="px-2 py-1.5 rounded-[6px] focus:outline-none cursor-pointer appearance-none pr-8"
                    style={{ ...inputStyle, backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FF7A00%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 8px top 50%", backgroundSize: "10px auto" }}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
                  >
                    <option value="ALL">All Domains</option>
                    {domainTaxonomyList.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Source Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Source:</span>
                  <select
                    value={selectedDocumentSource}
                    onChange={(e) => setSelectedDocumentSource(e.target.value)}
                    className="px-2 py-1.5 rounded-[6px] focus:outline-none cursor-pointer appearance-none pr-8"
                    style={{ ...inputStyle, backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FF7A00%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 8px top 50%", backgroundSize: "10px auto" }}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
                  >
                    <option value="ALL">All Sources</option>
                    <option value="DDR">Volve DDR Reports</option>
                    <option value="PDF">Ingested PDFs</option>
                    <option value="TXT">Shift Logs</option>
                  </select>
                </div>

                {/* Depth Range Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Min MD:</span>
                  <input
                    type="number"
                    placeholder="0"
                    value={minMd}
                    onChange={(e) => setMinMd(e.target.value)}
                    className="w-[60px] px-2 py-1.5 rounded-[6px] focus:outline-none text-center font-mono"
                    style={inputStyle}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
                  />
                  <span className="text-[#9A9A9A]">m &nbsp;&nbsp;-&nbsp;&nbsp; Max MD:</span>
                  <input
                    type="number"
                    placeholder="5000"
                    value={maxMd}
                    onChange={(e) => setMaxMd(e.target.value)}
                    className="w-[68px] px-2 py-1.5 rounded-[6px] focus:outline-none text-center font-mono"
                    style={inputStyle}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
                  />
                  <span className="text-[#9A9A9A]">m</span>
                </div>

                {/* Sort Order */}
                <div className="flex items-center gap-2">
                  <span className="text-[#9A9A9A]">Sort:</span>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-2 py-1.5 rounded-[6px] focus:outline-none cursor-pointer appearance-none pr-8"
                    style={{ ...inputStyle, backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23FF7A00%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 8px top 50%", backgroundSize: "10px auto" }}
                    onFocus={(e) => { e.target.style.borderColor = "#FF7A00"; e.target.style.boxShadow = "0 0 12px rgba(255,122,0,0.15)"; }}
                    onBlur={(e) => { e.target.style.borderColor = "rgba(255, 122, 0, 0.20)"; e.target.style.boxShadow = "none"; }}
                  >
                    <option value="depth_asc">Depth (Ascending)</option>
                    <option value="depth_desc">Depth (Descending)</option>
                    <option value="newest">Timestamp (Newest)</option>
                    <option value="oldest">Timestamp (Oldest)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center">
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="text-[#FF7A00] flex items-center gap-1.5 text-[13px] font-[600]"
                  style={{ transition: "all 180ms ease" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = "#FF8C00";
                    e.currentTarget.style.textShadow = "0 0 10px rgba(255,122,0,0.5)";
                    e.currentTarget.style.transform = "translateY(-1px)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = "#FF7A00";
                    e.currentTarget.style.textShadow = "none";
                    e.currentTarget.style.transform = "none";
                  }}
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset Filters
                </button>
              </div>
            </div>
          </div>

          {/* Results Header Count */}
          <div className="flex items-center justify-between text-[13px] px-[8px]">
            <div className="flex items-center gap-3">
              <Database className="w-4 h-4 text-[#FF7A00]" />
              <span className="font-[700] text-white uppercase tracking-wider">
                {loading
                  ? "SEARCHING EQUINOR VOLVE DDR RECORDS..."
                  : error
                  ? "SEARCH ERROR"
                  : searchResponse
                  ? `${searchResponse.total_count} VERIFIED HISTORICAL RECORDS FOUND`
                  : "SEARCH REPOSITORY"}
              </span>
            </div>

            <span className="text-[#9A9A9A] flex items-center gap-2 font-['Inter',sans-serif]">
              <Shield className="w-4 h-4 text-[#FF7A00]" />
              <strong className="text-[#FF7A00]">100%</strong> Deterministic Search (No LLM Generative Claims)
            </span>
          </div>

          {/* Loading Indicator */}
          {loading && (
            <div 
              className="rounded-[16px] p-[60px] text-center text-[#9A9A9A] animate-pulse flex flex-col items-center justify-center space-y-4"
              style={glassPanelStyle}
            >
              <div className="w-10 h-10 border-[3px] border-[#FF7A00] border-t-transparent rounded-full animate-spin"></div>
              <div className="text-[14px] uppercase tracking-widest font-[600]">Querying verified Volve DDR event dataset...</div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div 
              className="rounded-[16px] p-[24px] text-red-300 flex items-center gap-4"
              style={{ background: "rgba(255,0,0,0.05)", border: "1px solid rgba(255,0,0,0.2)", backdropFilter: "blur(10px)" }}
            >
              <AlertCircle className="w-6 h-6 text-red-500 shrink-0" />
              <span className="text-[14px] font-[500] uppercase tracking-wide">{error}</span>
            </div>
          )}

          {/* Results Grid - 3 Columns */}
          {!loading && !error && searchResponse && searchResponse.results.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[18px]">
              {searchResponse.results.map((ev, idx) => (
                <div
                  key={ev.event_episode_id || idx}
                  className="p-[16px] flex flex-col justify-between group"
                  style={glassCardStyle}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-4px)";
                    e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.70)";
                    e.currentTarget.style.boxShadow = "0 12px 35px rgba(255,122,0,0.12), 0 0 22px rgba(255,122,0,0.10)";
                    e.currentTarget.style.background = "rgba(28, 24, 20, 0.68)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "none";
                    e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.28)";
                    e.currentTarget.style.boxShadow = "0 5px 25px rgba(0,0,0,0.35)";
                    e.currentTarget.style.background = "linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,122,0,0.018) 40%, rgba(22, 22, 22, 0.55))";
                  }}
                >
                  <div className="space-y-[16px]">
                    {/* Card Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[11px] px-[8px] py-[4px] rounded-[6px] font-[600] tracking-wide border ${getEventBadgeStyle(
                            ev.event_type
                          )}`}
                        >
                          {ev.event_type}
                        </span>
                        <div 
                          className="flex items-center gap-1.5 px-[8px] py-[4px] rounded-[6px] text-[11px] font-mono font-[600] text-[#9A9A9A]"
                          style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.05)" }}
                        >
                          <MapPin className="w-3 h-3 text-[#FF7A00]" />
                          {ev.well_id}
                        </div>
                      </div>

                      <span className="text-[12px] font-mono font-[700] text-[#FF7A00]">
                        MD: {ev.onset_md.toFixed(1)} m
                      </span>
                    </div>

                    {/* Primary Evidence Excerpt */}
                    <div 
                      className="p-[14px] flex flex-col gap-[8px]"
                      style={evidencePanelStyle}
                    >
                      <strong className="text-[#FF7A00] font-[600] uppercase text-[10px] tracking-wider">
                        Verified DDR Evidence:
                      </strong>
                      <p className="text-[#E0E0E0] text-[13px] font-['Inter',sans-serif] leading-[1.6]">
                        {ev.primary_evidence}
                      </p>
                    </div>

                    {/* Mitigation & Resolution */}
                    <div className="space-y-2 font-['Inter',sans-serif]">
                      {ev.mitigation_text && ev.mitigation_text !== "None recorded" && (
                        <div className="text-[12px] text-[#9A9A9A]">
                          <strong className="text-[#B85E00] uppercase text-[10px] tracking-wider block mb-0.5">Mitigation:</strong>
                          <span className="line-clamp-2">{ev.mitigation_text}</span>
                        </div>
                      )}

                      {ev.resolution_text && ev.resolution_text !== "None recorded" && (
                        <div className="text-[12px] text-[#9A9A9A]">
                          <strong className="text-[#6B8E23] uppercase text-[10px] tracking-wider block mb-0.5">Resolution:</strong>
                          <span className="line-clamp-2">{ev.resolution_text}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Footer & Action Buttons */}
                  <div className="pt-[16px] mt-[16px] flex flex-col xl:flex-row xl:items-center justify-between gap-4" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                    <div className="flex items-center gap-2 text-[11px] text-[#686868] font-[500]">
                      <FileText className="w-4 h-4 text-[#FF7A00]" />
                      <span>{ev.source_label}</span>
                    </div>

                    <div className="flex items-center gap-[8px]">
                      <button
                        onClick={() => onOpenWellIntelligence && onOpenWellIntelligence(ev.well_id.replace("NO ", ""))}
                        className="px-[12px] py-[6px] rounded-[6px] text-[11px] font-[500] text-[#9A9A9A]"
                        style={{
                          background: "rgba(10, 10, 10, 0.6)",
                          border: "1px solid rgba(255,255,255,0.1)",
                          transition: "all 180ms ease"
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.5)";
                          e.currentTarget.style.boxShadow = "0 0 10px rgba(255,122,0,0.1)";
                          e.currentTarget.style.color = "#FFF";
                          e.currentTarget.style.background = "rgba(20, 20, 20, 0.8)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                          e.currentTarget.style.boxShadow = "none";
                          e.currentTarget.style.color = "#9A9A9A";
                          e.currentTarget.style.background = "rgba(10, 10, 10, 0.6)";
                        }}
                      >
                        View Well &rarr;
                      </button>
                      <button
                        onClick={() => {
                          if (onOpenEventDetail) {
                            onOpenEventDetail(ev);
                          } else {
                            setSelectedEventModal(ev);
                          }
                        }}
                        className="px-[12px] py-[6px] rounded-[6px] text-[11px] font-[600] text-[#FF7A00] group-btn"
                        style={{
                          background: "rgba(10, 10, 10, 0.8)",
                          border: "1px solid rgba(255, 122, 0, 0.4)",
                          transition: "all 180ms ease"
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#FF8C00";
                          e.currentTarget.style.boxShadow = "0 0 20px rgba(255,122,0,0.25)";
                          e.currentTarget.style.color = "#FFF";
                          e.currentTarget.style.transform = "translateY(-2px)";
                          e.currentTarget.style.background = "rgba(255,122,0,0.08)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.4)";
                          e.currentTarget.style.boxShadow = "none";
                          e.currentTarget.style.color = "#FF7A00";
                          e.currentTarget.style.transform = "none";
                          e.currentTarget.style.background = "rgba(10, 10, 10, 0.8)";
                        }}
                      >
                        View Event Details &rarr;
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty Search State */}
          {!loading && !error && searchResponse && searchResponse.results.length === 0 && (
            <div 
              className="py-[80px] flex flex-col items-center justify-center text-center rounded-[16px]"
              style={{ ...glassPanelStyle, borderStyle: "dashed" }}
            >
              <Search className="w-10 h-10 text-[#686868] mb-4" />
              <div className="text-[16px] text-[#F2F2F2] font-[600] mb-2">No historical records found matching query.</div>
              <div className="text-[13px] text-[#9A9A9A]">Try adjusting your keywords, well filters, or depth range criteria.</div>
            </div>
          )}
        </main>

        {/* Event Detail Modal */}
        {selectedEventModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
            <div 
              className="w-full max-w-3xl p-[24px] relative"
              style={{
                background: "rgba(15, 15, 15, 0.75)",
                backdropFilter: "blur(24px)",
                WebkitBackdropFilter: "blur(24px)",
                border: "1px solid rgba(255, 122, 0, 0.3)",
                borderRadius: "16px",
                boxShadow: "0 20px 50px rgba(0,0,0,0.6), inset 0 0 40px rgba(255,122,0,0.05)"
              }}
            >
              <button
                onClick={() => setSelectedEventModal(null)}
                className="absolute top-[20px] right-[20px] text-[#9A9A9A] hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>

              <div className="flex items-center gap-3 border-b border-[rgba(255,122,0,0.15)] pb-[16px] mb-[20px]">
                <span
                  className={`text-[12px] px-[10px] py-[4px] rounded-[6px] font-[600] tracking-wide border ${getEventBadgeStyle(
                    selectedEventModal.event_type
                  )}`}
                >
                  {selectedEventModal.event_type}
                </span>
                <h3 className="text-[18px] font-[700] text-white uppercase tracking-wide">
                  Verified DDR Event Evidence
                </h3>
              </div>

              <div className="space-y-[20px]">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-[16px] p-[16px] rounded-[12px]" style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Wellbore</span>
                    <strong className="text-[#F2F2F2] font-mono text-[13px]">{selectedEventModal.wellbore_id}</strong>
                  </div>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Onset Depth (MD)</span>
                    <strong className="text-[#FF7A00] font-mono text-[13px]">{selectedEventModal.onset_md.toFixed(1)} m</strong>
                  </div>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Onset TVD</span>
                    <strong className="text-[#F2F2F2] font-mono text-[13px]">
                      {selectedEventModal.onset_tvd ? `${selectedEventModal.onset_tvd.toFixed(1)} m` : "N/A"}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Timestamp</span>
                    <strong className="text-[#F2F2F2] font-mono text-[13px]">{selectedEventModal.onset_timestamp}</strong>
                  </div>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Event Domain</span>
                    <strong className="text-[#F2F2F2] text-[13px]">{selectedEventModal.event_domain}</strong>
                  </div>
                  <div>
                    <span className="text-[#686868] block text-[10px] uppercase font-[600] tracking-wider mb-1">Source Record</span>
                    <strong className="text-[#FF7A00] font-mono text-[13px]">{selectedEventModal.primary_source_record}</strong>
                  </div>
                </div>

                <div className="space-y-[8px]">
                  <span className="font-[600] text-[#FF7A00] uppercase text-[11px] tracking-wider">
                    Verified Primary DDR Activity Report:
                  </span>
                  <div 
                    className="p-[16px] rounded-[10px] text-[#E0E0E0] leading-[1.6] text-[14px] font-['Inter',sans-serif]"
                    style={evidencePanelStyle}
                  >
                    {selectedEventModal.primary_evidence}
                  </div>
                </div>

                {selectedEventModal.mitigation_text && selectedEventModal.mitigation_text !== "None recorded" && (
                  <div className="space-y-[8px]">
                    <span className="font-[600] text-[#B85E00] uppercase text-[11px] tracking-wider">
                      Recorded Mitigation Action:
                    </span>
                    <div className="p-[12px] rounded-[10px] text-[#F2F2F2] text-[13px] font-['Inter',sans-serif]" style={{ background: "rgba(184, 94, 0, 0.1)", border: "1px solid rgba(184, 94, 0, 0.3)" }}>
                      {selectedEventModal.mitigation_text}
                    </div>
                  </div>
                )}

                {selectedEventModal.resolution_text && selectedEventModal.resolution_text !== "None recorded" && (
                  <div className="space-y-[8px]">
                    <span className="font-[600] text-[#6B8E23] uppercase text-[11px] tracking-wider">
                      Recorded Resolution:
                    </span>
                    <div className="p-[12px] rounded-[10px] text-[#F2F2F2] text-[13px] font-['Inter',sans-serif]" style={{ background: "rgba(107, 142, 35, 0.1)", border: "1px solid rgba(107, 142, 35, 0.3)" }}>
                      {selectedEventModal.resolution_text}
                    </div>
                  </div>
                )}

                <div className="pt-[16px] border-t border-[rgba(255,122,0,0.15)] text-[11px] flex items-center justify-between">
                  <span className="text-[#686868]">Dataset: Equinor Volve verified_event_episodes_v2.csv</span>
                  <span className="text-[#FF7A00] font-[600]">100% Verified DDR Record</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
