// src/services/api.ts
import { CONFIG } from '../constants/Config';

const API_URL = CONFIG.API_URL;

export interface DashboardStats {
  total_calls_today: number;
  spam_calls_detected: number;
  blocked_calls_count: number;
  security_score: number;
  recent_alerts: Alert[];
}

export interface Alert {
  id: number;
  call_id: number | null;
  caller_number: string;
  alert_type: string;
  threat_level: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface Call {
  id: number;
  caller_number: string;
  caller_name: string | null;
  receiver_number: string;
  duration: number;
  call_type: string;
  risk_score: number;
  status: string;
  threat_level: string;
  is_blocked: boolean;
  created_at: string;
}

export interface Settings {
  id: number;
  auto_block_calls: boolean;
  notifications_enabled: boolean;
  detection_sensitivity: number;
  privacy_mode: boolean;
  auto_block_threshold: number;
}

export interface BlockedNumber {
  id: number;
  phone_number: string;
  caller_name: string | null;
  block_reason: string;
  block_date: string;
  is_permanent: boolean;
}

export interface CallerLookupResult {
  exists: boolean;
  caller_name: string;
  carrier: string;
  location: string;
  risk_score: number;
  is_spam: boolean;
  is_blocked: boolean;
  threat_level: string;
  report_count: number;
  [key: string]: any;
}

class ApiService {
  private baseUrl: string;
  private apiKey: string;

  constructor() {
    this.baseUrl = API_URL;
    this.apiKey = CONFIG.API_KEY;
    console.log("📡 API Service initialized with base URL:", this.baseUrl);
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      "X-API-Key": this.apiKey,
      "ngrok-skip-browser-warning": "true",
      ...options.headers,
    };

    try {
      console.log("🌐 Fetching:", url);
      const response = await fetch(url, { ...options, headers });

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}`);
      }

      const data = await response.json();
      console.log("✅ Response from", endpoint, ":", data);
      return data;
    } catch (error) {
      console.error(`❌ API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  async getDashboard(): Promise<DashboardStats> {
    return this.request("/api/dashboard");
  }

  async login(email: string, password: string): Promise<any> {
    return this.request("/api/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async saveCallHistory(data: any): Promise<any> {
    return this.request('/api/live-call/analyze', {
      method: 'POST',
      body: JSON.stringify({
        caller_number: data.phoneNumber,
        caller_name: data.callerName,
        call_type: data.status.includes('OUTGOING') ? 'OUTGOING' : 'INCOMING',
        duration: data.duration || 0,
        risk_score: data.riskScore || 0,
        user_id: 1
      }),
    });
  }

  async getCallHistory(): Promise<Call[]> {
    return this.request("/api/calls");
  }

  async getSpamLog(): Promise<any[]> {
    return this.request("/api/spam-log");
  }

  async getBlockedNumbers(): Promise<BlockedNumber[]> {
    return this.request("/api/blocked");
  }

  async getBlockedNumbersList(): Promise<any[]> {
    return this.request("/api/blocked");
  }

  async blockNumber(data: any): Promise<any> {
    return this.request("/api/blocked", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  async unblockCaller(phone: string): Promise<any> {
    const clean = phone.replace(/[^\d+]/g, '');
    return this.request(`/api/blocked/${clean}`, {
      method: "DELETE"
    });
  }

  async lookupCaller(phoneNumber: string): Promise<any> {
    const cleanNumber = phoneNumber.replace(/[^\d+]/g, '');
    return this.request(`/api/callers/lookup/${cleanNumber}`);
  }

  async searchNumber(phoneNumber: string): Promise<CallerLookupResult> {
    const res: any = await this.lookupCaller(phoneNumber);
    return {
        exists: res?.exists || false,
        caller_name: res?.caller_name || 'Unknown Caller',
        carrier: res?.carrier || 'Network Provider',
        location: res?.location || 'India',
        risk_score: res?.risk_score || 0,
        is_spam: res?.is_spam || false,
        is_blocked: res?.is_blocked || false,
        threat_level: res?.risk_score >= 75 ? 'Critical' : res?.risk_score >= 40 ? 'Suspicious' : 'Safe',
        report_count: res?.total_reports || 0
    };
  }

  async getSettings(): Promise<Settings> {
    return this.request("/api/settings");
  }

  async updateSettings(data: Partial<Settings>): Promise<any> {
    return this.request("/api/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async logError(data: any): Promise<any> {
    return this.request("/api/admin/logs", {
      method: "POST",
      body: JSON.stringify(data),
    }).catch(() => {});
  }

  async markAlertRead(alertId: number): Promise<any> {
    return this.request(`/api/alerts/${alertId}/read`, { method: "PUT" });
  }

  async healthCheck(): Promise<{ status: string }> {
    return this.request("/api/health");
  }

  async createReport(data: any): Promise<any> {
    return this.request("/api/reports", {
      method: "POST",
      body: JSON.stringify(data),
    }).catch(() => {});
  }

  async getSpamCalls(): Promise<any[]> {
    return this.request("/api/spam-log");
  }

  async addContact(data: any): Promise<any> {
    return this.request("/api/contacts", {
      method: "POST",
      body: JSON.stringify(data),
    }).catch(() => {});
  }

  async getCallerInfo(phoneNumber: string): Promise<any> {
    return this.lookupCaller(phoneNumber);
  }
}

export default new ApiService();
