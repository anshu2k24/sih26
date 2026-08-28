export type MLStatusType = "ML_READY" | "ML_NOT_READY" | "ML_UNAVAILABLE" | "NO_TELEMETRY";

export interface MLStatusState {
  status: MLStatusType;
  is_blocked: boolean;
  gate_reason: string;
  cutoff_md?: number;
  risk_score?: number | null;
  features_constructed?: number;
}
