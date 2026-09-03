import React, { useState, useEffect, useRef } from "react";
import type { HistoricalProximityResponse, HistoricalProximityMatch, HistoricalEventEpisode } from "../../types/api";
import { fetchHistoricalProximity } from "../../services/api";
import {
  AlertTriangle,
  MapPin,
  Shield,
  ArrowDown,
  Info
} from "lucide-react";

interface HistoricalProximityPanelProps {
  activeWellId: string;
  currentMd: number;
  onOpenWellIntelligence: (wellId: string) => void;
  onOpenEventDetail: (event: HistoricalEventEpisode) => void;
}

export const HistoricalProximityPanel: React.FC<HistoricalProximityPanelProps> = ({
  activeWellId,
  currentMd,
  onOpenWellIntelligence,
  onOpenEventDetail,
}) => {
  const [radiusKm, setRadiusKm] = useState<number>(5.0);
  const [depthWindowM, setDepthWindowM] = useState<number>(50.0);
  const [data, setData] = useState<HistoricalProximityResponse | null>(null);

  const lastMdRef = useRef<number>(-1);
  const lastWellRef = useRef<string>("");

  useEffect(() => {
    const depth = currentMd > 0 ? currentMd : 1509.1;
    const depthDiff = Math.abs(depth - lastMdRef.current);
    const wellChanged = activeWellId !== lastWellRef.current;

    // Only query on well change, initial mount, or significant depth step (>= 25m)
    if (wellChanged || depthDiff >= 25.0 || lastMdRef.current === -1) {
      lastMdRef.current = depth;
      lastWellRef.current = activeWellId;

      fetchHistoricalProximity(activeWellId, depth, radiusKm, depthWindowM).then((res) => {
        if (res) setData(res);
      });
    }
  }, [activeWellId, currentMd, radiusKm, depthWindowM]);

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

  const matches = data?.matches || [];
  const displayDepth = currentMd > 0 ? currentMd : 1509.1;

  return (
    <div className="bg-[#070B14]/60 backdrop-blur-xl border border-slate-800/60 rounded-2xl p-5 shadow-2xl space-y-5">
      {/* Header & Control Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4 font-mono">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />
              HISTORICAL OFFSET PROXIMITY ALERTS
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-mono">
              DETERMINISTIC DEPTH CORRELATION
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Proactively correlates active drilling depth ({displayDepth.toFixed(1)} m) against historical events in nearby offset wells.
          </p>
        </div>

        {/* Controls: Radius & Depth Window */}
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-slate-400">Search Radius:</span>
            <select
              value={radiusKm}
              onChange={(e) => setRadiusKm(Number(e.target.value))}
              className="bg-slate-900 text-emerald-400 font-bold px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
            >
              <option value={1.0}>1 km</option>
              <option value={5.0}>5 km</option>
              <option value={10.0}>10 km</option>
              <option value={25.0}>25 km</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-slate-400">Depth Window (Δ MD):</span>
            <select
              value={depthWindowM}
              onChange={(e) => setDepthWindowM(Number(e.target.value))}
              className="bg-slate-900 text-amber-400 font-bold px-2 py-0.5 rounded border border-slate-700 focus:outline-none"
            >
              <option value={25.0}>± 25 m</option>
              <option value={50.0}>± 50 m</option>
              <option value={100.0}>± 100 m</option>
              <option value={250.0}>± 250 m</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alert Matches Counter Banner */}
      {matches.length > 0 ? (
        <div className="bg-amber-950/40 border border-amber-500/40 rounded-lg p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2.5 text-amber-300 font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping"></span>
            <span>
              ⚠ {matches.length} HISTORICAL OFFSET EVENT{matches.length > 1 ? "S" : ""} NEAR CURRENT DEPTH ({displayDepth.toFixed(1)} m)
            </span>
          </div>

          <div className="text-slate-400 text-[11px] bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
            Within {depthWindowM}m depth window | Radius {radiusKm}km
          </div>
        </div>
      ) : (
        <div className="bg-slate-950 border border-slate-850 rounded-lg p-4 text-center font-mono text-xs text-slate-400 flex items-center justify-center gap-2">
          <Info className="w-4 h-4 text-blue-400" />
          <span>No historical offset events detected within {depthWindowM}m of current depth ({displayDepth.toFixed(1)} m).</span>
        </div>
      )}

      {/* Proximity Alert Cards Grid */}
      {matches.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {matches.map((m: HistoricalProximityMatch, idx: number) => (
            <div
              key={`${m.event_episode_id || 'match'}-${idx}`}
              className="rounded-[14px] p-5 space-y-4 relative overflow-hidden transition-all duration-300 flex flex-col group"
              style={{ background: "rgba(10,10,10,0.65)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,122,0,0.3)", boxShadow: "0 0 15px rgba(255,122,0,0.05)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,122,0,0.8)";
                e.currentTarget.style.boxShadow = "0 0 25px rgba(255,122,0,0.15)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "rgba(255,122,0,0.3)";
                e.currentTarget.style.boxShadow = "0 0 15px rgba(255,122,0,0.05)";
              }}
            >
              {/* Card Top Banner */}
              <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid rgba(255,122,0,0.15)" }}>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 rounded font-mono font-bold transition-colors" style={{ border: "1px solid rgba(255,122,0,0.4)", color: "#8A8A8A", background: "transparent" }}>
                    {m.event_type}
                  </span>
                  <span className="text-[11px] font-mono px-2 py-1 rounded transition-colors" style={{ color: "#FF7A00", background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.2)" }}>
                    {m.proximity_classification}
                  </span>
                </div>

                <div className="text-xs font-mono font-bold flex items-center gap-1.5" style={{ color: "#FF7A00" }}>
                  <MapPin className="w-3.5 h-3.5" />
                  {m.offset_well_id} ({m.offset_well_distance_km} km)
                </div>
              </div>

              {/* Depth Comparison Ruler Diagram */}
              <div className="p-3.5 rounded-lg space-y-2.5 font-mono text-xs" style={{ background: "rgba(15,15,15,0.7)", border: "1px solid rgba(255,122,0,0.2)" }}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 font-bold uppercase tracking-wide" style={{ color: "#FF7A00" }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: "#FF7A00", boxShadow: "0 0 8px #FF7A00" }}></span>
                    ACTIVE DRILLING ({activeWellId}):
                  </span>
                  <strong className="text-[13px]" style={{ color: "#FF7A00" }}>{m.current_md.toFixed(1)} m</strong>
                </div>

                <div className="flex items-center justify-center gap-2 text-[11px] py-2" style={{ color: "#8A8A8A", borderTop: "1px dashed rgba(255,122,0,0.2)", borderBottom: "1px dashed rgba(255,122,0,0.2)" }}>
                  <ArrowDown className="w-3.5 h-3.5 animate-bounce" style={{ color: "#FF7A00" }} />
                  <span>Depth Difference: <strong className="font-bold tracking-wide" style={{ color: "#F5F5F5" }}>Δ {m.delta_md.toFixed(1)} m</strong></span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2 font-bold uppercase tracking-wide" style={{ color: "#10B981" }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: "#10B981", boxShadow: "0 0 8px #10B981" }}></span>
                    OFFSET EVENT ({m.offset_well_id}):
                  </span>
                  <strong className="text-[13px]" style={{ color: "#10B981" }}>{m.event_md.toFixed(1)} m</strong>
                </div>
              </div>

              {/* Primary Evidence Excerpt */}
              <div className="text-[12px] leading-relaxed font-sans mt-2" style={{ color: "#8A8A8A" }}>
                <strong className="font-mono text-[10px] uppercase block mb-1 tracking-wider" style={{ color: "#6A6A6A" }}>
                  Primary DDR Activity Text:
                </strong>
                {m.primary_evidence}
              </div>

              {/* Source Tag & Explicit Scientific Disclaimer */}
              <div className="mt-auto pt-4 space-y-3">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="flex items-center gap-1.5" style={{ color: "#8A8A8A" }}>
                    <Shield className="w-3.5 h-3.5" style={{ color: "#FF7A00" }} />
                    Source: <code style={{ color: "#D4D4D4" }}>{m.source_label}</code>
                  </span>
                  <span className="font-bold" style={{ color: "#10B981" }}>Verified DDR Record</span>
                </div>

                {/* MANDATORY SCIENTIFIC RULE DISCLAIMER BANNER */}
                <div className="rounded-lg p-2.5 text-center text-[11px] font-mono font-bold tracking-wider uppercase" style={{ background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.4)", color: "#FF7A00", boxShadow: "inset 0 0 10px rgba(255,122,0,0.05)" }}>
                  ⚠ {m.disclaimer}
                </div>
              </div>

              {/* Card Action Buttons */}
              <div className="pt-3 flex items-center justify-end gap-3 text-xs font-mono mt-1">
                <button
                  onClick={() => onOpenWellIntelligence(m.offset_well_id)}
                  className="px-4 py-2 rounded-lg transition-all flex items-center gap-1.5 tracking-wide"
                  style={{ background: "transparent", border: "1px solid rgba(255,122,0,0.3)", color: "#A0A0A0" }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#FF7A00"; e.currentTarget.style.color = "#FF7A00"; e.currentTarget.style.boxShadow = "0 0 10px rgba(255,122,0,0.15)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,122,0,0.3)"; e.currentTarget.style.color = "#A0A0A0"; e.currentTarget.style.boxShadow = "none"; }}
                >
                  View Well ➔
                </button>

                <button
                  onClick={() =>
                    onOpenEventDetail({
                      event_episode_id: m.event_episode_id,
                      event_type: m.event_type,
                      event_domain: m.event_domain,
                      well_id: m.offset_well_id,
                      wellbore_id: m.offset_well_id,
                      onset_timestamp: "Historical DDR Record",
                      onset_md: m.event_md,
                      onset_tvd: m.event_tvd,
                      primary_evidence: m.primary_evidence,
                      mitigation_text: m.mitigation_text,
                      resolution_text: m.resolution_text,
                      primary_source_record: m.primary_source_record,
                      source_label: m.source_label,
                    })
                  }
                  className="px-4 py-2 rounded-lg transition-all flex items-center gap-1.5 font-bold tracking-wide"
                  style={{ background: "linear-gradient(180deg, rgba(255,122,0,0.65) 0%, rgba(200,90,0,0.9) 100%)", border: "1px solid rgba(255,122,0,0.8)", color: "#FFF", boxShadow: "0 0 15px rgba(255,122,0,0.25)" }}
                  onMouseEnter={(e) => e.currentTarget.style.boxShadow = "0 0 25px rgba(255,122,0,0.45)"}
                  onMouseLeave={(e) => e.currentTarget.style.boxShadow = "0 0 15px rgba(255,122,0,0.25)"}
                >
                  View Event Details →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
