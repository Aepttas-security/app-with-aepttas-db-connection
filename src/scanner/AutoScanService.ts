import { Platform } from 'react-native';
import RNFS from 'react-native-fs';

const STATE_FILE_PATH = `${RNFS.DocumentDirectoryPath}/.last_auto_scan.json`;

export interface ScannedFileMeta {
  filename: string;
  file_path: string;
  size: number;
}

export interface AutoScanState {
  lastScanTimestamp: number;
  totalFilesScanned: number;
  threatsFound: number;
  status: 'idle' | 'scanning' | 'completed' | 'failed';
}

export const AutoScanService = {
  /**
   * Recursively walks a directory path to find files with matching extensions.
   */
  async walkDirRecursive(
    dirPath: string,
    allowedExtensions: string[] = ['.apk', '.pdf', '.docx', '.doc', '.txt', '.png', '.jpg', '.jpeg', '.webp']
  ): Promise<ScannedFileMeta[]> {
    const results: ScannedFileMeta[] = [];
    try {
      const exists = await RNFS.exists(dirPath);
      if (!exists) return [];

      const items = await RNFS.readDir(dirPath);
      for (const item of items) {
        if (item.isDirectory()) {
          // Avoid systemic hidden directories
          if (item.name.startsWith('.')) continue;
          
          const subFiles = await this.walkDirRecursive(item.path, allowedExtensions);
          results.push(...subFiles);
        } else if (item.isFile()) {
          const ext = item.name.substring(item.name.lastIndexOf('.')).toLowerCase();
          if (allowedExtensions.includes(ext)) {
            results.push({
              filename: item.name,
              file_path: item.path,
              size: item.size,
            });
          }
        }
      }
    } catch (err) {
      console.warn(`[AutoScan] Failed walking directory: ${dirPath}`, err);
    }
    return results;
  },

  /**
   * Collects all target files across multiple standard directories.
   */
  async collectAllDeviceFiles(): Promise<{ files: ScannedFileMeta[]; scanPaths: string }> {
    const files: ScannedFileMeta[] = [];
    const scanPaths: string[] = [];

    // 1. Sandbox Folder (Always accessible)
    scanPaths.push('Sandbox');
    const sandboxFiles = await this.walkDirRecursive(RNFS.DocumentDirectoryPath);
    files.push(...sandboxFiles);

    // 2. Downloads Folder (Platform specific)
    const downloadDir = Platform.OS === 'android'
      ? `${RNFS.ExternalStorageDirectoryPath}/Download`
      : RNFS.DocumentDirectoryPath; // Fallback for iOS
    
    if (downloadDir !== RNFS.DocumentDirectoryPath) {
      scanPaths.push('Downloads');
      const downloadFiles = await this.walkDirRecursive(downloadDir);
      files.push(...downloadFiles);
    }

    // 3. Documents Folder (Platform specific)
    const documentsDir = Platform.OS === 'android'
      ? `${RNFS.ExternalStorageDirectoryPath}/Documents`
      : RNFS.DocumentDirectoryPath;
    
    if (documentsDir !== RNFS.DocumentDirectoryPath) {
      scanPaths.push('Documents');
      const docFiles = await this.walkDirRecursive(documentsDir);
      files.push(...docFiles);
    }

    // De-duplicate files by path
    const uniqueFilesMap = new Map<string, ScannedFileMeta>();
    for (const f of files) {
      uniqueFilesMap.set(f.file_path, f);
    }

    return {
      files: Array.from(uniqueFilesMap.values()),
      scanPaths: scanPaths.join(', '),
    };
  },

  /**
   * Gets the last scan session state from file system.
   */
  async getLastScanState(): Promise<AutoScanState> {
    try {
      const exists = await RNFS.exists(STATE_FILE_PATH);
      if (exists) {
        const content = await RNFS.readFile(STATE_FILE_PATH, 'utf8');
        return JSON.parse(content);
      }
    } catch (e) {
      console.warn('[AutoScan] Failed loading last scan state:', e);
    }
    return {
      lastScanTimestamp: 0,
      totalFilesScanned: 0,
      threatsFound: 0,
      status: 'idle',
    };
  },

  /**
   * Writes the scan session state to the file system.
   */
  async saveScanState(state: AutoScanState): Promise<void> {
    try {
      await RNFS.writeFile(STATE_FILE_PATH, JSON.stringify(state), 'utf8');
    } catch (e) {
      console.warn('[AutoScan] Failed saving scan state:', e);
    }
  },

  /**
   * Runs an automatic scan if more than 24 hours have elapsed since the last scan.
   */
  async checkAndTriggerDailyScan(
    scanBatchFn: (files: { filename: string; file_path: string }[], paths: string) => Promise<any>
  ): Promise<AutoScanState | null> {
    const state = await this.getLastScanState();
    const now = Date.now();
    const oneDayMs = 24 * 60 * 60 * 1000;

    if (now - state.lastScanTimestamp >= oneDayMs) {
      console.log('[AutoScan] Running scheduled daily device files scan...');
      
      try {
        await this.saveScanState({ ...state, status: 'scanning' });
        const { files, scanPaths } = await this.collectAllDeviceFiles();
        
        if (files.length === 0) {
          const finalState: AutoScanState = {
            lastScanTimestamp: now,
            totalFilesScanned: 0,
            threatsFound: 0,
            status: 'completed',
          };
          await this.saveScanState(finalState);
          return finalState;
        }

        const batchRequestFiles = files.map(f => ({
          filename: f.filename,
          file_path: f.file_path,
        }));

        const result = await scanBatchFn(batchRequestFiles, scanPaths);

        const finalState: AutoScanState = {
          lastScanTimestamp: now,
          totalFilesScanned: result.total_scanned ?? files.length,
          threatsFound: result.threats_found ?? 0,
          status: 'completed',
        };
        await this.saveScanState(finalState);
        return finalState;
      } catch (err) {
        console.error('[AutoScan] Scheduled scan failed:', err);
        const failedState: AutoScanState = {
          ...state,
          status: 'failed',
        };
        await this.saveScanState(failedState);
        return failedState;
      }
    }
    return null;
  },
};
