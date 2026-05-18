import { useState, useEffect, useRef, useCallback, useImperativeHandle, forwardRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { knowledgeBaseApi, chatApi, type KnowledgeBase, type ChatMessage, type StreamSource, type SessionSummary } from '../api/client';
import SourceCard from '../components/SourceCard';

export interface ChatPageHandle {
  clearConversation: () => void;
}

const ChatPage = forwardRef<ChatPageHandle>(function ChatPage(_props, ref) {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState(kbId ?? '');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [activeSources, setActiveSources] = useState<StreamSource[] | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useImperativeHandle(ref, () => ({
    clearConversation: () => {
      setMessages([]);
      setActiveSources(null);
      setCurrentSessionId(null);
    },
  }));

  useEffect(() => {
    knowledgeBaseApi.list().then((data) => setKbs(data.knowledge_bases)).catch(console.error);
  }, []);

  const loadSessions = useCallback(async (kbId: string) => {
    setSessionsLoading(true);
    try {
      const list = await chatApi.listSessions(kbId);
      setSessions(list);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedKbId) {
      navigate(`/knowledge-bases/${selectedKbId}/chat`, { replace: true });
      loadSessions(selectedKbId);
    }
  }, [selectedKbId, navigate, loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeSources]);

  const loadSessionHistory = useCallback(async (sessionId: string) => {
    try {
      const history = await chatApi.getHistory(sessionId);
      const msgs: ChatMessage[] = history.map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        sources: m.sources as StreamSource[] | undefined,
      }));
      setMessages(msgs);
      setCurrentSessionId(sessionId);
      setActiveSources(null);
    } catch (err) {
      console.error('Failed to load session history:', err);
    }
  }, []);

  const startNewChat = useCallback(() => {
    setMessages([]);
    setActiveSources(null);
    setCurrentSessionId(null);
  }, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || !selectedKbId || streaming) return;

    setInput('');
    setStreaming(true);
    setActiveSources(null);

    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);

    abortRef.current = new AbortController();
    let assistantText = '';
    let pendingSources: StreamSource[] | undefined = undefined;
    let receivedSessionId: string | undefined = undefined;

    try {
      const stream = chatApi.stream({
        knowledge_base_id: selectedKbId,
        message: question,
        session_id: currentSessionId ?? undefined,
      });

      const reader = stream.getReader();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        if (value.sessionId && !receivedSessionId) {
          receivedSessionId = value.sessionId;
          setCurrentSessionId(receivedSessionId);
          loadSessions(selectedKbId);
        }
        if (value.token) {
          assistantText += value.token;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, content: assistantText }];
            }
            return [...prev, { role: 'assistant', content: assistantText }];
          });
        }
        if (value.sources) {
          pendingSources = value.sources ?? undefined;
        }
        if (value.done) {
          break;
        }
      }

      if (pendingSources) {
        setActiveSources(pendingSources);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { ...last, sources: pendingSources }];
          }
          return prev;
        });
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '抱歉，发生了错误，请稍后重试。' },
        ]);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, selectedKbId, streaming, currentSessionId, loadSessions]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const currentKb = kbs.find((k) => k.id === selectedKbId);

  const formatSessionLabel = (session: SessionSummary): string => {
    if (!session.last_message) return '新对话';
    return session.last_message.length > 22
      ? session.last_message.slice(0, 22) + '...'
      : session.last_message;
  };

  const formatTime = (isoString: string): string => {
    const d = new Date(isoString);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${Math.floor(diff / 86400000)}天前`;
  };

  return (
    <div className="flex flex-1 h-[calc(100vh-4rem)] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
        <div className="px-4 py-4 border-b border-gray-100">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">选择知识库</h2>
          <select
            value={selectedKbId}
            onChange={(e) => {
              setSelectedKbId(e.target.value);
              startNewChat();
            }}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
          >
            <option value="">— 选择知识库 —</option>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto py-3 px-2">
          <div className="flex items-center justify-between px-2 mb-1">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">会话记录</h2>
            <button
              onClick={() => {
                startNewChat();
                if (selectedKbId) loadSessions(selectedKbId);
              }}
              className="p-1 text-gray-400 hover:text-primary-600 hover:bg-gray-100 rounded transition"
              title="新对话"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          {sessionsLoading ? (
            <div className="px-3 py-2 text-xs text-gray-400">加载中...</div>
          ) : sessions.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-400">暂无会话记录</div>
          ) : (
            <div className="space-y-0.5">
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => loadSessionHistory(session.session_id)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition text-sm ${
                    currentSessionId === session.session_id
                      ? 'bg-primary-50 border-l-2 border-primary-500'
                      : 'hover:bg-gray-100 border-l-2 border-transparent'
                  }`}
                >
                  <div className="text-gray-800 truncate">{formatSessionLabel(session)}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{formatTime(session.updated_at)} · {session.message_count}条</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Bottom utility buttons */}
        <div className="border-t border-gray-100 py-3 px-2 space-y-1">
          <button
            onClick={() => navigate(`/knowledge-bases/${selectedKbId}/documents`)}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 rounded-lg transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            文档管理
          </button>
        </div>
      </aside>

      {/* Chat area */}
      <main className="flex-1 flex flex-col bg-gray-50/50 overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
          <button
            onClick={() => navigate('/knowledge-bases')}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex-1">
            <h1 className="text-base font-semibold text-gray-900">智能问答</h1>
            {currentKb && (
              <p className="text-xs text-gray-400">当前知识库：{currentKb.name}</p>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mb-4 shadow-sm">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="text-base font-medium text-gray-700 mb-1">开始对话</h3>
              <p className="text-sm text-gray-400 max-w-xs">
                {selectedKbId ? '在下方输入问题，基于知识库内容进行智能问答' : '请先在左侧选择知识库'}
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                msg.role === 'user'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white border border-gray-200 text-gray-600 shadow-sm'
              }`}>
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div className={`flex-1 max-w-2xl ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary-500 text-white rounded-tr-sm'
                    : 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm'
                }`}>
                  {msg.content}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <SourceCard sources={msg.sources} />
                )}
              </div>
            </div>
          ))}

          {streaming && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 shadow-sm">
                AI
              </div>
              <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                <div className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="h-1.5 w-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="h-1.5 w-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="px-6 py-4 bg-white border-t border-gray-200">
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedKbId ? '输入问题，按 Enter 发送，Shift+Enter 换行...' : '请先选择知识库'}
              disabled={!selectedKbId || streaming}
              rows={1}
              className="flex-1 px-4 py-3 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition disabled:bg-gray-50 disabled:text-gray-400"
              style={{ maxHeight: '120px' }}
              onInput={(e) => {
                const t = e.target as HTMLTextAreaElement;
                t.style.height = 'auto';
                t.style.height = Math.min(t.scrollHeight, 120) + 'px';
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || !selectedKbId || streaming}
              className="flex-shrink-0 p-3 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
});

export default ChatPage;
