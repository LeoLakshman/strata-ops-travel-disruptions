"""
Main entry point for Strata Ops Travel Disruption Intelligence Platform.
Run via:
    python main.py
or:
    ./run.sh
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n=======================================================")
    print(f"  STRATA OPS // U.S. Corporate Travel Disruption Engine")
    print(f"  Server starting at: http://localhost:{port}")
    print(f"  API Documentation:  http://localhost:{port}/docs")
    print(f"=======================================================\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
