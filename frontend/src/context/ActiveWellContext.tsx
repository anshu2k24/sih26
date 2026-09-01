import React, { createContext, useContext, useState, useEffect } from "react";
import type { WellItem } from "../types/api";
import type { SensorRecord, StreamConnectionStatus } from "../types/sensor";
import type { MLStatusState } from "../types/ml";
import { fetchWells } from "../services/api";
import { useSensorStream } from "../hooks/useSensorStream";

interface ActiveWellContextType {
  wells: WellItem[];
  selectedWell: string;
  setSelectedWell: (wellId: string) => void;
  status: StreamConnectionStatus;
  currentMd: number;
  tvd: number | null;
  lastTimestamp: string;
  samplesReceived: number;
  latestSensor: SensorRecord | null;
  history: SensorRecord[];
  mlState: MLStatusState;
}

const ActiveWellContext = createContext<ActiveWellContextType | undefined>(undefined);

export const ActiveWellProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [wells, setWells] = useState<WellItem[]>([]);
  const [selectedWell, setSelectedWell] = useState<string>("15/9-F-9");

  useEffect(() => {
    fetchWells().then((data) => {
      if (data && data.length > 0) {
        setWells(data);
        if (!data.some((w) => w.well_id === selectedWell)) {
          setSelectedWell(data[0].well_id);
        }
      }
    });
  }, []);

  const streamState = useSensorStream(selectedWell);

  return (
    <ActiveWellContext.Provider
      value={{
        wells,
        selectedWell,
        setSelectedWell,
        ...streamState,
      }}
    >
      {children}
    </ActiveWellContext.Provider>
  );
};

export const useActiveWell = (): ActiveWellContextType => {
  const context = useContext(ActiveWellContext);
  if (!context) {
    throw new Error("useActiveWell must be used within an ActiveWellProvider");
  }
  return context;
};
