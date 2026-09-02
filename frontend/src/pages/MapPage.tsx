import React from "react";
import { useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { NearbyWellsMap } from "../components/map/NearbyWellsMap";
import { MapPin, Compass, ShieldAlert } from "lucide-react";

export const MapPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell } = useActiveWell();
  const navigate = useNavigate();

  return (
    <div className="group relative min-h-[calc(100vh-6rem)] -m-4 sm:-m-6 p-4 sm:p-6 overflow-hidden transition-all duration-500 hover:shadow-[0_0_80px_rgba(249,115,22,0.6)] rounded-xl">
      {/* Background Gradient */}
      <div
        className="absolute inset-0 z-0 transition-all duration-500 group-hover:opacity-90"
        style={{ 
          background: "linear-gradient(135deg, rgba(249, 115, 22, 0.8) 0%, rgba(234, 179, 8, 0.8) 100%)",
        }}
      >
        <div 
          className="absolute inset-0 z-0 transition-all duration-500 group-hover:bg-white/10" 
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)"
          }} 
        />
      </div>

      <div className="relative z-10 space-y-6">
        {/* Header Banner - Glassmorphism, Orange/Black */}
        <div 
          className="rounded-3xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono transition-all duration-300 hover:shadow-[0_0_20px_rgba(245,158,11,0.3)]"
          style={{
            background: "linear-gradient(145deg, rgba(20, 20, 20, 0.72), rgba(10, 10, 10, 0.60))",
            border: "1px solid rgba(245, 158, 11, 0.2)",
            backdropFilter: "blur(18px)",
            WebkitBackdropFilter: "blur(18px)",
            boxShadow: "0 25px 70px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)"
          }}
        >
          <div>
            <div className="flex items-center gap-3">
              <Compass className="w-5 h-5 text-amber-500 animate-spin-slow" />
              <h1 className="text-lg font-bold text-white uppercase tracking-wider">
                GEOSPATIAL INTELLIGENCE MAP
              </h1>
              <span className="text-xs px-2.5 py-0.5 rounded bg-amber-950/80 text-amber-500 border border-amber-500/30 font-bold shadow-[0_0_10px_rgba(245,158,11,0.2)]">
                AUTOFOCUSED VOLVE CLUSTER
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              Surface coordinates ingested from Norwegian Offshore Directorate (NPD). Distances labeled as Surface Platform Slot Distance.
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs bg-black/40 backdrop-blur-md px-3.5 py-2 rounded-lg border border-amber-500/20 shadow-[0_0_10px_rgba(245,158,11,0.1)]">
            <MapPin className="w-4 h-4 text-amber-500" />
            <span className="text-slate-300">Active Well Context:</span>
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
        <div 
          className="rounded-xl p-4 text-xs font-mono text-slate-300 flex items-center justify-between transition-all duration-300 hover:shadow-[0_0_15px_rgba(245,158,11,0.2)]"
          style={{
            background: "rgba(10, 10, 10, 0.6)",
            border: "1px solid rgba(245, 158, 11, 0.2)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-500 shrink-0" />
            <span>Surface Slot Distance represents platform slot header separation on the Volve Platform Complex deck.</span>
          </div>
          <span className="text-amber-500/70 font-bold">NPD Verified Coordinates</span>
        </div>
      </div>
    </div>
  );
};
