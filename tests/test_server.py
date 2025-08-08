import os

import requests

BASE_URL = os.getenv("BASE_URL", "http://app:8000")

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
