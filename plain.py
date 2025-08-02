import os
import textwrap
import re

from PIL import Image, ImageDraw, ImageFont


def draw_text(draw, position, text, font, max_width):
    lines = textwrap.wrap(text, width=max_width)
    y_offset = 0
    for line in lines:
        draw.text((position[0], position[1] + y_offset), line, font=font, fill="black")
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


def generate(
        title: str,
        casting_time: str,
        spell_range: str,
        components: str,
        duration: str,
        description: str,
        school: str,
        level: int
    ) -> None:
    image = Image.open("template/0.jpg").convert("RGB")
    draw = ImageDraw.Draw(image)
    width = image.size[0]

    font_title = ImageFont.truetype("fonts/Raleway/static/Raleway-Bold.ttf", 26)
    font_label = ImageFont.truetype("fonts/Raleway/static/Raleway-Italic.ttf", 14)
    font_body  = ImageFont.truetype("fonts/EB_Garamond/EBGaramond-VariableFont_wght.ttf", 16)
    font_footer = ImageFont.truetype("fonts/Raleway/static/Raleway-Bold.ttf", 14)

    duration = os.environ.get("DURATION", "")
    description = os.environ.get("DESCRIPTION", "")
    school = os.environ.get("SCHOOL", "")
    level = int(os.environ.get("LEVEL"))

    # Title (centered)
    center_text(draw, title, font_title, y=24, image_width=width)

    # Labels
    center_text(draw, casting_time, font_label, y=85, image_width=width / 2)
    center_text(draw, spell_range, font_label, y=85, image_width=width / 2, x_offset=width / 2)
    center_text(draw, components, font_label, y=130, image_width=width / 2)
    center_text(draw, duration, font_label, y=130, image_width=width / 2, x_offset=width / 2)

    # Description
    draw_text(draw, (45, 180), description, font=font_body, max_width=48)

    # Footer
    center_text(draw, school, font_footer, y=490, image_width=width / 2)
    center_text(draw, level_text(level), font_footer, y=490, image_width=width / 2, x_offset=width / 2)

    safe_title = title.replace(":", "")
    filename = f"cards/L{level}.{safe_title}.jpg"
    image.save(filename)
