import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { useCallDetection as useCallDetectionService } from '../services/CallDetectionService';
import api from '../services/api';

interface CallerInfo {
  name: string;
  number: string;
  carrier: string;
  location: string;
  riskScore: number;
  isSpam: boolean;
  isBlocked: boolean;
  isContact: boolean;
  reportCount?: number;
}

export const useCallDetection = () => {
  const [callerInfo, setCallerInfo] = useState<CallerInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [currentNumber, setCurrentNumber] = useState('');
  const [contacts, setContacts] = useState<any[]>([]);

  // Load contacts only on native platforms
  useEffect(() => {
    const loadContacts = async () => {
      if (Platform.OS === 'web') {
        console.log('📱 Contacts not supported on web');
        setContacts([]);
        return;
      }
      try {
        const { getLocalContacts } = await import('../services/ContactService');
        const localContacts = await getLocalContacts();
        setContacts(localContacts);
      } catch (error) {
        console.log('Contacts not available:', error);
        setContacts([]);
      }
    };
    loadContacts();
  }, []);

  const fetchCallerInfo = async (phoneNumber: string) => {
    setIsLoading(true);
    setCurrentNumber(phoneNumber);
    setShowPopup(true);

    try {
      // Check contacts first (if on native)
      let contactName: string | null = null;
      let isContact = false;

      if (Platform.OS !== 'web' && contacts.length > 0) {
        const { getContactName } = await import('../services/ContactService');
        contactName = getContactName(contacts, phoneNumber);
        isContact = !!contactName;
      }

      // Fetch from backend
      const result = await api.searchNumber(phoneNumber);

      const info: CallerInfo = {
        name: contactName || result?.caller_name || 'Unknown Caller',
        number: phoneNumber,
        carrier: result?.carrier || 'Unknown Carrier',
        location: result?.location || 'Unknown Location',
        riskScore: result?.risk_score || 30,
        isSpam: result?.is_spam || false,
        isBlocked: result?.is_blocked || false,
        isContact: isContact,
        reportCount: result?.report_count || 0,
      };

      setCallerInfo(info);
    } catch (error) {
      console.error('Failed to fetch caller info:', error);
      setCallerInfo({
        name: 'Unknown Caller',
        number: phoneNumber,
        carrier: 'Unknown Carrier',
        location: 'Unknown Location',
        riskScore: 30,
        isSpam: false,
        isBlocked: false,
        isContact: false,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const { isActive, startDetection, stopDetection, toggleDetection } = useCallDetectionService({
    onCallDetected: (callState) => {
      console.log('📞 Call detected:', callState);
      fetchCallerInfo(callState.number);
    },
    onCallEnded: (callState) => {
      console.log('📞 Call ended:', callState);
      setTimeout(() => {
        setShowPopup(false);
        setCallerInfo(null);
      }, 1000);
    },
  });

  const blockNumber = async () => {
    if (!callerInfo) return;
    try {
      await api.blockNumber({
        phone_number: callerInfo.number,
        caller_name: callerInfo.name,
        block_reason: 'Blocked from call popup',
      });
      setCallerInfo({ ...callerInfo, isBlocked: true });
      setShowPopup(false);  // ✅ Correct - use setShowPopup
    } catch (error) {
      console.error('Failed to block number:', error);
    }
  };

  const reportSpam = async () => {
    if (!callerInfo) return;
    try {
      await api.createReport({
        caller_number: callerInfo.number,
        report_type: 'Spam',
        description: 'Reported from call popup',
      });
      setShowPopup(false);  // ✅ Correct - use setShowPopup
    } catch (error) {
      console.error('Failed to report spam:', error);
    }
  };

  const closePopup = () => {
    setShowPopup(false);
    setCallerInfo(null);
  };

  return {
    showPopup,
    callerInfo,
    isLoading,
    currentNumber,
    isActive,
    startDetection,
    stopDetection,
    toggleDetection,
    fetchCallerInfo,
    blockNumber,
    reportSpam,
    closePopup,
  };
};