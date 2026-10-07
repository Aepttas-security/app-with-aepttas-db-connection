import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
  StatusBar,
  ScrollView,
} from 'react-native';
import { useAppTheme } from '../contexts/ThemeContext';
import { Icon } from '../components/Icon';
import { getUnifiedBaseUrl } from '../config/apiConfig';

interface ErrorLog {
  id: number;
  timestamp: string;
  service: string;
  error_level: 'CRITICAL' | 'ERROR' | 'WARNING';
  message: string;
  stack_trace: string;
  rectified: boolean;
}

export const AdminLogsScreen: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const { colors } = useAppTheme();
  const styles = React.useMemo(() => getStyles(colors), [colors]);

  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'ERROR' | 'WARNING' | 'RECTIFIED'>('ALL');
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  const API_BASE = `${getUnifiedBaseUrl()}/api/admin`;

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/logs`);
      if (response.ok) {
        const json = await response.json();
        if (json.status === 'success' && json.logs) {
          setLogs(json.logs);
        }
      } else {
        throw new Error('Failed to retrieve logs.');
      }
    } catch (e) {
      console.warn('Backend logs endpoint offline or empty:', e);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleRectifyLog = async (logId: number) => {
    try {
      const response = await fetch(`${API_BASE}/logs/rectify/${logId}`, {
        method: 'POST',
      });
      const json = await response.json();
      if (response.ok && json.status === 'success') {
        Alert.alert('Success', `Log entry #${logId} successfully marked as resolved.`);
        setLogs(prev =>
          prev.map(log => (log.id === logId ? { ...log, rectified: true } : log))
        );
      } else {
        throw new Error();
      }
    } catch (e) {
      // Local fallback mapping logic
      setLogs(prev =>
        prev.map(log => (log.id === logId ? { ...log, rectified: true } : log))
      );
      Alert.alert('Local Resolve', `Offline Mode: Log #${logId} marked resolved locally.`);
    }
  };

  const getLevelBadgeStyles = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return { borderColor: '#EF4444', textColor: '#EF4444', bgColor: '#EF444415' };
      case 'ERROR':
        return { borderColor: '#F97316', textColor: '#F97316', bgColor: '#F9731615' };
      case 'WARNING':
        return { borderColor: '#EAB308', textColor: '#EAB308', bgColor: '#EAB30815' };
      default:
        return { borderColor: colors.border, textColor: colors.textMuted, bgColor: 'transparent' };
    }
  };

  const filteredLogs = logs.filter(log => {
    if (filter === 'ALL') return true;
    if (filter === 'RECTIFIED') return log.rectified;
    return log.error_level === filter && !log.rectified;
  });

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.background} />

      {/* ADMIN HEADER APP BAR */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={onBack} activeOpacity={0.7}>
          <Icon name="arrow-back" color={colors.text} size={20} />
        </TouchableOpacity>
        <View style={styles.headerTitleContainer}>
          <Text style={styles.headerTitle}>Developer Central</Text>
          <Text style={styles.headerSubtitle}>Real-time system error logs & diagnosis</Text>
        </View>
        <TouchableOpacity style={styles.refreshButton} onPress={fetchLogs} activeOpacity={0.7}>
          <Icon name="refresh" color={colors.text} size={20} />
        </TouchableOpacity>
      </View>

      {/* FILTER BUTTONS CONTAINER */}
      <View style={styles.filterContainer}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterScroll}>
          {(['ALL', 'CRITICAL', 'ERROR', 'WARNING', 'RECTIFIED'] as const).map(f => {
            const isSelected = filter === f;
            return (
              <TouchableOpacity
                key={f}
                style={[styles.filterCap, isSelected && styles.filterCapActive]}
                onPress={() => setFilter(f)}
                activeOpacity={0.8}
              >
                <Text style={[styles.filterText, isSelected && styles.filterTextActive]}>{f}</Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* LOGS LIST */}
      {loading ? (
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color={colors.purpleAccent} />
          <Text style={styles.loadingText}>Fetching system diagnostic records...</Text>
        </View>
      ) : filteredLogs.length > 0 ? (
        <FlatList
          data={filteredLogs}
          keyExtractor={item => item.id.toString()}
          contentContainerStyle={styles.listContainer}
          renderItem={({ item }) => {
            const isExpanded = expandedLogId === item.id;
            const badge = getLevelBadgeStyles(item.error_level);
            
            return (
              <View style={[styles.logCard, item.rectified && styles.rectifiedCard]}>
                {/* Header Row */}
                <TouchableOpacity
                  style={styles.cardHeader}
                  onPress={() => setExpandedLogId(isExpanded ? null : item.id)}
                  activeOpacity={0.9}
                >
                  <View style={{ flex: 1, paddingRight: 8 }}>
                    <Text style={styles.serviceText}>{item.service}</Text>
                    <Text style={styles.timestampText}>
                      {new Date(item.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })}{' '}
                      {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </Text>
                  </View>

                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    {item.rectified ? (
                      <View style={styles.resolvedBadge}>
                        <Icon name="check-circle" color="#10B981" size={14} />
                        <Text style={styles.resolvedBadgeText}>RESOLVED</Text>
                      </View>
                    ) : (
                      <View style={[styles.levelBadge, { borderColor: badge.borderColor, backgroundColor: badge.bgColor }]}>
                        <Text style={[styles.levelBadgeText, { color: badge.textColor }]}>{item.error_level}</Text>
                      </View>
                    )}
                    <View style={{ marginLeft: 8 }}>
                      <Icon name={isExpanded ? 'expand-less' : 'expand-more'} color={colors.textMuted} size={20} />
                    </View>
                  </View>
                </TouchableOpacity>

                {/* Message Body */}
                <View style={styles.cardBody}>
                  <Text style={styles.errorMessageText}>{item.message}</Text>
                </View>

                {/* Expanded Stacktrace details */}
                {isExpanded && (
                  <View style={styles.expandedContainer}>
                    <Text style={styles.expandedTitleLabel}>STACK TRACE & DIAGNOSIS</Text>
                    <View style={styles.codeBlock}>
                      <Text style={styles.codeBlockText}>{item.stack_trace}</Text>
                    </View>

                    {/* Rectify Action Row */}
                    {!item.rectified && (
                      <TouchableOpacity
                        style={styles.rectifyActionBtn}
                        onPress={() => handleRectifyLog(item.id)}
                        activeOpacity={0.8}
                      >
                        <Icon name="check" color="#ffffff" size={16} />
                        <Text style={styles.rectifyActionBtnText}>Mark as Rectified</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
              </View>
            );
          }}
        />
      ) : (
        <View style={styles.centerBox}>
          <Icon name="check-circle" color={colors.greenSuccess} size={48} />
          <Text style={styles.emptyText}>All systems operational. No unresolved error logs found.</Text>
        </View>
      )}
    </View>
  );
};

const getStyles = (colors: any) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
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
  refreshButton: {
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
    flex: 1,
    marginLeft: 12,
  },
  headerTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: 'bold',
  },
  headerSubtitle: {
    color: colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  filterContainer: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  filterScroll: {
    paddingHorizontal: 16,
  },
  filterCap: {
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: 6,
    paddingHorizontal: 14,
    marginRight: 8,
    backgroundColor: colors.cardBackground,
  },
  filterCapActive: {
    borderColor: colors.purpleAccent,
    backgroundColor: colors.purpleAccent + '15',
  },
  filterText: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: 'bold',
  },
  filterTextActive: {
    color: colors.purpleAccent,
  },
  centerBox: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  loadingText: {
    color: colors.textMuted,
    marginTop: 12,
    fontSize: 12,
  },
  emptyText: {
    color: colors.textMuted,
    marginTop: 12,
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
  },
  listContainer: {
    padding: 16,
  },
  logCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: '#111827',
    padding: 14,
    marginBottom: 12,
  },
  rectifiedCard: {
    opacity: 0.6,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  serviceText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  timestampText: {
    color: '#6b7280',
    fontSize: 10,
    marginTop: 2,
  },
  levelBadge: {
    borderWidth: 1.5,
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  levelBadgeText: {
    fontSize: 9,
    fontWeight: 'bold',
  },
  resolvedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#10B98115',
    borderWidth: 1,
    borderColor: '#10B981',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  resolvedBadgeText: {
    color: '#10B981',
    fontSize: 8,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  cardBody: {
    marginTop: 10,
  },
  errorMessageText: {
    color: '#e5e7eb',
    fontSize: 12,
    lineHeight: 16,
  },
  expandedContainer: {
    marginTop: 14,
    borderTopWidth: 1,
    borderTopColor: '#1f2937',
    paddingTop: 12,
  },
  expandedTitleLabel: {
    color: '#a78bfa',
    fontSize: 9,
    fontWeight: 'bold',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  codeBlock: {
    backgroundColor: '#030712',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  codeBlockText: {
    color: '#34d399',
    fontFamily: 'monospace',
    fontSize: 10,
    lineHeight: 14,
  },
  rectifyActionBtn: {
    flexDirection: 'row',
    height: 38,
    borderRadius: 8,
    backgroundColor: '#10B981',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 12,
  },
  rectifyActionBtnText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 6,
  },
});
