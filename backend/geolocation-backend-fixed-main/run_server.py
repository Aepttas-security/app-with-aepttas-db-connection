import sys
import os
import uvicorn

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from app.main import app

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8003)
