from PIL import Image, ImageDraw, ImageFont
import os

def generate_thumbnail(image_path, output_path, overlay_text=""):
    """Generate a thumbnail with text overlay. Creates a default image if source doesn't exist."""
    
    try:
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"Image not found at {image_path}, creating default thumbnail")
            # Create a default background image
            image = create_default_background()
        else:
            # Load and process existing image
            image = Image.open(image_path).convert("RGB")
            
        # Resize to YouTube thumbnail dimensions (1280x720)
        image = image.resize((1280, 720), Image.Resampling.LANCZOS)
        
        # Create overlay if text is provided
        if overlay_text:
            image = add_text_overlay(image, overlay_text)
        
        # Save thumbnail
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, "JPEG", quality=95)
        print(f"Thumbnail generated: {output_path}")
        
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        # Create a simple fallback thumbnail
        create_fallback_thumbnail(output_path, overlay_text)

def create_default_background():
    """Create a default background image with gradient"""
    width, height = 1280, 720
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Create a gradient background
    for y in range(height):
        # Create a gradient from dark blue to purple
        r = int(30 + (y / height) * 50)   # 30 to 80
        g = int(20 + (y / height) * 30)   # 20 to 50  
        b = int(80 + (y / height) * 100)  # 80 to 180
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return image

def add_text_overlay(image, text):
    """Add text overlay to image"""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    # Try to load a bold font
    font_size = 60
    try:
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/System/Library/Fonts/Arial.ttf',
            'C:/Windows/Fonts/arial.ttf'
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Word wrap text for better display
    words = text.upper().split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= width - 100:  # 50px margin on each side
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Calculate positioning
    line_height = font_size + 10
    total_height = len(lines) * line_height
    start_y = (height - total_height) // 2
    
    # Draw text with outline/shadow effect
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = start_y + i * line_height
        
        # Draw shadow/outline
        shadow_offset = 3
        for dx in [-shadow_offset, 0, shadow_offset]:
            for dy in [-shadow_offset, 0, shadow_offset]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill='black')
        
        # Draw main text
        draw.text((x, y), line, font=font, fill='white')
    
    return image

def create_fallback_thumbnail(output_path, text=""):
    """Create a simple fallback thumbnail"""
    try:
        image = create_default_background()
        
        if text:
            image = add_text_overlay(image, text)
        else:
            # Add default text
            image = add_text_overlay(image, "NEW VIDEO")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path, "JPEG", quality=95)
        print(f"Fallback thumbnail created: {output_path}")
        
    except Exception as e:
        print(f"Failed to create fallback thumbnail: {e}")

# For backward compatibility
def generate_thumbnail_old(image_path, output_path, overlay_text=""):
    """Legacy function name for backward compatibility"""
    generate_thumbnail(image_path, output_path, overlay_text)