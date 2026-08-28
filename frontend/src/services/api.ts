import { supabase } from "../lib/supabase";

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
    // Continue
  }
  return fetch(url, { ...init, headers });
}

import type {
  WellsResponse,
  WellItem,
  NearbyWellsResponse,
  WellIntelligenceResponse,
  KnowledgeSearchResponse,
  KnowledgeSearchParams,
  HistoricalProximityResponse,
  SystemSettings
} from "../types/api";
import type { WellStreamState, SensorRecord } from "../types/sensor";
import type { EventsResponse } from "../types/events";
import type { MLStatusState } from "../types/ml";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" && window.location.protocol === "https:"
    ? `https://${window.location.host}`
    : "http://localhost:8000");


export async function fetchWells(): Promise<WellItem[]> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/wells`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: WellsResponse = await res.json();
    return data.wells;
  } catch (err) {
    console.error("fetchWells error:", err);
    return [
      { well_id: "15/9-F-15", status: "available" },
      { well_id: "15/9-F-14", status: "available" },
      { well_id: "15/9-F-9 A", status: "available" }
    ];
  }
}

export async function fetchWellState(wellId: string): Promise<WellStreamState | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const res = await authFetch(`${API_BASE_URL}/api/wells/${encodedWell}/state`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchWellState error:", err);
    return null;
  }
}

export async function fetchSensorHistory(wellId: string, cutoffMd?: number): Promise<SensorRecord[]> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    let url = `${API_BASE_URL}/api/wells/${encodedWell}/sensors/history`;
    if (cutoffMd !== undefined) {
      url += `?cutoff_md=${cutoffMd}`;
    }
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.records || [];
  } catch (err) {
    console.error("fetchSensorHistory error:", err);
    return [];
  }
}

export async function fetchOffsetEvents(
  wellId: string,
  currentMd: number = 3000.0,
  radius: number = 100.0
): Promise<EventsResponse | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const url = `${API_BASE_URL}/api/wells/${encodedWell}/events?current_md=${currentMd}&radius=${radius}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchOffsetEvents error:", err);
    return null;
  }
}

export async function fetchRiskStatus(wellId: string): Promise<MLStatusState | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const res = await authFetch(`${API_BASE_URL}/api/wells/${encodedWell}/risk`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchRiskStatus error:", err);
    return null;
  }
}

export async function fetchNearbyWells(
  wellId: string,
  radiusKm: number = 5.0
): Promise<NearbyWellsResponse | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    const res = await authFetch(`${API_BASE_URL}/api/wells/${encodedWell}/nearby?radius_km=${radiusKm}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNearbyWells error:", err);
    return null;
  }
}

export async function fetchWellFullIntelligence(
  wellId: string,
  activeWellId?: string
): Promise<WellIntelligenceResponse | null> {
  try {
    const encodedWell = encodeURIComponent(wellId);
    let url = `${API_BASE_URL}/api/wells/${encodedWell}/intelligence`;
    if (activeWellId) {
      url += `?active_well_id=${encodeURIComponent(activeWellId)}`;
    }
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchWellFullIntelligence error:", err);
    return null;
  }
}

export async function searchKnowledgeRepository(
  params: KnowledgeSearchParams
): Promise<KnowledgeSearchResponse | null> {
  try {
    const queryParams = new URLSearchParams();
    if (params.q) queryParams.append("q", params.q);
    if (params.well_id) queryParams.append("well_id", params.well_id);
    if (params.event_type) queryParams.append("event_type", params.event_type);
    if (params.domain) queryParams.append("domain", params.domain);
    if (params.document_source) queryParams.append("document_source", params.document_source);
    if (params.min_md !== undefined) queryParams.append("min_md", params.min_md.toString());
    if (params.max_md !== undefined) queryParams.append("max_md", params.max_md.toString());
    if (params.sort_by) queryParams.append("sort_by", params.sort_by);
    if (params.limit !== undefined) queryParams.append("limit", params.limit.toString());
    if (params.offset !== undefined) queryParams.append("offset", params.offset.toString());

    const res = await authFetch(`${API_BASE_URL}/api/knowledge/search?${queryParams.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("searchKnowledgeRepository error:", err);
    return null;
  }
}

export async function fetchAlerts(wellId?: string) {
  try {
    const url = wellId
      ? `${API_BASE_URL}/api/alerts?well_id=${encodeURIComponent(wellId)}`
      : `${API_BASE_URL}/api/alerts`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchAlerts error:", err);
    return { count: 0, alerts: [] };
  }
}

export async function acknowledgeAlertApi(alertId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("acknowledgeAlertApi error:", err);
    return null;
  }
}

export async function investigateAlertApi(alertId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/investigate`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("investigateAlertApi error:", err);
    return null;
  }
}

export async function assignAlertApi(alertId: string, assigneeId: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/assign?assignee_id=${encodeURIComponent(assigneeId)}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("assignAlertApi error:", err);
    return null;
  }
}

export async function fetchAlertNotes(alertId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/notes`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.notes || [];
  } catch (err) {
    console.error("fetchAlertNotes error:", err);
    return [];
  }
}

export async function addAlertNoteApi(alertId: string, noteText: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/notes?note_text=${encodeURIComponent(noteText)}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("addAlertNoteApi error:", err);
    return null;
  }
}

export async function resolveAlertApi(alertId: string, notes: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/api/alerts/${encodeURIComponent(alertId)}/resolve?notes=${encodeURIComponent(notes)}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("resolveAlertApi error:", err);
    return null;
  }
}

export async function fetchAuditLogs(wellId?: string, limit: number = 50) {
  try {
    const url = wellId
      ? `${API_BASE_URL}/api/audit?well_id=${encodeURIComponent(wellId)}&limit=${limit}`
      : `${API_BASE_URL}/api/audit?limit=${limit}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchAuditLogs error:", err);
    return { count: 0, events: [] };
  }
}

export async function fetchNotificationFeed() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNotificationFeed error:", err);
    return { count: 0, unread_count: 0, notifications: [] };
  }
}

export async function markNotificationReadApi(id: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/${encodeURIComponent(id)}/read`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("markNotificationReadApi error:", err);
    return null;
  }
}

export async function markAllNotificationsReadApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/read-all`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("markAllNotificationsReadApi error:", err);
    return null;
  }
}

export async function fetchNotificationPreferences() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/preferences`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNotificationPreferences error:", err);
    return null;
  }
}

export async function updateNotificationPreferencesApi(prefs: Record<string, boolean>) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/preferences`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prefs),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("updateNotificationPreferencesApi error:", err);
    return null;
  }
}

export async function fetchNotificationDeliveries() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/deliveries`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchNotificationDeliveries error:", err);
    return { count: 0, deliveries: [] };
  }
}

export async function evaluateEscalationsApi(timeoutMinutes: number = 30) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/escalate/evaluate?timeout_minutes=${timeoutMinutes}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("evaluateEscalationsApi error:", err);
    return null;
  }
}

export async function fetchDdrReport(wellId: string = "15/9-F-14") {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/reports/ddr?well_id=${encodeURIComponent(wellId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchDdrReport error:", err);
    return null;
  }
}

export async function fetchUserProfile() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/users/me`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchUserProfile error:", err);
    return null;
  }
}

export async function fetchSystemSettings() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/settings`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchSystemSettings error:", err);
    return null;
  }
}


export async function fetchHistoricalProximity(
  activeWellId: string,
  currentMd: number = 3000.0,
  radiusKm: number = 5.0,
  depthWindowM: number = 50.0
): Promise<HistoricalProximityResponse | null> {
  try {
    const encodedWell = encodeURIComponent(activeWellId);
    const url = `${API_BASE_URL}/api/wells/${encodedWell}/historical-proximity?current_md=${currentMd}&radius_km=${radiusKm}&depth_window_m=${depthWindowM}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchHistoricalProximity error:", err);
    return null;
  }
}

export async function uploadDocumentApi(file: File, wellId: string = "15/9-F-14") {
  try {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${API_BASE_URL}/api/documents/upload?well_id=${encodeURIComponent(wellId)}`;
    const res = await authFetch(url, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("uploadDocumentApi error:", err);
    return null;
  }
}

export async function fetchDocumentsApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/documents`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchDocumentsApi error:", err);
    return { count: 0, documents: [] };
  }
}

export async function fetchDocumentDetailsApi(docId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchDocumentDetailsApi error:", err);
    return null;
  }
}

export async function verifyExtractedEventApi(docId: string, eventId: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/events/${encodeURIComponent(eventId)}/verify`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("verifyExtractedEventApi error:", err);
    return null;
  }
}

export async function rejectExtractedEventApi(docId: string, eventId: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/api/documents/${encodeURIComponent(docId)}/events/${encodeURIComponent(eventId)}/reject`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("rejectExtractedEventApi error:", err);
    return null;
  }
}

export async function fetchWellTimeline(wellId: string, category: string = "ALL") {
  try {
    const url = `${API_BASE_URL}/api/wells/${encodeURIComponent(wellId)}/timeline?category=${encodeURIComponent(category)}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchWellTimeline error:", err);
    return { well_id: wellId, count: 0, timeline_events: [] };
  }
}

export async function postShiftNoteApi(wellId: string, noteText: string, currentMd?: number) {
  try {
    let url = `${API_BASE_URL}/api/wells/${encodeURIComponent(wellId)}/timeline/notes?note_text=${encodeURIComponent(noteText)}`;
    if (currentMd !== undefined) {
      url += `&current_md=${currentMd}`;
    }
    const res = await authFetch(url, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("postShiftNoteApi error:", err);
    return null;
  }
}

export async function generateReportApi(
  reportType: string = "DDR",
  wellId: string = "15/9-F-14",
  currentMd: number = 3050.0,
  outgoingEngineer?: string
) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report_type: reportType,
        well_id: wellId,
        current_md: currentMd,
        outgoing_engineer: outgoingEngineer,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("generateReportApi error:", err);
    return null;
  }
}

export async function fetchReportsListApi(wellId?: string) {
  try {
    const url = wellId
      ? `${API_BASE_URL}/api/reports?well_id=${encodeURIComponent(wellId)}`
      : `${API_BASE_URL}/api/reports`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchReportsListApi error:", err);
    return { count: 0, reports: [] };
  }
}

export async function fetchDetailedHealthApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/health/detailed`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchDetailedHealthApi error:", err);
    return null;
  }
}

export async function fetchDataProvenanceApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/provenance`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchDataProvenanceApi error:", err);
    return null;
  }
}

export async function fetchAnalyticsSummaryApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/analytics/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchAnalyticsSummaryApi error:", err);
    return null;
  }
}

export async function fetchWellProfileAnalyticsApi(wellId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/analytics/wells/${encodeURIComponent(wellId)}/profile`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchWellProfileAnalyticsApi error:", err);
    return null;
  }
}

export async function fetchAlertsTrendApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/analytics/alerts/trend`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchAlertsTrendApi error:", err);
    return null;
  }
}

export async function fetchAdminOrganizationsApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/admin/organizations`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("fetchAdminOrganizationsApi error:", err);
    return { status: "ERROR", organizations: [] };
  }
}

export async function updateSystemSettingsApi(payload: Partial<SystemSettings>): Promise<SystemSettings | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("updateSystemSettingsApi error:", err);
    return null;
  }
}

export async function deleteSystemSettingsApi(): Promise<SystemSettings | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/settings`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("deleteSystemSettingsApi error:", err);
    return null;
  }
}

