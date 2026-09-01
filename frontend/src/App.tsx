import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { ActiveWellProvider } from "./context/ActiveWellContext";
import { Header } from "./components/layout/Header";

import { lazy, Suspense } from 'react';

// Public pages
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const UnauthorizedPage = lazy(() => import('./pages/UnauthorizedPage').then(m => ({ default: m.UnauthorizedPage })));

// Operational pages (protected)
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const LivePage = lazy(() => import('./pages/LivePage').then(m => ({ default: m.LivePage })));
const MapPage = lazy(() => import('./pages/MapPage').then(m => ({ default: m.MapPage })));
const WellsPage = lazy(() => import('./pages/WellsPage').then(m => ({ default: m.WellsPage })));
const WellIntelligencePage = lazy(() => import('./pages/WellIntelligencePage').then(m => ({ default: m.WellIntelligencePage })));
const KnowledgePage = lazy(() => import('./pages/KnowledgePage').then(m => ({ default: m.KnowledgePage })));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })));
const HandwrittenNotesPage = lazy(() => import('./pages/HandwrittenNotesPage').then(m => ({ default: m.HandwrittenNotesPage })));
const NoteUploadPage = lazy(() => import('./pages/NoteUploadPage').then(m => ({ default: m.NoteUploadPage })));
const NoteReviewPage = lazy(() => import('./pages/NoteReviewPage').then(m => ({ default: m.NoteReviewPage })));
const NoteDetailPage = lazy(() => import('./pages/NoteDetailPage').then(m => ({ default: m.NoteDetailPage })));
const EventEvidencePage = lazy(() => import('./pages/EventEvidencePage').then(m => ({ default: m.EventEvidencePage })));
const AlertsPage = lazy(() => import('./pages/AlertsPage').then(m => ({ default: m.AlertsPage })));
const PredictionsPage = lazy(() => import('./pages/PredictionsPage').then(m => ({ default: m.PredictionsPage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then(m => ({ default: m.AuditPage })));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage').then(m => ({ default: m.NotificationsPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then(m => ({ default: m.ReportsPage })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then(m => ({ default: m.AnalyticsPage })));
const AdminPage = lazy(() => import('./pages/AdminPage').then(m => ({ default: m.AdminPage })));
const UsersPage = lazy(() => import('./pages/UsersPage').then(m => ({ default: m.UsersPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const RiskPage = lazy(() => import('./pages/RiskPage').then(m => ({ default: m.RiskPage })));

import { Sidebar } from "./components/layout/Sidebar";
import { ToastContainer } from "./components/ToastContainer";

// Protected app shell (sidebar + header + content via Outlet)
function AppShell() {
  return (
    <ActiveWellProvider>
      <div className="min-h-screen bg-[#070B14] text-[#E8EEF7] font-sans flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
      {/* Global ML anomaly toast notifications */}
      <ToastContainer />
    </ActiveWellProvider>
  );
}


export function App() {
  return (
    <BrowserRouter>
      {/* AuthProvider wraps everything — provides session state globally */}
      <AuthProvider>
        <Suspense fallback={<div className="flex h-screen w-full items-center justify-center text-slate-400">Loading...</div>}>
          <Routes>
            {/* ── Public routes ─────────────────────────────────────── */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            {/* ── Protected operational routes with Persistent AppShell ── */}
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/live" element={<LivePage />} />
              <Route path="/map" element={<MapPage />} />
              <Route path="/wells" element={<WellsPage />} />
              <Route path="/wells/:wellId" element={<WellIntelligencePage />} />
              <Route path="/events" element={<KnowledgePage />} />
              <Route path="/events/:eventId" element={<EventEvidencePage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/notes" element={<HandwrittenNotesPage />} />
              <Route path="/notes/upload" element={<NoteUploadPage />} />
              <Route path="/notes/:noteId/review" element={<NoteReviewPage />} />
              <Route path="/notes/:noteId" element={<NoteDetailPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/predictions" element={<PredictionsPage />} />
              <Route path="/risk" element={<RiskPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute requiredPermission="MANAGE_SYSTEM">
                    <AdminPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/users"
                element={
                  <ProtectedRoute requiredPermission="MANAGE_USERS">
                    <UsersPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
