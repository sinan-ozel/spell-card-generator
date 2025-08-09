import logging
import re
import os
from importlib import import_module
from typing import Optional

import requests
from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

from main import VALID_GENERATORS
from spell import Spell

generators = {}
for generator in VALID_GENERATORS:
    generators[generator] = getattr(import_module(f"generators.{generator}"), "generate")
    # TODO: Catch fails, start server, turn back an error message if missing.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spell Card Generator API",
    description="API for generating spell cards.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.mount("/cards", StaticFiles(directory="cards"), name="cards")


class SpellData(BaseModel):
    """Represents the details of a Dungeons & Dragons spell for card
    generation."""
    title: str = Field(
        ...,
        description=f"Name of the spell. "
                    f"Max {Spell.MAX_TITLE_CHARS} characters",
        example="Acid Splash"
    )
    casting_time: str = Field(
        ...,
        description="Time required to cast the spell.",
        example="1 action"
    )
    range: str = Field(
        ...,
        description="Effective range of the spell.",
        example="60 feet"
    )
    components: str = Field(
        ...,
        description="Spell components (V, S, M), validated and formatted.",
        example="V, S"
    )
    duration: str = Field(
        ...,
        description="Duration of the spell's effect.",
        example="Instantaneous"
    )
    description: str = Field(
        ...,
        description="Description of the spell's effect and mechanics."
                    f" Max {Spell.MAX_DESCRIPTION_CHARS} characters",
        example="You hurl a bubble of acid..."
    )
    school: str = Field(
        ...,
        description="Magical school the spell belongs to (e.g., Evocation).",
        example="Conjuration"
    )
    level: int = Field(
        ...,
        description="Spell level, must be between 0 (cantrip) & 9 (highest).",
        example=0,
    )


class SpellRequest(BaseModel):
    """Request for generating a spell card."""
    spell_data: SpellData = Field(..., description="Spell details")
    callback_url: Optional[HttpUrl] = Field(
        None,
        description="Optional callback URL to notify when the card is ready",
        example="http://localhost:9999/callback"
    )
    generator: str = Field(
        default="plain",
        description="Name of the generator to use."
                    f" Available generators: {', '.join(VALID_GENERATORS)}",
        example="plain"
    )


def notify_callback(callback_url: str, payload: dict):
    try:
        requests.post(callback_url, json=payload, timeout=10)
        logger.debug("Callback sent to %s", callback_url)
    except Exception as e:
        logger.info("Callback to %s failed: %s", callback_url, e)


@app.post(
    "/v1/generate",
    responses={
        200: {
            "description": "Spell card generation successfully queued.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "queued",
                        "title": "Acid Splash"
                    }
                }
            }
        },
        422: {
            "description": "Validation error. The request body is invalid.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "spell_data", "title"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_spell_card(request: SpellRequest,
                            background_tasks: BackgroundTasks):
    """Queue a spell card for generation.

    Accepts spell details and an optional callback URL. The spell card is
    generated asynchronously in the background. If a callback URL is provided,
    a POST request will be sent to that URL with the card's status and
    download information once generation is complete.

    Returns:
        dict: Status and spell title indicating the card generation has been
        queued.
    """
    spell = Spell(**request.spell_data.dict())
    background_tasks.add_task(generate_and_notify,
                              spell,
                              request.generator,
                              request.callback_url)
    return {"status": "queued", "title": spell.title}


def generate_and_notify(spell: Spell,
                        generator: str='plain',
                        callback_url: str | None=None):
    title_normalized = re.sub(r'\s+', ' ', spell.title.strip())
    safe_title = title_normalized.replace(":", "").replace(" ", "-")
    filename = f"L{spell.level}.{safe_title}.jpg".lower()
    output_dir = f"cards/{generator}"
    os.makedirs(output_dir, exist_ok=True)
    filepath = f"{output_dir}/{filename}"
    image = generators[generator](spell)
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


@app.get("/v1/generators", response_model=dict)
def get_generators():
    """Get available card generators."""
    return {name: "available" for name in VALID_GENERATORS}
