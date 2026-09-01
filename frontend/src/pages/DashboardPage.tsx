import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { CurrentDrillingState } from "../components/telemetry/CurrentDrillingState";
import { HistoricalProximityPanel } from "../components/events/HistoricalProximityPanel";
import { NearbyWellsMap } from "../components/map/NearbyWellsMap";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { SystemStatus } from "../components/system/SystemStatus";
import { Map, ArrowRight, X } from "lucide-react";
import type { HistoricalEventEpisode } from "../types/api";

export const DashboardPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell, currentMd, tvd, status, samplesReceived, lastTimestamp, latestSensor, mlState } = useActiveWell();
  const navigate = useNavigate();
  const [selectedEventModal, setSelectedEventModal] = useState<HistoricalEventEpisode | null>(null);

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
    <div className="relative min-h-[calc(100vh-6rem)] -m-4 sm:-m-6 p-4 sm:p-6 overflow-hidden">
      {/* Background Image scoped only to this page */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat bg-[#02050A]"
        style={{ backgroundImage: 'url("/src/assets/hero.png")' }}
      >
        <div className="absolute inset-0 bg-[#070B14]/85 backdrop-blur-[2px]" />
      </div>

      <div className="relative z-10 space-y-6 max-w-7xl mx-auto">
        {/* 1. Current Drilling Position Banner */}
      <CurrentDrillingState
        wellId={selectedWell}
        currentMd={currentMd}
        tvd={tvd}
        lastTimestamp={lastTimestamp}
        samplesReceived={samplesReceived}
      />

      {/* 2. Hero Proactive Historical Proximity Alerts */}
      <HistoricalProximityPanel
        activeWellId={selectedWell}
        currentMd={currentMd}
        onOpenWellIntelligence={(wellId) => navigate(`/wells/${encodeURIComponent(wellId)}`)}
        onOpenEventDetail={(ev) => setSelectedEventModal(ev)}
      />

      {/* 3. Map & Live Telemetry Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Preview (1/3) */}
        <div className="bg-[#070B14]/60 backdrop-blur-xl border border-slate-800/60 rounded-2xl p-5 shadow-2xl space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-slate-800/60 pb-3 font-mono">
            <div className="flex items-center gap-2">
              <Map className="w-4 h-4 text-emerald-400" />
              <span className="font-bold text-white text-xs uppercase tracking-wider">Field Map Preview</span>
            </div>
            <Link
              to="/map"
              className="text-xs text-blue-400 hover:text-orange-400 font-bold flex items-center gap-1 hover:underline transition-colors"
            >
              FULL MAP <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="h-[280px] rounded-xl overflow-hidden border border-slate-800/50 shadow-inner">
            <NearbyWellsMap
              wells={wells}
              selectedWell={selectedWell}
              onSelectWell={(wId) => setSelectedWell(wId)}
              onOpenIntelligence={(wId) => navigate(`/wells/${encodeURIComponent(wId)}`)}
            />
          </div>
        </div>

        {/* Real-time Telemetry Grid (2/3) */}
        <div className="lg:col-span-2">
          <TelemetryCards latestSensor={latestSensor} />
        </div>
      </div>

      {/* 4. System & Stream Health Status */}
      <SystemStatus streamStatus={status} mlState={mlState} />

      {/* Event Detail Modal */}
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
              <span className={`text-xs px-2.5 py-1 rounded font-mono font-bold border ${getEventBadgeStyle(selectedEventModal.event_type)}`}>
                {selectedEventModal.event_type}
              </span>
              <span className="text-xs font-mono text-slate-400">Well: {selectedEventModal.well_id}</span>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono">
              <div>
                <span className="text-slate-400 block text-[10px]">Onset MD</span>
                <span className="text-white font-bold">{selectedEventModal.onset_md} m</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">TVD</span>
                <span className="text-white font-bold">{selectedEventModal.onset_tvd ? `${selectedEventModal.onset_tvd} m` : "N/A"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Timestamp</span>
                <span className="text-white font-bold">{selectedEventModal.onset_timestamp || "N/A"}</span>
              </div>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1">
                <span className="text-emerald-400 font-bold block">Observed Evidence:</span>
                <p className="text-slate-300 font-sans text-xs">{selectedEventModal.primary_evidence}</p>
              </div>

              {selectedEventModal.mitigation_text && (
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1">
                  <span className="text-blue-400 font-bold block">Mitigation Response:</span>
                  <p className="text-slate-300 font-sans text-xs">{selectedEventModal.mitigation_text}</p>
                </div>
              )}

              {selectedEventModal.resolution_text && (
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-1">
                  <span className="text-amber-400 font-bold block">Resolution Outcome:</span>
                  <p className="text-slate-300 font-sans text-xs">{selectedEventModal.resolution_text}</p>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-400">Source: Equinor Volve DDR ({selectedEventModal.primary_source_record})</span>
              <button
                onClick={() => {
                  const evId = selectedEventModal.event_episode_id;
                  setSelectedEventModal(null);
                  navigate(`/events/${encodeURIComponent(evId)}`);
                }}
                className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg font-bold transition-all"
              >
                OPEN FULL EVIDENCE PAGE ➔
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};
