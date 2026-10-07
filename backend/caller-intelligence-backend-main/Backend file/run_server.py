import sys
import os
import uvicorn

# Ensure UTF-8 output encoding on Windows console
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

if __name__ == '__main__':
    uvicorn.run('main1:app', host='0.0.0.0', port=8004, log_level='info')
