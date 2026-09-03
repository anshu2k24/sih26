import React, { useState, useEffect, useCallback } from "react";
import { AlertTriangle, X, ShieldAlert, Info } from "lucide-react";

interface Toast {
  id: string;
  severity: string;
  title: string;
  description: string;
}

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const { severity, title, description } = (e as CustomEvent).detail;
      const id = `toast_${Date.now()}`;
      setToasts((prev) => [...prev.slice(-4), { id, severity, title, description }]);
      // Auto-dismiss after 7s
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 7000);
    };
    window.addEventListener("ertmac:toast", handler);
    return () => window.removeEventListener("ertmac:toast", handler);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => {
        const isCritical = t.severity === "CRITICAL" || t.severity === "HIGH";
        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-2xl backdrop-blur-md transition-all duration-300 animate-slideIn font-mono
              ${isCritical
                ? "bg-rose-950/90 border-rose-500/60 shadow-rose-500/20"
                : t.severity === "MEDIUM"
                ? "bg-amber-950/90 border-amber-500/60 shadow-amber-500/20"
                : "bg-slate-900/90 border-slate-700 shadow-slate-700/20"
              }`}
          >
            {isCritical
              ? <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5 animate-pulse" />
              : t.severity === "MEDIUM"
              ? <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              : <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />}

            <div className="flex-1 min-w-0">
              <div className={`text-sm font-bold whitespace-pre-wrap break-words ${isCritical ? "text-rose-300" : t.severity === "MEDIUM" ? "text-amber-300" : "text-slate-200"}`}>
                {t.title}
              </div>
              <div className="text-xs text-slate-400 font-sans mt-0.5 whitespace-pre-wrap break-words">{t.description}</div>
            </div>

            <button
              onClick={() => dismiss(t.id)}
              className="text-slate-500 hover:text-slate-300 transition-colors shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
