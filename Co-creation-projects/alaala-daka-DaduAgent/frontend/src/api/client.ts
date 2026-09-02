import type { ModelEntry, ModelInput, ModelListResponse, EmbeddingConfig, RerankerConfig, AuxModelUpdate, ReflectionEntry, ReflectionCreate, ReflectionUpdate } from '../types/config';
import type { ChatAttachment } from '../types/chat';

// fetch wrapper for REST API
const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const apiClient = {
  // ── Sessions ──
  listSessions: () => request<{ sessions: import('../types/session').Session[] }>('/sessions'),
  createSession: (name: string) =>
    request<{ session_id: string }>('/sessions', { method: 'POST', body: JSON.stringify({ name }) }),
  getSession: (id: string) => request<import('../types/session').Session>(`/sessions/${id}`),
  deleteSession: (id: string) =>
    request<{ deleted: string }>(`/sessions/${id}`, { method: 'DELETE' }),
  getMessages: (id: string, offset = 0, limit = 50) =>
    request<{ messages: unknown[]; total: number; todos?: import('../types/chat').TodoItem[] | null }>(`/sessions/${id}/messages?offset=${offset}&limit=${limit}`),

  // ── Config ──
  getConfig: (name: string) => request<{ config: string; values: Record<string, unknown> }>(`/config/${name}`),
  updateConfig: (name: string, values: Record<string, unknown>) =>
    request<{ config: string; updated: string[] }>(`/config/${name}`, {
      method: 'PUT',
      body: JSON.stringify({ values }),
    }),

  // ── Models ──
  listModels: () => request<ModelListResponse>('/models'),
  addModel: (input: ModelInput) =>
    request<{ created: string; active: string }>('/models', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  updateModel: (name: string, patch: Partial<Omit<ModelEntry, 'name'>>) =>
    request<{ updated: string }>(`/models/${encodeURIComponent(name)}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  deleteModel: (name: string) =>
    request<{ deleted: string; active: string }>(`/models/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  setActiveModel: (name: string) =>
    request<{ active: string; model_info?: Record<string, unknown> }>('/models/active', {
      method: 'PUT',
      body: JSON.stringify({ name }),
    }),
  getEmbeddingConfig: () => request<{ embedding: EmbeddingConfig }>('/models/embedding'),
  updateEmbeddingConfig: (patch: AuxModelUpdate) =>
    request<{ updated: string; model_info?: Record<string, unknown>; warning?: string }>('/models/embedding', {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  getRerankerConfig: () => request<{ reranker: RerankerConfig }>('/models/reranker'),
  updateRerankerConfig: (patch: AuxModelUpdate) =>
    request<{ updated: string; model_info?: Record<string, unknown>; warning?: string }>('/models/reranker', {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),

  // ── Chat upload（多部分表单，不能走 JSON 化的 request）──
  uploadChatFile: async (file: File): Promise<ChatAttachment> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE}/files/chat-upload`, { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || '上传失败');
    }
    const data = (await res.json()) as { file_name: string; path: string; size: number };
    return { name: data.file_name, path: data.path, size: data.size };
  },

  // ── Files / RAG ──
  listRagFiles: () => request<{ files: unknown[]; total: number }>('/files/rag-files'),
  getRagStatus: () =>
    request<{ file_count: number; total_chunks: number; vector_count: number; supported_extensions: string[] }>('/files/rag-status'),
  deleteRagFile: (name: string) =>
    request<{ deleted: string }>(`/files/rag-files/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // ── Reflections（反思笔记）──
  listReflections: () => request<{ reflections: ReflectionEntry[] }>('/reflections'),
  createReflection: (input: ReflectionCreate) =>
    request<{ reflection: ReflectionEntry }>('/reflections', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  updateReflection: (refId: string, patch: ReflectionUpdate) =>
    request<{ reflection: ReflectionEntry }>(`/reflections/${encodeURIComponent(refId)}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  deleteReflection: (refId: string) =>
    request<{ deleted: string }>(`/reflections/${encodeURIComponent(refId)}`, { method: 'DELETE' }),

  // ── Tools ──
  listTools: () => request<{ tools: unknown[] }>('/tools'),
  getTodos: () => request<{ todos: unknown[]; counter: number }>('/tools/todos'),
  searchReflections: (q: string) =>
    request<{ query: string; results: string }>(`/tools/reflections/search?q=${encodeURIComponent(q)}`),

  // ── Health ──
  health: () => request<{ status: string }>('/health'),
};
