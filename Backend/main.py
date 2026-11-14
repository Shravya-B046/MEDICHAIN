import os
import sys
from pathlib import Path

# Ensure the Backend directory is always on sys.path regardless of execution working directory
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from app.config import settings
from app.main import app

# Expose app for ASGI runners (uvicorn main:app)
__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

