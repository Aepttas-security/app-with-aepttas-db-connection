// Local persistent storage utility with AsyncStorage persistence and reactive event listeners
import AsyncStorage from '@react-native-async-storage/async-storage';

let memoryStore: Record<string, string> = {
  auth_token: '',
  assigned_role: '',
  child_id: '',
  linked_child: '',
};

type Listener = () => void;
const listenersMap: Map<string, Set<Listener>> = new Map();

const subscribe = (key: string, listener: Listener): (() => void) => {
  if (!listenersMap.has(key)) {
    listenersMap.set(key, new Set());
  }
  listenersMap.get(key)!.add(listener);
  return () => {
    const set = listenersMap.get(key);
    if (set) {
      set.delete(listener);
    }
  };
};

const notify = (key: string) => {
  const set = listenersMap.get(key);
  if (set) {
    set.forEach(cb => {
      try {
        cb();
      } catch (e) {
        console.error(`Error in storage listener for ${key}:`, e);
      }
    });
  }
  const wildcardSet = listenersMap.get('*');
  if (wildcardSet) {
    wildcardSet.forEach(cb => {
      try {
        cb();
      } catch (e) {
        console.error('Error in wildcard storage listener:', e);
      }
    });
  }
};

const getStored = async (key: string): Promise<string> => {
  try {
    const value = await AsyncStorage.getItem(`aepttas_${key}`);
    if (value !== null) {
      memoryStore[key] = value;
      return value;
    }
  } catch (err) {
    console.error(`[Storage] Error reading key ${key}:`, err);
  }
  return memoryStore[key] || '';
};

const setStored = async (key: string, value: string): Promise<void> => {
  memoryStore[key] = value;
  try {
    await AsyncStorage.setItem(`aepttas_${key}`, value);
  } catch (err) {
    console.error(`[Storage] Error writing key ${key}:`, err);
  }
  notify(key);
};

const removeStored = async (key: string): Promise<void> => {
  memoryStore[key] = '';
  try {
    await AsyncStorage.removeItem(`aepttas_${key}`);
  } catch (err) {
    console.error(`[Storage] Error removing key ${key}:`, err);
  }
  notify(key);
};

export const Storage = {
  subscribe,

  async setAuthToken(token: string): Promise<void> {
    await setStored('auth_token', token);
  },

  async getAuthToken(): Promise<string> {
    return await getStored('auth_token');
  },

  async setUserProfile(profile: { name: string; email: string; phone?: string; user_id?: number }): Promise<void> {
    await setStored('user_profile', JSON.stringify(profile));
  },

  async getUserProfile(): Promise<{ name: string; email: string; phone?: string; user_id?: number } | null> {
    try {
      const raw = await getStored('user_profile');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setAssignedRole(role: 'PARENT' | 'CHILD'): Promise<void> {
    await setStored('assigned_role', role);
    await setStored('is_existing_user', 'true');
  },

  async setIsExistingUser(val: boolean): Promise<void> {
    await setStored('is_existing_user', val ? 'true' : 'false');
  },

  async getIsExistingUser(): Promise<boolean> {
    const raw = await getStored('is_existing_user');
    if (raw === 'true') return true;
    const profile = await getStored('user_profile');
    const role = await getStored('assigned_role');
    const registered = await getStored('registered_accounts');
    return !!(profile || role || (registered && registered !== '[]'));
  },

  async getAssignedRole(): Promise<'PARENT' | 'CHILD' | ''> {
    return ((await getStored('assigned_role')) as 'PARENT' | 'CHILD') || '';
  },

  async setChildId(childId: string): Promise<void> {
    await setStored('child_id', childId);
  },

  async getChildId(): Promise<string> {
    return await getStored('child_id');
  },

  async setPairingId(pairingId: string | number): Promise<void> {
    await setStored('pairing_id', String(pairingId));
  },

  async getPairingId(): Promise<string> {
    return await getStored('pairing_id');
  },

  async setLinkedChild(childData: any): Promise<void> {
    if (!childData) {
      await setStored('linked_child', '');
      return;
    }
    await setStored('linked_child', JSON.stringify(childData));
    const parentEmail = (childData.parentEmail || childData.parent_email || '').trim().toLowerCase();
    if (parentEmail) {
      await setStored(`linked_child_${parentEmail}`, JSON.stringify(childData));
    }
  },

  async removeLinkedChild(forParentEmail?: string): Promise<void> {
    await setStored('linked_child', '');
    if (forParentEmail) {
      await setStored(`linked_child_${forParentEmail.trim().toLowerCase()}`, '');
    }
    const profileRaw = await getStored('user_profile');
    if (profileRaw) {
      try {
        const profile = JSON.parse(profileRaw);
        if (profile?.email) {
          await setStored(`linked_child_${profile.email.trim().toLowerCase()}`, '');
        }
      } catch {}
    }
  },

  async getLinkedChild(forParentEmail?: string): Promise<any | null> {
    try {
      let targetEmail = (forParentEmail || '').trim().toLowerCase();
      if (!targetEmail) {
        const profileRaw = await getStored('user_profile');
        if (profileRaw) {
          const profile = JSON.parse(profileRaw);
          if (profile?.email) {
            targetEmail = profile.email.trim().toLowerCase();
          }
        }
      }

      if (targetEmail) {
        const specificRaw = await getStored(`linked_child_${targetEmail}`);
        if (specificRaw) {
          return JSON.parse(specificRaw);
        }
      }

      const raw = await getStored('linked_child');
      if (!raw) return null;
      const child = JSON.parse(raw);

      if (targetEmail && child) {
        const childEmail = (child.parentEmail || child.parent_email || '').trim().toLowerCase();
        if (childEmail && childEmail !== targetEmail) {
          return null;
        }
      }
      return child;
    } catch {
      return null;
    }
  },

  async setChildrenList(list: any[]): Promise<void> {
    await setStored('children_list', JSON.stringify(list));
  },

  async getChildrenList(): Promise<any[] | null> {
    try {
      const raw = await getStored('children_list');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setScreentime(childId: string, data: any): Promise<void> {
    await setStored(`screentime_${childId}`, JSON.stringify(data));
  },

  async getScreentime(childId: string): Promise<any | null> {
    try {
      const raw = await getStored(`screentime_${childId}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setApps(childId: string, apps: any[]): Promise<void> {
    await setStored(`apps_${childId}`, JSON.stringify(apps));
  },

  async getApps(childId: string): Promise<any[] | null> {
    try {
      const raw = await getStored(`apps_${childId}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setFilterRules(childId: string, filters: any): Promise<void> {
    await setStored(`filters_${childId}`, JSON.stringify(filters));
  },

  async getFilterRules(childId: string): Promise<any | null> {
    try {
      const raw = await getStored(`filters_${childId}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setGeofences(childId: string, geofences: any[]): Promise<void> {
    await setStored(`geofences_${childId}`, JSON.stringify(geofences));
  },

  async getGeofences(childId: string): Promise<any[] | null> {
    try {
      const raw = await getStored(`geofences_${childId}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setScanLogs(scans: any[]): Promise<void> {
    await setStored('scan_logs', JSON.stringify(scans));
  },

  async getScanLogs(): Promise<any[] | null> {
    try {
      const raw = await getStored('scan_logs');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setQuarantineItems(items: any[]): Promise<void> {
    await setStored('quarantine_items', JSON.stringify(items));
  },

  async getQuarantineItems(): Promise<any[] | null> {
    try {
      const raw = await getStored('quarantine_items');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setCallerIntel(data: any): Promise<void> {
    await setStored('caller_intel', JSON.stringify(data));
  },

  async getCallerIntel(): Promise<any | null> {
    try {
      const raw = await getStored('caller_intel');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setVulnerabilities(data: any): Promise<void> {
    await setStored('vulnerabilities_data', JSON.stringify(data));
  },

  async getVulnerabilities(): Promise<any | null> {
    try {
      const raw = await getStored('vulnerabilities_data');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async setPendingCode(code: string): Promise<void> {
    await setStored('pending_code', code);
  },

  async getPendingCode(): Promise<string> {
    return await getStored('pending_code');
  },

  async setPairingState(code: string, pairingData: any): Promise<void> {
    await setStored(`pairing_${code.replace(/[^a-zA-Z0-9]/g, '')}`, JSON.stringify(pairingData));
  },

  async getPairingState(code: string): Promise<any | null> {
    try {
      const raw = await getStored(`pairing_${code.replace(/[^a-zA-Z0-9]/g, '')}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  async saveRegisteredAccount(account: { name: string; email: string; password?: string; user_id?: number }): Promise<void> {
    try {
      const existingRaw = await getStored('registered_accounts');
      const list: any[] = existingRaw ? JSON.parse(existingRaw) : [];
      const updated = list.filter((a: any) => a.email.toLowerCase() !== account.email.toLowerCase());
      updated.push(account);
      await setStored('registered_accounts', JSON.stringify(updated));
    } catch (e) {
      console.error('[Storage] Failed to save registered account:', e);
    }
  },

  async findRegisteredAccount(email: string): Promise<{ name: string; email: string; password?: string; user_id?: number } | null> {
    try {
      const existingRaw = await getStored('registered_accounts');
      if (!existingRaw) return null;
      const list: any[] = JSON.parse(existingRaw);
      return list.find((a: any) => a.email.toLowerCase() === email.trim().toLowerCase()) || null;
    } catch {
      return null;
    }
  },

  async hasActiveSession(): Promise<boolean> {
    const token = await getStored('auth_token');
    const profile = await getStored('user_profile');
    return !!(token || profile);
  },

  async hasSyncedInitialContacts(userEmail?: string): Promise<boolean> {
    try {
      if (userEmail) {
        const userSpecific = await getStored(`has_synced_contacts_${userEmail.toLowerCase().trim()}`);
        if (userSpecific === 'true') return true;
      }
      const globalVal = await getStored('has_synced_contacts');
      return globalVal === 'true';
    } catch {
      return false;
    }
  },

  async setHasSyncedInitialContacts(synced: boolean, userEmail?: string): Promise<void> {
    try {
      if (userEmail) {
        await setStored(`has_synced_contacts_${userEmail.toLowerCase().trim()}`, synced ? 'true' : 'false');
      }
      await setStored('has_synced_contacts', synced ? 'true' : 'false');
    } catch (e) {
      console.error('[Storage] Error setting hasSyncedInitialContacts:', e);
    }
  },

  async hasRequestedInitialPermissions(userEmail?: string): Promise<boolean> {
    try {
      if (userEmail) {
        const userSpecific = await getStored(`has_requested_initial_permissions_${userEmail.toLowerCase().trim()}`);
        if (userSpecific === 'true') return true;
      }
      const globalVal = await getStored('has_requested_initial_permissions');
      return globalVal === 'true';
    } catch {
      return false;
    }
  },

  async setHasRequestedInitialPermissions(requested: boolean, userEmail?: string): Promise<void> {
    try {
      if (userEmail) {
        await setStored(`has_requested_initial_permissions_${userEmail.toLowerCase().trim()}`, requested ? 'true' : 'false');
      }
      await setStored('has_requested_initial_permissions', requested ? 'true' : 'false');
    } catch (e) {
      console.error('[Storage] Error setting hasRequestedInitialPermissions:', e);
    }
  },

  async clear(): Promise<void> {
    await removeStored('auth_token');
    await removeStored('user_profile');
    await removeStored('assigned_role');
    await removeStored('child_id');
    await removeStored('linked_child');
    await removeStored('children_list');
    await removeStored('pending_code');
  },
};
