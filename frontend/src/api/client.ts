import {
  AgentResponse,
  Client,
  CompareResponse,
  FeedbackRequest,
  HealthResponse,
  ImportRequest,
  ImportResponse,
  ObservationItem,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getHealth: (): Promise<HealthResponse> => request<HealthResponse>('/api/health'),

  getClients: (): Promise<Client[]> => request<Client[]>('/api/clients'),

  createClient: (client: Omit<Client, 'id'> & { id?: string }): Promise<Client> =>
    request<Client>('/api/clients', {
      method: 'POST',
      body: JSON.stringify(client),
    }),

  respond: (payload: {
    client_id: string;
    incoming_text: string;
    memory_enabled?: boolean;
    compare?: boolean;
  }): Promise<AgentResponse | CompareResponse> =>
    request<AgentResponse | CompareResponse>('/api/respond', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  submitFeedback: (payload: FeedbackRequest): Promise<{ status: string; feedback: Record<string, unknown> }> =>
    request<{ status: string; feedback: Record<string, unknown> }>('/api/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  importHistory: (payload: ImportRequest): Promise<ImportResponse> =>
    request<ImportResponse>('/api/import', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getObservations: (clientId: string): Promise<ObservationItem[]> =>
    request<ObservationItem[]>(`/api/memory/observations?client_id=${encodeURIComponent(clientId)}`),
};
