import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  UploadCloud,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Layers,
} from "lucide-react";
import type { HandwrittenNote, OCRMetrics } from "../types/notes";
import { fetchNotesApi, fetchNotesMetricsApi, deleteNoteApi } from "../services/notesApi";
import { NoteCard } from "../components/notes/NoteCard";

export const HandwrittenNotesPage: React.FC = () => {
  const [notes, setNotes] = useState<HandwrittenNote[]>([]);
  const [metrics, setMetrics] = useState<OCRMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const loadData = async () => {
    setLoading(true);
    const [notesRes, metricsRes] = await Promise.all([
      fetchNotesApi({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        q: searchQuery || undefined,
      }),
      fetchNotesMetricsApi(),
    ]);

    setNotes(notesRes.notes);
    if (metricsRes) setMetrics(metricsRes);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this handwritten note?")) {
      const ok = await deleteNoteApi(id);
      if (ok) {
        setNotes((prev) => prev.filter((n) => n.id !== id));
        loadData();
      }
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
              SIH 2026 PS121
            </span>
            <span className="text-xs text-slate-500">• Production Ingestion Pipeline</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-blue-400" />
            Handwritten Notes & Document OCR
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Convert handwritten drilling logs, shift notes, and inspection sheets into verified, structured data.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData()}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-xl transition"
            title="Refresh notes list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
          </button>
          <Link
            to="/notes/upload"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-lg shadow-blue-900/30 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Handwritten Note</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-2xl">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Total Notes</span>
              <Layers className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-extrabold text-slate-100 font-mono">
              {metrics.total_notes}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Ingested in system</div>
          </div>

          <div className="bg-amber-950/20 border border-amber-800/40 p-4 rounded-2xl">
            <div className="flex items-center justify-between text-xs text-amber-400 mb-1">
              <span>Needs Review</span>
              <Clock className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-extrabold text-amber-300 font-mono">
              {metrics.needs_review}
            </div>
            <div className="text-[11px] text-amber-400/70 mt-1">Awaiting verification</div>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-800/40 p-4 rounded-2xl">
            <div className="flex items-center justify-between text-xs text-emerald-400 mb-1">
              <span>Verified Data</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-extrabold text-emerald-300 font-mono">
              {metrics.verified}
            </div>
            <div className="text-[11px] text-emerald-400/70 mt-1">
              {metrics.verification_rate_pct}% trust rate
            </div>
          </div>

          <div className="bg-blue-950/20 border border-blue-800/40 p-4 rounded-2xl">
            <div className="flex items-center justify-between text-xs text-blue-400 mb-1">
              <span>Processing</span>
              <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            </div>
            <div className="text-2xl font-extrabold text-blue-300 font-mono">
              {metrics.processing}
            </div>
            <div className="text-[11px] text-blue-400/70 mt-1">Active OCR jobs</div>
          </div>

          <div className="bg-rose-950/20 border border-rose-800/40 p-4 rounded-2xl">
            <div className="flex items-center justify-between text-xs text-rose-400 mb-1">
              <span>OCR Failed</span>
              <AlertCircle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-extrabold text-rose-300 font-mono">
              {metrics.failed}
            </div>
            <div className="text-[11px] text-rose-400/70 mt-1">Retry available</div>
          </div>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-2xl border border-slate-800">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes by keyword, equipment ID, parameters, or tags..."
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 transition"
          />
        </form>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {["ALL", "NEEDS_REVIEW", "VERIFIED", "FAILED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                statusFilter === st
                  ? "bg-blue-600 text-white shadow-md shadow-blue-900/40"
                  : "bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800"
              }`}
            >
              {st === "ALL" ? "All Notes" : st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Notes Grid */}
      {loading ? (
        <div className="py-20 text-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400 mx-auto" />
          <p className="text-xs text-slate-400">Loading handwritten notes repository...</p>
        </div>
      ) : notes.length === 0 ? (
        <div className="bg-slate-900/30 border border-slate-800 rounded-3xl p-12 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto text-blue-400">
            <UploadCloud className="w-8 h-8" />
          </div>
          <h3 className="text-base font-bold text-slate-200">No handwritten notes found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {searchQuery
              ? `No notes matched the query "${searchQuery}". Try different keywords.`
              : "Upload a photograph or scan of field notes to start OCR extraction and verification."}
          </p>
          <Link
            to="/notes/upload"
            className="inline-flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition shadow-lg shadow-blue-900/30"
          >
            <Plus className="w-4 h-4" />
            Upload First Note
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map((note) => (
            <NoteCard key={note.id} note={note} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
};
