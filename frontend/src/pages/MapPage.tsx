import React from "react";
import { useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { NearbyWellsMap } from "../components/map/NearbyWellsMap";
import { MapPin, Compass, ShieldAlert } from "lucide-react";

export const MapPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell } = useActiveWell();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono">
        <div>
          <div className="flex items-center gap-3">
            <Compass className="w-5 h-5 text-emerald-400 animate-spin-slow" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              GEOSPATIAL INTELLIGENCE MAP
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-bold">
              AUTOFOCUSED VOLVE CLUSTER
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Surface coordinates ingested from Norwegian Offshore Directorate (NPD). Distances labeled as Surface Platform Slot Distance.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs bg-slate-950 px-3.5 py-2 rounded-lg border border-slate-800">
          <MapPin className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-400">Active Well Context:</span>
          <span className="font-bold text-white">{selectedWell}</span>
        </div>
      </div>

      {/* Main Full-Size Map Component */}
      <NearbyWellsMap
        wells={wells}
        selectedWell={selectedWell}
        onSelectWell={(wId) => setSelectedWell(wId)}
        onOpenIntelligence={(wId) => navigate(`/wells/${encodeURIComponent(wId)}`)}
      />

      {/* Scientific Provenance Callout Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Surface Slot Distance represents platform slot header separation on the Volve Platform Complex deck.</span>
        </div>
        <span className="text-slate-500">NPD Verified Coordinates</span>
      </div>
    </div>
  );
};
