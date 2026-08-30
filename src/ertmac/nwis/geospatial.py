import json
import math
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nwis_geospatial")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes precise Haversine distance in kilometers between two lat/lon coordinates.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class GeospatialIntelligence:
    def __init__(self, well_metadata_path: Optional[str] = None):
        self.well_metadata_path = well_metadata_path
        self.coords: Dict[str, Dict[str, Any]] = {}
        self.coordinates_available = False
        self._load_coordinates()

    def _load_coordinates(self) -> None:
        # If explicit path provided by caller/test harness, load directly
        if self.well_metadata_path:
            file_path = Path(self.well_metadata_path)
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.coords = json.load(f)
                    if self.coords:
                        self.coordinates_available = True
                        return
                except Exception as e:
                    logger.error(f"Error loading well coordinates from {self.well_metadata_path}: {e}")

        import os
        is_prod = os.getenv("ENVIRONMENT", "").lower() == "production"

        # Priority 1: Load from Supabase wellbores table
        if self._load_from_supabase():
            return

        # In production, NEVER fall back to local files
        if is_prod:
            logger.error("[PRODUCTION] Failed to load well coordinates from Supabase wellbores table. Local JSON fallback is disabled in production.")
            return

        # Priority 2: Fallback to local JSON file (development only)
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        path = repo_root / "data" / "processed" / "usrop" / "well_coordinates.json"

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.coords = json.load(f)
                if self.coords:
                    self.coordinates_available = True
                    logger.info(f"Loaded {len(self.coords)} well coordinates from local JSON fallback (development only).")
            except Exception as e:
                logger.error(f"Error loading well coordinates from {path}: {e}")

    def _load_from_supabase(self) -> bool:
        """Attempt to load well coordinates from Supabase wellbores table."""
        try:
            from ertmac.auth.supabase_client import get_supabase_admin
            db = get_supabase_admin()
            if not db:
                return False

            res = db.table("wellbores").select("*").execute()
            if not res.data or len(res.data) == 0:
                return False

            for row in res.data:
                well_id = row.get("id", "")
                self.coords[well_id] = {
                    "well_id": well_id,
                    "name": row.get("name", well_id),
                    "field": row.get("field", "Volve"),
                    "operator": row.get("operator", "Equinor"),
                    "status": row.get("status", "Historical"),
                    "latitude": row.get("latitude"),
                    "longitude": row.get("longitude"),
                    "water_depth_m": row.get("water_depth_m", 84.0),
                    "slot_name": row.get("slot_name"),
                }

            if self.coords:
                self.coordinates_available = True
                logger.info(f"Loaded {len(self.coords)} well coordinates from Supabase.")
            return True

        except Exception as e:
            logger.warning(f"Failed to load coordinates from Supabase (will use JSON fallback): {e}")
            return False

    def find_nearby_wells(self, active_well_id: str, radius_km: float = 5.0) -> List[Dict[str, Any]]:
        if not self.coordinates_available or active_well_id not in self.coords:
            logger.warning(
                f"Coordinates unavailable for active well '{active_well_id}'. "
                "Returning empty nearby wells list per missing data policy."
            )
            return []

        active_info = self.coords[active_well_id]
        active_lat = active_info.get("latitude")
        active_lon = active_info.get("longitude")

        if active_lat is None or active_lon is None:
            return []

        nearby = []
        for w_id, w_info in self.coords.items():
            if w_id == active_well_id:
                continue

            lat = w_info.get("latitude")
            lon = w_info.get("longitude")
            if lat is None or lon is None:
                continue

            dist_km = haversine_distance_km(active_lat, active_lon, lat, lon)
            if dist_km <= radius_km:
                nearby.append({
                    "well_id": w_id,
                    "name": w_info.get("name", w_id),
                    "distance_km": round(dist_km, 3),
                    "distance_m": round(dist_km * 1000.0, 1),
                    "latitude": lat,
                    "longitude": lon,
                    "status": w_info.get("status", "Historical"),
                    "field": w_info.get("field", "Volve"),
                    "operator": w_info.get("operator", "Equinor"),
                    "slot_name": w_info.get("slot_name", "N/A"),
                    "water_depth_m": w_info.get("water_depth_m", 84.0)
                })

        # Sort strictly by ascending distance
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

