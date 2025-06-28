#!/usr/bin/env python3
"""
Thumbnail Generator - Creates eye-catching thumbnails for YouTube videos
"""

import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import random

def generate_thumbnail(topic, category, output_dir="output"):
    """
    Generate an eye-catching thumbnail for YouTube Shorts
    
    Args:
        topic (str): Video topic
        category (str): Video category
        output_dir (str): Output directory
        
    Returns:
        str: Path to generated thumbnail
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    thumbnail_filename = f"thumbnail_{timestamp}.jpg"
    thumbnail_path = os.path.join(output_dir, thumbnail_filename)
    
    try:
        print(f"🖼️ Generating thumbnail for: {topic}")
        
        # YouTube thumbnail dimensions (16:9 aspect ratio)
        width, height = 1280, 720
        
        # Create background based on category
        background = create_category_background(category, width, height)
        
        # Add text overlay
        thumbnail = add_thumbnail_text(background, topic, category)
        
        # Add visual elements
        thumbnail = add_visual_elements(thumbnail, category)
        
        # Save thumbnail
        thumbnail.save(thumbnail_path, 'JPEG', quality=95, optimize=True)
        
        print(f"✅ Thumbnail generated: {thumbnail_path}")
        return thumbnail_path
        
    except Exception as e:
        print(f"❌ Error generating thumbnail: {e}")
        
        # Create fallback thumbnail
        return create_fallback_thumbnail(topic, category, output_dir)

def create_category_background(category, width, height):
    """Create background based on category"""
    
    # Define color schemes for different categories
    color_schemes = {
        "History": [(139, 69, 19), (205, 133, 63)],      # Brown to SandyBrown
        "Science": [(25, 25, 112), (65, 105, 225)],      # MidnightBlue to RoyalBlue
        "Technology": [(0, 0, 0), (105, 105, 105)],      # Black to DimGray
        "Mystery": [(72, 61, 139), (147, 112, 219)],     # DarkSlateBlue to MediumSlateBlue
        "Nature": [(34, 139, 34), (144, 238, 144)],      # ForestGreen to LightGreen
        "Space": [(25, 25, 112), (75, 0, 130)],          # MidnightBlue to Indigo
        "Health": [(220, 20, 60), (255, 182, 193)],      # Crimson to LightPink
        "Psychology": [(128, 0, 128), (221, 160, 221)],  # Purple to Plum
        "Entertainment": [(255, 20, 147), (255, 105, 180)], # DeepPink to HotPink
        "Food": [(255, 140, 0), (255, 215, 0)]           # DarkOrange to Gold
    }
    
    # Get colors for category or use default
    start_color, end_color = color_schemes.get(category, [(25, 25, 112), (65, 105, 225)])
    
    # Create gradient background
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Create diagonal gradient
    for y in range(height):
        for x in range(width):
            # Calculate position ratio (0.0 to 1.0)
            ratio = (x + y) / (width + height)
            
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            
            draw.point((x, y), (r, g, b))
    
    return image

def add_thumbnail_text(image, topic, category):
    """Add text overlay to thumbnail"""
    
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    try:
        # Try to load fonts
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        category_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except:
        # Fallback to default font with larger size
        try:
            title_font = ImageFont.load_default()
            category_font = ImageFont.load_default()
        except:
            # Last resort - create dummy font objects
            title_font = None
            category_font = None
    
    # Prepare topic text (make it catchy)
    topic_words = topic.split()
    if len(topic_words) > 6:
        # Truncate long titles
        topic_short = ' '.join(topic_words[:6]) + "..."
    else:
        topic_short = topic
    
    # Wrap text
    wrapped_title = textwrap.fill(topic_short, width=20)
    
    if title_font:
        # Get text dimensions
        title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
    else:
        # Estimate dimensions
        title_width = len(wrapped_title) * 20
        title_height = wrapped_title.count('\n') * 30 + 30
    
    # Position title in center
    title_x = (width - title_width) // 2
    title_y = (height - title_height) // 2
    
    # Add semi-transparent background for better readability
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Create background rectangle for text
    padding = 20
    rect_coords = [
        title_x - padding,
        title_y - padding,
        title_x + title_width + padding,
        title_y + title_height + padding
    ]
    overlay_draw.rounded_rectangle(rect_coords, radius=15, fill=(0, 0, 0, 150))
    
    # Blend overlay with main image
    image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(image)
    
    # Draw title with outline
    draw_text_with_outline(draw, (title_x, title_y), wrapped_title, title_font, 'white', 'black', 3)
    
    # Add category badge
    category_text = f"🔥 {category.upper()}"
    if category_font:
        cat_bbox = draw.textbbox((0, 0), category_text, font=category_font)
        cat_width = cat_bbox[2] - cat_bbox[0]
    else:
        cat_width = len(category_text) * 12
    
    cat_x = width - cat_width - 30
    cat_y = 30
    
    # Draw category badge background
    badge_coords = [cat_x - 15, cat_y - 10, cat_x + cat_width + 15, cat_y + 40]
    draw.rounded_rectangle(badge_coords, radius=20, fill='red')
    
    # Draw category text
    draw_text_with_outline(draw, (cat_x, cat_y), category_text, category_font, 'white', 'black', 2)
    
    return image

def add_visual_elements(image, category):
    """Add visual elements like emojis and effects"""
    
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    # Add category-specific emojis/symbols
    emoji_map = {
        "History": "⏳📜🏛️",
        "Science": "🔬⚗️🧪",
        "Technology": "💻🤖⚡",
        "Mystery": "🔍❓👻",
        "Nature": "🌿🦋🌍",
        "Space": "🚀🌟🛸",
        "Health": "💊❤️🏥",
        "Psychology": "🧠💭🤔",
        "Entertainment": "🎬🎭🎪",
        "Food": "🍔🍕🍰"
    }
    
    emojis = emoji_map.get(category, "🤯💥⚡")
    
    # Try to add emoji text (might not render properly on all systems)
    try:
        emoji_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        
        # Add emojis in corners
        draw.text((50, 50), emojis[0], font=emoji_font, fill='white')
        draw.text((width - 100, 50), emojis[1], font=emoji_font, fill='white')
        draw.text((50, height - 100), emojis[2], font=emoji_font, fill='white')
        
    except:
        # Fallback: add colored circles as decorative elements
        colors = ['red', 'yellow', 'cyan', 'lime', 'orange']
        for i in range(5):
            x = random.randint(0, width - 50)
            y = random.randint(0, height - 50)
            color = random.choice(colors)
            draw.ellipse([x, y, x + 30, y + 30], fill=color)
    
    # Add "VIRAL" or "SHOCKING" text for engagement
    impact_words = ["🤯 VIRAL", "😱 SHOCKING", "🔥 TRENDING", "💥 AMAZING"]
    impact_text = random.choice(impact_words)
    
    try:
        impact_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except:
        impact_font = None
    
    # Position impact text
    impact_x = 50
    impact_y = height - 150
    
    # Add background for impact text
    if impact_font:
        impact_bbox = draw.textbbox((0, 0), impact_text, font=impact_font)
        impact_width = impact_bbox[2] - impact_bbox[0]
        impact_height = impact_bbox[3] - impact_bbox[1]
    else:
        impact_width = len(impact_text) * 15
        impact_height = 25
    
    impact_coords = [
        impact_x - 10,
        impact_y - 10,
        impact_x + impact_width + 10,
        impact_y + impact_height + 10
    ]
    draw.rounded_rectangle(impact_coords, radius=15, fill='yellow')
    
    # Draw impact text
    draw_text_with_outline(draw, (impact_x, impact_y), impact_text, impact_font, 'black', 'white', 2)
    
    return image

def draw_text_with_outline(draw, position, text, font, fill_color, outline_color, outline_width=2):
    """Draw text with outline for better visibility"""
    x, y = position
    
    if font is None:
        # Fallback to simple text without outline
        draw.text((x, y), text, fill=fill_color)
        return
    
    # Draw outline
    for adj_x in range(-outline_width, outline_width + 1):
        for adj_y in range(-outline_width, outline_width + 1):
            if adj_x != 0 or adj_y != 0:
                draw.text((x + adj_x, y + adj_y), text, font=font, fill=outline_color)
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_color)

def create_fallback_thumbnail(topic, category, output_dir):
    """Create a simple fallback thumbnail"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    thumbnail_filename = f"thumbnail_fallback_{timestamp}.jpg"
    thumbnail_path = os.path.join(output_dir, thumbnail_filename)
    
    try:
        # Create simple colored background
        width, height = 1280, 720
        image = Image.new('RGB', (width, height), color=(25, 25, 112))
        draw = ImageDraw.Draw(image)
        
        # Add simple text
        text = topic[:50] + "..." if len(topic) > 50 else topic
        
        # Center the text
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            font = None
            text_width = len(text) * 20
            text_height = 30
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text
        if font:
            draw.text((x, y), text, font=font, fill='white')
        else:
            draw.text((x, y), text, fill='white')
        
        # Save
        image.save(thumbnail_path, 'JPEG', quality=95)
        
        print(f"✅ Fallback thumbnail created: {thumbnail_path}")
        return thumbnail_path
        
    except Exception as e:
        print(f"❌ Fallback thumbnail creation failed: {e}")
        raise

def test_thumbnail_generation():
    """Test thumbnail generation"""
    
    test_cases = [
        ("The Day Photography Changed History Forever", "History"),
        ("Scientists Accidentally Created Time Crystals", "Science"),
        ("The Ship That Reappeared After 90 Years", "Mystery"),
        ("AI Just Solved a 50-Year-Old Problem", "Technology"),
        ("Trees Can Actually Talk to Each Other", "Nature")
    ]
    
    print("🧪 Testing thumbnail generation...")
    
    for topic, category in test_cases:
        print(f"\n📝 Testing: {topic} ({category})")
        thumbnail_path = generate_thumbnail(topic, category)
        
        if os.path.exists(thumbnail_path):
            print(f"✅ Success: {thumbnail_path}")
        else:
            print(f"❌ Failed: {topic}")

if __name__ == "__main__":
    test_thumbnail_generation()