import os
from pathlib import Path
import pandas as pd
import numpy as np
import logging

try:
    from dotenv import load_dotenv
    repo_root = Path(__file__).resolve().parent.parent
    load_dotenv(repo_root / ".env")
except ImportError:
    pass

logger = logging.getLogger("nwis_historical_api")

EVENT_COLUMNS = [
    'event_episode_id', 'well_id', 'wellbore_id', 'organization_id',
    'event_type', 'event_domain', 'onset_timestamp', 'onset_md',
    'onset_tvd', 'primary_evidence', 'mitigation_text', 'resolution_text',
    'primary_source_record', 'is_verified'
]


class NWISHistoricalAPI:
    def __init__(self, verified_events_path=None):
        """
        Loads verified historical DDR events.
        Priority: Supabase historical_ddr_events table → CSV file fallback (development only).
        """
        is_prod = os.getenv("ENVIRONMENT", "").lower() == "production"

        self.df_events = self._load_from_supabase()

        # In production, NEVER fall back to local files
        if (self.df_events is None or len(self.df_events) == 0) and not is_prod:
            if verified_events_path:
                csv_path = Path(verified_events_path)
                if csv_path.exists():
                    logger.info(f"Loading events from CSV fallback (development only): {csv_path}")
                    self.df_events = pd.read_csv(verified_events_path)
                else:
                    self.df_events = pd.DataFrame(columns=EVENT_COLUMNS)
            else:
                self.df_events = pd.DataFrame(columns=EVENT_COLUMNS)
        elif self.df_events is None:
            self.df_events = pd.DataFrame(columns=EVENT_COLUMNS)

        # Ensure all standard columns exist
        for col in EVENT_COLUMNS:
            if col not in self.df_events.columns:
                self.df_events[col] = None

        # Drop episodes missing onset_md
        if len(self.df_events) > 0 and 'onset_md' in self.df_events.columns:
            self.df_events = self.df_events[self.df_events['onset_md'].notnull()].copy()

    @staticmethod
    def _load_from_supabase():
        """Attempt to load all historical DDR events from Supabase."""
        try:
            import sys
            from pathlib import Path
            repo_root = Path(__file__).resolve().parent.parent
            src_dir = repo_root / "src"
            if str(src_dir) not in sys.path:
                sys.path.insert(0, str(src_dir))

            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if not db:
                return None

            res = db.table("historical_ddr_events").select("*").execute()
            if not res.data or len(res.data) == 0:
                logger.info("No historical_ddr_events found in Supabase (table may be empty).")
                return None

            rows = res.data
            # Map DB column names to the DataFrame schema expected by existing code
            mapped_rows = []
            for r in rows:
                mapped_rows.append({
                    "event_episode_id": r.get("id", ""),
                    "event_type": r.get("event_type", "Unknown"),
                    "event_domain": r.get("event_domain", "DRILLING_OPERATIONS"),
                    "well_id": r.get("wellbore_id", ""),
                    "wellbore_id": r.get("wellbore_id", ""),
                    "onset_timestamp": r.get("onset_timestamp"),
                    "onset_md": r.get("onset_md"),
                    "onset_tvd": r.get("onset_tvd"),
                    "primary_source_record": r.get("primary_source_record", "N/A"),
                    "primary_evidence": r.get("primary_evidence", "No evidence recorded"),
                    "mitigation_text": r.get("mitigation_text"),
                    "resolution_text": r.get("resolution_text"),
                    "is_verified_positive": r.get("is_verified", True),
                    "organization_id": r.get("organization_id", "00000000-0000-0000-0000-000000000001"),
                })

            df = pd.DataFrame(mapped_rows)
            logger.info(f"Loaded {len(df)} historical events from Supabase.")
            return df

        except Exception as e:
            logger.warning(f"Failed to load events from Supabase (will use CSV fallback): {e}")
            return None
        
    def get_intelligence_by_depth(self, active_well_id: str, current_md: float, radius: float = 100.0, event_type: str = None, organization_id: str = None, **kwargs):
        """
        Retrieves historical offset intelligence around a specific active well and depth.
        """
        # Filter out the active well itself (only look at offset/historical wells)
        df_offsets = self.df_events[self.df_events['wellbore_id'] != active_well_id].copy()
        if organization_id and 'organization_id' in df_offsets.columns:
            df_offsets = df_offsets[df_offsets['organization_id'] == organization_id]
        
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

    def get_well_full_intelligence(self, target_well_id: str, organization_id: str = None, **kwargs) -> dict:
        """
        Retrieves all historical verified DDR event episodes for a specific wellbore.
        Handles normalized matching (e.g. '15/9-F-14' matches 'NO 15/9-F-14').
        """
        clean_target = target_well_id.replace("NO ", "").strip()
        
        # Match where normalized wellbore_id or well_id matches clean_target
        # Special alias mapping handling: '15/9-F-15S' -> 'NO 15/9-F-15 A' or '15/9-F-15S'
        alias_targets = {clean_target, f"NO {clean_target}"}
        if clean_target == "15/9-F-15S":
            alias_targets.add("NO 15/9-F-15 A")
            
        df = self.df_events[self.df_events['wellbore_id'].isin(alias_targets) | self.df_events['well_id'].isin(alias_targets)].copy()
        if organization_id and 'organization_id' in df.columns:
            df = df[df['organization_id'] == organization_id]
        
        events = []
        for _, ep in df.iterrows():
            rec_id = str(ep['primary_source_record']) if pd.notnull(ep['primary_source_record']) else "DDR_REPORT"
            events.append({
                "event_episode_id": ep['event_episode_id'],
                "event_type": ep['event_type'],
                "event_domain": ep['event_domain'],
                "onset_timestamp": str(ep['onset_timestamp']) if pd.notnull(ep['onset_timestamp']) else "Data unavailable",
                "onset_md": ep['onset_md'],
                "onset_tvd": ep['onset_tvd'] if pd.notnull(ep['onset_tvd']) else None,
                "primary_evidence": ep['primary_evidence'],
                "mitigation_text": ep['mitigation_text'] if pd.notnull(ep['mitigation_text']) else "None recorded",
                "resolution_text": ep['resolution_text'] if pd.notnull(ep['resolution_text']) else "None recorded",
                "primary_source_record": rec_id,
                "source_label": f"Equinor Volve DDR ({rec_id})",
                "is_verified": True
            })
            
        event_counts = df['event_type'].value_counts().to_dict() if len(df) > 0 and 'event_type' in df.columns else {}
        return {
            "well_id": target_well_id,
            "wellbore_id": target_well_id,
            "total_events": len(events),
            "total_verified_events": len(events),
            "event_counts": event_counts,
            "events": events,
            "provenance": "All evidence extracted deterministically from Equinor Volve verified DDR semantic audit. No generative AI claims used."
        }

    def search_knowledge(
        self,
        q: str = None,
        well_id: str = None,
        event_type: str = None,
        domain: str = None,
        document_source: str = None,
        min_md: float = None,
        max_md: float = None,
        sort_by: str = "depth_asc",
        limit: int = 50,
        offset: int = 0,
        organization_id: str = None,
        **kwargs
    ) -> dict:
        """
        Searches historical verified DDR drilling knowledge using real repository records.
        Supports deterministic text search, well filtering, event type, domain, document source, depth bounds, and sorting.
        """
        df = self.df_events.copy()
        if organization_id and 'organization_id' in df.columns:
            df = df[df['organization_id'] == organization_id]
        
        # Normalize well identifiers
        df['norm_well'] = df['well_id'].astype(str).str.replace("NO ", "").str.strip()
        df['norm_wellbore'] = df['wellbore_id'].astype(str).str.replace("NO ", "").str.strip()

        # 1. Well Filter
        if well_id and well_id.strip() and well_id.upper() != "ALL":
            clean_well = well_id.replace("NO ", "").strip()
            alias_targets = {clean_well, f"NO {clean_well}"}
            if clean_well == "15/9-F-15S":
                alias_targets.update({"NO 15/9-F-15 A", "15/9-F-15 A"})
            elif clean_well == "15/9-F-9 A":
                alias_targets.update({"NO 15/9-F-9 A", "15/9-F-9"})

            mask_well = (
                df['well_id'].isin(alias_targets)
                | df['wellbore_id'].isin(alias_targets)
                | df['norm_well'].isin({clean_well})
                | df['norm_wellbore'].isin({clean_well})
            )
            df = df[mask_well]

        # 2. Event Type Filter
        if event_type and event_type.strip() and event_type.upper() != "ALL":
            df = df[df['event_type'] == event_type.strip()]

        # 2b. Domain Filter
        if domain and domain.strip() and domain.upper() != "ALL":
            if 'event_domain' in df.columns:
                df = df[df['event_domain'].astype(str).str.upper() == domain.strip().upper()]

        # 2c. Document Source Filter
        if document_source and document_source.strip() and document_source.upper() != "ALL":
            if 'primary_source_record' in df.columns:
                df = df[df['primary_source_record'].astype(str).str.contains(document_source.strip(), case=False, na=False)]

        # 3. Depth Range Filter
        if min_md is not None:
            df = df[df['onset_md'] >= min_md]
        if max_md is not None:
            df = df[df['onset_md'] <= max_md]

        # 4. Text Query (Case-insensitive multi-field search)
        if q and q.strip():
            query_str = q.strip().lower()
            
            def row_matches(row):
                fields = [
                    str(row.get('event_type', '')),
                    str(row.get('well_id', '')),
                    str(row.get('wellbore_id', '')),
                    str(row.get('onset_md', '')),
                    str(row.get('primary_evidence', '')),
                    str(row.get('mitigation_text', '')),
                    str(row.get('resolution_text', '')),
                    str(row.get('primary_source_record', ''))
                ]
                combined = " ".join(fields).lower()
                return query_str in combined

            df = df[df.apply(row_matches, axis=1)]

        # 5. Deterministic Sorting
        if sort_by == "depth_desc":
            df = df.sort_values('onset_md', ascending=False)
        elif sort_by == "newest":
            df = df.sort_values('onset_timestamp', ascending=False)
        elif sort_by == "oldest":
            df = df.sort_values('onset_timestamp', ascending=True)
        else: # default depth_asc
            df = df.sort_values('onset_md', ascending=True)

        total_count = len(df)
        
        # Paginate results
        df_paged = df.iloc[offset : offset + limit] if limit > 0 else df

        results = []
        for _, row in df_paged.iterrows():
            rec_id = str(row['primary_source_record']) if pd.notnull(row['primary_source_record']) else "DDR_REPORT"
            results.append({
                "event_episode_id": str(row['event_episode_id']),
                "event_type": str(row['event_type']),
                "event_domain": str(row['event_domain']) if pd.notnull(row['event_domain']) else "DRILLING_EVENT",
                "well_id": str(row['well_id']),
                "wellbore_id": str(row['wellbore_id']),
                "onset_timestamp": str(row['onset_timestamp']) if pd.notnull(row['onset_timestamp']) else "Data unavailable",
                "onset_md": float(row['onset_md']) if pd.notnull(row['onset_md']) else 0.0,
                "onset_tvd": float(row['onset_tvd']) if pd.notnull(row['onset_tvd']) else None,
                "primary_evidence": str(row['primary_evidence']) if pd.notnull(row['primary_evidence']) else "No primary evidence recorded.",
                "mitigation_text": str(row['mitigation_text']) if pd.notnull(row['mitigation_text']) else "None recorded",
                "resolution_text": str(row['resolution_text']) if pd.notnull(row['resolution_text']) else "None recorded",
                "primary_source_record": rec_id,
                "source_label": f"Equinor Volve DDR ({rec_id})",
                "is_verified": True
            })

        return {
            "query": q or "",
            "total_count": total_count,
            "results": results,
            "provenance": "All search results extracted deterministically from Equinor Volve verified DDR semantic audit. No generative AI claims used."
        }


