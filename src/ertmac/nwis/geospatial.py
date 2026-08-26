import logging
import pandas as pd

logger = logging.getLogger("nwis_geospatial")

class GeospatialIntelligence:
    def __init__(self, well_metadata_path: str = None):
        self.well_metadata_path = well_metadata_path
        self.coordinates_available = False
        
        # Volve DDR does not contain lat/lon/northing/easting.
        # This layer acts as a strict contract that refuses to invent data.
        
    def find_nearby_wells(self, active_well_id: str, radius_km: float) -> list:
        if not self.coordinates_available:
            logger.warning(
                "Geospatial coordinates are not available in the current Volve dataset. "
                "Returning all offset wells instead of inventing fake proximity."
            )
            # In a real environment with coordinates, this would filter by radius_km.
            # Here we strictly enforce the reality of missing data.
            return []
        
        # Future implementation when real OIL data provides coordinates:
        raise NotImplementedError("Geospatial calculations pending real coordinate ingestion.")
