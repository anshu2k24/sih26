import React, { useState, useEffect, useRef } from "react";
import { Header } from "../components/layout/Header";
import { CurrentDrillingState } from "../components/telemetry/CurrentDrillingState";
import { TelemetryCards } from "../components/telemetry/TelemetryCards";
import { LiveSensorCharts } from "../components/charts/LiveSensorCharts";
import { RiskCenter } from "../components/risk/RiskCenter";
import { WellIntelligence } from "../components/events/WellIntelligence";
import { EventTimeline } from "../components/events/EventTimeline";
import { SystemStatus } from "../components/system/SystemStatus";

import { useSensorStream } from "../hooks/useSensorStream";
import { fetchWells, fetchOffsetEvents } from "../services/api";
import type { WellItem } from "../types/api";
import type { EventsResponse } from "../types/events";

export const Dashboard: React.FC = () => {
  const [wells, setWells] = useState<WellItem[]>([]);
  const [selectedWell, setSelectedWell] = useState<string>("15/9-F-15");
  const [nwisData, setNwisData] = useState<EventsResponse | null>(null);

  const lastFetchedDepthRef = useRef<number>(-1);
  const lastFetchedWellRef = useRef<string>("");

  // Load available wells from FastAPI REST backend
  useEffect(() => {
    fetchWells().then((data) => {
      setWells(data);
      if (data.length > 0 && !data.some((w) => w.well_id === selectedWell)) {
        setSelectedWell(data[0].well_id);
      }
    });
  }, []);

  // Live stream hook
  const {
    status,
    currentMd,
    tvd,
    lastTimestamp,
    samplesReceived,
    latestSensor,
    history,
    mlState,
  } = useSensorStream(selectedWell);

  // Load offset DDR events efficiently (when well changes or depth moves by >= 5.0m)
  useEffect(() => {
    const depth = currentMd > 0 ? currentMd : 3000.0;
    const depthDiff = Math.abs(depth - lastFetchedDepthRef.current);
    const wellChanged = selectedWell !== lastFetchedWellRef.current;

    if (wellChanged || depthDiff >= 5.0 || lastFetchedDepthRef.current === -1) {
      lastFetchedDepthRef.current = depth;
      lastFetchedWellRef.current = selectedWell;
      fetchOffsetEvents(selectedWell, depth, 100.0).then((res) => {
        setNwisData(res);
      });
    }
  }, [selectedWell, currentMd]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-blue-500 selection:text-white pb-12">
      {/* Header with Mandatory Scientific Label & Well Selector */}
      <Header
        wells={wells}
        selectedWell={selectedWell}
        onSelectWell={setSelectedWell}
        status={status}
      />

      <main className="max-w-7xl mx-auto px-6 pt-6 space-y-6">
        {/* Section 1: Current Drilling Position & Stream State */}
        <CurrentDrillingState
          wellId={selectedWell}
          currentMd={currentMd}
          tvd={tvd}
          lastTimestamp={lastTimestamp}
          samplesReceived={samplesReceived}
        />

        {/* Section 2: Real-Time Telemetry Parameters */}
        <TelemetryCards latestSensor={latestSensor} />

        {/* Section 3: Real-Time Sensor Telemetry Line Charts */}
        <LiveSensorCharts history={history} />

        {/* Section 4: Predictive Risk Center vs Historical NWIS Intelligence */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RiskCenter mlState={mlState} />
          <WellIntelligence
            nwisData={nwisData}
            activeWell={selectedWell}
            currentMd={currentMd}
          />
        </div>

        {/* Section 5: Depth-Oriented Event Timeline */}
        <EventTimeline
          currentMd={currentMd}
          events={nwisData?.nearby_events || []}
        />

        {/* Section 6: System Infrastructure & Health Status */}
        <SystemStatus streamStatus={status} mlState={mlState} />
      </main>
    </div>
  );
};
