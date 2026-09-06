/**
 * ResearchFlow AI — API Client
 * Communicates with FastAPI backend service endpoints
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Document {
  id: string;
  filename: string;
  original_name: string;
  file_type: string;
  file_size: number;
  upload_timestamp: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  num_chunks?: number;
  vector_ids?: string[];
  error_message?: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  size: number;
}

export interface DocumentStats {
  total_documents: number;
  completed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_chunks: number;
}

export interface SourceCitation {
  id: string;
  document_id: string;
  document_name: string;
  content: string;
  page_number?: number;
  similarity_score: number;
  chunk_id?: string;
}

export interface ReasoningStep {
  step: string;
  status: 'SUCCESS' | 'WARNING' | 'INFO' | 'ERROR';
  details: string;
  score?: number;
  timestamp: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SourceCitation[];
  reasoning?: ReasoningStep[];
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  query_intent?: string;
  is_hallucination_free?: boolean;
  is_answer_relevant?: boolean;
  execution_time_ms?: number;
}

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  version: string;
  timestamp: string;
  services: {
    postgres: { status: string; latency_ms: number; total_documents?: number };
    redis: { status: string; latency_ms: number };
    qdrant: { status: string; latency_ms: number; total_vectors?: number };
    llm: { status: string; latency_ms: number; provider?: string };
  };
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || `Upload error: ${res.status}`);
  }

  return res.json();
}

export async function fetchDocuments(page = 1, size = 20, query = ''): Promise<DocumentListResponse> {
  const params = new URLSearchParams({ page: page.toString(), size: size.toString() });
  if (query) params.append('query', query);

  const res = await fetch(`${API_BASE}/documents?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function fetchDocumentStats(): Promise<DocumentStats> {
  const res = await fetch(`${API_BASE}/documents/stats`);
  if (!res.ok) throw new Error('Failed to fetch document stats');
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  selectedDocIds: string[] = [],
  k: number = 4
): Promise<ChatMessage> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      document_ids: selectedDocIds,
      k,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat request failed' }));
    throw new Error(err.detail || 'Failed to send message');
  }

  return res.json();
}

export async function fetchChatHistory(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/chat/history/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch chat history');
  const data = await res.json();
  return data.messages || [];
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to check health');
  return res.json();
}
