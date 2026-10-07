import { NativeModules, Platform } from 'react-native';
import { RiskAnalyzer, AnalysisResult } from './RiskAnalyzer';

// Extract the native module exposed by Android Kotlin code
const { ApkScanner: NativeApkScanner } = NativeModules;

export interface EnrichedAnalysisResult extends AnalysisResult {
  fileName: string;
  filePath: string;
  packageName: string;
  version: string;
  timestamp: number;
}

export const ApkScanner = {
  /**
   * Scans an APK file.
   * Calls the native Android PackageManager module when available,
   * and falls back to filename heuristics for testing or on iOS.
   */
  async scanApk(filePath: string): Promise<EnrichedAnalysisResult> {
    const fileName = filePath.substring(filePath.lastIndexOf('/') + 1);
    let permissions: string[] = [];
    let packageName = 'com.unknown.app';
    let version = '1.0.0';
    let isNativeSuccess = false;

    // 1. Attempt Native Scanning on Android
    if (Platform.OS === 'android' && NativeApkScanner) {
      try {
        const nativeResult = await NativeApkScanner.scanApk(filePath);
        if (nativeResult) {
          permissions = nativeResult.permissions || [];
          packageName = nativeResult.packageName || 'com.unknown.apk';
          version = nativeResult.versionName || '1.0';
          isNativeSuccess = true;
        }
      } catch (error) {
        console.warn('Native APK scanning failed:', error);
      }
    }

    // 2. If non-Android or parsing failed, return empty permissions
    if (!isNativeSuccess) {
      permissions = [];
      packageName = fileName.replace(/\.[^/.]+$/, '');
      version = '1.0';
    }

    // 3. Analyze permissions and build response
    const analysis = RiskAnalyzer.analyzePermissions(permissions);

    return {
      ...analysis,
      fileName,
      filePath,
      packageName,
      version,
      timestamp: Date.now(),
    };
  },

  getMockPermissionsForFileName(fileName: string): { permissions: string[] } {
    const lowerName = fileName.toLowerCase();
    
    if (lowerName.includes('spyware') || lowerName.includes('spy')) {
      return {
        permissions: [
          'android.permission.RECORD_AUDIO',
          'android.permission.CAMERA',
          'android.permission.ACCESS_FINE_LOCATION',
          'android.permission.READ_CONTACTS',
          'android.permission.INTERNET',
        ],
      };
    }
    
    if (lowerName.includes('ransomware') || lowerName.includes('ransom')) {
      return {
        permissions: [
          'android.permission.SYSTEM_ALERT_WINDOW',
          'android.permission.WRITE_EXTERNAL_STORAGE',
          'android.permission.RECEIVE_BOOT_COMPLETED',
          'android.permission.INTERNET',
        ],
      };
    }
    
    if (lowerName.includes('banker') || lowerName.includes('trojan')) {
      return {
        permissions: [
          'android.permission.BIND_ACCESSIBILITY_SERVICE',
          'android.permission.SYSTEM_ALERT_WINDOW',
          'android.permission.RECEIVE_SMS',
          'android.permission.READ_SMS',
          'android.permission.INTERNET',
        ],
      };
    }
    
    if (lowerName.includes('adware') || lowerName.includes('ad')) {
      return {
        permissions: [
          'android.permission.INTERNET',
          'android.permission.ACCESS_NETWORK_STATE',
          'android.permission.SYSTEM_ALERT_WINDOW',
        ],
      };
    }
    
    if (lowerName.includes('suspicious')) {
      return {
        permissions: [
          'android.permission.WRITE_EXTERNAL_STORAGE',
          'android.permission.RECEIVE_BOOT_COMPLETED',
          'android.permission.GET_TASKS',
        ],
      };
    }

    // Check non-APK high-risk extension profiles
    const ext = lowerName.substring(lowerName.lastIndexOf('.'));
    
    // 1. High-risk executables and binary installers (.exe, .scr, .msi, .dll)
    if (['.exe', '.scr', '.msi', '.dll'].includes(ext)) {
      return {
        permissions: [
          'android.permission.SYSTEM_ALERT_WINDOW',
          'android.permission.WRITE_EXTERNAL_STORAGE',
          'android.permission.RECEIVE_BOOT_COMPLETED',
          'android.permission.REQUEST_INSTALL_PACKAGES',
          'android.permission.INTERNET',
        ],
      };
    }

    // 2. High-risk script payloads (.bat, .cmd, .vbs, .js, .ps1, .hta)
    if (['.bat', '.cmd', '.vbs', '.js', '.ps1', '.hta'].includes(ext)) {
      return {
        permissions: [
          'android.permission.BIND_ACCESSIBILITY_SERVICE',
          'android.permission.SYSTEM_ALERT_WINDOW',
          'android.permission.REQUEST_INSTALL_PACKAGES',
          'android.permission.INTERNET',
        ],
      };
    }

    // 3. Macro documents & Java archives (.docm, .xlsm, .jar)
    if (['.docm', '.xlsm', '.jar'].includes(ext)) {
      return {
        permissions: [
          'android.permission.WRITE_EXTERNAL_STORAGE',
          'android.permission.READ_EXTERNAL_STORAGE',
          'android.permission.REQUEST_INSTALL_PACKAGES',
          'android.permission.INTERNET',
        ],
      };
    }

    // 4. Disk images and shortcuts (.iso, .img, .lnk)
    if (['.iso', '.img', '.lnk'].includes(ext)) {
      return {
        permissions: [
          'android.permission.SYSTEM_ALERT_WINDOW',
          'android.permission.WRITE_EXTERNAL_STORAGE',
          'android.permission.INTERNET',
        ],
      };
    }

    // Default Safe
    return {
      permissions: [
        'android.permission.INTERNET',
        'android.permission.ACCESS_NETWORK_STATE',
      ],
    };
  }
};
