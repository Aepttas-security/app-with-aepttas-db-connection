import { useState, useEffect, useCallback } from 'react';
import { getCallerBaseUrl } from '../config/apiConfig';
import { Storage } from '../utils/storage';
import CallDetection from '../native/CallDetection';

export interface BlockedNumber {
  number: string;
  name: string;
  reason: string;
  date: string;
}

export interface SpamCall {
  name: string;
  number: string;
  riskScore: number;
  date: string;
}

export interface CallReport {
  id: string;
  number: string;
  type: string;
  description: string;
  timestamp: string;
}

export interface MockCall {
  name: string;
  number: string;
  riskScore: number;
  type: 'Normal' | 'Spam' | 'Scam' | 'High-Risk' | 'Suspicious';
  carrier: string;
  location: string;
  frequency: string;
}

export function useCallerIntelligence(childId: string = '1') {
  const [blockedNumbers, setBlockedNumbers] = useState<BlockedNumber[]>([]);
  const [spamCalls, setSpamCalls] = useState<SpamCall[]>([]);
  const [reportHistory, setReportHistory] = useState<CallReport[]>([]);
  const [callHistory, setCallHistory] = useState<MockCall[]>([]);
  const [autoBlockEnabled, setAutoBlockEnabled] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const fetchFromBackendDB = useCallback(async () => {
    setIsLoading(true);
    let realDeviceLogs: MockCall[] = [];
    const deviceSpamCalls: SpamCall[] = [];
    const deviceBlockedNumbers: BlockedNumber[] = [];

    // 1. Fetch real device call logs from phone hardware via native bridge
    try {
      const deviceLogs = await CallDetection.getDeviceCallLogs(100);
      if (Array.isArray(deviceLogs) && deviceLogs.length > 0) {
        deviceLogs.forEach(log => {
          let callType: 'Normal' | 'Spam' | 'Scam' | 'High-Risk' | 'Suspicious' = 'Normal';
          if (log.isBlocked) {
            callType = 'Scam';
            deviceBlockedNumbers.push({
              number: log.phoneNumber || '',
              name: log.callerName || 'Blocked Caller',
              reason: 'Blocked on Mobile Device',
              date: log.timestamp ? log.timestamp.split(' ')[0] : 'Recent',
            });
          } else if (log.isSpam || log.riskScore >= 70) {
            callType = 'Spam';
            deviceSpamCalls.push({
              name: log.callerName || 'Spam Caller',
              number: log.phoneNumber || '',
              riskScore: log.riskScore || 85,
              date: log.timestamp || 'Recent',
            });
          } else if (log.riskScore >= 40) {
            callType = 'Suspicious';
          }

          realDeviceLogs.push({
            name: log.callerName || 'Unknown Caller',
            number: log.phoneNumber || '',
            riskScore: log.riskScore || (log.isBlocked ? 100 : log.isSpam ? 85 : 5),
            type: callType,
            carrier: 'Cellular Network',
            location: 'Mobile Device',
            frequency: `${log.callType} • ${log.duration || '00:00'}`,
          });
        });
      }
    } catch (e) {
      console.warn('Native device call logs error:', e);
    }

    // 2. Fetch locally persisted user-blocked numbers & preferences
    try {
      const localData = await Storage.getCallerIntel();
      if (localData) {
        if (Array.isArray(localData.blockedNumbers)) {
          localData.blockedNumbers.forEach((b: BlockedNumber) => {
            if (!deviceBlockedNumbers.some(d => d.number === b.number)) {
              deviceBlockedNumbers.push(b);
            }
          });
        }
        if (typeof localData.autoBlockEnabled === 'boolean') {
          setAutoBlockEnabled(localData.autoBlockEnabled);
        }
        if (typeof localData.notificationsEnabled === 'boolean') {
          setNotificationsEnabled(localData.notificationsEnabled);
        }
      }
    } catch {}

    // 3. Set purely mobile-derived data
    setCallHistory(realDeviceLogs);
    setSpamCalls(deviceSpamCalls);
    setBlockedNumbers(deviceBlockedNumbers);

    // Optional: sync preferences with backend without pulling mock calls
    try {
      const baseUrl = getCallerBaseUrl();
      const intelRes = await fetch(`${baseUrl}/api/caller-intel/${childId}`);
      if (intelRes.ok) {
        const data = await intelRes.json();
        if (typeof data.autoBlockEnabled === 'boolean') setAutoBlockEnabled(data.autoBlockEnabled);
        if (typeof data.notificationsEnabled === 'boolean') setNotificationsEnabled(data.notificationsEnabled);
      }
    } catch {}

    setIsLoading(false);
  }, [childId]);

  const saveToStorage = useCallback(async (updated: any) => {
    try {
      await Storage.setCallerIntel(updated);
    } catch (err) {
      console.error('Error saving caller intelligence to storage:', err);
    }
  }, []);

  useEffect(() => {
    fetchFromBackendDB();
  }, [fetchFromBackendDB]);

  const addBlockedNumber = useCallback(async (number: string, name: string, reason: string) => {
    const newEntry: BlockedNumber = {
      number,
      name: name || 'Spam Number',
      reason: reason || 'User Blocked',
      date: new Date().toISOString().split('T')[0],
    };
    const updated = [newEntry, ...blockedNumbers.filter(b => b.number !== number)];
    setBlockedNumbers(updated);
    saveToStorage({ blockedNumbers: updated, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled });

    try {
      await fetch(`${getCallerBaseUrl()}/api/blocked`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: number, caller_name: name, block_reason: reason }),
      });
      await fetchFromBackendDB();
    } catch (e) {
      console.error('Backend add blocked number error:', e);
    }
  }, [blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled, saveToStorage, fetchFromBackendDB]);

  const removeBlockedNumber = useCallback(async (number: string) => {
    const updated = blockedNumbers.filter(b => b.number !== number);
    setBlockedNumbers(updated);
    saveToStorage({ blockedNumbers: updated, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled });

    try {
      await fetch(`${getCallerBaseUrl()}/api/blocked/${encodeURIComponent(number)}`, {
        method: 'DELETE',
      });
      await fetchFromBackendDB();
    } catch (e) {
      console.error('Backend delete blocked number error:', e);
    }
  }, [blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled, saveToStorage, fetchFromBackendDB]);

  const reportCall = useCallback(async (number: string, type: string, description: string) => {
    const newReport: CallReport = {
      id: String(Date.now()),
      number,
      type,
      description,
      timestamp: new Date().toLocaleString(),
    };
    const updatedReports = [newReport, ...reportHistory];
    setReportHistory(updatedReports);
    saveToStorage({ blockedNumbers, spamCalls, reportHistory: updatedReports, callHistory, autoBlockEnabled, notificationsEnabled });

    try {
      await fetch(`${getCallerBaseUrl()}/api/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caller_number: number, report_reason: `${type}: ${description}` }),
      });
      await fetchFromBackendDB();
    } catch (e) {
      console.error('Backend report call error:', e);
    }
  }, [blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled, saveToStorage, fetchFromBackendDB]);

  const toggleAutoBlock = useCallback(async (val: boolean) => {
    setAutoBlockEnabled(val);
    saveToStorage({ blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled: val, notificationsEnabled });

    try {
      await fetch(`${getCallerBaseUrl()}/api/caller-intel/${childId}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_block_enabled: val }),
      });
      await fetchFromBackendDB();
    } catch (e) {
      console.error('Backend toggle auto block error:', e);
    }
  }, [blockedNumbers, spamCalls, reportHistory, callHistory, notificationsEnabled, saveToStorage, childId, fetchFromBackendDB]);

  const toggleNotifications = useCallback(async (val: boolean) => {
    setNotificationsEnabled(val);
    saveToStorage({ blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled, notificationsEnabled: val });

    try {
      await fetch(`${getCallerBaseUrl()}/api/caller-intel/${childId}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notifications_enabled: val }),
      });
      await fetchFromBackendDB();
    } catch (e) {
      console.error('Backend toggle notifications error:', e);
    }
  }, [blockedNumbers, spamCalls, reportHistory, callHistory, autoBlockEnabled, saveToStorage, childId, fetchFromBackendDB]);

  return {
    blockedNumbers,
    spamCalls,
    reportHistory,
    callHistory,
    autoBlockEnabled,
    notificationsEnabled,
    isLoading,
    addBlockedNumber,
    removeBlockedNumber,
    reportCall,
    toggleAutoBlock,
    toggleNotifications,
    refreshData: fetchFromBackendDB,
  };
}
