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
  AlertTriangle,
  Activity,
  Gauge,
  MapPin,
  FileText,
  Clock,
  Zap,
  ShieldCheck,
} from "lucide-react";

export const SettingsPage: React.FC = () => {
  const { profile } = useAuth();
  const [settings, setSettings] = useState<SystemSettings | null>(null);

  // Form State
  const [emailInput, setEmailInput] = useState<string>("");
  const [emailRateLimit, setEmailRateLimit] = useState<number>(4);
  const [sendToLoginAccount, setSendToLoginAccount] = useState<boolean>(true);
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
        setEmailRateLimit(res.email_rate_limit_per_sec ?? 4);
        const shouldRouteLogin = res.send_to_login_account ?? true;
        setSendToLoginAccount(shouldRouteLogin);

        if (shouldRouteLogin && profile?.email) {
          setEmailInput(profile.email);
        } else {
          setEmailInput(res.notification_recipient_email || profile?.email || "");
        }

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

    const targetEmail = sendToLoginAccount && profile?.email ? profile.email : emailInput.trim();

    if (!targetEmail) {
      setSaveError("Notification recipient email is required.");
      return;
    }

    setSaving(true);
    const updated = await updateSystemSettingsApi({
      notification_recipient_email: targetEmail,
      email_rate_limit_per_sec: Number(emailRateLimit),
      send_to_login_account: sendToLoginAccount,
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
        `Settings saved! Email notifications set to max ${emailRateLimit}/sec for account ${targetEmail}.`
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
      setEmailRateLimit(4);
      setSendToLoginAccount(true);
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
      setSaveSuccess("Your configuration has been reset to default values (4 emails/sec rate limit for login account).");
    } else {
      setSaveError("Failed to reset settings in Supabase.");
    }
  };

  return (
    <div 
      className="min-h-screen pb-[48px] relative font-['Space_Grotesk',sans-serif]"
      style={{ 
        backgroundColor: "#050505", 
        backgroundImage: "radial-gradient(circle at center, rgba(5, 5, 5, 0.5) 0%, rgba(5, 5, 5, 0.95) 100%), url('/bg-map.jpg')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundAttachment: "fixed"
      }}
    >
      <div className="relative z-10 max-w-[1200px] mx-auto px-[32px] pt-[32px] space-y-[28px]">
        {/* Header Banner */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 relative">
          <div className="relative z-10 flex flex-col gap-[12px]">
            <h1 className="text-[32px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
              OPERATOR CONFIGURATION & PERSONAL SETTINGS
            </h1>
          </div>

          {/* User Identity Pill */}
          <div 
            className="relative z-10 flex items-center gap-[16px] px-[20px] py-[14px] rounded-[16px] shrink-0 self-start md:self-auto transition-all"
            style={{
              background: "rgba(24, 20, 15, 0.60)",
              border: "1px solid rgba(255, 138, 0, 0.2)",
            }}
          >
            <div className="w-[40px] h-[40px] rounded-[10px] bg-[rgba(255,138,0,0.1)] border border-[rgba(255,138,0,0.3)] flex items-center justify-center">
              <UserCheck className="w-5 h-5 text-[#FF9D1A]" />
            </div>
            <div>
              <div className="text-[13px] text-white font-[700] tracking-wide">{profile?.full_name || profile?.email || "Operator"}</div>
              <div className="text-[11px] text-[#FF8A00] font-mono mt-0.5 flex items-center gap-2">
                {profile?.email} 
                <span className="text-[#00D084] font-[700] bg-[rgba(0,208,132,0.1)] px-1.5 py-0.5 rounded-[4px] border border-[rgba(0,208,132,0.3)]">• ADMIN</span>
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Settings Edit Form */}
        <div 
          className="rounded-[20px] p-[32px] space-y-[28px] relative group"
          style={{
            background: "rgba(18, 16, 13, 0.72)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            border: "1px solid rgba(255, 138, 0, 0.3)",
            boxShadow: "0 8px 35px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)"
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[rgba(255,138,0,0.2)] pb-[16px]">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" />
              <h2 className="text-[15px] font-[700] text-white uppercase tracking-wider drop-shadow-sm">
                SUPABASE CLOUD SETTINGS (CRUD)
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-[#00D084] font-[700] font-mono tracking-widest bg-[rgba(0,208,132,0.1)] px-[12px] py-[6px] rounded-[8px] border border-[rgba(0,208,132,0.3)] flex items-center gap-2 shadow-[0_0_10px_rgba(0,208,132,0.1)]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00D084] shadow-[0_0_5px_#00D084] animate-pulse" />
                INDIVIDUAL USER ISOLATION
              </span>
            </div>
          </div>

          {saveSuccess && (
            <div className="flex items-center gap-3 bg-[rgba(0,208,132,0.1)] border border-[rgba(0,208,132,0.4)] rounded-[12px] p-[16px] text-[13px] text-[#00D084] shadow-[0_0_15px_rgba(0,208,132,0.15)]">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span className="font-sans font-[500]">{saveSuccess}</span>
            </div>
          )}

          {saveError && (
            <div className="flex items-center gap-3 bg-[rgba(255,77,95,0.1)] border border-[rgba(255,77,95,0.4)] rounded-[12px] p-[16px] text-[13px] text-[#FF4D5F] shadow-[0_0_15px_rgba(255,77,95,0.15)]">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span className="font-sans font-[500]">{saveError}</span>
            </div>
          )}

          {loading ? (
            <div className="py-[60px] flex flex-col items-center justify-center gap-4 text-[#9AA0A6]">
              <Loader2 className="w-8 h-8 animate-spin text-[#FF9D1A]" />
              <span className="text-[12px] uppercase tracking-widest font-[700]">Loading user settings from Supabase...</span>
            </div>
          ) : (
            <form onSubmit={handleSave} className="space-y-[28px]">
              {/* Section 1: Email Target & Rate Limiting Governance */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-[24px]">
                {/* 1A: Recipient Account */}
                <div 
                  className="p-[24px] rounded-[16px] space-y-[16px] flex flex-col justify-between"
                  style={{
                    background: "rgba(24, 20, 15, 0.60)",
                    border: "1px solid rgba(255,138,0,0.15)",
                  }}
                >
                  <div className="flex items-start gap-[16px]">
                    <div className="w-[44px] h-[44px] shrink-0 rounded-[12px] bg-[rgba(255,138,0,0.1)] border border-[rgba(255,138,0,0.3)] flex items-center justify-center">
                      <Mail className="w-5 h-5 text-[#FF9D1A]" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-[4px]">
                        <label className="text-[13px] text-white font-[700] uppercase tracking-wider block">
                          ALERT DISPATCH EMAIL
                        </label>
                        {sendToLoginAccount && (
                          <span className="text-[10px] font-mono text-[#00D084] bg-[rgba(0,208,132,0.1)] border border-[rgba(0,208,132,0.3)] px-2 py-0.5 rounded-full font-[700]">
                            ● LOGIN ACCOUNT
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#9AA0A6] font-sans leading-relaxed">
                        Drilling alerts, offset hazards, and rig reports will be dispatched to this address.
                      </p>
                    </div>
                  </div>

                  {/* Login Account Binding Toggle */}
                  <div className="pt-2">
                    <label className="flex items-center gap-2.5 cursor-pointer select-none mb-3">
                      <input
                        type="checkbox"
                        checked={sendToLoginAccount}
                        onChange={(e) => {
                          const checked = e.target.checked;
                          setSendToLoginAccount(checked);
                          if (checked && profile?.email) {
                            setEmailInput(profile.email);
                          }
                        }}
                        className="w-[16px] h-[16px] rounded border-[#FF8A00] text-[#FF8A00] focus:ring-[#FF8A00] bg-transparent cursor-pointer"
                        style={{ accentColor: "#FF8A00" }}
                      />
                      <span className="text-[12px] text-white font-medium">
                        Send to Login Account ({profile?.email || "Authenticated Operator"})
                      </span>
                    </label>

                    <div className="relative">
                      <input
                        type="email"
                        value={emailInput}
                        onChange={(e) => {
                          setEmailInput(e.target.value);
                          if (sendToLoginAccount && e.target.value !== profile?.email) {
                            setSendToLoginAccount(false);
                          }
                        }}
                        placeholder="operator@company.com"
                        className="w-full rounded-[12px] px-[16px] py-[13px] text-[13px] font-mono text-[#FF9D1A] transition-all focus:outline-none placeholder:text-[#6B7280]"
                        style={{
                          background: "rgba(0,0,0,0.6)",
                          border: "1px solid rgba(255,138,0,0.3)",
                          boxShadow: "inset 0 0 15px rgba(0,0,0,0.5)"
                        }}
                      />
                      {profile?.email && emailInput !== profile.email && (
                        <button
                          type="button"
                          onClick={() => {
                            setEmailInput(profile.email || "");
                            setSendToLoginAccount(true);
                          }}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono font-[700] text-[#00D084] hover:text-white px-2 py-1 bg-[rgba(0,208,132,0.15)] border border-[rgba(0,208,132,0.3)] rounded-[6px] transition-all"
                        >
                          Use Login Email
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* 1B: Email Rate Limiter (Max 4 Mails per Sec) */}
                <div 
                  className="p-[24px] rounded-[16px] space-y-[16px] flex flex-col justify-between"
                  style={{
                    background: "rgba(24, 20, 15, 0.60)",
                    border: "1px solid rgba(255,138,0,0.15)",
                  }}
                >
                  <div className="flex items-start gap-[16px]">
                    <div className="w-[44px] h-[44px] shrink-0 rounded-[12px] bg-[rgba(255,138,0,0.1)] border border-[rgba(255,138,0,0.3)] flex items-center justify-center">
                      <Clock className="w-5 h-5 text-[#FF9D1A]" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2 mb-[4px]">
                        <label className="text-[13px] text-white font-[700] uppercase tracking-wider block">
                          EMAIL RATE LIMIT (PER SECOND)
                        </label>
                        <span 
                          className="text-[11px] font-mono font-[700] px-2.5 py-0.5 rounded-full border shadow-sm"
                          style={{
                            background: emailRateLimit <= 4 ? "rgba(0,208,132,0.1)" : "rgba(255,138,0,0.1)",
                            borderColor: emailRateLimit <= 4 ? "rgba(0,208,132,0.3)" : "rgba(255,138,0,0.3)",
                            color: emailRateLimit <= 4 ? "#00D084" : "#FF9D1A",
                          }}
                        >
                          {emailRateLimit} MAILS / SEC
                        </span>
                      </div>
                      <p className="text-[11px] text-[#9AA0A6] font-sans leading-relaxed">
                        Sliding-window dispatch throttler. Guarantees maximum of {emailRateLimit} emails/sec to prevent alert storms.
                      </p>
                    </div>
                  </div>

                  <div className="pt-2 space-y-3">
                    {/* Slider */}
                    <div className="flex items-center gap-3">
                      <span className="text-[11px] font-mono text-[#71717A]">1/s</span>
                      <input
                        type="range"
                        min="1"
                        max="10"
                        step="1"
                        value={emailRateLimit}
                        onChange={(e) => setEmailRateLimit(parseInt(e.target.value, 10))}
                        className="w-full h-2 rounded-lg bg-black/60 appearance-none cursor-pointer accent-[#FF8A00]"
                      />
                      <span className="text-[11px] font-mono text-[#71717A]">10/s</span>
                    </div>

                    {/* Presets */}
                    <div className="flex items-center justify-between gap-2">
                      {[1, 2, 4, 8].map((val) => (
                        <button
                          key={val}
                          type="button"
                          onClick={() => setEmailRateLimit(val)}
                          className={`flex-1 py-1.5 px-2 rounded-[8px] text-[11px] font-mono font-[700] transition-all border ${
                            emailRateLimit === val
                              ? "bg-[#FF8A00]/20 border-[#FF8A00] text-white shadow-[0_0_10px_rgba(255,138,0,0.2)]"
                              : "bg-black/40 border-white/10 text-[#A1A1AA] hover:border-white/20 hover:text-white"
                          }`}
                        >
                          {val}/s {val === 4 ? "(Def)" : ""}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 2: Correlation Windows */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-[24px]">
                <div 
                  className="p-[24px] rounded-[16px] space-y-[16px]"
                  style={{
                    background: "rgba(24, 20, 15, 0.60)",
                    border: "1px solid rgba(255,138,0,0.15)",
                  }}
                >
                  <div className="flex items-center gap-[12px]">
                    <Activity className="w-4 h-4 text-[#FF9D1A]" />
                    <label className="text-[12px] text-white font-[700] uppercase tracking-wider block">
                      DEFAULT PROXIMITY SEARCH RADIUS (KM)
                    </label>
                  </div>
                  <p className="text-[11px] text-[#9AA0A6] font-sans">
                    Search radius applied when querying offset historical wells.
                  </p>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.5"
                      min="0.5"
                      max="100"
                      value={radiusInput}
                      onChange={(e) => setRadiusInput(parseFloat(e.target.value) || 5.0)}
                      className="w-full rounded-[12px] px-[20px] py-[14px] text-[14px] font-mono font-[700] text-white transition-all focus:outline-none"
                      style={{
                        background: "rgba(0,0,0,0.6)",
                        border: "1px solid rgba(255,138,0,0.3)",
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,138,0,0.6)";
                        e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.15)";
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,138,0,0.3)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    />
                    <span className="absolute right-[20px] top-[50%] -translate-y-[50%] text-[#9AA0A6] text-[11px] font-[700] font-mono pointer-events-none">
                      KM
                    </span>
                  </div>
                </div>

                <div 
                  className="p-[24px] rounded-[16px] space-y-[16px]"
                  style={{
                    background: "rgba(24, 20, 15, 0.60)",
                    border: "1px solid rgba(255,138,0,0.15)",
                  }}
                >
                  <div className="flex items-center gap-[12px]">
                    <Activity className="w-4 h-4 text-[#FF9D1A]" />
                    <label className="text-[12px] text-white font-[700] uppercase tracking-wider block">
                      DEFAULT DEPTH CORRELATION WINDOW (M)
                    </label>
                  </div>
                  <p className="text-[11px] text-[#9AA0A6] font-sans">
                    Vertical depth search band (± MD) for finding matching historical DDR events.
                  </p>
                  <div className="relative">
                    <input
                      type="number"
                      step="5"
                      min="5"
                      max="500"
                      value={depthInput}
                      onChange={(e) => setDepthInput(parseFloat(e.target.value) || 50.0)}
                      className="w-full rounded-[12px] px-[20px] py-[14px] text-[14px] font-mono font-[700] text-white transition-all focus:outline-none"
                      style={{
                        background: "rgba(0,0,0,0.6)",
                        border: "1px solid rgba(255,138,0,0.3)",
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,138,0,0.6)";
                        e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.15)";
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "rgba(255,138,0,0.3)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    />
                    <span className="absolute right-[20px] top-[50%] -translate-y-[50%] text-[#9AA0A6] text-[11px] font-[700] font-mono pointer-events-none">
                      M
                    </span>
                  </div>
                </div>
              </div>

              {/* Section 3: Notification Filtering Matrix */}
              <div 
                className="p-[28px] rounded-[16px] space-y-[20px]"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: "1px solid rgba(255,138,0,0.15)",
                }}
              >
                <div className="flex items-center gap-[12px]">
                  <BellRing className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" />
                  <h3 className="text-[14px] text-white font-[700] uppercase tracking-wider block">
                    NOTIFICATION FILTER MATRIX
                  </h3>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[16px] pt-[8px]">
                  {/* Email Dispatch - Orange */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(255,138,0,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(255,138,0,0.15)";
                      e.currentTarget.style.background = "rgba(255,138,0,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(255,138,0,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={emailEnabled}
                      onChange={(e) => setEmailEnabled(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#FF8A00] text-[#FF8A00] focus:ring-[#FF8A00] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#FF8A00" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-white text-[13px] block tracking-wide">Email Dispatch</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Master email toggle</span>
                    </div>
                    <Mail className="w-5 h-5 text-[#FF9D1A] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#FF9D1A] transition-all" />
                  </label>

                  {/* Critical Severity - Red */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(255,77,95,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(255,77,95,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(255,77,95,0.15)";
                      e.currentTarget.style.background = "rgba(255,77,95,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(255,77,95,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={criticalAlerts}
                      onChange={(e) => setCriticalAlerts(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#FF4D5F] text-[#FF4D5F] focus:ring-[#FF4D5F] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#FF4D5F" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-[#FF4D5F] text-[13px] block tracking-wide">Critical Severity</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Packs, kicks & stuck pipe</span>
                    </div>
                    <AlertTriangle className="w-5 h-5 text-[#FF4D5F] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#FF4D5F] transition-all" />
                  </label>

                  {/* High Severity - Yellow/Orange */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(255,170,0,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(255,170,0,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(255,170,0,0.15)";
                      e.currentTarget.style.background = "rgba(255,170,0,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(255,170,0,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={highAlerts}
                      onChange={(e) => setHighAlerts(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#FFAA00] text-[#FFAA00] focus:ring-[#FFAA00] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#FFAA00" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-[#FFAA00] text-[13px] block tracking-wide">High Severity</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Losses, tight hole, vibrations</span>
                    </div>
                    <Activity className="w-5 h-5 text-[#FFAA00] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#FFAA00] transition-all" />
                  </label>

                  {/* Medium Severity - Blue */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(59,130,246,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(59,130,246,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(59,130,246,0.15)";
                      e.currentTarget.style.background = "rgba(59,130,246,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(59,130,246,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={mediumAlerts}
                      onChange={(e) => setMediumAlerts(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#3B82F6] text-[#3B82F6] focus:ring-[#3B82F6] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#3B82F6" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-[#3B82F6] text-[13px] block tracking-wide">Medium Severity</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Parameter drifts & warnings</span>
                    </div>
                    <Gauge className="w-5 h-5 text-[#3B82F6] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#3B82F6] transition-all" />
                  </label>

                  {/* Offset Events - Purple */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(168,85,247,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(168,85,247,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(168,85,247,0.15)";
                      e.currentTarget.style.background = "rgba(168,85,247,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(168,85,247,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={historicalAlerts}
                      onChange={(e) => setHistoricalAlerts(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#A855F7] text-[#A855F7] focus:ring-[#A855F7] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#A855F7" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-[#A855F7] text-[13px] block tracking-wide">Offset Events</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Historical proximity matches</span>
                    </div>
                    <MapPin className="w-5 h-5 text-[#A855F7] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#A855F7] transition-all" />
                  </label>

                  {/* Report Handovers - Green */}
                  <label 
                    className="flex items-start gap-[16px] p-[20px] rounded-[16px] cursor-pointer transition-all duration-200 group"
                    style={{
                      background: "rgba(0,0,0,0.4)",
                      border: "1px solid rgba(0,208,132,0.2)"
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = "translateY(-3px)";
                      e.currentTarget.style.borderColor = "rgba(0,208,132,0.5)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(0,208,132,0.15)";
                      e.currentTarget.style.background = "rgba(0,208,132,0.03)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.borderColor = "rgba(0,208,132,0.2)";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={reportNotifications}
                      onChange={(e) => setReportNotifications(e.target.checked)}
                      className="w-[18px] h-[18px] mt-[2px] rounded border-[#00D084] text-[#00D084] focus:ring-[#00D084] bg-transparent transition-colors cursor-pointer"
                      style={{ accentColor: "#00D084" }}
                    />
                    <div className="flex-1">
                      <span className="font-[700] text-[#00D084] text-[13px] block tracking-wide">Report Handovers</span>
                      <span className="text-[11px] text-[#9AA0A6] font-sans mt-[4px] block">Automated shift summaries</span>
                    </div>
                    <FileText className="w-5 h-5 text-[#00D084] opacity-[0.4] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_8px_#00D084] transition-all" />
                  </label>
                </div>
              </div>

              {/* Action Buttons (Save & Reset) */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-[16px] pt-[8px]">
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={resetting || saving}
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-[24px] py-[14px] rounded-[12px] font-[700] text-[13px] text-[#9AA0A6] tracking-wider uppercase transition-all duration-200 cursor-pointer disabled:opacity-50"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,138,0,0.2)"
                  }}
                  onMouseEnter={(e) => {
                    if(!resetting && !saving) {
                      e.currentTarget.style.background = "rgba(255,138,0,0.08)";
                      e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
                      e.currentTarget.style.color = "#FF9D1A";
                      e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.15)";
                      e.currentTarget.style.transform = "translateY(-1px)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if(!resetting && !saving) {
                      e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                      e.currentTarget.style.borderColor = "rgba(255,138,0,0.2)";
                      e.currentTarget.style.color = "#9AA0A6";
                      e.currentTarget.style.boxShadow = "none";
                      e.currentTarget.style.transform = "none";
                    }
                  }}
                >
                  {resetting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      RESETTING...
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      RESET TO DEFAULTS
                    </>
                  )}
                </button>

                <button
                  type="submit"
                  disabled={saving || resetting}
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-[32px] py-[14px] rounded-[12px] font-[700] text-[14px] tracking-wider uppercase transition-all duration-200 cursor-pointer disabled:opacity-50"
                  style={{
                    background: "linear-gradient(90deg, #FF8A00, #FF6A00)",
                    border: "1px solid rgba(255,170,100,0.5)",
                    color: "#FFFFFF",
                    boxShadow: "0 0 20px rgba(255,138,0,0.3), inset 0 0 15px rgba(255,255,255,0.2)"
                  }}
                  onMouseEnter={(e) => {
                    if(!saving && !resetting) {
                      e.currentTarget.style.transform = "translateY(-2px)";
                      e.currentTarget.style.boxShadow = "0 8px 25px rgba(255,138,0,0.3), 0 0 25px rgba(255,138,0,0.5), inset 0 0 15px rgba(255,255,255,0.3)";
                      e.currentTarget.style.filter = "brightness(1.1)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if(!saving && !resetting) {
                      e.currentTarget.style.transform = "none";
                      e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.3), inset 0 0 15px rgba(255,255,255,0.2)";
                      e.currentTarget.style.filter = "none";
                    }
                  }}
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      SAVING...
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
          <div 
            className="rounded-[20px] p-[32px] space-y-[24px]"
            style={{
              background: "rgba(18, 16, 13, 0.72)",
              backdropFilter: "blur(14px)",
              WebkitBackdropFilter: "blur(14px)",
              border: "1px solid rgba(255, 138, 0, 0.3)",
              boxShadow: "0 8px 35px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)"
            }}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255,138,0,0.2)] pb-[16px]">
              <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-3">
                <Shield className="w-5 h-5 text-[#FF9D1A] drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" />
                ACTIVE SUPABASE CLOUD STATUS & PROVENANCE
              </h2>
              {settings.updated_at && (
                <span className="text-[11px] text-[#9AA0A6] font-mono tracking-widest uppercase">
                  LAST UPDATED: {new Date(settings.updated_at).toLocaleString()}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-[16px]">
              {/* Supabase Postgres */}
              <div 
                className="p-[20px] rounded-[16px] transition-all duration-300 group"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: "1px solid rgba(0,208,132,0.2)"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,208,132,0.5)";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(0,208,132,0.15)";
                  e.currentTarget.style.background = "rgba(0,208,132,0.05)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,208,132,0.2)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.background = "rgba(24, 20, 15, 0.60)";
                }}
              >
                <div className="flex items-center gap-[12px] mb-[12px]">
                  <Database className="w-4 h-4 text-[#00D084] opacity-[0.6] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_5px_#00D084] transition-all" />
                  <span className="text-[#9AA0A6] text-[10px] font-[700] font-mono tracking-widest uppercase">SUPABASE POSTGRES</span>
                </div>
                <strong className="text-[#00D084] text-[13px] font-[700] tracking-wide block drop-shadow-[0_0_5px_rgba(0,208,132,0.3)]">CONNECTED (CLOUD)</strong>
              </div>

              {/* Account Isolation */}
              <div 
                className="p-[20px] rounded-[16px] transition-all duration-300 group"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: "1px solid rgba(56,189,248,0.2)"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(56,189,248,0.5)";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(56,189,248,0.15)";
                  e.currentTarget.style.background = "rgba(56,189,248,0.05)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(56,189,248,0.2)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.background = "rgba(24, 20, 15, 0.60)";
                }}
              >
                <div className="flex items-center gap-[12px] mb-[12px]">
                  <UserCheck className="w-4 h-4 text-[#38BDF8] opacity-[0.6] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_5px_#38BDF8] transition-all" />
                  <span className="text-[#9AA0A6] text-[10px] font-[700] font-mono tracking-widest uppercase">ACCOUNT ISOLATION</span>
                </div>
                <strong className="text-[#38BDF8] text-[13px] font-[700] font-mono tracking-wide block truncate drop-shadow-[0_0_5px_rgba(56,189,248,0.3)]" title={profile?.email}>
                  {profile?.email || "Per-User"}
                </strong>
              </div>

              {/* Email Rate Limit */}
              <div 
                className="p-[20px] rounded-[16px] transition-all duration-300 group"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: "1px solid rgba(255,138,0,0.2)"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,138,0,0.5)";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(255,138,0,0.15)";
                  e.currentTarget.style.background = "rgba(255,138,0,0.05)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,138,0,0.2)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.background = "rgba(24, 20, 15, 0.60)";
                }}
              >
                <div className="flex items-center gap-[12px] mb-[12px]">
                  <Clock className="w-4 h-4 text-[#FF9D1A] opacity-[0.6] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_5px_#FF9D1A] transition-all" />
                  <span className="text-[#9AA0A6] text-[10px] font-[700] font-mono tracking-widest uppercase">EMAIL RATE LIMIT</span>
                </div>
                <strong className="text-[#FF9D1A] text-[13px] font-[700] tracking-wide block drop-shadow-[0_0_5px_rgba(255,157,26,0.3)]">
                  {settings.email_rate_limit_per_sec ?? 4} / SEC (LOGIN USER)
                </strong>
              </div>

              {/* Resend Notifications */}
              <div 
                className="p-[20px] rounded-[16px] transition-all duration-300 group"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: `1px solid ${settings.resend_notifications_enabled ? 'rgba(0,208,132,0.2)' : 'rgba(255,138,0,0.2)'}`
                }}
                onMouseEnter={(e) => {
                  const color = settings.resend_notifications_enabled ? '0,208,132' : '255,138,0';
                  e.currentTarget.style.borderColor = `rgba(${color},0.5)`;
                  e.currentTarget.style.boxShadow = `0 0 20px rgba(${color},0.15)`;
                  e.currentTarget.style.background = `rgba(${color},0.05)`;
                }}
                onMouseLeave={(e) => {
                  const color = settings.resend_notifications_enabled ? '0,208,132' : '255,138,0';
                  e.currentTarget.style.borderColor = `rgba(${color},0.2)`;
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.background = "rgba(24, 20, 15, 0.60)";
                }}
              >
                <div className="flex items-center gap-[12px] mb-[12px]">
                  <BellRing className={`w-4 h-4 opacity-[0.6] group-hover:opacity-[1] transition-all ${settings.resend_notifications_enabled ? 'text-[#00D084] group-hover:drop-shadow-[0_0_5px_#00D084]' : 'text-[#FF8A00] group-hover:drop-shadow-[0_0_5px_#FF8A00]'}`} />
                  <span className="text-[#9AA0A6] text-[10px] font-[700] font-mono tracking-widest uppercase">RESEND NOTIFICATIONS</span>
                </div>
                <strong className={`text-[13px] font-[700] tracking-wide block ${settings.resend_notifications_enabled ? 'text-[#00D084] drop-shadow-[0_0_5px_rgba(0,208,132,0.3)]' : 'text-[#FF8A00] drop-shadow-[0_0_5px_rgba(255,138,0,0.3)]'}`}>
                  {settings.resend_notifications_enabled ? "ACTIVE (LIVE)" : "STUBBED"}
                </strong>
              </div>

              {/* ML Readiness Gate */}
              <div 
                className="p-[20px] rounded-[16px] transition-all duration-300 group"
                style={{
                  background: "rgba(24, 20, 15, 0.60)",
                  border: "1px solid rgba(0,208,132,0.2)"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,208,132,0.5)";
                  e.currentTarget.style.boxShadow = "0 0 20px rgba(0,208,132,0.15)";
                  e.currentTarget.style.background = "rgba(0,208,132,0.05)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(0,208,132,0.2)";
                  e.currentTarget.style.boxShadow = "none";
                  e.currentTarget.style.background = "rgba(24, 20, 15, 0.60)";
                }}
              >
                <div className="flex items-center gap-[12px] mb-[12px]">
                  <Shield className="w-4 h-4 text-[#00D084] opacity-[0.6] group-hover:opacity-[1] group-hover:drop-shadow-[0_0_5px_#00D084] transition-all" />
                  <span className="text-[#9AA0A6] text-[10px] font-[700] font-mono tracking-widest uppercase">ML READINESS GATE</span>
                </div>
                <strong className="text-[#00D084] text-[13px] font-[700] tracking-wide block drop-shadow-[0_0_5px_rgba(0,208,132,0.3)]">ENFORCED (RL_PROTECTED)</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
