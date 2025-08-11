"""Spell card generator using the TornioDuva item card background.

Background art credited to TornioDuva (https://tornioduva.itch.io/).
"""

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
