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
        <div class="absolute w-10 h-10 rounded-full bg-[#FF8A00]/40 animate-ping shadow-[0_0_20px_#FF8A00]"></div>
        <div class="w-8 h-8 rounded-full bg-[#050607] border-[2px] border-[#FF9D1A] flex items-center justify-center shadow-[0_0_15px_rgba(255,157,26,0.6)]">
          <span class="text-[#FF9D1A] font-bold text-sm drop-shadow-[0_0_5px_#FF9D1A]">★</span>
        </div>
        <div class="absolute top-10 whitespace-nowrap bg-[rgba(18,16,14,0.95)] backdrop-blur-md text-[#FF9D1A] font-mono font-bold text-[11px] px-[8px] py-[4px] rounded-[6px] border border-[rgba(255,138,0,0.5)] shadow-[0_4px_15px_rgba(0,0,0,0.6)] uppercase tracking-wider">
          ★ ${wellId} (ACTIVE)
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

const createNearbyMarkerIcon = (wellId: string, isSelected: boolean, hasAlert: boolean = false) => {
  const color = hasAlert ? "#FF3250" : isSelected ? "#FF9D1A" : "#FF8A00";
  const bg = isSelected ? "rgba(255,138,0,0.15)" : "rgba(18, 16, 14, 0.95)";
  const label = hasAlert ? `⚠ ${wellId}` : `● ${wellId}`;
  return L.divIcon({
    className: "custom-nearby-marker",
    html: `
      <div style="
        background: ${bg};
        backdrop-filter: blur(8px);
        border: 1.5px solid ${color};
        color: ${color};
        padding: 4px 10px;
        border-radius: 9999px;
        font-family: 'Space Grotesk', monospace;
        font-size: 11px;
        font-weight: 700;
        white-space: nowrap;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5), 0 0 ${hasAlert ? "20px rgba(255,50,80,0.6)" : "10px rgba(255,138,0,0.3)"};
        display: flex;
        align-items: center;
        gap: 4px;
        letter-spacing: 0.05em;
        transition: all 0.3s ease;
      ">
        ${label}
      </div>
    `,
    iconSize: [90, 28],
    iconAnchor: [45, 14],
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
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 16, animate: true, duration: 1.2 });
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
    <div 
      className="rounded-[20px] p-[24px] space-y-[20px] transition-all duration-300 relative group"
      style={{
        background: "rgba(18, 16, 14, 0.75)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 138, 0, 0.25)",
        boxShadow: "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)"
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.4)";
        e.currentTarget.style.boxShadow = "0 15px 50px rgba(0,0,0,0.5), 0 0 30px rgba(255,138,0,0.1), inset 0 0 30px rgba(255,138,0,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
        e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.5), inset 0 0 20px rgba(255,138,0,0.05)";
      }}
    >
      {/* Header Controls Banner */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-[rgba(255,138,0,0.2)] pb-[20px]">
        <div>
          <div className="flex items-center gap-3">
            <Compass className="w-5 h-5 text-[#FF9D1A] animate-spin-slow drop-shadow-[0_0_5px_rgba(255,157,26,0.6)]" />
            <h2 className="text-[18px] font-[700] text-white font-['Space_Grotesk',sans-serif] uppercase tracking-wider drop-shadow-sm">
              Nearby Wells Intelligence Map
            </h2>
            <span className="text-[10px] px-[8px] py-[2px] rounded-[6px] font-[700] font-mono tracking-wider uppercase border"
              style={{ background: "rgba(255, 138, 0, 0.15)", borderColor: "rgba(255, 138, 0, 0.4)", color: "#FF9D1A" }}
            >
              NWIS GEOSPATIAL
            </span>
          </div>
          <p className="text-[13px] text-[#A1A1AA] mt-2 font-mono">
            Interactive map-based offset intelligence for <strong className="text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">{selectedWell}</strong> in Equinor Volve Field (Block 15/9, North Sea).
          </p>
        </div>

        {/* Search Radius Controls */}
        <div 
          className="flex items-center gap-[12px] p-[6px] rounded-[12px] border transition-all duration-300"
          style={{ background: "rgba(0,0,0,0.6)", borderColor: "rgba(255,138,0,0.3)", boxShadow: "inset 0 0 15px rgba(255,138,0,0.05)" }}
        >
          <Layers className="w-4 h-4 text-[#FF8A00] ml-2 drop-shadow-[0_0_5px_rgba(255,138,0,0.5)]" />
          <span className="text-[11px] text-[#E2E2E2] font-[700] uppercase tracking-wider">Search Radius:</span>
          <div className="flex items-center gap-[4px] pr-[2px]">
            {radiusOptions.map((r) => {
              const isActive = radiusKm === r;
              return (
                <button
                  key={r}
                  onClick={() => setRadiusKm(r)}
                  className="text-[11px] px-[12px] py-[6px] rounded-[8px] font-[700] uppercase tracking-wider transition-all duration-200"
                  style={
                    isActive
                      ? {
                          background: "radial-gradient(circle at top, rgba(255,138,0,0.35), rgba(255,138,0,0.15))",
                          color: "#FFFFFF",
                          border: "1px solid rgba(255, 138, 0, 0.8)",
                          boxShadow: "0 4px 15px rgba(255, 138, 0, 0.25), inset 0 0 10px rgba(255,138,0,0.2)",
                          textShadow: "0 0 8px rgba(255,138,0,0.5)"
                        }
                      : {
                          background: "transparent",
                          color: "#A1A1AA",
                          border: "1px solid transparent",
                        }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "rgba(255, 138, 0, 0.1)";
                      e.currentTarget.style.color = "#FF9D1A";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.color = "#A1A1AA";
                    }
                  }}
                >
                  {r < 1 ? `${r * 1000}m` : `${r}km`}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Grid: Map (2/3) + Nearby Wells List (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-[24px]">
        {/* Map Container */}
        <div 
          className="lg:col-span-2 relative h-[500px] rounded-[16px] overflow-hidden transition-all duration-300"
          style={{ border: "1px solid rgba(255, 138, 0, 0.25)", boxShadow: "0 10px 40px rgba(0,0,0,0.6)" }}
        >
          {activeWellCoords ? (
            <MapContainer
              center={activeWellCoords}
              zoom={radiusKm <= 0.5 ? 17 : radiusKm <= 1.0 ? 16 : radiusKm <= 5.0 ? 15 : radiusKm <= 10.0 ? 14 : 13}
              scrollWheelZoom={true}
              style={{ height: "100%", width: "100%", backgroundColor: "#050607" }}
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
                  color: "#FF8A00",
                  fillColor: "#FF8A00",
                  fillOpacity: 0.08,
                  weight: 2,
                  dashArray: "6, 8",
                }}
              />

              {/* Active Well Marker (Glowing Star) */}
              <Marker
                position={activeWellCoords}
                icon={createActiveMarkerIcon(selectedWell)}
              >
                <Popup className="custom-leaflet-popup">
                  <div 
                    className="p-[12px] space-y-[8px] font-mono text-[11px] rounded-[8px]"
                    style={{ background: "rgba(18,16,14,0.95)", border: "1px solid rgba(255,138,0,0.3)" }}
                  >
                    <div className="font-[700] text-[#FF9D1A] text-[12px] border-b border-[rgba(255,138,0,0.2)] pb-[8px] uppercase tracking-wider flex items-center gap-2">
                      <span className="drop-shadow-[0_0_5px_#FF9D1A]">★</span> {selectedWell} <span className="text-[#A1A1AA] text-[10px]">(ACTIVE)</span>
                    </div>
                    <div className="text-[#E2E2E2]">
                      <strong className="text-[#FF8A00]">Status:</strong> {activeWellItem?.status || "Active Drilling"}
                    </div>
                    <div className="text-[#E2E2E2]">
                      <strong className="text-[#FF8A00]">Field:</strong> {activeWellItem?.field || "Volve (Block 15/9)"}
                    </div>
                    <div className="text-[#E2E2E2]">
                      <strong className="text-[#FF8A00]">Slot:</strong> {activeWellItem?.slot_name || "Slot 3"}
                    </div>
                    <div className="text-[#E2E2E2]">
                      <strong className="text-[#FF8A00]">Coordinates:</strong> {activeWellCoords[0].toFixed(5)}°N, {activeWellCoords[1].toFixed(5)}°E
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
                    <Popup className="custom-leaflet-popup">
                      <div 
                        className="p-[12px] space-y-[10px] font-mono text-[11px] rounded-[8px]"
                        style={{ background: "rgba(18,16,14,0.95)", border: "1px solid rgba(255,138,0,0.3)" }}
                      >
                        <div className="font-[700] text-[#FF9D1A] text-[12px] border-b border-[rgba(255,138,0,0.2)] pb-[8px] uppercase tracking-wider flex items-center justify-between gap-[16px]">
                          <span>{hasAlert ? `⚠ ${nw.well_id}` : `● ${nw.well_id}`}</span>
                          <span 
                            className="bg-[rgba(255,138,0,0.15)] text-[#FF9D1A] px-[6px] py-[2px] rounded-[4px] border border-[rgba(255,138,0,0.4)]"
                          >
                            {formatDistance(nw.distance_km, nw.distance_m)}
                          </span>
                        </div>

                        {matchForWell && (
                          <div 
                            className="p-[8px] rounded-[6px] space-y-[4px]"
                            style={{ background: "rgba(255,50,80,0.1)", border: "1px solid rgba(255,50,80,0.4)" }}
                          >
                            <div className="font-[700] text-[#FF3250] flex items-center gap-[4px] uppercase drop-shadow-[0_0_5px_rgba(255,50,80,0.5)]">
                              <span>⚠</span> {matchForWell.proximity_classification}
                            </div>
                            <div className="text-[#E2E2E2]">Event: <strong className="text-white">{matchForWell.event_type}</strong> @ {matchForWell.event_md}m</div>
                            <div className="text-[#E2E2E2]">Depth Delta: <strong className="text-white">Δ {matchForWell.delta_md}m</strong></div>
                            <div className="text-[9px] text-[#FF3250] mt-[4px] uppercase font-[700] tracking-wider">
                              HISTORICAL EVENT — NOT A PREDICTION
                            </div>
                          </div>
                        )}

                        <div className="text-[#E2E2E2] space-y-[4px] pt-[4px]">
                          <div><strong className="text-[#FF8A00]">Name:</strong> {nw.name}</div>
                          <div><strong className="text-[#FF8A00]">Status:</strong> {nw.status}</div>
                          <div><strong className="text-[#FF8A00]">Water Depth:</strong> {nw.water_depth_m} m</div>
                        </div>

                        <div className="pt-[8px]">
                          <button
                            onClick={() => {
                              if (onOpenIntelligence) {
                                onOpenIntelligence(nw.well_id);
                              } else {
                                onSelectWell(nw.well_id);
                              }
                            }}
                            className="w-full flex items-center justify-center gap-[6px] px-[12px] py-[8px] rounded-[6px] font-[700] text-[11px] uppercase tracking-wider transition-all"
                            style={{ background: "rgba(255,138,0,0.15)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.4)" }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = "rgba(255,138,0,0.3)";
                              e.currentTarget.style.boxShadow = "0 0 15px rgba(255,138,0,0.2)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = "rgba(255,138,0,0.15)";
                              e.currentTarget.style.boxShadow = "none";
                            }}
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            View Intelligence
                          </button>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-[#686868] text-[12px] font-mono tracking-widest uppercase">
              Location data unavailable for this well.
            </div>
          )}

          {/* Map Overlay Badge */}
          <div 
            className="absolute top-[16px] left-[16px] z-[400] px-[16px] py-[10px] rounded-[10px] text-[11px] font-[700] font-mono text-[#E2E2E2] uppercase tracking-wider"
            style={{ background: "rgba(18,16,14,0.85)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,138,0,0.3)", boxShadow: "0 6px 20px rgba(0,0,0,0.6)" }}
          >
            <div className="flex items-center gap-[12px]">
              <span className="flex items-center gap-[6px]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#34D399] animate-pulse drop-shadow-[0_0_5px_#34D399]"></span>
                <span className="text-[#A1A1AA]">Active:</span> <strong className="text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">{selectedWell}</strong>
              </span>
              <span className="text-[rgba(255,255,255,0.2)]">|</span>
              <span className="flex items-center gap-[6px]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#FF8A00] drop-shadow-[0_0_5px_#FF8A00]"></span>
                <span className="text-[#A1A1AA]">Radius:</span> <strong className="text-white drop-shadow-[0_0_5px_rgba(255,255,255,0.5)]">{radiusKm} km</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Nearby Wells Sorted List Panel */}
        <div 
          className="rounded-[16px] p-[24px] flex flex-col justify-between h-[500px] transition-all duration-300"
          style={{
            background: "rgba(5, 7, 9, 0.75)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            border: "1px solid rgba(255, 138, 0, 0.15)",
            boxShadow: "inset 0 0 30px rgba(0,0,0,0.3)"
          }}
        >
          <div>
            <div className="flex items-center justify-between border-b border-[rgba(255,138,0,0.2)] pb-[16px] mb-[16px]">
              <div className="flex items-center gap-[8px] text-[13px] font-[700] text-white uppercase font-mono tracking-wider drop-shadow-sm">
                <Navigation className="w-4 h-4 text-[#FF9D1A]" />
                Nearby Wells ({nearbyData?.count || 0})
              </div>
              <span className="text-[10px] text-[#686868] font-[700] uppercase tracking-widest font-mono">
                Sorted by Distance
              </span>
            </div>

            {/* List Container */}
            {isLoading ? (
              <div className="py-[60px] text-center text-[11px] font-mono font-[700] uppercase tracking-widest text-[#FF8A00] animate-pulse">
                Calculating Haversine offset distances...
              </div>
            ) : nearbyData && nearbyData.nearby_wells.length > 0 ? (
              <div className="space-y-[12px] max-h-[380px] overflow-y-auto custom-scrollbar pr-[8px]">
                {nearbyData.nearby_wells.map((nw: NearbyWellItem) => {
                  const isSelected = selectedNearbyWellId === nw.well_id;
                  return (
                    <div
                      key={nw.well_id}
                      onClick={() => setSelectedNearbyWellId(nw.well_id)}
                      className="p-[16px] rounded-[12px] transition-all duration-300 cursor-pointer"
                      style={
                        isSelected
                          ? {
                              background: "rgba(255, 138, 0, 0.1)",
                              border: "1px solid rgba(255, 138, 0, 0.5)",
                              boxShadow: "0 0 20px rgba(255, 138, 0, 0.15)"
                            }
                          : {
                              background: "rgba(255, 255, 255, 0.02)",
                              border: "1px solid rgba(255, 255, 255, 0.05)",
                              boxShadow: "none"
                            }
                      }
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.background = "rgba(255, 138, 0, 0.05)";
                          e.currentTarget.style.borderColor = "rgba(255, 138, 0, 0.25)";
                          e.currentTarget.style.boxShadow = "0 0 10px rgba(255, 138, 0, 0.05)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                          e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.05)";
                          e.currentTarget.style.boxShadow = "none";
                        }
                      }}
                    >
                      <div className="flex items-center justify-between font-mono mb-[6px]">
                        <span className="font-[700] text-[#FF9D1A] text-[12px] flex items-center gap-[6px] drop-shadow-sm">
                          <MapPin className="w-3.5 h-3.5" />
                          {nw.well_id}
                        </span>
                        <span 
                          className="text-[10px] px-[8px] py-[2px] rounded-[6px] font-[700] tracking-wider"
                          style={{ background: "rgba(0,0,0,0.6)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.3)" }}
                        >
                          {formatDistance(nw.distance_km, nw.distance_m)}
                        </span>
                      </div>

                      <div className="text-[12px] text-[#A1A1AA] flex items-center justify-between font-sans mb-[4px]">
                        <span className="truncate pr-2">{nw.name}</span>
                        <span className="font-mono text-[10px] text-[#686868] shrink-0 uppercase tracking-widest">
                          Slot: {nw.slot_name}
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-[#686868] uppercase tracking-widest">
                        Surface Platform Slot Distance
                      </div>

                      <div className="mt-[12px] pt-[12px] border-t border-[rgba(255,255,255,0.05)] flex items-center justify-between text-[10px] font-[700] font-mono uppercase tracking-wider">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectWell(nw.well_id);
                          }}
                          className="text-[#9A9A9A] hover:text-[#FFFFFF] flex items-center gap-[4px] transition-colors"
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
                          className="flex items-center gap-[4px] px-[10px] py-[6px] rounded-[6px] transition-all"
                          style={{ background: "rgba(255,138,0,0.1)", color: "#FF9D1A", border: "1px solid rgba(255,138,0,0.3)" }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = "rgba(255,138,0,0.25)";
                            e.currentTarget.style.boxShadow = "0 0 10px rgba(255,138,0,0.2)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = "rgba(255,138,0,0.1)";
                            e.currentTarget.style.boxShadow = "none";
                          }}
                        >
                          View Intelligence ➔
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div 
                className="py-[60px] text-center rounded-[12px] text-[11px] font-mono font-[700] text-[#686868] uppercase tracking-widest space-y-[8px]"
                style={{ background: "rgba(0,0,0,0.3)", border: "1px dashed rgba(255,255,255,0.1)" }}
              >
                <div>No nearby offset wells found within {radiusKm} km.</div>
                <div className="text-[10px] opacity-70">
                  Try expanding the search radius using the controls above.
                </div>
              </div>
            )}
          </div>

          <div className="pt-[16px] border-t border-[rgba(255,138,0,0.2)] text-[10px] font-[700] text-[#686868] font-mono uppercase tracking-widest flex flex-wrap items-center justify-between gap-2">
            <span className="flex items-center gap-[6px]">
              <Shield className="w-3.5 h-3.5 text-[#FF9D1A]" />
              Haversine Proximity Engine
            </span>
            <span className="text-[#60A5FA]">NPD Verified Coordinates</span>
          </div>
        </div>
      </div>
    </div>
  );
};
