import React from "react";
import { useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import { NearbyWellsMap } from "../components/map/NearbyWellsMap";
import { MapPin, Compass, ShieldAlert } from "lucide-react";

export const MapPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell } = useActiveWell();
  const navigate = useNavigate();

  return (
    <div 
      className="min-h-screen pb-[48px] relative overflow-hidden"
      style={{ 
        backgroundColor: "#050505", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        fontFamily: "'Space Grotesk', 'Inter', sans-serif" 
      }}
    >
      {/* Absolute Ambient Background Lights */}
      <div className="absolute top-[10%] left-[10%] w-[50%] h-[40%] rounded-full opacity-[0.04] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] rounded-full opacity-[0.03] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF8A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-[32px] pt-[32px] space-y-[24px]">
        {/* Header - Transparent */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-2">
          <div className="relative z-10">
            <div className="flex items-center gap-4 flex-wrap">
              <h1 className="text-[20px] sm:text-[24px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                GEOSPATIAL INTELLIGENCE MAP
              </h1>
            </div>
          </div>

          <div 
            className="relative z-10 flex items-center gap-3 px-[16px] py-[12px] rounded-[12px] transition-all duration-200"
            style={{
              background: "rgba(18, 16, 14, 0.8)",
              border: "1px solid rgba(255, 138, 0, 0.4)",
              boxShadow: "0 4px 15px rgba(0,0,0,0.3), inset 0 0 15px rgba(255,138,0,0.1)"
            }}
          >
            <MapPin className="w-4 h-4 text-[#FF8A00]" />
            <span className="text-[12px] text-[#A1A1AA] font-[700] tracking-wider uppercase">Active Well Context:</span>
            <span className="font-[700] text-white text-[14px] drop-shadow-[0_0_5px_rgba(255,138,0,0.5)]">{selectedWell}</span>
          </div>
        </div>

        {/* Main Full-Size Map Component */}
        <NearbyWellsMap
          wells={wells}
          selectedWell={selectedWell}
          onSelectWell={(wId) => setSelectedWell(wId)}
          onOpenIntelligence={(wId) => navigate(`/wells/${encodeURIComponent(wId)}`)}
        />
      </div>
    </div>
  );
};
