import { AppState, AppStateStatus, Platform } from 'react-native';
import { AutoScanService, ScannedFileMeta } from './AutoScanService';
import { ScannerRepository } from '../data/repository';
import { ApkScanner } from './ApkScanner';
import { getUnifiedBaseUrl } from '../config/apiConfig';

export type IdleScanStatus = 'active' | 'idle-waiting' | 'scanning' | 'paused' | 'completed' | 'failed';

export interface IdleScanState {
  status: IdleScanStatus;
  isIdle: boolean;
  scannedCount: number;
  totalCount: number;
  currentFileName: string;
  threatsFound: number;
}

type Subscriber = (state: IdleScanState) => void;

class IdleScanManagerClass {
  private state: IdleScanState = {
    status: 'active',
    isIdle: false,
    scannedCount: 0,
    totalCount: 0,
    currentFileName: '',
    threatsFound: 0,
  };

  private subscribers: Set<Subscriber> = new Set();
  private lastInteractionTime: number = Date.now();
  private idleThresholdMs: number = 10000; // 10 seconds default for demo/testing
  private checkInterval: ReturnType<typeof setInterval> | null = null;
  private scanQueue: ScannedFileMeta[] = [];
  private isScanInProgress: boolean = false;
  private shouldAbortScan: boolean = false;
  private appState: AppStateStatus = 'active';

  constructor() {
    this.handleAppStateChange = this.handleAppStateChange.bind(this);
  }

  getState(): IdleScanState {
    return { ...this.state };
  }

  subscribe(sub: Subscriber): () => void {
    this.subscribers.add(sub);
    sub(this.state);
    return () => {
      this.subscribers.delete(sub);
    };
  }

  private notify() {
    this.subscribers.forEach(sub => sub(this.state));
  }

  private updateState(updated: Partial<IdleScanState>) {
    this.state = { ...this.state, ...updated };
    this.notify();
  }

  /**
   * Reset idle timer when user interacts with screen
   */
  registerInteraction() {
    this.lastInteractionTime = Date.now();
    
    // If we were idle or scanning, transition back to active immediately
    if (this.state.isIdle) {
      console.log('[IdleScanManager] User activity detected! Pausing scan...');
      this.shouldAbortScan = true;
      this.updateState({
        isIdle: false,
        status: this.isScanInProgress ? 'paused' : 'active',
      });
    }
  }

  setIdleThreshold(seconds: number) {
    this.idleThresholdMs = seconds * 1000;
  }

  startMonitoring() {
    this.registerInteraction();
    
    // Listen for app state changes (e.g. screen off / app background)
    const subscription = AppState.addEventListener('change', this.handleAppStateChange);

    // Set up check interval every 2 seconds to check inactivity
    this.checkInterval = setInterval(() => {
      this.checkIdleState();
    }, 2000);

    return () => {
      subscription.remove();
      if (this.checkInterval) {
        clearInterval(this.checkInterval);
        this.checkInterval = null;
      }
    };
  }

  private handleAppStateChange(nextAppState: AppStateStatus) {
    console.log(`[IdleScanManager] AppState changed to: ${nextAppState}`);
    this.appState = nextAppState;

    if (nextAppState === 'active') {
      this.registerInteraction();
    } else {
      // Screen off or backgrounded immediately qualifies as idle/inactive
      this.enterIdleState();
    }
  }

  private enterIdleState() {
    if (!this.state.isIdle) {
      console.log('[IdleScanManager] Entering Idle state...');
      this.updateState({
        isIdle: true,
        status: this.isScanInProgress ? 'scanning' : 'idle-waiting',
      });
      
      // Trigger background scan loop
      this.triggerBackgroundScan();
    }
  }

  private checkIdleState() {
    const elapsed = Date.now() - this.lastInteractionTime;
    
    // If app is active and elapsed time > threshold, OR if app is in background, we are idle
    const isCurrentlyIdle = (this.appState !== 'active') || (elapsed >= this.idleThresholdMs);

    if (isCurrentlyIdle && !this.state.isIdle) {
      this.enterIdleState();
    } else if (!isCurrentlyIdle && this.state.isIdle) {
      // User active again
      console.log('[IdleScanManager] Exiting Idle state...');
      this.shouldAbortScan = true;
      this.updateState({
        isIdle: false,
        status: this.isScanInProgress ? 'paused' : 'active',
      });
    }
  }

  private async checkBackendOnline(): Promise<boolean> {
    try {
      const BASE_URL = getUnifiedBaseUrl();
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${BASE_URL}/api/health`, { signal: controller.signal });
      clearTimeout(timeout);
      return res.ok;
    } catch {
      return false;
    }
  }

  private async triggerBackgroundScan() {
    if (this.isScanInProgress) {
      // Resume existing scan queue if it was paused
      this.shouldAbortScan = false;
      this.updateState({ status: 'scanning' });
      this.runScanLoop();
      return;
    }

    console.log('[IdleScanManager] Initiating background scan of device files...');
    this.isScanInProgress = true;
    this.shouldAbortScan = false;
    this.updateState({
      status: 'scanning',
      scannedCount: 0,
      totalCount: 0,
      currentFileName: 'Collecting files...',
      threatsFound: 0,
    });

    try {
      const { files } = await AutoScanService.collectAllDeviceFiles();
      this.scanQueue = files;
      this.updateState({ totalCount: files.length });

      if (files.length === 0) {
        this.isScanInProgress = false;
        this.updateState({
          status: 'completed',
          currentFileName: 'No files to scan.',
        });
        return;
      }

      this.runScanLoop();
    } catch (err) {
      console.error('[IdleScanManager] Scan initialization failed:', err);
      this.isScanInProgress = false;
      this.updateState({ status: 'failed' });
    }
  }

  private async runScanLoop() {
    const isOnline = await this.checkBackendOnline();

    while (this.scanQueue.length > 0 && !this.shouldAbortScan && this.state.isIdle) {
      const file = this.scanQueue.shift()!;
      this.updateState({
        currentFileName: file.filename,
      });

      try {
        console.log(`[IdleScanManager] Scanning file: ${file.filename}`);
        if (isOnline) {
          // Scan via server
          const response = await ScannerRepository.scanApk(file.file_path);
          if (response && response.status !== 'Safe') {
            this.updateState({ threatsFound: this.state.threatsFound + 1 });
          }
        } else {
          // Scan locally
          const response = await ApkScanner.scanApk(file.file_path);
          if (response && response.status !== 'Safe') {
            this.updateState({ threatsFound: this.state.threatsFound + 1 });
          }
        }
      } catch (err) {
        console.warn(`[IdleScanManager] Failed to scan file ${file.filename}:`, err);
      }

      const nextScannedCount = this.state.scannedCount + 1;
      this.updateState({
        scannedCount: nextScannedCount,
      });

      // Throttle CPU by sleeping for 1000ms before scanning next file
      if (this.scanQueue.length > 0 && !this.shouldAbortScan && this.state.isIdle) {
        await this.sleep(1000);
      }
    }

    if (this.shouldAbortScan || !this.state.isIdle) {
      console.log('[IdleScanManager] Background scan paused.');
      this.updateState({ status: 'paused' });
    } else if (this.scanQueue.length === 0) {
      console.log('[IdleScanManager] Background scan completed!');
      this.isScanInProgress = false;
      this.updateState({
        status: 'completed',
        currentFileName: 'Finished scanning all files.',
      });
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

export const IdleScanManager = new IdleScanManagerClass();
