"""Main entrypoint for the machine learning client: runs poller loop."""
import time
import logging
from app.poller import process_pending

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    logging.info("Machine learning client started. Processing pending recordings...")
    while True:
        processed = process_pending(limit=10)
        if processed == 0:
            time.sleep(10)  # Wait before polling again if nothing to do
        else:
            time.sleep(2)  # Shorter wait if work was done
