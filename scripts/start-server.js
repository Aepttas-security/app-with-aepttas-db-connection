const { spawn } = require('child_process');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const port = process.env.PORT || 5000;

console.log('====================================================');
console.log(`🚀 Starting AEPTTAS Shield Backend Server on Port ${port}...`);
console.log('====================================================');

const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
const child = spawn(pythonCmd, ['-m', 'uvicorn', 'caller_backend.main:app', '--host', '0.0.0.0', '--port', String(port)], {
  cwd: rootDir,
  stdio: 'inherit',
  env: { ...process.env, PYTHONPATH: path.join(rootDir, 'caller_backend') }
});

child.on('error', (err) => {
  console.error('❌ Failed to start Python backend server:', err);
  process.exit(1);
});

child.on('exit', (code) => {
  console.log(`Server exited with code ${code}`);
  process.exit(code || 0);
});
