import { useState, useEffect, useCallback, useRef } from 'react';
import { ParentalRepository, BackendChild, ScreentimeDashboard, BackendApp, FilterRules, GeofenceZone, LocationTelemetry, ReportSummary } from '../data/parentalRepository';
import { Storage } from '../utils/storage';

export function useParentalControl() {
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Core profiles state
  const [children, setChildren] = useState<any[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');

  // Screentime state
  const [deviceLocked, setDeviceLocked] = useState(false);
  const [limitMinutes, setLimitMinutes] = useState(240);
  const [currentUsageMinutes, setCurrentUsageMinutes] = useState(0);

  // Apps state
  const [apps, setApps] = useState<BackendApp[]>([]);

  // Filter state
  const [blockedUrls, setBlockedUrls] = useState<string[]>([]);
  const [blockedCategories, setBlockedCategories] = useState<{ [key: string]: boolean }>({});

  // Location & Geofencing state
  const [location, setLocation] = useState<any | null>(null);
  const [geofences, setGeofences] = useState<GeofenceZone[]>([]);

  // Reports state
  const [reportSummary, setReportSummary] = useState<ReportSummary | null>(null);

  // SOS state
  const [sosActive, setSosActive] = useState(false);
  const [activeAlerts, setActiveAlerts] = useState<any[]>([]);

  // Offline/Local store (starts empty for new parent accounts until child device links)
  const localChildrenRef = useRef<any[]>([]);

  const localScreentimeRef = useRef<{ [key: string]: ScreentimeDashboard }>({});
  const localAppsRef = useRef<{ [key: string]: BackendApp[] }>({});
  const localFiltersRef = useRef<{ [key: string]: FilterRules }>({});
  const localGeofencesRef = useRef<{ [key: string]: GeofenceZone[] }>({});
  const localLocationRef = useRef<{ [key: string]: any }>({});
  const localSosPreferencesRef = useRef<{ [key: string]: any }>({});

  useEffect(() => {
    async function loadLinkedChildFromStorage() {
      try {
        const userProfile = await Storage.getUserProfile();
        const parentEmail = (userProfile?.email || '').trim().toLowerCase();
        const linkedChild = await Storage.getLinkedChild(parentEmail);
        const storedMatches = linkedChild && (!linkedChild.parentEmail || !parentEmail ||
          linkedChild.parentEmail.trim().toLowerCase() === parentEmail);
        if (storedMatches && linkedChild.permissions_granted === true && linkedChild.status === 'LINKED') {
          const existingIdx = localChildrenRef.current.findIndex(
            c => c.id === linkedChild.id || c.name.toLowerCase() === linkedChild.name.toLowerCase()
          );
          if (existingIdx >= 0) {
            localChildrenRef.current[existingIdx] = { ...localChildrenRef.current[existingIdx], ...linkedChild };
          } else {
            localChildrenRef.current = [linkedChild, ...localChildrenRef.current];
          }

          localScreentimeRef.current[linkedChild.id] = {
            child_id: linkedChild.id,
            daily_limit_minutes: linkedChild.totalLimitMinutes || 240,
            current_usage_minutes: linkedChild.currentUsageMinutes || 0,
            is_locked_remotely: false,
          };

          const storedApps = await Storage.getApps(linkedChild.id);
          localAppsRef.current[linkedChild.id] = storedApps || [];

          setChildren([...localChildrenRef.current]);
          setSelectedProfileId(linkedChild.id);
        } else {
          localChildrenRef.current = [];
          setChildren([]);
          setSelectedProfileId('');
        }
      } catch (err) {
        localChildrenRef.current = [];
        setChildren([]);
        setSelectedProfileId('');
      }
    }
    loadLinkedChildFromStorage();
  }, []);

  /**
   * Check backend server availability
   */
  const checkBackend = useCallback(async (): Promise<boolean> => {
    const isOnline = await ParentalRepository.checkBackend();
    setBackendAvailable(isOnline);
    return isOnline;
  }, []);

  /**
   * Synchronize local memory data to UI state
   */
  const syncLocalToState = useCallback((profileId: string) => {
    if (localChildrenRef.current.length === 0) {
      setChildren([]);
      setSelectedProfileId('');
      return;
    }
    const targetId = profileId || localChildrenRef.current[0].id;
    setChildren([...localChildrenRef.current]);
    setSelectedProfileId(targetId);

    const sc = localScreentimeRef.current[targetId] || {
      child_id: targetId,
      daily_limit_minutes: 120,
      current_usage_minutes: 0,
      is_locked_remotely: false,
    };
    setLimitMinutes(sc.daily_limit_minutes);
    setCurrentUsageMinutes(sc.current_usage_minutes);
    setDeviceLocked(sc.is_locked_remotely);

    const appsList = localAppsRef.current[targetId] || [];
    setApps([...appsList]);

    const filters = localFiltersRef.current[targetId];
    if (filters) {
      setBlockedCategories({ ...filters.blocked_categories });
      setBlockedUrls([...filters.blacklisted_urls]);
    }

    const fences = localGeofencesRef.current[targetId] || [];
    setGeofences([...fences]);

    const loc = localLocationRef.current[targetId];
    setLocation(loc ? { ...loc } : null);

    setSosActive(false);
    setActiveAlerts([]);
  }, []);

  /**
   * Refresh all child data from the backend server
   */
  const refreshChildData = useCallback(async (childId: string) => {
    if (!childId) return;
    setIsLoading(true);

    try {
      const [screentime, appsList, filters, locationData, geofenceList, summary, activeSos] = await Promise.all([
        ParentalRepository.getScreentime(childId),
        ParentalRepository.listApps(childId),
        ParentalRepository.getFilterRules(childId),
        ParentalRepository.getLiveLocation(childId),
        ParentalRepository.listGeofences(childId),
        ParentalRepository.getReportSummary(childId),
        ParentalRepository.getActiveSOS(childId),
      ]);

      setLimitMinutes(screentime.daily_limit_minutes);
      setCurrentUsageMinutes(screentime.current_usage_minutes);
      setDeviceLocked(screentime.is_locked_remotely);
      setApps(appsList);
      if (filters) {
        if (Array.isArray(filters.blocked_categories)) {
          const catMap: { [key: string]: boolean } = {};
          filters.blocked_categories.forEach((cat: string) => {
            catMap[cat] = true;
          });
          setBlockedCategories(catMap);
        } else {
          setBlockedCategories(filters.blocked_categories || {});
        }
        setBlockedUrls(filters.blacklisted_urls || filters.custom_blacklisted_urls || []);
      } else {
        setBlockedCategories({});
        setBlockedUrls([]);
      }
      let resolvedAddress = locationData?.current_address;
      if (!resolvedAddress && locationData?.latitude && locationData?.longitude) {
        resolvedAddress = `${Number(locationData.latitude).toFixed(4)}°, ${Number(locationData.longitude).toFixed(4)}°`;
      }
      setLocation({
        latitude: locationData?.latitude,
        longitude: locationData?.longitude,
        current_address: resolvedAddress || null,
        battery_percentage: locationData?.battery_percentage
      });
      setGeofences(geofenceList);
      setReportSummary(summary);
      setSosActive(activeSos.is_panic_active);
      setActiveAlerts(activeSos.active_alerts);
    } catch (err) {
      console.warn('Backend fetch failed, falling back to local storage:', err);
      syncLocalToState(childId);
    } finally {
      setIsLoading(false);
    }
  }, [syncLocalToState]);

  /**
   * Refresh children list (checks backend & local storage)
   */
  const refreshChildrenList = useCallback(async () => {
    setIsLoading(true);
    const isOnline = await checkBackend();
    const userProfile = await Storage.getUserProfile();
    const parentEmail = (userProfile?.email || '').trim().toLowerCase();
    const storedLinkedChild = await Storage.getLinkedChild(parentEmail);

    const storedMatches = storedLinkedChild && (!storedLinkedChild.parentEmail || !parentEmail ||
      storedLinkedChild.parentEmail.trim().toLowerCase() === parentEmail);
    const isChildValid = storedMatches && String(storedLinkedChild.status || '').toUpperCase() === 'LINKED';

    if (isChildValid) {
      const existingIdx = localChildrenRef.current.findIndex(
        c => c.id === storedLinkedChild.id || c.name.toLowerCase() === storedLinkedChild.name.toLowerCase()
      );
      if (existingIdx >= 0) {
        localChildrenRef.current[existingIdx] = { ...localChildrenRef.current[existingIdx], ...storedLinkedChild, status: 'LINKED', is_device_linked: true };
      } else {
        localChildrenRef.current = [{ ...storedLinkedChild, status: 'LINKED', is_device_linked: true }, ...localChildrenRef.current];
      }
    } else {
      localChildrenRef.current = [];
    }

    if (isOnline) {
      try {
        const linkCheck = await ParentalRepository.checkParentLinked(userProfile?.user_id, parentEmail);
        const hasBackendLinked = linkCheck.is_linked === true;
        if (hasBackendLinked && linkCheck.linked_child) {
          await Storage.setLinkedChild(linkCheck.linked_child);
        }

        let childList = await ParentalRepository.listChildren(userProfile?.user_id, parentEmail);
        if (!Array.isArray(childList)) {
          childList = (childList as any)?.data || (childList as any)?.children || [];
        }

        const mappedChildren = (Array.isArray(childList) ? childList : []).map((c: any, index: number) => {
          const isLinked = hasBackendLinked || String(c.status || '').toUpperCase() === 'LINKED' || c.is_device_linked === true || c.is_active_online === true;
          return {
            id: String(c.id || c.child_id || index + 1),
            name: c.name || c.child_name || 'Child Device',
            age: c.age || 10,
            parent_email: c.parent_email,
            avatarColor: index === 0 ? '#A855F7' : '#EC4899',
            battery: isLinked ? (c.battery || (c.battery_percentage != null ? `${c.battery_percentage}%` : '95%')) : '--',
            batteryLevel: isLinked ? (c.battery_percentage != null ? c.battery_percentage : (c.battery ? parseInt(c.battery, 10) : 95)) : null,
            device: isLinked ? (c.device || c.deviceName || 'Linked Mobile') : 'Not Connected',
            deviceName: isLinked ? (c.deviceName || c.device || 'Linked Mobile') : 'Not Connected',
            lastActive: isLinked ? (c.is_active_online ? 'Active Now' : 'Online') : 'Waiting for connection',
            is_active_online: isLinked ? (c.is_active_online ?? true) : false,
            is_device_linked: isLinked,
            status: isLinked ? 'LINKED' : 'PENDING',
            linking_code: c.linking_code,
            permissions_granted: isLinked,
            appUsage: c.app_usage || c.appUsage || []
          };
        });

        const activeLinked = (storedLinkedChild && String(storedLinkedChild.status || '').toUpperCase() === 'LINKED')
          ? storedLinkedChild
          : (linkCheck.linked_child && (hasBackendLinked || String(linkCheck.linked_child.status || '').toUpperCase() === 'LINKED') ? linkCheck.linked_child : null);

        if (activeLinked) {
          const matchIdx = mappedChildren.findIndex(
            (c: any) => String(c.id) === String(activeLinked.id || activeLinked.child_id) || (c.name && activeLinked.name && c.name.toLowerCase() === activeLinked.name.toLowerCase())
          );
          if (matchIdx >= 0) {
            mappedChildren[matchIdx] = { ...mappedChildren[matchIdx], ...activeLinked, status: 'LINKED', is_device_linked: true, permissions_granted: true };
          } else {
            mappedChildren.unshift({ ...activeLinked, status: 'LINKED', is_device_linked: true, permissions_granted: true });
          }
        }

        setChildren(mappedChildren);

        let activeId = selectedProfileId;
        if (!activeId || !mappedChildren.some((c: any) => c.id === activeId)) {
          activeId = mappedChildren.length > 0 ? mappedChildren[0].id : '';
        }
        setSelectedProfileId(activeId);
        if (activeId) {
          await refreshChildData(activeId);
        }
        setIsLoading(false);
        return;
      } catch (err) {
        console.error('Error fetching children:', err);
      }
    }

    // Offline / local fallback mode
    const fallbackList = [...localChildrenRef.current];
    setChildren(fallbackList);
    let activeId = selectedProfileId;
    if (!activeId || !fallbackList.some(c => c.id === activeId)) {
      activeId = fallbackList.length > 0 ? fallbackList[0].id : '';
    }
    setSelectedProfileId(activeId);
    if (activeId) {
      syncLocalToState(activeId);
    }
    setIsLoading(false);
  }, [selectedProfileId, checkBackend, refreshChildData, syncLocalToState]);

  // Initial load & reactive Storage listener
  useEffect(() => {
    refreshChildrenList();
    const unsubscribe = Storage.subscribe('*', () => {
      refreshChildrenList();
    });
    return () => {
      unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle selected child profile changes
  const selectProfile = useCallback(async (id: string) => {
    setSelectedProfileId(id);
    if (backendAvailable) {
      await refreshChildData(id);
    } else {
      syncLocalToState(id);
    }
  }, [backendAvailable, refreshChildData, syncLocalToState]);

  /**
   * Action methods
   */
  const changeDeviceLock = useCallback(async (isLocked: boolean) => {
    setDeviceLocked(isLocked);
    const target = localScreentimeRef.current[selectedProfileId] || {
      child_id: selectedProfileId,
      daily_limit_minutes: limitMinutes,
      current_usage_minutes: currentUsageMinutes,
      is_locked_remotely: isLocked,
    };
    target.is_locked_remotely = isLocked;
    localScreentimeRef.current[selectedProfileId] = target;
    await Storage.setScreentime(selectedProfileId, target);

    if (backendAvailable) {
      try {
        await ParentalRepository.remoteLock(selectedProfileId, isLocked);
      } catch (e) {
        console.error(e);
      }
    }
  }, [backendAvailable, selectedProfileId, limitMinutes, currentUsageMinutes]);

  const changeChildDailyLimit = useCallback(async (minutes: number) => {
    setLimitMinutes(minutes);
    const target = localScreentimeRef.current[selectedProfileId] || {
      child_id: selectedProfileId,
      daily_limit_minutes: minutes,
      current_usage_minutes: currentUsageMinutes,
      is_locked_remotely: deviceLocked,
    };
    target.daily_limit_minutes = minutes;
    localScreentimeRef.current[selectedProfileId] = target;
    await Storage.setScreentime(selectedProfileId, target);

    if (backendAvailable) {
      try {
        await ParentalRepository.updateDailyLimit(selectedProfileId, minutes);
      } catch (e) {
        console.error(e);
      }
    }
  }, [backendAvailable, selectedProfileId, currentUsageMinutes, deviceLocked]);

  const toggleBlockApp = useCallback(async (appId: string, appName: string) => {
    // Optimistic UI state flip
    setApps(prev => {
      const updated = prev.map(a => a.app_id === appId ? { ...a, is_blocked: !a.is_blocked } : a);
      Storage.setApps(selectedProfileId, updated);
      return updated;
    });

    const list = localAppsRef.current[selectedProfileId] || [];
    const app = list.find(a => a.app_id === appId);
    if (app) app.is_blocked = !app.is_blocked;

    if (backendAvailable) {
      try {
        await ParentalRepository.toggleAppLockout(selectedProfileId, appId);
      } catch (e) {
        console.error(e);
      }
    }
  }, [backendAvailable, selectedProfileId]);

  const toggleFilterCategory = useCallback(async (categoryName: string, isBlocked: boolean) => {
    setBlockedCategories(prev => ({ ...prev, [categoryName]: isBlocked }));
    if (backendAvailable) {
      try {
        await ParentalRepository.toggleFilterCategory(selectedProfileId, categoryName, isBlocked);
      } catch (e) {
        console.error(e);
      }
    } else {
      const target = localFiltersRef.current[selectedProfileId];
      if (target) target.blocked_categories[categoryName] = isBlocked;
    }
  }, [backendAvailable, selectedProfileId]);

  const addBlacklistUrl = useCallback(async (url: string) => {
    if (!url) return;
    const cleanUrl = url.trim().toLowerCase();
    setBlockedUrls(prev => [...prev, cleanUrl]);

    if (backendAvailable) {
      try {
        await ParentalRepository.blacklistUrl(selectedProfileId, cleanUrl);
      } catch (e) {
        console.error(e);
      }
    } else {
      const target = localFiltersRef.current[selectedProfileId];
      if (target) target.blacklisted_urls.push(cleanUrl);
    }
  }, [backendAvailable, selectedProfileId]);

  const removeBlacklistUrl = useCallback(async (url: string) => {
    setBlockedUrls(prev => prev.filter(u => u !== url));
    if (backendAvailable) {
      try {
        await ParentalRepository.removeBlacklistUrl(selectedProfileId, url);
      } catch (e) {
        console.error(e);
      }
    } else {
      const target = localFiltersRef.current[selectedProfileId];
      if (target) target.blacklisted_urls = target.blacklisted_urls.filter(u => u !== url);
    }
  }, [backendAvailable, selectedProfileId]);


  const generateLinkingCode = useCallback(async () => {
    if (backendAvailable) {
      try {
        const res = await ParentalRepository.generateLinkingCode(selectedProfileId);
        if (res?.linking_code) {
          await Storage.setPendingCode(res.linking_code);
        }
        // Reload children to display the generated linking code
        await refreshChildrenList();
        return res.linking_code;
      } catch (e) {
        console.error(e);
      }
    }

    // Local code generation & persistence to Storage DB
    const partLeft = Math.floor(100 + Math.random() * 900);
    const partRight = Math.floor(100 + Math.random() * 900);
    const mockCode = `${partLeft}-${partRight}`;

    await Storage.setPendingCode(mockCode);
    const activeChild = localChildrenRef.current.find(c => c.id === selectedProfileId);
    if (activeChild) {
      activeChild.linking_code = mockCode;
    }
    setChildren([...localChildrenRef.current]);
    await Storage.setChildrenList(localChildrenRef.current);
    return mockCode;
  }, [backendAvailable, selectedProfileId, refreshChildrenList]);

  const createChildProfile = useCallback(async (name: string, age: number, linkingCode: string) => {
    await Storage.setPendingCode(linkingCode);

    if (backendAvailable) {
      try {
        const newChild = await ParentalRepository.createChild(name, age, linkingCode);
        await refreshChildrenList();
        return newChild;
      } catch (e) {
        console.error('Error creating child profile:', e);
        throw e;
      }
    } else {
      const newChild = {
        id: (localChildrenRef.current.length + 1).toString(),
        name,
        age,
        avatarColor: localChildrenRef.current.length % 2 === 0 ? '#EC4899' : '#A855F7',
        battery: '100%',
        batteryLevel: 100,
        device: 'Child Device',
        deviceName: 'Child Device',
        lastActive: 'Active Now',
        is_active_online: true,
        linking_code: linkingCode,
        appUsage: []
      };
      localChildrenRef.current.push(newChild);
      setChildren([...localChildrenRef.current]);
      setSelectedProfileId(newChild.id);
      await Storage.setChildrenList(localChildrenRef.current);
      return newChild;
    }
  }, [backendAvailable, refreshChildrenList]);

  const addNewGeofence = useCallback(async (name: string, lat: number, lng: number, radius: number) => {
    const newFence: GeofenceZone = {
      id: String(Math.random()),
      child_id: selectedProfileId,
      name,
      latitude: lat,
      longitude: lng,
      radius_meters: radius,
      status: 'ACTIVE',
    };
    setGeofences(prev => [...prev, newFence]);

    if (backendAvailable) {
      try {
        await ParentalRepository.createGeofence(selectedProfileId, name, lat, lng, radius);
      } catch (e) {
        console.error(e);
      }
    } else {
      const list = localGeofencesRef.current[selectedProfileId] || [];
      list.push(newFence);
    }
  }, [backendAvailable, selectedProfileId]);

  const triggerSOS = useCallback(async (lat: number, lng: number, message: string) => {
    setSosActive(true);
    if (backendAvailable) {
      try {
        await ParentalRepository.triggerSOS(selectedProfileId, lat, lng, message);
      } catch (e) {
        console.error(e);
      }
    }
  }, [backendAvailable, selectedProfileId]);

  const resolveSOS = useCallback(() => {
    setSosActive(false);
  }, []);

  const updateSosPreferences = useCallback(async (emailEnabled: boolean, email: string, phoneEnabled: boolean, phone: string) => {
    if (backendAvailable) {
      try {
        await ParentalRepository.updateSOSPreferences(selectedProfileId, emailEnabled, email, phoneEnabled, phone);
      } catch (e) {
        console.error(e);
      }
    } else {
      localSosPreferencesRef.current[selectedProfileId] = {
        email_enabled: emailEnabled,
        parent_email: email,
        phone_enabled: phoneEnabled,
        parent_phone: phone,
      };
    }
  }, [backendAvailable, selectedProfileId]);

  const getSosPreferences = useCallback(() => {
    if (backendAvailable) {
      // Fetch or use mock
      return localSosPreferencesRef.current[selectedProfileId] || { email_enabled: false, parent_email: '', phone_enabled: false, parent_phone: '' };
    }
    return localSosPreferencesRef.current[selectedProfileId] || { email_enabled: false, parent_email: '', phone_enabled: false, parent_phone: '' };
  }, [backendAvailable, selectedProfileId]);

  const unlinkChildDevice = useCallback(async (childId: string) => {
    try {
      await Storage.setLinkedChild(null);
      await Storage.removeLinkedChild();
      await Storage.setChildId('');
    } catch {}

    if (backendAvailable) {
      try {
        await ParentalRepository.unlinkChildDevice(childId);
      } catch (e) {
        console.error(e);
      }
    }

    localChildrenRef.current = localChildrenRef.current.filter(c => c.id !== childId);
    setChildren(prev => prev.filter(c => c.id !== childId));
    if (selectedProfileId === childId) {
      const remaining = localChildrenRef.current;
      setSelectedProfileId(remaining.length > 0 ? remaining[0].id : '');
    }

    try {
      await refreshChildrenList();
    } catch {}
  }, [backendAvailable, selectedProfileId, refreshChildrenList]);

  return {
    isLoading,
    backendAvailable,
    children,
    selectedProfileId,
    selectProfile,
    unlinkChildDevice,
    deviceLocked,
    changeDeviceLock,
    limitMinutes,
    currentUsageMinutes,
    changeChildDailyLimit,
    apps,
    toggleBlockApp,
    blockedUrls,
    addBlacklistUrl,
    removeBlacklistUrl,
    blockedCategories,
    toggleFilterCategory,
    location,
    geofences,
    addNewGeofence,
    reportSummary,
    sosActive,
    triggerSOS,
    resolveSOS,
    activeAlerts,
    updateSosPreferences,
    getSosPreferences,
    generateLinkingCode,
    createChildProfile,
    refreshData: () => refreshChildrenList(),
  };
}
