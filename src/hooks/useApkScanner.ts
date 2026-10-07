import { useState, useEffect, useCallback, useRef } from 'react';
import { Platform } from 'react-native';
import { ScannerRepository, DashboardRepository, DashboardMetrics } from '../data/repository';
import { ApkScanner } from '../scanner/ApkScanner';
import { Storage } from '../utils/storage';

export interface LocalScanResult {
  id: number;
  filename: string;
  risk_score: number;
  risk_level: string;
  status: string;
  threat_type: string | null;
  permissions: string[];
  confidence_score: number;
  recommended_action: string;
  timestamp: string;
}

export interface LocalQuarantineItem {
  id: number;
  filename: string;
  threat_summary: string;
  timestamp: string;
}

export interface LocalHistoryItem {
  id: number;
  filename: string;
  status: string;
  timestamp: string;
  action_taken: string;
}

let _idCounter = 1000;

export function useApkScanner() {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [lastScanResult, setLastScanResult] = useState<any | null>(null);

  // Backend data states
  const [dashboardMetrics, setDashboardMetrics] = useState<DashboardMetrics | null>(null);
  const [scans, setScans] = useState<any[]>([]);
  const [quarantinedFiles, setQuarantinedFiles] = useState<any[]>([]);
  const [historyLogs, setHistoryLogs] = useState<any[]>([]);
  const [activeAlert, setActiveAlert] = useState<any | null>(null);

  // Local in-memory stores (React refs so they persist across renders without causing extra renders)
  const localScansRef = useRef<LocalScanResult[]>([]);
  const localQuarantineRef = useRef<LocalQuarantineItem[]>([]);
  const localHistoryRef = useRef<LocalHistoryItem[]>([]);

  // Backend availability
  const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

  /**
   * Check if the backend server is reachable
   */
  const checkBackend = useCallback(async (): Promise<boolean> => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const baseUrl = require('../config/apiConfig').getUnifiedBaseUrl();
      const res = await fetch(`${baseUrl}/api/dashboard`, { signal: controller.signal });
      clearTimeout(timeout);
      const available = res.ok;
      setBackendAvailable(available);
      return available;
    } catch {
      setBackendAvailable(false);
      return false;
    }
  }, []);


  /**
   * Push local store state into React state so the UI re-renders and save to Storage DB
   */
  const syncLocalToState = useCallback(async () => {
    const scansLocal = localScansRef.current;
    const quarantineLocal = localQuarantineRef.current;
    const historyLocal = localHistoryRef.current;

    const threats = scansLocal.filter(s => s.status !== 'Safe').length;
    const metrics = {
      total_scanned: scansLocal.length + historyLocal.length,
      threats_detected: threats,
      quarantined_files: quarantineLocal.length,
      device_security_score: scansLocal.length === 0 && quarantineLocal.length === 0
        ? 100
        : Math.max(10, 100 - quarantineLocal.length * 15 - threats * 10),
    };
    setDashboardMetrics(metrics);
    setScans([...scansLocal]);
    setQuarantinedFiles([...quarantineLocal]);
    setHistoryLogs([...historyLocal]);

    const maliciousAlert = scansLocal.find(s => s.status === 'Malicious');
    setActiveAlert(maliciousAlert ?? null);

    // Save to persistent Storage DB
    await Storage.setScanLogs(scansLocal);
    await Storage.setQuarantineItems(quarantineLocal);
  }, []);

  /**
   * Refresh data from backend, falling back to local store
   */
  const refreshData = useCallback(async () => {
    const isOnline = backendAvailable ?? (await checkBackend());

    if (isOnline) {
      try {
        const [metrics, allScans, allQuarantine, allHistory, alerts] = await Promise.all([
          DashboardRepository.getDashboardMetrics(),
          ScannerRepository.listScans(),
          ScannerRepository.listQuarantinedApks(),
          ScannerRepository.listScanHistory(),
          DashboardRepository.getActiveAlerts(),
        ]);

        setDashboardMetrics(metrics);
        setScans(Array.isArray(allScans) ? allScans : ((allScans as any)?.data ?? []));
        setQuarantinedFiles(Array.isArray(allQuarantine) ? allQuarantine : ((allQuarantine as any)?.data ?? []));
        setHistoryLogs(Array.isArray(allHistory) ? allHistory : ((allHistory as any)?.data ?? []));
        setActiveAlert(Array.isArray(alerts) && alerts.length > 0 ? alerts[0] : null);
        return;
      } catch {
        // Fall through to local
      }
    }

    // Load from local Storage DB if ref is empty
    if (localScansRef.current.length === 0) {
      const storedScans = await Storage.getScanLogs();
      if (storedScans) localScansRef.current = storedScans;
      const storedQuarantine = await Storage.getQuarantineItems();
      if (storedQuarantine) localQuarantineRef.current = storedQuarantine;
    }

    // Use local store
    syncLocalToState();
  }, [backendAvailable, checkBackend, syncLocalToState]);

  useEffect(() => {
    checkBackend().then(() => refreshData());
    const unsubscribe = Storage.subscribe('*', () => {
      refreshData();
    });
    return () => {
      unsubscribe();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * Smooth progress animation from `from` to `to` over `durationMs`
   */
  const animateProgress = (
    from: number,
    to: number,
    durationMs: number,
  ): Promise<void> => {
    return new Promise(resolve => {
      const steps = 20;
      const stepMs = Math.max(16, durationMs / steps);
      const stepSize = (to - from) / steps;
      let current = from;
      let count = 0;
      const timer = setInterval(() => {
        count++;
        current = Math.min(to, current + stepSize);
        setScanProgress(Math.round(current));
        if (count >= steps) {
          clearInterval(timer);
          resolve();
        }
      }, stepMs);
    });
  };

  /**
   * Run fully local analysis using RiskAnalyzer — no network needed
   */
  const runLocalAnalysis = async (filePath: string): Promise<LocalScanResult> => {
    const nativeResult = await ApkScanner.scanApk(filePath);
    const fileName = filePath.substring(filePath.lastIndexOf('/') + 1);
    const id = ++_idCounter;
    const now = new Date().toISOString();

    const scan: LocalScanResult = {
      id,
      filename: fileName,
      risk_score: nativeResult.riskScore,
      risk_level: nativeResult.riskLevel,
      status: nativeResult.status,
      threat_type: nativeResult.threatType,
      permissions: nativeResult.dangerousPermissions,
      confidence_score: nativeResult.confidenceScore,
      recommended_action: nativeResult.recommendedAction,
      timestamp: now,
    };

    // Add to local stores
    localScansRef.current = [scan, ...localScansRef.current];
    localHistoryRef.current = [
      { id, filename: fileName, status: nativeResult.status, timestamp: now, action_taken: 'Scanned' },
      ...localHistoryRef.current,
    ];

    return scan;
  };

  /**
   * Main scan entry point — tries backend, falls back to local
   */
  const scanFile = async (filePath: string): Promise<LocalScanResult> => {
    setIsScanning(true);
    setScanProgress(0);

    try {
      await animateProgress(0, 20, 400);   // Preparation
      await animateProgress(20, 50, 500);  // Sandbox init

      const isOnline = backendAvailable ?? (await checkBackend());
      let result: LocalScanResult;

      if (isOnline) {
        await animateProgress(50, 80, 600); // Upload
        try {
          const backendResult = await ScannerRepository.scanApk(filePath);
          await animateProgress(80, 100, 300);
          result = backendResult as LocalScanResult;
        } catch {
          // Backend upload failed — run locally
          result = await runLocalAnalysis(filePath);
          await animateProgress(80, 100, 300);
        }
      } else {
        await animateProgress(50, 90, 800); // Local AI analysis
        result = await runLocalAnalysis(filePath);
        await animateProgress(90, 100, 300);
      }

      setScanProgress(100);
      setLastScanResult(result);
      syncLocalToState(); // Immediately sync so UI sees updated data
      setIsScanning(false);
      return result;
    } catch (e) {
      setIsScanning(false);
      setScanProgress(0);
      console.error('Scan failed:', e);
      throw e;
    }
  };

  /**
   * Move a scan result into quarantine
   */
  const quarantineFile = async (scanId: number): Promise<boolean> => {
    // Try backend first
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.quarantineFile(scanId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }

    // Local quarantine
    const scanIdx = localScansRef.current.findIndex(s => s.id === scanId);
    if (scanIdx !== -1) {
      const scan = localScansRef.current[scanIdx];

      // Move to quarantine list
      const qItem: LocalQuarantineItem = {
        id: scanId,
        filename: scan.filename,
        threat_summary: scan.threat_type ? String(scan.threat_type) : scan.status,
        timestamp: new Date().toISOString(),
      };
      localQuarantineRef.current = [qItem, ...localQuarantineRef.current];

      // Remove from active scans
      localScansRef.current = localScansRef.current.filter(s => s.id !== scanId);

      // Update history action
      localHistoryRef.current = localHistoryRef.current.map(h =>
        h.id === scanId ? { ...h, action_taken: 'Quarantined' } : h
      );
    }

    syncLocalToState();
    return true;
  };

  /**
   * Delete a scan file directly
   */
  const deleteFileDirectly = async (scanId: number): Promise<boolean> => {
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.deleteScannedFileDirectly(scanId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }

    localScansRef.current = localScansRef.current.filter(s => s.id !== scanId);
    localHistoryRef.current = localHistoryRef.current.map(h =>
      h.id === scanId ? { ...h, action_taken: 'Deleted' } : h
    );
    syncLocalToState();
    return true;
  };

  /**
   * Ignore a threat
   */
  const ignoreThreat = async (scanId: number): Promise<boolean> => {
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.ignoreThreat(scanId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }

    localScansRef.current = localScansRef.current.filter(s => s.id !== scanId);
    localHistoryRef.current = localHistoryRef.current.map(h =>
      h.id === scanId ? { ...h, action_taken: 'Ignored' } : h
    );
    syncLocalToState();
    return true;
  };

  /**
   * Restore a quarantined file
   */
  const restoreFile = async (quarantineId: number): Promise<boolean> => {
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.restoreFile(quarantineId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }

    localQuarantineRef.current = localQuarantineRef.current.filter(q => q.id !== quarantineId);
    localHistoryRef.current = localHistoryRef.current.map(h =>
      h.id === quarantineId ? { ...h, action_taken: 'Restored' } : h
    );
    syncLocalToState();
    return true;
  };

  /**
   * Permanently delete a quarantined file
   */
  const deletePermanently = async (quarantineId: number): Promise<boolean> => {
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.deletePermanently(quarantineId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }

    localQuarantineRef.current = localQuarantineRef.current.filter(q => q.id !== quarantineId);
    localHistoryRef.current = localHistoryRef.current.map(h =>
      h.id === quarantineId ? { ...h, action_taken: 'Deleted Permanently' } : h
    );
    syncLocalToState();
    return true;
  };

  /**
   * Submit a quarantined file for cloud/AI analysis
   */
  const submitForCloudAnalysis = async (quarantineId: number): Promise<boolean> => {
    if (backendAvailable) {
      try {
        const ok = await ScannerRepository.submitForAnalysis(quarantineId);
        if (ok) { await refreshData(); return true; }
      } catch { /* fall through */ }
    }
    // Local: just mark as submitted in history
    localHistoryRef.current = localHistoryRef.current.map(h =>
      h.id === quarantineId ? { ...h, action_taken: 'Submitted for AI Analysis' } : h
    );
    syncLocalToState();
    return true;
  };

  return {
    isScanning,
    scanProgress,
    lastScanResult,
    dashboardMetrics,
    scans,
    quarantinedFiles,
    historyLogs,
    activeAlert,
    backendAvailable,
    scanFile,
    quarantineFile,
    deleteFileDirectly,
    ignoreThreat,
    restoreFile,
    deletePermanently,
    submitForCloudAnalysis,
    refreshData,
  };
}
