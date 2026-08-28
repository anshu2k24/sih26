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
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              NOTIFICATION CENTER & EMAIL DISPATCH LOG
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 font-bold flex items-center gap-1">
              <Mail className="w-3 h-3" /> RESEND INTEGRATED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Server-side HTML email dispatches for HIGH and CRITICAL drilling alerts, SLA escalation policy evaluation, and in-app feed.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleEvaluateEscalation}
            disabled={evaluatingEscalations}
            className="bg-amber-950/80 hover:bg-amber-900 text-amber-400 border border-amber-500/30 px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
          >
            <ShieldAlert className={`w-3.5 h-3.5 ${evaluatingEscalations ? "animate-spin" : ""}`} />
            {evaluatingEscalations ? "CHECKING SLA..." : "EVALUATE SLA ESCALATIONS"}
          </button>
          <button
            onClick={() => handleTabChange(activeTab)}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
          </button>
        </div>
      </div>

      {/* Escalation Result Banner */}
      {escalatedResult && (
        <div className="bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 text-xs space-y-1">
          <span className="font-bold text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" /> SLA ESCALATION EVALUATION COMPLETE
          </span>
          <p className="text-slate-300">
            Checked unacknowledged alerts older than {escalatedResult.timeout_minutes} minutes.
            Escalations triggered: <strong className="text-white">{escalatedResult.escalated?.length || 0}</strong>
          </p>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 text-xs font-bold">
        <button
          onClick={() => handleTabChange("FEED")}
          className={`px-3.5 py-2 rounded-lg border transition-all flex items-center gap-2 ${
            activeTab === "FEED"
              ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/20"
              : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>IN-APP NOTIFICATIONS</span>
          {unreadCount > 0 && (
            <span className="bg-rose-600 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
              {unreadCount}
            </span>
          )}
        </button>

        <button
          onClick={() => handleTabChange("DELIVERIES")}
          className={`px-3.5 py-2 rounded-lg border transition-all flex items-center gap-2 ${
            activeTab === "DELIVERIES"
              ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/20"
              : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
          }`}
        >
          <Send className="w-4 h-4" />
          <span>RESEND EMAIL DISPATCH LOG</span>
        </button>

        <button
          onClick={() => handleTabChange("PREFERENCES")}
          className={`px-3.5 py-2 rounded-lg border transition-all flex items-center gap-2 ${
            activeTab === "PREFERENCES"
              ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/20"
              : "bg-slate-900 text-slate-400 border-slate-800 hover:text-white"
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>DELIVERY PREFERENCES</span>
        </button>
      </div>

      {/* TAB 1: IN-APP FEED */}
      {activeTab === "FEED" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              Showing {notifications.length} notification events ({unreadCount} unread)
            </span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5 font-bold"
              >
                <CheckCheck className="w-4 h-4 text-emerald-400" /> MARK ALL AS READ
              </button>
            )}
          </div>

          <div className="space-y-2">
            {notifications.length === 0 && !loading && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-xs text-slate-400">
                No notification events recorded yet.
              </div>
            )}

            {notifications.map((evt) => (
              <div
                key={evt.id}
                className={`border rounded-xl p-4 shadow-lg transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                  evt.is_read
                    ? "bg-slate-900/60 border-slate-850 text-slate-400"
                    : "bg-slate-900 border-indigo-500/40 text-white"
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {!evt.is_read && (
                      <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block animate-pulse" />
                    )}
                    <strong className="text-sm font-bold">{evt.title}</strong>
                  </div>
                  <p className="text-xs text-slate-300 font-sans">{evt.body}</p>
                  <span className="text-[10px] text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {new Date(evt.created_at).toLocaleString()}
                  </span>
                </div>

                {!evt.is_read && (
                  <button
                    onClick={() => handleMarkRead(evt.id)}
                    className="self-start md:self-center bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-2.5 py-1 rounded border border-slate-700 font-bold transition-all flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Mark Read
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: EMAIL DISPATCH LOG */}
      {activeTab === "DELIVERIES" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl space-y-4">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-slate-300">
            <span>Resend Email Dispatch Audit Log ({deliveries.length} records)</span>
            <span className="text-slate-500">Gateway: Resend HTTP API</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold">
                  <th className="p-3.5">DELIVERY ID</th>
                  <th className="p-3.5">RECIPIENT EMAIL</th>
                  <th className="p-3.5">SUBJECT</th>
                  <th className="p-3.5">STATUS</th>
                  <th className="p-3.5">ATTEMPTS</th>
                  <th className="p-3.5">DISPATCH TIMESTAMP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {deliveries.length === 0 && !loading && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No email dispatches recorded yet. HIGH and CRITICAL alerts will generate dispatches.
                    </td>
                  </tr>
                )}
                {deliveries.map((del) => (
                  <tr key={del.id} className="hover:bg-slate-850/60 transition-all">
                    <td className="p-3.5 font-bold text-indigo-400">{del.id}</td>
                    <td className="p-3.5 text-slate-200">{del.recipient_email}</td>
                    <td className="p-3.5 text-white font-bold">{del.subject}</td>
                    <td className="p-3.5">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          del.status === "SENT"
                            ? "bg-emerald-950 text-emerald-400 border-emerald-500/30"
                            : "bg-rose-950 text-rose-400 border-rose-500/30"
                        }`}
                      >
                        {del.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-400">{del.attempt_count || 1}</td>
                    <td className="p-3.5 text-slate-400">{new Date(del.created_at || del.last_attempted).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: PREFERENCES */}
      {activeTab === "PREFERENCES" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6 max-w-2xl">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Notification Delivery Policies & Thresholds
            </h2>
            {prefSavedMsg && (
              <span className="text-xs text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {prefSavedMsg}
              </span>
            )}
          </div>

          <div className="space-y-4 text-xs">
            {Object.entries({
              email_enabled: ["Global Resend Email Dispatch", "Master toggle for outbound emails"],
              critical_alerts: ["CRITICAL Severity Alerts", "Immediate email dispatch & in-app banner"],
              high_alerts: ["HIGH Severity Alerts", "Outbound email to Drilling Superintendent"],
              medium_alerts: ["MEDIUM Severity Alerts", "Include in-app notification for medium events"],
              historical_alerts: ["Historical Proximity Alerts", "In-app alerts for offset historical correlation"],
              system_notifications: ["System Maintenance & Health", "Server health & ML readiness gate updates"],
              report_notifications: ["Daily Drilling Reports", "Notify when new DDR reports are generated"],
            }).map(([key, [label, desc]]) => (
              <div key={key} className="flex items-center justify-between p-3.5 bg-slate-950 rounded-lg border border-slate-800">
                <div>
                  <strong className="text-white block font-mono">{label}</strong>
                  <span className="text-slate-400 text-[11px] font-sans">{desc}</span>
                </div>

                <button
                  onClick={() => handlePrefToggle(key)}
                  className={`w-12 h-6 rounded-full p-1 transition-all ${
                    preferences[key] ? "bg-indigo-600 justify-end" : "bg-slate-800 justify-start"
                  } flex items-center`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-md" />
                </button>
              </div>
            ))}
          </div>

          <div className="pt-2 border-t border-slate-800 flex justify-end">
            <button
              onClick={handleSavePreferences}
              disabled={prefSaving}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold px-5 py-2 rounded-lg text-xs transition-all uppercase tracking-wider shadow-lg shadow-indigo-500/20"
            >
              {prefSaving ? "SAVING..." : "SAVE PREFERENCES"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
