import os
import sys
from datetime import datetime
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import textwrap
import numpy as np

def create_video(script, audio_path, background_image_path, topic, output_dir="output"):
    """
    Create a YouTube Shorts video
    
    Args:
        script (str): The script text
        audio_path (str): Path to audio narration
        background_image_path (str): Path to background image
        topic (str): Video topic
        output_dir (str): Output directory
        
    Returns:
        str: Path to created video file
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_filename = f"youtube_short_{timestamp}.mp4"
    video_path = os.path.join(output_dir, video_filename)
    
    try:
        print(f"🎬 Creating video...")
        
        # Load audio to get duration
        audio_clip = mp.AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        print(f"⏱️ Video duration: {duration:.1f} seconds")
        
        # Create visual elements
        video_clip = create_visual_content(
            script, 
            background_image_path, 
            topic, 
            duration
        )
        
        # Combine video and audio
        final_video = video_clip.set_audio(audio_clip)
        
        # Optimize for YouTube Shorts
        final_video = optimize_for_shorts(final_video)
        
        # Export video
        print(f"📤 Exporting video...")
        final_video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        # Clean up
        audio_clip.close()
        video_clip.close()
        final_video.close()
        
        print(f"✅ Video created: {video_path}")
        return video_path
        
    except Exception as e:
        print(f"❌ Error creating video: {e}")
        
        # Try fallback method
        try:
            print("🔄 Trying fallback video creation...")
            return create_simple_video(script, audio_path, topic, output_dir)
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            raise Exception(f"Video creation failed: {e}")

def create_visual_content(script, background_image_path, topic, duration):
    """
    Create visual content for the video
    """
    
    # YouTube Shorts dimensions (9:16 aspect ratio)
    width, height = 1080, 1920
    
    try:
        # Try to use provided background image
        if background_image_path and os.path.exists(background_image_path):
            background = Image.open(background_image_path)
        else:
            # Create gradient background
            background = create_gradient_background(width, height)
    except Exception as e:
        print(f"⚠️ Could not load background image: {e}")
        # Fallback to solid color background
        background = create_gradient_background(width, height)
    
    # Resize and crop to fit 9:16 aspect ratio
    background = resize_and_crop(background, width, height)
    
    # Add text overlay
    background_with_text = add_text_overlay(background, topic, script)
    
    # Ensure we have a valid image
    if background_with_text is None:
        print("⚠️ Text overlay failed, using plain background")
        background_with_text = background
    
    # Convert PIL image to numpy array for MoviePy
    image_array = np.array(background_with_text)
    
    # Convert to MoviePy clip
    image_clip = mp.ImageClip(image_array, duration=duration)
    
    # Add subtle zoom effect for engagement
    zoom_clip = image_clip.resize(lambda t: 1 + 0.05 * t / duration)
    
    return zoom_clip

def create_gradient_background(width, height):
    """Create a gradient background"""
    
    # Create gradient from top to bottom
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Define gradient colors (dark blue to purple)
    start_color = (25, 25, 112)  # MidnightBlue
    end_color = (75, 0, 130)     # Indigo
    
    for y in range(height):
        # Calculate color at this position
        ratio = y / height
        r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
        
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return image

def get_pillow_resample_filter():
    """Get the appropriate resampling filter based on Pillow version"""
    try:
        # For Pillow >= 10.0.0
        return Image.Resampling.LANCZOS
    except AttributeError:
        try:
            # For Pillow 9.x
            return Image.LANCZOS
        except AttributeError:
            try:
                # For older Pillow versions that still have ANTIALIAS
                return Image.ANTIALIAS
            except AttributeError:
                # Last resort - use a numeric constant that should work
                return 1  # This is the value of LANCZOS/ANTIALIAS

def resize_and_crop(image, target_width, target_height):
    """Resize and crop image to target dimensions"""
    
    # Calculate aspect ratios
    img_ratio = image.width / image.height
    target_ratio = target_width / target_height
    
    # Get the appropriate resampling filter
    resample_filter = get_pillow_resample_filter()
    
    if img_ratio > target_ratio:
        # Image is wider than target, crop width
        new_height = target_height
        new_width = int(new_height * img_ratio)
        image = image.resize((new_width, new_height), resample_filter)
        
        # Crop to center
        left = (new_width - target_width) // 2
        image = image.crop((left, 0, left + target_width, target_height))
    else:
        # Image is taller than target, crop height
        new_width = target_width
        new_height = int(new_width / img_ratio)
        image = image.resize((new_width, new_height), resample_filter)
        
        # Crop to center
        top = (new_height - target_height) // 2
        image = image.crop((0, top, target_width, top + target_height))
    
    return image

def get_text_dimensions(draw, text, font):
    """Get text dimensions with fallback for different Pillow versions"""
    try:
        # For newer Pillow versions (8.0.0+)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        try:
            # For older Pillow versions
            return draw.textsize(text, font=font)
        except AttributeError:
            # Fallback estimation
            lines = text.split('\n')
            max_line_length = max(len(line) for line in lines) if lines else 0
            # Rough estimation: 10 pixels per character, 20 pixels per line
            return max_line_length * 10, len(lines) * 20

def draw_rounded_rectangle_fallback(draw, coords, radius, fill):
    """Draw rounded rectangle with fallback for older Pillow versions"""
    try:
        # For newer Pillow versions
        draw.rounded_rectangle(coords, radius=radius, fill=fill)
    except AttributeError:
        # Fallback: draw regular rectangle
        draw.rectangle(coords, fill=fill)

def add_text_overlay(image, title, script):
    """Add text overlay to image"""
    
    try:
        # Create a copy of the image
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        width, height = img_copy.size
        
        # Try to load fonts with better fallback handling
        try:
            # Try common system font paths
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
            ]
            
            title_font = None
            text_font = None
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        title_font = ImageFont.truetype(font_path, 60)
                        # Try to find regular version of the font
                        regular_font_path = font_path.replace('Bold', '').replace('-Bold', '')
                        if os.path.exists(regular_font_path):
                            text_font = ImageFont.truetype(regular_font_path, 40)
                        else:
                            text_font = ImageFont.truetype(font_path, 40)
                        break
                    except (OSError, IOError):
                        continue
            
            # If no system fonts found, use default
            if title_font is None:
                try:
                    title_font = ImageFont.load_default()
                    text_font = ImageFont.load_default()
                    print("⚠️ Using default fonts (may appear smaller)")
                except:
                    # Create minimal fallback fonts
                    title_font = ImageFont.load_default()
                    text_font = ImageFont.load_default()
                    
        except Exception as font_error:
            print(f"⚠️ Font loading error: {font_error}")
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Add title at top with background
        title_wrapped = textwrap.fill(title, width=25)
        
        # Calculate title position using compatible method
        title_width, title_height = get_text_dimensions(draw, title_wrapped, title_font)
        
        title_x = (width - title_width) // 2
        title_y = 150
        
        # Add semi-transparent background for title
        padding = 30
        bg_left = max(0, title_x - padding)
        bg_top = max(0, title_y - padding)
        bg_right = min(width, title_x + title_width + padding)
        bg_bottom = min(height, title_y + title_height + padding)
        
        # Create overlay for background
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw rounded rectangle background with fallback
        draw_rounded_rectangle_fallback(
            overlay_draw,
            [bg_left, bg_top, bg_right, bg_bottom],
            20,
            (0, 0, 0, 128)  # Semi-transparent black
        )
        
        # Composite overlay onto image
        img_copy = Image.alpha_composite(img_copy.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img_copy)
        
        # Draw title text
        draw.text((title_x, title_y), title_wrapped, font=title_font, fill=(255, 255, 255))
        
        # Add script text at bottom (first few lines)
        script_lines = textwrap.fill(script[:200] + "...", width=35).split('\n')[:4]
        script_text = '\n'.join(script_lines)
        
        # Calculate script position
        script_width, script_height = get_text_dimensions(draw, script_text, text_font)
        
        script_x = (width - script_width) // 2
        script_y = height - script_height - 200
        
        # Add background for script text
        script_bg_left = max(0, script_x - padding)
        script_bg_top = max(0, script_y - padding)
        script_bg_right = min(width, script_x + script_width + padding)
        script_bg_bottom = min(height, script_y + script_height + padding)
        
        # Create overlay for script background
        overlay2 = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay2_draw = ImageDraw.Draw(overlay2)
        
        draw_rounded_rectangle_fallback(
            overlay2_draw,
            [script_bg_left, script_bg_top, script_bg_right, script_bg_bottom],
            15,
            (0, 0, 0, 100)  # Semi-transparent black
        )
        
        # Composite second overlay
        img_copy = Image.alpha_composite(img_copy.convert('RGBA'), overlay2).convert('RGB')
        draw = ImageDraw.Draw(img_copy)
        
        # Draw script text
        draw.text((script_x, script_y), script_text, font=text_font, fill=(255, 255, 255))
        
        return img_copy
        
    except Exception as e:
        print(f"⚠️ Error adding text overlay: {e}")
        return image  # Return original image if text overlay fails

def create_simple_video(script, audio_path, topic, output_dir):
    """
    Fallback method to create a simple video with just colored background and text
    """
    
    print("🎬 Creating simple fallback video...")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_filename = f"youtube_short_simple_{timestamp}.mp4"
    video_path = os.path.join(output_dir, video_filename)
    
    try:
        # Load audio to get duration
        audio_clip = mp.AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # Create simple colored background
        width, height = 1080, 1920
        background = create_gradient_background(width, height)
        
        # Add text
        background_with_text = add_text_overlay(background, topic, script)
        
        # Convert to numpy array
        image_array = np.array(background_with_text)
        
        # Create video clip
        video_clip = mp.ImageClip(image_array, duration=duration)
        
        # Combine with audio
        final_video = video_clip.set_audio(audio_clip)
        
        # Export
        final_video.write_videofile(
            video_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        # Clean up
        audio_clip.close()
        video_clip.close()
        final_video.close()
        
        print(f"✅ Simple video created: {video_path}")
        return video_path
        
    except Exception as e:
        print(f"❌ Simple video creation also failed: {e}")
        raise e

def optimize_for_shorts(video_clip):
    """
    Optimize video for YouTube Shorts
    """
    
    # Ensure 9:16 aspect ratio (1080x1920)
    target_width, target_height = 1080, 1920
    
    # Get current dimensions
    current_width, current_height = video_clip.size
    
    if (current_width, current_height) != (target_width, target_height):
        # Resize if needed
        video_clip = video_clip.resize((target_width, target_height))
    
    # Ensure duration is appropriate for Shorts (max 60 seconds)
    if video_clip.duration > 60:
        video_clip = video_clip.subclip(0, 60)
    
    return video_clip