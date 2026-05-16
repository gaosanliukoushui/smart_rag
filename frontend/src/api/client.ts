import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- 知识库 ---

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  document_count?: number;
  created_at: string;
  updated_at?: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
}

export const knowledgeBaseApi = {
  list: () =>
    apiClient.get<KnowledgeBase[]>('/knowledge-bases').then((r) => r.data),

  create: (data: CreateKnowledgeBaseRequest) =>
    apiClient.post<KnowledgeBase>('/knowledge-bases', data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/knowledge-bases/${id}`).then((r) => r.data),
};

// --- 文档 ---

export interface Document {
  id: string;
  knowledge_base_id: string;
  title: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count?: number;
  created_at: string;
  updated_at?: string;
}

export interface DocumentListParams {
  knowledge_base_id?: string;
  page?: number;
  page_size?: number;
}

export const documentApi = {
  list: (params?: DocumentListParams) =>
    apiClient.get<Document[]>('/documents', { params }).then((r) => r.data),

  upload: (knowledgeBaseId: string, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('knowledge_base_id', knowledgeBaseId);
    return apiClient.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    }).then((r) => r.data);
  },

  delete: (id: string) =>
    apiClient.delete(`/documents/${id}`).then((r) => r.data),
};

// --- 对话 (Chat) ---

export interface Source {
  document_id: string;
  document_title: string;
  chunk_text: string;
  score?: number;
}

export interface StreamSource {
  text: string;
  score: number;
  document_title: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: StreamSource[];
}

export interface ChatRequest {
  knowledge_base_id: string;
  question: string;
  session_id?: string;
  stream?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  session_id: string;
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

export interface StreamResult {
  sessionId?: string;
  token?: string;
  sources?: StreamSource[];
  done?: boolean;
}

export const chatApi = {
  send: (data: ChatRequest) =>
    apiClient.post<ChatResponse>('/chat', data).then((r) => r.data),

  stream(data: ChatRequest): ReadableStream<StreamResult> {
    let controller: ReadableStreamDefaultController<StreamResult>;
    let cleanup: (() => void) | null = null;

    const stream = new ReadableStream<StreamResult>({
      start(c) {
        controller = c;
        fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...data, stream: true }),
        }).then(async (response) => {
          if (!response.ok) {
            controller.error(new Error(`Stream request failed: ${response.status}`));
            return;
          }
          if (!response.body) {
            controller.error(new Error('No response body'));
            return;
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let currentEvent = '';
          cleanup = () => reader.cancel();

          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });

              while (buffer.includes('\n')) {
                const nlIndex = buffer.indexOf('\n');
                const line = buffer.slice(0, nlIndex);
                buffer = buffer.slice(nlIndex + 1);

                if (line.startsWith('event:')) {
                  currentEvent = line.slice(6).trim();
                } else if (line.startsWith('data:')) {
                  const raw = line.slice(5).trim();
                  if (!raw) continue;

                  if (currentEvent === 'session') {
                    controller.enqueue({ sessionId: raw });
                  } else if (currentEvent === 'message') {
                    try {
                      const parsed = JSON.parse(raw);
                      const token = parsed.answer ?? parsed.content ?? parsed.delta ?? '';
                      if (token) controller.enqueue({ token });
                    } catch {
                      if (raw) controller.enqueue({ token: raw });
                    }
                  } else if (currentEvent === 'sources') {
                    try {
                      const parsed: StreamSource[] = JSON.parse(raw);
                      controller.enqueue({ sources: parsed });
                    } catch {
                      // ignore
                    }
                  } else if (currentEvent === 'done') {
                    controller.enqueue({ done: true });
                  } else {
                    try {
                      const parsed = JSON.parse(raw);
                      const token = parsed.answer ?? parsed.content ?? parsed.delta ?? '';
                      if (token) controller.enqueue({ token });
                    } catch {
                      // ignore
                    }
                  }
                }
              }
            }
          } catch (err) {
            if ((err as Error).name !== 'AbortError') {
              controller.error(err);
            }
          } finally {
            controller.close();
          }
        }).catch((err) => controller.error(err));
      },
      cancel() {
        cleanup?.();
      },
    });
    return stream;
  },

  getHistory: (sessionId: string) =>
    apiClient.get<ChatHistoryMessage[]>(`/chat/history/${sessionId}`).then((r) => r.data),
};
