import React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell,
  Database,
  ShieldCheck,
  Sliders,
  LogOut,
  ChevronDown
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
    <header 
      className="px-4 py-3 sticky top-0 z-30 flex items-center justify-between"
      style={{
        background: "rgba(5, 6, 8, 0.82)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        borderBottom: "1px solid rgba(255, 122, 0, 0.14)",
        minHeight: "70px",
        fontFamily: "'Space Grotesk', 'Inter', sans-serif"
      }}
    >
      {/* LEFT SIDE */}
      <div className="flex items-center gap-6">
        
        {/* Brand */}
        <div 
          className="flex flex-col justify-center px-4 h-[44px] rounded-[14px]"
          style={{
            background: "rgba(20,20,20,0.55)",
            border: "1px solid rgba(255,122,0,0.18)",
            minWidth: "210px"
          }}
        >
          <div className="font-[700] text-[20px] leading-tight flex">
            <span className="text-[#F5F5F5]">eRTMAC</span>
            <span className="text-[#FF7A00]">-NWIS</span>
          </div>
          <div className="text-[#9A9A9A] text-[10px] font-[400] leading-none lowercase mt-0.5">
            Nearbywells intelligence system
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Active Well */}
          <div 
            className="relative flex items-center px-3 h-[44px] rounded-[14px] group transition-all duration-200"
            style={{
              background: "rgba(20,20,20,0.60)",
              border: "1px solid rgba(255,122,0,0.22)",
              boxShadow: "0 0 12px rgba(255,122,0,0.05)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-1px)";
              e.currentTarget.style.boxShadow = "0 0 18px rgba(255,122,0,0.16)";
              e.currentTarget.style.border = "1px solid rgba(255,122,0,0.55)";
              e.currentTarget.style.background = "rgba(25,25,25,0.70)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0px)";
              e.currentTarget.style.boxShadow = "0 0 12px rgba(255,122,0,0.05)";
              e.currentTarget.style.border = "1px solid rgba(255,122,0,0.22)";
              e.currentTarget.style.background = "rgba(20,20,20,0.60)";
            }}
          >
            <Database className="w-4 h-4 text-[#FF7A00] mr-2 group-hover:text-[#FF9A3D] transition-colors" />
            <span className="text-[#686B7A] text-[13px] font-[500]">Active Well</span>
            <span className="w-px h-4 bg-white/10 mx-2.5"></span>
            <div className="flex items-center gap-1.5 mr-1">
              <span className="text-[#F5F5F5] text-[14px] font-[600]">{selectedWell}</span>
              <ChevronDown className="w-4 h-4 text-[#FF7A00]" />
            </div>

            {/* Invisible Select */}
            <select
              id="well-select"
              value={selectedWell}
              onChange={(e) => setSelectedWell(e.target.value)}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            >
              {wells.map((w) => (
                <option key={w.well_id} value={w.well_id} className="bg-[#111111] text-white">
                  {w.well_id}
                </option>
              ))}
            </select>
          </div>

          {/* MD */}
          <div 
            className="flex items-center px-3 h-[44px] rounded-[14px]"
            style={{
              background: "rgba(20,20,20,0.60)",
              border: "1px solid rgba(255,122,0,0.22)",
            }}
          >
            <span className="text-[#686B7A] text-[13px] font-[500]">MD</span>
            <span className="w-px h-4 bg-white/10 mx-2.5"></span>
            <span className="text-[#FF7A00] text-[14px] font-[600]">
              {currentMd > 0 ? `${currentMd.toFixed(1)} m` : "1509.1 m"}
            </span>
          </div>

          {/* LIVE STREAM */}
          <div
            className={`flex items-center gap-2 px-4 h-[44px] rounded-[14px] font-[600] text-[13px] tracking-wider transition-all duration-200 ${
              status === "LIVE" ? "text-[#FF7A00]" : "text-slate-500"
            }`}
            style={
              status === "LIVE"
                ? { background: "rgba(255,122,0,0.05)", border: "1px solid rgba(255,122,0,0.4)", boxShadow: "0 0 10px rgba(255,122,0,0.15)" }
                : { background: "rgba(20,20,20,0.60)", border: "1px solid rgba(255,255,255,0.1)" }
            }
          >
            <span
              className={`w-2 h-2 rounded-full ${
                status === "LIVE" ? "bg-[#FF7A00] animate-pulse shadow-[0_0_8px_#FF7A00]" : "bg-slate-500"
              }`}
            />
            <span>{status === "LIVE" ? "LIVE STREAM" : "DISCONNECTED"}</span>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE */}
      <div className="flex items-center gap-3">
        
        {/* Notifications */}
        <Link
          to="/notifications"
          className="flex items-center justify-center w-[44px] h-[44px] rounded-[14px] transition-all duration-200 group"
          style={{ background: "rgba(20,20,20,0.60)", border: "1px solid rgba(255,255,255,0.1)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-1px)";
            e.currentTarget.style.border = "1px solid rgba(255,122,0,0.55)";
            e.currentTarget.style.background = "rgba(25,25,25,0.70)";
            e.currentTarget.style.boxShadow = "0 0 18px rgba(255,122,0,0.16)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0px)";
            e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
            e.currentTarget.style.background = "rgba(20,20,20,0.60)";
            e.currentTarget.style.boxShadow = "none";
          }}
          title="Notification Center"
        >
          <Bell className="w-4 h-4 text-[#F5F5F5] group-hover:text-[#FF7A00] transition-colors" />
        </Link>

        {/* Settings */}
        <Link
          to="/settings"
          className="flex items-center justify-center w-[44px] h-[44px] rounded-[14px] transition-all duration-200 group"
          style={{ background: "rgba(20,20,20,0.60)", border: "1px solid rgba(255,255,255,0.1)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-1px)";
            e.currentTarget.style.border = "1px solid rgba(255,122,0,0.55)";
            e.currentTarget.style.background = "rgba(25,25,25,0.70)";
            e.currentTarget.style.boxShadow = "0 0 18px rgba(255,122,0,0.16)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0px)";
            e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
            e.currentTarget.style.background = "rgba(20,20,20,0.60)";
            e.currentTarget.style.boxShadow = "none";
          }}
          title="System Settings"
        >
          <Sliders className="w-4 h-4 text-[#F5F5F5] group-hover:text-[#FF7A00] transition-colors" />
        </Link>

        {/* User Profile */}
        <div 
          className="flex items-center gap-2 px-3 h-[44px] rounded-[14px] transition-all duration-200 group cursor-default"
          style={{ background: "rgba(20,20,20,0.60)", border: "1px solid rgba(255,255,255,0.1)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.border = "1px solid rgba(255,122,0,0.55)";
            e.currentTarget.style.background = "rgba(25,25,25,0.70)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
            e.currentTarget.style.background = "rgba(20,20,20,0.60)";
          }}
        >
          <ShieldCheck className="w-4 h-4 text-[#FF7A00]" />
          <div className="flex flex-col justify-center">
             <span className="font-[600] text-[13px] leading-tight text-[#F5F5F5]">{profile?.full_name || profile?.email || "Jayanth"}</span>
             <span className="text-[#A1A1AA] text-[9px] leading-tight font-[500]">Principal Admin</span>
          </div>
          <span 
            className="text-[9px] px-1.5 py-0.5 rounded font-[700] ml-1" 
            style={{ color: "#FF7A00", border: "1px solid rgba(255,122,0,0.3)", background: "rgba(255,122,0,0.05)" }}
          >
            {profile?.role || "ADMIN"}
          </span>
        </div>

        {/* Sign Out */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-4 h-[44px] rounded-[14px] transition-all duration-200 group cursor-pointer"
          style={{ background: "rgba(20,20,20,0.60)", border: "1px solid rgba(255,255,255,0.1)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "translateY(-1px)";
            e.currentTarget.style.border = "1px solid rgba(255,122,0,0.55)";
            e.currentTarget.style.background = "rgba(25,20,20,0.80)";
            e.currentTarget.style.boxShadow = "0 0 18px rgba(255,122,0,0.16)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "translateY(0px)";
            e.currentTarget.style.border = "1px solid rgba(255,255,255,0.1)";
            e.currentTarget.style.background = "rgba(20,20,20,0.60)";
            e.currentTarget.style.boxShadow = "none";
          }}
          title="Sign out of Supabase session"
        >
          <LogOut className="w-4 h-4 text-[#FF7A00] transition-colors" />
          <span className="text-[#F5F5F5] font-[600] text-[13px]">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
