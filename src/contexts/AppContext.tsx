import React, { createContext, useContext, useState, ReactNode, useEffect, useCallback } from 'react';
import api, { DashboardStats, Alert, BlockedNumber, Settings, Call } from '../services/api';

interface AppContextType {
  isCallActive: boolean;
  setIsCallActive: (active: boolean) => void;
  currentCallNumber: string;
  setCurrentCallNumber: (number: string) => void;
  callHistory: Call[];
  addCallHistory: (call: { number: string; type: 'Incoming' | 'Outgoing' }) => void;

  dashboardData: DashboardStats | null;
  alerts: Alert[];
  blockedNumbers: BlockedNumber[];
  spamReports: any[];
  unreadCount: number;
  loading: boolean;
  settings: Settings | null;
  currentUser: { user_id: number; name: string; email: string } | null;

  refreshDashboard: () => Promise<void>;
  refreshBlockedNumbers: () => Promise<void>;
  refreshSpamReports: () => Promise<void>;
  refreshCallHistory: () => Promise<void>;
  refreshSettings: () => Promise<void>;
  markAlertRead: (alertId: number) => Promise<void>;
  blockNumber: (data: { phone_number: string; caller_name?: string; block_reason: string }) => Promise<void>;
  unblockNumber: (phoneNumber: string) => Promise<void>;
  updateSettings: (data: Partial<Settings>) => Promise<void>;
  setCurrentUser: (user: { user_id: number; name: string; email: string } | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isCallActive, setIsCallActive] = useState(false);
  const [currentCallNumber, setCurrentCallNumber] = useState('');
  const [callHistory, setCallHistory] = useState<Call[]>([]);

  const [dashboardData, setDashboardData] = useState<DashboardStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [blockedNumbers, setBlockedNumbers] = useState<BlockedNumber[]>([]);
  const [spamReports, setSpamReports] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [currentUser, setCurrentUser] = useState<{ user_id: number; name: string; email: string } | null>(null);

  const refreshDashboard = useCallback(async () => {
    try {
      const data = await api.getDashboard();
      setDashboardData(data);
      if (data.recent_alerts) {
        setAlerts(data.recent_alerts);
        setUnreadCount(data.recent_alerts.filter(a => !a.is_read).length);
      }
    } catch (error) {
      console.error('Failed to refresh dashboard:', error);
    }
  }, []);

  const refreshBlockedNumbers = useCallback(async () => {
    try {
      const data = await api.getBlockedNumbers();
      setBlockedNumbers(data.map(b => ({
        phone_number: b.phone_number,
        caller_name: b.caller_name,
        block_reason: b.block_reason,
        block_date: b.block_date,
        risk_score: (b as any).risk_score || 0
      })) as any);
    } catch (error) {
      console.error('Failed to refresh blocked numbers:', error);
    }
  }, []);

  const refreshSpamReports = useCallback(async () => {
    try {
      const data = await api.getSpamLog();
      setSpamReports(data);
    } catch (error) {
      console.error('Failed to refresh spam reports:', error);
    }
  }, []);

  const refreshCallHistory = useCallback(async () => {
    try {
      const data = await api.getCallHistory();
      setCallHistory(data);
    } catch (error) {
      console.error('Failed to refresh call history:', error);
    }
  }, []);

  const refreshSettings = useCallback(async () => {
    try {
      const data = await api.getSettings();
      setSettings(data);
    } catch (error) {
      console.error('Failed to refresh settings:', error);
    }
  }, []);

  const markAlertRead = async (alertId: number) => {
    try {
      await api.markAlertRead(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark alert as read:', error);
    }
  };

  const blockNumber = async (data: { phone_number: string; caller_name?: string; block_reason: string }) => {
    try {
      if (!data.phone_number) {
        console.error('Cannot block number: phone_number is undefined');
        return;
      }
      await api.blockNumber(data);
      await refreshBlockedNumbers();
    } catch (error) {
      console.error('Failed to block number:', error);
      throw error;
    }
  };

  const unblockNumber = async (phoneNumber: string) => {
    try {
      if (!phoneNumber) {
        console.error('Cannot unblock number: phoneNumber is undefined');
        return;
      }
      await api.unblockCaller(phoneNumber);
      await refreshBlockedNumbers();
    } catch (error) {
      console.error('Failed to unblock number:', error);
      throw error;
    }
  };

  const updateSettings = async (data: Partial<Settings>) => {
    try {
      await api.updateSettings(data);
      await refreshSettings();
    } catch (error) {
      console.error('Failed to update settings:', error);
      throw error;
    }
  };

  const addCallHistory = (call: { number: string; type: 'Incoming' | 'Outgoing' }) => {
    console.log('Adding call to history:', call);
    refreshCallHistory();
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
          await refreshDashboard();
          await new Promise(resolve => setTimeout(() => resolve(true), 500));
          await refreshBlockedNumbers();
          await new Promise(resolve => setTimeout(() => resolve(true), 500));
          await refreshSpamReports();
          await new Promise(resolve => setTimeout(() => resolve(true), 500));
          await refreshCallHistory();
          await new Promise(resolve => setTimeout(() => resolve(true), 500));
          await refreshSettings();
      } catch (e) {
          console.error('Initial data load failed:', e);
      } finally {
          setLoading(false);
      }
    };
    init();
  }, [refreshDashboard, refreshBlockedNumbers, refreshSpamReports, refreshCallHistory, refreshSettings]);

  return (
    <AppContext.Provider
      value={{
        isCallActive,
        setIsCallActive,
        currentCallNumber,
        setCurrentCallNumber,
        callHistory,
        addCallHistory,
        dashboardData,
        alerts,
        blockedNumbers,
        spamReports,
        unreadCount,
        loading,
        settings,
        refreshDashboard,
        refreshBlockedNumbers,
        refreshSpamReports,
        refreshCallHistory,
        refreshSettings,
        markAlertRead,
        blockNumber,
        unblockNumber,
        updateSettings,
        currentUser,
        setCurrentUser,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
