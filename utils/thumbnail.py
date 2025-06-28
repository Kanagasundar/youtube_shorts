from PIL import Image, ImageDraw, ImageFont
import textwrap
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_thumbnail_text(topic):
    prompt = f"Write a short, viral, 5-word YouTube thumbnail text for a video about: '{topic}'. Make it emotional or curiosity-driven."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def create_thumbnail(topic, bg_img=None, output_path="output/thumbnail.jpg"):
    text = generate_thumbnail_text(topic)

    if bg_img and os.path.exists(bg_img):
        img = Image.open(bg_img).resize((1280, 720))
    else:
        img = Image.new("RGB", (1280, 720), color=(20, 20, 20))

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(text, width=20)
    text_width, text_height = draw.textsize(wrapped, font=font)
    x = (1280 - text_width) // 2
    y = (720 - text_height) // 2

    draw.text((x, y), wrapped, fill="white", font=font)
    img.save(output_path)
