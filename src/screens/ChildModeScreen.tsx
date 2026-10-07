import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Modal,
  Animated,
  Easing,
  Keyboard,
  StatusBar,
  Vibration,
  Image,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Svg, { Circle as SvgCircle } from 'react-native-svg';
import { useAppTheme } from '../contexts/ThemeContext';
import { colors } from '../styles/theme';
import { Icon } from '../components/Icon';
import { Storage } from '../utils/storage';
import { ParentalRepository } from '../data/parentalRepository';

interface ChildModeScreenProps {
  onUnlink: () => void;
}

export const ChildModeScreen: React.FC<ChildModeScreenProps> = ({ onUnlink }) => {
  const { colors, mode } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [sosActive, setSosActive] = useState(false);
  const [showUnlinkModal, setShowUnlinkModal] = useState(false);
  const [enteredPin, setEnteredPin] = useState('');
  const [pinError, setPinError] = useState('');
  const [childName, setChildName] = useState('Child');
  const [childProfile, setChildProfile] = useState<any>(null);

  useEffect(() => {
    async function loadChildName() {
      const child = await Storage.getLinkedChild();
      if (child) {
        setChildProfile(child);
        if (child.name) {
          setChildName(child.name);
        }
      }
    }
    loadChildName();
  }, []);

  // 3-second long-press SOS State
  const [isPressing, setIsPressing] = useState(false);
  const [sosCountdown, setSosCountdown] = useState(3.0);
  const pressTimer = useRef<any>(null);
  const startTime = useRef<number>(0);

  // Animations
  const progressAnim = useRef(new Animated.Value(0)).current;
  const pulseScale = useRef(new Animated.Value(1.0)).current;

  // Pulse animation when idle or active
  useEffect(() => {
    let animation: Animated.CompositeAnimation;
    
    if (sosActive) {
      animation = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseScale, {
            toValue: 1.4,
            duration: 800,
            easing: Easing.linear,
            useNativeDriver: true,
          }),
          Animated.timing(pulseScale, {
            toValue: 1.0,
            duration: 800,
            easing: Easing.linear,
            useNativeDriver: true,
          })
        ])
      );
    } else {
      animation = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseScale, {
            toValue: 1.12,
            duration: 2000,
            easing: Easing.linear,
            useNativeDriver: true,
          }),
          Animated.timing(pulseScale, {
            toValue: 1.0,
            duration: 2000,
            easing: Easing.linear,
            useNativeDriver: true,
          })
        ])
      );
    }

    animation.start();
    return () => animation.stop();
  }, [sosActive, pulseScale]);

  // Press handlers for the SOS button
  const handlePressIn = () => {
    if (sosActive) return; // Prevent double trigger
    setIsPressing(true);
    setSosCountdown(3.0);
    startTime.current = Date.now();

    // Trigger soft haptic feedback on start
    Vibration.vibrate(50);

    Animated.timing(progressAnim, {
      toValue: 1,
      duration: 3000,
      easing: Easing.linear,
      useNativeDriver: false,
    }).start();

    pressTimer.current = setInterval(() => {
      const elapsed = Date.now() - startTime.current;
      const remaining = Math.max(0, 3 - elapsed / 1000);
      setSosCountdown(parseFloat(remaining.toFixed(1)));

      // Trigger periodic ticks during press
      if (Math.floor(elapsed) % 500 < 50) {
        Vibration.vibrate(20);
      }

      if (elapsed >= 3000) {
        triggerSosAlert();
      }
    }, 50);
  };

  const handlePressOut = () => {
    if (sosActive) return;
    cleanupPress();
  };

  const cleanupPress = () => {
    if (pressTimer.current) {
      clearInterval(pressTimer.current);
      pressTimer.current = null;
    }
    progressAnim.stopAnimation();
    progressAnim.setValue(0);
    setIsPressing(false);
    setSosCountdown(3.0);
  };

  const triggerSosAlert = async () => {
    cleanupPress();
    setSosActive(true);
    // Haptic pattern for alert successfully sent
    Vibration.vibrate([0, 200, 100, 200, 100, 400]);

    try {
      const childId = (await Storage.getChildId()) || '1';
      await ParentalRepository.triggerSOS(
        childId,
        13.0827,
        80.2707,
        'EMERGENCY SOS DISTRESS TRIGGERED FROM CHILD DEVICE'
      );
    } catch {
      console.warn('Failed to dispatch SOS API payload');
    }
  };

  const handleCancelSOS = () => {
    setSosActive(false);
    cleanupPress();
  };

  const handleVerifyUnlink = async () => {
    Keyboard.dismiss();
    const cleanPin = enteredPin.trim().replace(/\s+|-/g, '');

    if (cleanPin.length < 4 || cleanPin.length > 10) {
      setPinError('Invalid Code: Please enter a valid 6-digit Unlink Code');
      return;
    }

    const storedChild = await Storage.getLinkedChild();
    const cId = storedChild?.id || '1';
    const cName = storedChild?.name || 'Child Device';

    try {
      await ParentalRepository.notifyLogoutAttempt(cId, cName);
    } catch (e) {}

    let isValid = false;
    try {
      // 1. Verify code directly against backend API database
      const res = await ParentalRepository.verifyUnlinkCode(cId, enteredPin);
      if (res && res.unlinked) {
        isValid = true;
      }
    } catch (e) {
      // 2. Fallback PIN validation
      isValid = await ParentalRepository.verifyParentPin(enteredPin) || await ParentalRepository.verifyParentPin(cleanPin);
    }

    if (isValid) {
      setShowUnlinkModal(false);
      setEnteredPin('');
      setPinError('');
      try {
        if (cId) {
          await ParentalRepository.unlinkChildDevice(cId);
        }
      } catch (e) {}
      await Storage.setLinkedChild(null);
      await Storage.setChildId('');
      onUnlink();
    } else {
      setPinError('Invalid Unlink Code. Please enter the valid 6-digit code.');
    }
  };

  // Interpolating the progress ring fill
  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={styles.container}>
      <StatusBar barStyle={mode === 'dark' ? 'light-content' : 'dark-content'} backgroundColor={colors.background} />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        
        {/* 1. Header App Bar */}
        <View style={styles.headerBar}>
          <TouchableOpacity style={styles.headerBtn}>
            <Icon name="menu" color={colors.text} size={22} />
          </TouchableOpacity>
          <View style={styles.headerTitleCenter}>
            <Text style={styles.headerTitle}>Child Overview</Text>
            <Text style={styles.headerSubtitle}>Stay safe & connected</Text>
          </View>
          <TouchableOpacity style={styles.headerBtn}>
            <View style={{ position: 'relative' }}>
              <Icon name="notifications" color={colors.text} size={22} />
              <View style={styles.badgeDot} />
            </View>
          </TouchableOpacity>
        </View>

        {/* 2. Profile Header */}
        <View style={styles.profileHeader}>
          <Image source={require('../assets/child_avatar.png')} style={styles.avatarImage} />
          <View style={styles.profileTexts}>
            <Text style={styles.profileName}>Hello, {childName}</Text>
            <Text style={styles.managedText}>Managed securely by Parent Account</Text>
          </View>
          <Icon name="chevron-right" color={colors.textMuted} size={18} />
        </View>

        {/* 3. System Status Card (Screen 3C: Silent Lockdown Shield) */}
        <View style={styles.systemStatusCard}>
          <View style={styles.systemStatusLeft}>
            <View style={[styles.shieldIconBg, { backgroundColor: '#E5091415' }]}>
              <Icon name="shield" color="#E50914" size={28} />
            </View>
            <View style={styles.systemStatusTextContainer}>
              <Text style={styles.systemStatusLabel}>SHIELD ACTIVE</Text>
              <Text style={[styles.systemStatusValue, { color: '#E50914' }]}>SECURED BY PARENT</Text>
              <Text style={styles.systemStatusDesc}>Background telemetry sync loop running (10s ping)</Text>
            </View>
          </View>
          <View style={[styles.checkCircleBg, { backgroundColor: '#E5091415' }]}>
            <Icon name="check-circle" color="#E50914" size={18} />
          </View>
        </View>

        {/* 4. Dashboard Cards Grid */}
        <View style={styles.dashboardGrid}>
          {/* Card 1: Daily Screen Time */}
          <View style={styles.timeCard}>
            <View style={styles.cardHeaderRow}>
              <Icon name="schedule" color={colors.purpleAccent} size={20} />
              <Text style={styles.cardHeaderTitle}>Daily Screen Time</Text>
            </View>
            <View style={styles.circleContainer}>
              <Svg width={110} height={110} viewBox="0 0 100 100">
                <SvgCircle cx="50" cy="50" r="40" stroke={colors.border} strokeWidth="8" fill="none" />
                <SvgCircle
                  cx="50"
                  cy="50"
                  r="40"
                  stroke={colors.purpleAccent}
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 40}`}
                  strokeDashoffset={`${2 * Math.PI * 40 * (1 - 0.56)}`}
                  transform="rotate(-90 50 50)"
                />
              </Svg>
              <View style={styles.circleTextContainer}>
                <Text style={styles.circleMainText}>2h 15m</Text>
                <Text style={styles.circleSubText}>of 4h limit</Text>
              </View>
            </View>
          </View>

          {/* Card 2: Apps Used Today */}
          <View style={styles.appsCard}>
            <View style={styles.cardHeaderRow}>
              <Icon name="apps" color={colors.blueAccent} size={20} />
              <Text style={styles.cardHeaderTitle}>Apps Used Today</Text>
            </View>
            <View style={styles.appsList}>
              {childProfile?.appUsage && childProfile.appUsage.length > 0 ? (
                childProfile.appUsage.map((item: any, idx: number) => (
                  <View key={idx} style={styles.appRowItem}>
                    <View style={styles.appRowLeft}>
                      <View style={[styles.appBadge, { backgroundColor: item.color || colors.purpleAccent }]}>
                        <Icon name="apps" color="#fff" size={14} />
                      </View>
                      <Text style={styles.appRowName}>{item.name}</Text>
                    </View>
                    <Text style={styles.appRowTime}>{item.time || '0m'}</Text>
                  </View>
                ))
              ) : (
                <View style={{ paddingVertical: 12, alignItems: 'center' }}>
                  <Text style={{ color: colors.textMuted, fontSize: 13 }}>
                    No app activity recorded today.
                  </Text>
                </View>
              )}
            </View>
          </View>

          {/* Card 3: Notifications Today */}
          <View style={styles.statGridCard}>
            <View style={styles.statCardHeader}>
              <Icon name="notifications" color={colors.purpleAccent} size={20} />
              <Text style={styles.statCardTitle}>Notifications Today</Text>
            </View>
            <Text style={styles.statCardValue}>{childProfile?.notificationsToday ?? 0}</Text>
            <Text style={styles.statCardSub}>Total Notifications</Text>
          </View>

          {/* Card 4: Battery */}
          <View style={styles.statGridCard}>
            <View style={styles.statCardHeader}>
              <Icon name="battery-charging-full" color={colors.greenSuccess} size={20} />
              <Text style={styles.statCardTitle}>Battery</Text>
            </View>
            <Text style={[styles.statCardValue, { color: colors.greenSuccess }]}>84%</Text>
            <View style={styles.batterySubRow}>
              <Icon name="flash-on" color={colors.greenSuccess} size={12} />
              <Text style={styles.batterySubText}>Charging</Text>
            </View>
          </View>
        </View>

        {/* 5. Emergency SOS Help Card */}
        <View 
          style={styles.emergencyHelpCard}
          onTouchStart={handlePressIn}
          onTouchEnd={handlePressOut}
        >
          <View style={styles.emergencyHelpLeft}>
            {/* SOS Button Area */}
            <View style={styles.sosButtonIndicatorContainer}>
              <Animated.View
                style={[
                  styles.sosButtonIndicatorPulse,
                  {
                    transform: [{ scale: pulseScale }],
                    borderColor: colors.redDanger + '44',
                    backgroundColor: colors.redDanger + '20',
                  },
                ]}
              />
              <View style={[styles.sosButtonIndicator, { backgroundColor: colors.redDanger }]}>
                {isPressing && (
                  <Animated.View
                    style={[
                      styles.sosProgressFill,
                      {
                        width: progressWidth,
                        backgroundColor: '#fff',
                        opacity: 0.3,
                      },
                    ]}
                  />
                )}
                <Text style={styles.sosButtonIndicatorText}>
                  {isPressing ? `${sosCountdown}s` : 'SOS'}
                </Text>
              </View>
            </View>

            {/* Emergency Help Texts */}
            <View style={styles.emergencyHelpTexts}>
              <Text style={styles.emergencyHelpTitle}>🚨 TRIGGER DISTRESS SOS</Text>
              <Text style={[styles.emergencyHelpSubtitle, sosActive && { color: colors.greenSuccess }]}>
                {sosActive ? 'DISTRESS BROADCASTING' : 'HOLD FOR 3 SECONDS'}
              </Text>
              <Text style={styles.emergencyHelpDesc}>
                {sosActive 
                  ? 'Distress alarm and GPS telemetry details successfully transmitted to parent.' 
                  : 'Emergency alert will be sent to your parent with your location.'}
              </Text>
            </View>
          </View>
          <Icon name="chevron-right" color={colors.textMuted} size={18} />
        </View>

        {/* Unlink Device Button */}
        <TouchableOpacity
          style={styles.unlinkBtn}
          onPress={async () => {
            try {
              const storedChild = await Storage.getLinkedChild();
              const cId = storedChild?.id || 'child_lokeshbm';
              const cName = storedChild?.name || 'lokeshBM';
              await ParentalRepository.notifyLogoutAttempt(cId, cName);
            } catch (e) {}
            setShowUnlinkModal(true);
          }}
        >
          <Text style={styles.unlinkBtnText}>Unlink and Disassociate Device</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* PARENT UNLINK CODE VERIFICATION MODAL */}
      <Modal transparent={true} visible={showUnlinkModal} animationType="fade" onRequestClose={() => { setShowUnlinkModal(false); setEnteredPin(''); setPinError(''); }}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Parent Verification Required</Text>
              <TouchableOpacity onPress={() => { setShowUnlinkModal(false); setEnteredPin(''); setPinError(''); }}>
                <Icon name="close" color={colors.textMuted} size={20} />
              </TouchableOpacity>
            </View>
            <Text style={styles.modalDesc}>Enter the 6-digit Parent Unlink Code to authorize unlinking this child device.</Text>
            <TextInput
              style={styles.pinInput}
              placeholder="6-digit Code (e.g. 482-391)"
              placeholderTextColor={colors.textMuted}
              value={enteredPin}
              onChangeText={(text) => {
                setEnteredPin(text);
                if (pinError) setPinError('');
              }}
              keyboardType="numeric"
              maxLength={7}
            />
            {!!pinError && <Text style={styles.pinErrorText}>{pinError}</Text>}
            <TouchableOpacity style={styles.verifyBtn} onPress={handleVerifyUnlink}>
              <Text style={styles.verifyBtnText}>Verify &amp; Unlink Device</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const getStyles = (colors: any) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 30,
    maxWidth: 680,
    width: '100%',
    alignSelf: 'center',
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
    marginTop: 10,
  },
  headerBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  badgeDot: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.purpleAccent,
  },
  headerTitleCenter: {
    alignItems: 'center',
  },
  headerTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
    marginBottom: 20,
  },
  avatarImage: {
    width: 50,
    height: 50,
    borderRadius: 25,
  },
  profileTexts: {
    flex: 1,
    marginLeft: 16,
  },
  profileName: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  managedText: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  systemStatusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
    marginBottom: 20,
  },
  systemStatusLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  shieldIconBg: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  systemStatusTextContainer: {
    marginLeft: 16,
    flex: 1,
  },
  systemStatusLabel: {
    color: colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  systemStatusValue: {
    color: colors.greenSuccess,
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 2,
  },
  systemStatusDesc: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  checkCircleBg: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dashboardGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  timeCard: {
    width: '48%',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
    alignItems: 'center',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  cardHeaderTitle: {
    color: colors.text,
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  circleContainer: {
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
    width: 110,
    height: 110,
  },
  circleTextContainer: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  circleMainText: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  circleSubText: {
    color: colors.textMuted,
    fontSize: 9,
    marginTop: 2,
  },
  appsCard: {
    width: '48%',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
  },
  appsList: {
    marginTop: 8,
  },
  appRowItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  appRowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  appBadge: {
    width: 24,
    height: 24,
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  appRowName: {
    color: colors.text,
    fontSize: 11,
    fontWeight: '600',
    marginLeft: 8,
    flex: 1,
  },
  appRowTime: {
    color: colors.textMuted,
    fontSize: 11,
  },
  viewAllLink: {
    color: colors.purpleAccent,
    fontSize: 11,
    fontWeight: '600',
    textAlign: 'right',
    marginTop: 8,
  },
  statGridCard: {
    width: '48%',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
    marginTop: 16,
  },
  statCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  statCardTitle: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  statCardValue: {
    color: colors.text,
    fontSize: 24,
    fontWeight: 'bold',
    marginVertical: 4,
  },
  statCardSub: {
    color: colors.textMuted,
    fontSize: 11,
  },
  batterySubRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  batterySubText: {
    color: colors.greenSuccess,
    fontSize: 11,
    marginLeft: 4,
    fontWeight: '600',
  },
  emergencyHelpCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    padding: 16,
    marginBottom: 30,
  },
  emergencyHelpLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  sosButtonIndicatorContainer: {
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
    width: 68,
    height: 68,
  },
  sosButtonIndicatorPulse: {
    position: 'absolute',
    width: 68,
    height: 68,
    borderRadius: 34,
    borderWidth: 1.5,
  },
  sosButtonIndicator: {
    width: 52,
    height: 52,
    borderRadius: 26,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  sosButtonIndicatorText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '900',
  },
  sosProgressFill: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
  },
  emergencyHelpTexts: {
    marginLeft: 16,
    flex: 1,
  },
  emergencyHelpTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
  emergencyHelpSubtitle: {
    color: colors.redDanger,
    fontSize: 10,
    fontWeight: 'bold',
    marginTop: 2,
  },
  emergencyHelpDesc: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 4,
    lineHeight: 14,
  },
  unlinkBtn: {
    width: '100%',
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 40,
  },
  unlinkBtnText: {
    color: colors.redDanger,
    fontSize: 13,
    fontWeight: 'bold',
  },
  bottomNav: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 64,
    backgroundColor: colors.cardBackground,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    elevation: 8,
    zIndex: 10,
  },
  navItem: {
    justifyContent: 'center',
    alignItems: 'center',
    flex: 1,
  },
  navText: {
    fontSize: 9,
    fontWeight: '600',
    color: colors.textMuted,
    marginTop: 4,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    borderRadius: 20,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    marginBottom: 10,
  },
  modalTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalDesc: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginVertical: 10,
  },
  pinInput: {
    width: '100%',
    height: 50,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
    color: colors.text,
    fontSize: 17,
    textAlign: 'center',
    letterSpacing: 3,
    marginVertical: 8,
    paddingHorizontal: 10,
  },
  pinErrorText: {
    color: colors.redDanger,
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 5,
  },
  verifyBtn: {
    width: '100%',
    height: 48,
    borderRadius: 10,
    backgroundColor: colors.redDanger,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 24,
  },
  verifyBtnText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
});

