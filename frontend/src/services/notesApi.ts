/**
 * PS121 Handwritten Notes OCR — Frontend API Service
 */

import { supabase } from "../lib/supabase";
import type {
  HandwrittenNote,
  OCRRun,
  OCRMetrics,
} from "../types/notes";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000");

async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers || {});
  try {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.access_token) {
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${data.session.access_token}`);
      }
    }
  } catch (err) {
    // Continue with existing headers
  }

  let res = await fetch(url, { ...init, headers });

  if (res.status === 401 && import.meta.env.VITE_SUPABASE_URL) {
    try {
      const { data: refreshData, error } = await supabase.auth.refreshSession();
      if (!error && refreshData?.session?.access_token) {
        headers.set("Authorization", `Bearer ${refreshData.session.access_token}`);
        res = await fetch(url, { ...init, headers });
      }
    } catch {
      // Continue
    }
  }

  return res;
}

/**
 * Uploads a handwritten note image and runs OCR.
 */
export async function uploadNoteOcrApi(
  file: File,
  title?: string,
  model?: string
): Promise<{
  success: boolean;
  status: string;
  note?: HandwrittenNote;
  ocr_run?: OCRRun;
  error?: string;
  is_duplicate?: boolean;
} | null> {
  try {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (model) formData.append("model", model);

    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/ocr`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(errJson.detail || `Upload failed with HTTP ${res.status}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error("uploadNoteOcrApi error:", err);
    return { success: false, status: "ERROR", error: err.message || "Network error" };
  }
}

/**
 * Fetches list of handwritten notes with optional filtering.
 */
export async function fetchNotesApi(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  q?: string;
}): Promise<{ count: number; notes: HandwrittenNote[] }> {
  try {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    if (params?.status) query.set("status", params.status);
    if (params?.q) query.set("q", params.q);

    const res = await authFetch(`${API_BASE_URL}/api/v1/notes?${query.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { count: data.count || 0, notes: data.notes || [] };
  } catch (err) {
    console.error("fetchNotesApi error:", err);
    return { count: 0, notes: [] };
  }
}

/**
 * Fetches dashboard statistics.
 */
export async function fetchNotesMetricsApi(): Promise<OCRMetrics | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/metrics`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNotesMetricsApi error:", err);
    return null;
  }
}

/**
 * Fetches single note detail by ID.
 */
export async function fetchNoteDetailApi(
  noteId: string
): Promise<{ note: HandwrittenNote; ocr_runs: OCRRun[]; provenance: any } | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNoteDetailApi error:", err);
    return null;
  }
}

/**
 * Saves draft reviewer edits.
 */
export async function saveDraftNoteApi(
  noteId: string,
  verifiedText: string,
  title?: string
): Promise<HandwrittenNote | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verified_text: verifiedText, title }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.note;
  } catch (err) {
    console.error("saveDraftNoteApi error:", err);
    return null;
  }
}

/**
 * Verifies note, promoting it to trusted status.
 */
export async function verifyNoteApi(
  noteId: string,
  verifiedText: string,
  title?: string
): Promise<HandwrittenNote | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verified_text: verifiedText, title }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.note;
  } catch (err) {
    console.error("verifyNoteApi error:", err);
    return null;
  }
}

/**
 * Rejects a note if OCR output is unsalvageable.
 */
export async function rejectNoteApi(
  noteId: string
): Promise<HandwrittenNote | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}/reject`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.note;
  } catch (err) {
    console.error("rejectNoteApi error:", err);
    return null;
  }
}

/**
 * Retries OCR on an existing note.
 */
export async function retryNoteOcrApi(
  noteId: string,
  model?: string
): Promise<{ success: boolean; note?: HandwrittenNote; error?: string }> {
  try {
    const url = model
      ? `${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}/retry?model=${encodeURIComponent(model)}`
      : `${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}/retry`;
    
    const res = await authFetch(url, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err: any) {
    console.error("retryNoteOcrApi error:", err);
    return { success: false, error: err.message || "Retry request failed" };
  }
}

/**
 * Deletes a note.
 */
export async function deleteNoteApi(noteId: string): Promise<boolean> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}`, {
      method: "DELETE",
    });
    return res.ok;
  } catch (err) {
    console.error("deleteNoteApi error:", err);
    return false;
  }
}

/**
 * Gets note export URL (JSON or TXT).
 */
export function getNoteExportUrl(noteId: string, format: "json" | "txt"): string {
  return `${API_BASE_URL}/api/v1/notes/${encodeURIComponent(noteId)}/export?format=${format}`;
}

/**
 * Resolves full URL for note image.
 */
export function getNoteImageUrl(publicUrl: string): string {
  if (!publicUrl) return "";
  if (publicUrl.startsWith("http://") || publicUrl.startsWith("https://")) {
    return publicUrl;
  }
  return `${API_BASE_URL}${publicUrl}`;
}
