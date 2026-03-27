"""Start FastAPI server on port 8002"""
import sys
sys.path.insert(0, "services")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=False)
