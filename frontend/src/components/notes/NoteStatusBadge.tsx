import React from "react";
import { CheckCircle2, Clock, AlertCircle, Loader2, FileQuestion } from "lucide-react";
import type { NoteOCRStatus, NoteVerificationStatus } from "../../types/notes";

interface Props {
  verificationStatus?: NoteVerificationStatus;
  ocrStatus?: NoteOCRStatus;
  size?: "sm" | "md";
}

export const NoteStatusBadge: React.FC<Props> = ({
  verificationStatus,
  ocrStatus,
  size = "md",
}) => {
  const pad = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  if (ocrStatus === "PROCESSING") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30 ${pad} animate-pulse`}>
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        OCR Processing
      </span>
    );
  }

  if (ocrStatus === "FAILED") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 ${pad}`}>
        <AlertCircle className="w-3.5 h-3.5" />
        OCR Failed
      </span>
    );
  }

  if (verificationStatus === "VERIFIED") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${pad}`}>
        <CheckCircle2 className="w-3.5 h-3.5" />
        Verified Data
      </span>
    );
  }

  if (verificationStatus === "NEEDS_REVIEW") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 ${pad}`}>
        <Clock className="w-3.5 h-3.5" />
        Needs Review
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/30 ${pad}`}>
      <FileQuestion className="w-3.5 h-3.5" />
      {verificationStatus || ocrStatus || "Uploaded"}
    </span>
  );
};
