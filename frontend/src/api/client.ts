import type {
  UserSession, ClusterSummary, QueueTreeResponse,
  DraftQueueItem, DiffItem, TokenResponse
} from '../types';

const API_BASE = '/api';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function setToken(token: string) {
  localStorage.setItem('access_token', token);
}

function clearToken() {
  localStorage.removeItem('access_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearToken();
    throw new Error('UNAUTHORIZED');
  }

  if (!resp.ok) {
    const errBody = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(errBody.detail || `HTTP ${resp.status}`);
  }

  return resp.json();
}

export const api = {
  async login(username: string, password: string): Promise<UserSession> {
    const data = await request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setToken(data.access_token);
    return data.user;
  },

  async getMe(): Promise<UserSession> {
    return request<UserSession>('/auth/me');
  },

  async logout(): Promise<void> {
    await request('/auth/logout', { method: 'POST' }).catch(() => {});
    clearToken();
  },

  async getClusters(): Promise<ClusterSummary[]> {
    return request<ClusterSummary[]>('/clusters/');
  },

  async getQueueTree(clusterId: string): Promise<QueueTreeResponse> {
    return request<QueueTreeResponse>(`/clusters/${clusterId}/queues`);
  },

  async validateDraft(clusterId: string, queues: DraftQueueItem[], partition: string) {
    return request<{ is_valid: boolean; balances: any[]; errors: string[]; warnings: string[] }>(
      `/clusters/${clusterId}/validate`,
      {
        method: 'POST',
        body: JSON.stringify({ cluster_id: clusterId, selected_partition: partition, queues }),
      }
    );
  },

  async getDiff(clusterId: string, queues: DraftQueueItem[], partition: string) {
    return request<{ cluster_id: string; has_changes: boolean; diffs: DiffItem[] }>(
      `/clusters/${clusterId}/diff`,
      {
        method: 'POST',
        body: JSON.stringify({ cluster_id: clusterId, selected_partition: partition, queues }),
      }
    );
  },

  async generateXml(clusterId: string, queues: DraftQueueItem[], comment?: string, resourceModeOverride?: string) {
    return request<{
      cluster_id: string; filename: string; xml_content: string;
      applied_by: string; generated_at: string; instructions: string;
    }>(
      `/clusters/${clusterId}/generate-xml`,
      {
        method: 'POST',
        body: JSON.stringify({
          cluster_id: clusterId,
          queues,
          proposal_comment: comment,
          resource_mode_override: resourceModeOverride,
        }),
      }
    );
  },
};
