#!/usr/bin/env python3
"""
Video Creator - Creates YouTube Shorts videos with audio and visuals
"""

import os
import sys
from datetime import datetime
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import textwrap

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
        if os.path.exists(background_image_path):
            background = Image.open(background_image_path)
        else:
            # Create gradient background
            background = create_gradient_background(width, height)
    except:
        # Fallback to solid color background
        background = create_gradient_background(width, height)
    
    # Resize and crop to fit 9:16 aspect ratio
    background = resize_and_crop(background, width, height)
    
    # Add text overlay
    background_with_text = add_text_overlay(background, topic, script)
    
    # Convert PIL image to MoviePy clip
    image_array = mp.ImageClip(background_with_text, duration=duration)
    
    # Add subtle zoom effect for engagement
    zoom_clip = image_array.resize(lambda t: 1 + 0.1 * t / duration)
    
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

def resize_and_crop(image, target_width, target_height):
    """Resize and crop image to target dimensions"""
    
    # Calculate aspect ratios
    img_ratio = image.width / image.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        # Image is wider than target, crop width
        new_height = target_height
        new_width = int(new_height * img_ratio)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to center
        left = (new_width - target_width) // 2
        image = image.crop((left, 0, left + target_width, target_height))
    else:
        # Image is taller than target, crop height
        new_width = target_width
        new_height = int(new_width / img_ratio)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to center
        top = (new_height - target_height) // 2
        image = image.crop((0, top, target_width, top + target_height))
    
    return image

def add_text_overlay(image, title, script):
    """Add text overlay to image"""
    
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    try:
        # Try to load a nice font
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
    except:
        # Fallback to default font
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Add title at top
    title_wrapped = textwrap.fill(title, width=20)
    title_bbox = draw.textbbox((0, 0), title_wrapped, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    
    title_x = (width - title_width) // 2