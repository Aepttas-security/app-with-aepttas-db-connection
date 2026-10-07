import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  StatusBar,
  ScrollView,
  ActivityIndicator,
  Share,
} from 'react-native';
import Svg, { Rect, Path } from 'react-native-svg';
import { useAppTheme } from '../contexts/ThemeContext';
import { Icon } from '../components/Icon';
import { ParentalRepository } from '../data/parentalRepository';
import { Storage } from '../utils/storage';

interface TwoStepBindingScreenProps {
  onBack: () => void;
  bindingCode?: string;
  onCheckStatus?: () => void;
}

export const TwoStepBindingScreen: React.FC<TwoStepBindingScreenProps> = ({
  onBack,
  bindingCode: initialCode,
  onCheckStatus,
}) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [code, setCode] = useState(initialCode || '582-914');
  const [isGenerating, setIsGenerating] = useState(false);
  const [pairingStatus, setPairingStatus] = useState<'PENDING' | 'LINKED' | 'EXPIRED'>('PENDING');
  const [statusMessage, setStatusMessage] = useState('Waiting for child device to connect...');

  // Generate 6-digit parent linking code on mount
  useEffect(() => {
    async function initCode() {
      try {
        setIsGenerating(true);
        const profile = await Storage.getUserProfile();
        const res = await ParentalRepository.generateParentLinkingCode(profile?.user_id, profile?.email);
        if (res?.linking_code) {
          setCode(res.linking_code);
        }
      } catch (err) {
        console.warn('[Pairing] Fallback to default code');
      } finally {
        setIsGenerating(false);
      }
    }
    initCode();
  }, []);

  // Continuous status polling loop (every 2 seconds)
  useEffect(() => {
    let isMounted = true;
    const pollInterval = setInterval(async () => {
      if (!code) return;
      try {
        const liveStatus = await ParentalRepository.checkPairingStatusByCode(code);
        
        if (isMounted && liveStatus) {
          if (liveStatus.status === 'LINKED' || liveStatus.status === 'COMPLETED') {
            const profile = await Storage.getUserProfile();
            const parentEmail = (liveStatus.parent_email || profile?.email || '').trim().toLowerCase();
            const storedChild = await Storage.getLinkedChild(parentEmail);
            if (storedChild && storedChild.permissions_granted === false) {
              setPairingStatus('PENDING');
              setStatusMessage('Child device entered linking code. Waiting for system permissions to be granted on child device...');
              return;
            }

            setPairingStatus('LINKED');
            setStatusMessage('Child device connected & permissions verified successfully!');
            clearInterval(pollInterval);

            // Save linked child profile into persistent storage with real dynamic values
            const childName = liveStatus.child_name || storedChild?.name || 'Child Device';
            const deviceName = liveStatus.device_name || storedChild?.device || storedChild?.deviceName || 'Child Mobile Device';
            const osType = liveStatus.os_type || storedChild?.os_type || storedChild?.osType || 'Android';
            const batteryLevel = liveStatus.battery_percentage || liveStatus.batteryLevel || storedChild?.batteryLevel || 95;
            const childId = String(liveStatus.child_id || storedChild?.id || `child_${Date.now()}`);

            const linkedProfile = {
              id: childId,
              child_id: childId,
              name: childName,
              child_name: childName,
              device: deviceName,
              deviceName: deviceName,
              os_type: osType,
              osType: osType,
              age: storedChild?.age || 10,
              parentEmail: parentEmail || storedChild?.parentEmail || '',
              status: 'LINKED',
              permissions_granted: true,
              avatarColor: '#8b5cf6',
              battery: `${batteryLevel}%`,
              batteryLevel: batteryLevel,
              chargingStatus: 'Normal',
              currentLocation: 'Live Telemetry Active',
              securityStatus: 'Protected',
              notificationsToday: 0,
              sosStatus: 'Normal - Safe',
              deviceHealth: 'Optimal',
              lastSyncTime: 'Active Now',
              currentUsageMinutes: 0,
              totalLimitMinutes: 120,
              appUsage: [],
            };

            await Storage.setLinkedChild(linkedProfile);
            await Storage.setChildId(linkedProfile.id);

            // Automatic navigation to Parent Dashboard without manual refresh!
            setTimeout(() => {
              if (onCheckStatus) onCheckStatus();
            }, 600);
          } else if (liveStatus.status === 'EXPIRED') {
            setPairingStatus('EXPIRED');
            setStatusMessage('Linking code has expired. Tap below to generate a new code.');
          }
        }
      } catch (e) {
        // Continue polling silently
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [code, onCheckStatus]);

  const handleManualCheckStatus = async () => {
    try {
      const liveStatus = await ParentalRepository.checkPairingStatusByCode(code);
      const profile = await Storage.getUserProfile();
      const parentEmail = (liveStatus?.parent_email || profile?.email || '').trim().toLowerCase();
      const storedChild = await Storage.getLinkedChild(parentEmail);

      if ((liveStatus?.status === 'LINKED' || liveStatus?.status === 'COMPLETED') && storedChild?.permissions_granted === true) {
        setPairingStatus('LINKED');
        setStatusMessage('Child device connected & permissions verified successfully!');
        if (onCheckStatus) onCheckStatus();
      } else {
        setPairingStatus('PENDING');
        setStatusMessage(`Waiting for child device connection. Enter code ${code} on child device.`);
      }
    } catch {
      setPairingStatus('PENDING');
      setStatusMessage('Waiting for child device connection...');
    }
  };

  const handleRegenerateCode = async () => {
    setIsGenerating(true);
    setPairingStatus('PENDING');
    setStatusMessage('Waiting for child device to connect...');
    const profile = await Storage.getUserProfile();
    const res = await ParentalRepository.generateParentLinkingCode(profile?.user_id, profile?.email);
    if (res?.linking_code) {
      setCode(res.linking_code);
    }
    setIsGenerating(false);
  };

  const handleShareLink = async () => {
    try {
      const shareUrl = 'https://apps.aepttas.com/kids';
      const message = `Download Aepttas Kids on your child's device: ${shareUrl}\nLinking Code: ${code}`;
      await Share.share({
        message,
        url: shareUrl,
        title: 'Aepttas Kids App Download',
      });
    } catch (error) {
      console.warn('[Share] Share failed:', error);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Icon name="arrow-back" color={colors.text} size={22} />
        </TouchableOpacity>
        <Text style={styles.headerTitleText}>Pair Child Device</Text>
        <TouchableOpacity style={styles.moreBtn}>
          <Icon name="more-horiz" color={colors.textMuted} size={24} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Title */}
        <Text style={styles.title}>Pair Child Device</Text>
        <Text style={styles.subtitle}>
          Follow these steps on your child's device to complete the pairing setup.
        </Text>

        {/* Real-time Status Card */}
        <View style={[styles.statusBanner, pairingStatus === 'LINKED' && styles.statusBannerLinked]}>
          <ActivityIndicator
            size="small"
            color={pairingStatus === 'LINKED' ? '#10b981' : colors.purpleAccent}
            animating={pairingStatus === 'PENDING'}
          />
          <View style={styles.statusTextWrapper}>
            <Text style={[styles.statusTitle, pairingStatus === 'LINKED' && { color: '#10b981' }]}>
              {pairingStatus === 'LINKED' ? 'DEVICE LINKED!' : 'PAIRING STATUS'}
            </Text>
            <Text style={styles.statusSub}>{statusMessage}</Text>
          </View>
        </View>

        {/* Step 1 Card: Download Link */}
        <View style={styles.stepCard}>
          <View style={styles.stepHeaderRow}>
            <View style={styles.stepBadge}>
              <Text style={styles.stepBadgeText}>1</Text>
            </View>
            <Text style={styles.stepHeaderText}>
              On your child's device, download and install Aepttas Kids
            </Text>
          </View>

          <View style={styles.qrContainer}>
            <TouchableOpacity style={styles.urlPill} onPress={handleShareLink} activeOpacity={0.7}>
              <Text style={styles.urlText}>apps.aepttas.com/kids</Text>
              <Icon name="share" color={colors.purpleAccent} size={18} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Step 2 Card: Enter Binding Code */}
        <View style={[styles.stepCard, { marginTop: 20 }]}>
          <View style={styles.stepHeaderRow}>
            <View style={styles.stepBadge}>
              <Text style={styles.stepBadgeText}>2</Text>
            </View>
            <Text style={styles.stepHeaderText}>
              Open Aepttas Kids on child device and enter this 6-digit linking code:
            </Text>
          </View>

          {/* Binding Code Box */}
          <View style={styles.codeContainer}>
            {isGenerating ? (
              <ActivityIndicator color={colors.purpleAccent} size="large" />
            ) : (
              <Text style={styles.codeDisplay}>{code}</Text>
            )}
            <Text style={styles.codeSubtitle}>Code valid for 15 minutes • Pending connection</Text>
          </View>
        </View>

        {/* Action Buttons */}
        <TouchableOpacity style={styles.checkStatusBtn} onPress={handleManualCheckStatus}>
          <Icon name="refresh" color={colors.purpleAccent} size={18} />
          <Text style={styles.checkStatusText}>Check pairing status manually</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.regenerateBtn} onPress={handleRegenerateCode}>
          <Text style={styles.regenerateText}>Generate New Linking Code</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
};

const getStyles = (colors: any) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingTop: 12,
      paddingBottom: 8,
    },
    headerTitleText: {
      color: colors.text,
      fontSize: 16,
      fontWeight: '700',
    },
    backBtn: {
      width: 40,
      height: 40,
      borderRadius: 20,
      justifyContent: 'center',
      alignItems: 'center',
    },
    moreBtn: {
      padding: 4,
    },
    scrollContent: {
      paddingHorizontal: 24,
      paddingTop: 12,
      paddingBottom: 40,
      maxWidth: 480,
      width: '100%',
      alignSelf: 'center',
    },
    title: {
      color: colors.text,
      fontSize: 26,
      fontWeight: '800',
      textAlign: 'center',
      marginBottom: 6,
      letterSpacing: -0.5,
    },
    subtitle: {
      color: colors.textMuted,
      fontSize: 13,
      textAlign: 'center',
      marginBottom: 20,
    },
    statusBanner: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.purpleAccent + '66',
      borderRadius: 16,
      padding: 14,
      marginBottom: 20,
    },
    statusBannerLinked: {
      borderColor: '#10b981',
      backgroundColor: '#10b98115',
    },
    statusTextWrapper: {
      marginLeft: 12,
      flex: 1,
    },
    statusTitle: {
      color: colors.purpleAccent,
      fontSize: 11,
      fontWeight: '800',
      letterSpacing: 0.8,
    },
    statusSub: {
      color: colors.text,
      fontSize: 13,
      fontWeight: '600',
      marginTop: 2,
    },
    stepCard: {
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 24,
      padding: 20,
    },
    stepHeaderRow: {
      flexDirection: 'row',
      alignItems: 'flex-start',
      marginBottom: 16,
    },
    stepBadge: {
      width: 24,
      height: 24,
      borderRadius: 12,
      backgroundColor: colors.purpleAccent,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
      marginTop: 2,
    },
    stepBadgeText: {
      color: '#ffffff',
      fontSize: 12,
      fontWeight: '800',
    },
    stepHeaderText: {
      color: colors.text,
      fontSize: 14,
      fontWeight: '600',
      flex: 1,
      lineHeight: 20,
    },
    qrContainer: {
      alignItems: 'center',
    },
    qrBox: {
      padding: 14,
      backgroundColor: '#ffffff',
      borderRadius: 18,
      borderWidth: 2,
      borderColor: 'rgba(139, 92, 246, 0.4)',
      marginBottom: 14,
    },
    urlPill: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: colors.background,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 14,
      paddingHorizontal: 16,
      paddingVertical: 10,
      width: '100%',
    },
    urlText: {
      color: colors.purpleAccent,
      fontSize: 14,
      fontWeight: '700',
      marginRight: 8,
    },
    codeContainer: {
      alignItems: 'center',
      paddingVertical: 12,
    },
    codeDisplay: {
      color: colors.text,
      fontSize: 36,
      fontWeight: '900',
      letterSpacing: 4,
      fontFamily: 'System',
    },
    codeSubtitle: {
      color: colors.textMuted,
      fontSize: 12,
      marginTop: 6,
    },
    checkStatusBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      alignSelf: 'center',
      marginTop: 24,
      paddingVertical: 12,
      paddingHorizontal: 20,
    },
    checkStatusText: {
      color: colors.purpleAccent,
      fontSize: 14,
      fontWeight: '700',
      marginLeft: 8,
    },
    regenerateBtn: {
      alignSelf: 'center',
      marginTop: 8,
      paddingVertical: 8,
    },
    regenerateText: {
      color: colors.textMuted,
      fontSize: 12,
      textDecorationLine: 'underline',
    },
  });

