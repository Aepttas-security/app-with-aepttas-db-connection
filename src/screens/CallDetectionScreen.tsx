// src/screens/CallDetectionScreen.tsx

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  FlatList,
  Alert,
  ToastAndroid,
  Platform,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { useAppContext } from '../contexts/AppContext';
import api from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ============================================
// TYPES
// ============================================

interface CallHistoryItem {
  id: string;
  callerName: string;
  phoneNumber: string;
  carrier: string;
  location: string;
  riskScore: number;
  isSpam: boolean;
  isBlocked: boolean;
  callType: 'Incoming' | 'Outgoing' | 'Missed';
  duration: number;
  timestamp: string;
}

interface SpamItem {
  id: string;
  name: string;
  phoneNumber: string;
  reason: string;
  riskScore: number;
  date: string;
  isBlocked: boolean;
}

interface SavedContact {
  id: string;
  name: string;
  phoneNumber: string;
  createdAt: string;
}

const CONTACTS_STORAGE_KEY = '@shield_contacts';

interface CallDetectionScreenProps {
  onBack?: () => void;
}

const CallDetectionScreen: React.FC<CallDetectionScreenProps> = ({ onBack }) => {
  const { blockedNumbers, callHistory, refreshBlockedNumbers, refreshCallHistory } = useAppContext();
  
  const [activeTab, setActiveTab] = useState<'simulator' | 'search' | 'history' | 'spam'>('search');
  const [spamTab, setSpamTab] = useState<'blocked' | 'reports'>('blocked');
  const [spamReports, setSpamReports] = useState<any[]>([]);
  const [searchNumber, setSearchNumber] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [savedContacts, setSavedContacts] = useState<SavedContact[]>([]);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContactName, setNewContactName] = useState('');
  const [newContactNumber, setNewContactNumber] = useState('');
  const [isLoadingContacts, setIsLoadingContacts] = useState(false);

  // Load saved contacts on mount
  useEffect(() => {
    loadSavedContacts();
    if (activeTab === 'spam') {
      fetchSpamReports();
    }
  }, [activeTab]);

  const fetchSpamReports = async () => {
    try {
      const reports = await api.getSpamCalls();
      setSpamReports(reports);
    } catch (error) {
      console.error('Error fetching spam reports:', error);
    }
  };

  const loadSavedContacts = async () => {
    setIsLoadingContacts(true);
    try {
      const saved = await getSavedContacts();
      setSavedContacts(saved);
    } catch (error) {
      console.error('Error loading contacts:', error);
    } finally {
      setIsLoadingContacts(false);
    }
  };

  // Get saved contacts from AsyncStorage
  const getSavedContacts = async (): Promise<SavedContact[]> => {
    try {
      const data = await AsyncStorage.getItem(CONTACTS_STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Error getting saved contacts:', error);
      return [];
    }
  };

  // Save a new contact to AsyncStorage
  const saveContactToStorage = async (contact: { name: string; phoneNumber: string }): Promise<SavedContact> => {
    try {
      const existingContacts = await getSavedContacts();
      
      // Check if contact already exists
      const exists = existingContacts.find(c => c.phoneNumber === contact.phoneNumber);
      if (exists) {
        throw new Error('Contact already exists');
      }
      
      const newContact: SavedContact = {
        id: Date.now().toString(),
        name: contact.name,
        phoneNumber: contact.phoneNumber,
        createdAt: new Date().toISOString(),
      };
      
      const updatedContacts = [...existingContacts, newContact];
      await AsyncStorage.setItem(CONTACTS_STORAGE_KEY, JSON.stringify(updatedContacts));
      setSavedContacts(updatedContacts);
      return newContact;
    } catch (error) {
      console.error('Error saving contact:', error);
      throw error;
    }
  };

  // Find contact in saved contacts by number
  const findContactInSaved = (phoneNumber: string): SavedContact | null => {
    const cleaned = phoneNumber.replace(/\D/g, '');
    for (const contact of savedContacts) {
      const contactNumber = contact.phoneNumber.replace(/\D/g, '');
      if (contactNumber === cleaned || 
          contactNumber.endsWith(cleaned) || 
          cleaned.endsWith(contactNumber)) {
        return contact;
      }
    }
    return null;
  };

  // ============================================
  // NUMBER SEARCH - Database Search
  // ============================================

  const handleSearch = async () => {
    if (!searchNumber.trim()) {
      Alert.alert('Error', 'Please enter a phone number');
      return;
    }

    setIsSearching(true);
    setSearchResult(null);

    try {
      // 1. First check if number exists in our saved contacts
      const savedContact = findContactInSaved(searchNumber);
      
      // 2. Then search the database for the number details
      let dbResult = null;
      try {
        dbResult = await api.searchNumber(searchNumber);
        console.log('📊 Database search result:', dbResult);
      } catch (error) {
        console.log('DB search error:', error);
      }
      
      // 3. Build the result - PRIORITIZE DATABASE for name if exists
      let callerName = 'Unknown Caller';
      
      // If found in database, use that name (this is the contact directory)
      if (dbResult && dbResult.caller_name && dbResult.caller_name !== 'Unknown Caller') {
        callerName = dbResult.caller_name;
      } 
      // If not in DB but in saved contacts, use saved contact name
      else if (savedContact) {
        callerName = savedContact.name;
      }
      
      setSearchResult({
        phoneNumber: searchNumber,
        callerName: callerName,
        carrier: dbResult?.carrier || 'Unknown Carrier',
        location: dbResult?.location || 'Unknown Location',
        riskScore: dbResult?.risk_score || 50,
        isSpam: dbResult?.is_spam || false,
        isBlocked: dbResult?.is_blocked || false,
        isInSavedContacts: !!savedContact,
        isInDB: !!(dbResult && dbResult.caller_name && dbResult.caller_name !== 'Unknown Caller'),
        threatLevel: dbResult?.threat_level || 'Unknown',
        reportCount: dbResult?.report_count || 0,
        dbData: dbResult,
      });
    } catch (error) {
      console.error('Search error:', error);
      Alert.alert('Error', 'Failed to search number');
    } finally {
      setIsSearching(false);
    }
  };

  // ============================================
  // ADD NEW CONTACT - Save to local storage
  // ============================================

  const handleAddContact = async () => {
    if (!newContactName.trim() || !newContactNumber.trim()) {
      Alert.alert('Error', 'Please enter both name and number');
      return;
    }

    try {
      // Save to local AsyncStorage only
      await saveContactToStorage({
        name: newContactName.trim(),
        phoneNumber: newContactNumber.trim(),
      });

      // Also try to save to backend if available
      try {
        await api.addContact({
          name: newContactName.trim(),
          phone_number: newContactNumber.trim(),
        });
        console.log('Contact saved to backend');
      } catch (apiError) {
        console.log('Backend save error (non-critical):', apiError);
        // Continue - this is just a backup
      }

      ToastAndroid.show('Contact added successfully!', ToastAndroid.SHORT);
      setShowAddContact(false);
      setNewContactName('');
      setNewContactNumber('');
      
      // Reload contacts
      await loadSavedContacts();
      
      // Refresh search result if same number
      if (searchResult && searchResult.phoneNumber === newContactNumber.trim()) {
        setSearchResult({
          ...searchResult,
          isInSavedContacts: true,
        });
      }
    } catch (error) {
      console.error('Error adding contact:', error);
      Alert.alert('Error', 'Failed to add contact');
    }
  };

  // ============================================
  // GET RISK COLOR
  // ============================================

  const getRiskColor = (score: number): string => {
    if (score >= 75) return '#FF0000'; // Red - High Risk
    if (score >= 40) return '#FF8C00'; // Orange - Medium Risk  
    if (score >= 15) return '#FFD700'; // Yellow - Low Risk
    return '#00CC00'; // Green - Safe
  };

  const getRiskLabel = (score: number): string => {
    if (score >= 75) return 'High Risk';
    if (score >= 40) return 'Medium Risk';
    if (score >= 15) return 'Low Risk';
    return 'Safe';
  };

  const getRiskScoreColor = (score: number): { bg: string; text: string } => {
    if (score >= 75) return { bg: '#FF0000', text: '#FFFFFF' };
    if (score >= 40) return { bg: '#FF8C00', text: '#FFFFFF' };
    if (score >= 15) return { bg: '#FFD700', text: '#000000' };
    return { bg: '#00CC00', text: '#FFFFFF' };
  };

  // ============================================
  // RENDER: SEARCH TAB
  // ============================================

  const renderSearchTab = () => (
    <View style={styles.tabContent}>
      <Text style={styles.sectionTitle}>Reputation Directory Search</Text>
      <Text style={styles.sectionSubtitle}>Lookup the trust index of any phone number</Text>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Enter number (e.g. +91 9940530286)"
          placeholderTextColor="#6B6E85"
          value={searchNumber}
          onChangeText={setSearchNumber}
          keyboardType="phone-pad"
        />
        <TouchableOpacity 
          style={styles.searchButton} 
          onPress={handleSearch}
          disabled={isSearching}
        >
          <Text style={styles.searchButtonText}>
            {isSearching ? 'Searching...' : 'Search'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* ADD CONTACT BUTTON */}
      <TouchableOpacity 
        style={styles.addContactButton}
        onPress={() => setShowAddContact(true)}
      >
        <Text style={styles.addContactButtonText}>Add New Contact</Text>
      </TouchableOpacity>

      {/* Add Contact Modal */}
      <Modal
        transparent={true}
        visible={showAddContact}
        animationType="fade"
        onRequestClose={() => setShowAddContact(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
            <Text style={styles.modalTitle}>Add New Contact</Text>
            
            <TextInput
              style={styles.modalInput}
              placeholder="Contact Name"
              placeholderTextColor="#6B6E85"
              value={newContactName}
              onChangeText={setNewContactName}
            />
            
            <TextInput
              style={styles.modalInput}
              placeholder="Phone Number"
              placeholderTextColor="#6B6E85"
              value={newContactNumber}
              onChangeText={setNewContactNumber}
              keyboardType="phone-pad"
            />
            
            <View style={styles.modalButtons}>
              <TouchableOpacity 
                style={[styles.modalButton, styles.modalCancelButton]}
                onPress={() => {
                  setShowAddContact(false);
                  setNewContactName('');
                  setNewContactNumber('');
                }}
              >
                <Text style={styles.modalButtonText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity 
                style={[styles.modalButton, styles.modalSaveButton]}
                onPress={handleAddContact}
              >
                <Text style={styles.modalButtonText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Search Result */}
      {isLoadingContacts ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#8b5cf6" />
          <Text style={styles.loadingText}>Loading contacts...</Text>
        </View>
      ) : searchResult && (
        <View style={styles.resultContainer}>
          <View style={styles.resultHeader}>
            <Text style={styles.resultName}>{searchResult.callerName}</Text>
            {searchResult.isInDB && (
              <View style={[styles.contactBadge, { backgroundColor: '#3b82f6' }]}>
                <Text style={styles.contactBadgeText}>Database</Text>
              </View>
            )}
            {searchResult.isInSavedContacts && !searchResult.isInDB && (
              <View style={[styles.contactBadge, { backgroundColor: '#8b5cf6' }]}>
                <Text style={styles.contactBadgeText}>Saved</Text>
              </View>
            )}
          </View>
          
          <Text style={styles.resultNumber}>{searchResult.phoneNumber}</Text>
          
          <View style={styles.resultDetails}>
            <Text style={styles.resultDetail}>
              Carrier: {searchResult.carrier}
            </Text>
            <Text style={styles.resultDetail}>
              Location: {searchResult.location}
            </Text>
            {searchResult.threatLevel && searchResult.threatLevel !== 'Unknown' && (
              <Text style={styles.resultDetail}>
                Threat Level: {searchResult.threatLevel}
              </Text>
            )}
            {searchResult.reportCount > 0 && (
              <Text style={styles.resultDetail}>
                Reports: {searchResult.reportCount}
              </Text>
            )}
          </View>

          {/* Risk Score with Color */}
          <View style={styles.riskContainer}>
            <Text style={styles.riskLabel}>Risk Index:</Text>
            <View style={[
              styles.riskScoreBadge,
              { backgroundColor: getRiskScoreColor(searchResult.riskScore).bg }
            ]}>
              <Text style={[
                styles.riskScoreText,
                { color: getRiskScoreColor(searchResult.riskScore).text }
              ]}>
                {searchResult.riskScore}/100
              </Text>
            </View>
          </View>

          <Text style={[
            styles.riskStatus,
            { color: getRiskColor(searchResult.riskScore) }
          ]}>
            {getRiskLabel(searchResult.riskScore)}
          </Text>

          {searchResult.isSpam && (
            <View style={styles.spamBadge}>
              <Text style={styles.spamBadgeText}>Spam Detected</Text>
            </View>
          )}
          
          {searchResult.isBlocked && (
            <View style={[styles.spamBadge, { backgroundColor: '#FF8C00' }]}>
              <Text style={styles.spamBadgeText}>Blocked Number</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );

  // ============================================
  // RENDER: CALL HISTORY TAB - WITH COLOR CODING
  // ============================================

  const renderHistoryTab = () => {
    const historyItems: CallHistoryItem[] = callHistory.map((call: any) => ({
      id: call.id || Date.now().toString(),
      callerName: call.caller_name || 'Unknown Caller',
      phoneNumber: call.caller_number || 'Unknown',
      carrier: call.carrier || 'Unknown Carrier',
      location: call.location || 'Unknown Location',
      riskScore: call.risk_score || 0,
      isSpam: call.status === 'Spam',
      isBlocked: call.is_blocked || false,
      callType: call.call_type || 'Incoming',
      duration: call.duration || 0,
      timestamp: call.created_at || new Date().toISOString(),
    }));

    return (
      <View style={styles.tabContent}>
        <Text style={styles.sectionTitle}>CALL HISTORY LOGS</Text>
        
        <FlatList
          data={historyItems}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={[
              styles.historyItem,
              { 
                borderLeftColor: getRiskColor(item.riskScore),
                backgroundColor: item.riskScore >= 75 ? 'rgba(255,0,0,0.1)' :
                               item.riskScore >= 40 ? 'rgba(255,140,0,0.1)' :
                               item.riskScore >= 15 ? 'rgba(255,215,0,0.1)' :
                               'rgba(0,204,0,0.1)'
              }
            ]}>
              <View style={styles.historyItemLeft}>
                <Text style={styles.historyName}>{item.callerName}</Text>
                <Text style={styles.historyNumber}>{item.phoneNumber}</Text>
                <Text style={styles.historyDetails}>
                  {item.carrier} • {item.location}
                </Text>
              </View>
              
              <View style={styles.historyItemRight}>
                {/* Risk Score with Color */}
                <View style={[
                  styles.historyRiskBadge,
                  { backgroundColor: getRiskScoreColor(item.riskScore).bg }
                ]}>
                  <Text style={[
                    styles.historyRiskText,
                    { color: getRiskScoreColor(item.riskScore).text }
                  ]}>
                    {item.riskScore}
                  </Text>
                </View>
                
                <Text style={[
                  styles.historyType,
                  { 
                    color: getRiskColor(item.riskScore)
                  }
                ]}>
                  {item.isSpam ? 'Spam' :
                   item.isBlocked ? 'Blocked' :
                   item.riskScore >= 75 ? 'High Risk' :
                   item.riskScore >= 40 ? 'Medium' :
                   item.riskScore >= 15 ? 'Low' : 'Safe'}
                </Text>
                
                <TouchableOpacity style={styles.blockButton}>
                  <Text style={styles.blockButtonText}>Block</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
          contentContainerStyle={styles.historyList}
        />
      </View>
    );
  };

  // ============================================
  // RENDER: SPAM & BLOCKED TAB - WITH COLOR CODING
  // ============================================

  const renderSpamTab = () => {
    return (
      <View style={styles.tabContent}>
        <View style={styles.subTabNav}>
          <TouchableOpacity
            style={[styles.subTab, spamTab === 'blocked' && styles.activeSubTab]}
            onPress={() => setSpamTab('blocked')}
          >
            <Text style={[styles.subTabText, spamTab === 'blocked' && styles.activeSubTabText]}>Blocked Numbers</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.subTab, spamTab === 'reports' && styles.activeSubTab]}
            onPress={() => setSpamTab('reports')}
          >
            <Text style={[styles.subTabText, spamTab === 'reports' && styles.activeSubTabText]}>Community Reports</Text>
          </TouchableOpacity>
        </View>

        {spamTab === 'blocked' ? (
          <FlatList
            data={blockedNumbers}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <View style={[styles.spamItem, { borderLeftColor: '#ef4444' }]}>
                <View style={styles.spamItemLeft}>
                  <Text style={styles.spamName}>{item.caller_name || 'Unknown'}</Text>
                  <Text style={styles.spamNumber}>{item.phone_number}</Text>
                  <Text style={styles.spamReason}>Reason: {item.block_reason}</Text>
                  <Text style={styles.spamDate}>{new Date(item.block_date).toLocaleString()}</Text>
                </View>
                <TouchableOpacity style={styles.unblockButton}>
                  <Text style={styles.unblockButtonText}>Unblock</Text>
                </TouchableOpacity>
              </View>
            )}
            ListEmptyComponent={<Text style={styles.placeholderText}>No blocked numbers found.</Text>}
          />
        ) : (
          <FlatList
            data={spamReports}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <View style={[styles.spamItem, { borderLeftColor: '#f59e0b' }]}>
                <View style={styles.spamItemLeft}>
                  <Text style={styles.spamName}>{item.caller_name || 'Unknown'}</Text>
                  <Text style={styles.spamNumber}>{item.phone_number}</Text>
                  <Text style={styles.spamReason}>Community Report: {item.reason}</Text>
                  <Text style={styles.spamDate}>{new Date(item.created_at).toLocaleString()}</Text>
                </View>
                <View style={styles.reportsBadge}>
                  <Text style={styles.reportsBadgeText}>Reported</Text>
                </View>
              </View>
            )}
            ListEmptyComponent={<Text style={styles.placeholderText}>No community reports found.</Text>}
          />
        )}
      </View>
    );
  };

  // ============================================
  // RENDER: TAB NAVIGATION
  // ============================================

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Real-Time Call Shield & Spam Analysis Hub</Text>
      </View>

      {/* Tab Navigation */}
      <View style={styles.tabNav}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'simulator' && styles.activeTab]}
          onPress={() => setActiveTab('simulator')}
        >
          <Text style={[styles.tabText, activeTab === 'simulator' && styles.activeTabText]}>
            Live Call Simulator
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'search' && styles.activeTab]}
          onPress={() => setActiveTab('search')}
        >
          <Text style={[styles.tabText, activeTab === 'search' && styles.activeTabText]}>
            Number Search
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'history' && styles.activeTab]}
          onPress={() => setActiveTab('history')}
        >
          <Text style={[styles.tabText, activeTab === 'history' && styles.activeTabText]}>
            Call History
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'spam' && styles.activeTab]}
          onPress={() => setActiveTab('spam')}
        >
          <Text style={[styles.tabText, activeTab === 'spam' && styles.activeTabText]}>
            Spam & Blocked
          </Text>
        </TouchableOpacity>
      </View>

      {/* Tab Content */}
      <ScrollView style={styles.content}>
        {activeTab === 'search' && renderSearchTab()}
        {activeTab === 'history' && renderHistoryTab()}
        {activeTab === 'spam' && renderSpamTab()}
        {activeTab === 'simulator' && (
          <View style={styles.tabContent}>
            <Text style={styles.sectionTitle}>Live Call Simulator</Text>
            <Text style={styles.placeholderText}>Call simulation coming soon...</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
};

// ============================================
// STYLES
// ============================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0e17',
  },
  header: {
    padding: 16,
    backgroundColor: '#0f1923',
    borderBottomWidth: 1,
    borderBottomColor: '#1a2a3a',
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  tabNav: {
    flexDirection: 'row',
    backgroundColor: '#0f1923',
    borderBottomWidth: 1,
    borderBottomColor: '#1a2a3a',
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#8b5cf6',
  },
  tabText: {
    color: '#6B6E85',
    fontSize: 11,
    fontWeight: '500',
  },
  activeTabText: {
    color: '#ffffff',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  tabContent: {
    flex: 1,
  },
  sectionTitle: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  sectionSubtitle: {
    color: '#6B6E85',
    fontSize: 13,
    marginBottom: 16,
  },
  placeholderText: {
    color: '#6B6E85',
    fontSize: 14,
    textAlign: 'center',
    marginTop: 40,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
  loadingText: {
    color: '#6B6E85',
    marginTop: 12,
  },
  // Search styles
  searchContainer: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#0f1923',
    borderRadius: 8,
    padding: 12,
    color: '#ffffff',
    borderWidth: 1,
    borderColor: '#1a2a3a',
    marginRight: 8,
  },
  searchButton: {
    backgroundColor: '#8b5cf6',
    borderRadius: 8,
    padding: 12,
    justifyContent: 'center',
    minWidth: 80,
    alignItems: 'center',
  },
  searchButtonText: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  addContactButton: {
    backgroundColor: '#1a2a3a',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#8b5cf6',
    borderStyle: 'dashed',
  },
  addContactButtonText: {
    color: '#8b5cf6',
    fontWeight: 'bold',
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContainer: {
    backgroundColor: '#0f1923',
    borderRadius: 16,
    padding: 24,
    width: '90%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: '#1a2a3a',
  },
  modalTitle: {
    color: '#ffffff',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  modalInput: {
    backgroundColor: '#0a0e17',
    borderRadius: 8,
    padding: 12,
    color: '#ffffff',
    borderWidth: 1,
    borderColor: '#1a2a3a',
    marginBottom: 12,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  modalButton: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  modalCancelButton: {
    backgroundColor: '#1a2a3a',
  },
  modalSaveButton: {
    backgroundColor: '#8b5cf6',
  },
  modalButtonText: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  // Result styles
  resultContainer: {
    backgroundColor: '#0f1923',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#1a2a3a',
    marginTop: 12,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
    flexWrap: 'wrap',
  },
  resultName: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    flex: 1,
  },
  resultNumber: {
    color: '#6B6E85',
    fontSize: 14,
    marginBottom: 8,
  },
  resultDetails: {
    marginBottom: 8,
  },
  resultDetail: {
    color: '#6B6E85',
    fontSize: 12,
    marginBottom: 2,
  },
  riskContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 8,
  },
  riskLabel: {
    color: '#6B6E85',
    fontSize: 14,
    marginRight: 8,
  },
  riskScoreBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center',
  },
  riskScoreText: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  riskStatus: {
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 4,
  },
  contactBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
    marginLeft: 4,
  },
  contactBadgeText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  spamBadge: {
    backgroundColor: '#ef4444',
    padding: 8,
    borderRadius: 8,
    marginTop: 8,
    alignItems: 'center',
  },
  spamBadgeText: {
    color: '#ffffff',
    fontWeight: 'bold',
  },
  // History styles
  historyList: {
    paddingBottom: 80,
  },
  historyItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 4,
    backgroundColor: '#0f1923',
  },
  historyItemLeft: {
    flex: 1,
  },
  historyName: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  historyNumber: {
    color: '#6B6E85',
    fontSize: 12,
  },
  historyDetails: {
    color: '#6B6E85',
    fontSize: 10,
  },
  historyItemRight: {
    alignItems: 'flex-end',
  },
  historyRiskBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
    minWidth: 35,
    alignItems: 'center',
    marginBottom: 4,
  },
  historyRiskText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  historyType: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  blockButton: {
    backgroundColor: '#ef4444',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 4,
    marginTop: 4,
  },
  blockButtonText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  // Spam styles
  spamList: {
    paddingBottom: 80,
  },
  spamItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 4,
    backgroundColor: '#0f1923',
  },
  spamItemLeft: {
    flex: 1,
  },
  spamName: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  spamNumber: {
    color: '#6B6E85',
    fontSize: 12,
  },
  spamReason: {
    color: '#6B6E85',
    fontSize: 11,
  },
  spamDate: {
    color: '#6B6E85',
    fontSize: 10,
  },
  spamItemRight: {
    alignItems: 'flex-end',
  },
  spamRiskBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
    minWidth: 35,
    alignItems: 'center',
    marginBottom: 4,
  },
  spamRiskText: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  unblockButton: {
    backgroundColor: '#10b981',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 4,
  },
  unblockButtonText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  subTabNav: {
    flexDirection: 'row',
    marginBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a2a3a',
  },
  subTab: {
    paddingBottom: 8,
    marginRight: 24,
  },
  activeSubTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#8b5cf6',
  },
  subTabText: {
    color: '#6B6E85',
    fontSize: 13,
    fontWeight: 'bold',
  },
  activeSubTabText: {
    color: '#ffffff',
  },
  reportsBadge: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  reportsBadgeText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: 'bold',
  },
});

export { CallDetectionScreen };
export default CallDetectionScreen;