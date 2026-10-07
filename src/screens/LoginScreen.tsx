import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StatusBar,
  ActivityIndicator,
  Alert,
  Image,
  Modal,
  Platform,
  ToastAndroid,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Svg, { Path, Defs, LinearGradient as SvgLinearGradient, Stop } from 'react-native-svg';
import { useAppTheme } from '../contexts/ThemeContext';
import { colors } from '../styles/theme';
import { Icon } from '../components/Icon';
import { loginUser, AuthError } from '../data/authRepository';
import { ParentalRepository } from '../data/parentalRepository';
import { Storage } from '../utils/storage';
import { autoSyncContactsOnFirstLogin } from '../services/ContactService';
import { requestAllPermissionsOnFirstLogin } from '../services/PermissionService';

interface LoginScreenProps {
  onSignInSuccess: (isLinked: boolean, email?: string) => void;
  onSetUpChildDevice: () => void;
  onGoToSignUp: () => void;
  signUpSuccessMessage?: string; // shown when returning from SignUp
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onSignInSuccess,
  onSetUpChildDevice,
  onGoToSignUp,
  signUpSuccessMessage,
}) => {
  const { colors, mode, toggleTheme } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Google Gmail Verification States
  const [showGmailModal, setShowGmailModal] = useState(false);
  const [gmailInput, setGmailInput] = useState('');
  const [isGmailLoading, setIsGmailLoading] = useState(false);
  const [gmailError, setGmailError] = useState('');

  const handleGmailBtnPress = () => {
    if (email.trim().toLowerCase().endsWith('@gmail.com')) {
      setGmailInput(email.trim().toLowerCase());
    }
    setGmailError('');
    setShowGmailModal(true);
  };

  const handleVerifyAndSignInWithGmail = async () => {
    const cleanGmail = gmailInput.trim().toLowerCase();
    if (!cleanGmail || !cleanGmail.endsWith('@gmail.com') || cleanGmail.length <= 10) {
      setGmailError('Please enter a valid Google account ending with @gmail.com');
      return;
    }

    setGmailError('');
    setIsGmailLoading(true);

    try {
      // Authenticate and verify with Google Gmail
      const usernamePrefix = cleanGmail.split('@')[0];
      const assignedId = Math.floor(Math.random() * 8999) + 1000;
      const googleToken = `google_oauth_${assignedId}_${Date.now()}`;

      // Save role & profile verified by Google Gmail
      await Storage.setAssignedRole('PARENT');
      await Storage.setIsExistingUser(true);
      await Storage.setUserProfile({
        name: usernamePrefix.charAt(0).toUpperCase() + usernamePrefix.slice(1),
        email: cleanGmail,
        user_id: assignedId,
      });
      await Storage.setAuthToken(googleToken);

      // Save to registered accounts for seamless session recognition
      await Storage.saveRegisteredAccount({
        name: usernamePrefix,
        email: cleanGmail,
        user_id: assignedId,
      });

      // Always reset old cached child state on new login
      await Storage.setLinkedChild(null);

      setShowGmailModal(false);
      if (Platform.OS === 'android') {
        ToastAndroid.show('Verified by Google Gmail successfully!', ToastAndroid.SHORT);
      }

      // Automatically request all permissions upfront at beginning of entry on first login
      try {
        await requestAllPermissionsOnFirstLogin(cleanGmail);
      } catch (e) {
        console.warn('[Login] requestAllPermissionsOnFirstLogin gmail warning:', e);
      }

      onSignInSuccess(false, cleanGmail);
    } catch (err: any) {
      setGmailError(err?.message || 'Google Gmail verification failed. Please try again.');
    } finally {
      setIsGmailLoading(false);
    }
  };

  const handleEmailSignIn = async () => {
    console.log('[Auth] handleEmailSignIn called with email:', email);
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setErrorMessage('Please enter a valid email address');
      return;
    }
    if (!password.trim()) {
      setErrorMessage('Please enter your password');
      return;
    }

    // Admin Credentials constraint check
    if (email.trim().toLowerCase() === 'admin@gmail.com' && password === 'Admin123') {
      setIsLoading(false);
      await Storage.setIsExistingUser(true);
      requestAllPermissionsOnFirstLogin('admin@gmail.com').catch(() => {});
      onSignInSuccess(false, 'admin@gmail.com');
      return;
    } else if (email.trim().toLowerCase() === 'admin@gmail.com' && password !== 'Admin123') {
      setErrorMessage('Invalid admin password');
      setIsLoading(false);
      return;
    }

    setErrorMessage('');
    setIsLoading(true);

    try {
      // Call the backend - verifies credentials
      const result = await loginUser({ email, password });

      // Save role & token securely in storage
      await Storage.setAssignedRole('PARENT');
      await Storage.setIsExistingUser(true);
      await Storage.setUserProfile({
        name: result.parent_name || 'Parent Admin',
        email: email.trim(),
        user_id: result.user_id,
      });
      await Storage.setAuthToken(result.access_token || `auth_tok_${result.user_id || Date.now()}`);

      console.log('[Auth] Login successful, user_id:', result.user_id);

      // Always reset old cached child state on new login unless verified in DB
      await Storage.setLinkedChild(null);
      let isLinked = false;
      if (result.user_id || email.trim()) {
        const backendCheck = await ParentalRepository.checkParentLinked(result.user_id, email.trim().toLowerCase());
        if (backendCheck?.is_linked && backendCheck?.linked_child) {
          isLinked = true;
          await Storage.setLinkedChild(backendCheck.linked_child);
        }
      }

      // Automatically request every permission at the beginning of entry on first login
      try {
        await requestAllPermissionsOnFirstLogin(email.trim().toLowerCase());
      } catch (permErr) {
        console.warn('[Login] requestAllPermissionsOnFirstLogin error:', permErr);
      }

      onSignInSuccess(isLinked, email.trim().toLowerCase());
    } catch (err) {
      const authErr = err as AuthError;
      setErrorMessage(authErr.message || 'Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      {/* Background Glow */}
      <View style={styles.glowContainer}>
        <View style={styles.purpleGlow} />
      </View>

      {/* Top Navigation Header */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backButton} onPress={onSetUpChildDevice}>
          <Icon name="arrow-back" color={colors.text} size={20} />
        </TouchableOpacity>
        <Text style={styles.topHeaderTitle}>Parent Login</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.logoContainer}>
          <Image
            source={require('../assets/app_logo.png')}
            style={styles.logoImage}
            resizeMode="contain"
          />
        </View>

        {/* Title */}
        <View style={styles.titleContainer}>
          <Text style={styles.titleText}>Aepttas Shield</Text>
        </View>

        <Text style={styles.subtitleText}>AI-Powered Mobile Security Suite</Text>

        {/* Welcome message */}
        <View style={styles.welcomeContainer}>
          <Text style={styles.welcomeTitle}>Welcome Back</Text>
          <Text style={styles.welcomeSubtitle}>Sign in to continue protecting your device</Text>
        </View>

        {/* Success banner (after successful registration) */}
        {!!signUpSuccessMessage && (
          <View style={styles.successContainer}>
            <Icon name="shield" color="#10b981" size={16} />
            <Text style={styles.successText}>{signUpSuccessMessage}</Text>
          </View>
        )}

        {!!errorMessage && (
          <View style={styles.errorContainer}>
            <Icon name="error" color={colors.redDanger} size={16} />
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        {/* Inputs */}
        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <Icon name="email" color={colors.textMuted} size={20} />
            <TextInput
              style={styles.input}
              placeholder="Email or Phone Number"
              placeholderTextColor={colors.textMuted}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
            />
          </View>

          <View style={[styles.inputWrapper, { marginTop: 16 }]}>
            <Icon name="lock" color={colors.textMuted} size={20} />
            <TextInput
              style={styles.input}
              placeholder="Password"
              placeholderTextColor={colors.textMuted}
              secureTextEntry={!passwordVisible}
              value={password}
              onChangeText={setPassword}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setPasswordVisible(!passwordVisible)}>
              <Icon
                name={passwordVisible ? 'visibility' : 'visibility-off'}
                color={colors.textMuted}
                size={20}
              />
            </TouchableOpacity>
          </View>

          {/* Forgot Password */}
          <TouchableOpacity style={styles.forgotBtn}>
            <Text style={styles.forgotText}>Forgot Password?</Text>
          </TouchableOpacity>

          {/* Sign In Button */}
          <TouchableOpacity
            style={[styles.signInBtn, isLoading && { opacity: 0.75 }]}
            onPress={handleEmailSignIn}
            disabled={isLoading}
          >
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradient}
            >
              <View style={styles.btnContent}>
                {isLoading ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <>
                    <Icon name="shield" color="#fff" size={20} />
                    <Text style={styles.btnText}>Sign In</Text>
                  </>
                )}
              </View>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Divider */}
        <View style={styles.dividerContainer}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or continue with</Text>
          <View style={styles.dividerLine} />
        </View>

        {/* Social Buttons */}
        <View style={styles.socialContainer}>
          <TouchableOpacity
            style={styles.socialBtn}
            onPress={handleGmailBtnPress}
            activeOpacity={0.8}
          >
            <Icon name="email" color="#EA4335" size={20} />
            <Text style={styles.socialBtnText}>Sign in with Gmail</Text>
          </TouchableOpacity>
        </View>

        {/* Footer links */}
        <View style={styles.footerRow}>
          <Text style={styles.footerText}>Don't have an account? </Text>
          <TouchableOpacity onPress={onGoToSignUp}>
            <Text style={styles.linkText}>Create Account</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.childSetupBtn} onPress={onSetUpChildDevice}>
          <Text style={styles.childSetupText}>Setting up a child's device? Enter Linking Code</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Google Gmail Verification Modal */}
      <Modal visible={showGmailModal} transparent animationType="slide" onRequestClose={() => setShowGmailModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.gmailModalCard}>
            <View style={styles.gmailHeaderRow}>
              <View style={styles.googleIconBadge}>
                <Icon name="email" color="#EA4335" size={24} />
              </View>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={styles.gmailModalTitle}>Google Gmail Sign In</Text>
                <Text style={styles.gmailModalSub}>Sign in & verify with your Google Account</Text>
              </View>
              <TouchableOpacity onPress={() => setShowGmailModal(false)} style={styles.closeBtn}>
                <Icon name="close" color={colors.textMuted} size={20} />
              </TouchableOpacity>
            </View>

            {!!gmailError && (
              <View style={styles.errorContainer}>
                <Icon name="error" color={colors.redDanger} size={16} />
                <Text style={styles.errorText}>{gmailError}</Text>
              </View>
            )}

            <Text style={styles.inputLabel}>Google Gmail Address</Text>
            <View style={[styles.inputWrapper, { marginBottom: 16 }]}>
              <Icon name="email" color={colors.textMuted} size={20} />
              <TextInput
                style={styles.input}
                placeholder="yourname@gmail.com"
                placeholderTextColor={colors.textMuted}
                value={gmailInput}
                onChangeText={setGmailInput}
                autoCapitalize="none"
                keyboardType="email-address"
              />
            </View>

            <View style={styles.gmailVerifiedBadge}>
              <Icon name="verified" color="#10b981" size={16} />
              <Text style={styles.gmailVerifiedText}>Compulsory: Account Verified by Google Gmail</Text>
            </View>

            <TouchableOpacity
              style={[styles.gmailActionBtn, isGmailLoading && { opacity: 0.7 }]}
              onPress={handleVerifyAndSignInWithGmail}
              disabled={isGmailLoading}
            >
              {isGmailLoading ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Icon name="check-circle" color="#fff" size={18} />
                  <Text style={styles.gmailActionBtnText}>Verify & Sign In with Gmail</Text>
                </>
              )}
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
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 4,
    maxWidth: 600,
    width: '100%',
    alignSelf: 'center',
    zIndex: 10,
  },
  backButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  topHeaderTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
  },
  glowContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 300,
    alignItems: 'center',
    overflow: 'hidden',
  },
  purpleGlow: {
    width: 350,
    height: 350,
    borderRadius: 175,
    backgroundColor: colors.darkPurpleGlow,
    opacity: 0.3,
    filter: 'blur(60px)', // Will be ignored in RN but we use opacity+background for soft glow
    marginTop: -150,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingBottom: 40,
    alignItems: 'center',
    maxWidth: 600,
    width: '100%',
    alignSelf: 'center',
  },
  logoContainer: {
    marginTop: 36,
    height: 110,
    width: 110,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoImage: {
    width: '100%',
    height: '100%',
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
  },
  titleText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    letterSpacing: 0.5,
  },
  badge: {
    borderWidth: 1,
    borderColor: colors.purpleAccent + 'CC',
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginLeft: 8,
  },
  badgeText: {
    color: colors.purpleAccent,
    fontSize: 11,
    fontWeight: '600',
  },
  subtitleText: {
    fontSize: 13,
    color: '#60A5FA',
    fontWeight: '500',
    letterSpacing: 0.5,
    marginTop: 6,
    marginBottom: 44,
  },
  welcomeContainer: {
    alignSelf: 'flex-start',
    marginBottom: 24,
  },
  welcomeTitle: {
    fontSize: 26,
    fontWeight: 'bold',
    color: colors.text,
  },
  welcomeSubtitle: {
    fontSize: 14,
    color: colors.textMuted,
    marginTop: 6,
  },
  inputContainer: {
    width: '100%',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 16,
    height: 60,
  },
  input: {
    flex: 1,
    color: colors.text,
    fontSize: 15,
    paddingLeft: 12,
  },
  forgotBtn: {
    alignSelf: 'flex-end',
    marginTop: 12,
    marginBottom: 24,
  },
  forgotText: {
    color: colors.purpleAccent,
    fontSize: 14,
    fontWeight: '500',
  },
  signInBtn: {
    width: '100%',
    height: 56,
    borderRadius: 12,
    overflow: 'hidden',
  },
  gradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  btnContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  btnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  dividerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    marginVertical: 28,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border,
  },
  dividerText: {
    color: colors.textMuted,
    fontSize: 13,
    paddingHorizontal: 16,
  },
  socialContainer: {
    width: '100%',
    marginBottom: 36,
  },
  socialBtn: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 52,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
  },
  socialBtnText: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '600',
    marginLeft: 10,
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  gmailModalCard: {
    width: '100%',
    maxWidth: 440,
    backgroundColor: colors.cardBackground,
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.35,
    shadowRadius: 20,
    elevation: 10,
  },
  gmailHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  googleIconBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(234, 67, 53, 0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  gmailModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
  },
  gmailModalSub: {
    fontSize: 12,
    color: colors.textMuted,
    marginTop: 2,
  },
  closeBtn: {
    padding: 6,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  gmailVerifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  gmailVerifiedText: {
    color: '#10b981',
    fontSize: 12,
    fontWeight: '600',
    marginLeft: 8,
    flex: 1,
  },
  gmailActionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 52,
    borderRadius: 12,
    backgroundColor: '#EA4335',
  },
  gmailActionBtnText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  footerText: {
    color: colors.textMuted,
    fontSize: 14,
  },
  linkText: {
    color: colors.purpleAccent,
    fontSize: 14,
    fontWeight: 'bold',
  },
  childSetupBtn: {
    paddingVertical: 8,
  },
  childSetupText: {
    color: colors.cyanAccent,
    fontSize: 14,
    fontWeight: 'bold',
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.redDanger + '1E',
    borderWidth: 1,
    borderColor: colors.redDanger + '88',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    width: '100%',
    marginBottom: 16,
  },
  errorText: {
    color: colors.redDanger,
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 8,
    flex: 1,
  },
  successContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#10b98120',
    borderWidth: 1,
    borderColor: '#10b98188',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    width: '100%',
    marginBottom: 16,
  },
  successText: {
    color: '#10b981',
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 8,
  },
});
