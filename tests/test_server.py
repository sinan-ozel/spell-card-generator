import os
import requests
import threading
import time
import json

import pytest
from http.server import BaseHTTPRequestHandler, HTTPServer


BASE_URL = os.getenv("BASE_URL", "http://app:8000")
CALLBACK_PORT = 9999
CALLBACK_PATH = "/callback"
CALLBACK_URL = f"http://test:{CALLBACK_PORT}{CALLBACK_PATH}"

spell_data = {
    "title": "Acid Splash",
    "casting_time": "1 action",
    "spell_range": "60 feet",
    "components": "V, S",
    "duration": "Instantaneous",
    "description": "You hurl a bubble of acid...",
    "school": "Conjuration",
    "level": 0,
}
callback_result = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == CALLBACK_PATH:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            callback_result["payload"] = json.loads(body)
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def run_callback_server():
    httpd = HTTPServer(("0.0.0.0", CALLBACK_PORT), CallbackHandler)
    httpd.timeout = 20  # seconds
    httpd.handle_request()  # handle one request, then exit


def test_card_creation_without_callback():
    """Test card creation without a callback URL."""
    payload = {"spell_data": spell_data}
    r = requests.post(f"{BASE_URL}/v1/generate", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"


def test_card_creation_with_callback():
    """Test card creation with a callback URL."""
    payload = {
        "spell_data": spell_data,
        "callback_url": "http://localhost:9999/does-not-matter",
    }
    r = requests.post(f"{BASE_URL}/v1/generate", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"


def test_swagger_ui_available():
    """Test that the Swagger UI is available at /docs."""
    r = requests.get(f"{BASE_URL}/docs")
    assert r.status_code == 200, f"Swagger UI not available: {r.status_code}"
    assert "Swagger UI" in r.text or "swagger-ui" in r.text.lower()


def test_openapi_json_available():
    """Test that the OpenAPI JSON is available at /openapi.json."""
    r = requests.get(f"{BASE_URL}/openapi.json")
    assert r.status_code == 200, f"OpenAPI JSON not available: {r.status_code}"
    assert r.headers.get("content-type", "").startswith("application/json")


@pytest.mark.depends(on=["test_card_creation_with_callback"])
def test_callback_and_download_card():
    """Test callback reception and card download."""
    # Start callback server in a thread
    server_thread = threading.Thread(target=run_callback_server, daemon=True)
    server_thread.start()

    payload = {
        "spell_data": spell_data,
        "callback_url": CALLBACK_URL,
    }
    r = requests.post(f"{BASE_URL}/v1/generate", json=payload)
    assert r.status_code == 200, r.text

    # Wait for callback (max 20 seconds)
    for _ in range(40):
        if "payload" in callback_result:
            break
        time.sleep(0.5)
    else:
        assert False, "Callback not received"

    cb = callback_result["payload"]
    assert cb["status"] == "ready"
    assert "url" in cb

    # Download the card
    card_url = f"{BASE_URL}{cb['url']}"
    card_resp = requests.get(card_url)
    assert card_resp.status_code == 200
    assert card_resp.headers.get("content-type", "").startswith("image/")