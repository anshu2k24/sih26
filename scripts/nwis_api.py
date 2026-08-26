import pandas as pd
import numpy as np

class NWISHistoricalAPI:
    def __init__(self, verified_events_path):
        self.df_events = pd.read_csv(verified_events_path)
        # Drop episodes missing onset_md
        self.df_events = self.df_events[self.df_events['onset_md'].notnull()].copy()
        
    def get_intelligence_by_depth(self, active_well_id: str, current_md: float, radius: float = 100.0, event_type: str = None):
        """
        Retrieves historical offset intelligence around a specific active well and depth.
        """
        # Filter out the active well itself (only look at offset/historical wells)
        df_offsets = self.df_events[self.df_events['wellbore_id'] != active_well_id].copy()
        
        # Optional event filter
        if event_type:
            df_offsets = df_offsets[df_offsets['event_type'] == event_type]
            
        # Depth window filter
        df_offsets['depth_distance_m'] = (df_offsets['onset_md'] - current_md).abs()
        df_nearby = df_offsets[df_offsets['depth_distance_m'] <= radius].copy()
        
        # Deterministic scoring & sorting
        # Score = 1.0 - (distance / max_radius) - max 1.0, min 0.0
        # If radius is 0, score is 1.0
        if radius > 0:
            df_nearby['similarity_score'] = (1.0 - (df_nearby['depth_distance_m'] / radius)).clip(0.0, 1.0).round(2)
        else:
            df_nearby['similarity_score'] = 1.0
            
        # Sort by distance (ascending) -> relevance (descending)
        df_nearby = df_nearby.sort_values('depth_distance_m', ascending=True)
        
        # Build response
        nearby_events = []
        relevant_wells = set()
        historical_mitigations = set()
        
        for _, ep in df_nearby.iterrows():
            dist = ep['depth_distance_m']
            score = ep['similarity_score']
            
            reasons = [
                f"Historical {ep['event_type']} encountered in {ep['wellbore_id']}",
                f"Onset depth is {ep['onset_md']}m (Distance: {dist:.1f}m)",
            ]
            
            event_obj = {
                "offset_wellbore": ep['wellbore_id'],
                "event_type": ep['event_type'],
                "event_domain": ep['event_domain'],
                "onset_md": ep['onset_md'],
                "depth_distance_m": dist,
                "primary_evidence": ep['primary_evidence'],
                "mitigation": ep['mitigation_text'] if pd.notnull(ep['mitigation_text']) else "None recorded",
                "resolution": ep['resolution_text'] if pd.notnull(ep['resolution_text']) else "None recorded",
                "source_ddr_record": ep['primary_source_record'],
                "similarity_score": score,
                "similarity_reasons": "; ".join(reasons)
            }
            nearby_events.append(event_obj)
            relevant_wells.add(ep['wellbore_id'])
            
            if pd.notnull(ep['mitigation_text']):
                historical_mitigations.add(ep['mitigation_text'])
                
        risk_summary = "Historical nearby-well evidence detected." if len(nearby_events) > 0 else "No historical evidence detected within the specified depth window."
        
        return {
            "active_well": active_well_id,
            "current_md": current_md,
            "search_radius_m": radius,
            "nearby_events": nearby_events,
            "relevant_wells": list(relevant_wells),
            "risk_summary": risk_summary,
            "historical_mitigations": list(historical_mitigations),
            "provenance": "All evidence extracted deterministically from Equinor Volve verified DDR semantic audit. No generative AI claims used."
        }
