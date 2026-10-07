import { PermissionsAndroid, Platform, ToastAndroid, Permission } from 'react-native';
import { Storage } from '../utils/storage';
import { syncContactsWithBackend } from './ContactService';
import { locationService } from './LocationService';
import CallDetection from '../native/CallDetection';

/**
 * Returns all runtime permissions required for the application
 * to run with complete functionality (Geo Tracking, Caller Intelligence,
 * Threat Analysis, Contact Sync, and Notifications).
 */
export const getRequiredPermissions = (): Permission[] => {
  if (Platform.OS !== 'android') return [];

  const perms: Permission[] = [
    PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
    PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION,
    PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
    PermissionsAndroid.PERMISSIONS.WRITE_CONTACTS,
    PermissionsAndroid.PERMISSIONS.READ_PHONE_STATE,
    PermissionsAndroid.PERMISSIONS.READ_CALL_LOG,
    PermissionsAndroid.PERMISSIONS.CALL_PHONE,
  ];

  const sdkVersion =
    typeof Platform.Version === 'number'
      ? Platform.Version
      : parseInt(Platform.Version as string, 10) || 0;

  if (sdkVersion >= 33) {
    if (PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS) {
      perms.push(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
    }
    const mediaImages = (PermissionsAndroid.PERMISSIONS as any).READ_MEDIA_IMAGES;
    if (mediaImages) {
      perms.push(mediaImages);
    }
  } else {
    if (PermissionsAndroid.PERMISSIONS.READ_EXTERNAL_STORAGE) {
      perms.push(PermissionsAndroid.PERMISSIONS.READ_EXTERNAL_STORAGE);
    }
    if (PermissionsAndroid.PERMISSIONS.WRITE_EXTERNAL_STORAGE) {
      perms.push(PermissionsAndroid.PERMISSIONS.WRITE_EXTERNAL_STORAGE);
    }
  }

  return perms;
};

export interface PermissionRequestSummary {
  success: boolean;
  grantedCount: number;
  totalCount: number;
  results: Record<string, string>;
}

/**
 * Requests all required permissions upfront at the beginning of entry
 * upon first-time login, ensuring Geo Tracking, Call Detection, Contact Sync,
 * and Scanner can all operate without permission barriers.
 */
export const requestAllPermissionsOnFirstLogin = async (
  userEmail?: string,
  force: boolean = false
): Promise<PermissionRequestSummary> => {
  if (Platform.OS !== 'android') {
    return { success: true, grantedCount: 0, totalCount: 0, results: {} };
  }

  try {
    const alreadyRequested = await Storage.hasRequestedInitialPermissions(userEmail);
    if (alreadyRequested && !force) {
      console.log('[PermissionService] Permissions already requested previously for this user/device.');
      return { success: true, grantedCount: 0, totalCount: 0, results: {} };
    }

    console.log('[PermissionService] First login / entry detected: Requesting all necessary permissions...');
    ToastAndroid.show('Setting up Shield protection permissions...', ToastAndroid.SHORT);

    const permissions = getRequiredPermissions();
    const results = await PermissionsAndroid.requestMultiple(permissions);

    let grantedCount = 0;
    const totalCount = permissions.length;

    Object.entries(results).forEach(([perm, status]) => {
      if (status === PermissionsAndroid.RESULTS.GRANTED) {
        grantedCount++;
      }
      console.log(`[PermissionService] ${perm}: ${status}`);
    });

    // Mark that initial permissions were requested on this entry
    await Storage.setHasRequestedInitialPermissions(true, userEmail);

    // 1. Post-permission action: If Contacts permission granted, immediately upload device contacts
    const contactsGranted =
      results[PermissionsAndroid.PERMISSIONS.READ_CONTACTS] === PermissionsAndroid.RESULTS.GRANTED;

    if (contactsGranted) {
      console.log('[PermissionService] Contacts permission granted. Auto-syncing contacts to backend...');
      syncContactsWithBackend()
        .then(async res => {
          if (res.success) {
            await Storage.setHasSyncedInitialContacts(true, userEmail);
            console.log('[PermissionService] Contacts synced successfully:', res.count);
          }
        })
        .catch(err => console.warn('[PermissionService] Contact auto-sync failed:', err));
    }

    // 2. Post-permission action: If Location permission granted, prime live GPS location
    const locationGranted =
      results[PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION] === PermissionsAndroid.RESULTS.GRANTED ||
      results[PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION] === PermissionsAndroid.RESULTS.GRANTED;

    if (locationGranted) {
      console.log('[PermissionService] Location permission granted. Priming live GPS tracking...');
      locationService
        .detectLiveLocation()
        .then((loc: any) => console.log('[PermissionService] Live location primed:', loc.latitude, loc.longitude))
        .catch((err: any) => console.warn('[PermissionService] Live location prime failed:', err));
    }

    // 3. Post-permission action: If Phone State granted, initialize native Call Detection
    const phoneGranted =
      results[PermissionsAndroid.PERMISSIONS.READ_PHONE_STATE] === PermissionsAndroid.RESULTS.GRANTED;

    if (phoneGranted) {
      console.log('[PermissionService] Phone state permission granted. Initializing Call Detection...');
      CallDetection.initialize().catch(err => console.warn('[PermissionService] CallDetection init error:', err));
    }

    ToastAndroid.show(
      `Shield permissions configured (${grantedCount}/${totalCount} granted). App running perfectly!`,
      ToastAndroid.SHORT
    );

    return {
      success: grantedCount > 0,
      grantedCount,
      totalCount,
      results,
    };
  } catch (error: any) {
    console.error('[PermissionService] Error requesting all permissions on first login:', error);
    return {
      success: false,
      grantedCount: 0,
      totalCount: 0,
      results: {},
    };
  }
};
