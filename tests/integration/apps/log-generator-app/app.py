import datetime
import logging
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PORT = 8080


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass  # silence default per-request stderr logging


def serve():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=serve, daemon=True).start()

    while True:
        logger.debug(f"{datetime.datetime.now()} This is a debug message")
        logger.info(f"{datetime.datetime.now()} This is an info message")
        logger.warning(f"{datetime.datetime.now()} This is a warning message")
        logger.error(f"{datetime.datetime.now()} This is an error message")

        # Self-ping: auto-instrumented by opentelemetry-instrumentation-urllib -> emits a client HTTP span.
        try:
            with urllib.request.urlopen(f"http://localhost:{PORT}/health", timeout=5) as response:
                logger.info(f"GET /health -> {response.status}")
        except Exception as error:
            logger.error(f"GET /health failed: {error}")

        time.sleep(2)
