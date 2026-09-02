import React from "react";
import { useNavigate } from "react-router-dom";
import { useActiveWell } from "../context/ActiveWellContext";
import {
  Database,
  MapPin,
  ArrowRight,
  Radio,
  Play,
  Layers,
} from "lucide-react";

export const WellsPage: React.FC = () => {
  const { wells, selectedWell, setSelectedWell, currentMd, status } = useActiveWell();
  const navigate = useNavigate();

  const handleStartStream = (wellId: string) => {
    setSelectedWell(wellId);
    navigate("/live");
  };

  return (
    <div className="space-y-[24px] font-mono px-4 sm:px-8 py-2">
      {/* Header Banner */}
      <div 
        className="rounded-[24px] p-[24px] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,122,0,0.1)]"
        style={{
          background: "rgba(20, 20, 20, 0.65)",
          border: "1px solid rgba(249, 115, 22, 0.25)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          minHeight: "130px"
        }}
      >
        <div>
          <div className="flex items-center gap-5">
            <div 
              className="p-4 rounded-[16px] text-[#FF7A00]" 
              style={{ background: "rgba(255,122,0,0.08)", border: "1px solid rgba(255,122,0,0.3)" }}
            >
              <Database className="w-8 h-8" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-[22px] font-bold text-white uppercase tracking-wider" style={{ fontFamily: "Space Grotesk, system-ui, sans-serif" }}>
                VOLVE FIELD WELL INVENTORY & STREAM CONTROLLER
              </h1>
              <p className="text-[14px] text-slate-400 mt-1">
                Select any wellbore to initiate real-time telemetry streaming, spatial correlation, or deep intelligence.
              </p>
            </div>
          </div>
        </div>

        {/* Active Well Status Pill */}
        <div 
          className="flex items-center gap-4 px-5 py-3 rounded-[16px] self-start md:self-auto"
          style={{ background: "rgba(10,10,10,0.45)", border: "1px solid rgba(255,255,255,0.05)" }}
        >
          <Radio className={`w-5 h-5 ${status === "LIVE" ? "text-[#FF7A00] animate-pulse" : "text-slate-500"}`} />
          <div className="text-xs">
            <div className="text-slate-500 text-[10px] uppercase font-bold tracking-widest">CURRENT ACTIVE STREAM</div>
            <div className="text-white font-bold flex items-center gap-2 mt-0.5">
              <span className="text-[#FF7A00] text-sm">{selectedWell}</span>
              <span className="text-[#FF7A00] font-mono opacity-90 text-sm">({currentMd.toFixed(1)}m)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Wells Grid Table */}
      <div 
        className="rounded-[24px] overflow-hidden shadow-xl"
        style={{
          background: "rgba(20, 20, 20, 0.70)",
          border: "1px solid rgba(255, 122, 0, 0.20)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          padding: "20px"
        }}
      >
        <div className="pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-transparent">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-[#FF7A00]" />
            <span className="text-[14px] font-bold text-white uppercase tracking-wider">
              AVAILABLE WELLBORES <span className="text-[#FF7A00]">({wells.length})</span>
            </span>
          </div>
          <span className="text-[13px] text-slate-400 font-mono">
            Volve Platform Complex • <span className="text-[#FF7A00]">Block 15/9 (Equinor)</span>
          </span>
        </div>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-left text-xs" style={{ borderCollapse: "separate", borderSpacing: "0 8px" }}>
            <thead>
              <tr className="text-slate-500 font-bold text-[11px] uppercase tracking-[1px] border-b border-transparent">
                <th className="px-4 py-2 font-medium">WELLBORE ID</th>
                <th className="px-4 py-2 font-medium">SLOT ID</th>
                <th className="px-4 py-2 font-medium">OPERATOR</th>
                <th className="px-4 py-2 font-medium">FIELD</th>
                <th className="px-4 py-2 font-medium">SURFACE COORDINATES</th>
                <th className="px-4 py-2 font-medium">WATER DEPTH</th>
                <th className="px-4 py-2 font-medium text-right">STREAM & INTELLIGENCE</th>
              </tr>
            </thead>
            <tbody>
              {wells.map((w) => {
                const isActive = w.well_id === selectedWell;
                return (
                  <tr
                    key={w.well_id}
                    className="group transition-all duration-200"
                    style={{
                      background: "rgba(30, 30, 30, 0.65)",
                      boxShadow: isActive ? "inset 4px 0 0 #FF7A00, 0 0 10px rgba(255,122,0,0.05)" : "inset 1px 1px 0 rgba(255,255,255,0.05)",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "rgba(40, 40, 40, 0.75)";
                        e.currentTarget.style.boxShadow = "inset 1px 1px 0 rgba(255,122,0,0.2), 0 0 15px rgba(255,122,0,0.05)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "rgba(30, 30, 30, 0.65)";
                        e.currentTarget.style.boxShadow = "inset 1px 1px 0 rgba(255,255,255,0.05)";
                      }
                    }}
                  >
                    <td className="p-4 rounded-l-[12px] text-white">
                      <div className="flex items-center gap-3">
                        <MapPin className="w-4 h-4 text-[#FF7A00]" />
                        <span className="font-mono text-[14px] font-bold">{w.well_id}</span>
                      </div>
                    </td>
                    <td className="p-4 text-slate-300">{w.slot_name || "Subsea Template A"}</td>
                    <td className="p-4 text-slate-300">{w.operator || "Equinor"}</td>
                    <td className="p-4 text-slate-300">{w.field || "Volve"}</td>
                    <td className="p-4 text-slate-300 font-mono">
                      {w.latitude ? `${w.latitude.toFixed(5)}° N, ${w.longitude?.toFixed(5)}° E` : "58.43500° N, 1.90200° E"}
                    </td>
                    <td className="p-4 text-white">{w.water_depth_m ? `${w.water_depth_m} m` : "84 m"}</td>
                    <td className="p-4 rounded-r-[12px] text-right">
                      <div className="flex items-center justify-end gap-[10px]">
                        {/* Start Stream Button */}
                        <button
                          onClick={() => handleStartStream(w.well_id)}
                          className="text-white text-[11px] font-bold px-4 py-2 rounded-[10px] transition-all flex items-center justify-center gap-1.5 cursor-pointer w-[96px] h-[36px]"
                          style={{
                            background: "linear-gradient(145deg, #FF7A00, #FF5A00)",
                            boxShadow: "0 0 16px rgba(255,122,0,0.30)",
                            border: "none"
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 0 20px rgba(255,122,0,0.50)"; e.currentTarget.style.filter = "brightness(1.1)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 0 16px rgba(255,122,0,0.30)"; e.currentTarget.style.filter = "none"; }}
                        >
                          <Play className="w-3 h-3 fill-current" />
                          <span>STREAM</span>
                        </button>

                        {/* Set Active Button */}
                        <button
                          onClick={() => setSelectedWell(w.well_id)}
                          className="text-white text-[11px] font-bold rounded-[10px] transition-all cursor-pointer w-[72px] h-[36px] flex items-center justify-center"
                          style={{
                            background: "rgba(10,10,10,0.45)",
                            border: "1px solid rgba(255,122,0,0.30)"
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,122,0,0.08)"; e.currentTarget.style.border = "1px solid rgba(255,122,0,0.65)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(10,10,10,0.45)"; e.currentTarget.style.border = "1px solid rgba(255,122,0,0.30)"; }}
                        >
                          SELECT
                        </button>

                        {/* Intelligence Button */}
                        <button
                          onClick={() => navigate(`/wells/${encodeURIComponent(w.well_id)}`)}
                          className="text-white text-[11px] font-bold rounded-[10px] transition-all cursor-pointer w-[78px] h-[36px] flex items-center justify-center gap-1 group/intel"
                          style={{
                            background: "rgba(20,20,20,0.5)",
                            border: "1px solid rgba(255,122,0,0.4)"
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,122,0,0.08)"; e.currentTarget.style.border = "1px solid rgba(255,122,0,0.8)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(20,20,20,0.5)"; e.currentTarget.style.border = "1px solid rgba(255,122,0,0.4)"; }}
                        >
                          <span>INTEL</span>
                          <ArrowRight className="w-3 h-3 text-[#FF7A00]" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

