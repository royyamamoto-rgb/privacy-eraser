/**
 * API client for Privacy Eraser backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
  token?: string;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  }

  async fetch<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`;
    const token = options.token || this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
      throw new Error(error.detail || 'An error occurred');
    }

    return response.json();
  }

  // Auth endpoints
  async register(email: string, password: string) {
    const data = await this.fetch<{ access_token: string; user: any }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async logout() {
    this.clearToken();
  }

  // User endpoints
  async getProfile() {
    return this.fetch<any>('/users/me');
  }

  async updateProfile(data: any) {
    return this.fetch<any>('/users/me/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Broker endpoints
  async listBrokers() {
    return this.fetch<any[]>('/brokers');
  }

  async getDashboardStats() {
    return this.fetch<any>('/brokers/stats');
  }

  async getExposures() {
    return this.fetch<any[]>('/brokers/exposures');
  }

  async startScan() {
    return this.fetch<any>('/brokers/scan', {
      method: 'POST',
    });
  }

  // Request endpoints
  async listRequests() {
    return this.fetch<any[]>('/requests');
  }

  async getRequestStats() {
    return this.fetch<any>('/requests/stats');
  }

  async createRequest(exposureId: string, requestType: string = 'opt_out') {
    return this.fetch<any>('/requests', {
      method: 'POST',
      body: JSON.stringify({ exposure_id: exposureId, request_type: requestType }),
    });
  }

  async submitRequest(requestId: string) {
    return this.fetch<any>(`/requests/${requestId}/submit`, {
      method: 'POST',
    });
  }

  async completeRequest(requestId: string) {
    return this.fetch<any>(`/requests/${requestId}/complete`, {
      method: 'POST',
    });
  }

  // Monitoring endpoints
  async getAlerts(unreadOnly: boolean = false) {
    return this.fetch<any[]>(`/monitoring/alerts?unread_only=${unreadOnly}`);
  }

  async getAlertStats() {
    return this.fetch<any>('/monitoring/alerts/stats');
  }

  async markAlertRead(alertId: string) {
    return this.fetch<any>(`/monitoring/alerts/${alertId}/read`, {
      method: 'POST',
    });
  }

  async markAllAlertsRead() {
    return this.fetch<any>('/monitoring/alerts/read-all', {
      method: 'POST',
    });
  }
}

export const api = new ApiClient(API_URL);
export default api;
