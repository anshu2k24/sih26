import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Activity,
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
    { to: "/dashboard", label: "COMMAND CENTER", icon: LayoutDashboard },
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
      className={`bg-slate-900 border-r border-slate-800 flex flex-col justify-between transition-all duration-300 z-40 sticky top-0 h-screen ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Top Brand Banner */}
      <div>
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          {!collapsed ? (
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
                <Activity className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-tight text-white font-mono leading-none">
                  eRTMAC-NWIS
                </h1>
                <span className="text-[10px] text-amber-400 font-mono font-medium block mt-1">
                  Volve Operations
                </span>
              </div>
            </div>
          ) : (
            <div className="p-2 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30 mx-auto">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
          )}

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
        <nav className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)] custom-scrollbar">
          {navLinks.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl font-mono text-xs font-bold transition-all ${
                    isActive
                      ? "bg-blue-600 text-white shadow-lg shadow-blue-500/25 border border-blue-400/40"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                  } ${collapsed ? "justify-center px-0" : ""}`
                }
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* User Profile & Logout Section at Bottom */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 px-1">
              <div className="w-8 h-8 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-400 flex items-center justify-center font-bold font-mono text-xs">
                {profile?.full_name ? profile.full_name.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
              </div>
              <div className="overflow-hidden flex-1">
                <span className="text-xs font-bold text-white font-mono block truncate">
                  {profile?.full_name || profile?.email || "Operator"}
                </span>
                <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1 font-semibold">
                  <Shield className="w-3 h-3 text-cyan-400" />
                  {profile?.role || "ADMIN"}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-500/30 rounded-xl py-2 font-mono text-xs font-bold transition-all shadow-sm"
            >
              <LogOut className="w-3.5 h-3.5" />
              SIGN OUT
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center justify-center p-2 text-rose-400 hover:bg-rose-950/60 rounded-xl transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}
      </div>
    </aside>
  );
};
