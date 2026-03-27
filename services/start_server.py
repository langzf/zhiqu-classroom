"""Server launcher with UTF-8 logging to file."""
import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
import logging, uvicorn

# Configure file logging
logging.basicConfig(
    filename="server.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    encoding="utf-8",
    force=True,
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, log_level="debug")
