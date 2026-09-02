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
  const isSm = size === "sm";
  const commonClasses = `inline-flex items-center gap-1.5 font-[700] rounded-[6px] tracking-wide transition-all ${isSm ? "px-[8px] py-[4px] text-[10px]" : "px-[10px] py-[6px] text-[11px]"}`;

  if (ocrStatus === "PROCESSING") {
    return (
      <span 
        className={`${commonClasses} animate-pulse`}
        style={{ background: "rgba(59, 130, 246, 0.15)", border: "1px solid rgba(59, 130, 246, 0.4)", color: "#60A5FA", boxShadow: "0 0 10px rgba(59, 130, 246, 0.15)" }}
      >
        <Loader2 className={`${isSm ? "w-3 h-3" : "w-3.5 h-3.5"} animate-spin`} />
        OCR Processing
      </span>
    );
  }

  if (ocrStatus === "FAILED") {
    return (
      <span 
        className={commonClasses}
        style={{ background: "rgba(225, 29, 72, 0.15)", border: "1px solid rgba(225, 29, 72, 0.4)", color: "#FB7185", boxShadow: "0 0 10px rgba(225, 29, 72, 0.15)" }}
      >
        <AlertCircle className={isSm ? "w-3 h-3" : "w-3.5 h-3.5"} />
        OCR Failed
      </span>
    );
  }

  if (verificationStatus === "VERIFIED") {
    return (
      <span 
        className={commonClasses}
        style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid rgba(16, 185, 129, 0.4)", color: "#34D399", boxShadow: "0 0 10px rgba(16, 185, 129, 0.15)" }}
      >
        <CheckCircle2 className={isSm ? "w-3 h-3" : "w-3.5 h-3.5"} />
        Verified Data
      </span>
    );
  }

  if (verificationStatus === "NEEDS_REVIEW") {
    return (
      <span 
        className={commonClasses}
        style={{ background: "rgba(245, 158, 11, 0.15)", border: "1px solid rgba(245, 158, 11, 0.4)", color: "#FBBF24", boxShadow: "0 0 10px rgba(245, 158, 11, 0.15)" }}
      >
        <Clock className={isSm ? "w-3 h-3" : "w-3.5 h-3.5"} />
        Needs Review
      </span>
    );
  }

  return (
    <span 
      className={commonClasses}
      style={{ background: "rgba(100, 116, 139, 0.15)", border: "1px solid rgba(100, 116, 139, 0.4)", color: "#94A3B8", boxShadow: "none" }}
    >
      <FileQuestion className={isSm ? "w-3 h-3" : "w-3.5 h-3.5"} />
      {verificationStatus || ocrStatus || "Uploaded"}
    </span>
  );
};
