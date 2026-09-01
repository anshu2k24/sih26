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
              key={m.event_episode_id || idx}
              className="bg-[#0B101E]/80 backdrop-blur-md border border-amber-500/30 rounded-xl p-4 shadow-lg space-y-3 relative overflow-hidden group hover:-translate-y-1 hover:border-orange-500/60 hover:shadow-[0_0_20px_rgba(255,140,0,0.2)] hover:bg-[#0B101E] transition-all duration-300"
            >
              {/* Card Top Banner */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-mono font-bold border ${getEventBadgeStyle(
                      m.event_type
                    )}`}
                  >
                    {m.event_type}
                  </span>
                  <span className="text-[11px] font-mono font-bold text-amber-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    {m.proximity_classification}
                  </span>
                </div>

                <div className="text-xs font-mono font-bold text-emerald-400 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  {m.offset_well_id} ({m.offset_well_distance_km} km)
                </div>
              </div>

              {/* Depth Comparison Ruler Diagram */}
              <div className="bg-slate-900 p-3 rounded-lg border border-slate-850 space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between text-slate-300">
                  <span className="flex items-center gap-1 text-amber-400 font-bold">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    ACTIVE DRILLING ({activeWellId}):
                  </span>
                  <strong className="text-amber-400 text-sm">{m.current_md.toFixed(1)} m</strong>
                </div>

                <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400 py-0.5 border-y border-slate-800">
                  <ArrowDown className="w-3.5 h-3.5 text-amber-400 animate-bounce" />
                  <span>Depth Difference: <strong className="text-white font-bold">Δ {m.delta_md.toFixed(1)} m</strong></span>
                </div>

                <div className="flex items-center justify-between text-slate-300">
                  <span className="flex items-center gap-1 text-emerald-400 font-bold">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    OFFSET EVENT ({m.offset_well_id}):
                  </span>
                  <strong className="text-emerald-400 text-sm">{m.event_md.toFixed(1)} m</strong>
                </div>
              </div>

              {/* Primary Evidence Excerpt */}
              <div className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-900/60 p-2.5 rounded-lg border border-slate-850">
                <strong className="text-slate-400 font-mono text-[10px] uppercase block mb-0.5">
                  Primary DDR Activity Text:
                </strong>
                {m.primary_evidence}
              </div>

              {/* Source Tag & Explicit Scientific Disclaimer */}
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5 text-blue-400" />
                    Source: <code className="text-slate-200">{m.source_label}</code>
                  </span>
                  <span className="text-emerald-400 font-bold">Verified DDR Record</span>
                </div>

                {/* MANDATORY SCIENTIFIC RULE DISCLAIMER BANNER */}
                <div className="bg-amber-950/80 border border-amber-500/50 rounded p-2 text-center text-[11px] font-mono font-bold text-amber-300 tracking-wide uppercase">
                  ⚠ {m.disclaimer}
                </div>
              </div>

              {/* Card Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-2 text-xs font-mono">
                <button
                  onClick={() => onOpenWellIntelligence(m.offset_well_id)}
                  className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-700 font-bold transition-all flex items-center gap-1"
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
                  className="px-3.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded border border-emerald-500/40 font-bold transition-all flex items-center gap-1 shadow-md"
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
