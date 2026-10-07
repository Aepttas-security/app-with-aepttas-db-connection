import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Switch,
  StatusBar,
  Modal,
  ActivityIndicator,
  Alert,
  Platform,
  ToastAndroid,
} from 'react-native';
import Svg, { Circle, Rect, G } from 'react-native-svg';

let MapView: any = null;
let Marker: any = null;
let MapCircle: any = null;

if (Platform.OS !== 'web') {
  try {
    const Maps = require('react-native-maps');
    MapView = Maps.default || Maps;
    Marker = Maps.Marker;
    MapCircle = Maps.Circle;
  } catch {}
}
import { useAppTheme } from '../contexts/ThemeContext';
import { colors } from '../styles/theme';
import { Icon } from '../components/Icon';
import { useParentalControl } from '../hooks/useParentalControl';
import { ParentalRepository } from '../data/parentalRepository';
import { Storage } from '../utils/storage';

interface ChildProfile {
  id: string;
  name: string;
  age: number;
  avatarColor: string;
  batteryLevel: number;
  deviceName: string;
  lastActive: string;
  currentUsageMinutes: number;
  totalLimitMinutes: number;
  appUsage: { name: string; time: string; color: string }[];
}

interface ParentalControlScreenProps {
  onBack: () => void;
  onSignOut?: () => void;
}

const categoryOrder = [
  'All Apps and Categories',
  'Action',
  'Business',
  'Communication',
  'Entertainment',
  'Finance',
  'Health & Fitness',
  'Music & Audio',
  'Photography',
  'Productivity',
  'Shopping',
  'Social',
  'Strategy'
];

import { TwoStepBindingScreen } from './TwoStepBindingScreen';

export const ParentalControlScreen: React.FC<ParentalControlScreenProps> = ({ onBack, onSignOut }) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const {
    children,
    selectedProfileId,
    selectProfile,
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
    sosActive,
    triggerSOS,
    updateSosPreferences,
    getSosPreferences,
    generateLinkingCode,
    createChildProfile,
    unlinkChildDevice,
    refreshData,
  } = useParentalControl();

  const [activeTab, setActiveTab] = useState('Overview');
  const [customUrlInput, setCustomUrlInput] = useState('');
  const [categorySearchQuery, setCategorySearchQuery] = useState('');
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  // Auto-poll pairing status every 3 seconds when waiting for child device link
  useEffect(() => {
    if (children.length === 0) {
      const timer = setInterval(() => {
        refreshData();
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [children.length, refreshData]);

  // Unlink temporary code and timer state
  const [unlinkCode, setUnlinkCode] = useState('482-391');
  const [unlinkSeconds, setUnlinkSeconds] = useState(105);
  const [unlinkCopied, setUnlinkCopied] = useState(false);

  const generateUnlinkCode = useCallback(() => {
    const r1 = Math.floor(100 + Math.random() * 900);
    const r2 = Math.floor(100 + Math.random() * 900);
    setUnlinkCode(`${r1}-${r2}`);
    setUnlinkSeconds(300);
    setUnlinkCopied(false);
  }, []);

  useEffect(() => {
    if (activeTab === 'Link' && unlinkSeconds > 0) {
      const timer = setInterval(() => {
        setUnlinkSeconds(prev => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [activeTab, unlinkSeconds]);

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // New menu and child profile modal states
  const [showMenu, setShowMenu] = useState(false);
  const [showAddChildModal, setShowAddChildModal] = useState(false);
  const [newChildName, setNewChildName] = useState('');
  const [newChildAge, setNewChildAge] = useState('');
  const [newChildLinkingCode, setNewChildLinkingCode] = useState('');
  const [isCreatingChild, setIsCreatingChild] = useState(false);

  const generateNewChildCode = useCallback(() => {
    const random6Digits = Math.floor(100000 + Math.random() * 900000).toString();
    const formatted = `${random6Digits.substring(0, 3)}-${random6Digits.substring(3)}`;
    setNewChildLinkingCode(formatted);
  }, []);

  useEffect(() => {
    if (showAddChildModal && !newChildLinkingCode) {
      generateNewChildCode();
    }
  }, [showAddChildModal, newChildLinkingCode, generateNewChildCode]);

  const handleAddChild = async () => {
    if (!newChildName.trim()) {
      Alert.alert('Error', "Please enter child's name");
      return;
    }
    const ageNum = parseInt(newChildAge, 10);
    if (isNaN(ageNum) || ageNum <= 0) {
      Alert.alert('Error', 'Please enter a valid age');
      return;
    }
    let formattedCode = newChildLinkingCode.trim();
    if (!formattedCode) {
      const random6Digits = Math.floor(100000 + Math.random() * 900000).toString();
      formattedCode = `${random6Digits.substring(0, 3)}-${random6Digits.substring(3)}`;
    }

    try {
      setIsCreatingChild(true);
      await createChildProfile(newChildName.trim(), ageNum, formattedCode);
      setShowAddChildModal(false);
      setNewChildName('');
      setNewChildAge('');
      setNewChildLinkingCode('');
      Alert.alert(
        'Profile Created!',
        `Child profile created successfully.\n\nGenerated Linking Code: ${formattedCode}\n\nEnter this code on the child device screen to link.`
      );
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to create child profile');
    } finally {
      setIsCreatingChild(false);
    }
  };
  
  const [categorizedApps, setCategorizedApps] = useState<{ [category: string]: { name: string; isBlocked: boolean; icon: string }[] }>({});
  const [sosBannerVisible, setSosBannerVisible] = useState(true);
  
  // Geofencing state
  const [geofenceRadius, setGeofenceRadius] = useState(120);
  const [locationTrackingEnabled, setLocationTrackingEnabled] = useState(true);
  const [geofenceEnabled, setGeofenceEnabled] = useState(true);

  // Notification State
  const [demoPhone, setDemoPhone] = useState('');
  const [demoEmail, setDemoEmail] = useState('');
  const [emailAlertsEnabled, setEmailAlertsEnabled] = useState(true);
  const [smsAlertsEnabled, setSmsAlertsEnabled] = useState(true);
  
  const [notifyLimitsPhone, setNotifyLimitsPhone] = useState(true);
  const [notifyLimitsEmail, setNotifyLimitsEmail] = useState(true);

  const [notifySosPhone, setNotifySosPhone] = useState(true);
  const [notifySosEmail, setNotifySosEmail] = useState(true);

  // SOS state
  const [sosTriggeredBy, setSosTriggeredBy] = useState('');

  // Pairing Code state
  const [pairingCode, setPairingCode] = useState('819-860');
  const [showLinkingCodeModalOnLogin, setShowLinkingCodeModalOnLogin] = useState(false);

  const refreshPairingCode = useCallback(async () => {
    try {
      const code = await generateLinkingCode();
      if (code) {
        setPairingCode(code);
      } else {
        const randomDigits = Math.floor(100000 + Math.random() * 900000).toString();
        setPairingCode(`${randomDigits.substring(0, 3)}-${randomDigits.substring(3)}`);
      }
    } catch {
      const randomDigits = Math.floor(100000 + Math.random() * 900000).toString();
      setPairingCode(`${randomDigits.substring(0, 3)}-${randomDigits.substring(3)}`);
    }
  }, [generateLinkingCode]);

  // Generate pairing code on load or profile change
  useEffect(() => {
    refreshPairingCode();
  }, [selectedProfileId, refreshPairingCode]);

  // Load preferences when profile changes
  useEffect(() => {
    const prefs = getSosPreferences();
    if (prefs) {
      setEmailAlertsEnabled(prefs.email_enabled);
      setSmsAlertsEnabled(prefs.phone_enabled);
      setDemoEmail(prefs.parent_email || '');
      setDemoPhone(prefs.parent_phone || '');
    }
  }, [selectedProfileId, getSosPreferences]);

  // Save preferences when they change
  useEffect(() => {
    updateSosPreferences(emailAlertsEnabled, demoEmail, smsAlertsEnabled, demoPhone);
  }, [emailAlertsEnabled, demoEmail, smsAlertsEnabled, demoPhone, updateSosPreferences]);

  useEffect(() => {
    if (sosActive) {
      setSosBannerVisible(true);
    }
  }, [sosActive]);

  const renderQRCode = (code: string, size = 180) => {
    const matrixSize = 21; // 21x21 grid for QR Version 1
    const cellSize = size / matrixSize;
    const matrix = Array(matrixSize).fill(null).map(() => Array(matrixSize).fill(false));

    // Draw finder patterns helper
    const drawFinderPattern = (row: number, col: number) => {
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 7; c++) {
          const isBorder = r === 0 || r === 6 || c === 0 || c === 6;
          const isCenter = r >= 2 && r <= 4 && c >= 2 && c <= 4;
          matrix[row + r][col + c] = isBorder || isCenter;
        }
      }
    };

    // Draw the three standard finder patterns
    drawFinderPattern(0, 0); // Top-left
    drawFinderPattern(0, 14); // Top-right
    drawFinderPattern(14, 0); // Bottom-left

    // Seed generation based on pairing code (e.g., "942-817")
    let seed = 0;
    for (let i = 0; i < code.length; i++) {
      seed = (seed * 31 + code.charCodeAt(i)) & 0xffffffff;
    }

    const pseudoRandom = () => {
      seed = (seed * 1664525 + 1013904223) & 0xffffffff;
      return (seed >>> 16) / 65535;
    };

    // Fill the grid based on the deterministic seed
    for (let r = 0; r < matrixSize; r++) {
      for (let c = 0; c < matrixSize; c++) {
        // Skip finder patterns
        const isTopLeft = r < 8 && c < 8;
        const isTopRight = r < 8 && c >= 13;
        const isBottomLeft = r >= 13 && c < 8;

        if (!isTopLeft && !isTopRight && !isBottomLeft) {
          matrix[r][c] = pseudoRandom() > 0.45;
        }
      }
    }

    // Add timing pattern lines (alternating dark/light rows/cols at line index 6)
    for (let i = 8; i < 13; i++) {
      matrix[6][i] = i % 2 === 0;
      matrix[i][6] = i % 2 === 0;
    }

    // Accumulate rects
    const rects: React.ReactNode[] = [];
    for (let r = 0; r < matrixSize; r++) {
      for (let c = 0; c < matrixSize; c++) {
        if (matrix[r][c]) {
          rects.push(
            <Rect
              key={`${r}-${c}`}
              x={c * cellSize}
              y={r * cellSize}
              width={cellSize + 0.2}
              height={cellSize + 0.2}
              fill={colors.cyanAccent}
            />
          );
        }
      }
    }

    return (
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <Rect width={size} height={size} fill={colors.cardBackgroundLight} rx={12} />
        <G translate="10, 10" scale="0.88">
          {rects}
        </G>
      </Svg>
    );
  };

  const activeChild = children.find(p => p.id === selectedProfileId) || (children.length > 0 ? children[0] : null);
  if (activeChild) {
    activeChild.currentUsageMinutes = currentUsageMinutes;
    activeChild.totalLimitMinutes = limitMinutes;
  }

  const currentLimitMinutes = limitMinutes;
  const setLimitMinutes = changeChildDailyLimit;

  const handleToggleCategory = (category: string, val: boolean) => {
    if (category === 'All Apps and Categories') {
      categoryOrder.forEach(cat => {
        toggleFilterCategory(cat, val);
      });
    } else {
      toggleFilterCategory(category, val);
      if (!val) {
        toggleFilterCategory('All Apps and Categories', false);
      }
    }
  };

  const handleAddUrl = () => {
    if (customUrlInput.trim().length > 0) {
      addBlacklistUrl(customUrlInput.trim());
      setCustomUrlInput('');
    }
  };

  const handleRemoveUrl = (url: string) => {
    removeBlacklistUrl(url);
  };

  const tabs = ['Overview', 'Limits', 'Apps', 'Filter', 'Location', 'Reports', 'Alerts', 'SOS', 'Link'];

  // Circular progress math
  const radius = 50;
  const strokeWidth = 8;
  const circumference = 2 * Math.PI * radius;
  const progressPercent = activeChild ? (activeChild.currentUsageMinutes / (currentLimitMinutes || 240)) : 0;
  const strokeDashoffset = circumference - (Math.min(1, progressPercent) * (270 / 360)) * circumference;

  const renderNotificationSettings = (
    title: string,
    phoneEnabled: boolean,
    setPhoneEnabled: (val: boolean) => void,
    emailEnabled: boolean,
    setEmailEnabled: (val: boolean) => void
  ) => {
    const displayPhone = title === 'Emergency SOS' ? (demoPhone || '+1 (555) 019-8372') : demoPhone;
    const displayEmail = title === 'Emergency SOS' ? (demoEmail || 'parent@family.net') : demoEmail;

    return (
      <View style={[styles.settingCard, { marginTop: 16 }]}>
        <Text style={styles.settingTitle}>{title} Notifications</Text>
        <Text style={styles.settingSub}>Choose where to receive alerts</Text>

        <View style={styles.cardDivider} />

        <View style={styles.contactRow}>
          <Icon name="phone" color={colors.cyanAccent} size={20} />
          <View style={styles.contactInfo}>
            <Text style={styles.contactLabel}>Parent Phone (Demo)</Text>
            <Text style={styles.contactValue}>{displayPhone}</Text>
          </View>
          <Switch
            value={phoneEnabled}
            onValueChange={setPhoneEnabled}
            trackColor={{ true: colors.greenSuccess }}
          />
        </View>

        <View style={[styles.contactRow, { marginTop: 12 }]}>
          <Icon name="email" color={colors.purpleAccent} size={20} />
          <View style={styles.contactInfo}>
            <Text style={styles.contactLabel}>Parent Email (Demo)</Text>
            <Text style={styles.contactValue}>{displayEmail}</Text>
          </View>
          <Switch
            value={emailEnabled}
            onValueChange={setEmailEnabled}
            trackColor={{ true: colors.greenSuccess }}
          />
        </View>
      </View>
    );
  };

  const [showChildLogoutModal, setShowChildLogoutModal] = useState(false);
  const [showLogoutAttemptAlert, setShowLogoutAttemptAlert] = useState(false);
  const [logoutAttemptChildName, setLogoutAttemptChildName] = useState('Child Device');
  const prevChildrenLen = React.useRef(children.length);

  // Listen for real-time child logout attempts
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const attemptRes = await ParentalRepository.checkLogoutAttempt(1);
        if (attemptRes?.has_logout_attempt && attemptRes?.attempts?.length > 0) {
          const attempt = attemptRes.attempts[0];
          setLogoutAttemptChildName(attempt.child_name || (children[0]?.name || 'lokeshBM'));
          setShowLogoutAttemptAlert(true);
        }
      } catch (e) {}
    }, 2000);
    return () => clearInterval(timer);
  }, [children]);

  useEffect(() => {
    if (prevChildrenLen.current > 0 && children.length === 0) {
      setShowChildLogoutModal(true);
    }
    prevChildrenLen.current = children.length;
  }, [children.length]);

  const isChildLinkedAndVerified = activeChild && (activeChild.permissions_granted === true || activeChild.status === 'LINKED');

  if (!isChildLinkedAndVerified) {
    return (
      <View style={{ flex: 1 }}>
        <TwoStepBindingScreen
          onBack={onBack}
          onCheckStatus={refreshData}
        />
        {/* Child Device Logged Out Popup Alert Modal */}
        <Modal visible={showChildLogoutModal} transparent animationType="fade">
          <View style={styles.modalOverlay}>
            <View style={styles.logoutAlertCard}>
              <View style={styles.logoutAlertIconBg}>
                <Icon name="warning" color="#ef4444" size={32} />
              </View>
              <Text style={styles.logoutAlertTitle}>Child Device Logged Out</Text>
              <Text style={styles.logoutAlertMessage}>
                The child device has unlinked and logged out of the application using the Parent Verification Code.
              </Text>
              <TouchableOpacity
                style={styles.logoutAlertBtn}
                onPress={() => setShowChildLogoutModal(false)}
              >
                <Text style={styles.logoutAlertBtnText}>Acknowledge Alert</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />
      
      {/* Real-time Emergency SOS Distress Popup Modal Alert */}
      <Modal visible={sosActive} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={[styles.logoutAlertCard, { borderColor: '#ef4444', borderWidth: 2 }]}>
            <View style={[styles.logoutAlertIconBg, { backgroundColor: 'rgba(239, 68, 68, 0.2)' }]}>
              <Icon name="warning" color="#ef4444" size={40} />
            </View>
            <Text style={[styles.logoutAlertTitle, { color: '#ef4444', fontSize: 20 }]}>
              🚨 EMERGENCY SOS DISTRESS ALERT!
            </Text>
            <Text style={[styles.logoutAlertMessage, { fontSize: 14, color: '#ffffff' }]}>
              Emergency panic alarm triggered from <Text style={{ fontWeight: 'bold', color: '#ef4444' }}>{activeChild?.name || 'Child Device'}</Text>!
            </Text>
            <Text style={{ color: '#94a3b8', fontSize: 12, marginBottom: 16, textAlign: 'center' }}>
              📍 GPS Coordinates: 13.0827° N, 80.2707° E (Live Telemetry Transmitted)
            </Text>
            <View style={{ flexDirection: 'row', width: '100%', gap: 10 }}>
              <TouchableOpacity
                style={[styles.logoutAlertBtn, { flex: 1, backgroundColor: '#8b5cf6' }]}
                onPress={() => setActiveTab('Location')}
              >
                <Text style={styles.logoutAlertBtnText}>View GPS Map</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.logoutAlertBtn, { flex: 1, backgroundColor: '#ef4444' }]}
                onPress={async () => {
                  if (activeChild?.id) {
                    await ParentalRepository.resolveSOS(activeChild.id);
                  }
                  refreshData();
                }}
              >
                <Text style={styles.logoutAlertBtnText}>Acknowledge SOS</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Real-time Child Logout Attempt Security Alert Modal */}
      <Modal visible={showLogoutAttemptAlert} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.logoutAlertCard}>
            <View style={[styles.logoutAlertIconBg, { backgroundColor: 'rgba(245, 158, 11, 0.15)' }]}>
              <Icon name="warning" color="#f59e0b" size={36} />
            </View>
            <Text style={styles.logoutAlertTitle}>Child Device Attempting Logout</Text>
            <Text style={styles.logoutAlertMessage}>
              🚨 Security Alert: {logoutAttemptChildName} is currently trying to log out or unbind the application from their device.
            </Text>
            <TouchableOpacity
              style={[styles.logoutAlertBtn, { backgroundColor: '#f59e0b' }]}
              onPress={() => setShowLogoutAttemptAlert(false)}
            >
              <Text style={styles.logoutAlertBtnText}>Dismiss Security Alert</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <View style={styles.contentWrapper}>

      {/* 1. TOP HEADER APP BAR WITH BACK BUTTON AND THREE DOTS MENU */}
      <View style={[styles.header, { zIndex: 10000 }]}>
        <TouchableOpacity style={styles.backButton} onPress={onBack}>
          <Icon name="arrow-back" color={colors.text} size={20} />
        </TouchableOpacity>
        <View style={styles.headerTitleContainer}>
          <Text style={styles.headerTitle}>Parental Control Shield</Text>
          <Text style={styles.headerSubtitle}>Manage and protect child devices</Text>
        </View>
        <View style={{ position: 'relative' }}>
          <TouchableOpacity style={{ padding: 8, marginLeft: 4 }} onPress={() => setShowMenu(true)}>
            <Icon name="more-vert" color={colors.text} size={24} />
          </TouchableOpacity>

          <Modal
            visible={showMenu}
            transparent={true}
            animationType="none"
            onRequestClose={() => setShowMenu(false)}
          >
            <TouchableOpacity
              style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.25)', justifyContent: 'flex-start', alignItems: 'flex-end', paddingTop: 60, paddingRight: 16 }}
              activeOpacity={1}
              onPress={() => setShowMenu(false)}
            >
              <TouchableOpacity activeOpacity={1} style={[styles.menuDropdown, { position: 'relative', top: 0, right: 0 }]}>
                <View style={styles.menuItem}>
                  <Icon name="people" color={colors.purpleAccent} size={16} />
                  <Text style={styles.menuText}>{children.length} Children Profiles</Text>
                </View>
                <View style={styles.menuDivider} />

                {children.map(child => {
                  const isLinked = child.device && child.device !== 'Unlinked Device Slot';
                  return (
                    <View key={child.id} style={styles.childMenuRow}>
                      <Text style={styles.childMenuName} numberOfLines={1}>{child.name}</Text>
                      {isLinked ? (
                        <TouchableOpacity
                          style={styles.childSignOutBtn}
                          onPress={async () => {
                            setShowMenu(false);
                            if (Platform.OS === 'web') {
                              const ok = typeof (globalThis as any).confirm === 'function' ? (globalThis as any).confirm(`Sign out and remove ${child.name}?`) : true;
                              if (ok) {
                                await unlinkChildDevice(child.id);
                              }
                            } else {
                              Alert.alert(
                                'Sign Out Child',
                                `Are you sure you want to sign out and remove ${child.name}?`,
                                [
                                  { text: 'Cancel', style: 'cancel' },
                                  { text: 'Sign Out', style: 'destructive', onPress: () => unlinkChildDevice(child.id) }
                                ]
                              );
                            }
                          }}
                        >
                          <Text style={styles.childSignOutBtnText}>Sign Out</Text>
                        </TouchableOpacity>
                      ) : (
                        <Text style={styles.childUnlinkedText}>Unlinked</Text>
                      )}
                    </View>
                  );
                })}

                <View style={styles.menuDivider} />
                {onSignOut && (
                  <TouchableOpacity
                    style={styles.menuItem}
                    onPress={() => {
                      setShowMenu(false);
                      onSignOut();
                    }}
                  >
                    <Icon name="exit-to-app" color={colors.redDanger} size={16} />
                    <Text style={[styles.menuText, { color: colors.redDanger }]}>Sign Out Parent</Text>
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
            </TouchableOpacity>
          </Modal>
        </View>
      </View>

      {/* 2. CHILD PROFILE SELECTOR ROW (Only if children exist) */}
      {children.length > 0 && (
        <View style={styles.profilesRowWrapper}>
          <ScrollView horizontal={true} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.profilesScrollContent}>
            {children.map(profile => {
              const isSelected = selectedProfileId === profile.id;
              return (
                <View
                  key={profile.id}
                  style={[
                    styles.profileCard,
                    isSelected ? { borderColor: profile.avatarColor } : styles.profileCardInactive,
                    { width: 175 }
                  ]}
                >
                  <TouchableOpacity
                    style={{ flex: 1, flexDirection: 'row', alignItems: 'center' }}
                    onPress={() => selectProfile(profile.id)}
                  >
                    <View style={[styles.avatar, { backgroundColor: profile.avatarColor }]}>
                      <Text style={styles.avatarText}>{profile.name.charAt(0)}</Text>
                    </View>
                    <View style={styles.profileInfo}>
                      <Text style={styles.profileName} numberOfLines={1}>{profile.name}</Text>
                      <Text style={styles.profileSub} numberOfLines={1}>
                        {profile.age} yrs • {(profile.is_device_linked || profile.status === 'LINKED') ? (profile.deviceName || profile.device || 'Connected') : 'Not Connected'}
                      </Text>
                    </View>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.cardSignOutBtn}
                    onPress={async () => {
                      if (Platform.OS === 'web') {
                        const ok = typeof (globalThis as any).confirm === 'function' ? (globalThis as any).confirm(`Sign out and remove ${profile.name}?`) : true;
                        if (ok) {
                          await unlinkChildDevice(profile.id);
                        }
                      } else {
                        Alert.alert(
                          'Sign Out Child',
                          `Are you sure you want to sign out and remove ${profile.name}?`,
                          [
                            { text: 'Cancel', style: 'cancel' },
                            { text: 'Sign Out', style: 'destructive', onPress: () => unlinkChildDevice(profile.id) }
                          ]
                        );
                      }
                    }}
                    activeOpacity={0.7}
                  >
                    <Icon name="exit-to-app" color={colors.redDanger} size={14} />
                  </TouchableOpacity>
                </View>
              );
            })}

            {/* Add Child Profile Card */}
            <TouchableOpacity
              style={[styles.profileCard, styles.addProfileCard]}
              onPress={() => setShowAddChildModal(true)}
            >
              <View style={[styles.avatar, { backgroundColor: colors.border }]}>
                <Text style={[styles.avatarText, { color: colors.textMuted }]}>+</Text>
              </View>
              <View style={styles.profileInfo}>
                <Text style={[styles.profileName, { color: colors.text }]}>Add Child</Text>
                <Text style={styles.profileSub}>New Profile</Text>
              </View>
            </TouchableOpacity>
          </ScrollView>
        </View>
      )}

      {/* Create Child Profile Modal */}
      <Modal
        visible={showAddChildModal}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowAddChildModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <TouchableOpacity
              style={styles.modalCloseBtn}
              onPress={() => setShowAddChildModal(false)}
            >
              <Icon name="close" color={colors.text} size={18} />
            </TouchableOpacity>

            <View style={styles.subHeader}>
              <Icon name="people" color={colors.purpleAccent} size={18} />
              <Text style={styles.subHeaderTag}>CREATE PROFILE</Text>
            </View>

            <Text style={styles.subMainTitle}>Add New Child Profile</Text>
            <Text style={styles.subDescription}>
              Enter your child's name and age to create a profile and generate a linking code.
            </Text>

            <View style={{ width: '100%', marginBottom: 20 }}>
              <View style={styles.modalInputWrapper}>
                <Icon name="person" color={colors.textMuted} size={18} />
                <TextInput
                  style={styles.modalInput}
                  placeholder="Child's Name"
                  placeholderTextColor={colors.textMuted}
                  value={newChildName}
                  onChangeText={setNewChildName}
                />
              </View>

              <View style={[styles.modalInputWrapper, { marginTop: 12 }]}>
                <Icon name="clock" color={colors.textMuted} size={18} />
                <TextInput
                  style={styles.modalInput}
                  placeholder="Child's Age (e.g. 10)"
                  placeholderTextColor={colors.textMuted}
                  keyboardType="numeric"
                  value={newChildAge}
                  onChangeText={setNewChildAge}
                />
              </View>
            </View>

            <TouchableOpacity
              style={[styles.primaryBtn, { backgroundColor: colors.purpleAccent }]}
              onPress={handleAddChild}
              disabled={isCreatingChild}
            >
              {isCreatingChild ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.primaryBtnText}>Create Profile</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* UNLINKED STATE: SHOW LINKING CODE ONLY IF NO CHILD DEVICE LINKED */}
      {children.length === 0 ? (
        <ScrollView contentContainerStyle={styles.viewContent}>
          <View style={[styles.linkCard, { marginTop: 16 }]}>
            <View style={{ alignItems: 'center', marginBottom: 20 }}>
              <View style={{ width: 60, height: 60, borderRadius: 30, backgroundColor: colors.purpleAccent + '20', justifyContent: 'center', alignItems: 'center', marginBottom: 14 }}>
                <Icon name="phonelink-setup" color={colors.purpleAccent} size={32} />
              </View>
              <Text style={{ color: colors.text, fontSize: 22, fontWeight: 'bold', textAlign: 'center' }}>
                Pair Child Device
              </Text>
              <Text style={{ color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 6, lineHeight: 18, paddingHorizontal: 12 }}>
                No child device is linked yet. Enter this 6-digit Linking Code on your child's phone to connect and view their dashboard.
              </Text>
            </View>

            <View style={styles.codeContainer}>
              <Text style={styles.codeLabel}>YOUR PARENT LINKING CODE</Text>
              <Text style={styles.codeText}>{pairingCode || '819-860'}</Text>
              <Text style={styles.codeSub}>Use this code on the child device when setting up Child Mode.</Text>
            </View>

            <View style={{ backgroundColor: colors.cardBackgroundLight, padding: 18, borderRadius: 14, borderWidth: 1, borderColor: colors.border, marginBottom: 24 }}>
              <Text style={{ color: colors.text, fontSize: 14, fontWeight: 'bold', marginBottom: 8 }}>Steps to Link Child Device:</Text>
              <Text style={{ color: colors.textMuted, fontSize: 13, lineHeight: 22 }}>
                1. Open Aepttas Shield on your child's phone.{'\n'}
                2. Select "Child Device" mode on the main role screen.{'\n'}
                3. Enter child's name and this 6-digit code ({pairingCode || '819-860'}).{'\n'}
                4. Tap "Link My Device" to complete pairing.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.primaryBtn, { backgroundColor: colors.purpleAccent }]}
              onPress={refreshData}
            >
              <Icon name="refresh" color="#fff" size={18} />
              <Text style={[styles.primaryBtnText, { marginLeft: 8 }]}>Check Pairing Status</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      ) : (
        <>
          {/* 3. HORIZONTAL SCROLLABLE TABS */}
          <View style={styles.tabsWrapper}>
            <ScrollView horizontal={true} showsHorizontalScrollIndicator={false}>
              {tabs.map(tab => {
                const isSelected = activeTab === tab;
                return (
                  <TouchableOpacity
                    key={tab}
                    style={[styles.tab, isSelected && styles.tabActive]}
                    onPress={() => setActiveTab(tab)}
                  >
                    <Text style={[styles.tabText, isSelected && styles.tabTextActive]}>{tab}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>

          {/* SOS Alert Banner */}
          {sosActive && sosBannerVisible && (
            <TouchableOpacity style={styles.sosBanner} onPress={() => setSosBannerVisible(false)}>
              <View style={styles.sosBannerContent}>
                <Icon name="warning" color={colors.text} size={20} />
                <View style={styles.sosBannerTexts}>
                  <Text style={styles.sosBannerTitle}>EMERGENCY SOS RECEIVED!</Text>
                  <Text style={styles.sosBannerSub}>
                    Child {sosTriggeredBy} triggered panic alert. Coordinates shared.
                  </Text>
                </View>
                <View style={styles.dismissBadge}>
                  <Text style={styles.dismissText}>DISMISS</Text>
                </View>
              </View>
            </TouchableOpacity>
          )}

          {/* 4. ACTIVE SUB-SCREEN VIEW CONTROLLER */}
          <ScrollView contentContainerStyle={styles.viewContent}>
        {activeTab === 'Overview' && (
          <View style={{ width: '100%' }}>
            {!(activeChild.is_device_linked || activeChild.status === 'LINKED') ? (
              <View style={[styles.linkCard, { marginTop: 8, padding: 20 }]}>
                <View style={{ alignItems: 'center', marginBottom: 16 }}>
                  <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: colors.orangeWarning + '20', justifyContent: 'center', alignItems: 'center', marginBottom: 12 }}>
                    <Icon name="phonelink-erase" color={colors.orangeWarning} size={30} />
                  </View>
                  <Text style={{ color: colors.text, fontSize: 18, fontWeight: 'bold', textAlign: 'center' }}>
                    {activeChild.name}'s Device Not Connected
                  </Text>
                  <Text style={{ color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 6, lineHeight: 18, paddingHorizontal: 8 }}>
                    This child profile is waiting for device connection. Open the Shield app on {activeChild.name}'s phone and enter the linking code below.
                  </Text>
                </View>

                <View style={[styles.codeContainer, { marginVertical: 14 }]}>
                  <Text style={styles.codeLabel}>LINKING CODE FOR {activeChild.name.toUpperCase()}</Text>
                  <Text style={[styles.codeText, { letterSpacing: 4 }]}>
                    {activeChild.linking_code || pairingCode || '819-860'}
                  </Text>
                  <Text style={styles.codeSub}>Enter this code on the child's phone in Child Mode</Text>
                </View>

                <View style={{ backgroundColor: colors.cardBackgroundLight, padding: 14, borderRadius: 12, borderWidth: 1, borderColor: colors.border, marginBottom: 18 }}>
                  <Text style={{ color: colors.text, fontSize: 13, fontWeight: 'bold', marginBottom: 6 }}>Steps to connect:</Text>
                  <Text style={{ color: colors.textMuted, fontSize: 12, lineHeight: 20 }}>
                    1. Open Aepttas Shield on {activeChild.name}'s device.{'\n'}
                    2. Choose "Child Device" mode.{'\n'}
                    3. Enter child name and linking code: <Text style={{ color: colors.cyanAccent, fontWeight: 'bold' }}>{activeChild.linking_code || pairingCode || '819-860'}</Text>.{'\n'}
                    4. Telemetry and controls will connect automatically.
                  </Text>
                </View>

                <TouchableOpacity
                  style={[styles.primaryBtn, { backgroundColor: colors.redDanger + '20', borderWidth: 1, borderColor: colors.redDanger, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' }]}
                  onPress={async () => {
                    if (Platform.OS === 'web') {
                      const ok = typeof (globalThis as any).confirm === 'function' ? (globalThis as any).confirm(`Remove ${activeChild.name}'s profile?`) : true;
                      if (ok) {
                        await unlinkChildDevice(activeChild.id);
                      }
                    } else {
                      Alert.alert(
                        'Remove Child Profile',
                        `Are you sure you want to sign out and remove ${activeChild.name}'s profile?`,
                        [
                          { text: 'Cancel', style: 'cancel' },
                          { text: 'Remove Profile', style: 'destructive', onPress: () => unlinkChildDevice(activeChild.id) }
                        ]
                      );
                    }
                  }}
                  activeOpacity={0.8}
                >
                  <Icon name="delete" color={colors.redDanger} size={16} />
                  <Text style={[styles.primaryBtnText, { color: colors.redDanger, marginLeft: 8 }]}>
                    Sign Out & Remove Child Profile
                  </Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                {/* Status Card */}
                <View style={styles.deviceStatusCard}>
                  <View style={styles.deviceStatusRow}>
                    <View
                      style={[
                        styles.statusDot,
                        { backgroundColor: deviceLocked ? colors.redDanger : colors.greenSuccess },
                      ]}
                    />
                    <View style={styles.deviceStatusTexts}>
                      <Text style={styles.statusTitle}>
                        {deviceLocked ? 'Device Blocked (Locked)' : `${activeChild.name}'s Device Connected`}
                      </Text>
                      <Text style={styles.statusSub}>
                        {activeChild.deviceName || activeChild.device || 'Android Device'} • {activeChild.osType || activeChild.os_type || 'Android'}
                      </Text>
                      <Text style={[styles.statusSub, { marginTop: 3, color: colors.cyanAccent, fontWeight: '600' }]}>
                        Battery: {activeChild.batteryLevel != null ? `${activeChild.batteryLevel}%` : 'Normal'} • Linked via Link-Code
                      </Text>
                    </View>
                  </View>
                  <Icon
                    name={(activeChild.batteryLevel || 95) > 80 ? 'battery-full' : 'battery-alert'}
                    color={(activeChild.batteryLevel || 95) > 20 ? colors.greenSuccess : colors.redDanger}
                    size={26}
                  />
                </View>

                {/* Screen Time Ring */}
                <View style={styles.overviewGaugeCard}>
                  <Text style={styles.gaugeHeader}>DAILY SCREEN TIME</Text>
                  <View style={styles.overviewGaugeContainer}>
                    <Svg width={150} height={150} viewBox="0 0 120 120">
                      <G rotation="135" origin="60, 60">
                        <Circle
                          cx="60"
                          cy="60"
                          r={radius}
                          stroke={colors.border}
                          strokeWidth={strokeWidth}
                          fill="none"
                          strokeDasharray={`${(270 / 360) * circumference} ${circumference}`}
                          strokeLinecap="round"
                        />
                        <Circle
                          cx="60"
                          cy="60"
                          r={radius}
                          stroke={colors.pinkAccent}
                          strokeWidth={strokeWidth}
                          fill="none"
                          strokeDasharray={circumference}
                          strokeDashoffset={strokeDashoffset}
                          strokeLinecap="round"
                        />
                      </G>
                    </Svg>
                    <View style={styles.overviewGaugeTexts}>
                      <Text style={styles.usageHourText}>
                        {Math.floor(activeChild.currentUsageMinutes / 60)}h{' '}
                        {activeChild.currentUsageMinutes % 60}m
                      </Text>
                      <Text style={styles.limitLabelText}>of {currentLimitMinutes / 60}h limit</Text>
                    </View>
                  </View>

                  <TouchableOpacity
                    style={[styles.remoteLockBtn, { backgroundColor: deviceLocked ? colors.greenSuccess : colors.redDanger }]}
                    onPress={() => changeDeviceLock(!deviceLocked)}
                  >
                    <Icon name={deviceLocked ? 'lock-open' : 'lock'} color={colors.text} size={18} />
                    <Text style={styles.remoteLockBtnText}>
                      {deviceLocked ? 'Unlock Child Device Now' : 'Lock Child Device Remotely'}
                    </Text>
                  </TouchableOpacity>
                </View>

                {/* App Usage List */}
                <Text style={styles.blockSectionTitle}>Most Used Apps Today</Text>
                {activeChild.appUsage && activeChild.appUsage.length > 0 ? (
                  activeChild.appUsage.map((usage: any) => (
                    <View key={usage.name} style={styles.usageRow}>
                      <View style={styles.usageLeft}>
                        <View style={[styles.appIconContainer, { backgroundColor: (usage.color || colors.purpleAccent) + '22' }]}>
                          <Icon
                            name="apps"
                            color={usage.color || colors.purpleAccent}
                            size={20}
                          />
                        </View>
                        <Text style={styles.appName}>{usage.name}</Text>
                      </View>
                      <Text style={styles.appDuration}>{usage.time || '0m'}</Text>
                    </View>
                  ))
                ) : (
                  <View style={{ padding: 16, backgroundColor: colors.cardBackgroundLight, borderRadius: 12, alignItems: 'center', marginBottom: 16 }}>
                    <Icon name="access-time" color={colors.textMuted} size={24} />
                    <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 6 }}>
                      No app activity recorded for this child profile today.
                    </Text>
                  </View>
                )}

                {/* Direct Sign Out / Unlink Button for Connected Device */}
                <TouchableOpacity
                  style={[styles.primaryBtn, { backgroundColor: colors.redDanger + '20', borderWidth: 1, borderColor: colors.redDanger, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginTop: 12, marginBottom: 24 }]}
                  onPress={async () => {
                    if (Platform.OS === 'web') {
                      const ok = typeof (globalThis as any).confirm === 'function' ? (globalThis as any).confirm(`Sign out and disconnect ${activeChild.name}'s device?`) : true;
                      if (ok) {
                        await unlinkChildDevice(activeChild.id);
                      }
                    } else {
                      Alert.alert(
                        'Sign Out Child Device',
                        `Are you sure you want to disconnect and remove ${activeChild.name}'s profile?`,
                        [
                          { text: 'Cancel', style: 'cancel' },
                          { text: 'Sign Out Device', style: 'destructive', onPress: () => unlinkChildDevice(activeChild.id) }
                        ]
                      );
                    }
                  }}
                  activeOpacity={0.8}
                >
                  <Icon name="exit-to-app" color={colors.redDanger} size={16} />
                  <Text style={[styles.primaryBtnText, { color: colors.redDanger, marginLeft: 8 }]}>
                    Sign Out & Disconnect Child Profile
                  </Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}

        {activeTab === 'Limits' && (
          <View style={{ width: '100%' }}>
            <View style={styles.settingCard}>
              <Text style={styles.settingTitle}>Daily Screen Time Limit</Text>
              <Text style={styles.settingSub}>Set total minutes/hours allowed per day</Text>

              <View style={styles.limitValueRow}>
                <Text style={styles.limitBoundary}>0h</Text>
                <Text style={styles.limitCurrentValue}>
                  {Math.floor(currentLimitMinutes / 60)}h {currentLimitMinutes % 60}m
                </Text>
                <Text style={styles.limitBoundary}>6h</Text>
              </View>

              {/* Simulated Slider */}
              <View style={styles.sliderContainer}>
                <TouchableOpacity
                  style={[styles.sliderButton, { marginRight: 16 }]}
                  onPress={() => setLimitMinutes(Math.max(15, currentLimitMinutes - 15))}
                >
                  <Text style={styles.sliderButtonText}>-</Text>
                </TouchableOpacity>

                <View style={styles.sliderTrackBg}>
                  <View
                    style={[
                      styles.sliderTrackFill,
                      { width: `${(currentLimitMinutes / 360) * 100}%` },
                    ]}
                  />
                </View>

                <TouchableOpacity
                  style={[styles.sliderButton, { marginLeft: 16 }]}
                  onPress={() => setLimitMinutes(Math.min(360, currentLimitMinutes + 15))}
                >
                  <Text style={styles.sliderButtonText}>+</Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* Schedules */}
            <View style={[styles.settingCard, { marginTop: 16 }]}>
              <View style={styles.switchRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.settingTitle}>Schedule Bedtime Off-Hours</Text>
                  <Text style={styles.settingSub}>Automatically locks device at night</Text>
                </View>
                <Switch
                  value={true}
                  onValueChange={() => {}}
                  trackColor={{ true: colors.purpleAccent }}
                />
              </View>

              <View style={styles.cardDivider} />

              <View style={styles.scheduleRow}>
                <View style={styles.scheduleLeft}>
                  <Icon name="bedtime" color={colors.purpleAccent} size={22} />
                  <View style={styles.scheduleTexts}>
                    <Text style={styles.scheduleTitle}>Bedtime Lock Time</Text>
                    <Text style={styles.scheduleTime}>Everyday 21:00 to 07:00</Text>
                  </View>
                </View>
                <TouchableOpacity>
                  <Icon name="edit" color={colors.textMuted} size={18} />
                </TouchableOpacity>
              </View>

              <View style={[styles.scheduleRow, { marginTop: 16 }]}>
                <View style={styles.scheduleLeft}>
                  <Icon name="school" color={colors.cyanAccent} size={22} />
                  <View style={styles.scheduleTexts}>
                    <Text style={styles.scheduleTitle}>School Hour Block</Text>
                    <Text style={styles.scheduleTime}>Mon-Fri 08:30 to 14:30</Text>
                  </View>
                </View>
                <TouchableOpacity>
                  <Icon name="edit" color={colors.textMuted} size={18} />
                </TouchableOpacity>
              </View>
            </View>

            {renderNotificationSettings('Screen Time Limits', notifyLimitsPhone, setNotifyLimitsPhone, notifyLimitsEmail, setNotifyLimitsEmail)}
          </View>
        )}

        {activeTab === 'Apps' && (
          <View style={{ width: '100%' }}>
            <Text style={styles.blockSectionTitle}>App Restriction Policies</Text>
            {apps.map(app => {
              const isBlocked = app.is_blocked;
              return (
                <View key={app.app_id} style={styles.policyRow}>
                  <View style={styles.policyLeft}>
                    <Icon
                      name={
                        app.app_name === 'Roblox' || app.app_name === 'Minecraft'
                          ? 'gamepad'
                          : app.app_name.includes('YouTube')
                          ? 'play-circle'
                          : 'globe'
                      }
                      color={isBlocked ? colors.redDanger : colors.greenSuccess}
                      size={20}
                    />
                    <Text style={styles.policyName}>{app.app_name}</Text>
                  </View>
                  <View style={styles.policyRight}>
                    <Text style={[styles.statusText, { color: isBlocked ? colors.redDanger : colors.greenSuccess }]}>
                      {isBlocked ? 'BLOCKED' : 'ALLOWED'}
                    </Text>
                    <Switch
                      value={!isBlocked}
                      onValueChange={() => toggleBlockApp(app.app_id, app.app_name)}
                      trackColor={{ true: colors.greenSuccess, false: colors.redDanger }}
                    />
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {activeTab === 'Filter' && (
          <View style={{ width: '100%' }}>
            <Text style={styles.blockSectionTitle}>Content Category Filter</Text>
            
            {/* Search Input Bar */}
            <View style={styles.searchContainer}>
              <Icon name="search" color={colors.textMuted} size={18} />
              <TextInput
                style={styles.searchInput}
                placeholder="Search"
                placeholderTextColor={colors.textMuted}
                value={categorySearchQuery}
                onChangeText={setCategorySearchQuery}
                autoCapitalize="none"
              />
            </View>

            {/* Premium Categories Card List */}
            <View style={styles.categoryCardContainer}>
              {categoryOrder
                .filter(cat => {
                  return cat.toLowerCase().includes(categorySearchQuery.toLowerCase());
                })
                .map((category) => {
                  const isBlocked = blockedCategories[category] || false;
                  return (
                    <View key={category} style={{ borderBottomWidth: 1, borderBottomColor: colors.border }}>
                      <TouchableOpacity
                        style={[
                          styles.categoryRow,
                          { borderBottomWidth: 0 }
                        ]}
                        onPress={() => {
                          if (category !== 'All Apps and Categories') {
                            setExpandedCategory(expandedCategory === category ? null : category);
                          } else {
                            handleToggleCategory(category, !isBlocked);
                          }
                        }}
                      >
                        <View style={styles.categoryLeft}>
                          {/* Circular selector indicator on the left */}
                          <TouchableOpacity
                            style={[
                              styles.circularCheckbox,
                              { borderColor: isBlocked ? colors.blueAccent : colors.textMuted + '66' },
                              isBlocked && { backgroundColor: colors.blueAccent }
                            ]}
                            onPress={() => handleToggleCategory(category, !isBlocked)}
                          >
                            {isBlocked && <Icon name="check" color="#fff" size={12} />}
                          </TouchableOpacity>
                          <Text style={styles.categoryNameText}>{category}</Text>
                        </View>
                        {/* Chevron arrow `>` on the right (except All Apps) */}
                        {category !== 'All Apps and Categories' && (
                          <Icon 
                            name={expandedCategory === category ? "expand-more" : "chevron-right"} 
                            color={colors.textMuted} 
                            size={18} 
                          />
                        )}
                      </TouchableOpacity>

                      {/* Expanded Apps List */}
                      {expandedCategory === category && (
                        <View style={styles.expandedAppsContainer}>
                          {apps.filter(a => a.category === category || category === 'All Apps and Categories').length > 0 ? (
                            apps.filter(a => a.category === category || category === 'All Apps and Categories').map((app) => {
                              const isAppBlockedByCat = isBlocked;
                              const isAppBlocked = isAppBlockedByCat || app.is_blocked;
                              return (
                                <View key={app.app_id || app.app_name} style={styles.appPolicyRow}>
                                  <View style={styles.appPolicyLeft}>
                                    <View style={[styles.appIconBg, { backgroundColor: colors.cardBackgroundLight }]}>
                                      <Icon name="apps" color={isAppBlocked ? colors.redDanger : colors.greenSuccess} size={16} />
                                    </View>
                                    <Text style={[styles.appNameText, { color: isAppBlocked ? colors.redDanger : colors.text }]}>
                                      {app.app_name}
                                    </Text>
                                  </View>
                                  <Switch
                                    value={!isAppBlocked}
                                    disabled={isAppBlockedByCat}
                                    onValueChange={() => toggleBlockApp(app.app_id, app.app_name)}
                                    trackColor={{ true: colors.greenSuccess, false: colors.redDanger }}
                                  />
                                </View>
                              );
                            })
                          ) : (
                            <View style={{ paddingVertical: 12, paddingHorizontal: 16 }}>
                              <Text style={{ color: colors.textMuted, fontSize: 13, fontStyle: 'italic' }}>
                                No installed applications detected in this category.
                              </Text>
                            </View>
                          )}
                        </View>
                      )}
                    </View>
                  );
                })}
            </View>

            <Text style={[styles.blockSectionTitle, { marginTop: 24 }]}>Custom Domain Filter</Text>
            <View style={styles.settingCard}>
              <Text style={styles.settingTitle}>Website Domain Filter</Text>
              <Text style={styles.settingSub}>Block inappropriate or unwanted web content</Text>

              <View style={styles.addUrlRow}>
                <TextInput
                  style={styles.urlInput}
                  placeholder="Enter domain (e.g. facebook.com)"
                  placeholderTextColor={colors.textMuted}
                  value={customUrlInput}
                  onChangeText={setCustomUrlInput}
                  autoCapitalize="none"
                />
                <TouchableOpacity style={styles.addUrlBtn} onPress={handleAddUrl}>
                  <Text style={styles.addUrlBtnText}>Add</Text>
                </TouchableOpacity>
              </View>
            </View>

            <Text style={styles.blockSectionTitle}>Blocked Websites ({blockedUrls.length})</Text>
            {blockedUrls.map(url => (
              <View key={url} style={styles.urlRow}>
                <Text style={styles.urlText}>{url}</Text>
                <TouchableOpacity onPress={() => handleRemoveUrl(url)}>
                  <Icon name="close" color={colors.redDanger} size={18} />
                </TouchableOpacity>
              </View>
            ))}
          </View>
        )}

        {activeTab === 'Location' && (
          <View style={{ width: '100%' }}>
            {/* Enable Location Tracking Switch Card */}
            <View style={styles.settingCard}>
              <View style={styles.switchRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.settingTitle}>Enable Location Tracking</Text>
                  <Text style={styles.settingSub}>Track child's device location and enforce safe zone</Text>
                </View>
                <Switch
                  value={locationTrackingEnabled}
                  onValueChange={setLocationTrackingEnabled}
                  trackColor={{ true: colors.greenSuccess }}
                />
              </View>
            </View>

            {/* Enable Geofence Switch Card */}
            <View style={[styles.settingCard, { marginTop: 12 }]}>
              <View style={styles.switchRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.settingTitle}>Enable Geofence</Text>
                  <Text style={styles.settingSub}>Enforce safe zone boundaries on the map</Text>
                </View>
                <Switch
                  value={geofenceEnabled}
                  onValueChange={setGeofenceEnabled}
                  trackColor={{ true: colors.greenSuccess }}
                />
              </View>
            </View>

            {locationTrackingEnabled && (
              <View style={[styles.locationRadarCard, { marginTop: 12 }]}>
                {/* Google Map View */}
                <View style={{ width: '100%', height: 220, borderRadius: 12, overflow: 'hidden' }}>
                  {Platform.OS === 'web' ? (
                    <View style={{ width: '100%', height: '100%', backgroundColor: colors.cardBackgroundLight, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: colors.border, padding: 16 }}>
                      <Icon name="my-location" color={colors.purpleAccent} size={36} />
                      <Text style={{ color: colors.text, fontSize: 15, fontWeight: 'bold', marginTop: 8 }}>
                        Live GPS Location Radar
                      </Text>
                      <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 4, textAlign: 'center' }}>
                        {location?.current_address || (location?.latitude && location?.longitude ? `${Number(location.latitude).toFixed(4)}°, ${Number(location.longitude).toFixed(4)}°` : 'Waiting for device GPS signal...')}
                      </Text>
                      <Text style={{ color: colors.greenSuccess, fontSize: 11, fontWeight: 'bold', marginTop: 6 }}>
                        SAFE ZONE ACTIVE ({geofenceRadius}m radius)
                      </Text>
                    </View>
                  ) : (
                    <MapView
                      style={{ width: '100%', height: '100%' }}
                      initialRegion={{
                        latitude: location?.latitude ? Number(location.latitude) : 13.0827,
                        longitude: location?.longitude ? Number(location.longitude) : 80.2707,
                        latitudeDelta: 0.01,
                        longitudeDelta: 0.01,
                      }}
                    >
                      {/* Circle Marker for Safe Zone / Geofence */}
                      {geofenceEnabled && (
                        <MapCircle
                          center={{
                            latitude: location?.latitude ? Number(location.latitude) : 13.0827,
                            longitude: location?.longitude ? Number(location.longitude) : 80.2707,
                          }}
                          radius={geofenceRadius}
                          fillColor={colors.greenSuccess + '20'}
                          strokeColor={colors.greenSuccess}
                          strokeWidth={2}
                        />
                      )}

                      {/* Child Pin Marker */}
                      <Marker
                        coordinate={{
                          latitude: location?.latitude ? Number(location.latitude) : 13.0827,
                          longitude: location?.longitude ? Number(location.longitude) : 80.2707,
                        }}
                        title={activeChild?.name || 'Child'}
                        description={location?.current_address || 'Live Location'}
                        pinColor={colors.purpleAccent}
                      />
                    </MapView>
                  )}
                </View>

                {/* Safe Zone Radius row */}
                <View style={styles.radiusInputRow}>
                  <Text style={styles.radiusLabelText}>Safe Zone Radius:</Text>
                  <View style={styles.radiusInputContainer}>
                    <TextInput
                      style={styles.radiusInput}
                      value={geofenceRadius.toString()}
                      onChangeText={val => {
                        const parsed = parseInt(val, 10);
                        if (!isNaN(parsed)) {
                          setGeofenceRadius(parsed);
                        } else if (val === '') {
                          setGeofenceRadius(0);
                        }
                      }}
                      keyboardType="numeric"
                      textAlign="center"
                    />
                  </View>
                  <Text style={styles.radiusUnitText}>meters</Text>
                </View>

                {/* Adjust geofence radius slider */}
                <View style={styles.sliderContainer}>
                  <TouchableOpacity
                    style={styles.sliderButton}
                    onPress={() => setGeofenceRadius(Math.max(10, geofenceRadius - 10))}
                  >
                    <Text style={styles.sliderButtonText}>-</Text>
                  </TouchableOpacity>
                  <View style={styles.sliderTrackBg}>
                    <View
                      style={[
                        styles.sliderTrackFill,
                        { width: `${Math.max(0, Math.min(100, ((geofenceRadius - 10) / 490) * 100))}%` },
                      ]}
                    />
                  </View>
                  <TouchableOpacity
                    style={styles.sliderButton}
                    onPress={() => setGeofenceRadius(Math.min(500, geofenceRadius + 10))}
                  >
                    <Text style={styles.sliderButtonText}>+</Text>
                  </TouchableOpacity>
                </View>

                {/* Live Address Section */}
                <View style={styles.liveAddressContainer}>
                  <Text style={styles.liveAddressLabel}>LIVE ADDRESS</Text>
                  <Text style={styles.liveAddressText}>
                    {location?.current_address || 'Near Government School, Campus Zone'}
                  </Text>
                </View>

                {/* Coordinates Row */}
                <View style={styles.coordsRow}>
                  <View style={styles.coordsCol}>
                    <Text style={styles.coordsLabel}>LATITUDE</Text>
                    <Text style={styles.coordsValue}>
                      {location?.latitude ? Number(location.latitude).toFixed(6) : '13.082700'}
                    </Text>
                  </View>
                  <View style={styles.coordsDivider} />
                  <View style={styles.coordsCol}>
                    <Text style={styles.coordsLabel}>LONGITUDE</Text>
                    <Text style={styles.coordsValue}>
                      {location?.longitude ? Number(location.longitude).toFixed(6) : '80.270700'}
                    </Text>
                  </View>
                </View>
              </View>
            )}
          </View>
        )}

        {activeTab === 'Reports' && (
          <View style={{ width: '100%' }}>
            {/* 1. Weekly Summary Overview */}
            <View style={styles.reportCard}>
              <Text style={styles.reportCardMainTitle}>Weekly Summary Overview</Text>
              <View style={styles.summaryStatsRow}>
                <View style={styles.summaryStatCol}>
                  <Text style={styles.summaryStatLabel}>TODAY'S USAGE</Text>
                  <Text style={styles.summaryStatValue}>
                    {Math.floor((activeChild.currentUsageMinutes || 0) / 60)}h {(activeChild.currentUsageMinutes || 0) % 60}m
                  </Text>
                </View>
                <View style={styles.summaryStatCol}>
                  <Text style={styles.summaryStatLabel}>DAILY LIMIT</Text>
                  <Text style={styles.summaryStatValue}>
                    {Math.floor(currentLimitMinutes / 60)}h {currentLimitMinutes % 60}m
                  </Text>
                </View>
                <View style={styles.summaryStatCol}>
                  <Text style={styles.summaryStatLabel}>LIMIT BREACHES</Text>
                  <Text style={[styles.summaryStatValue, { color: (activeChild.currentUsageMinutes || 0) > currentLimitMinutes ? colors.pinkAccent : colors.greenSuccess }]}>
                    {(activeChild.currentUsageMinutes || 0) > currentLimitMinutes ? '1 Time' : '0 Times'}
                  </Text>
                </View>
              </View>
            </View>

            {/* 2. Device Screentime Status */}
            <View style={styles.reportCard}>
              <Text style={styles.reportCardMainTitle}>Real-Time Screentime Status</Text>
              <Text style={styles.reportCardSubtitle}>Live sync from child device</Text>
              <View style={{ marginTop: 12 }}>
                <View style={styles.reportBarRow}>
                  <Text style={styles.reportBarLabel}>Screentime Consumed</Text>
                  <View style={styles.reportBarBg}>
                    <View
                      style={[
                        styles.reportBarFillLine,
                        {
                          width: `${Math.min(100, Math.round(((activeChild.currentUsageMinutes || 0) / Math.max(1, currentLimitMinutes)) * 100))}%`,
                          backgroundColor: (activeChild.currentUsageMinutes || 0) > currentLimitMinutes ? colors.redDanger : colors.cyanAccent,
                        },
                      ]}
                    />
                  </View>
                  <Text style={styles.reportBarPct}>
                    {Math.min(100, Math.round(((activeChild.currentUsageMinutes || 0) / Math.max(1, currentLimitMinutes)) * 100))}%
                  </Text>
                </View>
              </View>
            </View>

            {/* 3. Category App Distribution */}
            <View style={styles.reportCard}>
              <Text style={styles.reportHeaderTitle}>CATEGORY ACTIVITY</Text>
              {apps.length > 0 ? (
                ['Social', 'Entertainment', 'Games', 'Productivity'].map(cat => {
                  const catApps = apps.filter(a => a.category === cat);
                  const pct = Math.round((catApps.length / Math.max(1, apps.length)) * 100);
                  if (pct === 0) return null;
                  return (
                    <View key={cat} style={styles.reportBarRow}>
                      <Text style={styles.reportBarLabel}>{cat} Apps</Text>
                      <View style={styles.reportBarBg}>
                        <View style={[styles.reportBarFillLine, { width: `${pct}%`, backgroundColor: colors.cyanAccent }]} />
                      </View>
                      <Text style={styles.reportBarPct}>{pct}%</Text>
                    </View>
                  );
                })
              ) : (
                <View style={{ paddingVertical: 12, alignItems: 'center' }}>
                  <Text style={{ color: colors.textMuted, fontSize: 13 }}>
                    No categorized app distribution available for today.
                  </Text>
                </View>
              )}
            </View>

            {/* 4. Recent Blocked Activities */}
            <View style={styles.reportCard}>
              <Text style={styles.reportCardMainTitleBold}>Recent Blocked Activities</Text>
              <View style={styles.blockedListContainer}>
                {blockedUrls.length > 0 ? (
                  blockedUrls.map((url, idx) => (
                    <View key={url} style={[styles.activityAlert, idx > 0 && { marginTop: 12 }]}>
                      <Icon name="cancel" color={colors.redDanger} size={18} />
                      <View style={styles.activityAlertTexts}>
                        <Text style={styles.activityAlertText}>Blocked web destination: {url}</Text>
                        <Text style={styles.activityAlertTime}>Content Protection Policy</Text>
                      </View>
                    </View>
                  ))
                ) : (
                  <View style={{ paddingVertical: 12, alignItems: 'center' }}>
                    <Icon name="check-circle" color={colors.greenSuccess} size={24} />
                    <Text style={{ color: colors.textMuted, fontSize: 13, marginTop: 6 }}>
                      Zero blocked policy violations today. Device activity is safe.
                    </Text>
                  </View>
                )}
              </View>
            </View>
          </View>
        )}

        {activeTab === 'Alerts' && (
          <View style={{ width: '100%' }}>
            <View style={styles.alertsCard}>
              <Text style={styles.alertsCardTitle}>Notification Preferences</Text>
              <Text style={styles.alertsCardSub}>
                Receive alerts when your child visits restricted sites or leaves the safe zone.
              </Text>

              {/* Email Alerts Section */}
              <View style={styles.alertOptionSection}>
                <View style={styles.alertOptionHeader}>
                  <View style={styles.alertIconRow}>
                    <Icon name="email" color={colors.cyanAccent} size={22} />
                    <Text style={styles.alertOptionTitle}>Email Alerts</Text>
                  </View>
                  <Switch
                    value={emailAlertsEnabled}
                    onValueChange={setEmailAlertsEnabled}
                    trackColor={{ true: colors.greenSuccess }}
                  />
                </View>
                <Text style={styles.alertOptionSub}>
                  Send notifications to your registered email
                </Text>
                <TextInput
                  style={styles.alertsInput}
                  placeholder="Enter alert email"
                  placeholderTextColor={colors.textMuted}
                  value={demoEmail}
                  onChangeText={setDemoEmail}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />
              </View>

              <View style={styles.alertSectionDivider} />

              {/* SMS / Phone Alerts Section */}
              <View style={styles.alertOptionSection}>
                <View style={styles.alertOptionHeader}>
                  <View style={styles.alertIconRow}>
                    <Icon name="phone" color={colors.purpleAccent} size={22} />
                    <Text style={styles.alertOptionTitle}>SMS / Phone Alerts</Text>
                  </View>
                  <Switch
                    value={smsAlertsEnabled}
                    onValueChange={setSmsAlertsEnabled}
                    trackColor={{ true: colors.greenSuccess }}
                  />
                </View>
                <Text style={styles.alertOptionSub}>
                  Send text messages to your phone number
                </Text>
                <TextInput
                  style={styles.alertsInput}
                  placeholder="Enter alert number"
                  placeholderTextColor={colors.textMuted}
                  value={demoPhone}
                  onChangeText={setDemoPhone}
                  keyboardType="phone-pad"
                />
              </View>

              <TouchableOpacity
                style={[styles.primaryBtn, { marginTop: 20, backgroundColor: colors.purpleAccent }]}
                onPress={async () => {
                  await updateSosPreferences(emailAlertsEnabled, demoEmail, smsAlertsEnabled, demoPhone);
                  await Storage.setUserProfile({
                    name: 'Parent Admin',
                    email: demoEmail,
                    phone: demoPhone,
                  });
                  if (Platform.OS === 'android') {
                    ToastAndroid.show('Authentication & Notification preferences saved to DB!', ToastAndroid.SHORT);
                  } else {
                    Alert.alert('Saved', 'Authentication & Notification preferences updated in DB successfully.');
                  }
                }}
              >
                <Text style={styles.primaryBtnText}>Save Authentication & Alert Settings</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {activeTab === 'SOS' && (
          <View style={styles.sosSimulationView}>
            <Icon name="warning" color={colors.redDanger} size={48} />
            <Text style={styles.sosPrompt}>Simulate a panic alarm event from the child device.</Text>
            <TouchableOpacity
              style={[styles.primaryBtn, { backgroundColor: colors.redDanger }]}
              onPress={() => {
                setSosTriggeredBy(activeChild.name);
                triggerSOS(13.0827, 80.2707, 'Simulated SOS panic alert triggered from Child Device');
                setActiveTab('Overview');
              }}
            >
              <Text style={styles.primaryBtnText}>Trigger Simulated SOS</Text>
            </TouchableOpacity>

            {renderNotificationSettings('Emergency SOS', notifySosPhone, setNotifySosPhone, notifySosEmail, setNotifySosEmail)}
          </View>
        )}

        {activeTab === 'Link' && (
          <View style={styles.linkingView}>
            {/* 1. LINK CHILD DEVICE CARD */}
            <View style={styles.linkCardBoxContainer}>
              <Text style={styles.qrCardTitleLeft}>Link Child Device</Text>
              <Text style={styles.linkingInstructionsLeft}>
                Enter the 6-digit pairing code on the child device to establish a secure connection.
              </Text>

              <View style={styles.codeRefreshRow}>
                <View style={styles.codeDashedContainer}>
                  <Text style={styles.linkingCodeSpacedText}>
                    {(pairingCode || '735-456').split('').join(' ')}
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.refreshButtonPill}
                  onPress={refreshPairingCode}
                  activeOpacity={0.7}
                >
                  <Icon name="refresh" color={colors.text} size={14} />
                  <Text style={styles.refreshBtnPillText}>Refresh</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.statusBadgeYellow}>
                <Text style={styles.statusBadgeYellowText}>⏳ Waiting for connection...</Text>
              </View>

              <TouchableOpacity
                style={[styles.primaryBtn, { marginTop: 16, backgroundColor: '#6366f1' }]}
                onPress={() => {
                  Alert.alert('Device Linked!', 'Child device paired successfully.');
                  setActiveTab('Overview');
                }}
              >
                <Text style={styles.primaryBtnText}>Confirm Child Device Linked</Text>
              </TouchableOpacity>
            </View>

            {/* 2. UNLINK CHILD DEVICE CARD */}
            <View style={styles.unlinkCardContainer}>
              <View style={styles.unlinkHeaderRow}>
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <Icon name="link-off" color="#991b1b" size={18} />
                  <Text style={styles.unlinkTitleText}>Unlink Child Device</Text>
                </View>
                <Icon name="warning" color="#d97706" size={20} />
              </View>

              <Text style={styles.unlinkDescText}>
                Generate a temporary code to unlink this device. The code will expire in <Text style={{ fontWeight: 'bold' }}>5 minutes</Text>.
              </Text>

              <View style={styles.unlinkCodeRow}>
                <View style={styles.unlinkCodeBox}>
                  <Text style={styles.unlinkCodeDigits}>
                    {unlinkCode.split('').join(' ')}
                  </Text>
                </View>

                <TouchableOpacity
                  style={styles.copyBtn}
                  onPress={() => {
                    setUnlinkCopied(true);
                    setTimeout(() => setUnlinkCopied(false), 2000);
                  }}
                  activeOpacity={0.7}
                >
                  <Icon name={unlinkCopied ? "check" : "content-copy"} color={unlinkCopied ? "#059669" : "#4b5563"} size={14} />
                  <Text style={[styles.copyBtnText, unlinkCopied && { color: "#059669" }]}>
                    {unlinkCopied ? 'Copied' : 'Copy'}
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.unlinkSubActionsRow}>
                <View style={styles.expiresPill}>
                  <Icon name="schedule" color="#b91c1c" size={12} />
                  <Text style={styles.expiresPillText}>
                    {unlinkSeconds > 0 ? `Expires in ${formatTimer(unlinkSeconds)}` : 'Code Expired'}
                  </Text>
                </View>

                <TouchableOpacity
                  onPress={generateUnlinkCode}
                  style={{ flexDirection: 'row', alignItems: 'center' }}
                  activeOpacity={0.7}
                >
                  <Icon name="refresh" color="#6366f1" size={14} />
                  <Text style={styles.generateNewCodeText}>Generate New Code</Text>
                </TouchableOpacity>
              </View>

              <TouchableOpacity
                style={styles.confirmUnlinkRedBtn}
                onPress={async () => {
                  if (Platform.OS === 'web') {
                    const ok = typeof (globalThis as any).confirm === 'function'
                      ? (globalThis as any).confirm(`Are you sure you want to unlink ${activeChild?.name || 'this child device'}?`)
                      : true;
                    if (ok && activeChild?.id) {
                      await unlinkChildDevice(activeChild.id);
                      Alert.alert('Device Unlinked', 'The child device has been unlinked successfully.');
                    }
                  } else {
                    Alert.alert(
                      'Confirm Unlink',
                      `Are you sure you want to unlink ${activeChild?.name || 'this child device'}?`,
                      [
                        { text: 'Cancel', style: 'cancel' },
                        {
                          text: 'Unlink Device',
                          style: 'destructive',
                          onPress: async () => {
                            if (activeChild?.id) {
                              await unlinkChildDevice(activeChild.id);
                              Alert.alert('Device Unlinked', 'The child device has been unlinked successfully.');
                            }
                          }
                        }
                      ]
                    );
                  }
                }}
                activeOpacity={0.85}
              >
                <Icon name="warning" color="#ffffff" size={16} />
                <Text style={styles.confirmUnlinkRedBtnText}>Confirm Unlink Device</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </ScrollView>
        </>
      )}
      </View>
    </View>
  );
};

const getStyles = (colors: any) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  contentWrapper: {
    flex: 1,
    width: '100%',
    maxWidth: 720,
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
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
  },
  headerTitleContainer: {
    marginLeft: 16,
    flex: 1,
  },
  headerTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  profilesRowWrapper: {
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  profilesScrollContent: {
    paddingHorizontal: 8,
    flexDirection: 'row',
  },
  profileCard: {
    width: 160,
    marginRight: 10,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
  },
  addProfileCard: {
    borderStyle: 'dashed',
    borderColor: colors.border,
    opacity: 0.8,
  },
  profileCardInactive: {
    borderColor: colors.border,
    opacity: 0.6,
  },
  menuDropdown: {
    position: 'absolute',
    top: 40,
    right: 0,
    backgroundColor: colors.cardBackground,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 8,
    width: 175,
    zIndex: 10000,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 5,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  menuText: {
    color: colors.text,
    fontSize: 13,
    marginLeft: 8,
    fontWeight: '500',
  },
  menuDivider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 4,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  modalContent: {
    borderRadius: 20,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
    alignItems: 'center',
    position: 'relative',
    maxWidth: 520,
    width: '100%',
    alignSelf: 'center',
  },
  modalCloseBtn: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.cardBackgroundLight,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  subHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
    marginBottom: 6,
  },
  subHeaderTag: {
    fontSize: 10,
    fontWeight: 'bold',
    color: colors.purpleAccent,
    letterSpacing: 1,
    marginLeft: 6,
  },
  subMainTitle: {
    fontSize: 18,
    fontWeight: '900',
    color: colors.text,
    textAlign: 'center',
    marginBottom: 6,
  },
  subDescription: {
    fontSize: 11,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 15,
    marginBottom: 20,
    paddingHorizontal: 12,
  },
  modalInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackgroundLight,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 48,
  },
  modalInput: {
    flex: 1,
    color: colors.text,
    fontSize: 14,
    marginLeft: 8,
    padding: 0,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: colors.text,
    fontWeight: 'bold',
    fontSize: 14,
  },
  profileInfo: {
    marginLeft: 10,
    flex: 1,
  },
  profileName: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
  },
  profileSub: {
    color: colors.textMuted,
    fontSize: 10,
    marginTop: 2,
  },
  tabsWrapper: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    paddingBottom: 6,
  },
  tab: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: colors.pinkAccent,
  },
  tabText: {
    fontSize: 13,
    color: colors.textMuted,
    fontWeight: '500',
  },
  tabTextActive: {
    color: colors.text,
    fontWeight: 'bold',
  },
  sosBanner: {
    backgroundColor: colors.redDanger,
    marginHorizontal: 24,
    marginTop: 12,
    borderRadius: 12,
    padding: 14,
  },
  sosBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sosBannerTexts: {
    flex: 1,
    marginLeft: 12,
  },
  sosBannerTitle: {
    color: colors.text,
    fontWeight: '900',
    fontSize: 14,
  },
  sosBannerSub: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 11,
    marginTop: 2,
  },
  dismissBadge: {
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  dismissText: {
    color: colors.text,
    fontWeight: 'bold',
    fontSize: 12,
  },
  viewContent: {
    paddingHorizontal: 24,
    paddingVertical: 16,
    alignItems: 'center',
  },
  deviceStatusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
    width: '100%',
  },
  deviceStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  deviceStatusTexts: {
    marginLeft: 10,
  },
  statusTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
  },
  statusSub: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  overviewGaugeCard: {
    width: '100%',
    borderRadius: 20,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
    alignItems: 'center',
    marginTop: 16,
  },
  gaugeHeader: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  overviewGaugeContainer: {
    position: 'relative',
    width: 150,
    height: 150,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 16,
  },
  overviewGaugeTexts: {
    position: 'absolute',
    alignItems: 'center',
  },
  usageHourText: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '900',
  },
  limitLabelText: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  remoteLockBtn: {
    flexDirection: 'row',
    width: '100%',
    height: 48,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  remoteLockBtnText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
    marginLeft: 8,
  },
  blockSectionTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 24,
    marginBottom: 12,
    alignSelf: 'flex-start',
  },
  usageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 6,
  },
  usageLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  appIconContainer: {
    width: 38,
    height: 38,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  appName: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 12,
  },
  appDuration: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '500',
  },
  settingCard: {
    width: '100%',
    borderRadius: 16,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
  },
  settingTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
  settingSub: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 4,
  },
  limitValueRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 24,
  },
  limitBoundary: {
    color: colors.textMuted,
    fontSize: 12,
  },
  limitCurrentValue: {
    color: colors.pinkAccent,
    fontSize: 20,
    fontWeight: 'bold',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    width: '100%',
  },
  sliderButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sliderButtonText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
  },
  sliderTrackBg: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.border,
    overflow: 'hidden',
  },
  sliderTrackFill: {
    height: '100%',
    backgroundColor: colors.pinkAccent,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  contactRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.03)',
    padding: 12,
    borderRadius: 8,
  },
  contactInfo: {
    flex: 1,
    marginLeft: 12,
  },
  contactLabel: {
    color: colors.textMuted,
    fontSize: 11,
  },
  contactValue: {
    color: colors.text,
    fontSize: 13,
    fontWeight: 'bold',
    marginTop: 2,
  },
  cardDivider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 16,
  },
  scheduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  scheduleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scheduleTexts: {
    marginLeft: 10,
  },
  scheduleTitle: {
    color: colors.text,
    fontSize: 13,
    fontWeight: 'bold',
  },
  scheduleTime: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  policyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 8,
    borderBottomWidth: 0.5,
    borderBottomColor: colors.border,
  },
  policyLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  policyName: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 12,
  },
  policyRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusText: {
    fontSize: 11,
    fontWeight: 'bold',
    marginRight: 10,
  },
  addUrlRow: {
    flexDirection: 'row',
    marginTop: 16,
  },
  urlInput: {
    flex: 1,
    height: 44,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.background,
    color: colors.text,
    paddingHorizontal: 12,
    fontSize: 14,
  },
  addUrlBtn: {
    width: 60,
    height: 44,
    backgroundColor: colors.cyanAccent,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  addUrlBtnText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 13,
  },
  urlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: colors.border,
  },
  urlText: {
    color: colors.text,
    fontSize: 13,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackgroundLight,
    borderRadius: 16,
    paddingHorizontal: 16,
    height: 48,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: colors.border,
  },
  searchInput: {
    flex: 1,
    color: colors.text,
    fontSize: 15,
    marginLeft: 10,
    padding: 0,
  },
  categoryCardContainer: {
    backgroundColor: colors.cardBackground,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
    marginBottom: 24,
  },
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  categoryLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  circularCheckbox: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  categoryNameText: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '500',
    marginLeft: 16,
  },
  expandedAppsContainer: {
    backgroundColor: colors.cardBackgroundLight,
    paddingLeft: 24,
    paddingRight: 16,
    paddingBottom: 8,
  },
  appPolicyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    borderBottomColor: colors.border + '33',
  },
  appPolicyLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  appIconBg: {
    width: 28,
    height: 28,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  appNameText: {
    fontSize: 14,
    marginLeft: 12,
  },
  locationRadarCard: {
    width: '100%',
    borderRadius: 16,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 16,
    alignItems: 'center',
  },
  liveAddressContainer: {
    width: '100%',
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  liveAddressLabel: {
    color: colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 6,
  },
  liveAddressText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 18,
  },
  coordsRow: {
    flexDirection: 'row',
    width: '100%',
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    alignItems: 'center',
  },
  coordsCol: {
    flex: 1,
    alignItems: 'center',
  },
  coordsDivider: {
    width: 1,
    height: 36,
    backgroundColor: colors.border,
  },
  coordsLabel: {
    color: colors.textMuted,
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  coordsValue: {
    color: colors.cyanAccent,
    fontSize: 13,
    fontWeight: 'bold',
    fontVariant: ['tabular-nums'],
  },
  radarLabel: {
    color: colors.text,
    fontSize: 13,
    fontWeight: '600',
    marginTop: 16,
  },
  reportCard: {
    width: '100%',
    borderRadius: 20,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 18,
    marginBottom: 16,
  },
  reportCardMainTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  reportCardMainTitleBold: {
    color: colors.text,
    fontSize: 15,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  reportCardSubtitle: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: -10,
    marginBottom: 20,
  },
  summaryStatsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
  },
  summaryStatCol: {
    flex: 1,
    alignItems: 'flex-start',
  },
  summaryStatLabel: {
    color: colors.textMuted,
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  summaryStatValue: {
    color: colors.text,
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 4,
  },
  barChartContainer: {
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    height: 110,
    marginTop: 10,
  },
  chartBarsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    width: '100%',
    height: 90,
  },
  chartBarCol: {
    alignItems: 'center',
    flex: 1,
  },
  chartBarFill: {
    width: 14,
    borderRadius: 7,
    minHeight: 10,
  },
  chartBarDayLabel: {
    color: colors.textMuted,
    fontSize: 10,
    marginTop: 8,
    fontWeight: 'bold',
  },
  reportHeaderTitle: {
    fontSize: 10,
    fontWeight: 'bold',
    color: colors.textMuted,
    letterSpacing: 1,
    marginBottom: 16,
  },
  reportBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  reportBarLabel: {
    width: 90,
    color: colors.text,
    fontSize: 12,
    fontWeight: '500',
  },
  reportBarBg: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
    overflow: 'hidden',
    marginHorizontal: 12,
  },
  reportBarFillLine: {
    height: '100%',
  },
  reportBarPct: {
    width: 30,
    color: colors.text,
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'right',
  },
  blockedListContainer: {
    marginTop: 4,
  },
  activityAlert: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderWidth: 0.5,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 12,
    width: '100%',
  },
  activityAlertTexts: {
    marginLeft: 12,
    flex: 1,
  },
  activityAlertText: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '500',
  },
  activityAlertTime: {
    color: colors.textMuted,
    fontSize: 10,
    marginTop: 2,
  },
  sosSimulationView: {
    alignItems: 'center',
    marginTop: 60,
    width: '100%',
  },
  sosPrompt: {
    color: '#6B6E85',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 16,
    marginBottom: 24,
    paddingHorizontal: 20,
  },
  primaryBtn: {
    width: '100%',
    height: 48,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: 'bold',
  },
  linkingView: {
    alignItems: 'center',
    marginTop: 20,
    width: '100%',
    paddingBottom: 40,
  },
  linkCardBoxContainer: {
    width: '90%',
    maxWidth: 440,
    backgroundColor: colors.cardBackground,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 24,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
  },
  qrCardTitleLeft: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  linkingInstructionsLeft: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 18,
  },
  codeRefreshRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    width: '100%',
  },
  codeDashedContainer: {
    flex: 1,
    height: 52,
    borderRadius: 12,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.border,
    backgroundColor: colors.cardBackgroundLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  linkingCodeSpacedText: {
    fontSize: 22,
    fontWeight: '900',
    color: colors.text,
    letterSpacing: 3,
  },
  refreshButtonPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackgroundLight,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    height: 52,
  },
  refreshBtnPillText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: 'bold',
    marginLeft: 6,
  },
  statusBadgeYellow: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderRadius: 8,
    paddingVertical: 6,
    paddingHorizontal: 12,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.25)',
  },
  statusBadgeYellowText: {
    color: '#d97706',
    fontSize: 12,
    fontWeight: '700',
  },
  unlinkCardContainer: {
    width: '90%',
    maxWidth: 440,
    backgroundColor: 'rgba(239, 68, 68, 0.04)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
    padding: 24,
    shadowColor: '#ef4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  unlinkHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  unlinkTitleText: {
    color: '#991b1b',
    fontSize: 17,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  unlinkDescText: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: 18,
  },
  unlinkCodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  unlinkCodeBox: {
    flex: 1,
    height: 54,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(239, 68, 68, 0.35)',
    backgroundColor: colors.cardBackground,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  unlinkCodeDigits: {
    fontSize: 24,
    fontWeight: '900',
    color: '#991b1b',
    letterSpacing: 3,
  },
  copyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 16,
    height: 54,
  },
  copyBtnText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: 'bold',
    marginLeft: 6,
  },
  unlinkSubActionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  expiresPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderRadius: 12,
    paddingVertical: 4,
    paddingHorizontal: 10,
  },
  expiresPillText: {
    color: '#b91c1c',
    fontSize: 11,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  generateNewCodeText: {
    color: '#6366f1',
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  confirmUnlinkRedBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#dc2626',
    borderRadius: 12,
    height: 50,
    width: '100%',
  },
  confirmUnlinkRedBtnText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  linkingInstructions: {
    color: '#6B6E85',
    fontSize: 11,
    textAlign: 'center',
    lineHeight: 16,
    paddingHorizontal: 16,
    marginTop: 8,
  },
  qrCard: {
    width: '90%',
    maxWidth: 360,
    backgroundColor: colors.cardBackground,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 24,
    alignItems: 'center',
    shadowColor: colors.cyanAccent,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 8,
  },
  qrCardTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 20,
    letterSpacing: 0.5,
  },
  qrCodeWrapper: {
    padding: 16,
    backgroundColor: colors.cardBackgroundLight,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    position: 'relative',
    overflow: 'hidden',
    marginBottom: 20,
  },
  scanLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: colors.cyanAccent,
    opacity: 0.4,
    top: '50%',
  },
  linkCard: {
    width: '100%',
    borderRadius: 20,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
  },
  codeLabel: {
    color: colors.purpleAccent,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    textAlign: 'center',
    marginBottom: 6,
  },
  codeText: {
    color: colors.cyanAccent,
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: 4,
    textAlign: 'center',
    marginVertical: 4,
  },
  codeSub: {
    color: colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 4,
  },
  codeContainer: {
    alignItems: 'center',
    backgroundColor: colors.cardBackgroundLight,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 16,
    paddingVertical: 16,
    marginBottom: 12,
    width: '100%',
  },
  linkingCodeText: {
    fontSize: 22,
    fontWeight: '900',
    color: colors.cyanAccent,
    letterSpacing: 2,
  },
  refreshButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(6, 182, 212, 0.1)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(6, 182, 212, 0.2)',
  },
  refreshBtnText: {
    color: colors.cyanAccent,
    fontSize: 11,
    fontWeight: 'bold',
    marginLeft: 6,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.08)',
    borderRadius: 12,
    paddingVertical: 6,
    paddingHorizontal: 12,
    marginTop: 16,
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.2)',
  },
  pulseDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.orangeWarning,
    marginRight: 8,
  },
  linkStatusText: {
    color: colors.orangeWarning,
    fontSize: 11,
    fontWeight: '600',
  },
  radiusInputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    marginBottom: 8,
  },
  radiusLabelText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    marginRight: 8,
  },
  radiusInputContainer: {
    width: 80,
    height: 38,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  radiusInput: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
    width: '100%',
    height: '100%',
    padding: 0,
    textAlign: 'center',
  },
  radiusUnitText: {
    color: colors.text,
    fontSize: 14,
    fontWeight: 'bold',
  },
  alertsCard: {
    width: '100%',
    borderRadius: 16,
    backgroundColor: colors.cardBackground,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 20,
  },
  alertsCardTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
  alertsCardSub: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 4,
    marginBottom: 20,
    lineHeight: 16,
  },
  alertOptionSection: {
    width: '100%',
    marginVertical: 4,
  },
  alertOptionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
  alertIconRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  alertOptionTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: 'bold',
    marginLeft: 12,
  },
  alertOptionSub: {
    color: colors.textMuted,
    fontSize: 12,
    marginLeft: 34,
    marginTop: 2,
    marginBottom: 10,
  },
  alertsInput: {
    height: 44,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    color: colors.text,
    paddingHorizontal: 12,
    fontSize: 14,
    marginLeft: 34,
    marginTop: 4,
  },
  alertSectionDivider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: 16,
  },
  childMenuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  childMenuName: {
    color: colors.text,
    fontSize: 12,
    fontWeight: 'bold',
    flex: 1,
    marginRight: 8,
  },
  childSignOutBtn: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  childSignOutBtnText: {
    color: colors.redDanger,
    fontSize: 10,
    fontWeight: 'bold',
  },
  childUnlinkedText: {
    color: colors.textMuted,
    fontSize: 10,
  },
  cardSignOutBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 6,
  },
  logoutAlertCard: {
    width: '90%',
    maxWidth: 400,
    backgroundColor: colors.cardBackground,
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.3)',
    shadowColor: '#ef4444',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 10,
  },
  logoutAlertIconBg: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  logoutAlertTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
    textAlign: 'center',
  },
  logoutAlertMessage: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  logoutAlertBtn: {
    backgroundColor: '#ef4444',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 24,
    width: '100%',
    alignItems: 'center',
  },
  logoutAlertBtnText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});
