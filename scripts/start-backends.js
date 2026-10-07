const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const callerBackendDir = path.join(rootDir, 'caller_backend');

const UNIFIED_PORT = 5000;
const LEGACY_PORTS = [8000, 8001, 8002, 8003, 8004, 8005, 5000];

console.log('====================================================');
console.log('🚀 Starting AEPTTAS Shield Unified Backend (Port 5000)...');
console.log('====================================================');

// Pre-clean ports before starting to prevent collisions
function freePort(port) {
  try {
    if (process.platform === 'win32') {
      const stdout = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
      const lines = stdout.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && /^\d+$/.test(pid) && pid !== '0') {
          try { execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' }); } catch {}
        }
      }
    } else {
      execSync(`lsof -ti:${port} | xargs kill -9`, { stdio: 'ignore' });
    }
  } catch {}
}

LEGACY_PORTS.forEach((p) => freePort(p));

if (fs.existsSync(callerBackendDir)) {
  try {
    if (process.platform === 'win32') {
      const child = spawn('cmd.exe', ['/c', 'start', '""', '/min', 'python', 'run_server.py'], {
        cwd: callerBackendDir,
        detached: true,
        stdio: 'ignore',
      });
      child.unref();
    } else {
      const child = spawn('python3', ['run_server.py'], {
        cwd: callerBackendDir,
        detached: true,
        stdio: 'ignore',
      });
      child.unref();
      child.on('error', (err) => {
        console.warn(`⚠️ [Unified Backend] notice: ${err.message}`);
      });
    }

    console.log(`✅ Started [AEPTTAS Unified Backend] on SINGLE port ${UNIFIED_PORT}`);
    console.log(`   ├── /api/callers/*   (Caller Intelligence)`);
    console.log(`   ├── /api/malware/*   (Malware APK Scanner)`);
    console.log(`   ├── /api/geo/*       (Geolocation & Spoofing)`);
    console.log(`   ├── /api/vuln/*      (Vulnerability Detection)`);
    console.log(`   └── /api/parental/*  (Parental Control & SOS)`);
  } catch (e) {
    console.warn(`⚠️ Could not auto-start Unified Backend: ${e.message}`);
  }
} else {
  console.log(`ℹ️ Unified backend directory not found at ${callerBackendDir}`);
}

// Configure ADB reverse port forwarding for Android devices / emulators
try {
  const ports = [5000, 8081];
  ports.forEach((p) => {
    try {
      execSync(`adb reverse tcp:${p} tcp:${p}`, { stdio: 'ignore' });
    } catch {}
  });
  console.log('🔌 ADB reverse port forwarding configured for ports (5000, 8081)');
} catch (e) {
  // ADB not connected or not in PATH, non-critical
}

console.log('====================================================');
console.log('⚡ Single unified backend running on http://127.0.0.1:5000');
console.log('====================================================\n');
