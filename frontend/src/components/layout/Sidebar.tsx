import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Cylinder,
  ShieldAlert,
  Database,
  Map,
  LayoutDashboard,
  AlertCircle,
  FileText,
  Radio,
  ShieldCheck,
  Sliders,
  BarChart3,
  Folder,
  FileSpreadsheet,
  LogOut,
  ChevronLeft,
  ChevronRight,
  User,
  Shield,
  Search,
  Menu
} from "lucide-react";
import { useActiveWell } from "../../context/ActiveWellContext";
import { useAuth } from "../../context/AuthContext";

export const Sidebar: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState<boolean>(false);

  const navLinks = [
    { to: "/dashboard", label: "DASHBOARD", icon: LayoutDashboard },
    { to: "/live", label: "LIVE TELEMETRY", icon: Radio },
    { to: "/map", label: "GEOSPATIAL MAP", icon: Map },
    { to: "/wells", label: "WELLS", icon: Database },
    { to: `/wells/${encodeURIComponent(selectedWell)}`, label: "INTELLIGENCE", icon: FileText },
    { to: "/documents", label: "DOCUMENTS", icon: Folder },
    { to: "/rag", label: "KNOWLEDGE SEARCH", icon: Search },
    { to: "/alerts", label: "ALERTS", icon: ShieldAlert },
    { to: "/risk", label: "ML RISK", icon: AlertCircle },
    { to: "/audit", label: "AUDIT LOGS", icon: ShieldCheck },
    { to: "/reports", label: "REPORTS", icon: FileSpreadsheet },
    { to: "/analytics", label: "ANALYTICS", icon: BarChart3 },
    { to: "/settings", label: "SETTINGS", icon: Sliders },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <aside
      className={`fixed left-4 top-1/2 -translate-y-1/2 z-50 flex flex-col py-6 transition-all duration-300 ease-in-out max-h-[90vh] overflow-hidden ${
        expanded ? "w-[280px] rounded-[24px] px-4" : "w-[72px] rounded-[32px] px-2 items-center"
      }`}
      style={{
        background: "rgba(10, 12, 16, 0.4)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        boxShadow: "0 20px 50px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,255,255,0.02)"
      }}
    >
      {/* Top Toggle / Brand Area */}
      <div className={`flex items-center mb-6 w-full ${expanded ? "justify-between px-2" : "justify-center"}`}>
        <div className={`flex flex-col justify-center overflow-hidden whitespace-nowrap transition-all duration-300 ${expanded ? 'w-[180px] opacity-100 px-2' : 'w-0 opacity-0'}`}>
          <div className="font-[700] text-[16px] leading-tight flex">
            <span className="text-[#F5F5F5]">eRTMAC</span>
            <span className="text-[#FF7A00]">-NWIS</span>
          </div>
          <div className="text-[#9A9A9A] text-[9px] font-[400] leading-none lowercase mt-0.5">
            Nearbywells intelligence system
          </div>
        </div>
        <button
          onClick={() => {
            const newVal = !expanded;
            setExpanded(newVal);
            window.dispatchEvent(new CustomEvent("sidebar:toggle", { detail: newVal }));
          }}
          className="w-10 h-10 rounded-full flex items-center justify-center text-[#9AA0A6] hover:text-[#FF9D1A] hover:bg-[rgba(255,138,0,0.1)] transition-all"
        >
          <Menu className="w-5 h-5 text-[#FF7A00]" />
        </button>
      </div>

      {/* Navigation Link List */}
      <nav className={`flex flex-col space-y-2 overflow-y-auto custom-scrollbar no-scrollbar w-full ${expanded ? "" : "items-center"}`}>
        {navLinks.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                `group relative flex items-center transition-all duration-300 ${
                  expanded 
                    ? `w-full px-4 py-3 rounded-[12px] ${isActive ? "bg-[rgba(255,138,0,0.1)] text-[#FF9D1A] shadow-[inset_3px_0_0_#FF9D1A]" : "text-[#9AA0A6] hover:text-[#FF9D1A] hover:bg-[rgba(255,138,0,0.05)]"}`
                    : `justify-center w-12 h-12 rounded-[16px] ${isActive ? "bg-[rgba(255,138,0,0.1)] text-[#FF9D1A] shadow-[inset_2px_0_0_#FF9D1A,0_0_15px_rgba(255,138,0,0.15)]" : "text-[#9AA0A6] hover:text-[#FF9D1A] hover:bg-[rgba(255,138,0,0.05)]"}`
                }`
              }
              title={!expanded ? item.label : undefined}
            >
              {({ isActive }) => (
                <>
                  <Icon 
                    className={`w-5 h-5 shrink-0 transition-all duration-300 ${
                      isActive ? 'drop-shadow-[0_0_8px_rgba(255,157,26,0.6)]' : ''
                    } ${!expanded && isActive ? 'scale-110' : (!expanded ? 'group-hover:scale-110' : '')}`} 
                    strokeWidth={1.5} 
                  />
                  {expanded && (
                    <span className={`ml-4 text-[13px] tracking-wide ${isActive ? 'font-[700]' : 'font-[600]'}`}>
                      {item.label}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Actions */}
      <div className={`mt-auto pt-4 w-full flex ${expanded ? "px-4" : "justify-center"}`}>
        <button
          onClick={handleLogout}
          className={`group relative flex items-center transition-all duration-300 text-[#9AA0A6] hover:text-[#FF3B3B] hover:bg-[rgba(255,59,59,0.05)] ${
            expanded ? "w-full px-4 py-3 rounded-[12px]" : "justify-center w-12 h-12 rounded-[16px]"
          }`}
          title={!expanded ? "Sign Out" : undefined}
        >
          <LogOut 
            className={`w-5 h-5 shrink-0 transition-all duration-300 ${!expanded ? 'group-hover:scale-110' : ''}`} 
            strokeWidth={1.5} 
          />
          {expanded && (
            <span className="ml-4 text-[13px] tracking-wide font-[600]">
              Sign Out
            </span>
          )}
        </button>
      </div>
    </aside>
  );
};
