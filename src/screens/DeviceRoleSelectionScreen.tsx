import React from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  StatusBar,
  ScrollView,
  Image,
} from 'react-native';
import Svg, { Circle, Path, G } from 'react-native-svg';
import { useAppTheme } from '../contexts/ThemeContext';
import { Icon } from '../components/Icon';
import { Storage } from '../utils/storage';

interface DeviceRoleSelectionScreenProps {
  onSelectParent: () => void;
  onSelectChild: () => void;
  onViewBindingCode?: () => void;
}

export const DeviceRoleSelectionScreen: React.FC<DeviceRoleSelectionScreenProps> = ({
  onSelectParent,
  onSelectChild,
  onViewBindingCode,
}) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const handleSelectParent = async () => {
    await Storage.setIsExistingUser(true);
    await Storage.setAssignedRole('PARENT');
    onSelectParent();
  };

  const handleSelectChild = async () => {
    await Storage.setIsExistingUser(true);
    await Storage.setAssignedRole('CHILD');
    onSelectChild();
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* Top Bar */}
      <View style={styles.topBar}>
        <View style={styles.topSpacer} />
        <TouchableOpacity style={styles.moreBtn}>
          <Icon name="more-horiz" color={colors.textMuted} size={24} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* App Branding Logo */}
        <View style={styles.brandContainer}>
          <Image
            source={require('../assets/app_logo.png')}
            style={styles.brandLogo}
            resizeMode="contain"
          />
          <Text style={styles.brandSubtitle}>AEPTTAS SHIELD</Text>
        </View>

        {/* Main Title */}
        <Text style={styles.title}>Whose device is this?</Text>

        {/* Card 1: Mine (Parent) */}
        <TouchableOpacity
          activeOpacity={0.85}
          style={styles.roleCard}
          onPress={handleSelectParent}
        >
          <View style={styles.avatarCircleParent}>
            {/* Parent Illustration Icon */}
            <Svg width={72} height={72} viewBox="0 0 100 100">
              <Circle cx="50" cy="50" r="45" fill="#1e1b4b" />
              <Circle cx="38" cy="42" r="16" fill="#fbbf24" />
              <Circle cx="62" cy="42" r="16" fill="#ec4899" />
              <Path d="M20 85 C25 65, 50 65, 55 85" fill="#3b82f6" />
              <Path d="M45 85 C50 62, 75 62, 80 85" fill="#10b981" />
            </Svg>
          </View>
          <View style={styles.cardHeaderRow}>
            <Text style={styles.cardTitle}>Mine</Text>
            <Icon name="chevron-right" color={colors.textMuted} size={22} />
          </View>
          <Text style={styles.cardSub}>
            I will use it to <Text style={styles.boldText}>manage</Text> my child's device
          </Text>
        </TouchableOpacity>

        {/* Card 2: My Child's */}
        <TouchableOpacity
          activeOpacity={0.85}
          style={[styles.roleCard, { marginTop: 24 }]}
          onPress={handleSelectChild}
        >
          <View style={styles.avatarCircleChild}>
            {/* Kids Illustration Icon */}
            <Svg width={72} height={72} viewBox="0 0 100 100">
              <Circle cx="50" cy="50" r="45" fill="#0f172a" />
              <Circle cx="40" cy="42" r="15" fill="#f472b6" />
              <Circle cx="60" cy="45" r="15" fill="#fb923c" />
              <Path d="M22 85 C28 68, 48 68, 54 85" fill="#8b5cf6" />
              <Path d="M46 85 C52 66, 72 66, 78 85" fill="#06b6d4" />
            </Svg>
          </View>
          <View style={styles.cardHeaderRow}>
            <Text style={styles.cardTitle}>My Child's</Text>
            <Icon name="chevron-right" color={colors.textMuted} size={22} />
          </View>
          <Text style={styles.cardSub}>
            I want to <Text style={styles.boldText}>supervise</Text> this device
          </Text>
        </TouchableOpacity>

        {/* Bottom Footer Link */}
        <View style={styles.footerLinkContainer}>
          <Text style={styles.footerText}>Already installed Aepttas Kids? </Text>
          <TouchableOpacity onPress={onViewBindingCode}>
            <Text style={styles.footerLink}>View the binding code</Text>
          </TouchableOpacity>
        </View>
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
    topBar: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingTop: 12,
      paddingBottom: 8,
    },
    topSpacer: {
      width: 24,
    },
    moreBtn: {
      padding: 4,
    },
    scrollContent: {
      paddingHorizontal: 24,
      paddingTop: 10,
      paddingBottom: 40,
      maxWidth: 480,
      width: '100%',
      alignSelf: 'center',
    },
    brandContainer: {
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 16,
    },
    brandLogo: {
      width: 72,
      height: 72,
      marginBottom: 6,
    },
    brandSubtitle: {
      fontSize: 12,
      fontWeight: '700',
      color: colors.cyanAccent || '#06b6d4',
      letterSpacing: 2,
    },
    title: {
      color: colors.text,
      fontSize: 26,
      fontWeight: '800',
      textAlign: 'center',
      marginBottom: 28,
      letterSpacing: -0.5,
    },
    roleCard: {
      backgroundColor: colors.cardBackground,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: 24,
      padding: 24,
      alignItems: 'center',
    },
    avatarCircleParent: {
      width: 88,
      height: 88,
      borderRadius: 44,
      backgroundColor: '#161622',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 14,
      borderWidth: 1,
      borderColor: 'rgba(139, 92, 246, 0.3)',
    },
    avatarCircleChild: {
      width: 88,
      height: 88,
      borderRadius: 44,
      backgroundColor: '#161622',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 14,
      borderWidth: 1,
      borderColor: 'rgba(6, 182, 212, 0.3)',
    },
    cardHeaderRow: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 6,
    },
    cardTitle: {
      color: colors.text,
      fontSize: 20,
      fontWeight: '700',
      marginRight: 4,
    },
    cardSub: {
      color: colors.textMuted,
      fontSize: 14,
      textAlign: 'center',
      lineHeight: 20,
    },
    boldText: {
      color: colors.text,
      fontWeight: '700',
    },
    footerLinkContainer: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      justifyContent: 'center',
      alignItems: 'center',
      marginTop: 56,
    },
    footerText: {
      color: colors.textMuted,
      fontSize: 13,
    },
    footerLink: {
      color: colors.purpleAccent,
      fontSize: 13,
      fontWeight: '700',
      textDecorationLine: 'underline',
    },
  });
