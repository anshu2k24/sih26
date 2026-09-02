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

      {/* User Profile & Logout Section at Bottom */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2.5 px-1">
              <div className="w-8 h-8 rounded-full bg-slate-900 border border-slate-700 text-slate-300 flex items-center justify-center font-bold font-mono text-xs">
                {profile?.full_name ? profile.full_name.charAt(0).toUpperCase() : <User className="w-4 h-4" />}
              </div>
              <div className="overflow-hidden flex-1">
                <span className="text-xs font-bold text-white font-mono block truncate">
                  {profile?.full_name || profile?.email || "Operator"}
                </span>
                <span className="text-[10px] text-orange-400 font-mono flex items-center gap-1 font-semibold">
                  <Shield className="w-3 h-3 text-orange-400" />
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
