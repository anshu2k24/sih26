import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  FileJson,
  CheckCircle2,
  History,
  Copy,
  Check,
  Eye,
  Trash2,
  RefreshCw,
} from "lucide-react";
import type { HandwrittenNote, OCRRun } from "../types/notes";
import {
  fetchNoteDetailApi,
  deleteNoteApi,
  getNoteExportUrl,
  getNoteImageUrl,
} from "../services/notesApi";
import { NoteStatusBadge } from "../components/notes/NoteStatusBadge";
import { StructuredInfo } from "../components/notes/StructuredInfo";
import { ProvenancePanel } from "../components/notes/ProvenancePanel";

export const NoteDetailPage: React.FC = () => {
  const { noteId } = useParams<{ noteId: string }>();
  const navigate = useNavigate();

  const [note, setNote] = useState<HandwrittenNote | null>(null);
  const [ocrRuns, setOcrRuns] = useState<OCRRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [showRaw, setShowRaw] = useState<boolean>(false);

  const loadNote = async () => {
    if (!noteId) return;
    setLoading(true);
    const data = await fetchNoteDetailApi(noteId);
    if (data && data.note) {
      setNote(data.note);
      setOcrRuns(data.ocr_runs || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadNote();
  }, [noteId]);

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!noteId) return;
    if (window.confirm("Are you sure you want to delete this handwritten note?")) {
      const ok = await deleteNoteApi(noteId);
      if (ok) {
        navigate("/notes");
      }
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-400 mx-auto" />
        <p className="text-xs text-slate-400">Loading handwritten note record...</p>
      </div>
    );
  }

  if (!note) {
    return (
      <div className="p-8 text-center bg-slate-900/60 rounded-3xl border border-slate-800 space-y-4">
        <h3 className="text-base font-bold text-slate-100">Note Not Found</h3>
        <Link to="/notes" className="px-4 py-2 bg-blue-600 rounded-xl text-xs text-white">
          Back to Notes
        </Link>
      </div>
    );
  }

  const imageUrl = getNoteImageUrl(note.public_url);

  return (
    <div className="space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Link
            to="/notes"
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-slate-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <NoteStatusBadge
                verificationStatus={note.verification_status}
                ocrStatus={note.ocr_status}
                size="sm"
              />
              <span className="text-[11px] font-mono text-slate-500">ID: {note.id}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-100 mt-0.5">
              {note.title}
            </h1>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to={`/notes/${note.id}/review`}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition flex items-center gap-1.5"
          >
            <span>Review & Edit</span>
          </Link>

          <a
            href={getNoteExportUrl(note.id, "txt")}
            download
            className="px-3 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5 text-blue-400" />
            <span>TXT</span>
          </a>

          <a
            href={getNoteExportUrl(note.id, "json")}
            download
            className="px-3 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5"
          >
            <FileJson className="w-3.5 h-3.5 text-purple-400" />
            <span>JSON</span>
          </a>

          <button
            onClick={handleDelete}
            className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 border border-slate-800 transition"
            title="Delete note"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Grid: Document Viewer & Verified Text */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Original Image */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Eye className="w-4 h-4 text-blue-400" />
              Source Handwritten Image
            </h3>
            {note.metadata?.validation?.dimensions && (
              <span className="text-[11px] font-mono text-slate-500">
                {note.metadata.validation.dimensions[0]}x{note.metadata.validation.dimensions[1]}px
              </span>
            )}
          </div>

          <div className="w-full max-h-[500px] overflow-hidden rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center p-2">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={note.title}
                className="max-h-[480px] object-contain rounded-lg shadow-xl"
              />
            ) : (
              <div className="text-slate-600 text-xs py-20">Image not available</div>
            )}
          </div>
        </div>

        {/* Right: Verified Text & Structured Summary */}
        <div className="space-y-6">
          {/* Verified Text Card */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Verified Note Transcription
              </h3>
              <button
                onClick={() => handleCopyText(note.verified_text || note.raw_ocr_text)}
                className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 bg-slate-800 px-2 py-1 rounded-lg border border-slate-700 transition"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied" : "Copy Text"}</span>
              </button>
            </div>

            <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 text-slate-100 text-xs sm:text-sm font-sans whitespace-pre-wrap leading-relaxed max-h-[280px] overflow-y-auto font-normal">
              {note.verified_text || note.raw_ocr_text || "No text available."}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
              <span>{note.verified_text ? `${note.verified_text.length} chars` : "0 chars"}</span>
              <button
                onClick={() => setShowRaw(!showRaw)}
                className="text-purple-400 hover:text-purple-300 text-[11px] underline"
              >
                {showRaw ? "Hide Raw Machine OCR" : "View Raw Machine OCR (Draft)"}
              </button>
            </div>

            {showRaw && (
              <div className="bg-slate-950 p-3 rounded-xl border border-purple-900/40 text-[11px] font-mono text-slate-400 whitespace-pre-wrap mt-2">
                <strong className="text-amber-400 block mb-1">ORIGINAL RAW OCR:</strong>
                {note.raw_ocr_text || "(Empty)"}
              </div>
            )}
          </div>

          {/* Structured Info Card */}
          <StructuredInfo data={note.structured_data || {}} />
        </div>
      </div>

      {/* Provenance & OCR Run History Tabs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ProvenancePanel note={note} ocrRuns={ocrRuns} />

        {/* OCR Run History Table */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <History className="w-4 h-4 text-purple-400" />
              OCR Processing Run History ({ocrRuns.length})
            </h3>
            <span className="text-xs text-slate-500 font-mono">Immutable</span>
          </div>

          {ocrRuns.length === 0 ? (
            <div className="text-center text-slate-500 text-xs py-8">
              No processing run history logged.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-medium">
                    <th className="pb-2">Attempt</th>
                    <th className="pb-2">Provider / Model</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Latency</th>
                    <th className="pb-2">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {ocrRuns.map((run) => (
                    <tr key={run.id} className="hover:bg-slate-850/50">
                      <td className="py-2.5 font-mono font-bold text-blue-400">#{run.attempt}</td>
                      <td className="py-2.5">
                        <span className="font-semibold text-slate-200 capitalize">{run.provider}</span>
                        <div className="text-[10px] font-mono text-slate-500">{run.model}</div>
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            run.status === "COMPLETED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40"
                              : "bg-rose-950 text-rose-400 border border-rose-800/40"
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="py-2.5 font-mono text-amber-300">{run.processing_time_ms}ms</td>
                      <td className="py-2.5 text-slate-500 text-[11px]">
                        {new Date(run.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
