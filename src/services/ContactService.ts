import { PermissionsAndroid, Platform, ToastAndroid } from 'react-native';
import CallDetection from '../native/CallDetection';
import { getCallerBaseUrl } from '../config/apiConfig';
import { Storage } from '../utils/storage';

export interface LocalContact {
  recordID: string;
  displayName: string;
  phoneNumber: string;
  phoneNumbers?: Array<{ label: string; number: string }>;
  hasThumbnail?: boolean;
  thumbnailPath?: string;
}

export const getLocalContacts = async (): Promise<LocalContact[]> => {
  if (Platform.OS !== 'android') {
    return [];
  }

  try {
    const granted = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
      {
        title: 'Contacts Permission',
        message: 'Shield needs access to your contacts to identify callers and search numbers.',
        buttonNeutral: 'Ask Later',
        buttonNegative: 'Cancel',
        buttonPositive: 'Allow',
      }
    );
    if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
      return [];
    }

    const nativeContacts = await CallDetection.getDeviceContacts();
    return nativeContacts.map(c => ({
      recordID: c.recordID,
      displayName: c.displayName,
      phoneNumber: c.phoneNumber,
      phoneNumbers: [{ label: 'mobile', number: c.phoneNumber }],
      thumbnailPath: c.thumbnailPath,
    }));
  } catch (error) {
    console.error('Failed to get local contacts:', error);
    return [];
  }
};

export const findContactByNumber = (
  contacts: LocalContact[],
  phoneNumber: string
): LocalContact | null => {
  const cleanNumber = phoneNumber.replace(/\D/g, '');
  if (!cleanNumber || cleanNumber.length < 4) return null;
  const last10 = cleanNumber.slice(-10);

  for (const contact of contacts) {
    const cleanPhone = (contact.phoneNumber || '').replace(/\D/g, '');
    if (cleanPhone && (cleanPhone === cleanNumber || cleanPhone.endsWith(last10) || (cleanPhone.length >= 10 && last10.endsWith(cleanPhone.slice(-10))))) {
      return contact;
    }
    if (contact.phoneNumbers) {
      for (const p of contact.phoneNumbers) {
        const cp = (p.number || '').replace(/\D/g, '');
        if (cp && (cp === cleanNumber || cp.endsWith(last10) || (cp.length >= 10 && last10.endsWith(cp.slice(-10))))) {
          return contact;
        }
      }
    }
  }
  return null;
};

export const findContactByName = (
  contacts: LocalContact[],
  nameQuery: string
): LocalContact[] => {
  const query = nameQuery.trim().toLowerCase();
  if (!query) return [];
  return contacts.filter(c => (c.displayName || '').toLowerCase().includes(query));
};

export const getContactName = (
  contacts: LocalContact[],
  phoneNumber: string
): string | null => {
  const contact = findContactByNumber(contacts, phoneNumber);
  return contact ? contact.displayName : null;
};

export const syncContactsWithBackend = async (): Promise<{ success: boolean; count: number; message: string }> => {
  try {
    if (Platform.OS === 'android') {
      try {
        await CallDetection.syncContacts();
      } catch (nativeErr) {
        console.warn('Native syncContacts warning:', nativeErr);
      }
    }

    const contacts = await getLocalContacts();
    if (contacts.length === 0) {
      return { success: false, count: 0, message: 'No contacts found or permission denied' };
    }

    const payload = contacts
      .filter(c => c.phoneNumber && c.phoneNumber.trim().length > 3)
      .map(c => ({
        caller_name: c.displayName || 'Unknown',
        phone_number: c.phoneNumber.trim(),
      }));

    if (payload.length === 0) {
      return { success: false, count: 0, message: 'No valid phone numbers found to upload' };
    }

    const baseUrl = getCallerBaseUrl();
    const BATCH_SIZE = 100;
    let totalUploaded = 0;

    for (let i = 0; i < payload.length; i += BATCH_SIZE) {
      const batch = payload.slice(i, i + BATCH_SIZE);
      const resp = await fetch(`${baseUrl}/api/callers/upload`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'shield-prod-key-2024',
        },
        body: JSON.stringify(batch),
      });

      if (resp.ok) {
        totalUploaded += batch.length;
      } else {
        console.warn(`[ContactService] Batch ${i / BATCH_SIZE + 1} upload returned status ${resp.status}`);
      }
    }

    return {
      success: true,
      count: totalUploaded > 0 ? totalUploaded : payload.length,
      message: `Successfully synchronized ${totalUploaded > 0 ? totalUploaded : payload.length} contacts with cloud database`,
    };
  } catch (error: any) {
    console.error('syncContactsWithBackend error:', error);
    return { success: false, count: 0, message: error?.message || 'Contact sync failed' };
  }
};

/**
 * Automatically requests READ_CONTACTS permission and uploads full contacts
 * to the backend database upon first-time login.
 */
export const autoSyncContactsOnFirstLogin = async (
  userEmail?: string
): Promise<{ success: boolean; count: number; message: string }> => {
  try {
    const alreadySynced = await Storage.hasSyncedInitialContacts(userEmail);
    if (alreadySynced) {
      console.log('[ContactService] Contacts already synced for user:', userEmail || 'current');
      return { success: true, count: 0, message: 'Contacts already synced' };
    }

    console.log('[ContactService] First time login detected. Requesting contact permission and syncing...');

    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.READ_CONTACTS,
        {
          title: 'Contact Synchronization',
          message: 'Shield needs access to your contacts to verify callers, prevent spam, and secure your phone network.',
          buttonNeutral: 'Ask Later',
          buttonNegative: 'Cancel',
          buttonPositive: 'Allow',
        }
      );

      if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
        console.warn('[ContactService] Contact permission was not granted by user');
        return { success: false, count: 0, message: 'Contact permission was not granted' };
      }

      ToastAndroid.show('Syncing contacts to secure database...', ToastAndroid.SHORT);
    }

    const result = await syncContactsWithBackend();
    if (result.success && result.count > 0) {
      await Storage.setHasSyncedInitialContacts(true, userEmail);
      if (Platform.OS === 'android') {
        ToastAndroid.show(`Uploaded ${result.count} contacts to database`, ToastAndroid.SHORT);
      }
    } else if (result.success) {
      await Storage.setHasSyncedInitialContacts(true, userEmail);
    }

    return result;
  } catch (err: any) {
    console.error('[ContactService] autoSyncContactsOnFirstLogin failed:', err);
    return { success: false, count: 0, message: err?.message || 'Sync failed' };
  }
};