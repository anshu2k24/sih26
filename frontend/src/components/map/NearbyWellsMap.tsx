import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Map, { Source, Layer, NavigationControl, FullscreenControl, Marker, Popup } from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import circle from "@turf/circle";
import { point } from "@turf/helpers";

import type { WellItem, NearbyWellItem, NearbyWellsResponse } from "../../types/api";
import { fetchNearbyWells } from "../../services/api";
import { MapPin, Navigation, Compass, Shield, Layers, Crosshair } from "lucide-react";

// Professional dark vector style (Carto Dark Matter fallback, customizable via env)
const MAP_STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL;

// If no vector style is provided or if carto fails, use the original Esri dark raster tiles inside MapLibre
const FALLBACK_STYLE = {
  version: 8,
  sources: {
    'esri-dark': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'
      ],
      tileSize: 256,
      attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
    }
  },
  layers: [
    {
      id: 'esri-dark-layer',
      type: 'raster',
      source: 'esri-dark',
      minzoom: 0,
      maxzoom: 22
    }
  ]
};

const MAP_STYLE = MAP_STYLE_URL || FALLBACK_STYLE;

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

  // Fit bounds when active well changes
  useEffect(() => {
    if (activeWellCoords && mapRef.current && lastFitWellId.current !== selectedWell && nearbyData) {
      let minLng = activeWellCoords[0];
      let minLat = activeWellCoords[1];
      let maxLng = activeWellCoords[0];
      let maxLat = activeWellCoords[1];

      nearbyData.nearby_wells.forEach(nw => {
        minLng = Math.min(minLng, nw.longitude);
        minLat = Math.min(minLat, nw.latitude);
        maxLng = Math.max(maxLng, nw.longitude);
        maxLat = Math.max(maxLat, nw.latitude);
      });

      if (radiusKm > 0) {
        const latDiff = radiusKm / 111;
        const lngDiff = radiusKm / (111 * Math.cos((activeWellCoords[1] * Math.PI) / 180));
        minLng = Math.min(minLng, activeWellCoords[0] - lngDiff);
        minLat = Math.min(minLat, activeWellCoords[1] - latDiff);
        maxLng = Math.max(maxLng, activeWellCoords[0] + lngDiff);
        maxLat = Math.max(maxLat, activeWellCoords[1] + latDiff);
      }

      mapRef.current.fitBounds(
        [[minLng, minLat], [maxLng, maxLat]],
        { padding: 50, maxZoom: 16, duration: 1200 }
      );
      
      lastFitWellId.current = selectedWell;
    }
  }, [activeWellCoords, nearbyData, selectedWell, radiusKm]);

  const radiusOptions = [0.5, 1.0, 5.0, 10.0, 25.0];

  const formatDistance = (distKm: number, distM: number) => {
    if (distKm < 1.0) {
      return `${distM.toFixed(0)} m`;
    }
    return `${distKm.toFixed(2)} km`;
  };

  // Generate GeoJSON for Nearby Wells
  const nearbyGeoJson = useMemo(() => {
    if (!nearbyData?.nearby_wells) return { type: "FeatureCollection", features: [] };

    const features = nearbyData.nearby_wells.map((nw, index) => {
      let lng = Number(nw.longitude);
      let lat = Number(nw.latitude);
      
      // If distance is very small (e.g. same platform), spread them in a spider spiral
      if (nw.distance_km < 0.1) {
        // Spiral spidering layout
        const ringSpacing = 0.03; // ~3km spacing between rings (push outside marker)
        const pointsPerRing = 10;
        const ring = Math.floor(index / pointsPerRing) + 1;
        const currentRingPoints = ring * pointsPerRing;
        
        const angle = index * (Math.PI * 2 / currentRingPoints);
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
        }
      };
    });

    return { type: "FeatureCollection", features };
  }, [nearbyData, proximityMatches, selectedNearbyWellId]);

  // Generate GeoJSON for the Radius Circle
  const radiusGeoJson = useMemo(() => {
    if (!activeWellCoords) return { type: "FeatureCollection", features: [] };
    const center = point(activeWellCoords);
    const options = { steps: 64, units: 'kilometers' as const };
    const circleFeature = circle(center, radiusKm, options);
    return { type: "FeatureCollection", features: [circleFeature] };
  }, [activeWellCoords, radiusKm]);

  const onHover = useCallback((event: any) => {
    // Only track cursor coordinates, do not mess with hoverInfo for DOM markers
    if (event.lngLat) {
      setCursorCoords([event.lngLat.lng, event.lngLat.lat]);
    }
  }, []);

  const onClick = useCallback((event: any) => {
    const feature = event.features && event.features[0];
    if (feature) {
      if (feature.layer.id === 'unclustered-point') {
        setSelectedNearbyWellId(feature.properties.id);
      } else if (feature.layer.id === 'clusters') {
        const clusterId = feature.properties.cluster_id;
        const mapboxSource = mapRef.current?.getSource('nearby-wells') as any;
        if (mapboxSource && mapboxSource.getClusterExpansionZoom) {
          mapboxSource.getClusterExpansionZoom(clusterId, (err: any, zoom: number) => {
            if (err) return;
            mapRef.current?.easeTo({
              center: [event.lngLat.lng, event.lngLat.lat],
              zoom: zoom + 1,
              duration: 500
            });
          });
        }
      }
    } else {
      setSelectedNearbyWellId(null);
    }
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header Controls Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-emerald-400 animate-spin-slow" />
            <h2 className="text-base font-bold text-white font-mono tracking-tight">
              Geospatial Intelligence Map
            </h2>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-mono">
              MAPLIBRE VECTOR
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            High-performance vector mapping for <strong>{selectedWell}</strong> offset intelligence.
          </p>
        </div>

        {/* Search Radius Controls */}
        <div className="flex items-center gap-2 bg-slate-850 p-1.5 rounded-lg border border-slate-800">
          <Layers className="w-4 h-4 text-slate-400 ml-1" />
          <span className="text-xs text-slate-400 font-mono font-medium">Search Radius:</span>
          <div className="flex items-center gap-1">
            {radiusOptions.map((r) => (
              <button
                key={r}
                onClick={() => setRadiusKm(r)}
                className={`text-xs px-2.5 py-1 rounded font-mono font-semibold transition-all ${
                  radiusKm === r
                    ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
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
        {/* Map Container */}
        <div className="lg:col-span-2 relative h-[450px] rounded-lg overflow-hidden border border-slate-800 shadow-inner bg-slate-950">
          {activeWellCoords ? (
            <Map
              ref={mapRef}
              initialViewState={{
                longitude: activeWellCoords[0],
                latitude: activeWellCoords[1],
                zoom: 12
              }}
              mapStyle={MAP_STYLE}
              onMouseMove={onHover}
              onClick={onClick}
            >
              <NavigationControl position="bottom-right" />
              <FullscreenControl position="top-right" />

              {/* Radius Circle */}
              <Source id="search-radius" type="geojson" data={radiusGeoJson as any}>
                <Layer
                  id="search-radius-fill"
                  type="fill"
                  paint={{
                    'fill-color': '#10b981',
                    'fill-opacity': 0.05
                  }}
                />
                <Layer
                  id="search-radius-line"
                  type="line"
                  paint={{
                    'line-color': '#10b981',
                    'line-width': 1.5,
                    'line-dasharray': [4, 6]
                  }}
                />
              </Source>

              {/* Nearby Wells DOM Markers (Guaranteed Visibility) */}
              {nearbyGeoJson.features.map((feature: any) => {
                const isHovered = hoverInfo && !hoverInfo.isCluster && hoverInfo.feature.properties.id === feature.properties.id;
                
                return (
                <Marker
                  key={feature.properties.id}
                  longitude={feature.geometry.coordinates[0]}
                  latitude={feature.geometry.coordinates[1]}
                  anchor="center"
                  onClick={(e) => {
                    e.originalEvent.stopPropagation();
                    onClick({ features: [feature], lngLat: { lng: feature.geometry.coordinates[0], lat: feature.geometry.coordinates[1] } } as any);
                  }}
                >
                  <div className="relative flex items-center justify-center">
                    <div 
                      className={`w-3 h-3 rounded-full border border-slate-900 cursor-pointer shadow-md transition-transform hover:scale-125
                        ${feature.properties.has_alert ? 'bg-amber-500' : 
                          feature.properties.is_selected ? 'bg-emerald-400' : 
                          feature.properties.status === 'Active' ? 'bg-emerald-500' : 
                          feature.properties.status === 'Suspended' ? 'bg-slate-500' : 
                          feature.properties.status === 'P&A' ? 'bg-slate-600' : 'bg-teal-500'}`}
                      onMouseEnter={() => setHoverInfo({
                        longitude: feature.geometry.coordinates[0],
                        latitude: feature.geometry.coordinates[1],
                        feature: feature,
                        isCluster: false
                      })}
                      onMouseLeave={() => setHoverInfo(null)}
                    />
                    
                    {/* Pure DOM Popup bypassing MapLibre WebGL bugs */}
                    {isHovered && (
                      <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-[100] pointer-events-none drop-shadow-2xl">
                        <div className="bg-slate-900 border border-slate-700 text-slate-200 p-2.5 rounded-lg text-xs font-mono w-[180px]">
                          <div className={`font-bold ${feature.properties.has_alert ? 'text-amber-400' : 'text-emerald-400'} border-b border-slate-700 pb-1.5 mb-1.5 flex items-center gap-1.5`}>
                            {feature.properties.has_alert ? '⚠' : '●'} {feature.properties.id}
                          </div>
                          <div className="truncate mb-1">{feature.properties.name}</div>
                          <div className="text-slate-400 flex justify-between">
                            <span>Dist:</span>
                            <span className="text-emerald-300">{formatDistance(feature.properties.distance_km, feature.properties.distance_m)}</span>
                          </div>
                          <div className="text-slate-400 flex justify-between mt-0.5">
                            <span>Status:</span>
                            <span>{feature.properties.status}</span>
                          </div>
                        </div>
                        {/* Little triangle pointer for the popup */}
                        <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-slate-700 mx-auto"></div>
                      </div>
                    )}
                  </div>
                </Marker>
              )})}
              {hoverInfo && hoverInfo.isCluster && (
                <Popup
                  longitude={hoverInfo.longitude}
                  latitude={hoverInfo.latitude}
                  closeButton={false}
                  closeOnClick={false}
                  anchor="bottom"
                  offset={10}
                  className="custom-maplibre-popup z-50"
                >
                  <div className="bg-slate-900 border border-slate-700 text-slate-200 p-2 rounded shadow-xl text-xs font-mono">
                    <div className="font-bold text-emerald-400">Cluster</div>
                    <div className="text-slate-400">Click to expand {hoverInfo.feature.properties.point_count} wells</div>
                  </div>
                </Popup>
              )}

              {/* Active Well Marker */}
              <Marker
                longitude={activeWellCoords[0]}
                latitude={activeWellCoords[1]}
                anchor="center"
              >
                <div className="relative flex items-center justify-center cursor-pointer">
                  <div className="absolute w-12 h-12 rounded-full bg-cyan-500/20 animate-ping"></div>
                  <div className="w-8 h-8 rounded-full bg-slate-900 border-2 border-cyan-400 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.5)] z-10 relative">
                    <span className="text-cyan-400 font-bold text-sm">★</span>
                  </div>
                  <div className="absolute top-10 whitespace-nowrap bg-slate-900/95 text-cyan-300 font-mono text-[11px] px-2.5 py-1 rounded border border-cyan-500/40 shadow-xl z-20 flex flex-col items-center">
                    <span className="text-[9px] text-cyan-400/80 font-bold uppercase">Active Well</span>
                    <span className="font-bold">{selectedWell}</span>
                  </div>
                </div>
              </Marker>
            </Map>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
              Location data unavailable for this well.
            </div>
          )}

          {/* Map Overlay Badge */}
          <div className="absolute top-3 left-3 z-[10] bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-md border border-slate-800 text-[11px] font-mono text-slate-300 shadow-md flex items-center gap-2 pointer-events-none">
             <span className="w-2.5 h-2.5 rounded-full border border-cyan-400 flex items-center justify-center text-[7px] text-cyan-400">★</span>
             <span>Active: <strong className="text-cyan-300">{selectedWell}</strong></span>
             <span className="text-slate-500 mx-1">|</span>
             <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
             <span>● Radius: <strong className="text-white">{radiusKm} km</strong></span>
          </div>

          {/* Map Legend */}
          <div className="absolute bottom-3 right-12 z-[10] bg-slate-900/90 backdrop-blur p-2.5 rounded-md border border-slate-800 text-[10px] font-mono text-slate-300 shadow-md pointer-events-none flex flex-col gap-1.5">
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full border border-cyan-400 bg-cyan-500/20 flex items-center justify-center text-[7px] text-cyan-400">★</span> Active Well</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-slate-900"></span> Active Offset</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-slate-900"></span> Alert / Warning</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-slate-500 border border-slate-900"></span> Suspended / Offline</div>
            <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-teal-500 border border-slate-900"></span> Unknown Status</div>
          </div>

          {/* Live Coordinate Display */}
          {cursorCoords && (
             <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-[10] bg-slate-900/90 backdrop-blur px-2.5 py-1 rounded-md border border-slate-800 text-[10px] font-mono text-slate-400 shadow-md pointer-events-none">
               LAT {(cursorCoords[1]).toFixed(4)}° N | LON {(cursorCoords[0]).toFixed(4)}° E
             </div>
          )}
          
          <div className="absolute bottom-3 left-3 z-[10] flex gap-2">
            <button 
              onClick={() => {
                if (mapRef.current && activeWellCoords) {
                  mapRef.current.flyTo({ center: activeWellCoords, zoom: 14 });
                }
              }}
              className="bg-slate-900/90 hover:bg-slate-800 backdrop-blur px-2.5 py-1.5 rounded-md border border-slate-700 text-[11px] font-mono text-slate-300 shadow-md flex items-center gap-1 cursor-pointer transition-colors"
            >
              <Crosshair className="w-3 h-3 text-emerald-400" /> Focus Active
            </button>
          </div>

        </div>

        {/* Nearby Wells Sorted List Panel */}
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 flex flex-col justify-between h-[450px]">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">
                <Navigation className="w-4 h-4 text-emerald-400" />
                Nearby Wells ({nearbyData?.count || 0})
              </div>
              <span className="text-[11px] text-slate-400 font-mono">
                Sorted by Distance
              </span>
            </div>

            {/* List Container */}
            {isLoading ? (
              <div className="py-12 text-center text-xs font-mono text-slate-400 animate-pulse">
                Calculating Haversine offset distances...
              </div>
            ) : nearbyData && nearbyData.nearby_wells.length > 0 ? (
              <div className="space-y-2.5 max-h-[350px] overflow-y-auto pr-1 custom-scrollbar">
                {nearbyData.nearby_wells.map((nw: NearbyWellItem) => {
                  const isSelected = selectedNearbyWellId === nw.well_id;
                  const matchForWell = proximityMatches.find(
                    (pm: any) => pm.offset_well_id.replace("NO ", "") === nw.well_id.replace("NO ", "")
                  );
                  const hasAlert = Boolean(matchForWell);
                  return (
                    <div
                      key={nw.well_id}
                      onClick={() => {
                        setSelectedNearbyWellId(nw.well_id);
                        if (mapRef.current) {
                           mapRef.current.flyTo({ center: [nw.longitude, nw.latitude], zoom: 15 });
                        }
                      }}
                      className={`p-3 rounded-lg border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-emerald-950/40 border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.1)]"
                          : hasAlert
                            ? "bg-slate-900 border-amber-500/40 hover:border-amber-500/80"
                            : "bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono">
                        <span className={`font-bold text-xs flex items-center gap-1.5 ${hasAlert ? 'text-amber-400' : 'text-emerald-400'}`}>
                          <MapPin className={`w-3.5 h-3.5 ${hasAlert ? 'text-amber-400' : 'text-emerald-400'}`} />
                          {nw.well_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-emerald-300 font-bold border border-slate-700">
                          {formatDistance(nw.distance_km, nw.distance_m)}
                        </span>
                      </div>

                      {matchForWell && (
                        <div className="mt-2 mb-1 bg-amber-950/80 text-amber-300 font-mono text-[10px] p-2 rounded border border-amber-500/40 space-y-0.5">
                          <div className="font-bold flex items-center gap-1 uppercase text-[9px]">
                            <span>⚠ {matchForWell.proximity_classification}</span>
                          </div>
                          <div>{matchForWell.event_type} @ {matchForWell.event_md}m</div>
                        </div>
                      )}

                      <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between font-sans">
                        <span className="truncate pr-2">{nw.name}</span>
                        <span className="font-mono text-[10px] text-slate-400 whitespace-nowrap">
                          Slot: {nw.slot_name}
                        </span>
                      </div>

                      <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectWell(nw.well_id);
                          }}
                          className="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1"
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
                          className={`hover:underline flex items-center gap-1 font-bold px-2 py-0.5 rounded border transition-colors ${
                            hasAlert 
                              ? "text-amber-400 bg-amber-950/60 border-amber-500/30 hover:bg-amber-900/60"
                              : "text-emerald-400 bg-emerald-950/60 border-emerald-500/30 hover:bg-emerald-900/60"
                          }`}
                        >
                          View Intelligence ➔
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-16 text-center border border-dashed border-slate-850 rounded-lg text-slate-400 text-xs font-mono space-y-2">
                <div>No nearby offset wells found within {radiusKm} km.</div>
                <div className="text-[11px] text-slate-400">
                  Try expanding the search radius using the controls above.
                </div>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-850 text-[10px] text-slate-400 font-mono flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Shield className="w-3 h-3 text-emerald-400" />
              Haversine Proximity Engine
            </span>
            <span>NPD Verified Coordinates</span>
          </div>
        </div>
      </div>
      
      {/* Global override for maplibre popups to fit the dark theme */}
      <style>{`
        .maplibregl-popup-content {
          background: #0f172a !important;
          border: 1px solid #334155 !important;
          padding: 0 !important;
          border-radius: 0.5rem !important;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
        }
        .maplibregl-popup-tip {
          border-top-color: #334155 !important;
          border-bottom-color: #334155 !important;
        }
        .custom-maplibre-popup .maplibregl-popup-content {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #0f172a;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #334155;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #475569;
        }
      `}</style>
    </div>
  );
};
