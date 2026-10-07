import sys
import os

# Ensure caller_backend directory is in Python path
backend_dir = os.path.join(os.path.dirname(__file__), 'caller_backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from caller_backend.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
