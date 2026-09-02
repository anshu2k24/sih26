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

  const filteredEvents = useMemo(() => {
    if (!data?.events) return [];
    return data.events.filter((ev) => {
      const matchType = selectedEventType === "ALL" || ev.event_type === selectedEventType;
      const matchDepth = ev.onset_md >= minMdFilter && ev.onset_md <= maxMdFilter;
      return matchType && matchDepth;
    });
  }, [data, selectedEventType, minMdFilter, maxMdFilter]);

  const getEventBadgeStyle = (eventType: string) => {
    switch (eventType) {
      case "FORMATION_MUD_LOSS":
      case "CEMENTING/OPERATIONAL_LOSS":
        return { color: "#FF5E5E", background: "rgba(255,94,94,0.05)", border: "1px solid rgba(255,94,94,0.3)" };
      case "Tight Hole":
      case "Pack-off":
        return { color: "#FF9A3D", background: "rgba(255,154,61,0.05)", border: "1px solid rgba(255,154,61,0.3)" };
      case "Stuck Pipe":
      case "Kick":
        return { color: "#D946EF", background: "rgba(217,70,239,0.05)", border: "1px solid rgba(217,70,239,0.3)" };
      case "Equipment Failure":
      default:
        return { color: "#F5F5F5", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.15)" };
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

  // Premium Glass Styles
  const glassPanelStyle = {
    background: "rgba(15, 15, 15, 0.35)",
    backdropFilter: "blur(24px)",
    WebkitBackdropFilter: "blur(24px)",
    border: "1px solid rgba(255, 122, 0, 0.25)",
    borderRadius: "16px",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4), inset 0 0 32px rgba(255,122,0,0.03)",
  };

  const glassCardStyle = {
    background: "rgba(20, 20, 20, 0.25)",
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(255, 122, 0, 0.3)",
    borderRadius: "12px",
    transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  };

  const hoverEffectProps = {
    onMouseEnter: (e: React.MouseEvent<HTMLElement>) => {
      e.currentTarget.style.transform = "translateY(-1px)";
      e.currentTarget.style.border = "1px solid rgba(255,122,0,0.45)";
      e.currentTarget.style.boxShadow = "0 0 20px rgba(255,122,0,0.06)";
      e.currentTarget.style.background = "rgba(25,25,25,0.75)";
    },
    onMouseLeave: (e: React.MouseEvent<HTMLElement>) => {
      e.currentTarget.style.transform = "translateY(0px)";
      e.currentTarget.style.border = "1px solid rgba(255, 122, 0, 0.25)";
      e.currentTarget.style.boxShadow = "none";
      e.currentTarget.style.background = "rgba(20, 20, 20, 0.55)";
    }
  };

  const inputStyle = {
    background: "rgba(10, 10, 10, 0.6)",
    border: "1px solid rgba(255, 122, 0, 0.25)",
    borderRadius: "8px",
    color: "#F2F2F2",
    outline: "none",
    transition: "all 0.2s ease",
  };

  return (
    <div 
      className="min-h-screen text-[#F2F2F2] pb-16 selection:bg-[#FF7A00] selection:text-white relative overflow-hidden"
      style={{ 
        backgroundColor: "#050607", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        fontFamily: "'Space Grotesk', 'Inter', sans-serif" 
      }}
    >
      {/* Ambient Background Glows to enhance glass transparency */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full opacity-[0.15] blur-[120px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full opacity-[0.12] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FFA000 0%, transparent 70%)" }}></div>
      <div className="absolute top-[30%] right-[10%] w-[30%] h-[30%] rounded-full opacity-[0.08] blur-[100px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF5000 0%, transparent 70%)" }}></div>

      <div className="relative z-10">
        {/* 4. TOP BREADCRUMB BAR */}
        <header 
          className="px-6 py-4 sticky top-0 z-50 flex items-center justify-between"
          style={{
            background: "rgba(5, 6, 7, 0.45)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            borderBottom: "1px solid rgba(255, 122, 0, 0.15)",
            height: "60px"
          }}
        >
          <div className="flex items-center text-[13px] text-[#A1A1A1] font-[500]">
            <ArrowLeft className="w-4 h-4 mr-2" />
            <span>Dashboard &nbsp;/&nbsp; Offset Wells &nbsp;/&nbsp; </span>
            <span className="text-[#F2F2F2] font-[700] ml-1 tracking-wider">{offsetWellId}</span>
          </div>
          <div className="flex items-center gap-2 text-[12px] text-[#A1A1A1]">
            <Shield className="w-4 h-4 text-[#FF7A00]" />
            <span>Equinor Volve Verified DDR Profile</span>
          </div>
        </header>

      <main className="max-w-[1400px] mx-auto px-[24px] pt-[20px] space-y-[20px]">
        
        {/* 5. MAIN HEADER / INTELLIGENCE HEADER - Transparent */}
        <div 
          className="flex flex-col xl:flex-row items-center gap-6 py-[10px]"
        >
          {/* 6. BACK BUTTON */}
          <button
            onClick={onBackToMap}
            className="flex items-center justify-center gap-3 shrink-0 cursor-pointer"
            style={{
              width: "260px",
              height: "60px",
              background: "rgba(20,20,20,0.55)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              borderRadius: "14px",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-1px)";
              e.currentTarget.style.border = "1px solid rgba(255,122,0,0.45)";
              e.currentTarget.style.boxShadow = "0 0 20px rgba(255,122,0,0.06)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0px)";
              e.currentTarget.style.border = "1px solid rgba(255, 122, 0, 0.25)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <ArrowLeft className="w-5 h-5 text-[#FF7A00]" />
            <div className="flex flex-col items-start leading-tight">
              <span className="text-[#F2F2F2] font-[600] text-[13px]">Back to Nearby Wells</span>
              <span className="text-[#FF7A00] font-[600] text-[13px]">Map</span>
            </div>
          </button>

          {/* 7. OFFSET WELL INTELLIGENCE TITLE */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex flex-col leading-tight font-[700] text-[20px] tracking-wide">
              <span className="text-[#F2F2F2]">OFFSET WELL</span>
              <span className="text-[#F2F2F2]">INTELLIGENCE:</span>
            </div>
          </div>

          {/* 8. HISTORICAL DDR / NWIS CARD */}
          <div 
            className="flex flex-col justify-center px-[20px] h-[60px]"
            style={{
              background: "rgba(20,20,20,0.55)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              borderRadius: "14px",
              boxShadow: "0 0 20px rgba(255,122,0,0.04)"
            }}
          >
            <span className="text-[#FF7A00] font-[600] text-[12px] tracking-wider uppercase leading-tight">Historical DDR / NWIS</span>
            <span className="text-[#A1A1A1] font-[500] text-[12px] uppercase leading-tight">Intelligence</span>
          </div>

          {/* Spacer */}
          <div className="flex-1"></div>

          {/* 9. ACTIVE OFFSET STATUS */}
          <div 
            className="flex items-center gap-4 px-[20px] h-[60px] whitespace-nowrap"
            style={{
              background: "rgba(20,20,20,0.55)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              borderRadius: "14px"
            }}
          >
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF7A00] shadow-[0_0_8px_#FF7A00]"></span>
              <div className="flex flex-col leading-tight">
                <span className="text-[#FF7A00] font-[600] text-[11px] tracking-wider">ACTIVE: {activeWellId}</span>
                <span className="text-[#A1A1A1] font-mono text-[10px]">({currentMd.toFixed(1)}m)</span>
              </div>
            </div>
            
            <span className="text-[#737373] mx-1">→</span>
            
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-[#FF7A00]" />
              <span className="text-[#FF7A00] font-[600] text-[11px] tracking-wider">OFFSET:</span>
            </div>

            <span className="text-[#737373]">|</span>

            <div className="flex flex-col leading-tight">
              <span className="text-[#F2F2F2] font-[600] text-[11px] tracking-wider">Dist: {formatDistance(data?.distance_km, data?.distance_m)?.split(' ')[0]}</span>
              <span className="text-[#F2F2F2] font-[600] text-[11px] tracking-wider">{formatDistance(data?.distance_km, data?.distance_m)?.split(' ')[1] || ''}</span>
            </div>
          </div>
        </div>

        {loading && (
          <div className="text-center p-12 text-[#A1A1A1] text-[13px] animate-pulse" style={glassPanelStyle}>
            Loading historical DDR offset intelligence for <strong>{offsetWellId}</strong>...
          </div>
        )}

        {error && !loading && (
          <div className="p-6 flex items-center justify-between" style={{ ...glassPanelStyle, borderColor: "rgba(255,0,0,0.3)" }}>
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={onBackToMap} className="px-4 py-2 bg-[#FF7A00] text-black font-bold rounded-lg text-sm">
              Return to Map
            </button>
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* 10. WELL SUMMARY & METADATA */}
            <div style={{ ...glassPanelStyle, padding: "20px" }}>
              <h2 className="text-[14px] font-[600] text-[#F2F2F2] uppercase tracking-wider flex items-center gap-2">
                <Info className="w-4 h-4 text-[#FF7A00]" />
                WELL SUMMARY & METADATA
              </h2>
              <p className="text-[12px] text-[#A1A1A1] mt-1 mb-4">
                Deterministic intelligence extracted from Equinor Volve historical drilling records.
              </p>

              {/* 11. METADATA CARDS */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">WELL ID</span>
                  <span className="text-[#FF7A00] font-[700] text-[16px]">{offsetWellId}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">STATUS</span>
                  <span className="text-[#FF7A00] font-[600] text-[13px] leading-tight">{metadata?.status || "Historical Surface Section"}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">FIELD</span>
                  <span className="text-[#FF7A00] font-[600] text-[16px]">{metadata?.field || "Volve"}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">OPERATOR</span>
                  <span className="text-[#FF7A00] font-[600] text-[16px]">{metadata?.operator || "Equinor"}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">WATER DEPTH</span>
                  <span className="text-[#FF7A00] font-[600] text-[16px]">{metadata?.water_depth_m ? `${metadata.water_depth_m} m` : "84 m"}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">SLOT</span>
                  <span className="text-[#FF7A00] font-[600] text-[16px]">{metadata?.slot_name || "Slot 5"}</span>
                </div>
                <div style={glassCardStyle} className="p-4 flex flex-col" {...hoverEffectProps}>
                  <span className="text-[#737373] text-[10px] font-[600] uppercase tracking-wider mb-1">TOTAL EVENTS</span>
                  <span className="text-[#FF7A00] font-[600] text-[14px] leading-tight">{data.total_events} Verified Episodes</span>
                </div>
              </div>
            </div>

            {/* 12. HISTORICAL EVENT BREAKDOWN */}
            <div className="space-y-4 pt-2">
              <h3 className="text-[13px] font-[600] text-[#F2F2F2] uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#FF7A00]" />
                HISTORICAL EVENT BREAKDOWN ({data.total_events} TOTAL)
              </h3>

              <div className="flex flex-wrap gap-4">
                {availableEventTypes.map((type) => {
                  const count = data.event_counts[type];
                  const isActive = selectedEventType === type;
                  return (
                    <div
                      key={type}
                      onClick={() => setSelectedEventType(isActive ? "ALL" : type)}
                      className="p-4 flex flex-col min-w-[200px] cursor-pointer"
                      style={{
                        ...glassCardStyle,
                        border: isActive ? "1px solid rgba(255,122,0,0.6)" : glassCardStyle.border,
                        boxShadow: isActive ? "0 0 20px rgba(255,122,0,0.1)" : "none",
                      }}
                      onMouseEnter={(e) => { if (!isActive) hoverEffectProps.onMouseEnter(e); }}
                      onMouseLeave={(e) => { if (!isActive) hoverEffectProps.onMouseLeave(e); }}
                    >
                      <span className="text-[#A1A1A1] text-[11px] font-[500] truncate">{type}</span>
                      <span className="text-[#FF7A00] font-[700] text-[18px] mt-1">{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 13. FILTER BAR */}
            <div 
              className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 mt-2"
              style={glassPanelStyle}
            >
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-[#FF7A00]" />
                <span className="font-[600] text-[13px] text-[#F2F2F2]">Filter Events:</span>
              </div>

              <div className="flex flex-wrap items-center gap-6">
                {/* Event Type Filter */}
                <div className="flex items-center gap-3">
                  <span className="text-[#A1A1A1] text-[12px]">Type:</span>
                  <select
                    value={selectedEventType}
                    onChange={(e) => setSelectedEventType(e.target.value)}
                    className="px-3 py-1.5 cursor-pointer appearance-none pr-8"
                    style={{
                      ...inputStyle,
                      backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23F2F2F2%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E")`,
                      backgroundRepeat: "no-repeat",
                      backgroundPosition: "right 10px center",
                    }}
                    onFocus={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.6)"}
                    onBlur={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.25)"}
                  >
                    <option value="ALL" className="bg-[#121212]">All Event Types ({data.total_events})</option>
                    {availableEventTypes.map((t) => (
                      <option key={t} value={t} className="bg-[#121212]">
                        {t} ({data.event_counts[t]})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Depth Range Controls */}
                <div className="flex items-center gap-3">
                  <span className="text-[#A1A1A1] text-[12px]">Min MD:</span>
                  <input
                    type="number"
                    value={minMdFilter}
                    onChange={(e) => setMinMdFilter(Number(e.target.value))}
                    className="w-20 px-2 py-1.5 font-mono text-[12px]"
                    style={inputStyle}
                    onFocus={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.6)"}
                    onBlur={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.25)"}
                  />
                  <span className="text-[#A1A1A1] text-[12px]">m &nbsp;&nbsp;−&nbsp;&nbsp; Max MD:</span>
                  <input
                    type="number"
                    value={maxMdFilter}
                    onChange={(e) => setMaxMdFilter(Number(e.target.value))}
                    className="w-20 px-2 py-1.5 font-mono text-[12px]"
                    style={inputStyle}
                    onFocus={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.6)"}
                    onBlur={(e) => e.currentTarget.style.border = "1px solid rgba(255,122,0,0.25)"}
                  />
                  <span className="text-[#A1A1A1] text-[12px]">m</span>
                </div>

                {/* 14. RESET FILTERS */}
                {(selectedEventType !== "ALL" || minMdFilter > 0 || maxMdFilter < 5000) && (
                  <button
                    onClick={() => {
                      setSelectedEventType("ALL");
                      setMinMdFilter(0);
                      setMaxMdFilter(5000);
                    }}
                    className="text-[13px] text-[#FF7A00] hover:text-[#FF8C00] font-[600] transition-all ml-2"
                    style={{ textShadow: "0 0 10px rgba(255,122,0,0.2)" }}
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>

            {/* 15. LOWER CONTENT — TWO COLUMN LAYOUT */}
            <div className="flex flex-col lg:flex-row gap-6 mt-4">
              
              {/* 16. VERTICAL DEPTH TIMELINE */}
              <div 
                className="w-full lg:w-[34%] p-5 flex flex-col h-[700px]"
                style={glassPanelStyle}
              >
                <div className="pb-4 mb-4" style={{ borderBottom: "1px solid rgba(255,122,0,0.15)" }}>
                  <h3 className="text-[13px] font-[600] text-[#F2F2F2] uppercase tracking-wider flex items-center gap-2">
                    <Clock className="w-4 h-4 text-[#FF7A00]" />
                    VERTICAL DEPTH TIMELINE
                  </h3>
                  <p className="text-[11px] text-[#A1A1A1] mt-1.5">
                    Events plotted chronologically by Measured Depth (MD).
                  </p>
                </div>

                {filteredEvents.length > 0 ? (
                  <div className="relative flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    {/* Orange Vertical Line */}
                    <div className="absolute left-[11px] top-4 bottom-4 w-px bg-gradient-to-b from-[rgba(255,122,0,0.5)] via-[rgba(255,122,0,0.2)] to-transparent"></div>

                    <div className="space-y-6 relative z-10 pl-8 pb-4">
                      {filteredEvents.map((ev, idx) => (
                        <div
                          key={ev.event_episode_id || idx}
                          onClick={() => setSelectedEventModal(ev)}
                          className="relative cursor-pointer group"
                        >
                          {/* Timeline Node */}
                          <div className="absolute -left-[32px] top-[14px] w-[22px] h-[22px] rounded-full border border-[#FF7A00] flex items-center justify-center bg-[#050607] shadow-[0_0_10px_rgba(255,122,0,0.2)] group-hover:shadow-[0_0_15px_rgba(255,122,0,0.4)] transition-all">
                            <div className="w-[8px] h-[8px] rounded-full bg-[#FF7A00]"></div>
                          </div>

                          {/* 17. TIMELINE EVENT CARDS */}
                          <div 
                            className="p-3" 
                            style={glassCardStyle}
                            onMouseEnter={hoverEffectProps.onMouseEnter}
                            onMouseLeave={hoverEffectProps.onMouseLeave}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="font-mono font-[700] text-[#FF7A00] text-[12px]">
                                {ev.onset_md.toFixed(1)} m
                              </span>
                              <span className="text-[#FF7A00] text-[9px] font-mono border border-[rgba(255,122,0,0.3)] bg-[rgba(255,122,0,0.05)] px-1.5 py-0.5 rounded">
                                {ev.primary_source_record}
                              </span>
                            </div>
                            <div className="text-[13px] font-[600] text-[#F2F2F2] mb-1 truncate">
                              {ev.event_type}
                            </div>
                            <div className="text-[11px] text-[#A1A1A1] line-clamp-2 leading-snug">
                              {ev.primary_evidence}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-center p-6 text-[#737373] text-[12px] border border-dashed border-[rgba(255,122,0,0.2)] rounded-lg">
                    No historical events fall within the current depth filter range.
                  </div>
                )}
              </div>

              {/* 18. HISTORICAL DDR EVENTS */}
              <div className="w-full lg:w-[66%] space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-[13px] font-[600] text-[#F2F2F2] uppercase tracking-wider flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#FF7A00]" />
                    HISTORICAL DDR EVENTS ({filteredEvents.length})
                  </h3>
                  <span className="text-[11px] text-[#737373]">
                    Source: Verified Equinor Volve DDR Records
                  </span>
                </div>

                {filteredEvents.length > 0 ? (
                  <div className="space-y-4 max-h-[660px] overflow-y-auto pr-2 custom-scrollbar">
                    {filteredEvents.map((ev, idx) => {
                      const badgeStyle = getEventBadgeStyle(ev.event_type);
                      return (
                        // 19. DDR EVENT CARD
                        <div
                          key={ev.event_episode_id || idx}
                          className="p-5 flex flex-col gap-3"
                          style={glassPanelStyle}
                        >
                          <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid rgba(255,122,0,0.1)" }}>
                            <div className="flex items-center gap-2">
                              {/* 20. EVENT BADGES */}
                              <span 
                                className="text-[12px] font-[600] px-3 py-1 rounded border"
                                style={badgeStyle}
                              >
                                {ev.event_type}
                              </span>
                              <span className="text-[11px] font-mono font-[600] text-[#FF7A00] border border-[rgba(255,122,0,0.25)] px-2 py-1 rounded">
                                MD: {ev.onset_md.toFixed(1)} m
                              </span>
                              {ev.onset_tvd && (
                                <span className="text-[11px] font-mono text-[#A1A1A1] border border-[rgba(255,255,255,0.1)] px-2 py-1 rounded">
                                  TVD: {ev.onset_tvd.toFixed(1)} m
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] font-mono text-[#737373]">
                              {ev.onset_timestamp}
                            </span>
                          </div>

                          {/* 21. PRIMARY EVIDENCE BOX */}
                          <div 
                            className="p-4 rounded-lg flex flex-col gap-1.5"
                            style={{
                              background: "rgba(10,10,10,0.4)",
                              border: "1px solid rgba(255,122,0,0.15)"
                            }}
                          >
                            <span className="text-[#A1A1A1] text-[10px] uppercase font-[600] tracking-wider">
                              PRIMARY EVIDENCE:
                            </span>
                            <span className="text-[#F2F2F2] text-[12px] leading-relaxed">
                              {ev.primary_evidence}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
                            {ev.mitigation_text && ev.mitigation_text !== "None recorded" && (
                              <div className="p-3 rounded-lg border border-[rgba(255,122,0,0.2)] bg-[rgba(255,122,0,0.05)] text-[#F2F2F2]">
                                <span className="text-[#FF7A00] text-[10px] uppercase font-[600] block mb-1">Mitigation Action:</span>
                                {ev.mitigation_text}
                              </div>
                            )}
                            {ev.resolution_text && ev.resolution_text !== "None recorded" && (
                              <div className="p-3 rounded-lg border border-[rgba(255,122,0,0.2)] bg-[rgba(255,122,0,0.05)] text-[#F2F2F2]">
                                <span className="text-[#FF7A00] text-[10px] uppercase font-[600] block mb-1">Resolution / Status:</span>
                                {ev.resolution_text}
                              </div>
                            )}
                          </div>

                          {/* 22. PROVENANCE */}
                          <div className="pt-3 flex items-center justify-between text-[11px] mt-1" style={{ borderTop: "1px solid rgba(255,122,0,0.1)" }}>
                            <div className="flex items-center gap-1.5 text-[#737373]">
                              <Shield className="w-3.5 h-3.5 text-[#FF7A00]" />
                              <span>Source Record:</span>
                              <span className="border border-[rgba(255,122,0,0.3)] text-[#FF7A00] bg-[rgba(255,122,0,0.05)] px-2 py-0.5 rounded font-mono">
                                Equinor Volve DDR ({ev.primary_source_record})
                              </span>
                            </div>

                            <button
                              onClick={() => {
                                if (onOpenEventDetail) onOpenEventDetail(ev);
                                else setSelectedEventModal(ev);
                              }}
                              className="text-[#FF7A00] hover:text-[#FF8C00] font-[600] transition-colors"
                            >
                              View Full Provenance →
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-12 text-center text-[#737373] text-[12px] border border-dashed border-[rgba(255,122,0,0.2)] rounded-xl" style={{ background: "rgba(10,10,10,0.4)" }}>
                    No historical DDR events match the current filter criteria for {offsetWellId}.
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>

      </div>

      {/* EVENT MODAL */}
      {selectedEventModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
          <div 
            className="w-full max-w-2xl p-6 relative"
            style={{
              background: "rgba(15, 15, 15, 0.65)",
              backdropFilter: "blur(30px)",
              WebkitBackdropFilter: "blur(30px)",
              border: "1px solid rgba(255, 122, 0, 0.4)",
              borderRadius: "16px",
              boxShadow: "0 20px 50px rgba(0,0,0,0.6), inset 0 0 40px rgba(255,122,0,0.05)"
            }}
          >
            <button
              onClick={() => setSelectedEventModal(null)}
              className="absolute top-4 right-4 text-[#A1A1A1] hover:text-[#FF7A00] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 pb-4 mb-4" style={{ borderBottom: "1px solid rgba(255,122,0,0.15)" }}>
              <span 
                className="text-[12px] font-[600] px-3 py-1 rounded border"
                style={getEventBadgeStyle(selectedEventModal.event_type)}
              >
                {selectedEventModal.event_type}
              </span>
              <h3 className="text-[16px] font-[700] text-[#F2F2F2]">
                Event Provenance & DDR Evidence Details
              </h3>
            </div>

            <div className="space-y-4">
              <div 
                className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 rounded-lg"
                style={{ background: "rgba(10,10,10,0.5)", border: "1px solid rgba(255,122,0,0.15)" }}
              >
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">WELLBORE</span>
                  <span className="text-[#F2F2F2] font-[600] text-[13px]">{selectedEventModal.wellbore_id}</span>
                </div>
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">ONSET DEPTH (MD)</span>
                  <span className="text-[#FF7A00] font-mono font-[600] text-[13px]">{selectedEventModal.onset_md.toFixed(1)} m</span>
                </div>
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">ONSET TVD</span>
                  <span className="text-[#F2F2F2] font-mono font-[600] text-[13px]">
                    {selectedEventModal.onset_tvd ? `${selectedEventModal.onset_tvd.toFixed(1)} m` : "Data unavailable"}
                  </span>
                </div>
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">TIMESTAMP</span>
                  <span className="text-[#F2F2F2] font-mono text-[12px]">{selectedEventModal.onset_timestamp}</span>
                </div>
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">EVENT DOMAIN</span>
                  <span className="text-[#F2F2F2] text-[12px]">{selectedEventModal.event_domain}</span>
                </div>
                <div>
                  <span className="text-[#737373] text-[10px] uppercase font-[600] block mb-1">SOURCE RECORD</span>
                  <span className="text-[#FF7A00] text-[12px] font-mono">{selectedEventModal.primary_source_record}</span>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <span className="text-[#FF7A00] text-[11px] uppercase font-[600] tracking-wider">
                  Verified Primary DDR Text:
                </span>
                <div 
                  className="p-4 rounded-lg text-[#F2F2F2] text-[13px] leading-relaxed"
                  style={{ background: "rgba(10,10,10,0.5)", border: "1px solid rgba(255,122,0,0.15)" }}
                >
                  {selectedEventModal.primary_evidence}
                </div>
              </div>

              {selectedEventModal.mitigation_text && selectedEventModal.mitigation_text !== "None recorded" && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[#FF7A00] text-[11px] uppercase font-[600] tracking-wider">
                    Recorded Mitigation:
                  </span>
                  <div 
                    className="p-3 rounded-lg text-[#F2F2F2] text-[12px]"
                    style={{ background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.2)" }}
                  >
                    {selectedEventModal.mitigation_text}
                  </div>
                </div>
              )}

              {selectedEventModal.resolution_text && selectedEventModal.resolution_text !== "None recorded" && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[#FF7A00] text-[11px] uppercase font-[600] tracking-wider">
                    Recorded Resolution:
                  </span>
                  <div 
                    className="p-3 rounded-lg text-[#F2F2F2] text-[12px]"
                    style={{ background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.2)" }}
                  >
                    {selectedEventModal.resolution_text}
                  </div>
                </div>
              )}

              <div className="pt-4 flex items-center justify-between text-[10px]" style={{ borderTop: "1px solid rgba(255,122,0,0.1)" }}>
                <span className="text-[#737373]">Dataset: Equinor Volve verified_event_episodes_v2.csv</span>
                <span className="text-[#FF7A00] font-[600]">100% Verified DDR Record</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
