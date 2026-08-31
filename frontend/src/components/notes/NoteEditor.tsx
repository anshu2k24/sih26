import React, { useState } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCw,
  Save,
  CheckCircle2,
  RefreshCw,
  Eye,
  FileText,
  AlertTriangle,
} from "lucide-react";
import type { HandwrittenNote } from "../../types/notes";
import { getNoteImageUrl } from "../../services/notesApi";

interface Props {
  note: HandwrittenNote;
  onSaveDraft: (text: string, title: string) => Promise<void>;
  onVerify: (text: string, title: string) => Promise<void>;
  onRetry: () => Promise<void>;
  saving: boolean;
  verifying: boolean;
  retrying: boolean;
}

export const NoteEditor: React.FC<Props> = ({
  note,
  onSaveDraft,
  onVerify,
  onRetry,
  saving,
  verifying,
  retrying,
}) => {
  const [title, setTitle] = useState<string>(note.title || "Handwritten Note");
  const [text, setText] = useState<string>(note.verified_text || note.raw_ocr_text || "");
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [showDiff, setShowDiff] = useState<boolean>(false);

  const imageUrl = getNoteImageUrl(note.public_url);
  const isDirty = text !== (note.verified_text || note.raw_ocr_text) || title !== note.title;

  const handleZoomIn = () => setZoom((z) => Math.min(z + 25, 300));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 25, 50));
  const handleRotate = () => setRotation((r) => (r + 90) % 360);

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Top Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/80 p-4 rounded-2xl border border-slate-800 backdrop-blur-md">
        <div className="flex-1 min-w-0 w-full sm:w-auto">
          <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
            Note Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-3.5 py-1.5 text-sm font-semibold text-slate-100 focus:outline-none focus:border-blue-500 transition"
            placeholder="Enter title for this handwritten note..."
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <button
            onClick={() => onRetry()}
            disabled={retrying || saving || verifying}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition disabled:opacity-50"
            title="Retry OCR transcription on original image"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${retrying ? "animate-spin text-blue-400" : ""}`} />
            {retrying ? "Retrying..." : "Retry OCR"}
          </button>

          <button
            onClick={() => onSaveDraft(text, title)}
            disabled={saving || verifying}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5 text-blue-400" />
            {saving ? "Saving..." : "Save Draft"}
          </button>

          <button
            onClick={() => onVerify(text, title)}
            disabled={verifying || saving}
            className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-900/30 transition disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-100" />
            {verifying ? "Verifying..." : "Verify & Save"}
          </button>
        </div>
      </div>

      {/* Side by Side Split Canvas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-[580px]">
        {/* Left: Original Handwritten Image Viewer */}
        <div className="flex flex-col bg-slate-950/80 rounded-2xl border border-slate-800 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-blue-400" />
              <span className="font-semibold text-slate-200">Original Handwritten Document</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleZoomOut}
                className="p-1 text-slate-400 hover:text-slate-200 bg-slate-800/80 rounded-lg hover:bg-slate-700 transition"
                title="Zoom out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] font-mono text-slate-400 px-1.5">{zoom}%</span>
              <button
                onClick={handleZoomIn}
                className="p-1 text-slate-400 hover:text-slate-200 bg-slate-800/80 rounded-lg hover:bg-slate-700 transition"
                title="Zoom in"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleRotate}
                className="p-1 text-slate-400 hover:text-slate-200 bg-slate-800/80 rounded-lg hover:bg-slate-700 ml-1 transition"
                title="Rotate 90°"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-slate-950/90 min-h-[420px]">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt="Original Handwritten Note"
                style={{
                  transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                  transition: "transform 0.15s ease-out",
                  maxHeight: "100%",
                }}
                className="object-contain rounded-lg shadow-2xl origin-center max-w-full"
              />
            ) : (
              <div className="text-center text-slate-500 text-xs">
                Image preview not available
              </div>
            )}
          </div>
        </div>

        {/* Right: Editable Transcription Editor */}
        <div className="flex flex-col bg-slate-950/80 rounded-2xl border border-slate-800 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold text-slate-200">Extracted Transcription (Editable)</span>
              {note.confidence !== null && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800/40">
                  Confidence: {Math.round((note.confidence || 0.9) * 100)}%
                </span>
              )}
            </div>

            <button
              onClick={() => setShowDiff(!showDiff)}
              className={`px-2 py-1 text-[11px] rounded-lg border transition ${
                showDiff
                  ? "bg-purple-950/80 text-purple-300 border-purple-700"
                  : "bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200"
              }`}
            >
              {showDiff ? "Hide Raw Draft" : "Compare with Raw Draft"}
            </button>
          </div>

          {showDiff && (
            <div className="bg-slate-900/80 p-3 border-b border-slate-800 text-xs max-h-36 overflow-y-auto">
              <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider block mb-1">
                Machine Raw OCR Transcript (Draft):
              </span>
              <pre className="font-mono text-slate-400 whitespace-pre-wrap text-[11px]">
                {note.raw_ocr_text || "(Empty raw transcript)"}
              </pre>
            </div>
          )}

          <div className="flex-1 flex flex-col p-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="flex-1 w-full bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-sm font-sans text-slate-100 focus:outline-none focus:border-emerald-500/80 leading-relaxed resize-none transition"
              placeholder="Correct transcribed handwritten text here..."
              rows={18}
            />

            <div className="flex items-center justify-between mt-2.5 text-xs text-slate-500">
              <span className="flex items-center gap-2">
                <span>{text.split(/\s+/).filter(Boolean).length} words</span>
                <span>•</span>
                <span>{text.length} characters</span>
              </span>
              {isDirty && (
                <span className="text-amber-400 font-medium text-[11px] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Unsaved edits
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
