import React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell,
  Database,
  ShieldCheck,
  Sliders,
  LogOut
} from "lucide-react";
import { useActiveWell } from "../../context/ActiveWellContext";
import { useAuth } from "../../context/AuthContext";

export const Header: React.FC = () => {
  const { wells, selectedWell, setSelectedWell, status, currentMd } = useActiveWell();
  const { profile, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 py-3 sticky top-0 z-30 shadow-md">
      <div className="flex items-center justify-between gap-4 font-mono text-xs">
        {/* Left Side: Active Well Context Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 px-3.5 py-1.5 rounded-xl border border-slate-800 shadow-inner">
            <Database className="w-4 h-4 text-cyan-400" />
            <span className="text-slate-400 font-semibold">Active Well:</span>
            <select
              id="well-select"
              value={selectedWell}
              onChange={(e) => setSelectedWell(e.target.value)}
              className="bg-slate-900 text-cyan-300 font-bold px-2.5 py-1 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              {wells.map((w) => (
                <option key={w.well_id} value={w.well_id}>
                  {w.well_id}
                </option>
              ))}
            </select>
            <span className="text-emerald-400 font-bold border-l border-slate-800 pl-2.5">
              MD: {currentMd > 0 ? `${currentMd.toFixed(1)}m` : "1509.1m"}
            </span>
          </div>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border font-bold tracking-wider ${
              status === "LIVE"
                ? "bg-emerald-950/50 text-emerald-400 border-emerald-500/30"
                : "bg-rose-950/50 text-rose-400 border-rose-500/30"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status === "LIVE" ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span>{status === "LIVE" ? "LIVE STREAM" : "DISCONNECTED"}</span>
          </div>
        </div>

        {/* Right Side: Quick Action Links & User Info */}
        <div className="flex items-center gap-3">
          <Link
            to="/notifications"
            className="flex items-center gap-1.5 bg-slate-950 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded-xl border border-slate-800 transition-all"
            title="Notification Center"
          >
            <Bell className="w-4 h-4 text-amber-400" />
            <span className="font-bold">Notifications</span>
          </Link>

          <Link
            to="/settings"
            className="p-2 bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl border border-slate-800 transition-all"
            title="System Settings"
          >
            <Sliders className="w-4 h-4" />
          </Link>

          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1 rounded-xl border border-slate-800 text-slate-300">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold text-white">{profile?.full_name || profile?.email || "Operator"}</span>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-500/30 font-bold">
              {profile?.role || "ADMIN"}
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 px-3 py-1.5 rounded-xl border border-rose-800/40 hover:border-rose-600 transition-all font-bold cursor-pointer"
            title="Sign out of Supabase session"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
};
