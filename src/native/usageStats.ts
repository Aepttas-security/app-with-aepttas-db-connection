import { NativeModules, Platform, Alert, Linking } from 'react-native';

const { UsageStatsModule } = NativeModules;

export interface InstalledAppUsage {
  package_name: string;
  app_name: string;
  category: string;
  usage_minutes: number;
}

/**
 * Native bridge wrapper for Android Special App Access (PACKAGE_USAGE_STATS)
 */
export const UsageStatsBridge = {
  /**
   * Check whether PACKAGE_USAGE_STATS permission has been granted by user
   */
  async checkUsagePermission(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    if (!UsageStatsModule?.checkUsagePermission) {
      console.warn('[UsageStatsBridge] UsageStatsModule not available on this platform.');
      return false;
    }
    try {
      return await UsageStatsModule.checkUsagePermission();
    } catch (e) {
      console.error('[UsageStatsBridge] checkUsagePermission error:', e);
      return false;
    }
  },

  /**
   * Open Android Special App Access -> Usage Access settings screen
   */
  async requestUsagePermission(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    if (!UsageStatsModule?.requestUsagePermission) {
      console.warn('[UsageStatsBridge] UsageStatsModule not available on this platform.');
      return false;
    }
    try {
      return await UsageStatsModule.requestUsagePermission();
    } catch (e) {
      console.error('[UsageStatsBridge] requestUsagePermission error:', e);
      return false;
    }
  },

  /**
   * Query aggregated daily usage minutes per installed application
   */
  async getDailyAppUsage(): Promise<InstalledAppUsage[]> {
    if (Platform.OS !== 'android') {
      return [];
    }
    if (!UsageStatsModule?.getDailyAppUsage) {
      console.warn('[UsageStatsBridge] getDailyAppUsage not implemented on this platform.');
      return [];
    }
    try {
      const stats = await UsageStatsModule.getDailyAppUsage();
      return Array.isArray(stats) ? stats : [];
    } catch (e) {
      console.error('[UsageStatsBridge] getDailyAppUsage error:', e);
      return [];
    }
  },

  /**
   * Helper to prompt user with instructions for Android 13/14 "Restricted settings" bypass
   */
  showRestrictedSettingsGuide(): void {
    if (Platform.OS !== 'android') return;
    Alert.alert(
      'Usage Access Restricted (Android 13/14)',
      'If Android displays "Restricted setting" when toggling Usage access:\n\n' +
      '1. Open device Settings > Apps > AEPTTAS Shield.\n' +
      '2. Tap the three dots (⋮) in the top-right corner.\n' +
      '3. Select "Allow restricted settings".\n' +
      '4. Return here and tap "Grant Usage Access".',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Open App Info',
          onPress: () => {
            Linking.openSettings();
          },
        },
      ]
    );
  },
};
