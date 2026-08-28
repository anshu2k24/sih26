/**
 * PS26121 — Protected Route Component
 *
 * Guards authenticated routes. If not authenticated → /login.
 * If authenticated but permission missing → /unauthorized.
 * While auth is initializing → shows loading spinner.
 */

import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { Loader2 } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Optional permission required to access this route (UX-level guard) */
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermission,
}) => {
  const { status, hasPermission } = useAuth();
  const location = useLocation();

  // Still determining session
  if (status === "initializing") {
    return (
      <div className="min-h-screen bg-[#070B14] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
          <span className="text-sm font-mono tracking-wider">
            INITIALIZING SESSION...
          </span>
        </div>
      </div>
    );
  }

  // Not authenticated → redirect to login, preserving intended route
  if (status === "unauthenticated") {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Session error state
  if (status === "error") {
    return <Navigate to="/login" state={{ from: location, authError: true }} replace />;
  }

  // Authenticated but missing required permission (UX guard only)
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};
