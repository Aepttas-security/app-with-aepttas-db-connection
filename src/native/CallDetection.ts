import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

const { CallDetectionModule } = NativeModules;

export interface CallState {
  state: number;
  stateName: 'IDLE' | 'RINGING' | 'OFFHOOK' | 'UNKNOWN';
  isActive: boolean;
}

export interface CallEvent {
  state: string;
  stateName?: string;
  phoneNumber: string;
  type?: 'INCOMING' | 'OUTGOING';
  isInContacts?: boolean;
  contactName?: string;
  isSpam?: boolean;
}

export interface CallerInfo {
  phoneNumber: string;
  callerName: string;
  isInContacts: boolean;
  isSpam: boolean;
  riskScore?: number;
  address?: string;
}

class CallDetectionManager {
  private eventEmitter: NativeEventEmitter | null = null;
  private isListening: boolean = false;
  private listeners: Array<(event: CallEvent) => void> = [];
  private contactListeners: Array<(info: CallerInfo) => void> = [];

  constructor() {
    if (Platform.OS === 'android' && CallDetectionModule) {
      this.eventEmitter = new NativeEventEmitter(CallDetectionModule);
      this.setupEventListeners();
    }
  }

  private setupEventListeners() {
    if (!this.eventEmitter) return;

    // Main call state listener
    this.eventEmitter.addListener('onCallStateChanged', (event: CallEvent) => {
      console.log('📞 Call event received:', event);
      this.listeners.forEach(callback => callback(event));
    });

    // Call detected listener (for live call analysis)
    this.eventEmitter.addListener('onCallDetected', (event: CallEvent) => {
      console.log('🔍 Call detected:', event);
      // Forward to contact listeners with enriched data
      const callerInfo: CallerInfo = {
        phoneNumber: event.phoneNumber || '',
        callerName: event.contactName || 'Unknown Caller',
        isInContacts: event.isInContacts || false,
        isSpam: event.isSpam || false,
      };
      this.contactListeners.forEach(callback => callback(callerInfo));
    });
  }

  async requestPermissions(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    try {
      await CallDetectionModule.requestPermissions();
      return true;
    } catch (error) {
      console.error('❌ Permission error:', error);
      return false;
    }
  }

  async requestContactPermission(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    try {
      const result = await CallDetectionModule.requestPermissions();
      return result === true;
    } catch (error) {
      console.error('❌ Contact permission error:', error);
      return false;
    }
  }

  async checkOverlayPermission(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    try {
      return await CallDetectionModule.checkOverlayPermission();
    } catch (error) {
      console.error('❌ Overlay permission check error:', error);
      return false;
    }
  }

  async requestOverlayPermission(): Promise<void> {
    if (Platform.OS !== 'android') return;
    try {
      await CallDetectionModule.requestOverlayPermission();
    } catch (error) {
      console.error('❌ Overlay permission request error:', error);
    }
  }

  async startDetection(): Promise<boolean> {
    if (Platform.OS !== 'android') return false;
    if (this.isListening) {
      console.log('📱 Already listening');
      return true;
    }

    try {
      const hasOverlay = await this.checkOverlayPermission();
      if (!hasOverlay) {
        console.warn('⚠️ Overlay permission not granted. Popups may not appear.');
        await this.requestOverlayPermission();
      }

      await CallDetectionModule.startCallDetection();
      this.isListening = true;
      console.log('✅ Call detection started');
      return true;
    } catch (error) {
      console.error('❌ Start detection error:', error);
      return false;
    }
  }

  async stopDetection(): Promise<boolean> {
    if (Platform.OS !== 'android') return false;
    if (!this.isListening) {
      console.log('📱 Already stopped');
      return true;
    }

    try {
      await CallDetectionModule.stopCallDetection();
      this.isListening = false;
      console.log('🛑 Call detection stopped');
      return true;
    } catch (error) {
      console.error('❌ Stop detection error:', error);
      return false;
    }
  }

  async getCallState(): Promise<CallState | null> {
    if (Platform.OS !== 'android') return null;
    try {
      return await CallDetectionModule.getCallState();
    } catch (error) {
      console.error('❌ Get call state error:', error);
      return null;
    }
  }

  async isCallActive(): Promise<boolean> {
    if (Platform.OS !== 'android') return false;
    try {
      return await CallDetectionModule.isCallActive();
    } catch (error) {
      console.error('❌ Check call active error:', error);
      return false;
    }
  }

  async simulateCall(phoneNumber: string): Promise<void> {
    if (Platform.OS !== 'android') return;
    try {
      await CallDetectionModule.simulateCall(phoneNumber);
      console.log(`📞 Simulated call from: ${phoneNumber}`);
    } catch (error) {
      console.error('❌ Simulate call error:', error);
    }
  }

  async initialize(): Promise<boolean> {
    if (Platform.OS !== 'android') return true;
    try {
      await CallDetectionModule.initialize();
      await CallDetectionModule.initializeModule();
      console.log('✅ Call detection module initialized');
      return true;
    } catch (error) {
      console.error('❌ Initialization error:', error);
      return false;
    }
  }

  addListener(callback: (event: CallEvent) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  onCallDetected(callback: (info: CallerInfo) => void): () => void {
    this.contactListeners.push(callback);
    return () => {
      this.contactListeners = this.contactListeners.filter(cb => cb !== callback);
    };
  }

  removeAllListeners(): void {
    this.listeners = [];
    this.contactListeners = [];
    if (this.eventEmitter) {
      this.eventEmitter.removeAllListeners('onCallStateChanged');
      this.eventEmitter.removeAllListeners('onCallDetected');
    }
  }

  get isActive(): boolean {
    return this.isListening;
  }

  async isNumberInContacts(phoneNumber: string): Promise<boolean> {
    return false;
  }

  async syncContacts(): Promise<{ success: boolean; message: string }> {
    if (Platform.OS !== 'android' || !CallDetectionModule?.syncContacts) {
      return { success: false, message: 'Platform not supported' };
    }
    try {
      return await CallDetectionModule.syncContacts();
    } catch (error: any) {
      console.error('❌ Sync contacts error:', error);
      return { success: false, message: error?.message || 'Failed to sync contacts' };
    }
  }

  async analyzeCaller(phoneNumber: string): Promise<{
    riskScore: number;
    riskLevel: string;
    shouldAutoBlock: boolean;
    isSpoofedOrBot: boolean;
    digitalDnaPattern: string;
    crowdsourcedReports: number;
    contextualReason: string;
    recommendedAction: string;
    isInContacts: boolean;
  } | null> {
    if (Platform.OS !== 'android' || !CallDetectionModule?.analyzeCaller) return null;
    try {
      return await CallDetectionModule.analyzeCaller(phoneNumber);
    } catch (error) {
      console.error('❌ Analyze caller error:', error);
      return null;
    }
  }

  async checkAndAutoBlock(phoneNumber: string): Promise<{
    autoBlocked: boolean;
    riskScore: number;
    riskLevel: string;
  } | null> {
    if (Platform.OS !== 'android' || !CallDetectionModule?.checkAndAutoBlock) return null;
    try {
      return await CallDetectionModule.checkAndAutoBlock(phoneNumber);
    } catch (error) {
      console.error('❌ Auto-block error:', error);
      return null;
    }
  }

  async getDeviceContacts(): Promise<Array<{ recordID: string; displayName: string; phoneNumber: string; thumbnailPath?: string }>> {
    if (Platform.OS !== 'android' || !CallDetectionModule?.getDeviceContacts) return [];
    try {
      return await CallDetectionModule.getDeviceContacts();
    } catch (e) {
      console.warn('getDeviceContacts error:', e);
      return [];
    }
  }

  async getDeviceCallLogs(limit: number = 100): Promise<Array<{
    id: string;
    callerName: string;
    phoneNumber: string;
    callType: string;
    timestamp: string;
    timestampMs: number;
    duration: string;
    durationSeconds: number;
    isBlocked: boolean;
    isSpam: boolean;
    riskScore: number;
  }>> {
    if (Platform.OS !== 'android' || !CallDetectionModule?.getDeviceCallLogs) return [];
    try {
      return await CallDetectionModule.getDeviceCallLogs(limit);
    } catch (e) {
      console.warn('getDeviceCallLogs error:', e);
      return [];
    }
  }

  getAvailableMethods(): string[] {
    if (!CallDetectionModule) return [];
    return Object.keys(CallDetectionModule);
  }
}

export default new CallDetectionManager();
