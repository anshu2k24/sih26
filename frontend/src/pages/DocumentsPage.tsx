import React, { useState, useEffect } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import {
  uploadDocumentApi,
  fetchDocumentsApi,
  fetchDocumentDetailsApi,
  verifyExtractedEventApi,
  rejectExtractedEventApi,
} from "../services/api";
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  Eye,
  FileCode,
  Layers,
  Sparkles,
} from "lucide-react";

export const DocumentsPage: React.FC = () => {
  const { selectedWell } = useActiveWell();
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "success" | "error" | "duplicate"; text: string } | null>(null);

  // Selected document detail view
  const [selectedDocModal, setSelectedDocModal] = useState<any | null>(null);
  const [docEvents, setDocEvents] = useState<any[]>([]);
  const [docLoading, setDocLoading] = useState<boolean>(false);

  const loadDocuments = async () => {
    setLoading(true);
    const data = await fetchDocumentsApi();
    if (data && data.documents) {
      setDocuments(data.documents);
    }
    setLoading(false);
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg(null);

    const res = await uploadDocumentApi(file, selectedWell);
    setUploading(false);

    if (!res) {
      setUploadMsg({ type: "error", text: "Upload failed. Check backend connection." });
      return;
    }

    if (res.status === "DUPLICATE") {
      setUploadMsg({
        type: "duplicate",
        text: `Duplicate file detected via SHA-256 checksum (${res.document?.checksum?.slice(0, 12)}...).`,
      });
    } else {
      setUploadMsg({
        type: "success",
        text: `Document '${file.name}' uploaded and parsed successfully (${res.extracted_events_count || 0} events extracted).`,
      });
    }

    loadDocuments();
    if (res.document) {
      openDocDetails(res.document.id);
    }
  };

  const openDocDetails = async (docId: string) => {
    setDocLoading(true);
    const data = await fetchDocumentDetailsApi(docId);
    setDocLoading(false);
    if (data && data.document) {
      setSelectedDocModal(data.document);
      setDocEvents(data.extracted_events || []);
    }
  };

  const handleVerifyEvent = async (docId: string, eventId: string) => {
    const res = await verifyExtractedEventApi(docId, eventId);
    if (res) {
      setDocEvents((prev) =>
        prev.map((e) => (e.id === eventId ? { ...e, verification_status: "VERIFIED" } : e))
      );
      loadDocuments();
    }
  };

  const handleRejectEvent = async (docId: string, eventId: string) => {
    const res = await rejectExtractedEventApi(docId, eventId);
    if (res) {
      setDocEvents((prev) =>
        prev.map((e) => (e.id === eventId ? { ...e, verification_status: "REJECTED" } : e))
      );
      loadDocuments();
    }
  };

  const getExtractionStatusBadge = (status: string) => {
    switch (status) {
      case "EXTRACTED":
        return "bg-emerald-950 text-emerald-400 border-emerald-500/30";
      case "OCR_REQUIRED":
        return "bg-amber-950 text-amber-400 border-amber-500/30";
      case "OCR_UNAVAILABLE":
        return "bg-rose-950 text-rose-400 border-rose-500/30";
      default:
        return "bg-slate-950 text-slate-400 border-slate-700";
    }
  };

  const getVerificationStatusBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return "bg-emerald-950 text-emerald-400 border-emerald-500/30";
      case "REVIEW_REQUIRED":
        return "bg-amber-950 text-amber-400 border-amber-500/30";
      case "REJECTED":
        return "bg-rose-950 text-rose-400 border-rose-500/30";
      default:
        return "bg-slate-950 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              DOCUMENT INGESTION & KNOWLEDGE EXTRACTION CONSOLE
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-500/30 font-bold">
              SHA-256 DEDUPLICATED
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Ingest drilling daily reports (DDR), logs, and incident reports (PDF, TXT, CSV, DOCX).
            Automated text extraction, NLP event episode parsing, and human-in-the-loop verification pipeline.
          </p>
        </div>

        <button
          onClick={loadDocuments}
          className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold px-3 py-1.5 rounded-lg border border-slate-700 transition-all flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> REFRESH
        </button>
      </div>

      {/* File Upload Zone */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-cyan-400" /> Upload Drilling Report / Event Log
          </h2>
          <span className="text-xs text-slate-400">Associated Well: <strong className="text-white">{selectedWell}</strong></span>
        </div>

        <div className="relative border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-8 text-center transition-all bg-slate-950/50">
          <input
            type="file"
            onChange={handleFileUpload}
            accept=".pdf,.txt,.csv,.docx,.log"
            disabled={uploading}
            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed"
          />

          <div className="flex flex-col items-center gap-2">
            <div className="p-3 bg-cyan-950/60 rounded-full border border-cyan-500/30 text-cyan-400">
              <UploadCloud className={`w-8 h-8 ${uploading ? "animate-bounce" : ""}`} />
            </div>
            <div>
              <p className="text-sm font-bold text-white">
                {uploading ? "UPLOADING & PARSING DOCUMENT..." : "Drop file here or click to browse"}
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Supports PDF, TXT, CSV, DOCX files (Max 50MB). Automated SHA-256 checksum deduplication.
              </p>
            </div>
          </div>
        </div>

        {uploadMsg && (
          <div
            className={`p-3.5 rounded-lg border text-xs flex items-center gap-2 ${
              uploadMsg.type === "success"
                ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/30"
                : uploadMsg.type === "duplicate"
                ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                : "bg-rose-950/60 text-rose-300 border-rose-500/30"
            }`}
          >
            {uploadMsg.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
            {uploadMsg.type === "duplicate" && <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />}
            {uploadMsg.type === "error" && <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />}
            <span>{uploadMsg.text}</span>
          </div>
        )}
      </div>

      {/* Uploaded Documents List */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-slate-300">
          <span>Uploaded Documents Repository ({documents.length} records)</span>
          <span className="text-slate-500">Deduplication: SHA-256 Active</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold">
                <th className="p-3.5">DOCUMENT ID</th>
                <th className="p-3.5">FILENAME</th>
                <th className="p-3.5">TYPE</th>
                <th className="p-3.5">EXTRACTION STATUS</th>
                <th className="p-3.5">VERIFICATION STATUS</th>
                <th className="p-3.5">CHECKSUM (SHA-256)</th>
                <th className="p-3.5 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {documents.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500">
                    No documents uploaded yet. Use the upload zone above to ingest drilling reports.
                  </td>
                </tr>
              )}
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-850/60 transition-all">
                  <td className="p-3.5 font-bold text-cyan-400">{doc.id}</td>
                  <td className="p-3.5 text-white font-bold">{doc.filename}</td>
                  <td className="p-3.5">
                    <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 font-bold text-[10px]">
                      {doc.document_type}
                    </span>
                  </td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getExtractionStatusBadge(doc.extraction_status)}`}>
                      {doc.extraction_status}
                    </span>
                  </td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getVerificationStatusBadge(doc.verification_status)}`}>
                      {doc.verification_status}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-slate-400 text-[10px]">
                    {doc.checksum ? `${doc.checksum.slice(0, 16)}...` : "N/A"}
                  </td>
                  <td className="p-3.5 text-right">
                    <button
                      onClick={() => openDocDetails(doc.id)}
                      className="bg-slate-800 hover:bg-slate-700 text-cyan-300 text-xs px-2.5 py-1 rounded border border-slate-700 font-bold transition-all inline-flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5" /> INSPECT & VERIFY
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Detail & Extracted Events Verification Modal */}
      {selectedDocModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full p-6 space-y-5 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedDocModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <XCircle className="w-5 h-5" />
            </button>

            {/* Modal Header */}
            <div className="border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold mb-1">
                <FileCode className="w-4 h-4" /> PROVENANCE RECORD: {selectedDocModal.id}
              </div>
              <h2 className="text-base font-bold text-white uppercase tracking-wider">
                {selectedDocModal.filename}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                SHA-256: <span className="font-mono text-slate-300">{selectedDocModal.checksum}</span>
              </p>
            </div>

            {/* Provenance Flow Chain */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" /> Provenance Verification Chain
              </span>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-[11px]">
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">STEP 1: UPLOAD</span>
                  <strong className="text-white block">SHA-256 Checksum</strong>
                  <span className="text-emerald-400 text-[10px]">Verified Unique</span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">STEP 2: EXTRACTION</span>
                  <strong className="text-white block">NLP / OCR Parse</strong>
                  <span className={`text-[10px] font-bold ${selectedDocModal.extraction_status === 'EXTRACTED' ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {selectedDocModal.extraction_status}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">STEP 3: NLP EVENT EPISODES</span>
                  <strong className="text-white block">Parsed Episodes</strong>
                  <span className="text-cyan-400 font-bold">{docEvents.length} Extracted</span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                  <span className="text-slate-500 block text-[9px]">STEP 4: HUMAN VERIFICATION</span>
                  <strong className="text-white block">Engineer Promotion</strong>
                  <span className="text-indigo-400 font-bold">Historical DDR Base</span>
                </div>
              </div>
            </div>

            {/* Extracted Events Table */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Extracted Event Episodes ({docEvents.length})
                </h3>
                <span className="text-[11px] text-amber-400/90 font-sans">
                  * Confidence score is an AI extraction metric, NOT ground truth until verified.
                </span>
              </div>

              {docLoading && <p className="text-xs text-slate-400 italic">Loading extracted events...</p>}

              {!docLoading && docEvents.length === 0 && (
                <div className="bg-slate-950 border border-slate-850 rounded-lg p-6 text-center text-xs text-slate-500">
                  No operational event episodes extracted from this document text.
                </div>
              )}

              {docEvents.map((ev) => (
                <div key={ev.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-850 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-bold text-xs">{ev.event_type}</span>
                      <span className="text-slate-400 text-xs">({ev.well_id})</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400 font-bold">
                        MD: {ev.onset_md} m
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400 text-[11px]">
                        AI Confidence: <strong className="text-amber-400 font-mono">{(ev.confidence * 100).toFixed(0)}%</strong>
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getVerificationStatusBadge(ev.verification_status)}`}>
                        {ev.verification_status}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-300 font-sans bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                    <strong className="text-cyan-400 font-mono block text-[10px] uppercase mb-1">Evidence Snippet:</strong>
                    {ev.evidence_text}
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-1">
                    <span className="text-[10px] text-slate-500 font-mono">Mitigation: {ev.mitigation_text}</span>

                    {ev.verification_status !== "VERIFIED" && ev.verification_status !== "REJECTED" && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleRejectEvent(selectedDocModal.id, ev.id)}
                          className="bg-rose-950 hover:bg-rose-900 text-rose-300 text-xs px-2.5 py-1 rounded border border-rose-500/40 font-bold transition-all flex items-center gap-1"
                        >
                          <XCircle className="w-3.5 h-3.5" /> REJECT
                        </button>
                        <button
                          onClick={() => handleVerifyEvent(selectedDocModal.id, ev.id)}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3 py-1 rounded font-bold transition-all flex items-center gap-1 shadow-md shadow-emerald-500/20"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" /> VERIFY & PROMOTE
                        </button>
                      </div>
                    )}

                    {ev.verification_status === "VERIFIED" && (
                      <span className="text-xs text-emerald-400 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Promoted to Historical Knowledge Base
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setSelectedDocModal(null)}
                className="bg-slate-800 text-slate-300 px-4 py-1.5 rounded-lg font-bold text-xs"
              >
                CLOSE WINDOW
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
