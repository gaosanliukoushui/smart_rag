import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import KnowledgeBasePage from './pages/KnowledgeBasePage';
import DocumentPage from './pages/DocumentPage';
import ChatPage from './pages/ChatPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-gray-50">
        <Header />
        <main className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<Navigate to="/knowledge-bases" replace />} />
            <Route path="/knowledge-bases" element={<KnowledgeBasePage />} />
            <Route path="/knowledge-bases/:kbId/documents" element={<DocumentPage />} />
            <Route path="/knowledge-bases/:kbId/chat" element={<ChatPage />} />
            <Route path="*" element={<Navigate to="/knowledge-bases" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
