import { Platform } from 'react-native';

/**
 * Central API Configuration for Parent Control Backend
 * - Dynamically extracts Host LAN IP from Expo environment when running on physical devices
 * - Android Emulator uses 10.0.2.2 to reach host machine localhost
 * - Web / Desktop uses 127.0.0.1 or localhost
 * - Port 8000 is the running FastAPI server
 */
const getHostFromExpo = (): string | null => {
  try {
    const g = globalThis as any;
    const constants = g?.expo?.modules?.ExponentConstants || g?.NativeModules?.ExponentConstants;
    const hostUri = constants?.debuggerHost || constants?.manifest?.debuggerHost || constants?.manifest2?.extra?.expoGo?.developer?.tool;
    if (hostUri) {
      const ip = String(hostUri).split(':')[0];
      if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
        return ip;
      }
    }
  } catch { }
  return null;
};


export const PRODUCTION_URL = 'https://aepttas-backend.onrender.com';
const expoIp = getHostFromExpo();
export const DEFAULT_HOST = expoIp || '127.0.0.1';
const CANDIDATE_HOSTS = [PRODUCTION_URL];
const DEFAULT_PORT = '5000';

let customBaseUrl: string | null = null;
let resolvedWorkingBaseUrl: string = PRODUCTION_URL;

export const getUnifiedBaseUrl = (): string => {
  if (customBaseUrl) {
    return customBaseUrl;
  }
  return resolvedWorkingBaseUrl;
};

export const getFallbackUrls = (): string[] => {
  return [PRODUCTION_URL];
};

export const setResolvedHost = (url: string) => {
  resolvedWorkingBaseUrl = url.replace(/\/+$/, '');
};

const getLocalBaseUrl = (port: number): string => {
  if (customBaseUrl) return customBaseUrl;
  return `http://127.0.0.1:${port}`;
};

export const getParentalBaseUrl = (): string => {
  return getLocalBaseUrl(8005);
};

export const getApiBaseUrl = (): string => {
  return getLocalBaseUrl(8005);
};

export const getMalwareBaseUrl = (): string => {
  return getLocalBaseUrl(8001);
};

export const getAuthBaseUrl = (): string => {
  return getLocalBaseUrl(8002);
};

export const getGeoBaseUrl = (): string => {
  return getLocalBaseUrl(8003);
};

export const getVulnBaseUrl = (): string => {
  return getLocalBaseUrl(8000);
};

export const getCallerBaseUrl = (): string => {
  return getLocalBaseUrl(8004);
};

export const setApiBaseUrl = (url: string) => {
  customBaseUrl = url.trim().replace(/\/+$/, '');
};

export const API_BASE_URL = `http://${DEFAULT_HOST}:${DEFAULT_PORT}`;
