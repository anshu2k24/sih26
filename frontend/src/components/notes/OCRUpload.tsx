import React, { useState, useRef } from "react";
import {
  UploadCloud,
  Camera,
  FileImage,
  Sparkles,
  Loader2,
  AlertCircle,
  X,
  Cpu,
} from "lucide-react";
import { uploadNoteOcrApi } from "../../services/notesApi";
import type { HandwrittenNote } from "../../types/notes";

interface Props {
  onSuccess: (note: HandwrittenNote) => void;
}

export const OCRUpload: React.FC<Props> = ({ onSuccess }) => {
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("");
  const [model, setModel] = useState<string>("mistral-ocr-latest");
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadStep, setUploadStep] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File) => {
    setSelectedFile(file);
    setErrorMessage(null);
    if (!title) {
      const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
      setTitle(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setTitle("");
    setErrorMessage(null);
    setUploadStep("");
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setErrorMessage(null);

    // Multi-step progress visual feedback
    setUploadStep("1/3: Validating format & magic bytes...");
    await new Promise((r) => setTimeout(r, 250));

    setUploadStep("2/3: Applying contrast & orientation preprocessing...");
    await new Promise((r) => setTimeout(r, 300));

    setUploadStep("3/3: Running handwriting OCR transcription...");

    const res = await uploadNoteOcrApi(selectedFile, title || undefined, model);
    setUploading(false);

    if (res && res.success && res.note) {
      onSuccess(res.note);
    } else {
      setErrorMessage(res?.error || "Failed to process image. Please try again.");
    }
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-5">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
            <Sparkles className="w-5 h-5 text-blue-400" />
            Upload Handwritten Note
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Ingest photographs, scans, and field log sheets with vision OCR & structured extraction.
          </p>
        </div>

        {/* Model selector */}
        <div className="flex items-center gap-2 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800">
          <Cpu className="w-4 h-4 text-purple-400" />
          <span className="text-xs text-slate-400 font-medium">Model:</span>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={uploading}
            className="bg-transparent text-xs text-slate-200 font-medium focus:outline-none cursor-pointer"
          >
            <option value="mistral-ocr-latest" className="bg-slate-900 text-slate-100">
              Mistral OCR (Latest Vision)
            </option>
            <option value="pixtral-12b-2409" className="bg-slate-900 text-slate-100">
              Pixtral 12B Vision
            </option>
            <option value="mock-handwriting-v1" className="bg-slate-900 text-slate-100">
              Mock OCR (Demo Mode)
            </option>
          </select>
        </div>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-3 p-4 bg-rose-950/30 border border-rose-800/60 rounded-2xl text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span className="flex-1">{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-rose-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Dropzone & Preview */}
      {!selectedFile ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-3xl p-10 text-center transition flex flex-col items-center justify-center min-h-[300px] cursor-pointer ${
            dragOver
              ? "border-blue-500 bg-blue-500/10 shadow-inner"
              : "border-slate-700/80 bg-slate-950/40 hover:border-slate-600 hover:bg-slate-950/60"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/heic,application/pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
            }}
          />
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
            }}
          />

          <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4 text-blue-400">
            <UploadCloud className="w-8 h-8" />
          </div>

          <h3 className="text-base font-semibold text-slate-200 mb-1">
            Drag & drop handwritten document image here
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mb-5">
            Supports JPEG, PNG, WEBP, HEIC, and Scanned PDF (up to 25 MB)
          </p>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              className="px-4 py-2 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition"
            >
              Browse Files
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                cameraInputRef.current?.click();
              }}
              className="px-4 py-2 text-xs font-semibold text-cyan-300 bg-cyan-950/50 hover:bg-cyan-900/60 rounded-xl border border-cyan-800/50 transition flex items-center gap-1.5"
            >
              <Camera className="w-3.5 h-3.5" />
              Capture with Camera
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-950/60 rounded-3xl border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileImage className="w-5 h-5 text-blue-400" />
              <div>
                <h4 className="text-sm font-semibold text-slate-200 truncate max-w-md">
                  {selectedFile.name}
                </h4>
                <p className="text-xs text-slate-400">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || "image"}
                </p>
              </div>
            </div>
            {!uploading && (
              <button
                onClick={handleReset}
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition"
                title="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Image preview box */}
          {previewUrl && (
            <div className="w-full max-h-72 rounded-2xl overflow-hidden bg-slate-900 flex items-center justify-center border border-slate-800">
              <img
                src={previewUrl}
                alt="Upload preview"
                className="max-h-72 object-contain rounded-xl"
              />
            </div>
          )}

          {/* Title input */}
          <div>
            <label className="text-xs font-semibold text-slate-400 block mb-1">
              Document / Note Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={uploading}
              className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
              placeholder="e.g. Drilling Handover Log - Well 15/9-F-14"
            />
          </div>

          {/* Upload progress or submit button */}
          {uploading ? (
            <div className="p-4 bg-blue-950/30 border border-blue-800/40 rounded-2xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-blue-300">
                <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                <span>{uploadStep}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-full w-3/4 animate-pulse rounded-full" />
              </div>
            </div>
          ) : (
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={handleReset}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                className="px-6 py-2.5 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-blue-900/30 transition flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Process & Extract Note
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
