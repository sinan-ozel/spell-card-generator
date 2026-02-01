import logging
import os
import re
from importlib import import_module
from typing import Dict, List, Optional

import requests
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl
from sse_starlette.sse import EventSourceResponse

from main import VALID_GENERATORS
from spell import Spell

generators = {}
stream_generators = {}
for generator in VALID_GENERATORS:
    generators[generator] = getattr(import_module(f"generators.{generator}"),
                                    "generate")
    # Load streaming generators for MCP
    stream_generators[generator] = getattr(
        import_module(f"generators.{generator}"),
        "generate_stream"
    )
    # TODO: Catch fails, start server, turn back an error message if missing.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spell Card Generator API",
    description="API for generating spell cards.",
    version="0.4.0",
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


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""
    jsonrpc: str = Field(
        default="2.0",
        description="JSON-RPC version",
        example="2.0"
    )
    method: str = Field(
        ...,
        description="Method to call (list_tools or generate_spell_card_stream)",
        example="list_tools"
    )
    params: Optional[Dict] = Field(
        default=None,
        description="Parameters for the method",
        example={}
    )
    id: Optional[str] = Field(
        default=None,
        description="Request ID",
        example="1"
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
                        generator: str = 'plain',
                        callback_url: str | None = None):
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


@app.get("/v1/generators", response_model=List[Dict[str, object]])
def get_generators():
    """Get available card generators with status and module docstring."""
    result = []
    for name in VALID_GENERATORS:
        try:
            mod = import_module(f"generators.{name}")
            doc = mod.__doc__ or ""
            info = [line.strip() for line in doc.splitlines() if line.strip()]
        except Exception:
            info = []
        result.append({
            "generator": name,
            "status": "available",
            "information": info
        })
    return result


@app.post(
    "/mcp",
    responses={
        200: {
            "description": "MCP JSON-RPC response or SSE stream",
            "content": {
                "application/json": {
                    "example": {
                        "jsonrpc": "2.0",
                        "result": {
                            "tools": [
                                {
                                    "name": "generate_spell_card_stream",
                                    "description": "Generate D&D spell cards with streaming progress updates"
                                }
                            ]
                        },
                        "id": "1"
                    }
                }
            }
        }
    }
)
async def mcp_endpoint(mcp_request: MCPRequest):
    """MCP JSON-RPC endpoint with SSE streaming support.

    Accepts JSON-RPC requests and streams progress updates via SSE.
    Supports the 'generate_spell_card_stream' tool and 'list_tools' method.

    Example JSON-RPC request for listing tools:
    ```json
    {
        "jsonrpc": "2.0",
        "method": "list_tools",
        "id": "1"
    }
    ```

    Example JSON-RPC request for streaming generation:
    ```json
    {
        "jsonrpc": "2.0",
        "method": "generate_spell_card_stream",
        "params": {
            "generator": "plain",
            "spell_data": {
                "title": "Fireball",
                "casting_time": "1 action",
                "range": "150 feet",
                "components": "V, S, M",
                "duration": "Instantaneous",
                "description": "A bright streak flashes...",
                "school": "Evocation",
                "level": 3
            }
        },
        "id": "2"
    }
    ```
    """
    method = mcp_request.method
    params = mcp_request.params or {}
    request_id = mcp_request.id

    # Map MCP tool names to generators
    if method == "generate_spell_card_stream":
        generator_name = params.get("generator", "plain")

        if generator_name not in VALID_GENERATORS:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Invalid generator: {generator_name}. "
                              f"Valid options: {', '.join(VALID_GENERATORS)}"
                },
                "id": request_id
            }

        # Return SSE stream
        async def event_generator():
            """Generate Server-Sent Events for streaming progress."""
            import json

            try:
                generator_fn = stream_generators[generator_name]

                # Stream progress events
                async for event in generator_fn(params, None):
                    data = {
                        "jsonrpc": "2.0",
                        "method": "tool.progress",
                        "params": event,
                        "id": request_id
                    }
                    yield {"data": json.dumps(data)}

            except Exception as e:
                logger.error(f"Error in MCP stream: {e}", exc_info=True)
                error_data = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": request_id
                }
                yield {"data": json.dumps(error_data)}

        return EventSourceResponse(event_generator())

    elif method == "list_tools":
        # Return available MCP tools
        tools = [{
            "name": "generate_spell_card_stream",
            "description": "Generate D&D spell cards with streaming progress updates",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "generator": {
                        "type": "string",
                        "description": f"Card generator to use. Options: {', '.join(VALID_GENERATORS)}",
                        "default": "plain"
                    },
                    "spell_data": {
                        "type": "object",
                        "description": "Spell details",
                        "properties": {
                            "title": {"type": "string"},
                            "casting_time": {"type": "string"},
                            "range": {"type": "string"},
                            "components": {"type": "string"},
                            "duration": {"type": "string"},
                            "description": {"type": "string"},
                            "school": {"type": "string"},
                            "level": {"type": "integer", "minimum": 0, "maximum": 9}
                        },
                        "required": ["title", "casting_time", "range", "components",
                                   "duration", "description", "school", "level"]
                    }
                },
                "required": ["spell_data"]
            }
        }]
        return {
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": request_id
        }

    else:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        }
