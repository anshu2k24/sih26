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
  Database
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
        return { bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.4)", text: "#34D399", shadow: "0 0 10px rgba(16, 185, 129, 0.15)" };
      case "OCR_REQUIRED":
      case "PENDING":
        return { bg: "rgba(245, 158, 11, 0.15)", border: "rgba(245, 158, 11, 0.4)", text: "#FBBF24", shadow: "0 0 10px rgba(245, 158, 11, 0.15)" };
      case "OCR_UNAVAILABLE":
        return { bg: "rgba(225, 29, 72, 0.15)", border: "rgba(225, 29, 72, 0.4)", text: "#FB7185", shadow: "0 0 10px rgba(225, 29, 72, 0.15)" };
      default:
        return { bg: "rgba(100, 116, 139, 0.15)", border: "rgba(100, 116, 139, 0.4)", text: "#94A3B8", shadow: "none" };
    }
  };

  const getVerificationStatusBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return { bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.4)", text: "#34D399", shadow: "0 0 10px rgba(16, 185, 129, 0.15)" };
      case "REVIEW_REQUIRED":
      case "PENDING":
        return { bg: "rgba(245, 158, 11, 0.15)", border: "rgba(245, 158, 11, 0.4)", text: "#FBBF24", shadow: "0 0 10px rgba(245, 158, 11, 0.15)" };
      case "REJECTED":
        return { bg: "rgba(225, 29, 72, 0.15)", border: "rgba(225, 29, 72, 0.4)", text: "#FB7185", shadow: "0 0 10px rgba(225, 29, 72, 0.15)" };
      default:
        return { bg: "rgba(100, 116, 139, 0.15)", border: "rgba(100, 116, 139, 0.4)", text: "#94A3B8", shadow: "none" };
    }
  };

  // Shared Glass Styles
  const glassPanelStyle = {
    background: "linear-gradient(135deg, rgba(255,255,255,0.035), rgba(255,122,0,0.018) 40%, rgba(11, 13, 14, 0.75))",
    backdropFilter: "blur(18px) saturate(120%)",
    WebkitBackdropFilter: "blur(18px) saturate(120%)",
    border: "1px solid rgba(255, 122, 0, 0.20)",
    borderRadius: "14px",
    boxShadow: "0 10px 40px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255,255,255,0.02)",
  };

  const uploadAreaStyle = {
    background: "rgba(15, 18, 20, 0.65)",
    backdropFilter: "blur(12px)",
    border: "2px dashed rgba(255, 122, 0, 0.4)",
    borderRadius: "12px",
    transition: "all 200ms ease",
  };

  return (
    <div 
      className="min-h-screen text-[#F2F2F2] pb-24 relative overflow-hidden"
      style={{ backgroundColor: "#050505", fontFamily: "'Space Grotesk', 'Inter', sans-serif" }}
    >
      {/* Ambient glows to give the glass something to refract */}
      <div className="absolute top-0 right-0 w-[50%] h-[50%] rounded-full opacity-[0.06] blur-[150px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>
      <div className="absolute bottom-[20%] left-[-10%] w-[40%] h-[40%] rounded-full opacity-[0.04] blur-[180px] pointer-events-none" style={{ background: "radial-gradient(circle, #FF7A00 0%, transparent 70%)" }}></div>

      <div className="relative z-10 max-w-[1500px] mx-auto px-[24px] pt-[24px] space-y-[24px]">
        
        {/* Header Banner */}
        <div className="p-[20px] flex flex-col md:flex-row md:items-center justify-between gap-4" style={glassPanelStyle}>
          <div>
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-[#FF7A00]" />
              <h1 className="text-[18px] font-[700] text-white uppercase tracking-wider">
                DOCUMENT INGESTION & KNOWLEDGE EXTRACTION CONSOLE
              </h1>
              <span 
                className="text-[10px] px-[8px] py-[4px] rounded-[6px] font-[600] uppercase tracking-wider"
                style={{ background: "rgba(255,122,0,0.1)", border: "1px solid rgba(255,122,0,0.3)", color: "#FF8A00" }}
              >
                SHA-256 DEDUPLICATED
              </span>
            </div>
            <p className="text-[13px] text-[#9A9A9A] mt-1 font-['Inter',sans-serif]">
              Ingest drilling daily reports (DDR), logs, and incident reports (PDF, TXT, CSV, DOCX).
              Automated text extraction, NLP event episode parsing, and human-in-the-loop verification pipeline.
            </p>
          </div>

          <button
            onClick={loadDocuments}
            className="text-white text-[12px] font-[700] px-[16px] py-[8px] rounded-[8px] transition-all flex items-center gap-2 group tracking-wide"
            style={{
              background: "rgba(10, 11, 13, 0.8)",
              border: "1px solid rgba(255, 122, 0, 0.4)",
              transition: "all 180ms ease"
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#FF7A00";
              e.currentTarget.style.boxShadow = "0 0 15px rgba(255,122,0,0.2)";
              e.currentTarget.style.transform = "translateY(-1px) scale(1.01)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.4)";
              e.currentTarget.style.boxShadow = "none";
              e.currentTarget.style.transform = "none";
            }}
          >
            <RefreshCw className={`w-4 h-4 text-[#FF7A00] group-hover:brightness-125 ${loading ? "animate-spin" : ""}`} /> REFRESH
          </button>
        </div>

        {/* File Upload Zone */}
        <div className="p-[24px] space-y-[20px]" style={glassPanelStyle}>
          <div className="flex items-center justify-between border-b pb-[12px]" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
            <h2 className="text-[14px] font-[700] text-white uppercase tracking-wider flex items-center gap-2">
              <UploadCloud className="w-4 h-4 text-[#FF7A00]" /> Upload Drilling Report / Event Log
            </h2>
            <span className="text-[12px] text-[#9A9A9A] font-['Inter',sans-serif]">
              Associated Well: <strong className="text-[#FF7A00] font-mono">{selectedWell}</strong>
            </span>
          </div>

          <div 
            className="relative p-[40px] text-center group cursor-pointer"
            style={uploadAreaStyle}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#FF7A00";
              e.currentTarget.style.boxShadow = "0 0 30px rgba(255,122,0,0.1)";
              e.currentTarget.style.background = "rgba(20, 24, 28, 0.7)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.4)";
              e.currentTarget.style.boxShadow = "none";
              e.currentTarget.style.background = "rgba(15, 18, 20, 0.65)";
            }}
          >
            <input
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.txt,.csv,.docx,.log"
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed z-10"
            />

            <div className="flex flex-col items-center gap-4 relative z-0">
              <div 
                className="p-[16px] rounded-full transition-all group-hover:scale-110"
                style={{ background: "rgba(255,122,0,0.1)", border: "1px solid rgba(255,122,0,0.3)" }}
              >
                <UploadCloud className={`w-10 h-10 text-[#FF7A00] group-hover:brightness-125 ${uploading ? "animate-bounce" : ""}`} />
              </div>
              <div>
                <p className="text-[16px] font-[700] text-white tracking-wide transition-colors group-hover:text-[#FF7A00]">
                  {uploading ? "UPLOADING & PARSING DOCUMENT..." : "Drop file here or click to browse"}
                </p>
                <p className="text-[13px] text-[#9A9A9A] mt-2 font-['Inter',sans-serif]">
                  Supports PDF, TXT, CSV, DOCX files (Max 50MB). Automated SHA-256 checksum deduplication.
                </p>
              </div>
            </div>
          </div>

          {uploadMsg && (
            <div
              className="p-[14px] rounded-[10px] text-[13px] flex items-center gap-2 font-[500] tracking-wide"
              style={{
                background: uploadMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : uploadMsg.type === "duplicate" ? "rgba(245, 158, 11, 0.15)" : "rgba(225, 29, 72, 0.15)",
                border: `1px solid ${uploadMsg.type === "success" ? "rgba(16, 185, 129, 0.3)" : uploadMsg.type === "duplicate" ? "rgba(245, 158, 11, 0.3)" : "rgba(225, 29, 72, 0.3)"}`,
                color: uploadMsg.type === "success" ? "#34D399" : uploadMsg.type === "duplicate" ? "#FBBF24" : "#FB7185",
                boxShadow: `0 0 15px ${uploadMsg.type === "success" ? "rgba(16, 185, 129, 0.1)" : uploadMsg.type === "duplicate" ? "rgba(245, 158, 11, 0.1)" : "rgba(225, 29, 72, 0.1)"}`
              }}
            >
              {uploadMsg.type === "success" && <CheckCircle2 className="w-5 h-5 flex-shrink-0" />}
              {uploadMsg.type === "duplicate" && <AlertTriangle className="w-5 h-5 flex-shrink-0" />}
              {uploadMsg.type === "error" && <XCircle className="w-5 h-5 flex-shrink-0" />}
              <span>{uploadMsg.text}</span>
            </div>
          )}
        </div>

        {/* Uploaded Documents List */}
        <div style={glassPanelStyle} className="overflow-hidden">
          <div className="p-[20px] flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <span className="text-[13px] font-[700] text-white flex items-center gap-2 tracking-wider">
              <Database className="w-4 h-4 text-[#FF7A00]" /> UPLOADED DOCUMENTS REPOSITORY ({documents.length} records)
            </span>
            <span className="text-[11px] text-[#9A9A9A] font-['Inter',sans-serif] flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#FF7A00]" /> Deduplication: <strong className="text-[#FF7A00]">SHA-256 Active</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-[12px] border-collapse font-['Inter',sans-serif]">
              <thead>
                <tr className="text-[#9A9A9A] font-[600] uppercase tracking-wider text-[11px]" style={{ background: "rgba(0,0,0,0.3)" }}>
                  <th className="p-[16px]">DOCUMENT ID</th>
                  <th className="p-[16px]">FILENAME</th>
                  <th className="p-[16px]">TYPE</th>
                  <th className="p-[16px]">EXTRACTION STATUS</th>
                  <th className="p-[16px]">VERIFICATION STATUS</th>
                  <th className="p-[16px]">CHECKSUM (SHA-256)</th>
                  <th className="p-[16px] text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: "rgba(255,255,255,0.03)" }}>
                {documents.length === 0 && !loading && (
                  <tr>
                    <td colSpan={7} className="p-[40px] text-center text-[#686868] text-[13px]">
                      No documents uploaded yet. Use the upload zone above to ingest drilling reports.
                    </td>
                  </tr>
                )}
                {documents.map((doc) => {
                  const extStatus = getExtractionStatusBadge(doc.extraction_status);
                  const verStatus = getVerificationStatusBadge(doc.verification_status);
                  
                  return (
                  <tr 
                    key={doc.id} 
                    className="transition-all"
                    style={{ background: "rgba(10,12,14,0.4)" }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(25, 25, 25, 0.6)";
                      e.currentTarget.style.boxShadow = "inset 0 0 10px rgba(255,122,0,0.05)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "rgba(10,12,14,0.4)";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  >
                    <td className="p-[16px] font-mono font-[500] text-[#FF7A00] opacity-90">{doc.id}</td>
                    <td className="p-[16px] text-white font-[500]">{doc.filename}</td>
                    <td className="p-[16px]">
                      <span className="px-[8px] py-[2px] rounded-[4px] font-[600] text-[10px]" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#9A9A9A" }}>
                        {doc.document_type}
                      </span>
                    </td>
                    <td className="p-[16px]">
                      <span 
                        className="px-[8px] py-[4px] rounded-[6px] text-[10px] font-[700] flex items-center gap-1.5 w-max tracking-wide"
                        style={{ background: extStatus.bg, border: `1px solid ${extStatus.border}`, color: extStatus.text, boxShadow: extStatus.shadow }}
                      >
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: extStatus.text }}></span> {doc.extraction_status}
                      </span>
                    </td>
                    <td className="p-[16px]">
                      <span 
                        className="px-[8px] py-[4px] rounded-[6px] text-[10px] font-[700] flex items-center gap-1.5 w-max tracking-wide"
                        style={{ background: verStatus.bg, border: `1px solid ${verStatus.border}`, color: verStatus.text, boxShadow: verStatus.shadow }}
                      >
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: verStatus.text }}></span> {doc.verification_status}
                      </span>
                    </td>
                    <td className="p-[16px] font-mono text-[#686868] text-[11px]">
                      {doc.checksum ? `${doc.checksum.slice(0, 16)}...` : "N/A"}
                    </td>
                    <td className="p-[16px] text-right">
                      <button
                        onClick={() => openDocDetails(doc.id)}
                        className="text-white text-[11px] font-[600] px-[12px] py-[6px] rounded-[6px] transition-all inline-flex items-center gap-1.5 group"
                        style={{
                          background: "rgba(10, 10, 10, 0.8)",
                          border: "1px solid rgba(255, 122, 0, 0.4)",
                          transition: "all 180ms ease"
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "#FF8A00";
                          e.currentTarget.style.boxShadow = "0 0 20px rgba(255,122,0,0.3)";
                          e.currentTarget.style.background = "rgba(255,122,0,0.08)";
                          e.currentTarget.style.transform = "translateY(-1px) scale(1.02)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255, 122, 0, 0.4)";
                          e.currentTarget.style.boxShadow = "none";
                          e.currentTarget.style.background = "rgba(10, 10, 10, 0.8)";
                          e.currentTarget.style.transform = "none";
                        }}
                      >
                        <Eye className="w-3.5 h-3.5 text-[#FF7A00] group-hover:brightness-125" /> INSPECT & VERIFY
                      </button>
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        </div>

        {/* Document Detail & Extracted Events Verification Modal */}
        {selectedDocModal && (
          <div className="fixed inset-0 z-50 bg-[#050505]/80 flex items-center justify-center p-4" style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
            <div 
              className="rounded-[16px] max-w-4xl w-full p-[24px] space-y-[24px] relative max-h-[90vh] overflow-y-auto"
              style={{
                background: "rgba(12, 14, 16, 0.85)",
                border: "1px solid rgba(255, 122, 0, 0.25)",
                boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)"
              }}
            >
              <button
                onClick={() => setSelectedDocModal(null)}
                className="absolute top-[20px] right-[20px] text-[#9A9A9A] transition-colors"
                onMouseEnter={(e) => e.currentTarget.style.color = "#FF7A00"}
                onMouseLeave={(e) => e.currentTarget.style.color = "#9A9A9A"}
              >
                <XCircle className="w-6 h-6" />
              </button>

              {/* Modal Header */}
              <div className="border-b pb-[16px]" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                <div className="flex items-center gap-2 text-[#FF7A00] text-[11px] font-[700] mb-1 uppercase tracking-widest">
                  <FileCode className="w-4 h-4" /> PROVENANCE RECORD: {selectedDocModal.id}
                </div>
                <h2 className="text-[18px] font-[700] text-white uppercase tracking-wider font-mono">
                  {selectedDocModal.filename}
                </h2>
                <p className="text-[12px] text-[#686868] mt-1 font-['Inter',sans-serif]">
                  SHA-256: <span className="font-mono text-[#9A9A9A]">{selectedDocModal.checksum}</span>
                </p>
              </div>

              {/* Provenance Flow Chain */}
              <div className="p-[20px] rounded-[12px]" style={{ background: "rgba(5,6,7,0.6)", border: "1px solid rgba(255,255,255,0.05)" }}>
                <span className="text-[11px] font-[700] text-[#9A9A9A] uppercase tracking-widest flex items-center gap-2 mb-3">
                  <Layers className="w-4 h-4 text-[#FF7A00]" /> Provenance Verification Chain
                </span>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-[11px] font-['Inter',sans-serif]">
                  <div className="p-[12px] rounded-[8px]" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[#686868] block text-[9px] uppercase tracking-wider mb-1">STEP 1: UPLOAD</span>
                    <strong className="text-[#E2E2E2] block text-[12px]">SHA-256 Checksum</strong>
                    <span className="text-[#34D399] font-[600] text-[11px]">Verified Unique</span>
                  </div>
                  <div className="p-[12px] rounded-[8px]" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[#686868] block text-[9px] uppercase tracking-wider mb-1">STEP 2: EXTRACTION</span>
                    <strong className="text-[#E2E2E2] block text-[12px]">NLP / OCR Parse</strong>
                    <span className={`font-[600] text-[11px] ${selectedDocModal.extraction_status === 'EXTRACTED' ? 'text-[#34D399]' : 'text-[#FBBF24]'}`}>
                      {selectedDocModal.extraction_status}
                    </span>
                  </div>
                  <div className="p-[12px] rounded-[8px]" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[#686868] block text-[9px] uppercase tracking-wider mb-1">STEP 3: NLP EVENT EPISODES</span>
                    <strong className="text-[#E2E2E2] block text-[12px]">Parsed Episodes</strong>
                    <span className="text-[#FF7A00] font-[600] text-[11px]">{docEvents.length} Extracted</span>
                  </div>
                  <div className="p-[12px] rounded-[8px]" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[#686868] block text-[9px] uppercase tracking-wider mb-1">STEP 4: HUMAN VERIFICATION</span>
                    <strong className="text-[#E2E2E2] block text-[12px]">Engineer Promotion</strong>
                    <span className="text-[#A78BFA] font-[600] text-[11px]">Historical DDR Base</span>
                  </div>
                </div>
              </div>

              {/* Extracted Events Table */}
              <div className="space-y-[16px]">
                <div className="flex items-center justify-between">
                  <h3 className="text-[13px] font-[700] text-[#F2F2F2] uppercase tracking-wider flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#FBBF24]" /> Extracted Event Episodes ({docEvents.length})
                  </h3>
                  <span className="text-[10px] text-[#FBBF24] font-['Inter',sans-serif]">
                    * Confidence score is an AI extraction metric, NOT ground truth until verified.
                  </span>
                </div>

                {docLoading && <p className="text-[13px] text-[#9A9A9A] italic">Loading extracted events...</p>}

                {!docLoading && docEvents.length === 0 && (
                  <div className="p-[30px] rounded-[12px] text-center text-[13px] text-[#686868]" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    No operational event episodes extracted from this document text.
                  </div>
                )}

                {docEvents.map((ev) => {
                  const evStatus = getVerificationStatusBadge(ev.verification_status);
                  return (
                  <div key={ev.id} className="p-[20px] rounded-[12px] space-y-[16px]" style={{ background: "rgba(5,6,7,0.5)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-[12px]" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                      <div className="flex items-center gap-3">
                        <span className="text-white font-[700] text-[14px] uppercase tracking-wide">{ev.event_type}</span>
                        <span className="text-[#9A9A9A] text-[12px] font-mono">({ev.well_id})</span>
                        <span className="text-[10px] px-[8px] py-[2px] rounded-[4px] font-[700] tracking-wide" style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34D399" }}>
                          MD: {ev.onset_md} m
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-[12px]">
                        <span className="text-[#9A9A9A] font-['Inter',sans-serif]">
                          AI Confidence: <strong className="text-[#FBBF24] font-mono">{(ev.confidence * 100).toFixed(0)}%</strong>
                        </span>
                        <span 
                          className="px-[8px] py-[4px] rounded-[6px] text-[10px] font-[700] flex items-center gap-1.5 w-max tracking-wide"
                          style={{ background: evStatus.bg, border: `1px solid ${evStatus.border}`, color: evStatus.text, boxShadow: evStatus.shadow }}
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: evStatus.text }}></span> {ev.verification_status}
                        </span>
                      </div>
                    </div>

                    <div className="text-[13px] text-[#D4D4D4] font-['Inter',sans-serif] p-[16px] rounded-[8px]" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                      <strong className="text-[#FF7A00] font-mono block text-[10px] uppercase mb-2 tracking-widest">Evidence Snippet:</strong>
                      {ev.evidence_text}
                    </div>

                    <div className="flex items-center justify-between gap-4 pt-2">
                      <span className="text-[11px] text-[#9A9A9A] font-mono"><span className="text-[#686868]">Mitigation:</span> {ev.mitigation_text}</span>

                      {ev.verification_status !== "VERIFIED" && ev.verification_status !== "REJECTED" && (
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleRejectEvent(selectedDocModal.id, ev.id)}
                            className="text-[#FB7185] text-[11px] font-[700] px-[12px] py-[6px] rounded-[6px] transition-all flex items-center gap-1.5 uppercase tracking-wide"
                            style={{ background: "rgba(225, 29, 72, 0.1)", border: "1px solid rgba(225, 29, 72, 0.3)", transition: "all 180ms ease" }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(225, 29, 72, 0.2)"; e.currentTarget.style.boxShadow = "0 0 15px rgba(225, 29, 72, 0.2)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(225, 29, 72, 0.1)"; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
                          >
                            <XCircle className="w-3.5 h-3.5" /> REJECT
                          </button>
                          <button
                            onClick={() => handleVerifyEvent(selectedDocModal.id, ev.id)}
                            className="text-[#34D399] text-[11px] font-[700] px-[12px] py-[6px] rounded-[6px] transition-all flex items-center gap-1.5 uppercase tracking-wide"
                            style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", transition: "all 180ms ease" }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(16, 185, 129, 0.2)"; e.currentTarget.style.boxShadow = "0 0 15px rgba(16, 185, 129, 0.2)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(16, 185, 129, 0.1)"; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
                          >
                            <ShieldCheck className="w-3.5 h-3.5" /> VERIFY & PROMOTE
                          </button>
                        </div>
                      )}

                      {ev.verification_status === "VERIFIED" && (
                        <span className="text-[11px] text-[#34D399] font-[700] flex items-center gap-1.5 tracking-wide">
                          <CheckCircle2 className="w-4 h-4" /> Promoted to Historical Knowledge Base
                        </span>
                      )}
                    </div>
                  </div>
                )})}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
