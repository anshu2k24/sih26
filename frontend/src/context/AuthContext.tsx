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

  // ── Fetch backend profile (authoritative role from DB) ──────────────────
  const fetchBackendProfile = useCallback(
    async (accessToken?: string): Promise<UserProfile | null> => {
      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (accessToken) {
          headers["Authorization"] = `Bearer ${accessToken}`;
        }

        const res = await fetch(`${API_BASE}/api/users/me`, { headers });
        if (!res.ok) {
          console.error(`[Auth] /api/users/me returned ${res.status}`);
          return null;
        }
        return await res.json();
      } catch (err) {
        console.error("[Auth] Failed to fetch backend profile:", err);
        return null;
      }
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
        if (p) {
          setProfile(p);
          setStatus("authenticated");
          setError(null);
        } else {
          setSession(null);
          setUser(null);
          setProfile(null);
          setStatus("unauthenticated");
        }
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
        if (p) {
          setProfile(p);
          setStatus("authenticated");
          setError(null);
        } else {
          setStatus("error");
          setError("Your account profile could not be loaded from database.");
        }
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
        // Hardcoded credential check
        if (email !== "jayanthjay751@gmail.com" || password !== "123456") {
          const msg = "Incorrect email or password.";
          setError(msg);
          return { error: msg };
        }
        setProfile({ ...DEV_PROFILE, email, full_name: "Jayasurya Midde" });
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

      const { error: authError } = await supabase.auth.signUp({
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
