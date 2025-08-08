import re
from typing import Optional
import logging

import requests
from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from plain import generate
from spell import Spell

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spell Card Generator API",
    description="API for generating spell cards.",
    version="0.1.1",
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
        logger.debug("Callback sent to %s", callback_url)
    except Exception as e:
        logger.info("Callback to %s failed: %s", callback_url, e)


@app.post("/v1/generate")
async def create_spell_card(request: SpellRequest,
                            background_tasks: BackgroundTasks):
    spell = Spell(**request.spell_data.dict())
    background_tasks.add_task(generate_and_notify, spell, request.callback_url)
    return {"status": "queued", "title": spell.title}


def generate_and_notify(spell: Spell, callback_url: Optional[str]):
    title_normalized = re.sub(r'\s+', ' ', spell.title.strip())
    safe_title = title_normalized.replace(":", "").replace(" ", "-")
    filename = f"L{spell.level}.{safe_title}.jpg"
    filepath = f"cards/{filename}"
    image = generate(spell)
    image.save(filepath)
    payload = {
        "status": "ready",
        "title": spell.title,
        "level": spell.level,
        "filename": filename,
        "url": f"/{filepath}",
    }
    if callback_url:
        notify_callback(callback_url, payload)
