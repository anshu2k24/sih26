import logging
from typing import List, Dict, Any, Optional
from ertmac.nwis.geospatial import GeospatialIntelligence

logger = logging.getLogger("nwis_depth_correlation")

DISCLAIMER_TEXT = "HISTORICAL OFFSET EVENT — NOT A PREDICTION"


class DepthCorrelationEngine:
    def __init__(self, geospatial_engine: GeospatialIntelligence, nwis_historical_api: Any):
        self.geospatial = geospatial_engine
        self.nwis_api = nwis_historical_api

    def evaluate_historical_proximity(
        self,
        active_well_id: str,
        current_md: float,
        radius_km: float = 5.0,
        depth_window_m: float = 50.0,
        organization_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically correlates current active drilling position (current_md)
        with verified historical DDR events in nearby offset wells.
        """
        # Find nearby offset wells using Geospatial Engine
        nearby_wells = self.geospatial.find_nearby_wells(
            active_well_id,
            organization_id=organization_id,
            radius_km=radius_km
        )

        matches = []

        if self.nwis_api:
            for nw in nearby_wells:
                offset_w_id = nw["well_id"]
                dist_km = nw["distance_km"]
                dist_m = nw["distance_m"]

                # Fetch all verified events for this offset well
                well_intel = self.nwis_api.get_well_full_intelligence(offset_w_id)
                events = well_intel.get("events", [])

                for ev in events:
                    event_md = ev.get("onset_md", 0.0)
                    delta_md = abs(event_md - current_md)

                    if delta_md <= depth_window_m:
                        # Categorize proximity based strictly on delta_md threshold
                        if delta_md <= 25.0:
                            classification = "Very Close Historical Event"
                        else:
                            classification = "Historical Event Nearby"

                        rec_id = ev.get("primary_source_record", "DDR_REPORT")

                        matches.append({
                            "event_episode_id": ev.get("event_episode_id"),
                            "offset_well_id": offset_w_id,
                            "offset_well_distance_km": dist_km,
                            "offset_well_distance_m": dist_m,
                            "event_type": ev.get("event_type"),
                            "event_domain": ev.get("event_domain", "DRILLING_EVENT"),
                            "event_md": round(event_md, 1),
                            "event_tvd": round(ev["onset_tvd"], 1) if ev.get("onset_tvd") is not None else None,
                            "current_md": round(current_md, 1),
                            "delta_md": round(delta_md, 1),
                            "proximity_classification": classification,
                            "primary_evidence": ev.get("primary_evidence"),
                            "mitigation_text": ev.get("mitigation_text", "None recorded"),
                            "resolution_text": ev.get("resolution_text", "None recorded"),
                            "primary_source_record": rec_id,
                            "source_label": f"Equinor Volve DDR ({rec_id})",
                            "disclaimer": DISCLAIMER_TEXT,
                            "is_verified": True
                        })

        # Sort matches strictly by smallest delta_md (closest depth difference first)
        matches.sort(key=lambda x: (x["delta_md"], x["offset_well_distance_km"]))

        # Deduplicate matches by event_episode_id (keep the closest match if an episode is matched via multiple well aliases)
        unique_matches = []
        seen_episodes = set()
        for m in matches:
            ep_id = m.get("event_episode_id")
            if ep_id:
                if ep_id in seen_episodes:
                    continue
                seen_episodes.add(ep_id)
            unique_matches.append(m)
        matches = unique_matches

        return {
            "active_well_id": active_well_id,
            "current_md": round(current_md, 1),
            "radius_km": radius_km,
            "depth_window_m": depth_window_m,
            "nearby_wells_checked": len(nearby_wells),
            "matches_count": len(matches),
            "matches": matches,
            "disclaimer": DISCLAIMER_TEXT,
            "provenance": "Deterministically correlated from Equinor Volve verified DDR semantic audit and surface coordinates."
        }
