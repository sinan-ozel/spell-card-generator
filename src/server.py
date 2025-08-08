from typing import Optional

import requests
from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from plain import generate
from spell import Spell

app = FastAPI(
    title="Spell Card Generator API",
    description="API for generating spell cards.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.mount("/cards", StaticFiles(directory="cards"), name="cards")


class SpellData(BaseModel):
    title: str
    casting_time: str
    spell_range: str
    components: str
    duration: str
    description: str
    school: str
    level: int


class SpellRequest(BaseModel):
    spell_data: SpellData
    callback_url: Optional[HttpUrl] = None


def notify_callback(callback_url: str, payload: dict):
    try:
        requests.post(callback_url, json=payload, timeout=10)
        print(f"✅ Callback sent to {callback_url}")
    except Exception as e:
        print(f"❌ Callback to {callback_url} failed: {e}")


@app.post("/v1/generate")
async def create_spell_card(request: SpellRequest,
                            background_tasks: BackgroundTasks):
    spell = Spell(**request.spell_data.dict())
    background_tasks.add_task(generate_and_notify, spell, request.callback_url)
    return {"status": "queued", "title": spell.title}


def generate_and_notify(spell: Spell, callback_url: Optional[str]):
    generate(spell)
    safe_title = spell.title.replace(":", "").replace(" ", "_")
    filename = f"L{spell.level}.{safe_title}.jpg"
    f"cards/{filename}"
    payload = {
        "status": "ready",
        "title": spell.title,
        "level": spell.level,
        "filename": filename,
        "url": f"/cards/{filename}",
    }
    if callback_url:
        notify_callback(callback_url, payload)
