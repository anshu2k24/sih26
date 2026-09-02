import React, { useState, useEffect, useMemo } from "react";
import { useActiveWell } from "../context/ActiveWellContext";
import {
  uploadDocumentApi,
  fetchDocumentsApi,
  fetchDocumentDetailsApi,
  verifyExtractedEventApi,
  rejectExtractedEventApi,
  API_BASE_URL,
} from "../services/api";
import {
  fetchNotesApi,
  fetchNoteDetailApi,
  uploadNoteOcrApi,
  verifyNoteApi,
  rejectNoteApi,
  deleteNoteApi,
} from "../services/notesApi";
import {
  ragQuery,
  indexNote,
  type SourceCitation,
} from "../services/ragApi";
import type { HandwrittenNote } from "../types/notes";
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Eye,
  Sparkles,
  Search,
  Bot,
  Send,
  Plus,
  X,
  FileCode,
  ShieldCheck,
  Clock,
  Trash2,
  Layers,
  Image as ImageIcon,
  Check,
  Edit3,
} from "lucide-react";

// Unified item type representing either a Standard Digital Document or a Handwritten OCR Note
interface UnifiedDocumentItem {
  id: string;
  sourceType: "DIGITAL_DOC" | "HANDWRITTEN_OCR";
  title: string;
  filename: string;
  wellId?: string;
  fileType: string;
  verificationStatus: "VERIFIED" | "YET_TO_BE_VERIFIED" | "REJECTED";
  createdAt: string;
  checksum?: string;
  eventsCount?: number;
  confidenceLevel?: string;
  rawDoc?: any;
  rawNote?: HandwrittenNote;
}

interface ChatMessage {
  id: string;
  sender: "user" | "gemini";
  text: string;
  sources?: SourceCitation[];
  timestamp: string;
  llmUsed?: boolean;
}

export const DocumentsPage: React.FC = () => {
  const { selectedWell } = useActiveWell();

  // Data states
  const [digitalDocs, setDigitalDocs] = useState<any[]>([]);
  const [ocrNotes, setOcrNotes] = useState<HandwrittenNote[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "YET_TO_BE_VERIFIED" | "VERIFIED">("ALL");

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadTab, setUploadTab] = useState<"DIGITAL" | "OCR">("DIGITAL");
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: "success" | "error" | "duplicate"; text: string } | null>(null);

  // Note OCR Upload Form states
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [ocrTitle, setOcrTitle] = useState<string>("");
  const [ocrModel, setOcrModel] = useState<string>("mistral-ocr-latest");

  // Gemini RAG Chat Assistant drawer state
  const [showChatDrawer, setShowChatDrawer] = useState<boolean>(false);
  const [chatInput, setChatInput] = useState<string>("");
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      sender: "gemini",
      text: "Hello! I am your AI Technical Assistant powered by Google Gemini and Grounded RAG. Ask me anything about your uploaded drilling reports, logbooks, or handwritten notes.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  // Selected item modal (Inspection & Verification)
  const [activeItem, setActiveItem] = useState<UnifiedDocumentItem | null>(null);
  const [itemDetailLoading, setItemDetailLoading] = useState<boolean>(false);
  const [digitalDocDetails, setDigitalDocDetails] = useState<{ document: any; extracted_events: any[] } | null>(null);
  const [noteDetails, setNoteDetails] = useState<HandwrittenNote | null>(null);
  const [editableVerifiedText, setEditableVerifiedText] = useState<string>("");
  const [verifyingAction, setVerifyingAction] = useState<boolean>(false);

  // Load all items (Digital docs + OCR notes)
  const loadAllData = async () => {
    setLoading(true);
    try {
      const [docsRes, notesRes] = await Promise.all([
        fetchDocumentsApi(),
        fetchNotesApi(),
      ]);

      if (docsRes && docsRes.documents) {
        setDigitalDocs(docsRes.documents);
      }
      if (notesRes && notesRes.notes) {
        setOcrNotes(notesRes.notes);
      }
    } catch (err) {
      console.error("Failed to load documents data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  // Merge & normalize both sources into unified list
  const unifiedItems: UnifiedDocumentItem[] = useMemo(() => {
    const list: UnifiedDocumentItem[] = [];

    // 1. Digital Documents — AUTOMATICALLY VERIFIED
    digitalDocs.forEach((doc) => {
      list.push({
        id: doc.id,
        sourceType: "DIGITAL_DOC",
        title: doc.filename,
        filename: doc.filename,
        wellId: doc.source_metadata?.well_id || doc.well_id,
        fileType: doc.document_type || doc.doc_type || "PDF",
        verificationStatus: "VERIFIED", // Automatically VERIFIED!
        createdAt: doc.created_at || new Date().toISOString(),
        checksum: doc.checksum,
        eventsCount: doc.extracted_events_count || 0,
        rawDoc: doc,
      });
    });

    // 2. Handwritten OCR Notes — REQUIRES HUMAN VERIFICATION
    ocrNotes.forEach((note: any) => {
      const vStatus: "VERIFIED" | "YET_TO_BE_VERIFIED" | "REJECTED" =
        note.verification_status === "VERIFIED"
          ? "VERIFIED"
          : note.verification_status === "REJECTED"
          ? "REJECTED"
          : "YET_TO_BE_VERIFIED";

      const noteFilename = note.original_filename || note.title || "Handwritten Note";

      list.push({
        id: note.id,
        sourceType: "HANDWRITTEN_OCR",
        title: note.title || noteFilename,
        filename: noteFilename,
        fileType: "OCR IMAGE",
        verificationStatus: vStatus,
        createdAt: note.created_at || new Date().toISOString(),
        confidenceLevel: note.confidence_level,
        rawNote: note,
      });
    });

    // Sort by creation date descending
    return list.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [digitalDocs, ocrNotes]);

  // Filtered documents based on status tab and search query
  const filteredItems = useMemo(() => {
    return unifiedItems.filter((item) => {
      // Status filter
      if (statusFilter !== "ALL" && item.verificationStatus !== statusFilter) {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = item.title.toLowerCase().includes(q);
        const matchFilename = item.filename.toLowerCase().includes(q);
        const matchId = item.id.toLowerCase().includes(q);
        const matchWell = item.wellId?.toLowerCase().includes(q) || false;
        
        let matchMetadata = false;
        if (item.sourceType === "DIGITAL_DOC" && item.rawDoc?.source_metadata) {
          const meta = item.rawDoc.source_metadata;
          const summary = meta.summary || "";
          const tags = (meta.tags || []).join(" ");
          matchMetadata = summary.toLowerCase().includes(q) || tags.toLowerCase().includes(q);
        } else if (item.sourceType === "HANDWRITTEN_OCR" && item.rawNote?.structured_data) {
          const struct = item.rawNote.structured_data;
          const summary = struct.summary || "";
          const tags = (struct.tags || []).join(" ");
          matchMetadata = summary.toLowerCase().includes(q) || tags.toLowerCase().includes(q);
        }
        
        return matchTitle || matchFilename || matchId || matchWell || matchMetadata;
      }
      return true;
    });
  }, [unifiedItems, statusFilter, searchQuery]);

  // Handle Digital Document Upload
  const handleDigitalFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
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
        text: `Document '${file.name}' ingested and verified (${res.extracted_events_count || 0} events extracted).`,
      });
    }

    loadAllData();
  };

  // Handle Handwritten OCR Note Upload
  const handleOcrSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ocrFile) return;

    setUploading(true);
    setUploadMsg(null);

    const res = await uploadNoteOcrApi(ocrFile, ocrTitle.trim() || undefined, ocrModel);
    setUploading(false);

    if (!res) {
      setUploadMsg({ type: "error", text: "OCR processing failed. Check server logs." });
      return;
    }

    if (res.is_duplicate) {
      setUploadMsg({
        type: "duplicate",
        text: `Duplicate image detected. Note ID: ${res.note?.id}`,
      });
    } else {
      setUploadMsg({
        type: "success",
        text: `Handwritten note transcribed successfully via OCR! Ready for verification.`,
      });
      setOcrFile(null);
      setOcrTitle("");
    }

    loadAllData();
  };

  // Open item inspection & review
  const openItemDetails = async (item: UnifiedDocumentItem) => {
    setActiveItem(item);
    setItemDetailLoading(true);
    setDigitalDocDetails(null);
    setNoteDetails(null);

    try {
      if (item.sourceType === "DIGITAL_DOC") {
        const data = await fetchDocumentDetailsApi(item.id);
        if (data) {
          setDigitalDocDetails(data);
        }
      } else {
        const data = await fetchNoteDetailApi(item.id);
        if (data && data.note) {
          setNoteDetails(data.note);
          setEditableVerifiedText(data.note.verified_text || data.note.raw_ocr_text || "");
        } else if (item.rawNote) {
          setNoteDetails(item.rawNote);
          setEditableVerifiedText(item.rawNote.verified_text || item.rawNote.raw_ocr_text || "");
        }
      }
    } catch (err) {
      console.error("Failed to load item details:", err);
    } finally {
      setItemDetailLoading(false);
    }
  };

  const [verifyingNoteId, setVerifyingNoteId] = useState<string | null>(null);

  // Handle One-Click Direct Note Verification from Table Row
  const handleDirectVerifyNote = async (item: UnifiedDocumentItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setVerifyingNoteId(item.id);
    try {
      let textToVerify =
        item.rawNote?.verified_text ||
        item.rawNote?.raw_ocr_text;

      // If the list summary didn't include full OCR text, fetch detail from backend
      if (!textToVerify || !textToVerify.trim()) {
        const detail = await fetchNoteDetailApi(item.id);
        if (detail && detail.note) {
          textToVerify = detail.note.verified_text || detail.note.raw_ocr_text;
        }
      }

      textToVerify = (textToVerify && textToVerify.trim()) ? textToVerify : (item.title || "Verified handwritten document");

      const res = await verifyNoteApi(item.id, textToVerify, item.title);
      if (res) {
        // Optimistically update list in state
        setOcrNotes((prev) =>
          prev.map((n) =>
            n.id === item.id
              ? { ...n, verification_status: "VERIFIED", verified_text: textToVerify }
              : n
          )
        );
        try {
          await indexNote({ note_id: item.id, force_reindex: true });
        } catch (ragErr) {
          console.warn("RAG indexing notice:", ragErr);
        }
        await loadAllData();
      }
    } catch (err) {
      console.error("Direct note verification failed:", err);
    } finally {
      setVerifyingNoteId(null);
    }
  };

  // Handle Note OCR Human Verification from Modal
  const handleVerifyNote = async () => {
    if (!activeItem) return;
    setVerifyingAction(true);
    try {
      const text =
        editableVerifiedText.trim() ||
        noteDetails?.raw_ocr_text ||
        noteDetails?.verified_text ||
        activeItem.title ||
        "Verified text";
      const res = await verifyNoteApi(activeItem.id, text, activeItem.title);
      if (res) {
        setNoteDetails(res);
        try {
          await indexNote({ note_id: activeItem.id, force_reindex: true });
        } catch (ragErr) {
          console.warn("RAG indexing notice:", ragErr);
        }
        await loadAllData();
        setActiveItem(null);
      }
    } catch (err) {
      console.error("Verification failed:", err);
    } finally {
      setVerifyingAction(false);
    }
  };

  // Handle Note OCR Human Rejection from Modal
  const handleRejectNote = async () => {
    if (!activeItem) return;
    setVerifyingAction(true);
    try {
      const res = await rejectNoteApi(activeItem.id);
      if (res) {
        setNoteDetails(res);
        await loadAllData();
        setActiveItem(null);
      }
    } catch (err) {
      console.error("Rejection failed:", err);
    } finally {
      setVerifyingAction(false);
    }
  };

  // Handle Digital Event Verification
  const handleVerifyEvent = async (docId: string, eventId: string) => {
    const res = await verifyExtractedEventApi(docId, eventId);
    if (res && digitalDocDetails) {
      setDigitalDocDetails({
        ...digitalDocDetails,
        extracted_events: digitalDocDetails.extracted_events.map((e) =>
          e.id === eventId ? { ...e, verification_status: "VERIFIED" } : e
        ),
      });
      loadAllData();
    }
  };

  // Handle Digital Event Rejection
  const handleRejectEvent = async (docId: string, eventId: string) => {
    const res = await rejectExtractedEventApi(docId, eventId);
    if (res && digitalDocDetails) {
      setDigitalDocDetails({
        ...digitalDocDetails,
        extracted_events: digitalDocDetails.extracted_events.map((e) =>
          e.id === eventId ? { ...e, verification_status: "REJECTED" } : e
        ),
      });
      loadAllData();
    }
  };

  // Delete note handler
  const handleDeleteNote = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this handwritten note?")) {
      const ok = await deleteNoteApi(id);
      if (ok) {
        loadAllData();
        if (activeItem?.id === id) setActiveItem(null);
      }
    }
  };

  // Handle Gemini RAG Chat submit
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = chatInput.trim();
    if (!query || chatLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await ragQuery({ question: query });
      const geminiMsg: ChatMessage = {
        id: `gemini-${Date.now()}`,
        sender: "gemini",
        text: res.answer || "I could not retrieve an answer for that question.",
        sources: res.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        llmUsed: res.llm_used,
      };
      setChatMessages((prev) => [...prev, geminiMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "gemini",
        text: `Error contacting RAG assistant: ${err.message || "Request failed"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setChatMessages((prev) => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="space-y-6 font-mono pb-16">
      {/* Top Header Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
              eRTMAC DOCUMENT & KNOWLEDGE HUB
            </span>
            <span className="text-xs text-slate-500">• Unified OCR, Ingestion & RAG</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-cyan-400" />
            Documents Repository
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Unified console for typed technical reports (PDF/DOCX), handwritten shift log OCR, human verification, and Gemini-powered RAG knowledge intelligence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadAllData}
            className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700/60 transition-all shadow-sm"
            title="Refresh documents list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          <button
            onClick={() => {
              setUploadMsg(null);
              setShowUploadModal(true);
            }}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 shadow-lg shadow-blue-500/25 border border-blue-400/30 transition-all transform active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>NEW DOCUMENT</span>
          </button>
        </div>
      </div>

      {/* Search Bar & Ask AI Button Row */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by filename, note title, well ID, or keywords..."
            className="w-full bg-slate-900/90 border border-slate-800 hover:border-slate-700 focus:border-cyan-500/80 rounded-xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none transition-all shadow-inner"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* ASK AI (Gemini RAG Chat) Button */}
        <button
          onClick={() => setShowChatDrawer(true)}
          className="flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl font-bold text-xs text-cyan-300 bg-cyan-950/70 hover:bg-cyan-900/90 border border-cyan-500/40 hover:border-cyan-400 shadow-lg shadow-cyan-950/50 transition-all group shrink-0"
        >
          <Sparkles className="w-4 h-4 text-cyan-400 group-hover:rotate-12 transition-transform" />
          <span className="tracking-wider">ASK AI (GEMINI RAG)</span>
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        </button>
      </div>

      {/* Status Segmented Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setStatusFilter("ALL")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "ALL"
              ? "bg-slate-800 text-white border border-slate-700 shadow-md"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          <span>ALL DOCUMENTS</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-950 text-slate-300 border border-slate-800">
            {unifiedItems.length}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("YET_TO_BE_VERIFIED")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "YET_TO_BE_VERIFIED"
              ? "bg-amber-950/60 text-amber-300 border border-amber-500/40 shadow-md"
              : "text-slate-400 hover:text-amber-300 hover:bg-slate-900"
          }`}
        >
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>YET TO BE VERIFIED</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-950 text-amber-300 border border-amber-500/30">
            {unifiedItems.filter((i) => i.verificationStatus === "YET_TO_BE_VERIFIED").length}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("VERIFIED")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "VERIFIED"
              ? "bg-emerald-950/60 text-emerald-300 border border-emerald-500/40 shadow-md"
              : "text-slate-400 hover:text-emerald-300 hover:bg-slate-900"
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>VERIFIED</span>
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-500/30">
            {unifiedItems.filter((i) => i.verificationStatus === "VERIFIED").length}
          </span>
        </button>
      </div>

      {/* Unified Documents Table List */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between text-xs font-bold text-slate-300 bg-slate-950/40">
          <span>Documents & OCR Ingestions ({filteredItems.length} records)</span>
          <span className="text-[11px] text-slate-500">Associated Active Well: <strong className="text-cyan-400">{selectedWell}</strong></span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-bold tracking-wider">
                <th className="p-3.5">SOURCE / TYPE</th>
                <th className="p-3.5">DOCUMENT TITLE / FILENAME</th>
                <th className="p-3.5">UPLOADED AT</th>
                <th className="p-3.5">STATUS</th>
                <th className="p-3.5">ENTITIES / EVENTS</th>
                <th className="p-3.5 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredItems.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} className="p-12 text-center text-slate-500">
                    <FileText className="w-8 h-8 mx-auto text-slate-600 mb-2 opacity-50" />
                    <p className="font-bold text-sm text-slate-400">No documents found matching this filter.</p>
                    <p className="text-xs text-slate-600 mt-1">Click "NEW DOCUMENT" to upload reports or handwritten notes.</p>
                  </td>
                </tr>
              )}

              {filteredItems.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => openItemDetails(item)}
                  className="hover:bg-slate-800/50 cursor-pointer transition-colors group"
                >
                  {/* Source Type Badge */}
                  <td className="p-3.5">
                    {item.sourceType === "DIGITAL_DOC" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-blue-950/70 text-blue-300 border border-blue-500/30">
                        <FileCode className="w-3 h-3 text-blue-400" />
                        DIGITAL {item.fileType}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-indigo-950/70 text-indigo-300 border border-indigo-500/30">
                        <ImageIcon className="w-3 h-3 text-indigo-400" />
                        HANDWRITTEN OCR
                      </span>
                    )}
                  </td>

                  {/* Document Title / Filename */}
                  <td className="p-3.5">
                    <div className="font-bold text-slate-100 group-hover:text-cyan-300 transition-colors flex items-center gap-2">
                      <span className="truncate max-w-xs sm:max-w-md">{item.title}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5 flex items-center gap-2">
                      <span>ID: {item.id.slice(0, 16)}...</span>
                      {item.wellId && <span>• Well: {item.wellId}</span>}
                    </div>
                  </td>

                  {/* Upload Date */}
                  <td className="p-3.5 text-slate-400 text-[11px] whitespace-nowrap">
                    {new Date(item.createdAt).toLocaleDateString()} {new Date(item.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>

                  {/* Verification Status */}
                  <td className="p-3.5">
                    {item.verificationStatus === "VERIFIED" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        VERIFIED
                      </span>
                    )}
                    {item.verificationStatus === "YET_TO_BE_VERIFIED" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-500/30 animate-pulse">
                        <Clock className="w-3 h-3 text-amber-400" />
                        NEEDS REVIEW
                      </span>
                    )}
                    {item.verificationStatus === "REJECTED" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-950/80 text-rose-300 border border-rose-500/30">
                        <XCircle className="w-3 h-3 text-rose-400" />
                        REJECTED
                      </span>
                    )}
                  </td>

                  {/* Extracted Entities / Events */}
                  <td className="p-3.5">
                    {item.sourceType === "DIGITAL_DOC" ? (
                      <span className="text-[11px] text-cyan-400 font-bold">
                        {item.eventsCount} events parsed
                      </span>
                    ) : (
                      <span className="text-[11px] text-indigo-400 font-bold">
                        {item.confidenceLevel || "HIGH"} confidence
                      </span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="p-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-2">
                      {/* One-click direct verify for OCR notes */}
                      {item.sourceType === "HANDWRITTEN_OCR" && item.verificationStatus === "YET_TO_BE_VERIFIED" && (
                        <button
                          onClick={(e) => handleDirectVerifyNote(item, e)}
                          disabled={verifyingNoteId === item.id}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-[11px] font-bold transition shadow-sm flex items-center gap-1"
                          title="Quick Approve & Verify Note"
                        >
                          {verifyingNoteId === item.id ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Check className="w-3 h-3" />
                          )}
                          <span>{verifyingNoteId === item.id ? "VERIFYING..." : "VERIFY"}</span>
                        </button>
                      )}

                      <button
                        onClick={() => openItemDetails(item)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold border border-slate-700 transition flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3 text-cyan-400" />
                        <span>{item.verificationStatus === "YET_TO_BE_VERIFIED" ? "REVIEW" : "VIEW"}</span>
                      </button>

                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── NEW DOCUMENT MODAL ── */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white uppercase tracking-wider">
                    Add New Document
                  </h3>
                  <p className="text-[11px] text-slate-400">Select document category for ingestion</p>
                </div>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Tab Selector */}
            <div className="grid grid-cols-2 p-3 bg-slate-950/40 border-b border-slate-800 gap-2">
              <button
                type="button"
                onClick={() => {
                  setUploadTab("DIGITAL");
                  setUploadMsg(null);
                }}
                className={`py-2.5 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all ${
                  uploadTab === "DIGITAL"
                    ? "bg-blue-600 text-white shadow-md shadow-blue-500/30 border border-blue-400/40"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                }`}
              >
                <FileCode className="w-4 h-4" />
                <span>DIGITAL FILE (PDF / DOCX / TXT)</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setUploadTab("OCR");
                  setUploadMsg(null);
                }}
                className={`py-2.5 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all ${
                  uploadTab === "OCR"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-500/30 border border-indigo-400/40"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                }`}
              >
                <ImageIcon className="w-4 h-4" />
                <span>HANDWRITTEN NOTE / OCR</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4">
              {uploadTab === "DIGITAL" ? (
                /* Digital Document Upload Form */
                <div className="space-y-4">
                  <p className="text-xs text-slate-400">
                    Upload digital drilling daily reports, incident logs, or CSV data. Automated text parsing, event extraction, and automatic verification run immediately.
                  </p>

                  <div className="relative border-2 border-dashed border-slate-700 hover:border-blue-500/60 rounded-xl p-8 text-center transition bg-slate-950/40">
                    <input
                      type="file"
                      onChange={handleDigitalFileUpload}
                      accept=".pdf,.txt,.csv,.docx,.log"
                      disabled={uploading}
                      className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed"
                    />
                    <div className="flex flex-col items-center gap-2">
                      <div className="p-3 bg-blue-950/60 rounded-full border border-blue-500/30 text-blue-400">
                        <UploadCloud className={`w-8 h-8 ${uploading ? "animate-bounce" : ""}`} />
                      </div>
                      <p className="text-sm font-bold text-white">
                        {uploading ? "Parsing & Verifying Document..." : "Click or Drag PDF/DOCX/TXT here"}
                      </p>
                      <span className="text-[11px] text-slate-500">Supports PDF, TXT, CSV, DOCX (Max 50MB) • Auto-Verified</span>
                    </div>
                  </div>
                </div>
              ) : (
                /* Handwritten Note OCR Form */
                <form onSubmit={handleOcrSubmit} className="space-y-4">
                  <p className="text-xs text-slate-400">
                    Upload photos or scans of handwritten field notes, shift logs, or inspection checklists. Mistral Vision OCR will transcribe and place the document in the verification queue.
                  </p>

                  <div>
                    <label className="text-xs font-bold text-slate-300 block mb-1.5">Note Title (Optional)</label>
                    <input
                      type="text"
                      value={ocrTitle}
                      onChange={(e) => setOcrTitle(e.target.value)}
                      placeholder="e.g. Shift B - Pump 2 Inspection Log"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-300 block mb-1.5">OCR Model</label>
                    <select
                      value={ocrModel}
                      onChange={(e) => setOcrModel(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                    >
                      <option value="mistral-ocr-latest">Mistral OCR Engine (mistral-ocr-latest)</option>
                      <option value="pixtral-12b-2409">Pixtral Vision (pixtral-12b-2409)</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-300 block mb-1.5">Handwritten Image File</label>
                    <input
                      type="file"
                      accept="image/*,.pdf"
                      onChange={(e) => setOcrFile(e.target.files?.[0] || null)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-300 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={!ocrFile || uploading}
                    className="w-full py-3 rounded-xl font-bold text-xs text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2"
                  >
                    {uploading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Transcribing Handwritten Note...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Run OCR Transcription</span>
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Status Message */}
              {uploadMsg && (
                <div
                  className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 ${
                    uploadMsg.type === "success"
                      ? "bg-emerald-950/60 text-emerald-300 border-emerald-500/30"
                      : uploadMsg.type === "duplicate"
                      ? "bg-amber-950/60 text-amber-300 border-amber-500/30"
                      : "bg-rose-950/60 text-rose-300 border-rose-500/30"
                  }`}
                >
                  {uploadMsg.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                  {uploadMsg.type === "duplicate" && <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />}
                  {uploadMsg.type === "error" && <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                  <span>{uploadMsg.text}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── DOCUMENT & NOTE DETAIL / VERIFICATION MODAL ── */}
      {activeItem && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
                  {activeItem.sourceType === "DIGITAL_DOC" ? <FileText className="w-5 h-5" /> : <ImageIcon className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white uppercase tracking-wider">
                    {activeItem.title}
                  </h3>
                  <span className="text-[11px] text-slate-400">
                    {activeItem.sourceType === "DIGITAL_DOC" ? "Digital Document Details (Auto-Verified)" : "Handwritten OCR Review & Verification"}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setActiveItem(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {itemDetailLoading ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
                  <span>Loading document contents...</span>
                </div>
              ) : activeItem.sourceType === "DIGITAL_DOC" && digitalDocDetails ? (
                /* Digital Document Content */
                <div className="space-y-5">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {/* Left Column: PDF Preview */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 h-[600px] flex flex-col">
                    <h4 className="text-xs font-bold text-slate-300 uppercase mb-2">Document Preview</h4>
                    {activeItem.filename?.toLowerCase().match(/\.(png|jpe?g|gif|webp)$/i) || ["PNG", "JPEG", "JPG", "GIF"].includes((digitalDocDetails.document.document_type || digitalDocDetails.document.doc_type || "").toUpperCase()) ? (
                      <div className="w-full h-full flex items-center justify-center overflow-hidden bg-black/40 rounded">
                        <img 
                          src={`${API_BASE_URL}/api/documents/${digitalDocDetails.document.id}/content`}
                          alt="Document Preview"
                          className="max-w-full max-h-full object-contain"
                        />
                      </div>
                    ) : (
                      <iframe
                        src={`${API_BASE_URL}/api/documents/${digitalDocDetails.document.id}/content#view=Fit`}
                        className="w-full h-full rounded bg-white"
                        title="Document Preview"
                      />
                    )}
                  </div>

                  {/* Right Column: Details */}
                  <div className="space-y-5 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Document Information</h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div><span className="text-slate-500 block text-[10px]">ID:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.id}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">TYPE:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.document_type || digitalDocDetails.document.doc_type}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">STATUS:</span><span className="text-emerald-400 font-bold">VERIFIED</span></div>
                        <div><span className="text-slate-500 block text-[10px]">EVENTS COUNT:</span><span className="text-cyan-400">{digitalDocDetails.extracted_events?.length || 0}</span></div>
                      </div>
                    </div>

                    {/* Document Metadata Details */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Imported Details</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">FILE NAME:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.filename}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">WELL ID:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.source_metadata?.well_id || activeItem.wellId || "N/A"}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">DEPTH:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.source_metadata?.depth || "N/A"}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">WATER DEPTH:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.source_metadata?.water_depth || "N/A"}</span></div>
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">REPORT PERIOD:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.source_metadata?.report_period || "N/A"}</span></div>
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">ABNORMAL REMARKS:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.source_metadata?.abnormal_remarks || "None"}</span></div>
                      </div>
                    </div>
                    
                    {/* Summary & Tags Section (Like OCR Notes) */}
                    {(digitalDocDetails.document.source_metadata?.summary || digitalDocDetails.document.source_metadata?.tags) && (
                      <div className="bg-cyan-950/20 border border-cyan-900/30 rounded-xl p-4 space-y-3">
                        {digitalDocDetails.document.source_metadata?.summary && (
                          <div>
                            <h4 className="text-xs font-bold text-cyan-400 flex items-center gap-1.5 mb-1.5">
                              <Bot className="w-3.5 h-3.5" /> AI Summary
                            </h4>
                            <p className="text-xs text-slate-300 leading-relaxed break-words">
                              {digitalDocDetails.document.source_metadata.summary}
                            </p>
                          </div>
                        )}
                        
                        {digitalDocDetails.document.source_metadata?.tags?.length > 0 && (
                          <div>
                            <h4 className="text-xs font-bold text-cyan-400 mb-1.5">Tags</h4>
                            <div className="flex flex-wrap gap-1.5">
                              {digitalDocDetails.document.source_metadata.tags.map((tag: string, idx: number) => (
                                <span key={idx} className="px-2 py-0.5 rounded-lg bg-cyan-900/40 text-cyan-300 text-[10px] font-bold border border-cyan-700/50">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                  {/* Extracted Events Section */}
                  <div>
                    <h4 className="text-xs font-bold text-slate-300 uppercase mb-3 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-cyan-400" /> Extracted Event Episodes ({digitalDocDetails.extracted_events?.length || 0})
                    </h4>
                    <div className="space-y-3">
                      {digitalDocDetails.extracted_events?.length === 0 && (
                        <p className="text-xs text-slate-500 italic">No structured events extracted from this file.</p>
                      )}
                      {digitalDocDetails.extracted_events?.map((ev: any) => (
                        <div key={ev.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white uppercase">{ev.event_type || "OPERATION LOG"}</span>
                            <div className="flex items-center gap-2">
                              {ev.verification_status === "VERIFIED" ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                                  VERIFIED
                                </span>
                              ) : (
                                <div className="flex items-center gap-1.5">
                                  <button
                                    onClick={() => handleVerifyEvent(digitalDocDetails.document.id, ev.id)}
                                    className="px-2 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold flex items-center gap-1"
                                  >
                                    <Check className="w-3 h-3" /> VERIFY
                                  </button>
                                  <button
                                    onClick={() => handleRejectEvent(digitalDocDetails.document.id, ev.id)}
                                    className="px-2 py-1 rounded bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-500/30 text-[10px] font-bold flex items-center gap-1"
                                  >
                                    <X className="w-3 h-3" /> REJECT
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                          <p className="text-xs text-slate-300">{ev.summary || ev.raw_text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : noteDetails ? (
                /* Handwritten OCR Note Review & Edit */
                <div className="space-y-5">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    {/* Left Column: Image Preview and Transcription */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-4">
                      <div>
                        <h4 className="text-xs font-bold text-slate-300 uppercase mb-2">Scanned Note Image</h4>
                        <div className="w-full max-h-[400px] bg-black/40 rounded flex items-center justify-center overflow-hidden">
                          <img
                            src={`${API_BASE_URL}/api/v1/notes/images/${noteDetails.metadata?.storage?.stored_filename || noteDetails.storage_path?.split('/').pop() || activeItem.filename}`}
                            alt="Scanned Handwritten Note"
                            className="max-w-full max-h-full object-contain"
                          />
                        </div>
                      </div>
                      
                      {/* Transcribed Text */}
                      <div className="flex-1 flex flex-col min-h-[150px]">
                        <h4 className="text-xs font-bold text-slate-300 uppercase mb-2">Transcribed Text</h4>
                        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex-1 overflow-y-auto custom-scrollbar max-h-[300px]">
                          <p className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                            {noteDetails.verified_text || noteDetails.raw_ocr_text || "No transcription available."}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Right Column: Details */}
                    <div className="space-y-5 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
                      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                        <h4 className="text-xs font-bold text-slate-300 uppercase">Handwritten Note Details</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div><span className="text-slate-500 block text-[10px]">NOTE ID:</span><span className="text-slate-200 break-words">{noteDetails.id.slice(0, 12)}...</span></div>
                          <div><span className="text-slate-500 block text-[10px]">CONFIDENCE:</span><span className="text-cyan-400">{noteDetails.confidence_level}</span></div>
                          <div><span className="text-slate-500 block text-[10px]">STATUS:</span><span className="text-amber-400 font-bold">{noteDetails.verification_status}</span></div>
                          <div><span className="text-slate-500 block text-[10px]">SOURCE:</span><span className="text-slate-200">{noteDetails.source}</span></div>
                        </div>
                      </div>

                      {/* OCR Metadata Details instead of Transcribed Text */}
                      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2">
                    <h4 className="text-xs font-bold text-slate-300 uppercase">Imported Details</h4>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div><span className="text-slate-500 block text-[10px]">FILE NAME:</span><span className="text-slate-200">{noteDetails.original_filename || activeItem.filename}</span></div>
                      <div><span className="text-slate-500 block text-[10px]">WELL ID:</span><span className="text-slate-200">{noteDetails.well_id || noteDetails.structured_data?.well_id || "N/A"}</span></div>
                      <div><span className="text-slate-500 block text-[10px]">DEPTH:</span><span className="text-slate-200">{noteDetails.structured_data?.depth || "N/A"}</span></div>
                      <div><span className="text-slate-500 block text-[10px]">WATER DEPTH:</span><span className="text-slate-200">{noteDetails.structured_data?.water_depth || "N/A"}</span></div>
                      <div className="col-span-2"><span className="text-slate-500 block text-[10px]">REPORT PERIOD:</span><span className="text-slate-200">{noteDetails.structured_data?.report_period || "N/A"}</span></div>
                      <div className="col-span-2"><span className="text-slate-500 block text-[10px]">ABNORMAL REMARKS:</span><span className="text-slate-200">{noteDetails.structured_data?.abnormal_remarks || "None"}</span></div>
                    </div>
                  </div>

                      {/* Side-by-side or Edit View is removed per user request */}
                      {noteDetails.verification_status !== "VERIFIED" && (
                        <div className="flex items-center justify-end gap-3 pt-2">
                          <button
                            onClick={handleRejectNote}
                            disabled={verifyingAction}
                            className="px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 shadow-lg shadow-rose-600/20 disabled:opacity-50 transition flex items-center gap-2"
                          >
                            {verifyingAction ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <X className="w-4 h-4" />
                            )}
                            <span>REJECT OCR</span>
                          </button>
                          
                          <button
                            onClick={handleVerifyNote}
                            disabled={verifyingAction}
                            className="px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-600/20 disabled:opacity-50 transition flex items-center gap-2"
                          >
                            {verifyingAction ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <ShieldCheck className="w-4 h-4" />
                            )}
                            <span>APPROVE & MARK AS VERIFIED (INDEX IN RAG)</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* ── ASK AI (GEMINI RAG CHAT) SLIDING DRAWER ── */}
      {showChatDrawer && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end">
          <div className="bg-slate-900 border-l border-slate-800 w-full max-w-xl h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-cyan-950 border border-cyan-500/40 rounded-xl text-cyan-400 shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    Gemini AI Technical Assistant
                    <span className="px-2 py-0.5 rounded text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-500/30">
                      RAG Active
                    </span>
                  </h3>
                  <p className="text-[10px] text-slate-400">Grounded exclusively on your verified documents & notes</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => {
                    setChatMessages([
                      {
                        id: `welcome-${Date.now()}`,
                        sender: "gemini",
                        text: "Hello! I am your AI Technical Assistant powered by Google Gemini and Grounded RAG. Ask me anything about your uploaded drilling reports, logbooks, or handwritten notes.",
                        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                      },
                    ]);
                  }}
                  className="px-2.5 py-1 text-[10px] font-bold text-slate-400 hover:text-slate-200 bg-slate-800/80 hover:bg-slate-700 rounded-lg border border-slate-700/60 transition"
                  title="Clear conversation history"
                >
                  Clear Chat
                </button>
                <button
                  onClick={() => setShowChatDrawer(false)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Quick Prompt Pills */}
            <div className="p-3 bg-slate-950/40 border-b border-slate-800/80 flex items-center gap-2 overflow-x-auto text-[11px]">
              <span className="text-slate-500 font-bold shrink-0">Try:</span>
              <button
                onClick={() => setChatInput("Summarize the most recent daily drilling reports and equipment logs.")}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0 border border-slate-700 transition"
              >
                Summarize recent reports
              </button>
              <button
                onClick={() => setChatInput("Were any high torque, pressure anomalies, or equipment warnings logged?")}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 shrink-0 border border-slate-700 transition"
              >
                Check equipment anomalies
              </button>
            </div>

            {/* Messages Feed */}
            <div className="flex-1 p-4 overflow-y-auto space-y-4">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`max-w-[88%] rounded-2xl p-3.5 text-xs leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-blue-600 text-white rounded-br-none shadow-md shadow-blue-600/20"
                        : "bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none shadow-md"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>

                    {/* Source Citations */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/80 space-y-1.5">
                        <span className="text-[10px] font-bold text-cyan-400 block uppercase tracking-wider">
                          Referenced Sources ({msg.sources.length}):
                        </span>
                        {msg.sources.map((src, idx) => (
                          <div
                            key={idx}
                            className="text-[10px] bg-slate-900/80 border border-slate-800 rounded-lg p-2 text-slate-300 flex items-start gap-1.5"
                          >
                            <span className="text-cyan-400 font-bold">[{idx + 1}]</span>
                            <div className="flex-1">
                              <strong className="text-white">{src.title}</strong> — {src.section}
                              {src.verified_at && (
                                <span className="text-slate-500 block text-[9px]">Verified: {new Date(src.verified_at).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="text-[9px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                </div>
              ))}

              {chatLoading && (
                <div className="flex items-center gap-2 p-3 bg-slate-950 border border-slate-800 rounded-2xl rounded-bl-none text-xs text-cyan-400 max-w-[75%] animate-pulse">
                  <Sparkles className="w-4 h-4 animate-spin" />
                  <span>Gemini is querying verified knowledge index...</span>
                </div>
              )}
            </div>

            {/* Chat Input Bar */}
            <form onSubmit={handleChatSubmit} className="p-3.5 border-t border-slate-800 bg-slate-950/80">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask a technical question based on your documents..."
                  className="flex-1 bg-slate-900 border border-slate-800 focus:border-cyan-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || chatLoading}
                  className="p-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl transition shadow-md shadow-cyan-600/20"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentsPage;
