import os
import requests
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def ping_backend():
    url = os.environ.get("HF_BACKEND_URL")
    if not url:
        logging.error("HF_BACKEND_URL environment variable is not set.")
        sys.exit(1)

    try:
        logging.info(f"Pinging Hugging Face backend at: {url}")
        # Sending a simple GET request to wake up the Hugging Face Space
        # Even if the endpoint returns 404, the space will wake up.
        response = requests.get(url, timeout=15)
        
        # We don't raise_for_status() because a 404 on '/' still means the backend is awake
        logging.info(f"Ping completed. Status Code: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to ping backend. Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ping_backend()
