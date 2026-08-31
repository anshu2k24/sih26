/**
 * PS121 Handwritten Notes OCR — TypeScript Interfaces
 */

export type NoteOCRStatus = "UPLOADED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type NoteVerificationStatus = "NEEDS_REVIEW" | "VERIFIED" | "REJECTED";
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";

export interface NoteMeasurement {
  parameter: string;
  value: string;
  numeric_value: number;
  unit: string;
}

export interface NoteEntity {
  type: string;
  value: string;
  role?: string;
  name?: string;
}

export interface NoteStructuredData {
  title: string;
  date: string | null;
  all_dates: string[];
  times: string[];
  summary: string;
  observations: string[];
  measurements: NoteMeasurement[];
  tasks: string[];
  entities: NoteEntity[];
  tags: string[];
}

export interface HandwrittenNote {
  id: string;
  organization_id?: string;
  title: string;
  raw_ocr_text: string;
  verified_text: string;
  source: "handwritten";
  source_file_id: string;
  storage_path: string;
  public_url: string;
  ocr_status: NoteOCRStatus;
  verification_status: NoteVerificationStatus;
  confidence: number | null;
  confidence_level: ConfidenceLevel;
  latest_ocr_run_id?: string;
  structured_data: NoteStructuredData;
  metadata: {
    validation?: {
      dimensions?: [number, number];
      extension?: string;
      format?: string;
      mime_type?: string;
      size_bytes?: number;
    };
    storage?: {
      filename?: string;
      checksum?: string;
    };
    checksum?: string;
    [key: string]: any;
  };
  created_by: string;
  verified_by?: string;
  created_at: string;
  updated_at: string;
  verified_at?: string;
}

export interface OCRRun {
  id: string;
  note_id: string;
  provider: string;
  model: string;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  confidence: number | null;
  raw_result: any;
  normalized_text: string;
  processing_time_ms: number;
  error?: string;
  attempt: number;
  created_at: string;
  completed_at: string;
}

export interface OCRMetrics {
  total_notes: number;
  processing: number;
  needs_review: number;
  verified: number;
  failed: number;
  verification_rate_pct: number;
  active_provider: string;
  active_model: string;
}

export interface NoteProvenance {
  source_file_id: string;
  storage_path: string;
  checksum: string;
  created_by: string;
  verified_by?: string;
  verified_at?: string;
  ocr_run_id?: string;
}
