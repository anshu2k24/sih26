import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Shield, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, UserPlus, KeyRound, LogIn } from "lucide-react";


type Mode = "LOGIN" | "SIGNUP" | "FORGOT";

export const LoginPage: React.FC = () => {
  const { login, signUp, resetPassword, status, error: authError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [mode, setMode] = useState<Mode>("LOGIN");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("ADMIN");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const from = (location.state as any)?.from?.pathname || "/dashboard";

  // If already authenticated, redirect
  useEffect(() => {
    if (status === "authenticated") {
      navigate(from, { replace: true });
    }
  }, [status, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setSuccessMsg(null);

    if (!email.trim()) {
      setFormError("Email address is required.");
      return;
    }

    if (mode !== "FORGOT" && !password) {
      setFormError("Password is required.");
      return;
    }

    setLoading(true);

    if (mode === "LOGIN") {
      const { error } = await login(email, password);
      setLoading(false);
      if (error) setFormError(error);
    } else if (mode === "SIGNUP") {
      const { error } = await signUp(email, password, fullName, role);
      setLoading(false);
      if (error) {
        setFormError(error);
      } else {
        setSuccessMsg("Account created successfully in Supabase! Signing in...");
        setTimeout(() => {
          login(email, password);
        }, 1200);
      }
    } else if (mode === "FORGOT") {
      const { error } = await resetPassword(email);
      setLoading(false);
      if (error) {
        setFormError(error);
      } else {
        setSuccessMsg(`Password reset instructions sent to ${email}. Check your inbox.`);
      }
    }
  };

  const displayError = formError || authError;

  return (
    <div className="min-h-screen bg-[#070B14] flex items-center justify-center p-4">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(#334155 1px, transparent 1px), linear-gradient(90deg, #334155 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-xl shadow-lg">
              <Shield className="w-8 h-8 text-blue-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white font-mono tracking-wider">
            eRTMAC-NWIS
          </h1>
          <p className="text-slate-400 text-sm mt-1 font-mono">
            Real-Time Operational Advisory Platform
          </p>
          <div className="mt-1 text-xs text-slate-500 font-mono">
            PS26121 — Equinor Volve Operations
          </div>
        </div>

        {/* Mode Navigation Tabs */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1.5 rounded-xl border border-slate-800 mb-4 font-mono text-xs">
          <button
            type="button"
            onClick={() => { setMode("LOGIN"); setFormError(null); setSuccessMsg(null); }}
            className={`py-2 rounded-lg font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === "LOGIN"
                ? "bg-blue-600 text-white shadow-md"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            SIGN IN
          </button>

          <button
            type="button"
            onClick={() => { setMode("SIGNUP"); setFormError(null); setSuccessMsg(null); }}
            className={`py-2 rounded-lg font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === "SIGNUP"
                ? "bg-blue-600 text-white shadow-md"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" />
            CREATE
          </button>

          <button
            type="button"
            onClick={() => { setMode("FORGOT"); setFormError(null); setSuccessMsg(null); }}
            className={`py-2 rounded-lg font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === "FORGOT"
                ? "bg-blue-600 text-white shadow-md"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
            }`}
          >
            <KeyRound className="w-3.5 h-3.5" />
            FORGOT
          </button>
        </div>

        {/* Form Card */}
        <div className="bg-slate-900/90 backdrop-blur-sm border border-slate-700/60 rounded-2xl p-7 shadow-2xl space-y-4">
          <h2 className="text-sm font-bold text-white font-mono tracking-wider uppercase border-b border-slate-800 pb-3 flex items-center justify-between">
            <span>
              {mode === "LOGIN" && "Operator Authentication"}
              {mode === "SIGNUP" && "Create New Supabase Account"}
              {mode === "FORGOT" && "Reset Password Request"}
            </span>
            <span className="text-[10px] text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30">
              SUPABASE DB
            </span>
          </h2>

          {/* Messages */}
          {displayError && (
            <div className="flex items-start gap-2.5 bg-rose-950/50 border border-rose-500/40 rounded-xl p-3 text-xs text-rose-300 font-mono">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{displayError}</span>
            </div>
          )}

          {successMsg && (
            <div className="flex items-start gap-2.5 bg-emerald-950/50 border border-emerald-500/40 rounded-xl p-3 text-xs text-emerald-300 font-mono">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name for Signup */}
            {mode === "SIGNUP" && (
              <div>
                <label className="block text-xs text-slate-400 font-mono uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jayanth (Principal Admin)"
                  className="w-full bg-slate-950 text-white border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm font-mono focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-600"
                />
              </div>
            )}

            {/* Email */}
            <div>
              <label className="block text-xs text-slate-400 font-mono uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="engineer@company.com"
                className="w-full bg-slate-950 text-white border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm font-mono focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-600"
              />
            </div>

            {/* Password (if not forgot) */}
            {mode !== "FORGOT" && (
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs text-slate-400 font-mono uppercase tracking-wider">
                    Password
                  </label>
                  {mode === "LOGIN" && (
                    <button
                      type="button"
                      onClick={() => setMode("FORGOT")}
                      className="text-[11px] text-cyan-400 hover:text-cyan-300 font-mono"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "LOGIN" ? "current-password" : "new-password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-slate-950 text-white border border-slate-700 rounded-xl px-3.5 py-2.5 pr-10 text-sm font-mono focus:outline-none focus:border-blue-500 transition-all placeholder:text-slate-600"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* Role Selection for Signup */}
            {mode === "SIGNUP" && (
              <div>
                <label className="block text-xs text-slate-400 font-mono uppercase tracking-wider mb-1">
                  Privilege Role Assignment
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-950 text-white border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs font-mono focus:outline-none focus:border-blue-500"
                >
                  <option value="ADMIN">ADMIN (Full High Privilege Access)</option>
                  <option value="DRILLING_ENGINEER">DRILLING_ENGINEER</option>
                  <option value="OPERATIONS_ENGINEER">OPERATIONS_ENGINEER</option>
                  <option value="ANALYST">ANALYST</option>
                  <option value="VIEWER">VIEWER</option>
                </select>
              </div>
            )}

            {/* Submit Button */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-mono font-bold py-3 rounded-xl text-xs tracking-wider uppercase transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  PROCESSING...
                </>
              ) : mode === "LOGIN" ? (
                "SIGN IN TO CONSOLE"
              ) : mode === "SIGNUP" ? (
                "CREATE SUPABASE ACCOUNT"
              ) : (
                "SEND RESET LINK"
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-[11px] text-slate-600 mt-4 font-mono">
          Volve USROP Telemetry Replay — Equinor Volve Field Dataset
        </p>
      </div>
    </div>
  );
};
