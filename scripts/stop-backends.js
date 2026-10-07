const { execSync } = require('child_process');

const PORTS = [5000, 8000, 8001, 8002, 8003, 8004, 8005, 8081];

console.log('====================================================');
console.log('🛑 Stopping AEPTTAS Shield Unified Backend...');
console.log('====================================================');

function killPortWindows(port) {
  try {
    const stdout = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
    const lines = stdout.trim().split('\n');
    const pids = new Set();
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      const pid = parts[parts.length - 1];
      if (pid && /^\d+$/.test(pid) && pid !== '0') {
        pids.add(pid);
      }
    }

    for (const pid of pids) {
      try {
        execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
        console.log(`🧹 Freed port ${port} (Terminated PID ${pid})`);
      } catch {}
    }
  } catch {
    // Port not in use
  }
}

function killPortUnix(port) {
  try {
    execSync(`lsof -ti:${port} | xargs kill -9`, { stdio: 'ignore' });
    console.log(`🧹 Freed port ${port}`);
  } catch {}
}

PORTS.forEach((port) => {
  if (process.platform === 'win32') {
    killPortWindows(port);
  } else {
    killPortUnix(port);
  }
});

try {
  [5000, 8081].forEach((p) => {
    try {
      execSync(`adb reverse --remove tcp:${p}`, { stdio: 'ignore' });
    } catch {}
  });
  console.log('🔌 Removed ADB reverse port forwards.');
} catch {}

console.log('====================================================');
console.log('⚡ Unified backend has been stopped.');
console.log('====================================================\n');
