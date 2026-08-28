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
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-xl text-blue-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white uppercase tracking-wider">
                Volve Field Well Inventory & Stream Controller
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Select any wellbore to initiate real-time telemetry streaming, spatial correlation, or deep intelligence.
              </p>
            </div>
          </div>
        </div>

        {/* Active Well Status Pill */}
        <div className="flex items-center gap-3 bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-800 self-start md:self-auto">
          <Radio className={`w-4 h-4 ${status === "LIVE" ? "text-emerald-400 animate-pulse" : "text-amber-400"}`} />
          <div className="text-xs">
            <div className="text-slate-400 text-[10px] uppercase font-bold">CURRENT ACTIVE STREAM</div>
            <div className="text-white font-bold flex items-center gap-2">
              <span className="text-cyan-400">{selectedWell}</span>
              <span className="text-emerald-400 font-mono">({currentMd.toFixed(1)}m)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Wells Grid Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Available Wellbores ({wells.length})
            </span>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Volve Platform Complex • Block 15/9 (Equinor)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold">
                <th className="p-3.5">WELLBORE ID</th>
                <th className="p-3.5">SLOT ID</th>
                <th className="p-3.5">OPERATOR</th>
                <th className="p-3.5">FIELD</th>
                <th className="p-3.5">SURFACE COORDINATES</th>
                <th className="p-3.5">WATER DEPTH</th>
                <th className="p-3.5 text-right">STREAM & INTELLIGENCE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {wells.map((w) => {
                const isActive = w.well_id === selectedWell;
                return (
                  <tr
                    key={w.well_id}
                    className={`hover:bg-slate-850/60 transition-all ${
                      isActive ? "bg-cyan-950/20 border-l-2 border-l-cyan-400" : ""
                    }`}
                  >
                    <td className="p-3.5 font-bold text-white">
                      <div className="flex items-center gap-2">
                        <MapPin className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-500"}`} />
                        <span>{w.well_id}</span>
                        {isActive && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 font-bold flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            ACTIVE
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3.5 text-slate-300">{w.slot_name || "Platform Slot"}</td>
                    <td className="p-3.5 text-slate-300">{w.operator || "Equinor Energy AS"}</td>
                    <td className="p-3.5 text-slate-300">{w.field || "Volve Field"}</td>
                    <td className="p-3.5 text-slate-400 font-mono">
                      {w.latitude ? `${w.latitude.toFixed(5)}° N, ${w.longitude?.toFixed(5)}° E` : "58.44168° N, 1.88778° E"}
                    </td>
                    <td className="p-3.5 text-slate-300">{w.water_depth_m ? `${w.water_depth_m} m` : "91.0 m"}</td>
                    <td className="p-3.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Start Stream Button */}
                        <button
                          onClick={() => handleStartStream(w.well_id)}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all shadow-md shadow-emerald-500/10 flex items-center gap-1.5 cursor-pointer"
                        >
                          <Play className="w-3 h-3 fill-current" />
                          <span>STREAM</span>
                        </button>

                        {/* Set Active Button */}
                        {!isActive && (
                          <button
                            onClick={() => setSelectedWell(w.well_id)}
                            className="bg-slate-800 hover:bg-slate-700 text-cyan-300 text-[11px] font-bold px-3 py-1.5 rounded-lg border border-slate-700 hover:border-cyan-500/40 transition-all cursor-pointer"
                          >
                            SELECT
                          </button>
                        )}

                        {/* Intelligence Button */}
                        <button
                          onClick={() => navigate(`/wells/${encodeURIComponent(w.well_id)}`)}
                          className="bg-blue-600/80 hover:bg-blue-500 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1 cursor-pointer"
                        >
                          <span>INTEL</span>
                          <ArrowRight className="w-3 h-3" />
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

