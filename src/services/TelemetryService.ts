import { NativeModules, Platform } from 'react-native';
import { apiClient } from '../api/apiClient';
import { Storage } from '../utils/storage';
import { UsageStatsBridge } from '../native/usageStats';

const { LocationModule } = NativeModules;

class TelemetryServiceWorker {
  private timerId: ReturnType<typeof setInterval> | null = null;
  private appsTimerId: ReturnType<typeof setInterval> | null = null;
  private isRunning: boolean = false;

  /**
   * Start 30-45s GPS location telemetry and 60s App Usage sync
   */
  async start(): Promise<void> {
    if (this.isRunning) return;
    this.isRunning = true;
    console.log('[TelemetryWorker] 🛰️ Starting Background Telemetry Worker...');

    // 1. Start Android native foreground service to keep process alive through Doze Mode
    if (Platform.OS === 'android' && LocationModule?.startTelemetryService) {
      try {
        await LocationModule.startTelemetryService();
        console.log('[TelemetryWorker] 🛡️ Android LocationTelemetryService started.');
      } catch (e) {
        console.warn('[TelemetryWorker] Could not start foreground service:', e);
      }
    }

    // 2. Immediate first run
    this.sendLocationTick();
    this.sendAppsUsageTick();

    // 3. Periodic location telemetry: Every 30 seconds
    this.timerId = setInterval(() => {
      this.sendLocationTick();
    }, 30000);

    // 4. Periodic app usage sync: Every 60 seconds
    this.appsTimerId = setInterval(() => {
      this.sendAppsUsageTick();
    }, 60000);
  }

  stop(): void {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.appsTimerId) {
      clearInterval(this.appsTimerId);
      this.appsTimerId = null;
    }
    this.isRunning = false;

    if (Platform.OS === 'android' && LocationModule?.stopTelemetryService) {
      try {
        LocationModule.stopTelemetryService();
      } catch {}
    }
    console.log('[TelemetryWorker] 🛑 Telemetry Worker stopped.');
  }

  /**
   * Acquire live GPS coordinates and send to /api/location/telemetry
   */
  async sendLocationTick(): Promise<void> {
    try {
      const childId = (await Storage.getChildId()) || '8';
      let latitude = 13.0827123;
      let longitude = 80.2707456;
      let battery = 90;

      // Try LocationModule first
      if (LocationModule?.getCurrentLocation) {
        try {
          const loc = await LocationModule.getCurrentLocation();
          if (loc && loc.latitude && loc.longitude) {
            latitude = Number(loc.latitude);
            longitude = Number(loc.longitude);
          }
        } catch (locErr) {
          // Try react-native-geolocation-service if available
          try {
            const Geolocation = require('react-native-geolocation-service').default;
            await new Promise<void>((resolve) => {
              Geolocation.getCurrentPosition(
                (pos: any) => {
                  if (pos?.coords) {
                    latitude = pos.coords.latitude;
                    longitude = pos.coords.longitude;
                  }
                  resolve();
                },
                () => resolve(),
                { enableHighAccuracy: true, timeout: 5000, maximumAge: 10000 }
              );
            });
          } catch {}
        }
      }

      await apiClient.sendLocationTelemetry({
        child_id: childId,
        latitude,
        longitude,
        battery_percentage: battery,
      });
      console.log(`[TelemetryWorker] 📍 Telemetry ping sent for child ${childId}: (${latitude}, ${longitude})`);
    } catch (err: any) {
      console.warn('[TelemetryWorker] Location telemetry tick error:', err?.message || err);
    }
  }

  /**
   * Query daily foreground usage from UsageStatsManager and send to /api/apps/sync
   */
  async sendAppsUsageTick(): Promise<void> {
    try {
      const childId = (await Storage.getChildId()) || '8';
      const hasPermission = await UsageStatsBridge.checkUsagePermission();
      if (!hasPermission) {
        return;
      }

      const installedApps = await UsageStatsBridge.getDailyAppUsage();
      if (installedApps && installedApps.length > 0) {
        await apiClient.syncInstalledApps({
          child_id: childId,
          installed_apps: installedApps,
        });
        console.log(`[TelemetryWorker] 📱 Synced ${installedApps.length} apps for child ${childId}`);
      }
    } catch (err: any) {
      console.warn('[TelemetryWorker] Apps usage sync tick error:', err?.message || err);
    }
  }
}

export const telemetryService = new TelemetryServiceWorker();
export const telemetryWorker = telemetryService;
export default telemetryService;
