# backend/caller_backend/run_server.py
import sys
import os

# Ensure script directory is first in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure UTF-8 output encoding on Windows console
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import uvicorn
import main

if __name__ == '__main__':
    print("==================================================================")
    print("Starting AEPTTAS Shield Unified Backend Server on Port 5000...")
    print("==================================================================")
    uvicorn.run(main.app, host='0.0.0.0', port=5000, log_level='info')
