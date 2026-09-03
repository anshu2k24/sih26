import React, { useState, useEffect } from "react";
import {
  fetchNotificationFeed,
  markNotificationReadApi,
  markAllNotificationsReadApi,
  fetchNotificationPreferences,
  updateNotificationPreferencesApi,
  fetchNotificationDeliveries,
  evaluateEscalationsApi,
} from "../services/api";
import {
  Bell,
  Mail,
  RefreshCw,
  CheckCheck,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Send,
  Clock,
  ShieldAlert,
} from "lucide-react";

export const NotificationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"FEED" | "DELIVERIES" | "PREFERENCES">("FEED");
  const [loading, setLoading] = useState<boolean>(true);

  // Feed state
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  // Deliveries state
  const [deliveries, setDeliveries] = useState<any[]>([]);

  // Preferences state
  const [preferences, setPreferences] = useState<Record<string, boolean>>({
    email_enabled: true,
    critical_alerts: true,
    high_alerts: true,
    medium_alerts: false,
    historical_alerts: false,
    system_notifications: true,
    report_notifications: false,
  });
  const [prefSaving, setPrefSaving] = useState<boolean>(false);
  const [prefSavedMsg, setPrefSavedMsg] = useState<string | null>(null);

  // Escalation state
  const [evaluatingEscalations, setEvaluatingEscalations] = useState<boolean>(false);
  const [escalatedResult, setEscalatedResult] = useState<any | null>(null);

  const loadFeed = async () => {
    setLoading(true);
    const data = await fetchNotificationFeed();
    if (data) {
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    }
    setLoading(false);
  };

  const loadDeliveries = async () => {
    setLoading(true);
    const data = await fetchNotificationDeliveries();
    if (data) {
      setDeliveries(data.deliveries || []);
    }
    setLoading(false);
  };

  const loadPreferences = async () => {
    const data = await fetchNotificationPreferences();
    if (data && data.preferences) {
      setPreferences(data.preferences);
    }
  };

  useEffect(() => {
    loadFeed();
    loadPreferences();
  }, []);

  const handleTabChange = (tab: "FEED" | "DELIVERIES" | "PREFERENCES") => {
    setActiveTab(tab);
    if (tab === "FEED") loadFeed();
    if (tab === "DELIVERIES") loadDeliveries();
  };

  const handleMarkRead = async (id: string) => {
    await markNotificationReadApi(id);
    loadFeed();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsReadApi();
    loadFeed();
  };

  const handlePrefToggle = (key: string) => {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSavePreferences = async () => {
    setPrefSaving(true);
    setPrefSavedMsg(null);
    const res = await updateNotificationPreferencesApi(preferences);
    setPrefSaving(false);
    if (res) {
      setPrefSavedMsg("Notification preferences updated successfully.");
      setTimeout(() => setPrefSavedMsg(null), 3000);
    }
  };

  const handleEvaluateEscalation = async () => {
    setEvaluatingEscalations(true);
    setEscalatedResult(null);
    const res = await evaluateEscalationsApi(30);
    setEvaluatingEscalations(false);
    if (res) {
      setEscalatedResult(res);
      loadFeed();
    }
  };

  return (
    <div 
      className="font-mono min-h-screen text-slate-300 relative overflow-hidden pb-12"
      style={{ 
        backgroundColor: "#030303",
        backgroundImage: "radial-gradient(circle at center, rgba(3, 3, 3, 0.85) 0%, rgba(3, 3, 3, 0.98) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        fontFamily: "'Space Grotesk', 'Inter', monospace" 
      }}
    >
      {/* Ambient Background Glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full opacity-[0.10] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full opacity-[0.08] blur-[180px] pointer-events-none" style={{ background: "radial-gradient(circle, #FFB000 0%, transparent 70%)" }}></div>
      <div className="absolute top-[30%] right-[10%] w-[30%] h-[30%] rounded-full opacity-[0.05] blur-[120px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF5000 0%, transparent 70%)" }}></div>

      <div className="max-w-6xl mx-auto space-y-6 pt-6 relative z-10">
        {/* Header Banner */}
        <div className="relative z-10 bg-[#0a0a0a]/70 backdrop-blur-md rounded-[16px] p-6 shadow-[0_0_20px_rgba(255,122,0,0.05)] flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex flex-col md:flex-row gap-5 md:items-center">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-[20px] md:text-[22px] font-bold text-white uppercase tracking-wider">
                  NOTIFICATION CENTER & EMAIL DISPATCH LOG
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded border border-[#FF7A00]/30 bg-[#1a1005]/80 text-[#FF7A00] font-bold flex items-center gap-1.5">
                  <Mail className="w-3 h-3" /> RESEND INTEGRATED
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0 mt-2 md:mt-0">
            <button
              onClick={handleEvaluateEscalation}
              disabled={evaluatingEscalations}
              className="bg-[#1a1005]/80 hover:bg-[#251508]/90 text-[#FF7A00] border border-[#FF7A00]/60 hover:border-[#FF7A00] hover:shadow-[0_0_15px_rgba(255,122,0,0.25)] hover:-translate-y-0.5 px-4 py-2.5 rounded-[10px] text-[12px] font-bold transition-all duration-200 flex items-center gap-2"
            >
              <ShieldAlert className={`w-4 h-4 ${evaluatingEscalations ? "animate-spin" : ""}`} />
              {evaluatingEscalations ? "CHECKING SLA..." : "EVALUATE SLA ESCALATIONS"}
            </button>
            <button
              onClick={() => handleTabChange(activeTab)}
              className="bg-[#0a0a0a]/80 hover:bg-[#151515] hover:border-[#FF7A00]/50 hover:shadow-[0_0_10px_rgba(255,122,0,0.1)] text-slate-300 hover:text-white text-[12px] font-bold px-4 py-2.5 rounded-[10px] border border-slate-700 transition-all duration-200 flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> REFRESH
            </button>
          </div>
        </div>

        {/* Escalation Result Banner */}
        {escalatedResult && (
          <div className="bg-[#1a1005]/80 backdrop-blur-md border border-[#FF7A00]/40 rounded-[14px] p-4 text-[13px] space-y-1 relative z-10 shadow-[0_0_15px_rgba(255,122,0,0.1)]">
            <span className="font-bold text-[#FF7A00] flex items-center gap-2 text-[14px]">
              <AlertTriangle className="w-4 h-4" /> SLA ESCALATION EVALUATION COMPLETE
            </span>
            <p className="text-slate-300 mt-1.5 ml-6">
              Checked unacknowledged alerts older than {escalatedResult.timeout_minutes} minutes.
              Escalations triggered: <strong className="text-white ml-1">{escalatedResult.escalated?.length || 0}</strong>
            </p>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center gap-4 text-[12px] font-bold relative z-10 overflow-x-auto hide-scrollbar pt-2">
          <button
            onClick={() => handleTabChange("FEED")}
            className={`px-5 py-2.5 rounded-[10px] border transition-all duration-200 flex items-center gap-2.5 shrink-0 ${
              activeTab === "FEED"
                ? "bg-[#FF7A00]/15 text-white border-[#FF7A00] shadow-[0_0_15px_rgba(255,122,0,0.25)]"
                : "bg-[#0a0a0a]/60 text-slate-400 border-slate-800 hover:border-[#FF7A00]/50 hover:text-white hover:shadow-[0_0_10px_rgba(255,122,0,0.1)]"
            }`}
          >
            <Bell className={`w-4 h-4 ${activeTab === "FEED" ? "text-[#FF7A00]" : ""}`} />
            <span className="tracking-wider">IN-APP NOTIFICATIONS</span>
            {unreadCount > 0 && (
              <span className="bg-[#FF7A00] text-white text-[10px] px-2 py-0.5 rounded-full font-bold ml-1">
                {unreadCount}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabChange("DELIVERIES")}
            className={`px-5 py-2.5 rounded-[10px] border transition-all duration-200 flex items-center gap-2.5 shrink-0 ${
              activeTab === "DELIVERIES"
                ? "bg-[#FF7A00]/15 text-white border-[#FF7A00] shadow-[0_0_15px_rgba(255,122,0,0.25)]"
                : "bg-[#0a0a0a]/60 text-slate-400 border-slate-800 hover:border-[#FF7A00]/50 hover:text-white hover:shadow-[0_0_10px_rgba(255,122,0,0.1)]"
            }`}
          >
            <Send className={`w-4 h-4 ${activeTab === "DELIVERIES" ? "text-[#FF7A00]" : ""}`} />
            <span className="tracking-wider">RESEND EMAIL DISPATCH LOG</span>
          </button>

          <button
            onClick={() => handleTabChange("PREFERENCES")}
            className={`px-5 py-2.5 rounded-[10px] border transition-all duration-200 flex items-center gap-2.5 shrink-0 ${
              activeTab === "PREFERENCES"
                ? "bg-[#FF7A00]/15 text-white border-[#FF7A00] shadow-[0_0_15px_rgba(255,122,0,0.25)]"
                : "bg-[#0a0a0a]/60 text-slate-400 border-slate-800 hover:border-[#FF7A00]/50 hover:text-white hover:shadow-[0_0_10px_rgba(255,122,0,0.1)]"
            }`}
          >
            <Sliders className={`w-4 h-4 ${activeTab === "PREFERENCES" ? "text-[#FF7A00]" : ""}`} />
            <span className="tracking-wider">DELIVERY PREFERENCES</span>
          </button>
        </div>

        {/* Thin Horizontal Divider */}
        <div className="h-px w-full bg-gradient-to-r from-[#FF7A00]/30 via-slate-800/80 to-transparent relative z-10 my-4" />

        {/* TAB 1: IN-APP FEED */}
        {activeTab === "FEED" && (
          <div className="space-y-5 relative z-10 mt-6">
            <div className="flex items-center justify-between pb-1">
              <span className="text-[13px] text-slate-400 font-mono tracking-wide">
                Showing {notifications.length} notification events ({unreadCount} unread)
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-[12px] bg-[#0a0a0a]/80 hover:bg-[#151515] hover:border-[#FF7A00] hover:shadow-[0_0_10px_rgba(255,122,0,0.2)] hover:-translate-y-0.5 text-white px-4 py-2 rounded-[10px] border border-[#FF7A00]/40 transition-all duration-200 flex items-center gap-2 font-bold tracking-wide"
                >
                  <CheckCheck className="w-4 h-4 text-[#FF7A00]" /> MARK ALL AS READ
                </button>
              )}
            </div>

            <div className="space-y-3.5">
              {notifications.length === 0 && !loading && (
                <div className="bg-[#0a0a0a]/70 backdrop-blur-md border border-slate-800 rounded-[14px] p-12 text-center text-[13px] text-slate-400">
                  No notification events recorded yet.
                </div>
              )}

              {notifications.map((evt) => {
                const severityMatch = evt.title.match(/\[(.*?)\]/);
                const severityText = severityMatch ? severityMatch[1] : "";
                const titleText = evt.title.replace(`[${severityText}]`, "").trim();
                
                let severityColor = "text-slate-400";
                let dotColor = "bg-slate-500";
                
                if (severityText === "HIGH" || severityText === "CRITICAL") {
                  severityColor = "text-[#FF7A00]";
                  dotColor = "bg-[#FF7A00]";
                } else if (severityText === "MEDIUM") {
                  severityColor = "text-amber-500";
                  dotColor = "bg-amber-500";
                } else if (severityText === "LOW") {
                  severityColor = "text-slate-400";
                  dotColor = "bg-slate-400";
                }

                return (
                  <div
                    key={evt.id}
                    className={`group relative border rounded-[14px] p-5 transition-all duration-200 flex flex-col md:flex-row justify-between gap-5 ${
                      evt.is_read
                        ? "bg-[#0a0a0a]/50 backdrop-blur-md border-slate-800/80 shadow-[0_0_10px_rgba(0,0,0,0.3)] hover:bg-[#0f0f0f]/80 hover:border-slate-700"
                        : "bg-[#0a0a0a]/75 backdrop-blur-md border-[#FF7A00]/30 shadow-[0_0_15px_rgba(0,0,0,0.5)] hover:bg-[#0f0f0f]/90 hover:border-[#FF7A00]/50 hover:shadow-[0_0_20px_rgba(255,122,0,0.15)] hover:-translate-y-[1px]"
                    }`}
                  >
                    <div className="space-y-3 flex-1 min-w-0">
                      <div className="flex items-center gap-2.5">
                        <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor} ${!evt.is_read ? "animate-pulse shadow-[0_0_8px_rgba(255,122,0,0.8)]" : ""}`} />
                        <strong className="text-[15px] font-bold text-white tracking-wide truncate">
                          {severityText && <span className={`${severityColor} mr-1.5`}>[{severityText}]</span>}
                          <span>{titleText || evt.title}</span>
                        </strong>
                      </div>
                      <p className="text-[13px] md:text-[14px] text-slate-300 font-mono leading-relaxed opacity-90 pr-2">
                        {evt.body}
                      </p>
                      <div className="text-[12px] text-slate-500 flex items-center gap-1.5 pt-1">
                        <Clock className="w-3.5 h-3.5 text-slate-600" /> {new Date(evt.created_at).toLocaleString()}
                      </div>
                    </div>

                    {!evt.is_read && (
                      <button
                        onClick={() => handleMarkRead(evt.id)}
                        className="self-start md:self-center shrink-0 bg-[#0a0a0a]/80 hover:bg-[#1a1005] text-slate-300 hover:text-white text-[11px] px-4 py-2.5 rounded-[10px] border border-[#FF7A00]/40 hover:border-[#FF7A00] hover:shadow-[0_0_10px_rgba(255,122,0,0.3)] font-bold transition-all duration-200 flex items-center gap-2.5 mt-2 md:mt-0 group/btn"
                      >
                        <span className="w-4 h-4 rounded-full border border-[#FF7A00]/80 flex items-center justify-center group-hover/btn:border-[#FF7A00] group-hover/btn:bg-[#FF7A00]/10 transition-colors">
                          <span className="w-1.5 h-1.5 bg-[#FF7A00] rounded-full"></span>
                        </span>
                        <span className="text-left leading-tight tracking-wider">Mark<br/>Read</span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 2: EMAIL DISPATCH LOG */}
        {activeTab === "DELIVERIES" && (
          <div className="bg-[#0a0a0a]/70 backdrop-blur-md border border-slate-800 rounded-[16px] overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.5)] space-y-4 relative z-10 mt-6">
            <div className="p-5 border-b border-slate-800/60 flex items-center justify-between text-[13px] font-bold text-slate-300">
              <span>Resend Email Dispatch Audit Log ({deliveries.length} records)</span>
              <span className="text-slate-500 font-mono">Gateway: Resend HTTP API</span>
            </div>

            <div className="overflow-x-auto pb-2">
              <table className="w-full text-left text-[13px] border-collapse whitespace-nowrap">
                <thead>
                  <tr className="bg-black/40 text-slate-400 border-b border-slate-800/80 font-bold uppercase tracking-wider">
                    <th className="p-4 px-5">DELIVERY ID</th>
                    <th className="p-4 px-5">RECIPIENT EMAIL</th>
                    <th className="p-4 px-5">SUBJECT</th>
                    <th className="p-4 px-5">STATUS</th>
                    <th className="p-4 px-5">ATTEMPTS</th>
                    <th className="p-4 px-5">DISPATCH TIMESTAMP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {deliveries.length === 0 && !loading && (
                    <tr>
                      <td colSpan={6} className="p-10 text-center text-slate-500 text-[13px]">
                        No email dispatches recorded yet. HIGH and CRITICAL alerts will generate dispatches.
                      </td>
                    </tr>
                  )}
                  {deliveries.map((del) => (
                    <tr key={del.id} className="hover:bg-[#151515]/80 transition-colors group">
                      <td className="p-4 px-5 font-bold text-[#FF7A00]/80 group-hover:text-[#FF7A00] transition-colors">{del.id}</td>
                      <td className="p-4 px-5 text-slate-300">{del.recipient_email}</td>
                      <td className="p-4 px-5 text-white font-bold">{del.subject}</td>
                      <td className="p-4 px-5">
                        <span
                          className={`px-2.5 py-1 rounded text-[11px] font-bold border tracking-wider ${
                            del.status === "SENT"
                              ? "bg-emerald-950/30 text-emerald-500 border-emerald-500/30"
                              : "bg-rose-950/30 text-rose-500 border-rose-500/30"
                          }`}
                        >
                          {del.status}
                        </span>
                      </td>
                      <td className="p-4 px-5 text-slate-400">{del.attempt_count || 1}</td>
                      <td className="p-4 px-5 text-slate-400 flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 opacity-50" />
                        {new Date(del.created_at || del.last_attempted).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: PREFERENCES */}
        {activeTab === "PREFERENCES" && (
          <div className="bg-[#0a0a0a]/70 backdrop-blur-md border border-slate-800 rounded-[16px] p-7 shadow-[0_0_15px_rgba(0,0,0,0.5)] space-y-6 max-w-3xl relative z-10 mt-6">
            <div className="border-b border-slate-800/80 pb-4 flex items-center justify-between">
              <h2 className="text-[14px] font-bold text-white uppercase tracking-wider">
                Notification Delivery Policies & Thresholds
              </h2>
              {prefSavedMsg && (
                <span className="text-[13px] text-[#FF7A00] font-bold flex items-center gap-1.5 bg-[#FF7A00]/10 px-3 py-1 rounded border border-[#FF7A00]/30 shadow-[0_0_10px_rgba(255,122,0,0.15)]">
                  <CheckCircle2 className="w-4 h-4" /> {prefSavedMsg}
                </span>
              )}
            </div>

            <div className="space-y-3 text-[13px]">
              {Object.entries({
                email_enabled: ["Global Resend Email Dispatch", "Master toggle for outbound emails"],
                critical_alerts: ["CRITICAL Severity Alerts", "Immediate email dispatch & in-app banner"],
                high_alerts: ["HIGH Severity Alerts", "Outbound email to Drilling Superintendent"],
                medium_alerts: ["MEDIUM Severity Alerts", "Include in-app notification for medium events"],
                historical_alerts: ["Historical Proximity Alerts", "In-app alerts for offset historical correlation"],
                system_notifications: ["System Maintenance & Health", "Server health & ML readiness gate updates"],
                report_notifications: ["Daily Drilling Reports", "Notify when new DDR reports are generated"],
              }).map(([key, [label, desc]]) => (
                <div key={key} className="flex items-center justify-between p-4 px-5 bg-black/40 rounded-[12px] border border-slate-800/60 hover:border-[#FF7A00]/30 hover:bg-black/60 transition-all duration-200">
                  <div>
                    <strong className="text-white block font-mono text-[14px] tracking-wide">{label}</strong>
                    <span className="text-slate-400 text-[12px] font-sans mt-1 block opacity-90">{desc}</span>
                  </div>

                  <button
                    onClick={() => handlePrefToggle(key)}
                    className={`w-[46px] h-[24px] rounded-full p-1 transition-all duration-300 ${
                      preferences[key] ? "bg-[#FF7A00] justify-end shadow-[0_0_10px_rgba(255,122,0,0.4)]" : "bg-slate-700 justify-start"
                    } flex items-center`}
                  >
                    <span className="w-4 h-4 rounded-full bg-white shadow-md" />
                  </button>
                </div>
              ))}
            </div>

            <div className="pt-5 border-t border-slate-800/80 flex justify-end">
              <button
                onClick={handleSavePreferences}
                disabled={prefSaving}
                className="bg-[#FF7A00] hover:bg-[#ff8f24] disabled:opacity-50 text-black font-bold px-7 py-3 rounded-[10px] text-[13px] transition-all duration-200 uppercase tracking-widest shadow-[0_0_15px_rgba(255,122,0,0.3)] hover:shadow-[0_0_20px_rgba(255,122,0,0.5)] hover:-translate-y-[1px]"
              >
                {prefSaving ? "SAVING..." : "SAVE PREFERENCES"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
