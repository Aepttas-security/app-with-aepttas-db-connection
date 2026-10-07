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
  Image,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Svg, {
  Path,
  Defs,
  LinearGradient as SvgLinearGradient,
  Stop,
} from 'react-native-svg';
import { useAppTheme } from '../contexts/ThemeContext';
import { colors } from '../styles/theme';
import { Icon } from '../components/Icon';
import { registerUser, AuthError } from '../data/authRepository';
import { Storage } from '../utils/storage';

interface SignUpScreenProps {
  onSignUpSuccess: () => void; // go back to Login after registration
  onGoToLogin: () => void;     // already have an account → Login
}

export const SignUpScreen: React.FC<SignUpScreenProps> = ({
  onSignUpSuccess,
  onGoToLogin,
}) => {
  const { colors, mode, toggleTheme } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPasswordVisible, setConfirmPasswordVisible] = useState(false);
  const [linkingCode, setLinkingCode] = useState('');
  const [accountType, setAccountType] = useState<'parent' | 'child'>('parent');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  
  // Validation checks for child form
  const isChildUsernameValid = name.trim().length >= 2 && /^[a-zA-Z0-9\s\-]+$/.test(name);
  const isChildEmailValid = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(email);
  const isChildPasswordValid = password.length >= 8;
  const isChildConfirmPasswordValid = password === confirmPassword && confirmPassword.length > 0;
  const isChildLinkingCodeValid = linkingCode.trim().length >= 4;
  const isChildFormValid = isChildUsernameValid && isChildEmailValid && isChildPasswordValid && isChildConfirmPasswordValid && isChildLinkingCodeValid;

  const validateAndRegister = async () => {
    setErrorMessage('');
    setSuccessMessage('');

    if (!name.trim()) {
      setErrorMessage('Please enter your full name.');
      return;
    }
    if (!email.trim()) {
      setErrorMessage('Please enter your email address.');
      return;
    }
    if (!email.toLowerCase().endsWith('@gmail.com')) {
      setErrorMessage('Email must end with @gmail.com');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter a password.');
      return;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters.');
      return;
    }
    if (!/[a-z]/.test(password)) {
      setErrorMessage('Password must contain at least one lowercase letter.');
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setErrorMessage('Password must contain at least one uppercase letter.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await registerUser({ name: name.trim(), email, password });
      const createdId = res.user_id || Math.floor(Math.random() * 8999) + 1000;
      await Storage.saveRegisteredAccount({
        name: name.trim(),
        email: email.trim(),
        user_id: createdId,
      });
      await Storage.setUserProfile({
        name: name.trim(),
        email: email.trim(),
        user_id: createdId,
      });
      await Storage.setAssignedRole('PARENT');
      await Storage.setIsExistingUser(true);
      await Storage.setAuthToken(`auth_sess_${createdId}_${Date.now()}`);
      setSuccessMessage('Account created! Redirecting to Sign In...');
      setTimeout(() => {
        onSignUpSuccess();
      }, 1500);
    } catch (err) {
      const authErr = err as AuthError;
      setErrorMessage(authErr.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* Background glow */}
      <View style={styles.glowContainer}>
        <View style={styles.cyanGlow} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Logo */}
        <View style={styles.logoContainer}>
          <Image
            source={require('../assets/app_logo.png')}
            style={styles.logoImage}
            resizeMode="contain"
          />
        </View>

        {/* Header */}
        <Text style={styles.titleText}>Aepttas Shield</Text>
        <Text style={styles.subtitleText}>AI-Powered Mobile Security Suite</Text>

        <View style={styles.welcomeContainer}>
          <Text style={styles.welcomeTitle}>{accountType === 'parent' ? 'Create Account' : 'Child Account Creation Form'}</Text>
          <Text style={styles.welcomeSubtitle}>
            {accountType === 'parent' 
              ? 'Set up your parent account to protect your family' 
              : 'Onboarding Screen — Specification & Design Guide'}
          </Text>
        </View>

        {/* Account Type Toggle */}
        <View style={styles.toggleContainer}>
          <TouchableOpacity
            style={[styles.toggleBtn, accountType === 'parent' && styles.toggleBtnActive]}
            onPress={() => setAccountType('parent')}
          >
            <Text style={[styles.toggleText, accountType === 'parent' && styles.toggleTextActive]}>Parent</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.toggleBtn, accountType === 'child' && styles.toggleBtnActive]}
            onPress={() => setAccountType('child')}
          >
            <Text style={[styles.toggleText, accountType === 'child' && styles.toggleTextActive]}>Child</Text>
          </TouchableOpacity>
        </View>

        {/* Error banner */}
        {!!errorMessage && (
          <View style={styles.errorContainer}>
            <Icon name="error" color={colors.redDanger} size={16} />
            <Text style={styles.errorText}>{errorMessage}</Text>
          </View>
        )}

        {/* Success banner */}
        {!!successMessage && (
          <View style={styles.successContainer}>
            <Icon name="shield" color="#10b981" size={16} />
            <Text style={styles.successText}>{successMessage}</Text>
          </View>
        )}

        {/* Form */}
        <View style={styles.inputContainer}>

          {accountType === 'parent' ? (
            <>
              {/* Full Name */}
              <Text style={styles.fieldLabel}>Full Name</Text>
              <View style={styles.inputWrapper}>
                <Icon name="person" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter your full name"
                  placeholderTextColor={colors.textMuted}
                  value={name}
                  onChangeText={setName}
                  autoCapitalize="words"
                />
              </View>

              {/* Email */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Email Address</Text>
              <View style={styles.inputWrapper}>
                <Icon name="email" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="yourname@gmail.com"
                  placeholderTextColor={colors.textMuted}
                  value={email}
                  onChangeText={setEmail}
                  autoCapitalize="none"
                  keyboardType="email-address"
                />
              </View>

              {/* Password */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Password</Text>
              <View style={styles.inputWrapper}>
                <Icon name="lock" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Min 6 chars, upper & lowercase"
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

              {/* Confirm Password */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Confirm Password</Text>
              <View style={styles.inputWrapper}>
                <Icon name="lock" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Re-enter your password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!confirmPasswordVisible}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity
                  onPress={() => setConfirmPasswordVisible(!confirmPasswordVisible)}
                >
                  <Icon
                    name={confirmPasswordVisible ? 'visibility' : 'visibility-off'}
                    color={colors.textMuted}
                    size={20}
                  />
                </TouchableOpacity>
              </View>

              {/* Password rules hint */}
              <View style={styles.rulesContainer}>
                <RuleHint met={password.length >= 6} text="At least 6 characters" />
                <RuleHint met={/[a-z]/.test(password)} text="One lowercase letter" />
                <RuleHint met={/[A-Z]/.test(password)} text="One uppercase letter" />
                <RuleHint met={password === confirmPassword && password.length > 0} text="Passwords match" />
              </View>
            </>
          ) : (
            <>
              {/* Child Username */}
              <Text style={styles.fieldLabel}>Username</Text>
              <View style={[styles.inputWrapper, focusedField === 'childUsername' && styles.inputFocused]}>
                <Icon name="person" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter child's full name or nickname"
                  placeholderTextColor={colors.textMuted}
                  value={name}
                  onChangeText={setName}
                  autoCapitalize="words"
                  onFocus={() => setFocusedField('childUsername')}
                  onBlur={() => setFocusedField(null)}
                />
              </View>
              <Text style={styles.inlineHintText}>Accepts letters, numbers, spaces, and hyphens. Minimum 2 characters.</Text>

              {/* Child Email */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Email Address</Text>
              <View style={[styles.inputWrapper, focusedField === 'childEmail' && styles.inputFocused]}>
                <Icon name="email" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter child's email address"
                  placeholderTextColor={colors.textMuted}
                  value={email}
                  onChangeText={(text) => setEmail(text.toLowerCase())}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  onFocus={() => setFocusedField('childEmail')}
                  onBlur={() => setFocusedField(null)}
                />
              </View>
              <Text style={styles.inlineHintText}>Must follow valid email format: lowercase, contains @, and ends with a valid TLD (e.g. .com, .org)</Text>

              {/* Child Password */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Password</Text>
              <View style={[styles.inputWrapper, focusedField === 'childPassword' && styles.inputFocused]}>
                <Icon name="lock" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!passwordVisible}
                  value={password}
                  onChangeText={setPassword}
                  autoCapitalize="none"
                  onFocus={() => setFocusedField('childPassword')}
                  onBlur={() => setFocusedField(null)}
                />
                <TouchableOpacity style={styles.showHideToggle} onPress={() => setPasswordVisible(!passwordVisible)}>
                  <Icon name={passwordVisible ? 'visibility' : 'visibility-off'} color={colors.purpleAccent} size={16} />
                  <Text style={styles.showHideText}>{passwordVisible ? 'Hide' : 'Show'}</Text>
                </TouchableOpacity>
              </View>
              <Text style={styles.inlineHintText}>Toggle the eye icon on the right to reveal or conceal your password as you type. Minimum 8 characters recommended.</Text>

              {/* Re-enter Password */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Re-enter Password</Text>
              <View style={[styles.inputWrapper, focusedField === 'childConfirmPassword' && styles.inputFocused, isChildConfirmPasswordValid && { borderColor: colors.greenSuccess }]}>
                <Icon name="lock" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Re-enter your password"
                  placeholderTextColor={colors.textMuted}
                  secureTextEntry={!confirmPasswordVisible}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  autoCapitalize="none"
                  onFocus={() => setFocusedField('childConfirmPassword')}
                  onBlur={() => setFocusedField(null)}
                />
                <TouchableOpacity style={styles.showHideToggle} onPress={() => setConfirmPasswordVisible(!confirmPasswordVisible)}>
                  <Icon name={confirmPasswordVisible ? 'visibility' : 'visibility-off'} color={colors.purpleAccent} size={16} />
                  <Text style={styles.showHideText}>{confirmPasswordVisible ? 'Hide' : 'Show'}</Text>
                </TouchableOpacity>
              </View>
              {confirmPassword.length > 0 && !isChildConfirmPasswordValid && (
                <Text style={[styles.inlineHintText, { color: colors.redDanger }]}>Passwords do not match.</Text>
              )}
              {isChildConfirmPasswordValid && (
                <Text style={[styles.inlineHintText, { color: colors.greenSuccess }]}>✓ Passwords match!</Text>
              )}

              {/* Linking Code */}
              <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Linking Code</Text>
              <View style={[styles.inputWrapper, focusedField === 'childLinkingCode' && styles.inputFocused]}>
                <Icon name="vpn-key" color={colors.textMuted} size={20} />
                <TextInput
                  style={styles.input}
                  placeholder="Enter linking code from parent device"
                  placeholderTextColor={colors.textMuted}
                  value={linkingCode}
                  onChangeText={setLinkingCode}
                  autoCapitalize="characters"
                  onFocus={() => setFocusedField('childLinkingCode')}
                  onBlur={() => setFocusedField(null)}
                />
              </View>
              <Text style={[styles.inlineHintText, { marginBottom: 24 }]}>Enter the pairing code provided by the parent's Aepttas Shield app.</Text>
            </>
          )}

          {/* Create Account Button */}
          {accountType === 'child' ? (
            <TouchableOpacity
              style={[
                styles.signUpBtn,
                !isChildFormValid && styles.signUpBtnDisabled
              ]}
              onPress={validateAndRegister}
              disabled={!isChildFormValid || isLoading}
            >
              {isChildFormValid ? (
                <LinearGradient
                  colors={['#3b82f6', '#2563eb']} // Blue CTA color for child form
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
                        <Text style={styles.btnText}>Register Account & Activate Guard</Text>
                      </>
                    )}
                  </View>
                </LinearGradient>
              ) : (
                <View style={[styles.gradient, styles.btnDisabledBg]}>
                  <View style={styles.btnContent}>
                    <Text style={styles.btnTextDisabled}>Register Account & Activate Guard</Text>
                  </View>
                </View>
              )}
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.signUpBtn, isLoading && { opacity: 0.75 }]}
              onPress={validateAndRegister}
              disabled={isLoading}
            >
              <LinearGradient
                colors={['#06b6d4', '#8b5cf6']}
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
                      <Text style={styles.btnText}>Create Account</Text>
                    </>
                  )}
                </View>
              </LinearGradient>
            </TouchableOpacity>
          )}
        </View>

        {/* Back to Login */}
        <View style={styles.footerRow}>
          <Text style={styles.footerText}>Already have an account? </Text>
          <TouchableOpacity onPress={onGoToLogin}>
            <Text style={styles.linkText}>Sign In</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
};

// Small rule hint component
const RuleHint: React.FC<{ met: boolean; text: string }> = ({ met, text }) => (
  <View style={ruleStyles.row}>
    <View style={[ruleStyles.dot, met ? ruleStyles.dotMet : ruleStyles.dotUnmet]} />
    <Text style={[ruleStyles.text, met ? ruleStyles.textMet : ruleStyles.textUnmet]}>
      {text}
    </Text>
  </View>
);

const ruleStyles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  dot: { width: 6, height: 6, borderRadius: 3, marginRight: 8 },
  dotMet: { backgroundColor: '#10b981' },
  dotUnmet: { backgroundColor: '#6b7280' },
  text: { fontSize: 12 },
  textMet: { color: '#10b981' },
  textUnmet: { color: '#6b7280' },
});

const getStyles = (colors: any) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
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
  cyanGlow: {
    width: 350,
    height: 350,
    borderRadius: 175,
    backgroundColor: '#06b6d4',
    opacity: 0.12,
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
    marginTop: 32,
    height: 90,
    width: 90,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoImage: {
    width: '100%',
    height: '100%',
  },
  titleText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: colors.text,
    letterSpacing: 0.5,
    marginTop: 12,
  },
  subtitleText: {
    fontSize: 13,
    color: '#06b6d4',
    fontWeight: '500',
    letterSpacing: 0.5,
    marginTop: 4,
    marginBottom: 28,
  },
  welcomeContainer: {
    alignSelf: 'flex-start',
    marginBottom: 20,
  },
  welcomeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
  },
  welcomeSubtitle: {
    fontSize: 13,
    color: colors.textMuted,
    marginTop: 4,
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: colors.cardBackground,
    borderRadius: 12,
    padding: 4,
    marginBottom: 20,
    width: '100%',
    borderWidth: 1,
    borderColor: colors.border,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  toggleBtnActive: {
    backgroundColor: colors.purpleAccent + '33', // Slight transparent purple
  },
  toggleText: {
    color: colors.textMuted,
    fontWeight: '600',
    fontSize: 14,
  },
  toggleTextActive: {
    color: colors.purpleAccent,
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
  inputContainer: {
    width: '100%',
  },
  fieldLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginBottom: 6,
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
  inputFocused: {
    borderColor: '#3b82f6', // Blue highlight on focus
    borderWidth: 1.5,
  },
  inlineHintText: {
    fontSize: 11,
    color: colors.textMuted,
    fontStyle: 'italic',
    marginTop: 4,
    marginLeft: 4,
  },
  showHideToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 8,
  },
  showHideText: {
    color: colors.purpleAccent,
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  input: {
    flex: 1,
    color: colors.text,
    fontSize: 15,
    paddingLeft: 12,
  },
  rulesContainer: {
    marginTop: 12,
    marginBottom: 24,
    paddingHorizontal: 4,
  },
  signUpBtn: {
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
  signUpBtnDisabled: {
    opacity: 1, // Let the background handle the disabled look
  },
  btnDisabledBg: {
    backgroundColor: '#374151', // Grayed out background
  },
  btnTextDisabled: {
    color: '#9ca3af', // Gray text
    fontSize: 16,
    fontWeight: 'bold',
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 28,
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
});
