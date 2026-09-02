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
  Search
} from "lucide-react";
import { useActiveWell } from "../../context/ActiveWellContext";
import { useAuth } from "../../context/AuthContext";

export const Sidebar: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const { profile, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState<boolean>(false);

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
      className={`bg-[#050607] flex flex-col justify-between transition-all duration-300 z-40 sticky top-0 h-screen font-['Space_Grotesk',sans-serif] ${
        collapsed ? "w-[80px]" : "w-[280px]"
      }`}
      style={{
        borderRight: "1px solid rgba(255,138,0,0.05)",
      }}
    >
      {/* Top Brand Banner */}
      <div className="flex flex-col h-full">
        <div className="p-[24px] border-b border-[rgba(255,255,255,0.05)] flex items-center justify-between">
          <div 
            className={`w-[44px] h-[44px] rounded-[12px] flex items-center justify-center border transition-all duration-300 ${collapsed ? "mx-auto" : ""}`}
            style={{ 
              background: "rgba(255, 138, 0, 0.08)", 
              borderColor: "rgba(255, 138, 0, 0.4)", 
              boxShadow: "0 0 20px rgba(255,138,0,0.15)" 
            }}
          >
            <Cylinder className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_8px_rgba(255,157,26,0.6)] animate-pulse" strokeWidth={1.5} />
          </div>

          {!collapsed && (
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="w-[32px] h-[32px] rounded-[8px] flex items-center justify-center text-[#9AA0A6] transition-all duration-200 hover:text-[#FF9D1A] hover:bg-[rgba(255,138,0,0.05)] hover:border hover:border-[rgba(255,138,0,0.3)] hover:shadow-[0_0_10px_rgba(255,138,0,0.1)] border border-transparent"
              title="Collapse sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
          {collapsed && (
            <div className="absolute -right-4 top-[32px] z-50">
              <button
                type="button"
                onClick={() => setCollapsed(false)}
                className="w-[28px] h-[28px] rounded-full flex items-center justify-center text-[#9AA0A6] bg-[#050607] border border-[rgba(255,138,0,0.3)] transition-all duration-200 hover:text-[#FF9D1A] hover:shadow-[0_0_10px_rgba(255,138,0,0.2)]"
                title="Expand sidebar"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Navigation Link List */}
        <nav className="flex-1 p-[16px] space-y-[12px] overflow-y-auto custom-scrollbar">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `group relative flex items-center justify-between px-[16px] py-[14px] rounded-[12px] transition-all duration-200 border ${
                    isActive
                      ? "border-[rgba(255,138,0,0.4)] bg-[rgba(255,138,0,0.08)] shadow-[0_0_20px_rgba(255,138,0,0.15)] text-[#FF9D1A]"
                      : "border-transparent text-[#9AA0A6] hover:border-[rgba(255,138,0,0.2)] hover:bg-[rgba(255,138,0,0.03)] hover:shadow-[0_0_15px_rgba(255,138,0,0.08)] hover:text-[#FF9D1A]"
                  } ${collapsed ? "justify-center px-[0] w-[44px] h-[44px] mx-auto" : ""}`
                }
                title={collapsed ? item.label : undefined}
              >
                {({ isActive }) => (
                  <>
                    {/* Active State Left Edge Accent */}
                    {isActive && (
                      <div className="absolute left-0 top-[15%] bottom-[15%] w-[4px] bg-[#FF9D1A] rounded-r-[4px] shadow-[0_0_10px_#FF9D1A]"></div>
                    )}
                    
                    <div className="flex items-center gap-[16px]">
                      <Icon 
                        className={`w-[20px] h-[20px] shrink-0 transition-colors duration-200 ${isActive ? 'drop-shadow-[0_0_8px_rgba(255,157,26,0.5)]' : 'group-hover:drop-shadow-[0_0_5px_rgba(255,157,26,0.3)]'}`} 
                        strokeWidth={1.5} 
                      />
                      {!collapsed && (
                        <span className={`text-[13px] tracking-wide ${isActive ? 'font-[700]' : 'font-[600]'}`}>
                          {item.label}
                        </span>
                      )}
                    </div>

                    {!collapsed && isActive && (
                      <ChevronRight className="w-4 h-4 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.5)]" />
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </aside>
  );
};
