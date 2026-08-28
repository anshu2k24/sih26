export interface WellItem {
  well_id: string;
  status: string;
}

export interface WellsResponse {
  wells: WellItem[];
}

export interface WSEventMessage {
  type: "sensor_update" | "ml_update" | "stream_status" | "error";
  data: any;
}
