export interface WellItem {
  well_id: string;
  status: string;
  name?: string;
  field?: string;
  operator?: string;
  latitude?: number;
  longitude?: number;
  water_depth_m?: number;
  slot_name?: string;
}

export interface NearbyWellItem {
  well_id: string;
  name: string;
  distance_km: number;
  distance_m: number;
  latitude: number;
  longitude: number;
  status: string;
  field: string;
  operator: string;
  slot_name: string;
  water_depth_m: number;
}

export interface NearbyWellsResponse {
  active_well: string;
  active_well_metadata: Partial<WellItem>;
  radius_km: number;
  count: number;
  nearby_wells: NearbyWellItem[];
}

export interface WellsResponse {
  wells: WellItem[];
}

export interface WSEventMessage {
  type: "sensor_update" | "ml_update" | "stream_status" | "error" | "alert_created";
  data: any;
}

export interface HistoricalEventEpisode {
  event_episode_id: string;
  event_type: string;
  event_domain: string;
  well_id: string;
  wellbore_id: string;
  onset_timestamp: string;
  onset_md: number;
  onset_tvd?: number | null;
  primary_evidence: string;
  mitigation_text: string;
  resolution_text: string;
  primary_source_record: string;
  source_label: string;
}

export interface WellIntelligenceResponse {
  well_id: string;
  active_well_id?: string | null;
  distance_km?: number | null;
  distance_m?: number | null;
  total_events: number;
  event_counts: Record<string, number>;
  events: HistoricalEventEpisode[];
  well_metadata?: WellItem;
  provenance: string;
}

export interface KnowledgeSearchResponse {
  query: string;
  total_count: number;
  results: HistoricalEventEpisode[];
  provenance: string;
}

export interface KnowledgeSearchParams {
  q?: string;
  well_id?: string;
  event_type?: string;
  domain?: string;
  document_source?: string;
  min_md?: number;
  max_md?: number;
  sort_by?: string;
  limit?: number;
  offset?: number;
}

export interface HistoricalProximityMatch {
  event_episode_id: string;
  offset_well_id: string;
  offset_well_distance_km: number;
  offset_well_distance_m: number;
  event_type: string;
  event_domain: string;
  event_md: number;
  event_tvd?: number | null;
  current_md: number;
  delta_md: number;
  proximity_classification: string;
  primary_evidence: string;
  mitigation_text: string;
  resolution_text: string;
  primary_source_record: string;
  source_label: string;
  disclaimer: string;
  is_verified: boolean;
}

export interface HistoricalProximityResponse {
  active_well_id: string;
  current_md: number;
  radius_km: number;
  depth_window_m: number;
  nearby_wells_checked: number;
  matches_count: number;
  matches: HistoricalProximityMatch[];
  disclaimer: string;
  provenance: string;
}

export interface AlertItem {
  alert_id: string;
  well_id: string;
  title: string;
  description: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  source: string;
  current_md: number;
  evidence: string;
  source_record?: string;
  disclaimer: string;
  status: "ACTIVE" | "ACKNOWLEDGED" | "INVESTIGATING" | "RESOLVED" | "DISMISSED";
  created_at: string;
  updated_at: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  investigating_by?: string;
  investigating_at?: string;
  assigned_to?: string;
  resolved_by?: string;
  resolved_at?: string;
  resolution_notes?: string;
}

export interface AlertNoteItem {
  id: string;
  alert_id: string;
  author_id: string;
  note_text: string;
  created_at: string;
}

export interface AlertsResponse {
  count: number;
  alerts: AlertItem[];
}

export interface AuditEvent {
  audit_id: string;
  timestamp: string;
  actor_id: string;
  actor_role?: string;
  action: string;
  resource_type: string;
  resource_id: string;
  well_id?: string;
  organization_id?: string;
  payload: Record<string, any>;
  before_state?: Record<string, any>;
  after_state?: Record<string, any>;
  tenant_id?: string;
}

export interface AuditLogsResponse {
  count: number;
  events: AuditEvent[];
}

export interface UserInfo {
  user_id: string;
  email: string;
  role: string;
  tenant_id: string;
  permissions: string[];
}

export interface SystemSettings {
  user_id?: string;
  user_email?: string;
  user_role?: string;
  search_radius_km_default: number;
  depth_window_m_default: number;
  telemetry_stream_url: string;
  notification_recipient_email?: string;
  email_rate_limit_per_sec?: number;
  send_to_login_account?: boolean;
  email_enabled?: boolean;
  critical_alerts?: boolean;
  high_alerts?: boolean;
  medium_alerts?: boolean;
  historical_alerts?: boolean;
  system_notifications?: boolean;
  report_notifications?: boolean;
  resend_notifications_enabled: boolean;
  supabase_persistence_enabled: boolean;
  ml_readiness_gate_enforced: boolean;
  updated_at?: string;
}

export interface AnalyticsSummary {
  status: string;
  total_active_alerts: number;
  total_alerts: number;
  alert_severity_breakdown: Record<string, number>;
  alert_status_breakdown: Record<string, number>;
  monitored_wells_count: number;
  nwis_dataset_source: string;
  knowledge_records_count: number;
}

export interface WellProfileAnalytics {
  well_id: string;
  field: string;
  operator: string;
  spud_year: number;
  total_depth_md_m: number;
  max_tvd_m: number;
  drilling_days: number;
  historical_events_count: number;
  event_type_distribution: Record<string, number>;
  depth_range_distribution: Array<{
    range: string;
    event_count: number;
    primary_risk: string;
  }>;
  severity_breakdown: Record<string, number>;
}

export interface AlertTrendPoint {
  date: string;
  CRITICAL: number;
  HIGH: number;
  MEDIUM: number;
  LOW: number;
}

export interface OrganizationItem {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  isolation_policy: string;
}


