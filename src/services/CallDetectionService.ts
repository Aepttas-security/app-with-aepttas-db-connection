import { useEffect, useRef, useState } from 'react';
import { Alert, AppState, PermissionsAndroid, Platform } from 'react-native';

let CallDetector: any = null;
if (Platform.OS === 'android') {
  try {
    CallDetector = require('react-native-call-detection').default;
  } catch (e) {
    console.log('Call detection not available:', e);
  }
}

export interface CallState {
  number: string;
  status: 'Incoming' | 'Outgoing' | 'Ended' | 'Missed';
  timestamp: Date;
}

interface CallDetectionServiceProps {
  onCallDetected: (callState: CallState) => void;
  onCallEnded: (callState: CallState) => void;
}

export const useCallDetection = ({ onCallDetected, onCallEnded }: CallDetectionServiceProps) => {
  const [isActive, setIsActive] = useState(false);
  const [callPermissionGranted, setCallPermissionGranted] = useState(false);
  const [callListener, setCallListener] = useState<any>(null);
  const appState = useRef(AppState.currentState);
  const currentCall = useRef<CallState | null>(null);

  const requestAndroidPermissions = async (): Promise<boolean> => {
    try {
      if (Platform.OS !== 'android') return true;

      const permissions = [
        PermissionsAndroid.PERMISSIONS.READ_PHONE_STATE,
        PermissionsAndroid.PERMISSIONS.READ_CALL_LOG,
      ];

      const results = await PermissionsAndroid.requestMultiple(permissions);
      const allGranted = Object.values(results).every(
        (result) => result === PermissionsAndroid.RESULTS.GRANTED
      );

      if (allGranted) {
        setCallPermissionGranted(true);
        return true;
      } else {
        Alert.alert(
          'Permission Required',
          'Please grant phone permissions to detect spam calls.',
          [{ text: 'OK' }]
        );
        return false;
      }
    } catch (error) {
      console.error('Permission error:', error);
      return false;
    }
  };

  const startAndroidDetection = () => {
    if (Platform.OS !== 'android' || !CallDetector) {
      console.warn('Call detection not available on this platform');
      return;
    }

    try {
      if (callListener) {
        callListener.dispose();
        setCallListener(null);
      }

      const listener = new CallDetector(
        (callState: any) => {
          console.log('📞 Android Call State:', callState);

          if (callState.status === 'Incoming' || callState.status === 'Ringing') {
            const state: CallState = {
              number: callState.number || 'Unknown',
              status: 'Incoming',
              timestamp: new Date(),
            };
            currentCall.current = state;
            onCallDetected(state);
          }

          if (callState.status === 'Dialing' || callState.status === 'Outgoing') {
            const state: CallState = {
              number: callState.number || 'Unknown',
              status: 'Outgoing',
              timestamp: new Date(),
            };
            currentCall.current = state;
            onCallDetected(state);
          }

          if (callState.status === 'Disconnected' || callState.status === 'Ended') {
            if (currentCall.current) {
              const endedState: CallState = {
                ...currentCall.current,
                status: 'Ended',
                timestamp: new Date(),
              };
              onCallEnded(endedState);
              currentCall.current = null;
            }
          }

          if (callState.status === 'Missed') {
            if (currentCall.current) {
              const missedState: CallState = {
                ...currentCall.current,
                status: 'Missed',
                timestamp: new Date(),
              };
              onCallEnded(missedState);
              currentCall.current = null;
            }
          }
        },
        (error: any) => {
          console.error('❌ Call detection error:', error);
        },
        true,
        true,
        false
      );

      setCallListener(listener);
      setIsActive(true);
      console.log('✅ Android call detection started');
    } catch (error) {
      console.error('Failed to start Android call detection:', error);
    }
  };

  const startDetection = async () => {
    if (Platform.OS === 'android') {
      const hasPermission = await requestAndroidPermissions();
      if (hasPermission) {
        startAndroidDetection();
      }
    }
  };

  const stopDetection = () => {
    if (Platform.OS === 'android' && callListener) {
      try {
        callListener.dispose();
        setCallListener(null);
        setIsActive(false);
        console.log('🛑 Android call detection stopped');
      } catch (error) {
        console.error('Error stopping call detection:', error);
      }
    }
  };

  const toggleDetection = () => {
    if (isActive) {
      stopDetection();
    } else {
      startDetection();
    }
  };

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (appState.current === 'background' && nextAppState === 'active') {
        if (isActive && Platform.OS === 'android') {
          startAndroidDetection();
        }
      }
      appState.current = nextAppState;
    });

    return () => {
      subscription.remove();
    };
  }, [isActive]);

  useEffect(() => {
    return () => {
      stopDetection();
    };
  }, []);

  return {
    startDetection,
    stopDetection,
    toggleDetection,
    isActive,
    callPermissionGranted,
  };
};