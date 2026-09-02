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
    <header className="bg-[#050608]/90 backdrop-blur-xl border-b border-[#FF7A00]/10 px-6 py-3 sticky top-0 z-30 shadow-md">
      <div className="flex items-center justify-between gap-4 font-mono text-xs">
        {/* Left Side: Active Well Context Indicator */}
        <div className="flex items-center gap-3">
          <div 
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-[12px] shadow-inner"
            style={{ background: "rgba(10,10,10,0.45)", border: "1px solid rgba(255,122,0,0.3)" }}
          >
            <Database className="w-4 h-4 text-[#FF7A00]" />
            <span className="text-slate-400 font-semibold">Active Well:</span>
            <select
              id="well-select"
              value={selectedWell}
              onChange={(e) => setSelectedWell(e.target.value)}
              className="bg-transparent text-white font-bold px-1 py-1 focus:outline-none cursor-pointer"
            >
              {wells.map((w) => (
                <option key={w.well_id} value={w.well_id} className="bg-[#111111]">
                  {w.well_id}
                </option>
              ))}
            </select>
            <span className="text-slate-400 font-semibold border-l border-white/10 pl-2.5">
              MD: <span className="text-[#FF7A00] font-mono font-bold">{currentMd > 0 ? `${currentMd.toFixed(1)}m` : "1509.1m"}</span>
            </span>
          </div>

          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-[12px] border font-bold tracking-wider ${
              status === "LIVE"
                ? "text-[#FF7A00]"
                : "text-slate-500"
            }`}
            style={
              status === "LIVE"
                ? { background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.4)", boxShadow: "0 0 10px rgba(255,122,0,0.15)" }
                : { background: "rgba(20,20,20,0.6)", border: "1px solid rgba(255,255,255,0.1)" }
            }
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status === "LIVE" ? "bg-[#FF7A00] animate-pulse" : "bg-slate-500"
              }`}
            />
            <span>{status === "LIVE" ? "LIVE STREAM" : "DISCONNECTED"}</span>
          </div>
        </div>

        {/* Right Side: Quick Action Links & User Info */}
        <div className="flex items-center gap-3">
          <Link
            to="/notifications"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] transition-all hover:bg-white/5"
            style={{ background: "rgba(20,20,20,0.65)", border: "1px solid rgba(255,255,255,0.1)" }}
            title="Notification Center"
          >
            <Bell className="w-4 h-4 text-[#FF7A00]" />
            <span className="font-bold text-white">Notifications</span>
          </Link>

          <Link
            to="/settings"
            className="p-1.5 rounded-[12px] text-slate-400 hover:text-white transition-all hover:bg-white/5"
            style={{ background: "rgba(20,20,20,0.65)", border: "1px solid rgba(255,255,255,0.1)" }}
            title="System Settings"
          >
            <Sliders className="w-4 h-4" />
          </Link>

          <div 
            className="flex items-center gap-2 px-3 py-1.5 rounded-[12px] text-slate-300"
            style={{ background: "rgba(20,20,20,0.65)", border: "1px solid rgba(255,255,255,0.1)" }}
          >
            <ShieldCheck className="w-4 h-4 text-[#FF7A00]" />
            <span className="font-semibold text-white">{profile?.full_name || profile?.email || "Operator"}</span>
            <span className="text-[10px] px-2 py-0.5 rounded font-bold" style={{ color: "#FF7A00" }}>
              {profile?.role || "ADMIN"}
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[12px] transition-all font-bold cursor-pointer hover:bg-white/5"
            style={{ background: "rgba(20,20,20,0.65)", border: "1px solid rgba(255,255,255,0.1)", color: "#FF7A00" }}
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
