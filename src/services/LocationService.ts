import { NativeModules, PermissionsAndroid, Platform } from 'react-native';
import Geolocation from 'react-native-geolocation-service';
import { GeolocationRepository } from '../data/repository';

export interface UserLiveLocation {
  latitude: number;
  longitude: number;
  latitudeStr: string;
  longitudeStr: string;
  accuracy: number;
  city: string;
  region: string;
  country: string;
  countryCode: string;
  isp: string;
  ip: string;
  provider: string;
  isMock: boolean;
  threatLevel: 'Safe' | 'Suspicious' | 'High Risk';
  timestamp: string;
  source: 'native_gps' | 'network' | 'ip_lookup';
}

const { LocationModule } = NativeModules;

class LocationService {
  /**
   * Request Android runtime location permissions.
   */
  async requestLocationPermission(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;

    try {
      const granted = await PermissionsAndroid.requestMultiple([
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION,
      ]);

      const fineGranted =
        granted[PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION] ===
        PermissionsAndroid.RESULTS.GRANTED;
      const coarseGranted =
        granted[PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION] ===
        PermissionsAndroid.RESULTS.GRANTED;

      return fineGranted || coarseGranted;
    } catch (err) {
      console.warn('[LocationService] Permission request error:', err);
      return false;
    }
  }

  /**
   * Check if location services (GPS or Network) are enabled on the device.
   */
  async isLocationEnabled(): Promise<boolean> {
    if (Platform.OS === 'android' && LocationModule?.isLocationEnabled) {
      try {
        return await LocationModule.isLocationEnabled();
      } catch {
        return false;
      }
    }
    return true;
  }

  /**
   * Obtains live GPS position using react-native-geolocation-service with enableHighAccuracy: true
   */
  private getGpsViaGeolocationService(): Promise<{
    latitude: number;
    longitude: number;
    accuracy: number;
    speed?: number;
    altitude?: number;
    provider?: string;
    isMock?: boolean;
    timestamp?: number;
  }> {
    return new Promise((resolve, reject) => {
      Geolocation.getCurrentPosition(
        (pos) => {
          const isMock = Boolean((pos as any)?.mocked || (pos as any)?.isFromMockProvider);
          resolve({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy || 10,
            speed: pos.coords.speed || 0,
            altitude: pos.coords.altitude || 0,
            provider: 'GPS',
            isMock,
            timestamp: pos.timestamp,
          });
        },
        (err) => {
          reject(err);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 5000,
          showLocationDialog: true,
          forceRequestLocation: true,
        }
      );
    });
  }

  /**
   * Detects the user's actual live location:
   * 1. Uses react-native-geolocation-service with enableHighAccuracy: true.
   * 2. Falls back to Android native LocationModule (hardware GPS provider).
   * 3. Enriches native coordinates with reverse geocoding & ISP/IP.
   * 4. Syncs the live detected coordinate with the backend Geolocation repository.
   * 5. Does NOT use hardcoded Bangalore coordinates as the actual location!
   */
  async detectLiveLocation(): Promise<UserLiveLocation> {
    let gpsResult: any = null;
    const hasPermission = await this.requestLocationPermission();

    // 1. Primary: Try react-native-geolocation-service with high accuracy
    if (hasPermission) {
      try {
        gpsResult = await this.getGpsViaGeolocationService();
        console.log('[LocationService] Live GPS acquired via react-native-geolocation-service:', gpsResult);
      } catch (geoErr) {
        console.log('[LocationService] react-native-geolocation-service notice, trying native LocationModule:', geoErr);
      }
    }

    // 2. Secondary fallback: Native Android LocationModule (hardware GPS / network listener)
    if (!gpsResult && hasPermission && Platform.OS === 'android' && LocationModule?.getCurrentLocation) {
      try {
        const native = await LocationModule.getCurrentLocation();
        if (native && typeof native.latitude === 'number' && typeof native.longitude === 'number') {
          gpsResult = {
            latitude: native.latitude,
            longitude: native.longitude,
            accuracy: native.accuracy || 10,
            speed: native.speed || 0,
            provider: native.provider ? native.provider.toUpperCase() : 'GPS',
            isMock: Boolean(native.isMock),
            timestamp: native.timestamp || Date.now(),
          };
          console.log('[LocationService] Live GPS acquired via LocationModule:', gpsResult);
        }
      } catch (nativeErr) {
        console.log('[LocationService] Native LocationModule notice:', nativeErr);
      }
    }

    let detected: UserLiveLocation;

    if (gpsResult && typeof gpsResult.latitude === 'number' && typeof gpsResult.longitude === 'number') {
      const lat = gpsResult.latitude;
      const lon = gpsResult.longitude;
      const isMock = Boolean(gpsResult.isMock);

      // Resolve human-readable place name & network details dynamically
      const meta = await this.enrichCoordinates(lat, lon);

      detected = {
        latitude: lat,
        longitude: lon,
        latitudeStr: `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}`,
        longitudeStr: `${Math.abs(lon).toFixed(4)}° ${lon >= 0 ? 'E' : 'W'}`,
        accuracy: Math.round(gpsResult.accuracy || 10),
        city: meta.city || `Live Location (${Math.abs(lat).toFixed(2)}°)`,
        region: meta.region || 'Active Region',
        country: meta.country || 'Detected Region',
        countryCode: meta.countryCode || '',
        isp: meta.isp || 'Mobile Cellular / GPS',
        ip: meta.ip || '127.0.0.1',
        provider: gpsResult.provider || 'GPS',
        isMock,
        threatLevel: isMock ? 'High Risk' : 'Safe',
        timestamp: new Date().toISOString(),
        source: 'native_gps',
      };
    } else {
      // 3. Fallback to live IP-based geolocation lookup (dynamic, NOT hardcoded Bangalore)
      detected = await this.fetchIpLocationFallback();
    }

    // 4. Sync detected live location with the backend server via POST /api/v1/geolocation/current
    this.syncWithBackend(detected).catch(err => {
      console.log('[LocationService] Backend sync notice:', err);
    });

    return detected;
  }


  /**
   * Enriches GPS coordinates with human-readable location name & IP info
   */
  private async enrichCoordinates(lat: number, lon: number): Promise<{
    city?: string;
    region?: string;
    country?: string;
    countryCode?: string;
    isp?: string;
    ip?: string;
  }> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3500);

    try {
      // Try reverse geocoding via OpenStreetMap Nominatim
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=14&addressdetails=1`,
        {
          headers: { 'User-Agent': 'AePttasShield-GeoTracker/1.0' },
          signal: controller.signal,
        }
      );
      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        const addr = data.address || {};
        const city =
          addr.city ||
          addr.town ||
          addr.village ||
          addr.suburb ||
          addr.municipality ||
          addr.county ||
          'Live Node';
        const region = addr.state || addr.province || '';
        const country = addr.country || 'Detected Country';
        const countryCode = addr.country_code ? addr.country_code.toUpperCase() : '';

        // Also fetch public IP & ISP asynchronously or quickly
        const ipInfo = await this.fetchQuickIpInfo();

        return {
          city,
          region,
          country,
          countryCode,
          isp: ipInfo.isp,
          ip: ipInfo.ip,
        };
      }
    } catch {
      clearTimeout(timeout);
    }

    // Fallback to quick IP info if reverse geocoding fails
    return await this.fetchQuickIpInfo();
  }

  /**
   * Quick IP and ISP lookup
   */
  private async fetchQuickIpInfo(): Promise<{ ip?: string; isp?: string; city?: string; country?: string }> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const res = await fetch('https://ipapi.co/json/', { signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok) {
        const data = await res.json();
        return {
          ip: data.ip,
          isp: data.org || data.asn || 'Internet Service Provider',
          city: data.city,
          country: data.country_name,
        };
      }
    } catch {
      clearTimeout(timeout);
    }
    return { ip: '127.0.0.1', isp: 'Active Network Gateway' };
  }

  /**
   * Fast IP-based geolocation fallback when GPS hardware fix is not available yet
   */
  private async fetchIpLocationFallback(): Promise<UserLiveLocation> {
    // Attempt 1: ipapi.co
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);
      const res = await fetch('https://ipapi.co/json/', { signal: controller.signal });
      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        const lat = parseFloat(data.latitude);
        const lon = parseFloat(data.longitude);

        if (!isNaN(lat) && !isNaN(lon)) {
          return {
            latitude: lat,
            longitude: lon,
            latitudeStr: `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}`,
            longitudeStr: `${Math.abs(lon).toFixed(4)}° ${lon >= 0 ? 'E' : 'W'}`,
            accuracy: 50,
            city: data.city || 'Detected City',
            region: data.region || 'Detected Region',
            country: data.country_name || 'Detected Country',
            countryCode: data.country_code || '',
            isp: data.org || data.asn || 'Broadband ISP',
            ip: data.ip || '127.0.0.1',
            provider: 'IP GEOLOCATION',
            isMock: false,
            threatLevel: 'Safe',
            timestamp: new Date().toISOString(),
            source: 'ip_lookup',
          };
        }
      }
    } catch (err) {
      console.log('[LocationService] ipapi.co notice, trying freeipapi:', err);
    }

    // Attempt 2: freeipapi.com
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3500);
      const res = await fetch('https://freeipapi.com/api/json', { signal: controller.signal });
      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        const lat = parseFloat(data.latitude);
        const lon = parseFloat(data.longitude);

        if (!isNaN(lat) && !isNaN(lon)) {
          return {
            latitude: lat,
            longitude: lon,
            latitudeStr: `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}`,
            longitudeStr: `${Math.abs(lon).toFixed(4)}° ${lon >= 0 ? 'E' : 'W'}`,
            accuracy: 100,
            city: data.cityName || 'Detected City',
            region: data.regionName || 'Detected Region',
            country: data.countryName || 'Detected Country',
            countryCode: data.countryCode || '',
            isp: 'Internet Gateway',
            ip: data.ipAddress || '127.0.0.1',
            provider: 'IP GEOLOCATION',
            isMock: false,
            threatLevel: 'Safe',
            timestamp: new Date().toISOString(),
            source: 'ip_lookup',
          };
        }
      }
    } catch (err) {
      console.log('[LocationService] freeipapi notice, trying backend current API:', err);
    }

    // Attempt 3: Query backend /api/v1/geolocation/current API
    try {
      const backendRes = await GeolocationRepository.getCurrentLocation();
      if (backendRes?.data && typeof backendRes.data.latitude === 'number') {
        const d = backendRes.data;
        const lat = d.latitude;
        const lon = d.longitude;
        return {
          latitude: lat,
          longitude: lon,
          latitudeStr: `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}`,
          longitudeStr: `${Math.abs(lon).toFixed(4)}° ${lon >= 0 ? 'E' : 'W'}`,
          accuracy: d.accuracy || 15,
          city: d.city || `GPS Node (${Math.abs(lat).toFixed(2)}°)`,
          region: d.region || '',
          country: d.country || 'Detected Region',
          countryCode: '',
          isp: d.isp || d.provider || 'Mobile GPS Gateway',
          ip: d.ip || '127.0.0.1',
          provider: 'CELLULAR / GPS',
          isMock: Boolean(d.is_mock_location),
          threatLevel: d.is_spoofed ? 'High Risk' : 'Safe',
          timestamp: d.timestamp || new Date().toISOString(),
          source: 'network',
        };
      }
    } catch {}

    throw new Error('Unable to determine location. Please enable GPS permissions.');
  }

  /**
   * Syncs user live location to backend server database via POST /api/v1/geolocation/current
   */
  private async syncWithBackend(loc: UserLiveLocation): Promise<void> {
    try {
      await GeolocationRepository.updateCurrentLocation({
        latitude: loc.latitude,
        longitude: loc.longitude,
        ip: loc.ip,
        is_mock_location: loc.isMock,
        accuracy: loc.accuracy,
        provider: (loc.provider || 'gps').toLowerCase(),
        timestamp: loc.timestamp,
        device_id: 'primary_phone',
        platform: Platform.OS,
        city: loc.city,
        country: loc.country,
        address: `${loc.latitudeStr}, ${loc.longitudeStr}`,
        isp: loc.isp,
      });
    } catch (e) {
      console.log('[LocationService] Non-critical sync error:', e);
    }
  }
}

export const locationService = new LocationService();

