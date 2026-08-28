export interface NearbyEvent {
  offset_wellbore: string;
  event_type: string;
  event_domain: string;
  onset_md: number;
  depth_distance_m: number;
  primary_evidence: string;
  mitigation: string;
  resolution: string;
  source_ddr_record: string;
  similarity_score: number;
  similarity_reasons: string;
}

export interface EventsResponse {
  active_well: string;
  current_md: number;
  search_radius_m: number;
  risk_summary: string;
  nearby_events: NearbyEvent[];
  relevant_wells: string[];
  provenance: string;
}
