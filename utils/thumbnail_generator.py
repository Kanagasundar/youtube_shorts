
from PIL import Image, ImageDraw, ImageFont
import os

def generate_thumbnail(image_path, output_path, overlay_text=""):
    # Open the base image
    image = Image.open(image_path).convert("RGB")

    # Prepare drawing context
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Load a font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = int(height * 0.08)
    font = ImageFont.truetype(font_path, font_size)

    # Define text placement
    text_width, text_height = draw.textsize(overlay_text, font=font)
    text_position = ((width - text_width) / 2, height - text_height - 40)

    # Draw text background rectangle
    padding = 10
    rect_coords = [
        text_position[0] - padding,
        text_position[1] - padding,
        text_position[0] + text_width + padding,
        text_position[1] + text_height + padding
    ]
    draw.rectangle(rect_coords, fill="black")

    # Draw overlay text
    draw.text(text_position, overlay_text, font=font, fill="white")

    # Save thumbnail
    image.save(output_path)
