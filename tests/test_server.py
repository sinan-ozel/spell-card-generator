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
    payload = {"spell_data": spell_data}
    r = requests.post(f"{BASE_URL}/v1/generate", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"


def test_card_creation_with_callback():
    payload = {
        "spell_data": spell_data,
        "callback_url": "http://localhost:9999/does-not-matter",
    }
    r = requests.post(f"{BASE_URL}/v1/generate", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"
