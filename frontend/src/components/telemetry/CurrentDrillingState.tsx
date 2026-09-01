import React from "react";
import { Compass, Hash, Clock, Layers } from "lucide-react";

interface CurrentDrillingStateProps {
  wellId: string;
  currentMd: number;
  tvd: number | null;
  lastTimestamp: string;
  samplesReceived: number;
}

export const CurrentDrillingState: React.FC<CurrentDrillingStateProps> = ({
  wellId,
  currentMd,
  tvd,
  lastTimestamp,
  samplesReceived,
}) => {
  return (
    <div className="bg-[rgba(2,5,10,0.3)] backdrop-blur-md border border-[rgba(255,255,255,0.08)] rounded-2xl p-5 shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
      <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest mb-5 flex items-center gap-2">
        <Compass className="w-4 h-4 text-blue-400" />
        Current Drilling Position & Stream State
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-5">
        <div className="bg-[rgba(255,255,255,0.03)] p-4 rounded-xl border border-[rgba(255,255,255,0.05)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/40 hover:bg-[rgba(255,255,255,0.08)] hover:shadow-[0_0_20px_rgba(255,140,0,0.15)]">
          <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
            <Layers className="w-4 h-4 text-blue-400" /> Active Well
          </div>
          <div className="text-xl font-bold font-mono text-white tracking-wider">{wellId}</div>
        </div>

        <div className="bg-[rgba(255,255,255,0.03)] p-4 rounded-xl border border-[rgba(255,255,255,0.05)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/40 hover:bg-[rgba(255,255,255,0.08)] hover:shadow-[0_0_20px_rgba(255,140,0,0.15)]">
          <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
            <Compass className="w-4 h-4 text-emerald-400" /> Measured Depth (MD)
          </div>
          <div className="text-xl font-bold font-mono text-emerald-400 tracking-wider">
            {currentMd > 0 ? `${currentMd.toFixed(2)} m` : "0.00 m"}
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.03)] p-4 rounded-xl border border-[rgba(255,255,255,0.05)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/40 hover:bg-[rgba(255,255,255,0.08)] hover:shadow-[0_0_20px_rgba(255,140,0,0.15)]">
          <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
            <Compass className="w-4 h-4 text-cyan-400" /> True Vertical Depth (TVD)
          </div>
          <div className="text-xl font-bold font-mono text-cyan-400 tracking-wider">
            {tvd !== null ? `${tvd.toFixed(2)} m` : "N/A"}
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.03)] p-4 rounded-xl border border-[rgba(255,255,255,0.05)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/40 hover:bg-[rgba(255,255,255,0.08)] hover:shadow-[0_0_20px_rgba(255,140,0,0.15)]">
          <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
            <Clock className="w-4 h-4 text-amber-400" /> Historical Timestamp
          </div>
          <div className="text-sm font-mono font-bold text-amber-300 truncate" title={lastTimestamp}>
            {lastTimestamp !== "N/A" ? lastTimestamp : "N/A"}
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.03)] p-4 rounded-xl border border-[rgba(255,255,255,0.05)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-orange-500/40 hover:bg-[rgba(255,255,255,0.08)] hover:shadow-[0_0_20px_rgba(255,140,0,0.15)] col-span-2 md:col-span-1">
          <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
            <Hash className="w-4 h-4 text-purple-400" /> Samples Received
          </div>
          <div className="text-xl font-bold font-mono text-purple-300 tracking-wider">
            {samplesReceived.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
};
