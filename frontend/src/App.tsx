import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { tokenStorage, authApi } from './api/client';
import Header from './components/Header';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import DocumentPage from './pages/DocumentPage';
import ChatPage, { type ChatPageHandle } from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import AgentTaskPage from './pages/AgentTaskPage';

// Protected route: redirects to /login if not authenticated
function RequireAuth({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [checking, setChecking] = useState(true);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    const token = tokenStorage.get();
    if (!token) {
      setHasToken(false);
      setChecking(false);
      return;
    }
    // Verify token is still valid via /auth/me
    authApi.me()
      .then(() => setHasToken(true))
      .catch(() => {
        tokenStorage.clear();
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('username');
        setHasToken(false);
      })
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <svg className="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-sm text-gray-500">验证身份中...</p>
        </div>
      </div>
    );
  }

  if (!hasToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// Wrapper that holds the ChatPage ref so Header can access it
function ChatPageWrapper({ chatPageRef }: { chatPageRef: React.RefObject<ChatPageHandle> }) {
  return <ChatPage ref={chatPageRef} />;
}

export default function App() {
  const chatPageRef = useRef<ChatPageHandle>(null!);

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Header chatPageRef={chatPageRef} />
        <main className="flex-1 flex flex-col">
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected — require auth */}
            <Route
              path="/knowledge-bases"
              element={
                <RequireAuth>
                  <KnowledgeBasePage />
                </RequireAuth>
              }
            />
            <Route
              path="/knowledge-bases/:kbId/documents"
              element={
                <RequireAuth>
                  <DocumentPage />
                </RequireAuth>
              }
            />
            <Route
              path="/knowledge-bases/:kbId/chat"
              element={
                <RequireAuth>
                  <ChatPageWrapper chatPageRef={chatPageRef} />
                </RequireAuth>
              }
            />
            <Route
              path="/knowledge-bases/:kbId/agent"
              element={
                <RequireAuth>
                  <AgentTaskPage />
                </RequireAuth>
              }
            />
            <Route
              path="/agent"
              element={
                <RequireAuth>
                  <AgentTaskPage />
                </RequireAuth>
              }
            />

            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/knowledge-bases" replace />} />
            <Route path="*" element={<Navigate to="/knowledge-bases" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
