import React from "react";
import { Activity, ShieldAlert, Database } from "lucide-react";
import type { WellItem } from "../../types/api";

interface HeaderProps {
  wells: WellItem[];
  selectedWell: string;
  onSelectWell: (wellId: string) => void;
  status: string;
}

export const Header: React.FC<HeaderProps> = ({
  wells,
  selectedWell,
  onSelectWell,
  status,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 sticky top-0 z-50 shadow-xl">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Brand & Scientific Classification Banner */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg border border-blue-500/30">
            <Activity className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-white font-mono">
                eRTMAC-NWIS
              </h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-sans font-medium">
                Operational Drilling Console
              </span>
            </div>
            {/* MANDATORY SCIENTIFIC LABEL */}
            <div className="mt-1 flex items-center gap-1.5 text-xs text-amber-400 font-medium tracking-wide">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>REAL VOLVE DATA — HISTORICAL REPLAY</span>
            </div>
          </div>
        </div>

        {/* Well Selector & Connection Status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <Database className="w-4 h-4 text-slate-400" />
            <label htmlFor="well-select" className="text-xs text-slate-400 font-medium">
              Well:
            </label>
            <select
              id="well-select"
              value={selectedWell}
              onChange={(e) => onSelectWell(e.target.value)}
              className="bg-slate-900 text-white text-xs font-mono font-semibold px-2.5 py-1 rounded border border-slate-700 focus:outline-none focus:border-blue-500"
            >
              {wells.map((w) => (
                <option key={w.well_id} value={w.well_id}>
                  {w.well_id}
                </option>
              ))}
            </select>
          </div>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-mono text-xs font-bold tracking-wide ${
              status === "LIVE"
                ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/40"
                : "bg-rose-950/60 text-rose-400 border-rose-500/40"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status === "LIVE" ? "bg-emerald-400 animate-ping" : "bg-rose-500"
              }`}
            />
            <span>{status === "LIVE" ? "🟢 LIVE" : "🔴 STREAM DISCONNECTED"}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
