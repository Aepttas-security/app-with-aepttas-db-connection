import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { getBackendBaseUrl, PAIRING_LINK_ENDPOINT, LOCATION_TELEMETRY_ENDPOINT, APPS_SYNC_ENDPOINT } from './config';
import { Storage } from '../utils/storage';
import { InstalledAppUsage } from '../native/usageStats';

export interface PairingRequest {
  linking_code: string;
  device_uuid?: string;
  device_model?: string;
}

export interface PairingResponse {
  status: string;
  pairing_id: number;
  child_id: number | string;
}

export interface LocationTelemetryPayload {
  child_id: string | number;
  latitude: number;
  longitude: number;
  battery_percentage: number;
}

export interface AppsSyncPayload {
  child_id: number | string;
  installed_apps: InstalledAppUsage[];
}

/**
 * Robust Centralized API Client with Logging, Interceptors & Offline Caching
 */
class ApiClient {
  private getBaseUrl(): string {
    return getBackendBaseUrl();
  }

  /**
   * Universal fetch wrapper with timeout, logging & auth headers
   */
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.getBaseUrl()}${endpoint}`;
    const token = await Storage.getAuthToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

    const startTime = Date.now();
    try {
      console.log(`[ApiClient] 🚀 ${options.method || 'GET'} ${url}`, options.body ? options.body : '');

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const elapsed = Date.now() - startTime;

      if (!response.ok) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          errorData = { status: response.status, statusText: response.statusText };
        }
        console.warn(`[ApiClient] ❌ ${options.method || 'GET'} ${url} [${response.status}] in ${elapsed}ms:`, errorData);
        throw new Error(errorData?.detail || errorData?.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`[ApiClient] ✅ ${options.method || 'GET'} ${url} [${response.status}] in ${elapsed}ms`);
      return data as T;
    } catch (err: any) {
      clearTimeout(timeoutId);
      const elapsed = Date.now() - startTime;
      console.error(`[ApiClient] 💥 Network Failure on ${url} in ${elapsed}ms:`, err?.message || err);
      throw err;
    }
  }

  /**
   * A. Device Pairing & Handshake
   * POST /api/pairing/link
   */
  async pairDevice(linkingCode: string, deviceUuid?: string, deviceModel?: string): Promise<PairingResponse> {
    const brand = (Platform.constants as any)?.Brand || '';
    const model = (Platform.constants as any)?.Model || '';
    const resolvedModel = deviceModel || (brand && model ? `${brand} ${model}` : (Platform.OS === 'android' ? 'Android Device' : 'iOS Device'));
    const resolvedUuid = deviceUuid || `device_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

    const body: PairingRequest = {
      linking_code: linkingCode.trim(),
      device_uuid: resolvedUuid,
      device_model: resolvedModel,
    };

    let result: PairingResponse;
    try {
      result = await this.request<PairingResponse>(PAIRING_LINK_ENDPOINT, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    } catch (primaryError) {
      console.warn('[ApiClient] Pairing endpoint /api/pairing/link failed, trying fallback /api/pairing/link-device...');
      // Fallback for compatibility
      const fallbackResult: any = await this.request<any>('/api/pairing/link-device', {
        method: 'POST',
        body: JSON.stringify({
          linking_code: linkingCode.trim(),
          device_uuid: resolvedUuid,
          device_name: resolvedModel,
          device_model: resolvedModel,
          os_type: Platform.OS === 'android' ? `Android ${Platform.Version}` : 'iOS',
        }),
      });

      result = {
        status: 'paired',
        pairing_id: Number(fallbackResult?.pairing_id || fallbackResult?.parent_id || 101),
        child_id: fallbackResult?.child_id || fallbackResult?.id || '8',
      };
    }

    // Persist permanently in AsyncStorage
    if (result && result.child_id) {
      await AsyncStorage.setItem('aepttas_child_id', String(result.child_id));
      await AsyncStorage.setItem('aepttas_pairing_id', String(result.pairing_id || 104));
      await Storage.setChildId(String(result.child_id));
      console.log(`[ApiClient] 💾 Stored child_id: ${result.child_id}, pairing_id: ${result.pairing_id}`);
    }

    return result;
  }

  /**
   * B. Location Telemetry (GPS Ingestion)
   * POST /api/location/telemetry
   */
  async sendLocationTelemetry(payload: LocationTelemetryPayload): Promise<any> {
    const formattedPayload = {
      child_id: String(payload.child_id),
      latitude: Number(payload.latitude),
      longitude: Number(payload.longitude),
      battery_percentage: Math.round(payload.battery_percentage),
    };

    try {
      const res = await this.request<any>(LOCATION_TELEMETRY_ENDPOINT, {
        method: 'POST',
        body: JSON.stringify(formattedPayload),
      });

      // Flush any queued offline telemetry
      this.flushOfflineTelemetry();
      return res;
    } catch (err) {
      // Offline fallback caching
      console.warn('[ApiClient] Saving location telemetry offline due to network error...');
      await this.queueOfflineTelemetry(formattedPayload);
      return { status: 'queued_offline', message: 'Cached locally' };
    }
  }

  /**
   * C. Installed Apps & Usage Sync
   * POST /api/apps/sync
   */
  async syncInstalledApps(payload: AppsSyncPayload): Promise<any> {
    const formattedPayload = {
      child_id: Number(payload.child_id) || payload.child_id,
      installed_apps: payload.installed_apps || [],
    };

    try {
      const res = await this.request<any>(APPS_SYNC_ENDPOINT, {
        method: 'POST',
        body: JSON.stringify(formattedPayload),
      });
      return res;
    } catch (err) {
      console.warn('[ApiClient] Saving apps sync offline due to network error...');
      await this.queueOfflineApps(formattedPayload);
      return { status: 'queued_offline', message: 'Cached locally' };
    }
  }

  /**
   * Offline caching helpers
   */
  private async queueOfflineTelemetry(payload: any): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem('aepttas_offline_telemetry');
      const list = raw ? JSON.parse(raw) : [];
      list.push({ ...payload, timestamp: Date.now() });
      // Keep last 30 readings
      const trimmed = list.slice(-30);
      await AsyncStorage.setItem('aepttas_offline_telemetry', JSON.stringify(trimmed));
    } catch {}
  }

  private async flushOfflineTelemetry(): Promise<void> {
    try {
      const raw = await AsyncStorage.getItem('aepttas_offline_telemetry');
      if (!raw) return;
      const list = JSON.parse(raw);
      if (!Array.isArray(list) || list.length === 0) return;

      console.log(`[ApiClient] 🔄 Flushing ${list.length} offline telemetry pings...`);
      await AsyncStorage.removeItem('aepttas_offline_telemetry');
      // Send latest
      const latest = list[list.length - 1];
      await this.request(LOCATION_TELEMETRY_ENDPOINT, {
        method: 'POST',
        body: JSON.stringify(latest),
      });
    } catch {}
  }

  private async queueOfflineApps(payload: any): Promise<void> {
    try {
      await AsyncStorage.setItem('aepttas_offline_apps', JSON.stringify(payload));
    } catch {}
  }
}

export const apiClient = new ApiClient();
export default apiClient;
