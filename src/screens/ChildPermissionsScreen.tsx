import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  Switch,
  TouchableOpacity,
  StatusBar,
  ScrollView,
} from 'react-native';
import { useAppTheme } from '../contexts/ThemeContext';
import { Icon } from '../components/Icon';
import { Storage } from '../utils/storage';
import { ParentalRepository } from '../data/parentalRepository';
import { ChildDaemon } from '../services/childDaemon';

interface ChildPermissionsScreenProps {
  onBack: () => void;
  onConfirmPermissions: () => void;
}

export const ChildPermissionsScreen: React.FC<ChildPermissionsScreenProps> = ({
  onBack,
  onConfirmPermissions,
}) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [gpsTracking, setGpsTracking] = useState(false);
  const [usageLogs, setUsageLogs] = useState(false);
  const [proxyFilters, setProxyFilters] = useState(false);

  const allPermissionsGranted = gpsTracking && usageLogs && proxyFilters;

  const handleConfirm = async () => {
    if (!allPermissionsGranted) return;
    try {
      const childId = (await Storage.getChildId()) || '1';
      await ParentalRepository.permissionsSync(childId);
      await Storage.setAssignedRole('CHILD');
      ChildDaemon.startDaemon();
    } catch {
      await Storage.setAssignedRole('CHILD');
    }
    onConfirmPermissions();
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBack}>
          <Icon name="arrow-back" color={colors.text} size={20} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>System Permissions Shield</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>System Integration Compliance</Text>
        <Text style={styles.subtitle}>
          Grant hardware access permissions to allow parent monitoring and protection services.
        </Text>

        {/* Permission Gate 1: Background GPS Tracking */}
        <View style={styles.permissionCard}>
          <View style={styles.cardLeft}>
            <View style={styles.iconCircle}>
              <Icon name="location-on" color="#E50914" size={22} />
            </View>
            <View style={styles.textContainer}>
              <Text style={styles.permissionTitle}>Background GPS Tracking</Text>
              <Text style={styles.permissionDesc}>
                Real-time geolocation telemetry (ACCESS_BACKGROUND_LOCATION) and geofence alerts.
              </Text>
            </View>
          </View>
          <Switch
            value={gpsTracking}
            onValueChange={setGpsTracking}
            trackColor={{ false: colors.border, true: '#E50914' }}
            thumbColor="#ffffff"
          />
        </View>

        {/* Permission Gate 2: Window Usage Logs */}
        <View style={styles.permissionCard}>
          <View style={styles.cardLeft}>
            <View style={styles.iconCircle}>
              <Icon name="assessment" color="#E50914" size={22} />
            </View>
            <View style={styles.textContainer}>
              <Text style={styles.permissionTitle}>App Usage & Window Metrics</Text>
              <Text style={styles.permissionDesc}>
                Tracks app statistics, active screen time, and enforces app lockout rules.
              </Text>
            </View>
          </View>
          <Switch
            value={usageLogs}
            onValueChange={setUsageLogs}
            trackColor={{ false: colors.border, true: '#E50914' }}
            thumbColor="#ffffff"
          />
        </View>

        {/* Permission Gate 3: Network Proxy Filters */}
        <View style={styles.permissionCard}>
          <View style={styles.cardLeft}>
            <View style={styles.iconCircle}>
              <Icon name="security" color="#E50914" size={22} />
            </View>
            <View style={styles.textContainer}>
              <Text style={styles.permissionTitle}>Network Proxy & Content Filters</Text>
              <Text style={styles.permissionDesc}>
                Enforces web safe-search filters, blocks malicious URLs via VPN profile rules.
              </Text>
            </View>
          </View>
          <Switch
            value={proxyFilters}
            onValueChange={setProxyFilters}
            trackColor={{ false: colors.border, true: '#E50914' }}
            thumbColor="#ffffff"
          />
        </View>

        {/* Bottom Full-Width Confirm Button Block */}
        <TouchableOpacity
          style={[styles.confirmBtn, !allPermissionsGranted && { opacity: 0.45 }]}
          onPress={handleConfirm}
          disabled={!allPermissionsGranted}
        >
          <Text style={styles.confirmBtnText}>
            {allPermissionsGranted ? 'GRANT & CONFIRM PERMISSIONS' : 'TOGGLE ALL 3 PERMISSIONS TO ENFORCE'}
          </Text>
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
    title: {
      color: colors.text,
      fontSize: 22,
      fontWeight: '900',
      marginBottom: 6,
    },
    subtitle: {
      color: colors.textMuted,
      fontSize: 13,
      lineHeight: 18,
      marginBottom: 28,
    },
    permissionCard: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 16,
      padding: 18,
      marginBottom: 16,
    },
    cardLeft: {
      flexDirection: 'row',
      alignItems: 'center',
      flex: 1,
      marginRight: 12,
    },
    iconCircle: {
      width: 44,
      height: 44,
      borderRadius: 22,
      backgroundColor: 'rgba(229, 9, 20, 0.12)',
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 14,
    },
    textContainer: {
      flex: 1,
    },
    permissionTitle: {
      color: colors.text,
      fontSize: 15,
      fontWeight: '800',
    },
    permissionDesc: {
      color: colors.textMuted,
      fontSize: 11,
      marginTop: 4,
      lineHeight: 15,
    },
    confirmBtn: {
      backgroundColor: '#E50914',
      borderRadius: 14,
      height: 56,
      justifyContent: 'center',
      alignItems: 'center',
      marginTop: 32,
      shadowColor: '#E50914',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.4,
      shadowRadius: 10,
    },
    confirmBtnText: {
      color: '#ffffff',
      fontSize: 14,
      fontWeight: '900',
      letterSpacing: 1.5,
    },
  });
