import React from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { OCRUpload } from "../components/notes/OCRUpload";
import type { HandwrittenNote } from "../types/notes";

export const NoteUploadPage: React.FC = () => {
  const navigate = useNavigate();

  const handleUploadSuccess = (note: HandwrittenNote) => {
    // Navigate straight to side-by-side review
    navigate(`/notes/${note.id}/review`);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header with back button */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <Link
          to="/notes"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Notes Repository</span>
        </Link>
        <span className="text-xs font-mono text-slate-500">PS121 Ingestion Pipeline</span>
      </div>

      {/* Main Upload Dropzone / Camera Area */}
      <OCRUpload onSuccess={handleUploadSuccess} />

      {/* Info card on Verification Policy */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 text-xs text-slate-400 space-y-2">
        <div className="flex items-center gap-2 text-slate-200 font-semibold">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span>Important Operating Principle:</span>
        </div>
        <p className="leading-relaxed">
          OCR output is treated as a <strong>draft</strong>. Uploaded files undergo SHA-256 fingerprinting, contrast & orientation preprocessing, and multi-line handwriting transcription. Human review is required before text is promoted to verified trusted data.
        </p>
      </div>
    </div>
  );
};
