import React, { useState, useEffect } from "react";
import { fetchUserProfile } from "../services/api";
import type { UserInfo } from "../types/api";
import { Users, CheckCircle2 } from "lucide-react";

export const UsersPage: React.FC = () => {
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    fetchUserProfile().then((res) => {
      if (res) setUser(res);
    });
  }, []);

  return (
    <div className="space-y-6 font-mono">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-blue-400" />
            <h1 className="text-lg font-bold text-white uppercase tracking-wider">
              USER IDENTITY & RBAC MANAGEMENT
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-500/30 font-bold">
              ROLE-BASED ACCESS CONTROL
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative user roles and permission policies enforced across REST APIs and WebSocket stream endpoints.
          </p>
        </div>
      </div>

      {user && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <span className="text-xs text-slate-400 block text-[10px]">CURRENT AUTHENTICATED USER</span>
              <strong className="text-white text-base">{user.email}</strong>
              <span className="text-xs text-emerald-400 block mt-0.5 font-bold">ID: {user.user_id}</span>
            </div>

            <span className="text-xs px-3 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-500/40 font-bold">
              ROLE: {user.role}
            </span>
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">Assigned RBAC Permissions:</span>
            <div className="flex flex-wrap gap-2">
              {user.permissions.map((p) => (
                <span key={p} className="text-xs px-2.5 py-1 rounded bg-slate-950 text-slate-200 border border-slate-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> {p}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
