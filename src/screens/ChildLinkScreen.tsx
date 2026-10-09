import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Keyboard,
  StatusBar,
  Platform,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { useAppTheme } from '../contexts/ThemeContext';
import { Icon } from '../components/Icon';
import { ParentalRepository } from '../data/parentalRepository';
import { Storage } from '../utils/storage';
import { telemetryWorker } from '../services/TelemetryService';

interface ChildLinkScreenProps {
  onBack: () => void;
  onLinkSuccess: () => void;
}

export const ChildLinkScreen: React.FC<ChildLinkScreenProps> = ({
  onBack,
  onLinkSuccess,
}) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [childName, setChildName] = useState('');
  const [childAge, setChildAge] = useState('');
  const [parentEmail, setParentEmail] = useState('');
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  const [activeIndex, setActiveIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const inputRefs = useRef<Array<TextInput | null>>([]);

  const handleDigitChange = (text: string, index: number) => {
    // Only accept numeric characters
    const cleanDigit = text.replace(/\D/g, '').slice(-1);
    const newDigits = [...otpDigits];
    newDigits[index] = cleanDigit;
    setOtpDigits(newDigits);

    if (cleanDigit && index < 5) {
      setActiveIndex(index + 1);
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (e: any, index: number) => {
    if (e.nativeEvent.key === 'Backspace' && !otpDigits[index] && index > 0) {
      setActiveIndex(index - 1);
      inputRefs.current[index - 1]?.focus();
    }
  };

  const pairingCode = otpDigits.join('');
  const isComplete = pairingCode.length === 6;
  const isFormValid = isComplete && childName.trim() && childAge.trim() && parentEmail.trim();

  const handleLinkDevice = async () => {
    Keyboard.dismiss();

    if (!childName.trim()) {
      setErrorMessage("Please enter the child's name");
      return;
    }
    const ageNum = parseInt(childAge.trim(), 10);
    if (!childAge.trim() || isNaN(ageNum) || ageNum <= 0 || ageNum > 18) {
      setErrorMessage("Please enter a valid age (1-18)");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!parentEmail.trim() || !emailRegex.test(parentEmail.trim())) {
      setErrorMessage("Please enter a valid parent email address");
      return;
    }
    if (pairingCode.length !== 6) {
      setErrorMessage('Please enter all 6 digits of the linking code');
      return;
    }

    const formattedCode = `${pairingCode.substring(0, 3)}-${pairingCode.substring(3)}`;

    try {
      setIsLoading(true);
      setErrorMessage('');

      // Gather real device mobile hardware & platform information
      const brand = (Platform.constants as any)?.Brand || '';
      const model = (Platform.constants as any)?.Model || '';
      const realDeviceName = (brand && model)
        ? `${brand} ${model}`
        : (model || (Platform.OS === 'android' ? 'Android Phone' : 'Apple Device'));
      const osInfo = Platform.OS === 'android' ? `Android ${Platform.Version || '14'}` : 'iOS';
      const initialBatteryLevel = 92;

      const response = await ParentalRepository.linkChildDevice(
        formattedCode,
        childName.trim(),
        realDeviceName,
        osInfo,
        parentEmail.trim(),
        ageNum,
        initialBatteryLevel
      );

      const childId = String(response?.child_id || `child_${Date.now()}`);

      const newChildProfile = {
        id: childId,
        child_id: childId,
        name: childName.trim(),
        child_name: childName.trim(),
        age: ageNum,
        parentEmail: parentEmail.trim(),
        avatarColor: '#8b5cf6',
        battery: `${initialBatteryLevel}%`,
        batteryLevel: initialBatteryLevel,
        device: realDeviceName,
        deviceName: realDeviceName,
        os_type: osInfo,
        osType: osInfo,
        lastActive: 'Active Now',
        is_active_online: true,
        permissions_granted: true,
        status: 'LINKED',
        currentUsageMinutes: 0,
        totalLimitMinutes: 120,
        notificationsToday: 0,
        appUsage: [],
      };

      if (response?.pairing_id) {
        await Storage.setPairingId(response.pairing_id);
      }
      await Storage.setChildId(childId);
      await Storage.setLinkedChild(newChildProfile);
      await Storage.setAssignedRole('CHILD');
      await Storage.setIsExistingUser(true);

      // Immediately start background location telemetry and app usage sync
      try {
        await telemetryWorker.start();
      } catch (workerErr) {
        console.warn('Telemetry worker start warning:', workerErr);
      }

      onLinkSuccess();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Invalid Linking Code. Please check the code and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBack}>
          <Icon name="arrow-back" color={colors.text} size={20} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Link Child Device</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        {/* Info Card */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>Enter Parent's Linking Code</Text>
          <Text style={styles.infoSub}>
            Please enter your details and the 6-digit linking code generated on your parent's Parental Control screen to link this device.
          </Text>
        </View>

        {/* Identity Inputs */}
        <View style={styles.form}>
          {/* Child's Name */}
          <View style={styles.inputWrapper}>
            <Icon name="person" color={colors.textMuted} size={20} />
            <TextInput
              style={styles.input}
              placeholder="Child's Name (e.g. Rohan)"
              placeholderTextColor={colors.textMuted}
              value={childName}
              onChangeText={setChildName}
              returnKeyType="next"
            />
          </View>

          {/* Child's Age */}
          <View style={[styles.inputWrapper, { marginTop: 12 }]}>
            <Icon name="event" color={colors.textMuted} size={20} />
            <TextInput
              style={styles.input}
              placeholder="Child's Age (e.g. 10)"
              placeholderTextColor={colors.textMuted}
              value={childAge}
              onChangeText={setChildAge}
              keyboardType="number-pad"
              maxLength={2}
              returnKeyType="next"
            />
          </View>

          {/* Parent's Email for Verification */}
          <View style={[styles.inputWrapper, { marginTop: 12 }]}>
            <Icon name="email" color={colors.textMuted} size={20} />
            <TextInput
              style={styles.input}
              placeholder="Parent's Email for Verification (e.g. parent@example.com)"
              placeholderTextColor={colors.textMuted}
              value={parentEmail}
              onChangeText={setParentEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              returnKeyType="done"
            />
          </View>
        </View>

        {/* 6-Digit OTP Box Grid (Screen 3A Specification) */}
        <View style={styles.otpSection}>
          <Text style={styles.otpLabel}>ENTER 6-DIGIT LINKING CODE</Text>
          <View style={styles.otpGrid}>
            {otpDigits.map((digit, idx) => {
              const isActive = idx === activeIndex;
              return (
                <View
                  key={idx}
                  style={[
                    styles.otpBox,
                    isActive && styles.otpBoxActive,
                    digit !== '' && styles.otpBoxFilled,
                  ]}
                >
                  <TextInput
                    ref={(el) => {
                      inputRefs.current[idx] = el;
                    }}
                    style={styles.otpInput}
                    keyboardType="number-pad"
                    maxLength={1}
                    value={digit}
                    onChangeText={(text) => handleDigitChange(text, idx)}
                    onKeyPress={(e) => handleKeyPress(e, idx)}
                    onFocus={() => setActiveIndex(idx)}
                    selectTextOnFocus
                  />
                </View>
              );
            })}
          </View>
        </View>

        {/* Error Message */}
        {!!errorMessage && <Text style={styles.errorText}>{errorMessage}</Text>}

        {/* Link Button */}
        <TouchableOpacity
          style={[styles.linkBtn, (!isFormValid || isLoading) && styles.linkBtnDisabled]}
          onPress={handleLinkDevice}
          disabled={!isFormValid || isLoading}
        >
          <LinearGradient
            colors={isFormValid ? ['#E50914', '#b30710'] : ['#2A2A38', '#1c1c28']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.gradient}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.btnText}>LINK MY DEVICE</Text>
            )}
          </LinearGradient>
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
      alignItems: 'center',
      paddingHorizontal: 24,
      paddingTop: 16,
      marginBottom: 16,
      maxWidth: 600,
      width: '100%',
      alignSelf: 'center',
    },
    backButton: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 16,
    },
    headerTitle: {
      color: colors.text,
      fontSize: 18,
      fontWeight: 'bold',
    },
    scrollContent: {
      paddingHorizontal: 24,
      paddingBottom: 40,
      maxWidth: 600,
      width: '100%',
      alignSelf: 'center',
    },
    infoCard: {
      width: '100%',
      borderRadius: 16,
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      padding: 16,
      marginBottom: 24,
    },
    infoTitle: {
      color: colors.text,
      fontSize: 15,
      fontWeight: 'bold',
    },
    infoSub: {
      color: colors.textMuted,
      fontSize: 12,
      marginTop: 6,
      lineHeight: 16,
    },
    form: {
      width: '100%',
      marginBottom: 24,
    },
    inputWrapper: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 12,
      paddingHorizontal: 16,
      height: 56,
    },
    input: {
      flex: 1,
      color: colors.text,
      fontSize: 14,
      paddingLeft: 12,
    },
    otpSection: {
      width: '100%',
      marginBottom: 24,
    },
    otpLabel: {
      color: colors.textMuted,
      fontSize: 11,
      fontWeight: '800',
      letterSpacing: 1,
      marginBottom: 12,
      textAlign: 'center',
    },
    otpGrid: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      width: '100%',
    },
    otpBox: {
      width: 44,
      height: 54,
      borderRadius: 12,
      backgroundColor: colors.cardBackground,
      borderWidth: 1.5,
      borderColor: colors.border,
      justifyContent: 'center',
      alignItems: 'center',
    },
    otpBoxActive: {
      borderColor: '#E50914',
      shadowColor: '#E50914',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.8,
      shadowRadius: 6,
    },
    otpBoxFilled: {
      backgroundColor: '#1E141A',
      borderColor: '#E50914',
    },
    otpInput: {
      color: colors.text,
      fontSize: 22,
      fontWeight: '900',
      textAlign: 'center',
      width: '100%',
      height: '100%',
    },
    errorText: {
      color: colors.redDanger || '#ef4444',
      fontSize: 12,
      fontWeight: 'bold',
      marginBottom: 16,
      textAlign: 'center',
    },
    linkBtn: {
      width: '100%',
      height: 56,
      borderRadius: 12,
      overflow: 'hidden',
      marginTop: 8,
    },
    linkBtnDisabled: {
      opacity: 0.6,
    },
    gradient: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    btnText: {
      color: '#fff',
      fontSize: 15,
      fontWeight: '900',
      letterSpacing: 1.5,
    },
  });
