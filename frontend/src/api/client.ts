import axios, { InternalAxiosRequestConfig } from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Token management ---

const TOKEN_KEY = 'access_token';

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Auto-attach Bearer token and handle 401 refresh
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.get();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let refreshQueue: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          });
        });
      }
      original._retry = true;
      isRefreshing = true;
      try {
        const refresh = localStorage.getItem('refresh_token');
        if (refresh) {
          const { data } = await axios.post<{ access_token: string; refresh_token: string }>(
            '/api/v1/auth/refresh',
            null,
            { params: { refresh_token: refresh } }
          );
          tokenStorage.set(data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          refreshQueue.forEach((cb) => cb(data.access_token));
          refreshQueue = [];
          return apiClient(original);
        }
      } catch {
        tokenStorage.clear();
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(err);
  }
);

// --- 认证 (Auth) ---

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<{ access_token: string; refresh_token: string }>('/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    apiClient.post('/auth/register', data).then((r) => r.data),

  me: () =>
    apiClient.get('/auth/me').then((r) => r.data),
};

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

export interface KnowledgeBasesResponse {
  knowledge_bases: KnowledgeBase[];
}

export const knowledgeBaseApi = {
  list: () =>
    apiClient.get<KnowledgeBasesResponse>('/knowledge-bases').then((r) => r.data),

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

export interface DocumentsResponse {
  documents: Document[];
  total: number;
}

export interface DocumentListParams {
  knowledge_base_id?: string;
  page?: number;
  page_size?: number;
}

export const documentApi = {
  list: (params?: DocumentListParams) =>
    apiClient.get<DocumentsResponse>('/documents', { params }).then((r) => r.data.documents),

  upload: (knowledgeBaseId: string, file: File, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post<Document>('/documents/upload', formData, {
      params: { knowledge_base_id: knowledgeBaseId },
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
  message: string;
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

export interface SessionSummary {
  session_id: string;
  knowledge_base_id: string;
  message_count: number;
  first_message: string | null;
  last_message: string | null;
  created_at: string;
  updated_at: string;
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
          headers: {
            'Content-Type': 'application/json',
            ...(tokenStorage.get() ? { Authorization: `Bearer ${tokenStorage.get()}` } : {}),
          },
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

  listSessions: (knowledgeBaseId?: string) =>
    apiClient.get<{ sessions: SessionSummary[] }>('/chat/sessions', {
      params: knowledgeBaseId ? { knowledge_base_id: knowledgeBaseId } : undefined,
    }).then((r) => r.data.sessions),
};
