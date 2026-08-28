import React, { useState, useEffect } from "react";
import { fetchSystemSettings, updateSystemSettingsApi, deleteSystemSettingsApi } from "../services/api";
import type { SystemSettings } from "../types/api";
import { useAuth } from "../context/AuthContext";
import {
  Sliders,
  Mail,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  Database,
  UserCheck,
  BellRing,
  Shield,
} from "lucide-react";

export const SettingsPage: React.FC = () => {
  const { profile } = useAuth();
  const [settings, setSettings] = useState<SystemSettings | null>(null);

  // Form State
  const [emailInput, setEmailInput] = useState<string>("");
  const [radiusInput, setRadiusInput] = useState<number>(5.0);
  const [depthInput, setDepthInput] = useState<number>(50.0);

  // Alert Severity & Channel Preferences
  const [emailEnabled, setEmailEnabled] = useState<boolean>(true);
  const [criticalAlerts, setCriticalAlerts] = useState<boolean>(true);
  const [highAlerts, setHighAlerts] = useState<boolean>(true);
  const [mediumAlerts, setMediumAlerts] = useState<boolean>(false);
  const [historicalAlerts, setHistoricalAlerts] = useState<boolean>(false);
  const [systemNotifications, setSystemNotifications] = useState<boolean>(true);
  const [reportNotifications, setReportNotifications] = useState<boolean>(false);

  // Action Status States
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const res = await fetchSystemSettings();
      if (res) {
        setSettings(res);
        setEmailInput(res.notification_recipient_email || profile?.email || "");
        setRadiusInput(res.search_radius_km_default ?? 5.0);
        setDepthInput(res.depth_window_m_default ?? 50.0);

        setEmailEnabled(res.email_enabled ?? true);
        setCriticalAlerts(res.critical_alerts ?? true);
        setHighAlerts(res.high_alerts ?? true);
        setMediumAlerts(res.medium_alerts ?? false);
        setHistoricalAlerts(res.historical_alerts ?? false);
        setSystemNotifications(res.system_notifications ?? true);
        setReportNotifications(res.report_notifications ?? false);
      }
    } catch (err) {
      console.error("Failed to load user settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, [profile]);

  // ── CREATE / UPDATE (Save to Supabase) ──────────────────────────────────
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(null);
    setSaveError(null);

    if (!emailInput.trim()) {
      setSaveError("Notification recipient email is required.");
      return;
    }

    setSaving(true);
    const updated = await updateSystemSettingsApi({
      notification_recipient_email: emailInput.trim(),
      search_radius_km_default: Number(radiusInput),
      depth_window_m_default: Number(depthInput),
      email_enabled: emailEnabled,
      critical_alerts: criticalAlerts,
      high_alerts: highAlerts,
      medium_alerts: mediumAlerts,
      historical_alerts: historicalAlerts,
      system_notifications: systemNotifications,
      report_notifications: reportNotifications,
    });
    setSaving(false);

    if (updated) {
      setSettings(updated);
      setSaveSuccess(
        `Your personal settings have been successfully saved in Supabase for ${profile?.email || emailInput}!`
      );
    } else {
      setSaveError("Failed to save settings to Supabase. Please check your network connection.");
    }
  };

  // ── DELETE / RESET (Reset to default in Supabase) ─────────────────────────
  const handleReset = async () => {
    if (!window.confirm("Are you sure you want to reset your personal settings to default values?")) {
      return;
    }

    setSaveSuccess(null);
    setSaveError(null);
    setResetting(true);

    const res = await deleteSystemSettingsApi();
    setResetting(false);

    if (res) {
      setSettings(res);
      setEmailInput(profile?.email || "");
      setRadiusInput(5.0);
      setDepthInput(50.0);
      setEmailEnabled(true);
      setCriticalAlerts(true);
      setHighAlerts(true);
      setMediumAlerts(false);
      setHistoricalAlerts(false);
      setSystemNotifications(true);
      setReportNotifications(false);
      setSaveSuccess("Your configuration has been reset to default values in Supabase.");
    } else {
      setSaveError("Failed to reset settings in Supabase.");
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white uppercase tracking-wider">
                Operator Configuration & Personal Settings
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Per-user settings stored in Supabase PostgreSQL for individual alert delivery & correlation parameters.
              </p>
            </div>
          </div>
        </div>

        {/* User Identity Pill */}
        <div className="flex items-center gap-2.5 bg-slate-950 px-4 py-2 rounded-xl border border-slate-800 self-start md:self-auto">
          <UserCheck className="w-4 h-4 text-cyan-400" />
          <div className="text-xs">
            <div className="text-slate-300 font-bold">{profile?.full_name || profile?.email || "Operator"}</div>
            <div className="text-[10px] text-cyan-400">
              {profile?.email} • <span className="text-emerald-400 font-bold">{profile?.role}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Settings Edit Form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
              Supabase Cloud Settings (CRUD)
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-emerald-400 font-bold bg-emerald-950/60 px-3 py-1 rounded-lg border border-emerald-500/30 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              INDIVIDUAL USER ISOLATION
            </span>
          </div>
        </div>

        {saveSuccess && (
          <div className="flex items-start gap-3 bg-emerald-950/50 border border-emerald-500/40 rounded-xl p-4 text-xs text-emerald-300 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <span>{saveSuccess}</span>
          </div>
        )}

        {saveError && (
          <div className="flex items-start gap-3 bg-rose-950/50 border border-rose-500/40 rounded-xl p-4 text-xs text-rose-300 animate-in fade-in">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{saveError}</span>
          </div>
        )}

        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
            <span className="text-xs">Loading user settings from Supabase...</span>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-6">
            {/* Section 1: Email Target */}
            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-cyan-400" />
                <label className="text-xs text-slate-200 font-bold uppercase tracking-wider">
                  Personal Alert Dispatch Email
                </label>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                All drilling alerts, real-time offset events, and shift handovers destined for your account will be dispatched to this email address.
              </p>
              <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                placeholder="your.email@company.com"
                className="w-full max-w-lg bg-slate-900 text-cyan-300 border border-slate-700 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none focus:border-cyan-500 transition-all shadow-inner"
              />
            </div>

            {/* Section 2: Correlation Windows */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-2">
                <label className="block text-xs text-slate-300 font-bold uppercase tracking-wider">
                  Default Proximity Search Radius (km)
                </label>
                <p className="text-[10px] text-slate-500">
                  Search radius applied when querying offset historical wells.
                </p>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="100"
                  value={radiusInput}
                  onChange={(e) => setRadiusInput(parseFloat(e.target.value) || 5.0)}
                  className="w-full bg-slate-900 text-white border border-slate-700 rounded-xl px-4 py-2 text-sm font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-2">
                <label className="block text-xs text-slate-300 font-bold uppercase tracking-wider">
                  Default Depth Correlation Window (m)
                </label>
                <p className="text-[10px] text-slate-500">
                  Vertical depth search band (± MD) for finding matching historical DDR events.
                </p>
                <input
                  type="number"
                  step="5"
                  min="5"
                  max="500"
                  value={depthInput}
                  onChange={(e) => setDepthInput(parseFloat(e.target.value) || 50.0)}
                  className="w-full bg-slate-900 text-emerald-400 border border-slate-700 rounded-xl px-4 py-2 text-sm font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Section 3: Notification Filtering Matrix */}
            <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 space-y-4">
              <div className="flex items-center gap-2">
                <BellRing className="w-4 h-4 text-amber-400" />
                <label className="text-xs text-slate-200 font-bold uppercase tracking-wider">
                  Notification Filter Matrix
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={emailEnabled}
                    onChange={(e) => setEmailEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-cyan-600 focus:ring-cyan-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-white block">Email Dispatch</span>
                    <span className="text-[10px] text-slate-400">Master email toggle</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={criticalAlerts}
                    onChange={(e) => setCriticalAlerts(e.target.checked)}
                    className="w-4 h-4 rounded text-rose-600 focus:ring-rose-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-rose-400 block">Critical Severity</span>
                    <span className="text-[10px] text-slate-400">Packs, kicks & stuck pipe</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={highAlerts}
                    onChange={(e) => setHighAlerts(e.target.checked)}
                    className="w-4 h-4 rounded text-amber-600 focus:ring-amber-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-amber-400 block">High Severity</span>
                    <span className="text-[10px] text-slate-400">Losses, tight hole, vibrations</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={mediumAlerts}
                    onChange={(e) => setMediumAlerts(e.target.checked)}
                    className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-blue-400 block">Medium Severity</span>
                    <span className="text-[10px] text-slate-400">Parameter drifts & warnings</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={historicalAlerts}
                    onChange={(e) => setHistoricalAlerts(e.target.checked)}
                    className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-purple-400 block">Offset Events</span>
                    <span className="text-[10px] text-slate-400">Historical proximity matches</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition-all">
                  <input
                    type="checkbox"
                    checked={reportNotifications}
                    onChange={(e) => setReportNotifications(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 bg-slate-950 border-slate-700"
                  />
                  <div className="text-xs">
                    <span className="font-bold text-emerald-400 block">Report Handovers</span>
                    <span className="text-[10px] text-slate-400">Automated shift summaries</span>
                  </div>
                </label>
              </div>
            </div>

            {/* Action Buttons (Save & Reset) */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={handleReset}
                disabled={resetting || saving}
                className="w-full sm:w-auto bg-slate-800 hover:bg-rose-950/60 hover:text-rose-300 text-slate-400 font-bold py-2.5 px-5 rounded-xl text-xs tracking-wider uppercase transition-all border border-slate-700 hover:border-rose-700/50 flex items-center justify-center gap-2 cursor-pointer"
              >
                {resetting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    RESETTING...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    RESET TO DEFAULTS
                  </>
                )}
              </button>

              <button
                type="submit"
                disabled={saving || resetting}
                className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold py-2.5 px-6 rounded-xl text-xs tracking-wider uppercase transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 cursor-pointer"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    SAVING TO SUPABASE...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    SAVE SETTINGS TO SUPABASE
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Cloud & Supabase Sync Metadata */}
      {settings && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              Active Supabase Cloud Status & Provenance
            </h2>
            {settings.updated_at && (
              <span className="text-[10px] text-slate-400 font-mono">
                LAST UPDATED: {new Date(settings.updated_at).toLocaleString()}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-bold uppercase">SUPABASE POSTGRES</span>
              <strong className="text-emerald-400 text-sm block mt-1">CONNECTED (CLOUD)</strong>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-bold uppercase">ACCOUNT ISOLATION</span>
              <strong className="text-cyan-400 text-sm block mt-1">{profile?.email || "Per-User"}</strong>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-bold uppercase">RESEND NOTIFICATIONS</span>
              <strong className={settings.resend_notifications_enabled ? "text-emerald-400 text-sm block mt-1" : "text-amber-400 text-sm block mt-1"}>
                {settings.resend_notifications_enabled ? "ACTIVE (LIVE)" : "STUBBED"}
              </strong>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <span className="text-slate-500 block text-[10px] font-bold uppercase">ML READINESS GATE</span>
              <strong className="text-emerald-400 text-sm block mt-1">ENFORCED (RL_PROTECTED)</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

