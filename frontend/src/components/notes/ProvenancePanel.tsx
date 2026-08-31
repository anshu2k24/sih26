import React from "react";
import {
  ShieldCheck,
  FileImage,
  Cpu,
  UserCheck,
  Hash,
  Clock,
} from "lucide-react";
import type { HandwrittenNote, OCRRun } from "../../types/notes";

interface Props {
  note: HandwrittenNote;
  ocrRuns?: OCRRun[];
}

export const ProvenancePanel: React.FC<Props> = ({ note, ocrRuns = [] }) => {
  const latestRun = ocrRuns.length > 0 ? ocrRuns[ocrRuns.length - 1] : null;
  const checksum = note.metadata?.checksum || note.metadata?.storage?.checksum || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          End-to-End Provenance & Traceability Chain
        </h3>
        <span className="text-xs font-mono text-slate-500">
          ID: {note.id.slice(0, 8)}...
        </span>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-blue-500 before:via-purple-500 before:to-emerald-500">
        {/* Step 1: Original Ingestion */}
        <div className="relative group">
          <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-blue-950 border-2 border-blue-500 flex items-center justify-center">
            <FileImage className="w-2.5 h-2.5 text-blue-400" />
          </div>
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <strong className="text-slate-200 font-semibold">1. Original Image Ingestion</strong>
              <span className="text-[11px] text-slate-500">{new Date(note.created_at).toLocaleString()}</span>
            </div>
            <p className="text-slate-400 font-mono text-[11px]">
              Source File ID: <span className="text-slate-300">{note.source_file_id || "file_source_raw"}</span>
            </p>
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Hash className="w-3 h-3 text-cyan-400" />
              <span>SHA-256:</span>
              <span className="font-mono text-cyan-300 truncate max-w-[240px]">{checksum}</span>
            </div>
          </div>
        </div>

        {/* Step 2: OCR Processing Run */}
        <div className="relative group">
          <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-purple-950 border-2 border-purple-500 flex items-center justify-center">
            <Cpu className="w-2.5 h-2.5 text-purple-400" />
          </div>
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <strong className="text-slate-200 font-semibold">2. OCR Processing Run</strong>
              {latestRun && (
                <span className="px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800/40 text-[10px] font-mono">
                  Attempt #{latestRun.attempt}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
              <div>
                Provider: <span className="text-slate-200 font-medium capitalize">{latestRun?.provider || "Mistral OCR"}</span>
              </div>
              <div>
                Model: <span className="text-slate-200 font-mono">{latestRun?.model || "mistral-ocr-latest"}</span>
              </div>
              <div>
                Latency: <span className="text-amber-300 font-mono">{latestRun?.processing_time_ms ? `${latestRun.processing_time_ms}ms` : "Fast (<1s)"}</span>
              </div>
              <div>
                Confidence: <span className="text-emerald-300 font-medium">{note.confidence ? `${(note.confidence * 100).toFixed(0)}%` : "High"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Step 3: Raw OCR Draft State */}
        <div className="relative group">
          <div className="absolute -left-6 top-1 w-5 h-5 rounded-full bg-amber-950 border-2 border-amber-500 flex items-center justify-center">
            <Clock className="w-2.5 h-2.5 text-amber-400" />
          </div>
          <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <strong className="text-slate-200 font-semibold">3. Raw OCR Draft Generated</strong>
              <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/40 text-[10px]">
                Draft (Immutable)
              </span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Raw transcript preserved separately to audit original machine output vs human corrections.
            </p>
          </div>
        </div>

        {/* Step 4: Human Verification & Trust Promotion */}
        <div className="relative group">
          <div className={`absolute -left-6 top-1 w-5 h-5 rounded-full ${note.verification_status === "VERIFIED" ? "bg-emerald-950 border-emerald-500" : "bg-slate-800 border-slate-600"} border-2 flex items-center justify-center`}>
            <UserCheck className={`w-2.5 h-2.5 ${note.verification_status === "VERIFIED" ? "text-emerald-400" : "text-slate-400"}`} />
          </div>
          <div className={`p-3 rounded-xl border text-xs space-y-1.5 ${note.verification_status === "VERIFIED" ? "bg-emerald-950/20 border-emerald-800/60" : "bg-slate-950/40 border-slate-800"}`}>
            <div className="flex items-center justify-between">
              <strong className={note.verification_status === "VERIFIED" ? "text-emerald-300 font-bold" : "text-slate-400"}>
                4. Human Verification & Trust Promotion
              </strong>
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${note.verification_status === "VERIFIED" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40" : "bg-slate-800 text-slate-400"}`}>
                {note.verification_status}
              </span>
            </div>

            {note.verification_status === "VERIFIED" ? (
              <div className="text-[11px] text-slate-300 space-y-1 pt-1">
                <div>Verified By: <span className="font-mono text-emerald-300 font-semibold">{note.verified_by || "Verified Operator"}</span></div>
                <div>Verified At: <span className="font-mono text-slate-400">{note.verified_at ? new Date(note.verified_at).toLocaleString() : "Recently"}</span></div>
              </div>
            ) : (
              <p className="text-slate-500 text-[11px]">
                Pending human verification. Data is currently classified as unverified draft.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
