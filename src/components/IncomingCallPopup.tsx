import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Icon } from './Icon';

const { width, height } = Dimensions.get('window');

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

interface IncomingCallPopupProps {
  visible: boolean;
  callerInfo: CallerInfo | null;
  isLoading: boolean;
  onClose: () => void;
  onBlock: () => void;
  onAllow: () => void;
  onReport: () => void;
}

export const IncomingCallPopup: React.FC<IncomingCallPopupProps> = ({
  visible,
  callerInfo,
  isLoading,
  onClose,
  onBlock,
  onAllow,
  onReport,
}) => {
  const [isVisible, setIsVisible] = React.useState(false);
  const slideAnim = useRef(new Animated.Value(-height)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      setIsVisible(true);
      Animated.parallel([
        Animated.spring(slideAnim, {
          toValue: 0,
          useNativeDriver: true,
          tension: 65,
          friction: 11,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();

      // Auto close after 15 seconds
      const timer = setTimeout(() => {
        closePopup();
      }, 15000);

      return () => clearTimeout(timer);
    } else {
      closePopup();
    }
  }, [visible]);

  const closePopup = () => {
    Animated.parallel([
      Animated.timing(slideAnim, {
        toValue: -height,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setIsVisible(false);
      onClose();
    });
  };

  const getRiskColor = (score: number) => {
    if (score > 80) return '#FF0000';
    if (score > 50) return '#FF8000';
    if (score > 10) return '#FFD700';
    return '#00CC00';
  };

  const getRiskLabel = (score: number) => {
    if (score > 80) return 'âš ï¸ High Risk - Spam';
    if (score > 50) return 'âš ï¸ Medium Risk - Suspicious';
    if (score > 10) return 'â„¹ï¸ Low Risk';
    return 'âœ… Safe';
  };

  if (!isVisible) return null;

  return (
    <Modal transparent visible={isVisible} animationType="none">
      <Animated.View style={[styles.overlay, { opacity: fadeAnim }]}>
        <Animated.View style={[styles.popupContainer, { transform: [{ translateY: slideAnim }] }]}>
          {/* Close Button */}
          <TouchableOpacity style={styles.closeBtn} onPress={closePopup}>
            <Text style={styles.closeBtnText}>âœ•</Text>
          </TouchableOpacity>

          {isLoading ? (
            <View style={styles.loadingContainer}>
              <View style={styles.loadingSpinner} />
              <Text style={styles.loadingText}>Analyzing caller...</Text>
            </View>
          ) : callerInfo ? (
            <>
              {/* Header */}
              <View style={styles.header}>
                <Text style={styles.headerTitle}>
                  {callerInfo.isContact ? 'ðŸ“ž CONTACT CALLING' :
                   callerInfo.isBlocked ? 'ðŸš« BLOCKED CALLER' :
                   callerInfo.isSpam ? 'âš ï¸ SPAM DETECTED' : 'ðŸ“ž INCOMING CALL'}
                </Text>
              </View>

              {/* Caller Avatar */}
              <View style={styles.avatarContainer}>
                <Text style={styles.avatarText}>
                  {callerInfo.name ? callerInfo.name.charAt(0).toUpperCase() : '?'}
                </Text>
                {callerInfo.isContact && (
                  <View style={styles.contactBadge}>
                    <Text style={styles.contactBadgeText}>âœ“</Text>
                  </View>
                )}
              </View>

              {/* Caller Details */}
              <Text style={styles.callerName}>{callerInfo.name || 'Unknown Caller'}</Text>
              <Text style={styles.callerNumber}>{callerInfo.number}</Text>
              <Text style={styles.callerCarrier}>
                {callerInfo.carrier} â€¢ {callerInfo.location}
              </Text>

              {/* Risk Score */}
              <View style={styles.riskContainer}>
                <View style={styles.riskHeader}>
                  <Text style={styles.riskLabel}>Risk Score</Text>
                  <Text style={[styles.riskScoreText, { color: getRiskColor(callerInfo.riskScore) }]}>
                    {callerInfo.riskScore}%
                  </Text>
                </View>
                <View style={styles.riskBarContainer}>
                  <View
                    style={[
                      styles.riskBar,
                      {
                        width: `${Math.min(callerInfo.riskScore, 100)}%`,
                        backgroundColor: getRiskColor(callerInfo.riskScore),
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.riskLabelText, { color: getRiskColor(callerInfo.riskScore) }]}>
                  {getRiskLabel(callerInfo.riskScore)}
                </Text>
                {callerInfo.reportCount && callerInfo.reportCount > 0 && (
                  <Text style={styles.reportCount}>
                    Reported by {callerInfo.reportCount} users
                  </Text>
                )}
              </View>

              {/* Action Buttons */}
              <View style={styles.actionsContainer}>
                <TouchableOpacity style={[styles.actionBtn, styles.allowBtn]} onPress={onAllow}>
                  <Icon name="phone" color="#10b981" size={18} />
                  <Text style={[styles.actionBtnText, { color: '#10b981' }]}>Allow</Text>
                </TouchableOpacity>

                <TouchableOpacity style={[styles.actionBtn, styles.blockBtn]} onPress={onBlock}>
                  <Icon name="cancel" color="#fff" size={18} />
                  <Text style={[styles.actionBtnText, { color: '#fff' }]}>Block</Text>
                </TouchableOpacity>

                <TouchableOpacity style={[styles.actionBtn, styles.reportBtn]} onPress={onReport}>
                  <Icon name="warning" color="#FFD700" size={18} />
                  <Text style={[styles.actionBtnText, { color: '#FFD700' }]}>Report</Text>
                </TouchableOpacity>
              </View>
            </>
          ) : (
            <View style={styles.loadingContainer}>
              <Text style={styles.loadingText}>No caller information available</Text>
            </View>
          )}
        </Animated.View>
      </Animated.View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: 'transparent',
    zIndex: 9999,
  },
  popupContainer: {
    backgroundColor: '#0b0f19',
    marginTop: 50,
    marginHorizontal: 16,
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#1e293b',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  closeBtn: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  closeBtnText: { color: '#9ca3af', fontSize: 14, fontWeight: 'bold' },
  header: { alignItems: 'center', marginBottom: 8 },
  headerTitle: { color: '#6B6E85', fontSize: 12, fontWeight: 'bold' },
  avatarContainer: {
    alignSelf: 'center',
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#8b5cf6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
    position: 'relative',
  },
  avatarText: { color: '#fff', fontSize: 26, fontWeight: 'bold' },
  contactBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#10b981',
    justifyContent: 'center',
    alignItems: 'center',
  },
  contactBadgeText: { color: '#fff', fontSize: 12, fontWeight: 'bold' },
  callerName: { color: '#fff', fontSize: 18, fontWeight: 'bold', textAlign: 'center' },
  callerNumber: { color: '#9ca3af', fontSize: 14, textAlign: 'center', marginTop: 2 },
  callerCarrier: { color: '#6B6E85', fontSize: 12, textAlign: 'center', marginTop: 4 },
  riskContainer: { marginVertical: 10 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  riskLabel: { color: '#6B6E85', fontSize: 12 },
  riskScoreText: { fontSize: 14, fontWeight: 'bold' },
  riskBarContainer: { height: 6, backgroundColor: '#1e293b', borderRadius: 3, overflow: 'hidden', marginTop: 4 },
  riskBar: { height: '100%', borderRadius: 3 },
  riskLabelText: { fontSize: 12, fontWeight: 'bold', marginTop: 4 },
  reportCount: { color: '#6B6E85', fontSize: 11, marginTop: 4 },
  actionsContainer: { flexDirection: 'row', marginTop: 10, gap: 8 },
  actionBtn: { flex: 1, paddingVertical: 10, borderRadius: 8, alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 6 },
  allowBtn: { backgroundColor: 'rgba(16, 185, 129, 0.2)', borderWidth: 1, borderColor: '#10b981' },
  blockBtn: { backgroundColor: '#ef4444' },
  reportBtn: { backgroundColor: 'rgba(255, 215, 0, 0.2)', borderWidth: 1, borderColor: '#FFD700' },
  actionBtnText: { fontWeight: 'bold', fontSize: 12 },
  loadingContainer: { paddingVertical: 30, alignItems: 'center' },
  loadingSpinner: { width: 36, height: 36, borderRadius: 18, borderWidth: 3, borderColor: '#8b5cf6', borderTopColor: 'transparent' },
  loadingText: { color: '#6B6E85', marginTop: 10 },
});
