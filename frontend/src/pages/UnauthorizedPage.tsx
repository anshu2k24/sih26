import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ShieldOff, ArrowLeft } from "lucide-react";

export const UnauthorizedPage: React.FC = () => {
  const { profile } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="flex items-center justify-center">
          <div className="p-4 bg-rose-950/40 border border-rose-500/30 rounded-2xl">
            <ShieldOff className="w-10 h-10 text-rose-400" />
          </div>
        </div>

        <div>
          <h1 className="text-xl font-bold text-white font-mono tracking-wider uppercase mb-2">
            Access Denied
          </h1>
          <p className="text-sm text-slate-400">
            Your current role does not include the permission required to access
            this resource.
          </p>
          {profile && (
            <p className="text-xs text-slate-500 mt-2 font-mono">
              Authenticated as: <strong className="text-slate-300">{profile.email}</strong>
              {" "}— Role: <strong className="text-amber-400">{profile.role}</strong>
            </p>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-left space-y-2">
          <p className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
            What to do
          </p>
          <ul className="text-xs text-slate-400 space-y-1">
            <li>• Contact your system administrator to request access.</li>
            <li>• Ensure you are logged in with the correct account.</li>
            <li>• All access attempts are recorded in the audit trail.</li>
          </ul>
        </div>

        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 mx-auto text-sm text-slate-400 hover:text-white
                     font-mono border border-slate-700 hover:border-slate-500 px-4 py-2 rounded-lg
                     transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          Go Back
        </button>
      </div>
    </div>
  );
};
