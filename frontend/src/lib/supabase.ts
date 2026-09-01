/**
 * PS26121 eRTMAC-NWIS — Supabase Client (Frontend)
 *
 * IMPORTANT SECURITY RULES:
 * - Only uses SUPABASE_ANON_KEY — this is safe in the browser (Supabase design).
 * - SUPABASE_SERVICE_ROLE_KEY must NEVER appear here or in any frontend file.
 * - RESEND_API_KEY must NEVER appear here or in any frontend file.
 * - JWT verification is performed on the backend — frontend only uses the session token.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "[Supabase] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY not set in frontend/.env. " +
      "Auth features will be disabled. Set AUTH_REQUIRED=false in backend for local dev."
  );
}

export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder-anon-key"
);

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);
