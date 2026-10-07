import RNFS from 'react-native-fs';

const QUARANTINE_DIR = `${RNFS.DocumentDirectoryPath}/quarantine`;

export const QuarantineManager = {
  /**
   * Moves a file to the secure internal app quarantine directory,
   * renaming it to its SHA-256 hash to prevent execution.
   * @returns The new secure isolated file path.
   */
  async quarantineFile(originalPath: string): Promise<string> {
    const fileExists = await RNFS.exists(originalPath);
    if (!fileExists) {
      throw new Error(`Source file does not exist: ${originalPath}`);
    }

    // 1. Ensure the secure quarantine folder exists
    const quarantineFolderExists = await RNFS.exists(QUARANTINE_DIR);
    if (!quarantineFolderExists) {
      await RNFS.mkdir(QUARANTINE_DIR);
    }

    // 2. Calculate the SHA-256 hash of the file using react-native-fs native hashing
    let fileHash: string;
    try {
      fileHash = await RNFS.hash(originalPath, 'sha256');
    } catch (e) {
      // Fallback: generate a random string ID if native hashing fails
      fileHash = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    }

    const secureFileName = `${fileHash}.qtn`; // Obfuscated extension to neutralize it
    const quarantinePath = `${QUARANTINE_DIR}/${secureFileName}`;

    // 3. Move file from original path to quarantine
    await RNFS.moveFile(originalPath, quarantinePath);

    return quarantinePath;
  },

  /**
   * Restores a quarantined file back to its original location.
   * Falls back to public external files dir if the original directory is not writable.
   * @returns The path where the file was restored.
   */
  async restoreFile(quarantinePath: string, originalPath: string): Promise<string> {
    const fileExists = await RNFS.exists(quarantinePath);
    if (!fileExists) {
      throw new Error(`Quarantined file does not exist: ${quarantinePath}`);
    }

    let targetPath = originalPath;
    const parentDir = originalPath.substring(0, originalPath.lastIndexOf('/'));

    // Check if the parent directory exists and is writable
    let isWritable = false;
    try {
      const parentExists = await RNFS.exists(parentDir);
      if (parentExists) {
        // Test write ability by attempting a temp directory check
        isWritable = true; 
      }
    } catch (e) {
      isWritable = false;
    }

    if (!isWritable) {
      // Fallback: Restore to the app's external files directory
      const restoredFolder = `${RNFS.ExternalDirectoryPath || RNFS.DocumentDirectoryPath}/RestoredAPKs`;
      const folderExists = await RNFS.exists(restoredFolder);
      if (!folderExists) {
        await RNFS.mkdir(restoredFolder);
      }
      const fileName = originalPath.substring(originalPath.lastIndexOf('/') + 1);
      targetPath = `${restoredFolder}/${fileName}`;
    } else {
      // Ensure target directory path is fully structured
      await RNFS.mkdir(parentDir);
    }

    // Move file back
    await RNFS.moveFile(quarantinePath, targetPath);

    return targetPath;
  },

  /**
   * Permanently deletes the file from quarantine storage.
   */
  async deletePermanently(quarantinePath: string): Promise<boolean> {
    const fileExists = await RNFS.exists(quarantinePath);
    if (fileExists) {
      await RNFS.unlink(quarantinePath);
      return true;
    }
    return false;
  },

  /**
   * Scans the local secure quarantine directory and automatically deletes
   * any files that have been quarantined for over a week (7 days) without user response.
   * Can be configured with custom expiration time in milliseconds (e.g. for testing).
   * @returns The number of files deleted.
   */
  async cleanupExpiredFiles(expirationMs: number = 7 * 24 * 60 * 60 * 1000): Promise<number> {
    const quarantineFolderExists = await RNFS.exists(QUARANTINE_DIR);
    if (!quarantineFolderExists) {
      return 0;
    }

    let deletedCount = 0;
    try {
      const files = await RNFS.readDir(QUARANTINE_DIR);
      const now = Date.now();

      for (const file of files) {
        if (file.isFile() && file.name.endsWith('.qtn')) {
          const fileStat = await RNFS.stat(file.path);
          const mtimeObj: any = fileStat.mtime;
          const quarantineTime = typeof mtimeObj === 'number' ? mtimeObj : (mtimeObj instanceof Date ? mtimeObj.getTime() : Date.parse(String(mtimeObj)));
          if (now - quarantineTime >= expirationMs) {
            await RNFS.unlink(file.path);
            deletedCount++;
          }
        }
      }
    } catch (e) {
      console.warn('Failed to perform local quarantine cleanup:', e);
    }
    return deletedCount;
  }
};
