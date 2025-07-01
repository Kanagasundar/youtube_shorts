import os
import logging
from datetime import datetime
from pathlib import Path
import moviepy.editor as mpe
from moviepy.config import change_settings
import time
import numpy as np

# PIL compatibility fix
try:
    from PIL import Image
    # For newer Pillow versions (10.0.0+), ANTIALIAS was removed
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
        logging.info("Applied PIL compatibility fix: Image.ANTIALIAS -> Image.LANCZOS")
except ImportError:
    pass

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

def create_video(audio_path: str, thumbnail_path: str, output_dir: str, script_text: str, max_retries: int = 5) -> str:
    """
    Create a YouTube Shorts video using a sequence of images and narration with professionally edited effects.
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
        
        # Determine number of images and target duration (15-60s)
        image_paths = thumbnail_path
        num_images = len(image_paths)
        target_duration = min(max(15, audio_duration), 60)
        duration_per_image = target_duration / num_images if num_images > 0 else target_duration
        
        # Create video clips from image sequence with crossfade transitions
        clips = []
        for i, image_path in enumerate(image_paths):
            logger.info(f"🖼️ Loading image {i+1}: {image_path}")
            clip = (mpe.ImageClip(image_path)
                   .set_duration(duration_per_image)
                   .resize((1080, 1920)))
            
            if i > 0:
                clip = clip.crossfadein(duration_per_image * 0.2)  # 20% crossfade
            clips.append(clip)
        
        # Concatenate clips with smooth transitions
        video = mpe.concatenate_videoclips(clips, method="compose", padding=-duration_per_image * 0.2)
        video = video.set_audio(audio)
        
        # Add animated gradient background
        def gradient_frame(t):
            r = int(25 + 40 * np.sin(t + 0))
            g = int(25 + 40 * np.cos(t + 2))
            b = int(112 + 40 * np.sin(t + 4))
            return np.array([[[r, g, b]] * 1080] * 1920, dtype=np.uint8)
        
        animated_bg = mpe.VideoClip(gradient_frame, duration=target_duration).resize((1080, 1920))
        video = mpe.CompositeVideoClip([animated_bg.set_opacity(0.7), video])
        
        # Split script into words for text overlays with animations
        words = script_text.split()
        text_clips = []
        current_time = 0
        time_per_word = target_duration / max(len(words), 1)
        
        for i, word in enumerate(words):
            for attempt in range(max_retries):
                try:
                    logger.info(f"📝 Creating text clip for word '{word}'...")
                    text_clip = mpe.TextClip(
                        word,
                        fontsize=60,
                        color='white',
                        stroke_color='black',
                        stroke_width=3,
                        font='Arial-Bold',
                        size=(900, 400),
                        method='caption',
                        align='center'
                    ).set_position(('center', 'bottom' if i % 2 == 0 else 'top'))
                    
                    def get_position(t):
                        x = 'center'
                        y = 1800 - 1400 * np.exp(-4 * t / time_per_word) if i % 2 == 0 else -200 + 1400 * np.exp(-4 * t / time_per_word)
                        return x, y
                    
                    text_clip = (text_clip
                               .set_start(current_time)
                               .set_duration(time_per_word)
                               .fadein(0.5)
                               .fadeout(0.5)
                               .set_position(get_position, relative=False))
                    
                    text_clips.append(text_clip)
                    logger.info(f"✅ Text clip created for '{word}' with effects")
                    break
                except Exception as e:
                    logger.error(f"❌ Failed to create text clip for word '{word}': {str(e)}")
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed. Retrying in {2 ** attempt}s...")
                        time.sleep(2 ** attempt)
                    else:
                        logger.error(f"❌ Failed after {max_retries} attempts for word '{word}'")
                        text_clip = mpe.ColorClip(
                            size=(1080, 400),
                            color=(0, 0, 0, 0),
                            duration=time_per_word
                        ).set_position(('center', 'bottom')).set_start(current_time).fadein(0.3).fadeout(0.3)
                        text_clips.append(text_clip)
                        logger.info(f"✅ Fallback blank clip created for '{word}'")
                        break
            current_time += time_per_word
        
        # Composite video with text overlays
        video = mpe.CompositeVideoClip([video] + text_clips)
        
        # Add final touch: Dynamic scaling and rotation
        video = (video
                .resize(lambda t: 1 + 0.1 * np.sin(t))
                .rotate(lambda t: 2 * np.sin(t), unit='deg'))
        
        # Generate sanitized output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")
        
        # Write video with high quality
        logger.info(f"💾 Writing video to {output_path}...")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=str(Path(output_dir) / f"temp-audio-{timestamp}.m4a"),
            remove_temp=True,
            fps=30,
            preset='medium',
            threads=4,
            bitrate='5000k'
        )
        
        # Clean up resources
        try:
            audio.close()
            for clip in clips + text_clips:
                clip.close()
            video.close()
        except Exception as e:
            logger.warning(f"⚠️ Error during resource cleanup: {e}")
        
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
        temp_files = [f for f in os.listdir() if f.startswith('temp-') or f.endswith('.m4a')]
        for file in temp_files:
            try:
                os.remove(file)
                logger.info(f"✅ Removed {file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {file}: {e}")
        logger.info(f"✅ Cleaned up {len(temp_files)} temporary files")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}", exc_info=True)