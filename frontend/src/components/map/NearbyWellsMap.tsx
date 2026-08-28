import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { WellItem, NearbyWellItem, NearbyWellsResponse } from "../../types/api";
import { fetchNearbyWells } from "../../services/api";
import { MapPin, Navigation, Compass, Shield, ExternalLink, Layers } from "lucide-react";

// Fix Leaflet default icon issues in React/Vite builds
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom Icon Creators using DivIcon for custom styling & animations
const createActiveMarkerIcon = (wellId: string) =>
  L.divIcon({
    className: "custom-active-marker",
    html: `
      <div class="relative flex items-center justify-center">
        <div class="absolute w-8 h-8 rounded-full bg-amber-500/40 animate-ping"></div>
        <div class="w-7 h-7 rounded-full bg-slate-950 border-2 border-amber-400 flex items-center justify-center shadow-lg shadow-amber-500/50">
          <span class="text-amber-400 font-bold text-xs">★</span>
        </div>
        <div class="absolute top-8 whitespace-nowrap bg-slate-900/95 text-amber-300 font-mono text-[10px] px-2 py-0.5 rounded border border-amber-500/40 shadow">
          ★ ${wellId} (ACTIVE)
        </div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

const createNearbyMarkerIcon = (wellId: string, isSelected: boolean, hasAlert: boolean = false) => {
  const color = hasAlert ? "#f59e0b" : isSelected ? "#34d399" : "#10b981";
  const label = hasAlert ? `⚠ ${wellId}` : `● ${wellId}`;
  return L.divIcon({
    className: "custom-nearby-marker",
    html: `
      <div style="
        background: rgba(15, 23, 42, 0.95);
        border: 1.5px solid ${color};
        color: ${color};
        padding: 2px 7px;
        border-radius: 9999px;
        font-family: monospace;
        font-size: 10px;
        font-weight: bold;
        white-space: nowrap;
        box-shadow: 0 0 ${hasAlert ? "14px rgba(245, 158, 11, 0.7)" : "8px rgba(16, 185, 129, 0.4)"};
        display: flex;
        align-items: center;
        gap: 3px;
      ">
        ${label}
      </div>
    `,
    iconSize: [84, 24],
    iconAnchor: [42, 12],
  });
};

interface MapControllerProps {
  center: [number, number];
  nearbyWells?: NearbyWellItem[];
}

const MapController: React.FC<MapControllerProps> = ({ center, nearbyWells = [] }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      const points: [number, number][] = [center];
      nearbyWells.forEach((w) => {
        if (w.latitude && w.longitude) {
          points.push([w.latitude, w.longitude]);
        }
      });

      if (points.length > 1) {
        const bounds = L.latLngBounds(points);
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16, animate: true, duration: 1.2 });
      } else {
        map.setView(center, 15, { animate: true });
      }
    }
  }, [center, nearbyWells, map]);
  return null;
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
  const [radiusKm, setRadiusKm] = useState<number>(5.0);
  const [nearbyData, setNearbyData] = useState<NearbyWellsResponse | null>(null);
  const [activeWellCoords, setActiveWellCoords] = useState<[number, number] | null>(null);
  const [selectedNearbyWellId, setSelectedNearbyWellId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Load active well metadata from wells list
  const activeWellItem = wells.find((w) => w.well_id === selectedWell);

  // Fetch nearby wells whenever active well or search radius changes
  useEffect(() => {
    setIsLoading(true);
    fetchNearbyWells(selectedWell, radiusKm).then((res) => {
      setNearbyData(res);
      setIsLoading(false);

      if (res && res.active_well_metadata?.latitude && res.active_well_metadata?.longitude) {
        setActiveWellCoords([
          res.active_well_metadata.latitude,
          res.active_well_metadata.longitude,
        ]);
      } else if (activeWellItem?.latitude && activeWellItem?.longitude) {
        setActiveWellCoords([activeWellItem.latitude, activeWellItem.longitude]);
      } else {
        // Default Volve field center coordinates if specific well missing
        setActiveWellCoords([58.44168, 1.88778]);
      }
    });
  }, [selectedWell, radiusKm, activeWellItem]);

  const radiusOptions = [0.5, 1.0, 5.0, 10.0, 25.0];

  // Helper to format distance cleanly
  const formatDistance = (distKm: number, distM: number) => {
    if (distKm < 1.0) {
      return `${distM.toFixed(0)} m`;
    }
    return `${distKm.toFixed(2)} km`;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
      {/* Header Controls Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-emerald-400 animate-spin-slow" />
            <h2 className="text-base font-bold text-white font-mono tracking-tight">
              Nearby Wells Intelligence Map
            </h2>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 font-mono">
              NWIS GEOSPATIAL
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Interactive map-based offset intelligence for <strong>{selectedWell}</strong> in Equinor Volve Field (Block 15/9, North Sea).
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
            <MapContainer
              center={activeWellCoords}
              zoom={radiusKm <= 0.5 ? 17 : radiusKm <= 1.0 ? 16 : radiusKm <= 5.0 ? 15 : radiusKm <= 10.0 ? 14 : 13}
              scrollWheelZoom={true}
              style={{ height: "100%", width: "100%" }}
              className="z-10"
            >
              <MapController
                center={activeWellCoords}
                nearbyWells={nearbyData?.nearby_wells || []}
              />
              <TileLayer
                attribution='&copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
              />

              {/* Active Well Search Radius Overlay Circle */}
              <Circle
                center={activeWellCoords}
                radius={radiusKm * 1000}
                pathOptions={{
                  color: "#10b981",
                  fillColor: "#10b981",
                  fillOpacity: 0.08,
                  weight: 1.5,
                  dashArray: "4, 6",
                }}
              />

              {/* Active Well Marker (Glowing Star) */}
              <Marker
                position={activeWellCoords}
                icon={createActiveMarkerIcon(selectedWell)}
              >
                <Popup className="custom-leaflet-popup">
                  <div className="p-2 space-y-1 font-sans text-xs">
                    <div className="font-bold text-amber-400 font-mono text-sm border-b border-slate-700 pb-1">
                      ★ {selectedWell} (ACTIVE WELL)
                    </div>
                    <div className="text-slate-300">
                      <strong>Status:</strong> {activeWellItem?.status || "Active Drilling"}
                    </div>
                    <div className="text-slate-300">
                      <strong>Field:</strong> {activeWellItem?.field || "Volve (Block 15/9)"}
                    </div>
                    <div className="text-slate-300">
                      <strong>Slot:</strong> {activeWellItem?.slot_name || "Slot 3"}
                    </div>
                    <div className="text-slate-300">
                      <strong>Coordinates:</strong> {activeWellCoords[0].toFixed(5)}°N, {activeWellCoords[1].toFixed(5)}°E
                    </div>
                  </div>
                </Popup>
              </Marker>

              {/* Nearby Offset Well Markers */}
              {nearbyData?.nearby_wells.map((nw: NearbyWellItem) => {
                const matchForWell = proximityMatches.find(
                  (pm: any) => pm.offset_well_id.replace("NO ", "") === nw.well_id.replace("NO ", "")
                );
                const hasAlert = Boolean(matchForWell);

                return (
                  <Marker
                    key={nw.well_id}
                    position={[nw.latitude, nw.longitude]}
                    icon={createNearbyMarkerIcon(nw.well_id, selectedNearbyWellId === nw.well_id, hasAlert)}
                    eventHandlers={{
                      click: () => setSelectedNearbyWellId(nw.well_id),
                    }}
                  >
                    <Popup>
                      <div className="p-2 space-y-1.5 font-sans text-xs">
                        <div className="font-bold text-emerald-400 font-mono text-sm border-b border-slate-700 pb-1 flex items-center justify-between gap-2">
                          <span>{hasAlert ? `⚠ ${nw.well_id}` : `● ${nw.well_id}`}</span>
                          <span className="text-slate-300 font-mono text-[11px] bg-slate-800 px-1.5 py-0.5 rounded">
                            {formatDistance(nw.distance_km, nw.distance_m)}
                          </span>
                        </div>

                        {matchForWell && (
                          <div className="bg-amber-950/90 text-amber-300 font-mono text-[11px] p-2 rounded border border-amber-500/40 space-y-0.5">
                            <div className="font-bold text-amber-400 flex items-center gap-1 uppercase">
                              <span>⚠ {matchForWell.proximity_classification}</span>
                            </div>
                            <div>Event: <strong>{matchForWell.event_type}</strong> @ {matchForWell.event_md}m</div>
                            <div>Depth Delta: <strong>Δ {matchForWell.delta_md}m</strong></div>
                            <div className="text-[9px] text-amber-400/80 mt-1 uppercase font-bold">
                              HISTORICAL EVENT — NOT A PREDICTION
                            </div>
                          </div>
                        )}
                      </div>
                      <div className="text-slate-300">
                        <strong>Name:</strong> {nw.name}
                      </div>
                      <div className="text-slate-300">
                        <strong>Status:</strong> {nw.status}
                      </div>
                      <div className="text-slate-300">
                        <strong>Distance from {selectedWell}:</strong> {formatDistance(nw.distance_km, nw.distance_m)}
                      </div>
                      <div className="text-slate-300">
                        <strong>Water Depth:</strong> {nw.water_depth_m} m
                      </div>
                      <div className="pt-2">
                        <button
                          onClick={() => {
                            if (onOpenIntelligence) {
                              onOpenIntelligence(nw.well_id);
                            } else {
                              onSelectWell(nw.well_id);
                            }
                          }}
                          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-[11px] py-1 rounded flex items-center justify-center gap-1 transition-all"
                        >
                          <ExternalLink className="w-3 h-3" />
                          View Well Intelligence
                        </button>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
              Location data unavailable for this well.
            </div>
          )}

          {/* Map Overlay Badge */}
          <div className="absolute top-3 left-3 z-[400] bg-slate-900/90 backdrop-blur px-3 py-1.5 rounded-md border border-slate-800 text-[11px] font-mono text-slate-300 shadow-md">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>★ Active: <strong>{selectedWell}</strong></span>
              <span className="text-slate-500">|</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>● Radius: <strong>{radiusKm} km</strong></span>
            </div>
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
              <div className="space-y-2.5 max-h-[350px] overflow-y-auto pr-1">
                {nearbyData.nearby_wells.map((nw: NearbyWellItem) => {
                  const isSelected = selectedNearbyWellId === nw.well_id;
                  return (
                    <div
                      key={nw.well_id}
                      onClick={() => setSelectedNearbyWellId(nw.well_id)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-emerald-950/40 border-emerald-500/50 shadow-md shadow-emerald-500/10"
                          : "bg-slate-900 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono">
                        <span className="font-bold text-emerald-400 text-xs flex items-center gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                          {nw.well_id}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-emerald-300 font-bold border border-slate-700">
                          {formatDistance(nw.distance_km, nw.distance_m)}
                        </span>
                      </div>

                      <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between font-sans">
                        <span>{nw.name}</span>
                        <span className="font-mono text-[10px] text-slate-400">
                          Slot: {nw.slot_name}
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                        Surface Platform Slot Distance
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
                          className="text-emerald-400 hover:underline flex items-center gap-1 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30"
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
    </div>
  );
};
