import os
import logging
import cv2
import numpy as np
from pathlib import Path
import moviepy.editor as mpe
from moviepy.config import change_settings
from PIL import Image
from manim import *
import random
from datetime import datetime  # Added import to fix NameError

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
    logger.warning("ImageMagick binary not found, text rendering may rely on Manim")

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
    
    # Add text overlay
    font = cv2.FONT_HERSHEY_SIMPLEX
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
                    roi[:, :, c] = roi[:, :, c] * (1 - alpha) + logo[:, :, c] * alpha
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
                    roi[:, :, c] = roi[:, :, c] * (1 - alpha) + sticker[:, :, c] * alpha
            else:
                roi[:] = sticker
            img[10:10+sticker_h, w-sticker_w-10:w-10] = roi
    
    return img

def create_caption_clip(text, duration):
    """
    Create animated caption using Manim.
    
    Args:
        text (str): Caption text
        duration (float): Duration of the caption
    
    Returns:
        MoviePy clip with animated caption
    """
    class CaptionScene(Scene):
        def construct(self):
            caption = Text(text, font="Arial", font_size=40, color=WHITE)
            caption.move_to(ORIGIN)
            self.add(caption)
            self.wait(duration)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/temp_caption_{timestamp}.mp4"
    try:
        config.output_file = output_file
        config.transparent = False  # Disable transparency to avoid serialization issues
        config.resolution = (1080, 1920)
        config.quality = "medium_quality"  # Reduce rendering complexity
        scene = CaptionScene()
        scene.render()
        logger.info(f"✅ Caption clip created: {output_file}")
        return mpe.VideoFileClip(output_file).set_duration(duration).set_position(('center', 'bottom'))
    except Exception as e:
        logger.warning(f"⚠️ Manim caption generation failed: {str(e)}")
        # Fallback to MoviePy TextClip
        logger.info("Falling back to MoviePy TextClip for caption")
        return mpe.TextClip(
            text,
            fontsize=60,
            color='white',
            stroke_color='black',
            stroke_width=1,
            size=(1000, None),
            method='caption',
            align='center',
            font='Arial'  # Use Arial instead of Courier
        ).set_duration(duration).set_position(('center', 'bottom')).fadein(0.3).fadeout(0.3)

def create_video(audio_path: str, thumbnail_path: list, output_dir: str, script_text: str, max_retries: int = 5) -> str:
    """
    Create a YouTube Shorts video with overlays, transitions, captions, and 9:16 aspect ratio.
    
    Args:
        audio_path (str): Path to narration audio
        thumbnail_path (list): List of image paths
        output_dir (str): Directory to save video
        script_text (str): Script text for captions
        max_retries (int): Maximum retry attempts
    
    Returns:
        str: Path to generated video
    """
    try:
        logger.info("🎬 Starting video creation...")
        
        # Validate inputs
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not isinstance(thumbnail_path, list) or not all(os.path.exists(p) for p in thumbnail_path):
            raise FileNotFoundError(f"Image sequence not found or invalid: {thumbnail_path}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"✅ Created output directory: {output_dir}")
        
        # Load audio
        logger.info(f"🔊 Loading audio: {audio_path}")
        audio = mpe.AudioFileClip(audio_path)
        audio_duration = audio.duration
        
        # Ensure video duration is 15-40 seconds
        target_duration = max(15, min(40, audio_duration))
        image_paths = thumbnail_path
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
            # Load and resize to 9:16 (1080x1920)
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
            
            # Convert to NumPy array for OpenCV
            img_np = np.array(img)
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            # Add overlays
            overlay_text = f"Part {i+1}: {script_text.split('.')[i % len(script_text.split('.'))].strip()}"
            img_np = add_overlays(img_np, overlay_text, logo_path, sticker_path)
            
            # Save debug image
            debug_path = os.path.join(output_dir, f"debug_frame_{i+1}.png")
            cv2.imwrite(debug_path, img_np)
            logger.info(f"🖼️ Saved debug image: {debug_path}")
            
            # Convert back to MoviePy clip
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
        video = mpe.concatenate_videoclips(clips, method="compose", padding=-0.5)
        video = video.set_audio(audio)
        video = video.set_duration(target_duration)
        
        # Generate animated captions with Manim
        logger.info("📝 Generating captions...")
        words = script_text.split()
        word_duration = target_duration / max(len(words), 1)
        subtitles = []
        current_time = 0
        for word in words:
            subtitles.append(((current_time, current_time + word_duration), word))
            current_time += word_duration
        
        try:
            subtitle_clips = []
            for (start, end), word in subtitles:
                caption_clip = create_caption_clip(word, end - start)
                caption_clip = caption_clip.set_start(start)
                subtitle_clips.append(caption_clip)
            video = mpe.CompositeVideoClip([video] + subtitle_clips)
        except Exception as e:
            logger.warning(f"⚠️ Caption compositing failed: {str(e)}")
            # Fallback to MoviePy TextClip
            logger.info("Falling back to MoviePy TextClip for subtitles")
            subtitle_clips = [
                mpe.TextClip(
                    word,
                    fontsize=60,
                    color='white',
                    stroke_color='black',
                    stroke_width=1,
                    size=(1000, None),
                    method='caption',
                    align='center',
                    font='Arial'  # Use Arial instead of Courier
                ).set_position(('center', 'bottom')).set_start(start).set_duration(end - start).fadein(0.3).fadeout(0.3)
                for (start, end), word in subtitles
            ]
            video = mpe.CompositeVideoClip([video] + subtitle_clips)
        
        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")
        
        # Write video
        logger.info(f"💾 Writing video to {output_path}...")
        video.write_videofile(
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            bitrate="4000k",
            threads=2,
            fps=30,
            logger=None
        )
        
        # Clean up resources
        audio.close()
        video.close()
        for clip in subtitle_clips:
            clip.close()
        if os.path.exists(output_file):
            os.remove(output_file)
        logger.info(f"✅ Video created successfully: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"❌ Failed to create video: {str(e)}", exc_info=True)
        return False

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