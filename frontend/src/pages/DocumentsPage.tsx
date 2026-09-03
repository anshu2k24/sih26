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
      text: "Hello! I am your AI Technical Assistant powered by Grounded RAG. Ask me anything about your uploaded drilling reports, logbooks, or handwritten notes.",
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
    <>
      <div 
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          backgroundImage: "url('/bg-map.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center",
          opacity: 0.15,
        }}
      />
      {/* Ambient Lights */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[20%] right-[10%] w-[600px] h-[600px] bg-[#FF8A00] rounded-full mix-blend-screen filter blur-[150px] opacity-10" />
        <div className="absolute bottom-[-10%] left-[20%] w-[500px] h-[500px] bg-[#FF8A00] rounded-full mix-blend-screen filter blur-[120px] opacity-[0.05]" />
      </div>
      <div className="space-y-6 font-mono pb-16 relative z-10">
        {/* Top Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-2">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider text-[#FF9D1A] border" style={{ background: "rgba(255,140,0,0.10)", borderColor: "rgba(255,140,0,0.3)" }}>
                eRTMAC DOCUMENT & KNOWLEDGE HUB
              </span>
              <span className="text-xs text-slate-500">• Unified OCR, Ingestion & RAG</span>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2.5">
              DOCUMENTS REPOSITORY
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadAllData}
              className="p-2.5 rounded-xl transition-all shadow-sm group hover:-translate-y-[1px]"
              style={{ background: "rgba(10, 10, 10, 0.5)", border: "1px solid rgba(255, 145, 0, 0.2)" }}
              title="Refresh documents list"
            >
              <RefreshCw className={`w-4 h-4 text-slate-400 group-hover:text-[#FF9D1A] ${loading ? "animate-spin text-[#FF9D1A]" : ""}`} />
            </button>

            <button
              onClick={() => {
                setUploadMsg(null);
                setShowUploadModal(true);
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-[#FF9D1A] transition-all transform active:scale-95 group hover:-translate-y-[1px] hover:text-[#FFF]"
              style={{ 
                background: "rgba(255,140,0,0.10)", 
                border: "1px solid rgba(255, 145, 0, 0.4)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,140,0,0.20)";
                e.currentTarget.style.boxShadow = "0 0 22px rgba(255,140,0,0.45)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255,140,0,0.10)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <Plus className="w-4 h-4 group-hover:text-[#FFF]" />
              <span>NEW DOCUMENT</span>
            </button>
          </div>
        </div>

      {/* Search Bar & Ask AI Button Row */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        {/* Search Bar */}
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#FF9D1A] transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by filename, note title, well ID, or keywords..."
            className="w-full rounded-xl pl-11 pr-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none transition-all focus:shadow-[0_0_15px_rgba(255,140,0,0.2)]"
            style={{ background: "rgba(10, 10, 10, 0.72)", border: "1px solid rgba(255, 145, 0, 0.15)", backdropFilter: "blur(14px)" }}
            onFocus={(e) => e.target.style.borderColor = "rgba(255, 145, 0, 0.5)"}
            onBlur={(e) => e.target.style.borderColor = "rgba(255, 145, 0, 0.15)"}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#FF9D1A]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* ASK AI (Gemini RAG Chat) Button */}
        <button
          onClick={() => setShowChatDrawer(true)}
          className="flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl font-bold text-xs text-[#FF9D1A] transition-all group shrink-0 hover:-translate-y-[1px]"
          style={{ background: "rgba(10, 10, 10, 0.72)", border: "1px solid rgba(255, 145, 0, 0.3)", backdropFilter: "blur(14px)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = "0 0 20px rgba(255,140,0,0.3)";
            e.currentTarget.style.borderColor = "rgba(255, 145, 0, 0.6)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "none";
            e.currentTarget.style.borderColor = "rgba(255, 145, 0, 0.3)";
          }}
        >
          <Sparkles className="w-4 h-4 text-[#FF9D1A] group-hover:rotate-12 transition-transform group-hover:brightness-125" />
          <span className="tracking-wider group-hover:brightness-125">ChatBot</span>
          <span className="w-2 h-2 rounded-full bg-[#FF9D1A] animate-pulse" />
        </button>
      </div>

      {/* Status Segmented Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-[rgba(255,145,0,0.15)] pb-2">
        <button
          onClick={() => setStatusFilter("ALL")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "ALL"
              ? "text-[#FFF] shadow-[0_0_15px_rgba(255,140,0,0.2)]"
              : "text-slate-400 hover:text-[#FF9D1A]"
          }`}
          style={{
            background: statusFilter === "ALL" ? "rgba(255,140,0,0.15)" : "rgba(10,10,10,0.5)",
            border: statusFilter === "ALL" ? "1px solid rgba(255, 145, 0, 0.5)" : "1px solid rgba(255, 145, 0, 0.1)",
          }}
        >
          <Layers className={`w-3.5 h-3.5 ${statusFilter === "ALL" ? "text-[#FF9D1A]" : "text-slate-500"}`} />
          <span>ALL DOCUMENTS</span>
          <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,145,0,0.2)", color: statusFilter === "ALL" ? "#FFF" : "#888" }}>
            {unifiedItems.length}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("YET_TO_BE_VERIFIED")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "YET_TO_BE_VERIFIED"
              ? "text-[#FFF] shadow-[0_0_15px_rgba(255,140,0,0.2)]"
              : "text-slate-400 hover:text-[#FF9D1A]"
          }`}
          style={{
            background: statusFilter === "YET_TO_BE_VERIFIED" ? "rgba(255,140,0,0.15)" : "rgba(10,10,10,0.5)",
            border: statusFilter === "YET_TO_BE_VERIFIED" ? "1px solid rgba(255, 145, 0, 0.5)" : "1px solid rgba(255, 145, 0, 0.1)",
          }}
        >
          <Clock className={`w-3.5 h-3.5 ${statusFilter === "YET_TO_BE_VERIFIED" ? "text-[#FF9D1A]" : "text-slate-500"}`} />
          <span>YET TO BE VERIFIED</span>
          <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,145,0,0.2)", color: statusFilter === "YET_TO_BE_VERIFIED" ? "#FFF" : "#888" }}>
            {unifiedItems.filter((i) => i.verificationStatus === "YET_TO_BE_VERIFIED").length}
          </span>
        </button>

        <button
          onClick={() => setStatusFilter("VERIFIED")}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
            statusFilter === "VERIFIED"
              ? "text-[#FFF] shadow-[0_0_15px_rgba(255,140,0,0.2)]"
              : "text-slate-400 hover:text-[#FF9D1A]"
          }`}
          style={{
            background: statusFilter === "VERIFIED" ? "rgba(255,140,0,0.15)" : "rgba(10,10,10,0.5)",
            border: statusFilter === "VERIFIED" ? "1px solid rgba(255, 145, 0, 0.5)" : "1px solid rgba(255, 145, 0, 0.1)",
          }}
        >
          <ShieldCheck className={`w-3.5 h-3.5 ${statusFilter === "VERIFIED" ? "text-[#FF9D1A]" : "text-slate-500"}`} />
          <span>VERIFIED</span>
          <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,145,0,0.2)", color: statusFilter === "VERIFIED" ? "#FFF" : "#888" }}>
            {unifiedItems.filter((i) => i.verificationStatus === "VERIFIED").length}
          </span>
        </button>
      </div>

      {/* Unified Documents Table List */}
      <div 
        className="rounded-2xl overflow-hidden shadow-[0_8px_35px_rgba(0,0,0,0.35)]"
        style={{ background: "rgba(10, 10, 10, 0.72)", backdropFilter: "blur(14px)", border: "1px solid rgba(255, 145, 0, 0.15)", borderTop: "1px solid rgba(255,145,0,0.4)" }}
      >
        <div className="p-4 flex items-center justify-between text-xs font-bold text-slate-300" style={{ borderBottom: "1px solid rgba(255,145,0,0.15)", background: "rgba(0,0,0,0.2)" }}>
          <span className="flex items-center gap-2"><FileText className="w-4 h-4 text-[#FF9D1A]" /> Documents & OCR Ingestions ({filteredItems.length} records)</span>
          <span className="text-[11px] text-slate-400">Associated Active Well: <strong className="text-[#FF9D1A]">{selectedWell}</strong></span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="text-[#FF9D1A] font-bold tracking-wider" style={{ borderBottom: "1px solid rgba(255,145,0,0.15)", background: "rgba(0,0,0,0.3)" }}>
                <th className="p-3.5 font-semibold text-[11px]">SOURCE / TYPE</th>
                <th className="p-3.5 font-semibold text-[11px]">DOCUMENT TITLE / FILENAME</th>
                <th className="p-3.5 font-semibold text-[11px]">UPLOADED AT</th>
                <th className="p-3.5 font-semibold text-[11px]">STATUS</th>
                <th className="p-3.5 font-semibold text-[11px]">ENTITIES / EVENTS</th>
                <th className="p-3.5 text-right font-semibold text-[11px]">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(255,145,0,0.05)]">
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
                  className="cursor-pointer transition-colors group"
                  style={{ background: "rgba(0,0,0,0.4)" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255,145,0,0.05)";
                    e.currentTarget.style.boxShadow = "inset 2px 0 0 #FF9D1A, inset -2px 0 0 #FF9D1A";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(0,0,0,0.4)";
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  {/* Source Type Badge */}
                  <td className="p-3.5">
                    {item.sourceType === "DIGITAL_DOC" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all group-hover:brightness-125 group-hover:shadow-[0_0_10px_rgba(255,145,0,0.2)]" style={{ background: "rgba(10,10,10,0.6)", color: "#FF9D1A", border: "1px solid rgba(255,145,0,0.3)" }}>
                        <FileCode className="w-3 h-3 text-[#FF9D1A]" />
                        DIGITAL {item.fileType}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all group-hover:brightness-125 group-hover:shadow-[0_0_10px_rgba(255,145,0,0.2)]" style={{ background: "rgba(10,10,10,0.6)", color: "#FF9D1A", border: "1px solid rgba(255,145,0,0.3)" }}>
                        <ImageIcon className="w-3 h-3 text-[#FF9D1A]" />
                        HANDWRITTEN OCR
                      </span>
                    )}
                  </td>

                  {/* Document Title / Filename */}
                  <td className="p-3.5">
                    <div className="font-bold text-slate-100 group-hover:text-white transition-colors flex items-center gap-2">
                      <span className="truncate max-w-xs sm:max-w-md group-hover:brightness-125">{item.title}</span>
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
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold transition-all" style={{ background: "rgba(10,10,10,0.6)", color: "#10b981", border: "1px solid rgba(16, 185, 129, 0.4)", boxShadow: "0 0 10px rgba(16, 185, 129, 0.1)" }}>
                        <CheckCircle2 className="w-3 h-3 text-[#10b981]" />
                        VERIFIED
                      </span>
                    )}
                    {item.verificationStatus === "YET_TO_BE_VERIFIED" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold animate-pulse transition-all" style={{ background: "rgba(10,10,10,0.6)", color: "#f59e0b", border: "1px solid rgba(245, 158, 11, 0.4)", boxShadow: "0 0 10px rgba(245, 158, 11, 0.1)" }}>
                        <Clock className="w-3 h-3 text-[#f59e0b]" />
                        NEEDS REVIEW
                      </span>
                    )}
                    {item.verificationStatus === "REJECTED" && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold transition-all" style={{ background: "rgba(10,10,10,0.6)", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.4)", boxShadow: "0 0 10px rgba(239, 68, 68, 0.1)" }}>
                        <XCircle className="w-3 h-3 text-[#ef4444]" />
                        REJECTED
                      </span>
                    )}
                  </td>

                  {/* Extracted Entities / Events */}
                  <td className="p-3.5">
                    {item.sourceType === "DIGITAL_DOC" ? (
                      <span className="text-[11px] text-[#FF9D1A] font-bold opacity-80 group-hover:opacity-100">
                        {item.eventsCount} events parsed
                      </span>
                    ) : (
                      <span className="text-[11px] text-rose-400 font-bold opacity-80 group-hover:opacity-100">
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
                          className="px-3 py-1.5 rounded-lg disabled:opacity-50 text-[#10b981] text-[11px] font-bold transition shadow-sm flex items-center gap-1 hover:-translate-y-[1px]"
                          style={{ background: "rgba(10,10,10,0.6)", border: "1px solid rgba(16,185,129,0.3)" }}
                          title="Quick Approve & Verify Note"
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = "rgba(16,185,129,0.6)";
                            e.currentTarget.style.boxShadow = "0 0 15px rgba(16,185,129,0.3)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = "rgba(16,185,129,0.3)";
                            e.currentTarget.style.boxShadow = "none";
                          }}
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
                        className="px-3 py-1.5 rounded-lg text-[#FF9D1A] text-[11px] font-bold transition flex items-center gap-1 hover:-translate-y-[1px]"
                        style={{ background: "rgba(10,10,10,0.6)", border: "1px solid rgba(255,145,0,0.3)" }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255,145,0,0.8)";
                          e.currentTarget.style.boxShadow = "0 0 18px rgba(255,140,0,0.45)";
                          e.currentTarget.style.background = "rgba(255,145,0,0.15)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "rgba(255,145,0,0.3)";
                          e.currentTarget.style.boxShadow = "none";
                          e.currentTarget.style.background = "rgba(10,10,10,0.6)";
                        }}
                      >
                        <Eye className="w-3 h-3 text-[#FF9D1A]" />
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300" style={{ background: "rgba(0, 0, 0, 0.75)", backdropFilter: "blur(8px)" }}>
          {/* Modal Container */}
          <div 
            className="w-full max-w-[850px] rounded-3xl shadow-2xl flex flex-col relative overflow-hidden"
            style={{
              background: "rgba(10, 10, 10, 0.85)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
              border: "1px solid rgba(255, 122, 0, 0.25)",
              boxShadow: "0 0 60px rgba(255, 122, 0, 0.08), inset 0 0 20px rgba(255, 122, 0, 0.02)",
            }}
          >
            {/* Subtle ambient lighting behind modal content */}
            <div className="absolute inset-0 pointer-events-none z-0">
              <div className="absolute top-0 left-1/4 w-[400px] h-[150px] bg-[#FF7A00] rounded-full mix-blend-screen blur-[100px] opacity-[0.06]" />
            </div>

            <div className="relative z-10 flex flex-col w-full h-full p-8 md:p-10">
              {/* HEADER */}
              <div className="flex items-start justify-between w-full mb-8">
                <div className="flex items-center gap-5">
                  {/* Glowing Icon Container */}
                  <div 
                    className="flex items-center justify-center w-[54px] h-[54px] rounded-[16px] shrink-0"
                    style={{
                      background: "rgba(255, 122, 0, 0.05)",
                      border: "1px solid rgba(255, 122, 0, 0.35)",
                      boxShadow: "0 0 20px rgba(255, 122, 0, 0.15), inset 0 0 10px rgba(255, 122, 0, 0.1)",
                    }}
                  >
                    <UploadCloud className="w-7 h-7 text-[#FF7A00] drop-shadow-[0_0_8px_rgba(255,122,0,0.8)]" strokeWidth={2} />
                  </div>
                  <div className="flex flex-col justify-center">
                    <h3 className="text-[22px] md:text-[24px] font-bold text-white uppercase tracking-wide leading-tight" style={{ fontFamily: "'Space Grotesk', 'Inter', sans-serif" }}>
                      ADD NEW DOCUMENT
                    </h3>
                    <p className="text-[13px] text-[#9AA0A6] mt-1 font-mono tracking-wide">
                      Select document category for ingestion
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setShowUploadModal(false)}
                  className="group flex items-center justify-center w-10 h-10 rounded-full transition-all duration-200 shrink-0"
                  style={{
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "rgba(255, 122, 0, 0.1)";
                    e.currentTarget.style.border = "1px solid rgba(255, 122, 0, 0.4)";
                    e.currentTarget.style.boxShadow = "0 0 15px rgba(255, 122, 0, 0.2)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
                    e.currentTarget.style.border = "1px solid rgba(255, 255, 255, 0.08)";
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <X className="w-5 h-5 text-[#9AA0A6] group-hover:text-[#FF7A00] transition-colors" strokeWidth={2} />
                </button>
              </div>

              {/* HEADER SEPARATOR */}
              <div className="w-full h-[1px] mb-8" style={{ background: "linear-gradient(90deg, rgba(255, 122, 0, 0.15) 0%, rgba(255, 255, 255, 0.05) 50%, rgba(255, 255, 255, 0.02) 100%)" }} />

              {/* TABS */}
              <div className="flex flex-col sm:flex-row w-full gap-4 mb-10">
                {/* Digital Tab */}
                <button
                  type="button"
                  onClick={() => {
                    setUploadTab("DIGITAL");
                    setUploadMsg(null);
                  }}
                  className="flex-1 py-4 px-6 rounded-[14px] flex items-center justify-center gap-3 transition-all duration-300"
                  style={uploadTab === "DIGITAL" ? {
                    background: "rgba(255, 122, 0, 0.08)",
                    border: "1px solid rgba(255, 122, 0, 0.6)",
                    boxShadow: "0 0 25px rgba(255, 122, 0, 0.15), inset 0 0 12px rgba(255, 122, 0, 0.08)",
                  } : {
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                  onMouseEnter={(e) => {
                    if (uploadTab !== "DIGITAL") {
                      e.currentTarget.style.border = "1px solid rgba(255, 122, 0, 0.3)";
                      e.currentTarget.style.background = "rgba(255, 122, 0, 0.03)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (uploadTab !== "DIGITAL") {
                      e.currentTarget.style.border = "1px solid rgba(255, 255, 255, 0.06)";
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                    }
                  }}
                >
                  <FileCode className={`w-5 h-5 ${uploadTab === "DIGITAL" ? "text-[#FF7A00] drop-shadow-[0_0_5px_rgba(255,122,0,0.8)]" : "text-[#7A8086]"}`} strokeWidth={2} />
                  <span className={`text-[13px] tracking-widest font-bold ${uploadTab === "DIGITAL" ? "text-[#FF7A00] drop-shadow-[0_0_8px_rgba(255,122,0,0.3)]" : "text-[#7A8086]"}`}>
                    DIGITAL FILE (PDF / DOCX / TXT)
                  </span>
                </button>

                {/* OCR Tab */}
                <button
                  type="button"
                  onClick={() => {
                    setUploadTab("OCR");
                    setUploadMsg(null);
                  }}
                  className="flex-1 py-4 px-6 rounded-[14px] flex items-center justify-center gap-3 transition-all duration-300"
                  style={uploadTab === "OCR" ? {
                    background: "rgba(255, 122, 0, 0.08)",
                    border: "1px solid rgba(255, 122, 0, 0.6)",
                    boxShadow: "0 0 25px rgba(255, 122, 0, 0.15), inset 0 0 12px rgba(255, 122, 0, 0.08)",
                  } : {
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                  onMouseEnter={(e) => {
                    if (uploadTab !== "OCR") {
                      e.currentTarget.style.border = "1px solid rgba(255, 122, 0, 0.3)";
                      e.currentTarget.style.background = "rgba(255, 122, 0, 0.03)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (uploadTab !== "OCR") {
                      e.currentTarget.style.border = "1px solid rgba(255, 255, 255, 0.06)";
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                    }
                  }}
                >
                  <ImageIcon className={`w-5 h-5 ${uploadTab === "OCR" ? "text-[#FF7A00] drop-shadow-[0_0_5px_rgba(255,122,0,0.8)]" : "text-[#7A8086]"}`} strokeWidth={2} />
                  <span className={`text-[13px] tracking-widest font-bold ${uploadTab === "OCR" ? "text-[#FF7A00] drop-shadow-[0_0_8px_rgba(255,122,0,0.3)]" : "text-[#7A8086]"}`}>
                    HANDWRITTEN NOTE / OCR
                  </span>
                </button>
              </div>

              {/* DESCRIPTION & UPLOAD ZONE */}
              <div className="flex-1 flex flex-col min-h-0 w-full px-2">
                {uploadTab === "DIGITAL" ? (
                  <>
                    <div 
                      className="relative w-full rounded-[24px] flex flex-col items-center justify-center p-12 transition-all duration-300 group"
                      style={{
                        background: "rgba(5, 5, 5, 0.4)",
                        border: "1px dashed rgba(255, 122, 0, 0.3)",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "rgba(255, 122, 0, 0.03)";
                        e.currentTarget.style.border = "1px dashed rgba(255, 122, 0, 0.7)";
                        e.currentTarget.style.boxShadow = "inset 0 0 40px rgba(255, 122, 0, 0.05), 0 0 20px rgba(255, 122, 0, 0.05)";
                        const iconContainer = e.currentTarget.querySelector('.upload-icon-container') as HTMLElement;
                        if (iconContainer) {
                          iconContainer.style.boxShadow = "0 0 30px rgba(255, 122, 0, 0.2), inset 0 0 15px rgba(255, 122, 0, 0.15)";
                          iconContainer.style.transform = "scale(1.05)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "rgba(5, 5, 5, 0.4)";
                        e.currentTarget.style.border = "1px dashed rgba(255, 122, 0, 0.3)";
                        e.currentTarget.style.boxShadow = "none";
                        const iconContainer = e.currentTarget.querySelector('.upload-icon-container') as HTMLElement;
                        if (iconContainer) {
                          iconContainer.style.boxShadow = "0 0 20px rgba(255, 122, 0, 0.08), inset 0 0 10px rgba(255, 122, 0, 0.05)";
                          iconContainer.style.transform = "scale(1)";
                        }
                      }}
                    >
                      <input
                        type="file"
                        onChange={handleDigitalFileUpload}
                        accept=".pdf,.txt,.csv,.docx,.log"
                        disabled={uploading}
                        className="absolute inset-0 opacity-0 cursor-pointer w-full h-full disabled:cursor-not-allowed z-20"
                      />
                      
                      {/* Concentric Glow Rings */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[160px] h-[160px] rounded-full border border-[rgba(255,122,0,0.05)] pointer-events-none" />
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120px] h-[120px] rounded-full border border-[rgba(255,122,0,0.1)] pointer-events-none" />
                      
                      {/* Center Icon Container */}
                      <div 
                        className="upload-icon-container relative z-10 flex items-center justify-center w-[80px] h-[80px] rounded-full mb-8 transition-all duration-300"
                        style={{
                          background: "rgba(10, 10, 10, 0.8)",
                          border: "1px solid rgba(255, 122, 0, 0.2)",
                          boxShadow: "0 0 20px rgba(255, 122, 0, 0.08), inset 0 0 10px rgba(255, 122, 0, 0.05)",
                        }}
                      >
                        <UploadCloud className={`w-9 h-9 text-[#FF7A00] drop-shadow-[0_0_10px_rgba(255,122,0,0.6)] ${uploading ? 'animate-bounce' : ''}`} strokeWidth={2} />
                      </div>

                      <h4 className="relative z-10 text-[20px] font-bold text-white mb-3">
                        {uploading ? (
                          "Parsing & Verifying Document..."
                        ) : (
                          <>Click or Drag <span className="text-[#FF7A00]">PDF/DOCX/TXT</span> here</>
                        )}
                      </h4>
                      
                      <p className="relative z-10 text-[13px] text-[#7A8086] flex items-center gap-2 font-mono">
                        Supports PDF, TXT, CSV, DOCX (Max 50MB) 
                        <span className="w-1.5 h-1.5 rounded-full bg-[#FF7A00] drop-shadow-[0_0_4px_rgba(255,122,0,0.8)]"></span>
                        Auto-Verified
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-[14px] text-[#A1A1AA] leading-relaxed font-mono max-w-[700px] mb-8">
                      Upload photos or scans of handwritten field notes, shift logs, or inspection checklists. Selected OCR Engine will transcribe and place the document in the verification queue.
                    </p>

                    <form onSubmit={handleOcrSubmit} className="space-y-5">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                        <div className="space-y-2">
                          <label className="text-[12px] font-bold text-[#A1A1AA] uppercase tracking-wider block font-mono">Note Title (Optional)</label>
                          <input
                            type="text"
                            value={ocrTitle}
                            onChange={(e) => setOcrTitle(e.target.value)}
                            placeholder="e.g. Shift B - Pump 2 Inspection Log"
                            className="w-full bg-[rgba(5,5,5,0.4)] border border-[rgba(255,255,255,0.08)] rounded-[12px] px-4 py-3 text-[13px] text-white placeholder-[#7A8086] focus:outline-none focus:border-[#FF7A00] focus:ring-1 focus:ring-[#FF7A00]/50 transition-all font-mono"
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-[12px] font-bold text-[#A1A1AA] uppercase tracking-wider block font-mono">OCR Engine</label>
                          <select
                            value={ocrModel}
                            onChange={(e) => setOcrModel(e.target.value)}
                            className="w-full bg-[rgba(5,5,5,0.4)] border border-[rgba(255,255,255,0.08)] rounded-[12px] px-4 py-3 text-[13px] text-white focus:outline-none focus:border-[#FF7A00] focus:ring-1 focus:ring-[#FF7A00]/50 transition-all font-mono"
                          >
                            <option value="mistral-ocr-latest">Mistral OCR Engine</option>
                            <option value="pixtral-12b-2409">Pixtral Vision Engine</option>
                          </select>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-[12px] font-bold text-[#A1A1AA] uppercase tracking-wider block font-mono">Handwritten Image File</label>
                        <div 
                          className="relative w-full rounded-[16px] flex items-center p-4 transition-all duration-300"
                          style={{
                            background: "rgba(5, 5, 5, 0.4)",
                            border: "1px dashed rgba(255, 122, 0, 0.3)",
                          }}
                        >
                          <input
                            type="file"
                            accept="image/*,.pdf"
                            onChange={(e) => setOcrFile(e.target.files?.[0] || null)}
                            className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-20"
                          />
                          <div className="flex items-center gap-4 relative z-10 w-full">
                            <div className="p-3 bg-[rgba(255,122,0,0.05)] rounded-xl border border-[rgba(255,122,0,0.2)] text-[#FF7A00]">
                              <ImageIcon className="w-5 h-5" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[14px] font-bold text-white truncate">
                                {ocrFile ? ocrFile.name : "Click or drag to select image..."}
                              </p>
                              {ocrFile && <p className="text-[11px] text-[#A1A1AA] font-mono mt-0.5">Ready for processing</p>}
                            </div>
                            {ocrFile && (
                              <button 
                                type="button"
                                className="px-5 py-2.5 rounded-[10px] text-[12px] font-bold text-white transition-all z-30 flex items-center gap-2"
                                style={{
                                  background: "rgba(255, 122, 0, 0.15)",
                                  border: "1px solid rgba(255, 122, 0, 0.5)",
                                  boxShadow: "0 0 15px rgba(255, 122, 0, 0.15)",
                                }}
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleOcrSubmit(e as any);
                                }}
                                disabled={uploading}
                              >
                                {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                RUN TRANSCRIBER
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </form>
                  </>
                )}

                {/* Status Message Area */}
                {uploadMsg && (
                  <div
                    className="mt-6 p-4 rounded-[12px] text-[13px] font-mono flex items-center gap-3 transition-all"
                    style={
                      uploadMsg.type === "success"
                        ? { background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399" }
                        : uploadMsg.type === "duplicate"
                        ? { background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "#fbbf24" }
                        : { background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#f87171" }
                    }
                  >
                    {uploadMsg.type === "success" && <CheckCircle2 className="w-5 h-5 shrink-0" />}
                    {uploadMsg.type === "duplicate" && <AlertTriangle className="w-5 h-5 shrink-0" />}
                    {uploadMsg.type === "error" && <XCircle className="w-5 h-5 shrink-0" />}
                    <span>{uploadMsg.text}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── DOCUMENT & NOTE DETAIL / VERIFICATION MODAL ── */}
      {activeItem && (
        <div className="fixed inset-0 z-[100] bg-black/85 backdrop-blur-sm flex items-start justify-center pt-[70px] pb-6 px-4">
          <div 
            className="bg-slate-900 border border-slate-700 rounded-2xl w-full shadow-2xl flex flex-col overflow-hidden relative"
            style={{ 
              maxWidth: "1100px", 
              width: "90vw", 
              height: "80vh", 
              maxHeight: "calc(100vh - 100px)" 
            }}
          >
            {/* Modal Header - Fixed at top */}
            <div className="shrink-0 sticky top-0 z-20 p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950 shadow-md">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-950 border border-blue-500/40 rounded-xl text-blue-400 shadow-sm">
                  {activeItem.sourceType === "DIGITAL_DOC" ? <FileCode className="w-5 h-5" /> : <ImageIcon className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    {activeItem.title}
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                      {activeItem.sourceType === "DIGITAL_DOC" ? `DIGITAL ${activeItem.fileType}` : "HANDWRITTEN OCR"}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {activeItem.id}</p>
                </div>
              </div>
              <button
                onClick={() => setActiveItem(null)}
                className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body - Grid with independently scrolling columns */}
            <div className="flex-1 min-h-0 p-6 flex flex-col">
              {itemDetailLoading ? (
                <div className="py-20 flex-1 flex flex-col items-center justify-center text-center text-slate-400 space-y-3">
                  <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-400" />
                  <p className="text-sm">Loading document details & verified evidence...</p>
                </div>
              ) : activeItem.sourceType === "DIGITAL_DOC" && digitalDocDetails ? (
                /* Digital Document Content */
                <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                  {/* Left Column: PDF Preview */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col h-full min-h-0">
                    <h4 className="text-xs font-bold text-slate-300 uppercase mb-3 shrink-0">Document Preview</h4>
                    <div className="flex-1 min-h-0 overflow-hidden rounded bg-black/40">
                      {activeItem.filename?.toLowerCase().match(/\.(png|jpe?g|gif|webp)$/i) || ["PNG", "JPEG", "JPG", "GIF"].includes((digitalDocDetails.document.document_type || digitalDocDetails.document.doc_type || "").toUpperCase()) ? (
                        <div className="w-full h-full flex items-center justify-center">
                          <img 
                            src={`${API_BASE_URL}/api/documents/${digitalDocDetails.document.id}/content`}
                            alt="Document Preview"
                            className="max-w-full max-h-full object-contain"
                          />
                        </div>
                      ) : (
                        <iframe
                          src={`${API_BASE_URL}/api/documents/${digitalDocDetails.document.id}/content#view=Fit`}
                          className="w-full h-full bg-white"
                          title="Document Preview"
                        />
                      )}
                    </div>
                  </div>

                  {/* Right Column: Details & Events */}
                  <div className="flex flex-col space-y-5 overflow-y-auto min-h-0 h-full pr-2 custom-scrollbar">
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2 shrink-0">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Document Information</h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div><span className="text-slate-500 block text-[10px]">ID:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.id}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">TYPE:</span><span className="text-slate-200 break-words">{digitalDocDetails.document.document_type || digitalDocDetails.document.doc_type}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">STATUS:</span><span className="text-emerald-400 font-bold">VERIFIED</span></div>
                        <div><span className="text-slate-500 block text-[10px]">EVENTS COUNT:</span><span className="text-cyan-400">{digitalDocDetails.extracted_events?.length || 0}</span></div>
                      </div>
                    </div>

                    {/* Document Metadata Details */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2 shrink-0">
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
                      <div className="bg-cyan-950/20 border border-cyan-900/30 rounded-xl p-4 space-y-3 shrink-0">
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
                            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Semantic Tags</h4>
                            <div className="flex flex-wrap gap-1.5">
                              {digitalDocDetails.document.source_metadata.tags.map((tag: string, i: number) => (
                                <span key={i} className="px-2 py-0.5 rounded-full text-[10px] bg-cyan-950/60 text-cyan-300 border border-cyan-700/40">
                                  #{tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Extracted Events Section */}
                    <div className="space-y-3 shrink-0 pb-4">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">
                        Extracted Events & Operational Episodes ({digitalDocDetails.extracted_events?.length || 0})
                      </h4>
                      <div className="space-y-2">
                        {digitalDocDetails.extracted_events?.map((ev: any) => (
                          <div key={ev.id} className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-cyan-400">{ev.event_type || "Drilling Event"}</span>
                              <span className="text-[10px] font-mono text-slate-500">MD: {ev.onset_md ? `${ev.onset_md}m` : "N/A"}</span>
                            </div>
                            <p className="text-xs text-slate-300">{ev.summary || ev.raw_text}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ) : noteDetails ? (
                /* Handwritten OCR Note Review & Edit */
                <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                  {/* Left Column: Image Preview and Transcription */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col h-full min-h-0 gap-4">
                    <div className="flex-1 min-h-0 flex flex-col">
                      <h4 className="text-xs font-bold text-slate-300 uppercase mb-3 shrink-0">Scanned Note Image</h4>
                      <div className="w-full flex-1 min-h-0 bg-black/40 rounded flex items-center justify-center overflow-hidden">
                        <img
                          src={`${API_BASE_URL}/api/v1/notes/images/${encodeURIComponent(
                            (noteDetails.metadata?.storage as any)?.stored_filename ||
                            noteDetails.storage_path?.split('/').pop() ||
                            noteDetails.public_url?.split('/').pop() ||
                            (noteDetails.metadata?.storage as any)?.filename ||
                            activeItem.filename ||
                            noteDetails.id
                          )}`}
                          alt="Scanned Handwritten Note"
                          className="max-w-full max-h-full object-contain"
                          onError={(e) => {
                            const target = e.currentTarget;
                            if (!target.src.includes("fallback")) {
                              target.src = `${API_BASE_URL}/api/v1/notes/images/${encodeURIComponent(noteDetails.id)}?fallback=1`;
                            }
                          }}
                        />
                      </div>
                    </div>
                    
                    {/* Transcribed Text */}
                    <div className="h-1/3 min-h-[150px] flex flex-col shrink-0">
                      <h4 className="text-xs font-bold text-slate-300 uppercase mb-2 shrink-0">Transcribed Text</h4>
                      <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
                        <p className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                          {noteDetails.verified_text || noteDetails.raw_ocr_text || "No transcription available."}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Details */}
                  <div className="flex flex-col space-y-5 overflow-y-auto min-h-0 h-full pr-2 custom-scrollbar">
                    {/* Note Information */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2 shrink-0">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Note Information</h4>
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div><span className="text-slate-500 block text-[10px]">ID:</span><span className="text-slate-200 break-words">{noteDetails.id}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">SOURCE:</span><span className="text-slate-200 break-words">HANDWRITTEN OCR</span></div>
                        <div><span className="text-slate-500 block text-[10px]">STATUS:</span>
                          <span className={noteDetails.verification_status === "VERIFIED" ? "text-emerald-400 font-bold" : noteDetails.verification_status === "REJECTED" ? "text-rose-400 font-bold" : "text-amber-400 font-bold"}>
                            {noteDetails.verification_status === "VERIFIED" ? "VERIFIED" : noteDetails.verification_status === "REJECTED" ? "REJECTED" : "YET TO BE VERIFIED"}
                          </span>
                        </div>
                        <div><span className="text-slate-500 block text-[10px]">CONFIDENCE:</span><span className="text-slate-200">{noteDetails.confidence ? `${(noteDetails.confidence * 100).toFixed(1)}%` : "HIGH"}</span></div>
                      </div>
                    </div>

                    {/* Imported Note Details */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-2 shrink-0">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Imported Details</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">FILE NAME:</span><span className="text-slate-200 break-words">{noteDetails.title || noteDetails.metadata?.storage?.filename || activeItem.filename}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">WELL ID:</span><span className="text-slate-200 break-words">{noteDetails.structured_data?.well_id || noteDetails.well_id || "N/A"}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">DEPTH:</span><span className="text-slate-200 break-words">{noteDetails.structured_data?.depth || "N/A"}</span></div>
                        <div><span className="text-slate-500 block text-[10px]">WATER DEPTH:</span><span className="text-slate-200 break-words">{noteDetails.structured_data?.water_depth || "N/A"}</span></div>
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">REPORT PERIOD:</span><span className="text-slate-200 break-words">{noteDetails.structured_data?.report_period || "N/A"}</span></div>
                        <div className="col-span-1 sm:col-span-2"><span className="text-slate-500 block text-[10px]">ABNORMAL REMARKS:</span><span className="text-slate-200 break-words">{noteDetails.structured_data?.abnormal_remarks || "None"}</span></div>
                      </div>
                    </div>

                    {/* OCR Structured Entities & Measurements */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-4 shrink-0">
                      <h4 className="text-xs font-bold text-slate-300 uppercase">Structured Extraction (Mistral OCR)</h4>
                      
                      {/* Summary & Tags */}
                      {noteDetails.structured_data?.summary && (
                        <div className="space-y-1">
                          <span className="text-slate-500 text-[10px] uppercase font-bold">Summary</span>
                          <p className="text-xs text-slate-300 leading-relaxed">{noteDetails.structured_data.summary}</p>
                        </div>
                      )}
                      {noteDetails.structured_data?.tags && noteDetails.structured_data.tags.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-slate-500 text-[10px] uppercase font-bold">Tags</span>
                          <div className="flex flex-wrap gap-1.5">
                            {noteDetails.structured_data.tags.map((t, idx) => (
                              <span key={idx} className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                                #{t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Measurements List */}
                      {noteDetails.structured_data?.measurements && noteDetails.structured_data.measurements.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-slate-500 text-[10px] uppercase font-bold">Detected Measurements ({noteDetails.structured_data.measurements.length})</span>
                          <div className="grid grid-cols-2 gap-2">
                            {noteDetails.structured_data.measurements.map((m, idx) => (
                              <div key={idx} className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs">
                                <span className="text-slate-400 block text-[10px]">{m.parameter}</span>
                                <span className="font-bold text-cyan-400">{m.value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Identified Entities */}
                      {noteDetails.structured_data?.entities && noteDetails.structured_data.entities.length > 0 && (
                        <div className="space-y-2">
                          <span className="text-slate-500 text-[10px] uppercase font-bold">Detected Entities ({noteDetails.structured_data.entities.length})</span>
                          <div className="flex flex-wrap gap-1.5">
                            {noteDetails.structured_data.entities.map((ent, idx) => (
                              <span key={idx} className="px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-300">
                                <strong className="text-cyan-400">{ent.type}:</strong> {ent.value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Human Verification & Editing Action */}
                    <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-3 shrink-0 pb-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-slate-300 uppercase">Human Verification & Text Edit</h4>
                        <span className="text-[10px] text-slate-500">Edit and confirm to promote to RAG Ground Truth</span>
                      </div>
                      <textarea
                        rows={6}
                        value={editableVerifiedText}
                        onChange={(e) => setEditableVerifiedText(e.target.value)}
                        placeholder="Edit or correct OCR transcribed text before human verification..."
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500 transition"
                      />
                      <div className="flex items-center justify-end gap-2 pt-2">
                        {noteDetails.verification_status !== "REJECTED" && (
                          <button
                            onClick={handleRejectNote}
                            disabled={verifyingAction}
                            className="px-4 py-2 text-xs font-bold bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-700/50 rounded-xl transition flex items-center gap-1.5 disabled:opacity-50"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>REJECT OCR</span>
                          </button>
                        )}
                        <button
                          onClick={handleVerifyNote}
                          disabled={verifyingAction}
                          className="px-4 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl transition flex items-center gap-1.5 disabled:opacity-50 shadow-md shadow-emerald-600/20"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>VERIFY OCR AS GROUND TRUTH</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* ── CHATBOT SLIDING DRAWER ── */}
      {showChatDrawer && (
        <div className="fixed inset-0 top-[70px] z-[100] bg-black/70 backdrop-blur-sm flex justify-end">
          <div className="bg-slate-900 border-l border-slate-800 w-full max-w-xl h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
            {/* Drawer Header with Title and Clear/Exit Actions */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-cyan-950/80 border border-cyan-500/40 rounded-xl text-cyan-400 shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    AI Technical Assistant
                    <span className="px-2 py-0.5 rounded text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-500/30">
                      RAG Active
                    </span>
                  </h3>
                  <p className="text-[10px] text-slate-400">Grounded exclusively on your verified documents & notes</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setChatMessages([
                      {
                        id: `welcome-${Date.now()}`,
                        sender: "gemini",
                        text: "Hello! I am your AI Technical Assistant powered by Grounded RAG. Ask me anything about your uploaded drilling reports, logbooks, or handwritten notes.",
                        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                      },
                    ]);
                  }}
                  className="px-2.5 py-1.5 text-[10px] font-bold text-slate-300 hover:text-white bg-slate-800/90 hover:bg-slate-700 rounded-lg border border-slate-700 transition"
                  title="Clear conversation history"
                >
                  Clear Chat
                </button>
                <button
                  onClick={() => setShowChatDrawer(false)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-200 hover:text-white bg-rose-950/70 hover:bg-rose-900/90 border border-rose-700/50 rounded-xl transition shadow-sm"
                  title="Exit Chat"
                >
                  <X className="w-4 h-4 text-rose-400" />
                  <span>EXIT</span>
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
                  <span>AI assistant is querying verified knowledge index...</span>
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
    </>
  );
};

export default DocumentsPage;
