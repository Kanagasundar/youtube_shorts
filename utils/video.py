#!/usr/bin/env python3
"""
Video creation utilities for YouTube Shorts automation
"""

import os
import logging
import cv2
import numpy as np
from pathlib import Path
import moviepy.editor as mpe
from moviepy.config import change_settings
from PIL import Image
import random
from datetime import datetime
import subprocess
from voice import fix_composite_audio_clips, debug_audio_clip, safe_write_videofile, fix_composite_video_clips

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set ImageMagick binary path
IMAGEMAGICK_BINARY = None
for path in ['/usr/bin/convert', '/usr/local/bin/convert', '/bin/convert']:
    if os.path.exists(path):
        IMAGEMAGICK_BINARY = path
        break

if IMAGEMAGICK_BINARY:
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
    logger.info(f"Found ImageMagick binary at: {IMAGEMAGICK_BINARY}")
else:
    logger.warning("ImageMagick binary not found, text rendering may fail")

def fix_clip_properties(clip: mpe.VideoClip, duration: float) -> mpe.VideoClip:
    """
    Fix clip properties to avoid _NoValueType errors by ensuring duration, start, and end are set correctly.
    
    Args:
        clip: MoviePy VideoClip object
        duration: Desired duration for the clip
    
    Returns:
        MoviePy VideoClip with fixed properties
    """
    try:
        if clip is None:
            logger.warning("Received None clip, creating black clip")
            clip = mpe.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)
        
        # Set duration if not set or invalid
        if not hasattr(clip, 'duration') or clip.duration is None or clip.duration <= 0:
            logger.info(f"Setting clip duration to {duration}")
            clip = clip.set_duration(duration)
        
        # Ensure start and end times
        if not hasattr(clip, 'start') or clip.start is None:
            clip = clip.set_start(0)
        
        # Log fixed properties for debugging
        logger.debug(f"Fixed clip properties: duration={clip.duration}, start={clip.start}, "
                    f"end={clip.start + clip.duration if clip.start is not None else 'NOT SET'}")
        
        return clip
    except Exception as e:
        logger.error(f"Failed to fix clip properties: {str(e)}", exc_info=True)
        # Fallback: return a black clip
        return mpe.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)

def create_safe_text_clip(text: str, duration: float, **kwargs) -> mpe.TextClip:
    """
    Create a TextClip with safe font handling and error recovery.
    
    Args:
        text: Text to display
        duration: Duration of the text clip
        **kwargs: Additional TextClip parameters (fontsize, color, etc.)
    
    Returns:
        MoviePy TextClip or None if creation fails
    """
    fonts = ['FreeSans', 'LiberationSans', 'Arial', 'Sans']
    for font in fonts:
        try:
            logger.debug(f"Attempting to create TextClip with font: {font}")
            text_clip = mpe.TextClip(
                text,
                font=font,
                fontsize=kwargs.get('fontsize', 60),
                color=kwargs.get('color', 'white'),
                stroke_color=kwargs.get('stroke_color', 'black'),
                stroke_width=kwargs.get('stroke_width', 1),
                size=kwargs.get('size', (1000, None)),
                method=kwargs.get('method', 'caption'),
                align=kwargs.get('align', 'center')
            )
            text_clip = fix_clip_properties(text_clip, max(float(duration), 0.1))
            logger.debug(f"Successfully created TextClip with font: {font}")
            return text_clip
        except Exception as e:
            logger.warning(f"Failed to create TextClip with font {font}: {str(e)}")
            continue
    logger.error(f"Could not create TextClip for text: {text}")
    return None

def add_overlays(image, text, logo_path=None, sticker_path=None):
    """
    Add text, logo, and sticker overlays to an image using OpenCV.
    
    Args:
        image: NumPy array of the image
        text (str): Text to overlay
        logo_path (str): Path to logo image
        sticker_path (str): Path to sticker image
    
    Returns:
        NumPy array with overlays
    """
    img = image.copy()
    h, w = img.shape[:2]
    
    # Log available fonts for debugging
    try:
        font_list = subprocess.check_output(['fc-list'], text=True)
        logger.info("Available fonts:")
        logger.info(font_list)
        if 'FreeSans' in font_list:
            logger.info("FreeSans font is available")
        if 'LiberationSans' in font_list:
            logger.info("LiberationSans font is available")
    except Exception as e:
        logger.warning(f"Failed to list fonts: {str(e)}")

    # Add text overlay with fallback fonts
    fonts = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_DUPLEX, cv2.FONT_HERSHEY_PLAIN]
    font = fonts[0]  # Default to SIMPLEX
    font_scale = 1.5
    font_color = (255, 255, 255)  # White text
    font_thickness = 2
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    text_x = (w - text_size[0]) // 2
    text_y = h - 50
    cv2.putText(img, text, (text_x, text_y), font, font_scale, (0, 0, 0), font_thickness + 2, cv2.LINE_AA)  # Black outline
    cv2.putText(img, text, (text_x, text_y), font, font_scale, font_color, font_thickness, cv2.LINE_AA)  # White text
    
    # Add logo (top-left corner)
    if logo_path and os.path.exists(logo_path):
        logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
        if logo is not None:
            logo_h, logo_w = logo.shape[:2]
            logo = cv2.resize(logo, (int(logo_w * 0.2), int(logo_h * 0.2)))
            logo_h, logo_w = logo.shape[:2]
            roi = img[10:10+logo_h, 10:10+logo_w]
            if logo.shape[2] == 4:  # Handle transparency
                alpha = logo[:, :, 3] / 255.0
                for c in range(3):
                    roi[:, :, c] = (1.0 - alpha) * roi[:, :, c] + alpha * logo[:, :, c]
            else:
                roi[:] = logo
            img[10:10+logo_h, 10:10+logo_w] = roi
    
    # Add sticker (top-right corner)
    if sticker_path and os.path.exists(sticker_path):
        sticker = cv2.imread(sticker_path, cv2.IMREAD_UNCHANGED)
        if sticker is not None:
            sticker_h, sticker_w = sticker.shape[:2]
            sticker = cv2.resize(sticker, (int(sticker_w * 0.2), int(sticker_h * 0.2)))
            sticker_h, sticker_w = sticker.shape[:2]
            roi = img[10:10+sticker_h, w-sticker_w-10:w-10]
            if sticker.shape[2] == 4:  # Handle transparency
                alpha = sticker[:, :, 3] / 255.0
                for c in range(3):
                    roi[:, :, c] = (1.0 - alpha) * roi[:, :, c] + alpha * sticker[:, :, c]
            else:
                roi[:] = sticker
            img[10:10+sticker_h, w-sticker_w-10:w-10] = roi
    
    return img

def create_caption_clip(text, duration):
    """
    Create animated caption using MoviePy TextClip with font fallbacks and duration validation.
    
    Args:
        text (str): Caption text
        duration (float): Duration of the caption
    
    Returns:
        MoviePy clip with animated caption
    """
    logger.info(f"Generating caption for text: '{text}' with duration: {duration}s")
    fonts = ['FreeSans', 'LiberationSans', 'Sans']  # Fallback fonts
    clip = None
    for font in fonts:
        try:
            logger.info(f"Attempting to use font: {font}")
            clip = mpe.TextClip(
                text,
                fontsize=60,
                color='white',
                stroke_color='black',
                stroke_width=1,
                size=(1000, None),
                method='caption',
                align='center',
                font=font
            )
            # Ensure duration is valid
            clip = clip.set_duration(max(float(duration), 0.1))  # Minimum 0.1s to avoid zero duration
            clip = clip.set_position(('center', 'bottom')).fadein(0.3).fadeout(0.3)
            logger.info(f"Successfully created caption with font: {font}")
            
            # Debug clip properties
            logger.info(f"🔍 Caption clip properties: duration={getattr(clip, 'duration', 'NOT SET')}, "
                       f"start={getattr(clip, 'start', 'NOT SET')}, "
                       f"end={getattr(clip, 'end', 'NOT SET')}")
            return clip
        except Exception as e:
            logger.warning(f"Failed to create caption with font {font}: {str(e)}")
            continue
    logger.error("Failed to create caption with any font")
    raise Exception("Could not create caption: No suitable font found")

def create_video(audio_path: str, image_paths: list, output_dir: str, script_text: str, max_retries: int = 5) -> str:
    """
    Create a YouTube Shorts video with overlays, transitions, captions, and 9:16 aspect ratio.
    
    Args:
        audio_path (str): Path to narration audio
        image_paths (list): List of image paths
        output_dir (str): Directory to save video
        script_text (str): Script text for captions
        max_retries (int): Maximum retry attempts
    
    Returns:
        str: Path to generated video
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🎬 Starting video creation (Attempt {attempt}/{max_retries})...")
            
            # Validate inputs
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            if not isinstance(image_paths, list) or not all(os.path.exists(p) for p in image_paths):
                raise FileNotFoundError(f"Image sequence not found or invalid: {image_paths}")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"✅ Created output directory: {output_dir}")
            
            # Load audio
            logger.info(f"🔊 Loading audio: {audio_path}")
            audio = mpe.AudioFileClip(audio_path)
            audio = fix_composite_audio_clips([audio])[0]  # Fix audio clip
            debug_audio_clip(audio, "Main Audio")
            audio_duration = audio.duration
            
            # Ensure video duration is 15-40 seconds
            target_duration = max(15, min(40, audio_duration))
            num_images = len(image_paths)
            
            # Calculate variable image durations (0.5-6s)
            if num_images > 0:
                min_duration_per_image = 0.5
                max_duration_per_image = 6.0
                durations = [random.uniform(min_duration_per_image, max_duration_per_image) for _ in range(num_images)]
                total_image_duration = sum(durations)
                if total_image_duration < target_duration:
                    scale_factor = target_duration / total_image_duration
                    durations = [d * scale_factor for d in durations]
                elif total_image_duration > target_duration:
                    scale_factor = target_duration / total_image_duration
                    durations = [min(d * scale_factor, max_duration_per_image) for d in durations]
            else:
                durations = [target_duration]
            
            # Process images with OpenCV
            logger.info(f"🖼️ Pre-processing {num_images} images...")
            clips = []
            logo_path = os.path.join(output_dir, "logo.png")  # Placeholder for logo
            sticker_path = os.path.join(output_dir, "sticker.png")  # Placeholder for sticker
            
            for i, (image_path, duration) in enumerate(zip(image_paths, durations)):
                logger.info(f"🖼️ Processing image {i+1}: {image_path}")
                # Load with PIL to preserve RGB
                img = Image.open(image_path).convert("RGB")
                img_w, img_h = img.size
                target_w, target_h = 1080, 1920
                if img_w / img_h > target_w / target_h:
                    new_w = int(target_h * img_w / img_h)
                    img = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
                    left = (new_w - target_w) // 2
                    img = img.crop((left, 0, left + target_w, target_h))
                else:
                    new_h = int(target_w * img_h / img_w)
                    img = img.resize((target_w, new_h), Image.Resampling.LANCZOS)
                    top = (new_h - target_h) // 2
                    img = img.crop((0, top, target_w, top + target_h))
                
                # Convert to NumPy array without BGR conversion
                img_np = np.array(img)
                logger.debug(f"Initial image shape: {img_np.shape}, dtype: {img_np.dtype}")
                logger.debug(f"Sample pixel (top-left): {img_np[0, 0]}")
                
                # Verify color channels
                if img_np.shape[2] != 3:
                    raise ValueError(f"Image {image_path} has unexpected channel count: {img_np.shape[2]}")
                if np.all(img_np[:, :, 2] > img_np[:, :, 0]) and np.all(img_np[:, :, 2] > img_np[:, :, 1]):
                    logger.warning(f"Potential blue dominance detected in image {image_path}")
                
                # Add overlays
                overlay_text = f"Part {i+1}: {script_text.split('.')[i % len(script_text.split('.'))].strip()}"
                img_np = add_overlays(img_np, overlay_text, logo_path, sticker_path)
                
                # Save intermediate debug image
                debug_path = os.path.join(output_dir, f"debug_frame_pre_cv2_{i+1}.png")
                cv2.imwrite(debug_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
                logger.info(f"🖼️ Saved pre-CV2 debug image: {debug_path}")
                
                # Convert to MoviePy clip
                clip = mpe.ImageClip(img_np).set_duration(duration)
                
                # Apply transitions
                if i > 0:
                    transition_type = random.choice(['fade', 'zoom', 'slide'])
                    if transition_type == 'fade':
                        clip = clip.crossfadein(0.5)
                    elif transition_type == 'zoom':
                        clip = clip.resize(lambda t: 1 + 0.1 * t / duration)
                    elif transition_type == 'slide':
                        clip = clip.set_position(lambda t: ('center', -100 + 100 * t / duration))
                
                clips.append(clip)
            
            # Concatenate clips
            logger.info("Concatenating image clips...")
            video = mpe.concatenate_videoclips(clips, method="compose", padding=-0.5)
            video = video.set_audio(audio)
            video = video.set_duration(target_duration)
            
            # Generate captions with MoviePy
            logger.info("📝 Generating captions...")
            words = script_text.split()
            word_duration = target_duration / max(len(words), 1)
            subtitles = []
            current_time = 0
            for word in words:
                subtitles.append(((current_time, current_time + word_duration), word))
                current_time += word_duration
            
            subtitle_clips = []
            for (start, end), word in subtitles:
                try:
                    caption_clip = create_safe_text_clip(
                        word,
                        duration=end - start,
                        fontsize=60,
                        color='white',
                        stroke_color='black',
                        stroke_width=1
                    )
                    if caption_clip:
                        caption_clip = caption_clip.set_start(start)
                        subtitle_clips.append(caption_clip)
                        logger.info(f"✅ Set caption '{word}' start time to {start:.2f}s")
                except Exception as e:
                    logger.error(f"Failed to create caption for word '{word}': {str(e)}")
                    continue
            
            # Fix subtitle clips to avoid _NoValueType errors
            subtitle_clips = [fix_clip_properties(clip, max(float(clip.duration), 0.1)) 
                             for clip in subtitle_clips if clip is not None]
            
            # Create composite video
            logger.info("🔄 Creating composite video with subtitles...")
            video = mpe.CompositeVideoClip([video] + subtitle_clips)
            
            # Fix all video clips in composite
            video.clips = fix_composite_video_clips(video.clips, fallback_duration=target_duration)
            
            # Ensure video audio is fixed
            if video.audio is not None:
                video.audio = fix_composite_audio_clips([video.audio])[0]
                debug_audio_clip(video.audio, "Final Video Audio")
            
            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")
            
            # Write video using safe_write_videofile
            logger.info(f"💾 Writing video to {output_path}...")
            success = safe_write_videofile(video, output_path,
                                          codec="libx264",
                                          audio_codec="aac",
                                          preset="medium",
                                          bitrate="4000k",
                                          threads=2,
                                          fps=30)
            
            if not success:
                raise RuntimeError("Failed to write video file")
            
            # Clean up resources
            audio.close()
            video.close()
            for clip in clips + subtitle_clips:
                clip.close()
            logger.info(f"✅ Video created successfully: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"❌ Failed to create video (Attempt {attempt}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries:
                logger.info(f"Retrying in 1.0s...")
                import time
                time.sleep(1.0)
            else:
                logger.error("❌ Max retries reached. Video creation failed.")
                # Save last processed image for debugging
                if 'img_np' in locals():
                    debug_path = os.path.join(output_dir, f"debug_last_frame.png")
                    cv2.imwrite(debug_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
                    logger.info(f"🖼️ Saved last processed frame for debugging: {debug_path}")
                return None

def cleanup():
    """
    Clean up temporary files.
    """
    try:
        logger.info("🧹 Cleaning up temporary files...")
        temp_files = [f for f in os.listdir() if f.startswith('temp-') or f.endswith('.m4a') or f.startswith('temp_caption')]
        for file in temp_files:
            try:
                os.remove(file)
                logger.info(f"✅ Removed {file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {file}: {e}")
        logger.info(f"✅ Cleaned up {len(temp_files)} temporary files")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    audio_path = "output/narration_20250704_084011.mp3"
    image_paths = [
        f"output/frame_20250704_084016_1.png",
        f"output/frame_20250704_084022_2.png",
        f"output/frame_20250704_084031_3.png",
        f"output/frame_20250704_084035_4.png",
        f"output/frame_20250704_084047_5.png"
    ]
    output_dir = "output"
    script_text = "AI just solved a 50-year-old problem"
    video_path = create_video(audio_path, image_paths, output_dir, script_text)
    if video_path:
        print(f"Video created at: {video_path}")
    else:
        print("Video creation failed.")