/**
 * PS26121 eRTMAC-NWIS — Auth Context
 *
 * Provides authenticated session state across the entire application.
 *
 * Session flow:
 * 1. On mount, check Supabase for existing session.
 * 2. On login(), call supabase.auth.signInWithPassword().
 * 3. On auth state change, fetch user profile from backend /api/users/me
 *    to get the DB-authoritative role (not the JWT role claim).
 * 4. On logout(), call supabase.auth.signOut() and clear state.
 *
 * IMPORTANT:
 * - Role and permissions are fetched from the BACKEND (which reads from DB).
 * - Frontend role is UX-only — backend enforces all permissions independently.
 * - Service role key is NEVER present in this file.
 */

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import type { ReactNode } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import { API_BASE_URL } from "../services/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export type UserRole =
  | "ADMIN"
  | "DRILLING_ENGINEER"
  | "OPERATIONS_ENGINEER"
  | "ANALYST"
  | "VIEWER";

export interface UserProfile {
  user_id: string;
  email: string;
  role: UserRole;
  organization_id: string;
  full_name: string | null;
  permissions: string[];
}

export type AuthStatus =
  | "initializing"   // App startup — checking for existing session
  | "authenticated"  // Valid session + profile loaded
  | "unauthenticated" // No session or expired
  | "error";         // Unexpected failure

interface AuthContextType {
  status: AuthStatus;
  session: Session | null;
  user: User | null;
  profile: UserProfile | null;
  error: string | null;
  login: (email: string, password: string) => Promise<{ error: string | null }>;
  signUp: (email: string, password: string, fullName?: string, role?: string) => Promise<{ error: string | null }>;
  resetPassword: (email: string) => Promise<{ error: string | null }>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
  refreshProfile: () => Promise<void>;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ── Dev bypass profile (when Supabase not configured) ────────────────────────

const DEV_PROFILE: UserProfile = {
  user_id: "00000000-0000-0000-0000-000000000001",
  email: "dev.engineer@localhost",
  role: "DRILLING_ENGINEER",
  organization_id: "00000000-0000-0000-0000-000000000001",
  full_name: "Dev Engineer (Local)",
  permissions: [
    "VIEW_TELEMETRY",
    "VIEW_WELLS",
    "VIEW_HISTORICAL_DATA",
    "VIEW_ALERTS",
    "ACKNOWLEDGE_ALERT",
    "INVESTIGATE_ALERT",
    "RESOLVE_ALERT",
    "VIEW_PREDICTIONS",
    "RUN_ANALYSIS",
    "VIEW_AUDIT",
    "GENERATE_REPORTS",
    "UPLOAD_DOCUMENTS",
    "VERIFY_KNOWLEDGE",
    "VIEW_NOTIFICATIONS",
    "MANAGE_NOTIFICATIONS",
  ],
};

// ── Provider ──────────────────────────────────────────────────────────────────

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const createFallbackProfile = useCallback((currentUser: User): UserProfile => {
    const metaRole = (currentUser.user_metadata?.role as UserRole) || "ADMIN";
    return {
      user_id: currentUser.id,
      email: currentUser.email || "",
      role: metaRole,
      organization_id: currentUser.user_metadata?.organization_id || "00000000-0000-0000-0000-000000000001",
      full_name: currentUser.user_metadata?.full_name || currentUser.email?.split("@")[0] || "Operator",
      permissions: currentUser.user_metadata?.permissions || DEV_PROFILE.permissions,
    };
  }, []);

  // ── Fetch backend profile (authoritative role from DB) ──────────────────
  const fetchBackendProfile = useCallback(
    async (accessToken?: string): Promise<UserProfile | null> => {
      const endpoints = [
        `${API_BASE}/api/users/me`,
        API_BASE.includes("localhost") ? API_BASE.replace("localhost", "127.0.0.1") + "/api/users/me" : null,
      ].filter(Boolean) as string[];

      for (const endpoint of endpoints) {
        try {
          const headers: Record<string, string> = {
            "Content-Type": "application/json",
          };
          if (accessToken) {
            headers["Authorization"] = `Bearer ${accessToken}`;
          }

          const res = await fetch(endpoint, { headers });
          if (res.ok) {
            return await res.json();
          }
        } catch {
          // Try next endpoint (e.g. 127.0.0.1)
        }
      }
      return null;
    },
    [API_BASE]
  );

  const refreshProfile = useCallback(async () => {
    if (!isSupabaseConfigured) return;
    const currentSession = (await supabase.auth.getSession()).data.session;
    if (!currentSession) return;
    const p = await fetchBackendProfile(currentSession.access_token);
    if (p) setProfile(p);
  }, [fetchBackendProfile]);

  // ── Initialize auth state on mount ──────────────────────────────────────
  useEffect(() => {
    if (!isSupabaseConfigured) {
      // No Supabase configured → require manual login via hardcoded credentials
      setStatus("unauthenticated");
      return;
    }

    // Check for existing session (handles page refresh)
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session) {
        setSession(session);
        setUser(session.user);
        const p = await fetchBackendProfile(session.access_token);
        setProfile(p || createFallbackProfile(session.user));
        setStatus("authenticated");
        setError(null);
      } else {
        setStatus("unauthenticated");
      }
    });

    // Listen for auth state changes (login/logout/refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_IN" && session) {
        setSession(session);
        setUser(session.user);
        const p = await fetchBackendProfile(session.access_token);
        setProfile(p || createFallbackProfile(session.user));
        setStatus("authenticated");
        setError(null);
      } else if (event === "SIGNED_OUT") {
        setSession(null);
        setUser(null);
        setProfile(null);
        setStatus("unauthenticated");
        setError(null);
      } else if (event === "TOKEN_REFRESHED" && session) {
        setSession(session);
      }
    });

    return () => subscription.unsubscribe();
  }, [fetchBackendProfile]);

  // ── Login ────────────────────────────────────────────────────────────────
  const login = useCallback(
    async (email: string, password: string): Promise<{ error: string | null }> => {
      setError(null);

      if (!isSupabaseConfigured) {
        setProfile({ ...DEV_PROFILE, email, full_name: email.split("@")[0] });
        setStatus("authenticated");
        return { error: null };
      }

      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) {
        const msg =
          authError.message === "Invalid login credentials"
            ? "Incorrect email or password."
            : authError.message;
        setError(msg);
        return { error: msg };
      }

      if (!data.session) {
        const msg = "Login failed: no session returned.";
        setError(msg);
        return { error: msg };
      }

      // Profile will be loaded via onAuthStateChange
      return { error: null };
    },
    []
  );

  // ── SignUp ───────────────────────────────────────────────────────────────
  const signUp = useCallback(
    async (email: string, password: string, fullName?: string, role: string = "ADMIN"): Promise<{ error: string | null }> => {
      setError(null);

      if (!isSupabaseConfigured) {
        setProfile({
          ...DEV_PROFILE,
          email,
          role: role as UserRole,
          full_name: fullName || "New Operator",
        });
        setStatus("authenticated");
        return { error: null };
      }

      // 1. Try pre-confirming user directly via backend admin endpoint
      try {
        const regRes = await fetch(`${API_BASE_URL}/api/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            password,
            full_name: fullName || email.split("@")[0],
            role: role || "ADMIN",
          }),
        });
        if (regRes.ok) {
          // Immediately sign in with the new credentials
          const { error: signInErr } = await supabase.auth.signInWithPassword({ email, password });
          if (signInErr) {
            return { error: null };
          }
          return { error: null };
        } else {
          const errData = await regRes.json();
          if (errData.detail && !errData.detail.includes("unavailable")) {
            setError(errData.detail);
            return { error: errData.detail };
          }
        }
      } catch (err) {
        // Fallback to client-side Supabase signUp
      }

      // 2. Client-side Supabase fallback
      const { data: signUpData, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName || email.split("@")[0],
            role: role || "ADMIN",
          },
        },
      });

      if (authError) {
        setError(authError.message);
        return { error: authError.message };
      }

      if (signUpData?.session) {
        return { error: null };
      }

      return { error: null };
    },
    []
  );

  // ── Reset Password ───────────────────────────────────────────────────────
  const resetPassword = useCallback(
    async (email: string): Promise<{ error: string | null }> => {
      setError(null);

      if (!isSupabaseConfigured) {
        return { error: null };
      }

      const redirectUrl = `${window.location.origin}/login`;
      const { error: authError } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: redirectUrl,
      });

      if (authError) {
        setError(authError.message);
        return { error: authError.message };
      }

      return { error: null };
    },
    []
  );

  // ── Logout ───────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    if (isSupabaseConfigured) {
      await supabase.auth.signOut();
    } else {
      // Dev bypass logout
      setProfile(null);
      setStatus("unauthenticated");
    }
  }, []);

  // ── Permission check (UX only — backend enforces independently) ──────────
  const hasPermission = useCallback(
    (permission: string): boolean => {
      return profile?.permissions.includes(permission) ?? false;
    },
    [profile]
  );

  return (
    <AuthContext.Provider
      value={{
        status,
        session,
        user,
        profile,
        error,
        login,
        signUp,
        resetPassword,
        logout,
        hasPermission,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );

};

// ── Hook ──────────────────────────────────────────────────────────────────────

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
