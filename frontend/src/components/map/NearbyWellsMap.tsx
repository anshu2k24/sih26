import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Map, { Source, Layer, NavigationControl, FullscreenControl, Marker, Popup } from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import circle from "@turf/circle";
import { point } from "@turf/helpers";

import type { WellItem, NearbyWellItem, NearbyWellsResponse } from "../../types/api";
import { fetchNearbyWells } from "../../services/api";
import { MapPin, Navigation, Compass, Layers, Crosshair, Globe, ShieldAlert, Sparkles, ArrowRight } from "lucide-react";

// Map Layer Types:
// 1. "dark": OpenStreetMap (from v04) filtered to dark night-mode matching sih2k26 background (NO API KEY / NO WATERMARK)
// 2. "osm": Natural OpenStreetMap (the exact street/area map from v04)
// 3. "ocean": Official Ocean Bathymetry map (marine depth contours & sea floor)
// 4. "satellite": High-resolution satellite imagery (Esri World Imagery)
export type MapLayerType = "dark" | "osm" | "ocean" | "satellite";

const MAP_TILE_CONFIGS: Record<MapLayerType, { name: string; label: string; description: string; style: any }> = {
  dark: {
    name: "Dark (sih2k26)",
    label: "DARK (SIH26)",
    description: "OSM tiles styled for deep dark background",
    style: {
      version: 8,
      sources: {
        "osm-dark-tiles": {
          type: "raster",
          tiles: [
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          attribution: "&copy; OpenStreetMap contributors",
        },
      },
      layers: [
        {
          id: "osm-dark-layer",
          type: "raster",
          source: "osm-dark-tiles",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
    },
  },
  osm: {
    name: "OpenStreetMap (v04)",
    label: "OSM (V04)",
    description: "Original clean OpenStreetMap from v04",
    style: {
      version: 8,
      sources: {
        "osm-clean-tiles": {
          type: "raster",
          tiles: [
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          attribution: "&copy; OpenStreetMap contributors",
        },
      },
      layers: [
        {
          id: "osm-clean-layer",
          type: "raster",
          source: "osm-clean-tiles",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
    },
  },
  ocean: {
    name: "Ocean Bathymetry",
    label: "OCEAN BATHYMETRY",
    description: "Marine depth contours & offshore seafloor",
    style: {
      version: 8,
      sources: {
        "esri-ocean": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "&copy; Esri &mdash; Ocean Basemap",
        },
      },
      layers: [
        {
          id: "esri-ocean-layer",
          type: "raster",
          source: "esri-ocean",
          minzoom: 0,
          maxzoom: 16,
        },
      ],
    },
  },
  satellite: {
    name: "Satellite",
    label: "SATELLITE",
    description: "High-resolution satellite view",
    style: {
      version: 8,
      sources: {
        "esri-satellite": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 12,
          attribution: "&copy; Esri &mdash; World Imagery",
        },
      },
      layers: [
        {
          id: "esri-satellite-layer",
          type: "raster",
          source: "esri-satellite",
          minzoom: 0,
          maxzoom: 12,
        },
      ],
    },
  },
};

interface NearbyWellsMapProps {
  wells: WellItem[];
  selectedWell: string;
  onSelectWell: (wellId: string) => void;
  onOpenIntelligence?: (wellId: string) => void;
  proximityMatches?: any[];
}

export const NearbyWellsMap: React.FC<NearbyWellsMapProps> = ({
  wells,
  selectedWell,
  onSelectWell,
  onOpenIntelligence,
  proximityMatches = [],
}) => {
  const mapRef = useRef<MapRef>(null);
  // Default to Satellite view as requested by user
  const [selectedLayer, setSelectedLayer] = useState<MapLayerType>("satellite");
  const [radiusKm, setRadiusKm] = useState<number>(5.0);
  const [nearbyData, setNearbyData] = useState<NearbyWellsResponse | null>(null);
  const [activeWellCoords, setActiveWellCoords] = useState<[number, number] | null>(null);
  const [selectedNearbyWellId, setSelectedNearbyWellId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hoverInfo, setHoverInfo] = useState<any | null>(null);
  const [cursorCoords, setCursorCoords] = useState<[number, number] | null>(null);
  const lastFitWellId = useRef<string | null>(null);

  const activeWellItem = wells.find((w) => w.well_id === selectedWell);

  // Fetch nearby wells whenever active well or search radius changes
  useEffect(() => {
    setIsLoading(true);
    fetchNearbyWells(selectedWell, radiusKm).then((res) => {
      setNearbyData(res);
      setIsLoading(false);

      if (res && res.active_well_metadata?.latitude && res.active_well_metadata?.longitude) {
        setActiveWellCoords([
          res.active_well_metadata.longitude, // MapLibre uses [lng, lat]
          res.active_well_metadata.latitude,
        ]);
      } else if (activeWellItem?.latitude && activeWellItem?.longitude) {
        setActiveWellCoords([activeWellItem.longitude, activeWellItem.latitude]);
      } else {
        setActiveWellCoords([1.88778, 58.44168]); // Default Volve field center
      }
    });
  }, [selectedWell, radiusKm, activeWellItem]);

  // Maintain the user's preferred regional view (showing Scottish coast, Norway coast, and North Sea basin)
  useEffect(() => {
    if (lastFitWellId.current === null) {
      // Preserve user's default regional view frame on initial load
      lastFitWellId.current = selectedWell;
      return;
    }

    if (activeWellCoords && mapRef.current && lastFitWellId.current !== selectedWell) {
      mapRef.current.flyTo({
        center: [2.6, 58.7],
        zoom: 5.85,
        duration: 1200,
      });
      lastFitWellId.current = selectedWell;
    }
  }, [activeWellCoords, selectedWell]);

  const radiusOptions = [0.5, 1.0, 5.0, 10.0, 25.0];

  const formatDistance = (distKm: number, distM: number) => {
    if (distKm < 1.0) {
      return `${distM.toFixed(0)} m`;
    }
    return `${distKm.toFixed(2)} km`;
  };

  // Generate GeoJSON for Nearby Wells (with spider layout for tight platform clusters)
  const nearbyGeoJson = useMemo(() => {
    if (!nearbyData?.nearby_wells) return { type: "FeatureCollection", features: [] };

    const features = nearbyData.nearby_wells.map((nw, index) => {
      let lng = Number(nw.longitude);
      let lat = Number(nw.latitude);

      // If distance is very small (same platform cluster), spread them in a concentric spiral
      if (nw.distance_km < 0.1) {
        const ringSpacing = 0.025; // ~2.5km offset to clearly show individual wells
        const pointsPerRing = 8;
        const ring = Math.floor(index / pointsPerRing) + 1;
        const currentRingPoints = ring * pointsPerRing;

        const angle = index * ((Math.PI * 2) / currentRingPoints);
        const jitterRadius = ring * ringSpacing;

        lng += jitterRadius * Math.cos(angle);
        lat += jitterRadius * Math.sin(angle);
      }

      const matchForWell = proximityMatches.find(
        (pm: any) => pm.offset_well_id.replace("NO ", "") === nw.well_id.replace("NO ", "")
      );
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [lng, lat] },
        properties: {
          id: nw.well_id,
          name: nw.name,
          status: nw.status,
          distance_km: nw.distance_km,
          distance_m: nw.distance_m,
          water_depth_m: nw.water_depth_m,
          slot_name: nw.slot_name,
          has_alert: Boolean(matchForWell),
          is_selected: nw.well_id === selectedNearbyWellId,
          match: matchForWell ? JSON.stringify(matchForWell) : null,
        },
      };
    });

    return { type: "FeatureCollection", features };
  }, [nearbyData, proximityMatches, selectedNearbyWellId]);

  // Generate GeoJSON for the Radius Circle
  const radiusGeoJson = useMemo(() => {
    if (!activeWellCoords) return { type: "FeatureCollection", features: [] };
    const center = point(activeWellCoords);
    const options = { steps: 64, units: "kilometers" as const };
    const circleFeature = circle(center, radiusKm, options);
    return { type: "FeatureCollection", features: [circleFeature] };
  }, [activeWellCoords, radiusKm]);

  const onHover = useCallback((event: any) => {
    if (event.lngLat) {
      setCursorCoords([event.lngLat.lng, event.lngLat.lat]);
    }
  }, []);

  const navigate = useNavigate();

  const handleNavigateToWell = useCallback(
    (wellId: string) => {
      if (onOpenIntelligence) {
        onOpenIntelligence(wellId);
      } else {
        navigate(`/wells/${encodeURIComponent(wellId)}`);
      }
    },
    [onOpenIntelligence, navigate]
  );

  const onClick = useCallback((event: any) => {
    const feature = event.features && event.features[0];
    if (feature && feature.properties?.id) {
      setSelectedNearbyWellId(feature.properties.id);
      handleNavigateToWell(feature.properties.id);
    } else {
      setSelectedNearbyWellId(null);
    }
  }, [handleNavigateToWell]);

  const currentMapStyle = MAP_TILE_CONFIGS[selectedLayer].style;

  return (
    <div
      className="rounded-2xl p-5 shadow-2xl space-y-4 transition-all duration-300"
      style={{
        background: "rgba(14, 13, 12, 0.85)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        border: "1px solid rgba(255, 122, 0, 0.22)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.6), inset 0 0 24px rgba(255, 122, 0, 0.04)",
      }}
    >
      {/* Header Controls Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[rgba(255,122,0,0.15)] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[rgba(255,122,0,0.12)] border border-[rgba(255,122,0,0.3)] flex items-center justify-center shadow-[0_0_12px_rgba(255,122,0,0.2)]">
              <Compass className="w-4 h-4 text-[#FF7A00]" />
            </div>
            <h2 className="text-[15px] font-bold text-white tracking-wide uppercase font-mono">
              Geospatial Intelligence Map
            </h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[rgba(255,122,0,0.15)] text-[#FF9A3D] border border-[rgba(255,122,0,0.3)] font-mono font-bold tracking-wider">
              {MAP_TILE_CONFIGS[selectedLayer].label}
            </span>
          </div>
          <p className="text-xs text-[#9A9A9A] mt-1 font-mono">
            High-precision offset mapping for <strong className="text-white">{selectedWell}</strong> | Volve Field Sector
          </p>
        </div>

        {/* Right side controls: Layer Switcher & Search Radius */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Tile Layer Switcher (Dark / OSM / Ocean / Satellite) */}
          <div
            className="flex items-center gap-1 p-1 rounded-xl"
            style={{
              background: "rgba(22, 20, 18, 0.8)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
            }}
          >
            <Globe className="w-3.5 h-3.5 text-[#FF7A00] ml-1.5 mr-0.5" />
            {(["dark", "osm", "ocean", "satellite"] as MapLayerType[]).map((layerKey) => (
              <button
                key={layerKey}
                onClick={() => setSelectedLayer(layerKey)}
                title={MAP_TILE_CONFIGS[layerKey].description}
                className={`text-[11px] px-2.5 py-1 rounded-lg font-mono font-bold transition-all ${
                  selectedLayer === layerKey
                    ? "bg-[#FF7A00] text-black shadow-[0_0_12px_rgba(255,122,0,0.4)]"
                    : "text-[#A1A1AA] hover:text-white hover:bg-white/5"
                }`}
              >
                {layerKey === "dark"
                  ? "🌙 Dark (sih26)"
                  : layerKey === "osm"
                  ? "🗺️ OSM (v04)"
                  : layerKey === "ocean"
                  ? "🌊 Ocean"
                  : "🛰️ Satellite"}
              </button>
            ))}
          </div>

          {/* Search Radius Controls */}
          <div
            className="flex items-center gap-1.5 p-1 rounded-xl"
            style={{
              background: "rgba(22, 20, 18, 0.8)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
            }}
          >
            <Layers className="w-3.5 h-3.5 text-[#FF7A00] ml-1.5" />
            <span className="text-[11px] text-[#A1A1AA] font-mono mr-1">Radius:</span>
            {radiusOptions.map((r) => (
              <button
                key={r}
                onClick={() => setRadiusKm(r)}
                className={`text-[11px] px-2.5 py-1 rounded-lg font-mono font-bold transition-all ${
                  radiusKm === r
                    ? "bg-[#FF7A00] text-black shadow-[0_0_12px_rgba(255,122,0,0.4)]"
                    : "text-[#A1A1AA] hover:text-white hover:bg-white/5"
                }`}
              >
                {r < 1 ? `${r * 1000}m` : `${r}km`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Map (2/3) + Nearby Wells List (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Map Container with Dark Mode Invert Filter for OSM */}
        <div
          className={`lg:col-span-2 relative h-[480px] rounded-xl overflow-hidden shadow-inner transition-all duration-300 ${
            selectedLayer === "dark" ? "map-style-dark" : selectedLayer === "ocean" ? "map-style-ocean" : ""
          }`}
          style={{
            border: "1px solid rgba(255, 122, 0, 0.28)",
            background: "#08090C",
            boxShadow: "inset 0 0 25px rgba(0,0,0,0.8)",
          }}
        >
          {activeWellCoords ? (
            <Map
              key={selectedLayer}
              ref={mapRef}
              initialViewState={{
                longitude: 2.6,
                latitude: 58.7,
                zoom: 5.85,
              }}
              minZoom={4.0}
              maxZoom={selectedLayer === "satellite" ? 12.5 : 18.0}
              mapStyle={currentMapStyle}
              onMouseMove={onHover}
              onClick={onClick}
            >
              <NavigationControl position="bottom-right" />
              <FullscreenControl position="top-right" />

              {/* Radius Geofence Circle */}
              <Source id="search-radius" type="geojson" data={radiusGeoJson as any}>
                <Layer
                  id="search-radius-fill"
                  type="fill"
                  paint={{
                    "fill-color": "#FF7A00",
                    "fill-opacity": 0.06,
                  }}
                />
                <Layer
                  id="search-radius-line"
                  type="line"
                  paint={{
                    "line-color": "#FF7A00",
                    "line-width": 1.8,
                    "line-dasharray": [4, 6],
                  }}
                />
              </Source>

              {/* Nearby Wells DOM Markers (Interactive Offset Dots) */}
              {nearbyGeoJson.features.map((feature: any) => {
                const isHovered =
                  hoverInfo &&
                  !hoverInfo.isCluster &&
                  hoverInfo.feature?.properties?.id === feature.properties.id;

                const hasAlert = feature.properties.has_alert;
                const isSelected = feature.properties.is_selected;

                // Vibrant dot colors
                let dotBg = "#2DD4BF"; // Teal for standard offset
                let pulseRing = false;

                if (hasAlert) {
                  dotBg = "#F59E0B"; // Amber for incident offset
                  pulseRing = true;
                } else if (isSelected) {
                  dotBg = "#FF7A00"; // Orange for currently selected
                } else if (feature.properties.status === "Active") {
                  dotBg = "#10B981"; // Emerald for active
                } else if (feature.properties.status === "Suspended") {
                  dotBg = "#64748B"; // Slate for suspended
                }

                return (
                  <Marker
                    key={feature.properties.id}
                    longitude={feature.geometry.coordinates[0]}
                    latitude={feature.geometry.coordinates[1]}
                    anchor="center"
                    onClick={(e) => {
                      e.originalEvent.stopPropagation();
                      onClick({
                        features: [feature],
                        lngLat: {
                          lng: feature.geometry.coordinates[0],
                          lat: feature.geometry.coordinates[1],
                        },
                      } as any);
                    }}
                  >
                    <div className="relative flex items-center justify-center group">
                      {pulseRing && (
                        <div
                          className="absolute w-6 h-6 rounded-full animate-ping pointer-events-none"
                          style={{ background: "rgba(245, 158, 11, 0.45)" }}
                        ></div>
                      )}
                      <div
                        className="w-4 h-4 rounded-full border-2 border-[#0E0D0C] cursor-pointer transition-transform duration-200 group-hover:scale-150"
                        style={{
                          backgroundColor: dotBg,
                          boxShadow: hasAlert
                            ? "0 0 12px rgba(245, 158, 11, 0.9)"
                            : "0 0 8px rgba(0, 0, 0, 0.7)",
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigateToWell(feature.properties.id);
                        }}
                        onMouseEnter={() =>
                          setHoverInfo({
                            longitude: feature.geometry.coordinates[0],
                            latitude: feature.geometry.coordinates[1],
                            feature: feature,
                            isCluster: false,
                          })
                        }
                        onMouseLeave={() => setHoverInfo(null)}
                      />

                      {/* Pure DOM Hover Card / Matter showing */}
                      {isHovered && (
                        <div 
                          onClick={(e) => {
                            e.stopPropagation();
                            handleNavigateToWell(feature.properties.id);
                          }}
                          className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-[100] pointer-events-auto cursor-pointer drop-shadow-2xl transition-all duration-150 hover:scale-[1.02]"
                        >
                          <div
                            className="p-3.5 rounded-xl text-xs font-mono w-[220px]"
                            style={{
                              background: "rgba(18, 16, 14, 0.96)",
                              border: "1px solid rgba(255, 122, 0, 0.5)",
                              backdropFilter: "blur(14px)",
                              boxShadow: "0 8px 28px rgba(0,0,0,0.85), 0 0 15px rgba(255,122,0,0.15)",
                            }}
                          >
                            <div
                              className={`font-bold ${
                                hasAlert ? "text-amber-400" : "text-[#FF9A3D]"
                              } border-b border-white/10 pb-1.5 mb-1.5 flex items-center justify-between`}
                            >
                              <div className="flex items-center gap-1.5">
                                {hasAlert ? (
                                  <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                                ) : (
                                  <MapPin className="w-3.5 h-3.5 text-[#FF7A00]" />
                                )}
                                <span>{feature.properties.id}</span>
                              </div>
                              <span className="text-[9px] text-[#FF7A00] uppercase font-bold tracking-wider opacity-90 flex items-center gap-0.5">
                                INTEL <ArrowRight className="w-2.5 h-2.5" />
                              </span>
                            </div>
                            <div className="truncate text-white text-[11px] mb-1 font-semibold">
                              {feature.properties.name}
                            </div>
                            <div className="text-[#A1A1AA] flex justify-between text-[10px]">
                              <span>Distance:</span>
                              <span className="text-white font-bold">
                                {formatDistance(
                                  feature.properties.distance_km,
                                  feature.properties.distance_m
                                )}
                              </span>
                            </div>
                            <div className="text-[#A1A1AA] flex justify-between text-[10px] mt-0.5">
                              <span>Water Depth:</span>
                              <span className="text-white">
                                {feature.properties.water_depth_m
                                  ? `${feature.properties.water_depth_m}m`
                                  : "N/A"}
                              </span>
                            </div>
                            <div className="text-[#A1A1AA] flex justify-between text-[10px] mt-0.5">
                              <span>Status:</span>
                              <span className={hasAlert ? "text-amber-400 font-bold" : "text-emerald-400 font-bold"}>
                                {feature.properties.status || "Offset"}
                              </span>
                            </div>

                            {/* Interactive Click Action Button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleNavigateToWell(feature.properties.id);
                              }}
                              className="mt-2.5 w-full py-1.5 px-2 rounded-lg text-[10px] font-bold text-white uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-md group/btn"
                              style={{
                                background: "linear-gradient(145deg, #FF7A00, #FF5A00)",
                                boxShadow: "0 0 12px rgba(255,122,0,0.35)",
                                border: "none",
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.filter = "brightness(1.15)";
                                e.currentTarget.style.boxShadow = "0 0 16px rgba(255,122,0,0.6)";
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.filter = "none";
                                e.currentTarget.style.boxShadow = "0 0 12px rgba(255,122,0,0.35)";
                              }}
                            >
                              <span>VIEW WELL INTELLIGENCE</span>
                              <ArrowRight className="w-3 h-3 group-hover/btn:translate-x-0.5 transition-transform" />
                            </button>
                          </div>
                          <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-[rgba(255,122,0,0.5)] mx-auto"></div>
                        </div>
                      )}
                    </div>
                  </Marker>
                );
              })}

              {/* Active Drilling Well Marker with Cyan Star Beacon */}
              <Marker
                longitude={activeWellCoords[0]}
                latitude={activeWellCoords[1]}
                anchor="center"
                onClick={(e) => {
                  e.originalEvent.stopPropagation();
                  handleNavigateToWell(selectedWell);
                }}
              >
                <div 
                  onClick={() => handleNavigateToWell(selectedWell)}
                  className="relative flex items-center justify-center cursor-pointer group"
                  title="Click to view Active Well Intelligence"
                >
                  <div className="absolute w-12 h-12 rounded-full bg-[#00F0FF]/30 animate-ping"></div>
                  <div className="w-8 h-8 rounded-full bg-[#0E0D0C] border-2 border-[#00F0FF] flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.8)] z-10 relative group-hover:scale-125 transition-transform">
                    <span className="text-[#00F0FF] font-bold text-sm">★</span>
                  </div>
                  <div
                    className="absolute top-10 whitespace-nowrap text-[#00F0FF] font-mono text-[11px] px-2.5 py-1 rounded-lg shadow-xl z-20 flex flex-col items-center group-hover:scale-105 transition-transform"
                    style={{
                      background: "rgba(14, 13, 12, 0.95)",
                      border: "1px solid rgba(0, 240, 255, 0.5)",
                      boxShadow: "0 4px 15px rgba(0,0,0,0.7)",
                    }}
                  >
                    <span className="text-[9px] text-[#00F0FF]/80 font-bold uppercase tracking-wider">
                      ACTIVE DRILLING
                    </span>
                    <span className="font-bold text-white flex items-center gap-1">
                      {selectedWell} <ArrowRight className="w-3 h-3 text-[#00F0FF]" />
                    </span>
                  </div>
                </div>
              </Marker>
            </Map>
          ) : (
            <div className="h-full flex items-center justify-center text-[#A1A1AA] text-xs font-mono">
              Loading geospatial coordinates for {selectedWell}...
            </div>
          )}

          {/* Top-Left Active Well Badge Overlay */}
          <div
            className="absolute top-3 left-3 z-[10] px-3 py-1.5 rounded-xl text-[11px] font-mono text-white shadow-lg flex items-center gap-2 pointer-events-none"
            style={{
              background: "rgba(14, 13, 12, 0.85)",
              border: "1px solid rgba(255, 122, 0, 0.3)",
              backdropFilter: "blur(12px)",
            }}
          >
            <span className="w-2.5 h-2.5 rounded-full border border-[#00F0FF] flex items-center justify-center text-[7px] text-[#00F0FF]">
              ★
            </span>
            <span>
              Active: <strong className="text-[#00F0FF]">{selectedWell}</strong>
            </span>
            <span className="text-white/20 mx-1">|</span>
            <span className="w-2 h-2 rounded-full bg-[#FF7A00]"></span>
            <span>
              Radius: <strong className="text-[#FF9A3D]">{radiusKm} km</strong>
            </span>
          </div>


          {/* Bottom-Right Legend */}
          <div
            className="absolute bottom-3 right-12 z-[10] p-2.5 rounded-xl text-[10px] font-mono text-[#D4D4D8] shadow-lg pointer-events-none flex flex-col gap-1.5"
            style={{
              background: "rgba(14, 13, 12, 0.85)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              backdropFilter: "blur(12px)",
            }}
          >
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full border border-[#00F0FF] bg-[#00F0FF]/20 flex items-center justify-center text-[7px] text-[#00F0FF]">
                ★
              </span>
              <span>Active Well</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 border border-black"></span>
              <span>Active Offset</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-black shadow-[0_0_6px_rgba(245,158,11,0.6)]"></span>
              <span>Alert / Offset Incident</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400 border border-black"></span>
              <span>Suspended / Offline</span>
            </div>
          </div>

          {/* Live Coordinates Display */}
          {cursorCoords && (
            <div
              className="absolute bottom-3 left-1/2 -translate-x-1/2 z-[10] px-3 py-1 rounded-xl text-[10px] font-mono text-[#A1A1AA] shadow-lg pointer-events-none"
              style={{
                background: "rgba(14, 13, 12, 0.85)",
                border: "1px solid rgba(255, 122, 0, 0.25)",
                backdropFilter: "blur(12px)",
              }}
            >
              LAT {cursorCoords[1].toFixed(4)}° N | LON {cursorCoords[0].toFixed(4)}° E
            </div>
          )}

          {/* Bottom-Left Controls: Overview & Focus Active */}
          <div className="absolute bottom-3 left-3 z-[10] flex gap-2">
            <button
              onClick={() => {
                if (mapRef.current) {
                  mapRef.current.flyTo({ center: [2.6, 58.7], zoom: 5.85, duration: 1000 });
                }
              }}
              title="Wide regional view spanning Scotland to Norway"
              className="px-3 py-1.5 rounded-xl text-[11px] font-mono text-white flex items-center gap-1.5 cursor-pointer transition-all duration-200 hover:scale-105"
              style={{
                background: "rgba(14, 13, 12, 0.85)",
                border: "1px solid rgba(255, 122, 0, 0.35)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 4px 15px rgba(0,0,0,0.4)",
              }}
            >
              <Globe className="w-3.5 h-3.5 text-[#FF7A00]" /> Overview
            </button>
            <button
              onClick={() => {
                if (mapRef.current && activeWellCoords) {
                  mapRef.current.flyTo({ center: activeWellCoords, zoom: 12, duration: 1000 });
                }
              }}
              title="Zoom in to active drilling platform"
              className="px-3 py-1.5 rounded-xl text-[11px] font-mono text-white flex items-center gap-1.5 cursor-pointer transition-all duration-200 hover:scale-105"
              style={{
                background: "rgba(14, 13, 12, 0.85)",
                border: "1px solid rgba(0, 240, 255, 0.35)",
                backdropFilter: "blur(12px)",
                boxShadow: "0 4px 15px rgba(0,0,0,0.4)",
              }}
            >
              <Crosshair className="w-3.5 h-3.5 text-[#00F0FF]" /> Focus Well
            </button>
          </div>
        </div>

        {/* Nearby Wells Sorted List Panel */}
        <div
          className="rounded-xl p-4 flex flex-col justify-between h-[480px]"
          style={{
            background: "rgba(18, 16, 14, 0.85)",
            border: "1px solid rgba(255, 122, 0, 0.2)",
            boxShadow: "inset 0 0 20px rgba(0,0,0,0.5)",
          }}
        >
          <div>
            <div className="flex items-center justify-between border-b border-white/10 pb-3 mb-3">
              <div className="flex items-center gap-2 text-xs font-bold text-white uppercase font-mono tracking-wider">
                <Navigation className="w-4 h-4 text-[#FF7A00]" />
                Nearby Wells ({nearbyData?.count || 0})
              </div>
              <span className="text-[10px] text-[#A1A1AA] font-mono">Sorted by Distance</span>
            </div>

            {/* List Container */}
            {isLoading ? (
              <div className="py-16 text-center text-xs font-mono text-[#A1A1AA] animate-pulse">
                Calculating offset distances...
              </div>
            ) : nearbyData && nearbyData.nearby_wells.length > 0 ? (
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                {nearbyData.nearby_wells.map((nw: NearbyWellItem) => {
                  const isSelected = selectedNearbyWellId === nw.well_id;
                  const matchForWell = proximityMatches.find(
                    (pm: any) =>
                      pm.offset_well_id.replace("NO ", "") === nw.well_id.replace("NO ", "")
                  );
                  const hasAlert = Boolean(matchForWell);
                  return (
                    <div
                      key={nw.well_id}
                      onClick={() => {
                        setSelectedNearbyWellId(nw.well_id);
                        if (mapRef.current) {
                          mapRef.current.flyTo({ center: [nw.longitude, nw.latitude], zoom: 11.5, duration: 1000 });
                        }
                      }}
                      className={`p-3 rounded-xl border transition-all duration-200 cursor-pointer ${
                        isSelected
                          ? "bg-[rgba(255,122,0,0.15)] border-[#FF7A00] shadow-[0_0_15px_rgba(255,122,0,0.3)] transform scale-[1.01]"
                          : hasAlert
                          ? "bg-[rgba(245,158,11,0.1)] border-amber-500/50 hover:border-amber-400 hover:shadow-[0_0_12px_rgba(245,158,11,0.25)]"
                          : "bg-white/[0.03] border-white/10 hover:border-[rgba(255,122,0,0.4)] hover:bg-white/[0.06]"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono">
                        <span
                          className={`font-bold text-xs flex items-center gap-1.5 ${
                            hasAlert ? "text-amber-400" : "text-white"
                          }`}
                        >
                          <MapPin
                            className={`w-3.5 h-3.5 ${
                              hasAlert ? "text-amber-400" : "text-[#FF7A00]"
                            }`}
                          />
                          {nw.well_id}
                        </span>
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full font-bold font-mono"
                          style={{
                            background: "rgba(255, 122, 0, 0.15)",
                            color: "#FF9A3D",
                            border: "1px solid rgba(255, 122, 0, 0.3)",
                          }}
                        >
                          {formatDistance(nw.distance_km, nw.distance_m)}
                        </span>
                      </div>

                      {matchForWell && (
                        <div className="mt-2 mb-1 bg-amber-950/70 text-amber-300 font-mono text-[10px] p-2 rounded-lg border border-amber-500/30 space-y-0.5">
                          <div className="font-bold flex items-center gap-1 uppercase text-[9px]">
                            <span>⚠ {matchForWell.proximity_classification}</span>
                          </div>
                          <div>
                            {matchForWell.event_type} @ {matchForWell.event_md}m
                          </div>
                        </div>
                      )}

                      <div className="text-[11px] text-[#A1A1AA] mt-1.5 flex items-center justify-between">
                        <span className="truncate pr-2">{nw.name}</span>
                        <span className="font-mono text-[10px] text-[#71717A] whitespace-nowrap">
                          Slot: {nw.slot_name || "N/A"}
                        </span>
                      </div>

                      <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center justify-between text-[10px] font-mono">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectWell(nw.well_id);
                          }}
                          className="text-[#A1A1AA] hover:text-[#FF7A00] transition-colors flex items-center gap-1"
                        >
                          Set Active ➔
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onOpenIntelligence) {
                              onOpenIntelligence(nw.well_id);
                            } else {
                              onSelectWell(nw.well_id);
                            }
                          }}
                          className="font-bold px-2.5 py-0.5 rounded-lg border transition-all text-[#FF9A3D] bg-[rgba(255,122,0,0.12)] border-[rgba(255,122,0,0.3)] hover:bg-[#FF7A00] hover:text-black"
                        >
                          Intelligence ➔
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-16 text-center border border-dashed border-white/10 rounded-xl text-[#A1A1AA] text-xs font-mono space-y-2">
                <div>No offset wells found within {radiusKm} km.</div>
                <div className="text-[11px] text-[#71717A]">
                  Expand the search radius using the controls above.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Global styling overrides for custom map controls, dark filter, and scrollbars */}
      <style>{`
        /* Dark night-mode filter for OpenStreetMap (v04) to match sih2k26 background */
        .map-style-dark canvas.maplibregl-canvas {
          filter: invert(100%) hue-rotate(180deg) brightness(76%) contrast(120%) saturate(65%) !important;
        }

        /* Ocean bathymetry subtle contrast boost */
        .map-style-ocean canvas.maplibregl-canvas {
          filter: brightness(85%) contrast(115%) !important;
        }

        .maplibregl-ctrl-group {
          background: rgba(14, 13, 12, 0.9) !important;
          border: 1px solid rgba(255, 122, 0, 0.3) !important;
          border-radius: 12px !important;
          overflow: hidden !important;
        }
        .maplibregl-ctrl-group button {
          border-bottom: 1px solid rgba(255, 122, 0, 0.15) !important;
        }
        .maplibregl-ctrl-group button:hover {
          background: rgba(255, 122, 0, 0.15) !important;
        }
        .maplibregl-ctrl-icon {
          filter: invert(1) brightness(1.5) !important;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(14, 13, 12, 0.5);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 122, 0, 0.25);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 122, 0, 0.5);
        }
      `}</style>
    </div>
  );
};
