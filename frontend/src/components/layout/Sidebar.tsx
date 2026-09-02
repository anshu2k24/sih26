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
  BookOpen,
  Folder,
  FileSpreadsheet,
  LogOut,
  ChevronLeft,
  ChevronRight,
  User,
  Shield
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
    { to: "/knowledge", label: "KNOWLEDGE BASE", icon: BookOpen },
    { to: "/documents", label: "DOCUMENTS", icon: Folder },
    { to: "/notes", label: "OCR", icon: FileText },
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
      className={`bg-[#050608]/90 backdrop-blur-xl border-r border-[#FF7A00]/10 flex flex-col justify-between transition-all duration-300 z-40 sticky top-0 h-screen ${
        collapsed ? "w-[70px]" : "w-64"
      }`}
    >
      {/* Top Brand Banner */}
      <div>
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className={`p-2 bg-orange-600/20 text-orange-400 rounded-xl border border-orange-500/30 ${collapsed ? "mx-auto" : ""}`}>
            <Cylinder className="w-5 h-5 animate-pulse" strokeWidth={1.5} />
          </div>

          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Link List */}
        <nav className="group/nav p-3 space-y-2 overflow-y-auto max-h-[calc(100vh-140px)] custom-scrollbar">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `group flex items-center gap-3 px-3 py-3 rounded-[12px] font-mono text-xs transition-all duration-300 border ${
                    isActive
                      ? "font-bold scale-[1.02]"
                      : "text-slate-500 border-transparent hover:text-[#FF7A00] hover:bg-[#FF7A00]/5 hover:border-[#FF7A00]/20 hover:shadow-[0_0_10px_rgba(255,122,0,0.1)] hover:scale-[1.02] font-medium"
                  } ${collapsed ? "justify-center w-12 h-12 mx-auto p-0" : ""}`
                }
                style={
                  ({ isActive }) =>
                    isActive
                      ? {
                          color: "#FF7A00",
                          background: "rgba(255,122,0,0.08)",
                          border: "1px solid rgba(255,122,0,0.3)",
                          boxShadow: "0 0 16px rgba(255,122,0,0.1)",
                        }
                      : {}
                }
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-[18px] h-[18px] shrink-0 transition-colors duration-200" strokeWidth={1.5} />
                {!collapsed && <span className="tracking-wide">{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

    </aside>
  );
};
