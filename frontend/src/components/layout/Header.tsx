import React, { useState, useEffect } from "react";
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
  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  useEffect(() => {
    const handleToggle = (e: any) => {
      setSidebarExpanded(e.detail);
    };
    window.addEventListener("sidebar:toggle", handleToggle);
    return () => window.removeEventListener("sidebar:toggle", handleToggle);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header 
      className="pr-4 py-3 sticky top-0 z-30 flex items-center justify-between transition-all duration-300 ease-in-out"
      style={{
        paddingLeft: "var(--sidebar-offset)",
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
        {!sidebarExpanded && (
          <div 
            className="flex items-center gap-3 px-3.5 h-[46px] rounded-[14px] transition-all duration-300 select-none"
            style={{
              background: "rgba(20,20,20,0.55)",
              border: "1px solid rgba(255,122,0,0.22)",
              boxShadow: "0 0 16px rgba(255,122,0,0.08)",
            }}
          >
            <img 
              src="/oris-badge.png" 
              alt="ORIS" 
              className="h-8 w-8 object-contain drop-shadow-[0_0_8px_rgba(255,122,0,0.4)]" 
            />
            <div className="flex flex-col justify-center">
              <div className="font-[800] text-[20px] leading-tight flex items-center gap-1.5 tracking-wider">
                <span className="text-[#F5F5F5] font-black">ORIS</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#FF7A00] animate-pulse"></span>
              </div>
              <div className="text-[#9A9A9A] text-[9.5px] font-[500] leading-none uppercase tracking-wide mt-0.5 whitespace-nowrap">
                Oil Field Risk & Intelligence System
              </div>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT SIDE */}
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

      </div>
    </header>
  );
};
