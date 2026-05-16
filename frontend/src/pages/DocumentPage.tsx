import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { documentApi, type Document } from '../api/client';
import FileUpload from '../components/FileUpload';

const statusLabel: Record<Document['status'], string> = {
  pending: '等待中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

const statusColor: Record<Document['status'], string> = {
  pending: 'bg-gray-100 text-gray-600',
  processing: 'bg-yellow-100 text-yellow-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-600',
};

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function DocumentRow({ doc, onDeleted }: { doc: Document; onDeleted: (id: string) => void }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`确定要删除文档「${doc.title}」吗？`)) return;
    setDeleting(true);
    try {
      await documentApi.delete(doc.id);
      onDeleted(doc.id);
    } catch {
      alert('删除失败，请重试');
    } finally {
      setDeleting(false);
    }
  };

  const ext = doc.file_type.replace('.', '').toUpperCase();

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50/60 transition-colors">
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-bold text-gray-500">{ext}</span>
          </div>
          <div className="min-w-0">
            <p className="font-medium text-gray-900 truncate">{doc.title}</p>
            <p className="text-xs text-gray-400">{formatSize(doc.file_size)}</p>
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-sm text-gray-500">{doc.file_type}</td>
      <td className="py-3 px-4">
        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[doc.status]}`}>
          {statusLabel[doc.status]}
        </span>
      </td>
      <td className="py-3 px-4 text-sm text-gray-500">
        {doc.chunk_count != null ? doc.chunk_count + ' 个切片' : '-'}
      </td>
      <td className="py-3 px-4 text-sm text-gray-400">
        {new Date(doc.created_at).toLocaleString('zh-CN')}
      </td>
      <td className="py-3 px-4">
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition disabled:opacity-50"
          title="删除文档"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </td>
    </tr>
  );
}

export default function DocumentPage() {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDocs = async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const data = await documentApi.list({ knowledge_base_id: kbId });
      setDocs(data);
    } catch {
      console.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [kbId]);

  const handleDeleted = (id: string) => {
    setDocs((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate('/knowledge-bases')}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">文档管理</h1>
          <p className="text-sm text-gray-500 mt-0.5">知识库 ID: {kbId}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/knowledge-bases/${kbId}/chat`)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            问答
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm mb-6">
        <div className="p-5 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">上传文档</h2>
          <FileUpload knowledgeBaseId={kbId!} onUploaded={fetchDocs} />
        </div>
        <div>
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              文档列表
              {docs.length > 0 && (
                <span className="ml-2 text-xs font-normal text-gray-400">共 {docs.length} 个</span>
              )}
            </h2>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-400 text-sm gap-2">
              <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              加载中...
            </div>
          ) : docs.length === 0 ? (
            <div className="py-12 text-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-sm text-gray-400">暂无文档，上传第一个文件开始</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-gray-400 uppercase tracking-wide border-b border-gray-100">
                    <th className="py-2.5 px-4 font-medium">文件名</th>
                    <th className="py-2.5 px-4 font-medium">类型</th>
                    <th className="py-2.5 px-4 font-medium">状态</th>
                    <th className="py-2.5 px-4 font-medium">切片数</th>
                    <th className="py-2.5 px-4 font-medium">上传时间</th>
                    <th className="py-2.5 px-4 font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((doc) => (
                    <DocumentRow key={doc.id} doc={doc} onDeleted={handleDeleted} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
