import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { HandwrittenNote, OCRRun } from "../types/notes";
import {
  fetchNoteDetailApi,
  saveDraftNoteApi,
  verifyNoteApi,
  retryNoteOcrApi,
} from "../services/notesApi";
import { NoteEditor } from "../components/notes/NoteEditor";
import { StructuredInfo } from "../components/notes/StructuredInfo";
import { ProvenancePanel } from "../components/notes/ProvenancePanel";
import { NoteStatusBadge } from "../components/notes/NoteStatusBadge";

export const NoteReviewPage: React.FC = () => {
  const { noteId } = useParams<{ noteId: string }>();
  const navigate = useNavigate();

  const [note, setNote] = useState<HandwrittenNote | null>(null);
  const [ocrRuns, setOcrRuns] = useState<OCRRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [retrying, setRetrying] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"structured" | "provenance">("structured");
  const [statusBanner, setStatusBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

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

  const handleSaveDraft = async (text: string, title: string) => {
    if (!noteId) return;
    setSaving(true);
    setStatusBanner(null);
    const updated = await saveDraftNoteApi(noteId, text, title);
    setSaving(false);
    if (updated) {
      setNote(updated);
      setStatusBanner({ type: "success", message: "Draft edits saved successfully." });
      setTimeout(() => setStatusBanner(null), 3000);
    } else {
      setStatusBanner({ type: "error", message: "Failed to save draft." });
    }
  };

  const handleVerify = async (text: string, title: string) => {
    if (!noteId) return;
    setVerifying(true);
    setStatusBanner(null);
    const updated = await verifyNoteApi(noteId, text, title);
    setVerifying(false);
    if (updated) {
      setNote(updated);
      setStatusBanner({ type: "success", message: "Note verified and promoted to trusted status!" });
      setTimeout(() => {
        navigate(`/notes/${noteId}`);
      }, 1200);
    } else {
      setStatusBanner({ type: "error", message: "Verification failed." });
    }
  };

  const handleRetry = async () => {
    if (!noteId) return;
    setRetrying(true);
    setStatusBanner(null);
    const res = await retryNoteOcrApi(noteId);
    setRetrying(false);
    if (res.success && res.note) {
      setNote(res.note);
      loadNote();
      setStatusBanner({ type: "success", message: "OCR retry completed with new run recorded." });
    } else {
      setStatusBanner({ type: "error", message: res.error || "Retry failed." });
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto" />
        <p className="text-xs text-slate-400">Loading note review studio...</p>
      </div>
    );
  }

  if (!note) {
    return (
      <div className="p-8 text-center bg-slate-900/60 rounded-3xl border border-slate-800 space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-base font-bold text-slate-100">Handwritten Note Not Found</h3>
        <Link
          to="/notes"
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded-xl"
        >
          Return to Notes
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-16">
      {/* Navigation bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <Link
            to="/notes"
            className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl text-slate-300 transition"
            title="Back to notes list"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-500">ID: {note.id.slice(0, 8)}</span>
              <NoteStatusBadge
                verificationStatus={note.verification_status}
                ocrStatus={note.ocr_status}
                size="sm"
              />
            </div>
            <h1 className="text-lg font-bold text-slate-100 truncate max-w-xl">
              {note.title}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/notes/${note.id}`}
            className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
          >
            View Detail & Runs
          </Link>
        </div>
      </div>

      {statusBanner && (
        <div
          className={`flex items-center gap-2 p-3.5 rounded-xl border text-xs font-medium ${
            statusBanner.type === "success"
              ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
              : "bg-rose-950/40 border-rose-800 text-rose-300"
          }`}
        >
          {statusBanner.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          )}
          <span>{statusBanner.message}</span>
        </div>
      )}

      {/* Main Side-by-Side Editor Studio */}
      <NoteEditor
        note={note}
        onSaveDraft={handleSaveDraft}
        onVerify={handleVerify}
        onRetry={handleRetry}
        saving={saving}
        verifying={verifying}
        retrying={retrying}
      />

      {/* Bottom Collapsible Insights & Provenance Tabs */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="flex border-b border-slate-800 bg-slate-950/60">
          <button
            onClick={() => setActiveTab("structured")}
            className={`px-5 py-3 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
              activeTab === "structured"
                ? "border-blue-500 text-blue-400 bg-slate-900/80"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Structured Entities & Measurements
          </button>
          <button
            onClick={() => setActiveTab("provenance")}
            className={`px-5 py-3 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
              activeTab === "provenance"
                ? "border-emerald-500 text-emerald-400 bg-slate-900/80"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Provenance & Run History ({ocrRuns.length})
          </button>
        </div>

        <div className="p-5">
          {activeTab === "structured" ? (
            <StructuredInfo data={note.structured_data || {}} />
          ) : (
            <ProvenancePanel note={note} ocrRuns={ocrRuns} />
          )}
        </div>
      </div>
    </div>
  );
};
