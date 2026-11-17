"""Root entrypoint to run the Rock-Paper-Scissors Web Server."""

import os
import uvicorn
from rps.web.server import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Starting Rock-Paper-Scissors AI Arena on http://localhost:{port}")
    uvicorn.run("rps.web.server:app", host=host, port=port, reload=False)
