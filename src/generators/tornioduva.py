"""Spell card generator using the TornioDuva item card background.

Background art credited to TornioDuva (https://tornioduva.itch.io/).
"""

import asyncio
import textwrap

from PIL import Image, ImageDraw, ImageFont

from spell import Spell


def draw_text(draw, position, text, font, max_width):
    lines = textwrap.wrap(text, width=max_width)
    y_offset = 0
    for line in lines:
        draw.text(
            (position[0], position[1] + y_offset),
            line,
            font=font,
            fill="black",
        )
        bbox = font.getbbox(line)
        line_height = bbox[3] - bbox[1]
        y_offset += line_height + 5


def center_text(draw, text, font, y, image_width, x_offset=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (image_width - text_width) // 2 + x_offset
    draw.text((x, y), text, font=font, fill="black")


def level_text(level: int) -> str:
    if level == 0:
        return "Cantrip"
    elif level < 10:
        return f"Level {level}"
    else:
        raise ValueError(f"Allowed spell levels: {list(range(10))}")


# TODO: Change the generate function to be a wrapper around generate_stream, to avoid code duplication.
def generate(spell: Spell) -> Image:
    image = Image.open("template/tornio-duva/item-card.png").convert("RGB")
    draw = ImageDraw.Draw(image)
    width = image.size[0]

    font_title = ImageFont.truetype(
        "fonts/RINGM___.TTF", 48
    )
    font_light_label = ImageFont.truetype(
        "fonts/MPLANTI1.ttf", 36
    )
    font_label = ImageFont.truetype(
        "fonts/MPLANTI3.ttf", 36
    )
    font_body = ImageFont.truetype(
        "fonts/MPLANTIN.ttf", 32
    )
    font_footer = ImageFont.truetype(
        "fonts/Raleway/static/Raleway-Bold.ttf", 28
    )

    # Title (centered)
    center_text(draw, spell.title, font_title, y=130, image_width=width)

    # Labels
    center_text(
        draw,
        "Casting Time\nRange\nComponents\nDuration",
        font_label,
        y=290,
        image_width=width / 2 + 16
    )
    center_text(
        draw,
        '\n'.join([spell.casting_time,
                   spell.range,
                   spell.components,
                   spell.duration]),
        font_light_label,
        y=290,
        image_width=width / 2 + 16,
        x_offset=width / 2 - 16
    )

    # Description
    draw_text(draw,
              (100, 450),
              spell.description,
              font=font_body,
              max_width=48)

    # Footer
    center_text(
        draw, spell.school, font_footer, y=1075, image_width=width / 2 + 16
    )
    center_text(
        draw,
        level_text(spell.level),
        font_footer,
        y=1075,
        image_width=width / 2,
        x_offset=width / 2,
    )

    return image


async def generate_stream(params: dict, progress_callback):
    """MCP-compatible streaming generator for spell cards.

    Args:
        params: Dict with 'spell_data' containing spell attributes
        progress_callback: Async function to report progress

    Yields:
        Progress events and final result
    """
    try:
        # Extract spell data
        spell_data = params.get('spell_data', {})

        # Send initial progress
        yield {"progress": 5, "message": "Initializing TornioDuva card generation"}
        await asyncio.sleep(0.01)  # Allow event to be sent

        # Create Spell object
        spell = Spell(
            title=spell_data.get('title', ''),
            casting_time=spell_data.get('casting_time', ''),
            range=spell_data.get('range', ''),
            components=spell_data.get('components', ''),
            duration=spell_data.get('duration', ''),
            description=spell_data.get('description', ''),
            school=spell_data.get('school', ''),
            level=spell_data.get('level', 0)
        )

        yield {"progress": 20, "message": "Loading TornioDuva template"}
        await asyncio.sleep(0.01)

        yield {"progress": 40, "message": "Loading fonts"}
        await asyncio.sleep(0.01)

        # Generate the image using existing logic
        image = generate(spell)

        yield {"progress": 70, "message": "Drawing spell details"}
        await asyncio.sleep(0.01)

        yield {"progress": 90, "message": "Finalizing card"}
        await asyncio.sleep(0.01)

        # Convert to base64 for transport
        import io
        import base64
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # Send final result
        yield {
            "progress": 100,
            "message": "Card generation complete",
            "status": "completed",
            "card": {
                "title": spell.title,
                "level": spell.level,
                "image_data": image_base64,
                "format": "jpeg"
            }
        }

    except Exception as e:
        yield {
            "progress": -1,
            "message": f"Error: {str(e)}",
            "status": "error",
            "error": str(e)
        }
