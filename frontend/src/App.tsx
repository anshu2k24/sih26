import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { ActiveWellProvider } from "./context/ActiveWellContext";
import { Header } from "./components/layout/Header";

// Public pages
import { LoginPage } from "./pages/LoginPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";

// Operational pages (protected)
import { DashboardPage } from "./pages/DashboardPage";
import { LivePage } from "./pages/LivePage";
import { MapPage } from "./pages/MapPage";
import { WellsPage } from "./pages/WellsPage";
import { WellIntelligencePage } from "./pages/WellIntelligencePage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { HandwrittenNotesPage } from "./pages/HandwrittenNotesPage";
import { NoteUploadPage } from "./pages/NoteUploadPage";
import { NoteReviewPage } from "./pages/NoteReviewPage";
import { NoteDetailPage } from "./pages/NoteDetailPage";
import { EventEvidencePage } from "./pages/EventEvidencePage";
import { AlertsPage } from "./pages/AlertsPage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { AuditPage } from "./pages/AuditPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AdminPage } from "./pages/AdminPage";
import { UsersPage } from "./pages/UsersPage";
import { SettingsPage } from "./pages/SettingsPage";


import { Sidebar } from "./components/layout/Sidebar";

// Protected app shell (sidebar + header + content via Outlet)
function AppShell() {
  return (
    <ActiveWellProvider>
      <div className="min-h-screen bg-[#070B14] text-[#E8EEF7] font-sans flex">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="flex-1 w-full p-4 sm:p-6 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </ActiveWellProvider>
  );
}


export function App() {
  return (
    <BrowserRouter>
      {/* AuthProvider wraps everything — provides session state globally */}
      <AuthProvider>
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
            <Route path="/risk" element={<PredictionsPage />} />
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
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
