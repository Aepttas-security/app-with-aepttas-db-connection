import { Platform } from 'react-native';
import { getMalwareBaseUrl, getGeoBaseUrl } from '../config/apiConfig';

export interface DashboardMetrics {
  total_scanned: number;
  threats_detected: number;
  quarantined_files: number;
  device_security_score: number;
}

const getBaseUrl = () => getMalwareBaseUrl();
const getGeoUrl = () => getGeoBaseUrl();

const originalFetch = globalThis.fetch;
const fetch = async (url: string | Request, options: any = {}) => {
  if (options && options.signal) {
    return originalFetch(url, options);
  }
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await originalFetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
};

export const ScannerRepository = {
  /**
   * Uploads and scans the APK by sending it to the backend server.
   * Saves the result to the cloud PostgreSQL database.
   */
  async scanApk(filePath: string): Promise<any> {
    const fileName = filePath.substring(filePath.lastIndexOf('/') + 1);
    
    // Create multipart form-data payload
    const formData = new FormData();
    formData.append('file', {
      uri: Platform.OS === 'android' ? `file://${filePath}` : filePath,
      name: fileName,
      type: 'application/vnd.android.package-archive',
    } as any);

    // NOTE: Do NOT pass manual 'Content-Type': 'multipart/form-data' header.
    // In JS/React Native fetch, passing FormData without explicit Content-Type allows fetch
    // to automatically inject the correct boundary header so PostgreSQL backend can parse form fields.
    const response = await fetch(`${getBaseUrl()}/api/scan`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to scan file on server. Status: ${response.status}`);
    }

    return response.json();
  },

  async getScanDetails(scanId: number): Promise<any> {
    const response = await fetch(`${getBaseUrl()}/api/scans/${scanId}`);
    if (!response.ok) throw new Error('Failed to retrieve scan details.');
    return response.json();
  },

  async listScans(): Promise<any[]> {
    const response = await fetch(`${getBaseUrl()}/api/scans`);
    if (!response.ok) throw new Error('Failed to retrieve scans list.');
    return response.json();
  },

  async listQuarantinedApks(): Promise<any[]> {
    const response = await fetch(`${getBaseUrl()}/api/quarantine`);
    if (!response.ok) throw new Error('Failed to retrieve quarantined files.');
    return response.json();
  },

  async listScanHistory(): Promise<any[]> {
    const response = await fetch(`${getBaseUrl()}/api/history`);
    if (!response.ok) throw new Error('Failed to retrieve scan history.');
    return response.json();
  },

  /**
   * Triggers the quarantine action on the backend server.
   */
  async quarantineFile(scanId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/scans/${scanId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'quarantine' }),
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  /**
   * Triggers file restoration on the backend server.
   */
  async restoreFile(quarantineId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/quarantine/${quarantineId}/restore`, {
        method: 'POST',
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  /**
   * Permanently deletes the file on the backend server.
   */
  async deletePermanently(quarantineId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/quarantine/${quarantineId}/delete`, {
        method: 'POST',
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  /**
   * Direct deletion of a scanned file.
   */
  async deleteScannedFileDirectly(scanId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/scans/${scanId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'delete' }),
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  /**
   * Ignores the threat.
   */
  async ignoreThreat(scanId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/scans/${scanId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'ignore' }),
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  },

  /**
   * Submits the quarantined file for cloud analysis.
   */
  async submitForAnalysis(quarantineId: number): Promise<boolean> {
    try {
      const response = await fetch(`${getBaseUrl()}/api/quarantine/${quarantineId}/analyze`, {
        method: 'POST',
      });
      return response.ok;
    } catch (e) {
      console.error(e);
      return false;
    }
  }
};

export const DashboardRepository = {
  /**
   * Retrieves dashboard aggregation metrics directly from the server.
   */
  async getDashboardMetrics(): Promise<any> {
    const response = await fetch(`${getBaseUrl()}/api/dashboard`);
    if (!response.ok) throw new Error('Failed to retrieve dashboard metrics.');
    return response.json();
  },

  /**
   * Retrieves active warnings/alerts.
   */
  async getActiveAlerts(): Promise<any[]> {
    const response = await fetch(`${getBaseUrl()}/api/alerts`);
    if (!response.ok) throw new Error('Failed to retrieve active alerts.');
    return response.json();
  }
};

export const GeolocationRepository = {
  async getCurrentLocation(): Promise<any> {
    const response = await fetch(`${getGeoUrl()}/current`);
    if (!response.ok) throw new Error('Failed to retrieve current location.');
    return response.json();
  },

  async updateCurrentLocation(payload: {
    latitude: number;
    longitude: number;
    ip?: string;
    is_mock_location?: boolean;
    accuracy?: number;
    provider?: string;
    timestamp?: string;
    device_id?: string;
  }): Promise<any> {
    const response = await fetch(`${getGeoUrl()}/current`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to update current location.');
    return response.json();
  },

  async getLocationHistory(): Promise<any[]> {
    const response = await fetch(`${getGeoUrl()}/history`);
    if (!response.ok) throw new Error('Failed to retrieve location history.');
    const json = await response.json();
    return json.history || [];
  },

  async deleteHistoryEntry(): Promise<any> {
    const response = await fetch(`${getGeoUrl()}/history`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to clear location history.');
    return response.json();
  },

  async getNearbyPlaces(payload: { latitude: number; longitude: number; radius_km: number }): Promise<any[]> {
    const response = await fetch(`${getGeoUrl()}/nearby`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to fetch nearby places.');
    const json = await response.json();
    return json.places || [];
  }
};
