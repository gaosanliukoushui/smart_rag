import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { knowledgeBaseApi, type KnowledgeBase } from '../api/client';
import KnowledgeBaseCard from '../components/KnowledgeBaseCard';
import CreateKnowledgeBaseModal from '../components/CreateKnowledgeBaseModal';

export default function KnowledgeBasePage() {
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchKbs = async () => {
    setLoading(true);
    try {
      const data = await knowledgeBaseApi.list();
      setKbs(data.knowledge_bases);
    } catch {
      console.error('Failed to load knowledge bases');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKbs();
  }, []);

  const handleDeleted = (id: string) => {
    setKbs((prev) => prev.filter((kb) => kb.id !== id));
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">知识库管理</h1>
          <p className="mt-1 text-sm text-gray-500">创建和管理多个知识库，每个知识库可关联多个文档</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition shadow-sm"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          新建知识库
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-2 text-gray-400">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            加载中...
          </div>
        </div>
      ) : kbs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
              />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-700 mb-1">暂无知识库</h3>
          <p className="text-sm text-gray-400 mb-5">点击上方按钮创建一个新的知识库</p>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition"
          >
            创建第一个知识库
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {kbs.map((kb) => (
            <div
              key={kb.id}
              className="cursor-pointer"
              onClick={() => navigate(`/knowledge-bases/${kb.id}/documents`)}
            >
              <KnowledgeBaseCard knowledgeBase={kb} onDeleted={handleDeleted} />
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <CreateKnowledgeBaseModal
          onClose={() => setShowModal(false)}
          onCreated={fetchKbs}
        />
      )}
    </div>
  );
}
