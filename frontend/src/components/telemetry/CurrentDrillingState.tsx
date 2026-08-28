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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        <Compass className="w-4 h-4 text-blue-400" />
        Current Drilling Position & Stream State
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Layers className="w-3.5 h-3.5 text-blue-400" /> Active Well
          </div>
          <div className="text-lg font-bold font-mono text-white">{wellId}</div>
        </div>

        <div className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Compass className="w-3.5 h-3.5 text-emerald-400" /> Measured Depth (MD)
          </div>
          <div className="text-lg font-bold font-mono text-emerald-400">
            {currentMd > 0 ? `${currentMd.toFixed(2)} m` : "0.00 m"}
          </div>
        </div>

        <div className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Compass className="w-3.5 h-3.5 text-cyan-400" /> True Vertical Depth (TVD)
          </div>
          <div className="text-lg font-bold font-mono text-cyan-400">
            {tvd !== null ? `${tvd.toFixed(2)} m` : "N/A"}
          </div>
        </div>

        <div className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Clock className="w-3.5 h-3.5 text-amber-400" /> Historical Timestamp
          </div>
          <div className="text-xs font-mono font-semibold text-amber-300 truncate" title={lastTimestamp}>
            {lastTimestamp !== "N/A" ? lastTimestamp : "N/A"}
          </div>
        </div>

        <div className="bg-slate-850/60 p-3.5 rounded-lg border border-slate-800 col-span-2 md:col-span-1">
          <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Hash className="w-3.5 h-3.5 text-purple-400" /> Samples Received
          </div>
          <div className="text-lg font-bold font-mono text-purple-300">
            {samplesReceived.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
};
