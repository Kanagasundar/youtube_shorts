import os
import logging
from datetime import datetime
from pathlib import Path
import moviepy.editor as mpe
from moviepy.config import change_settings
import numpy as np

# PIL compatibility fix
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
        logging.info("Applied PIL compatibility fix: Image.ANTIALIAS -> Image.Resampling.LANCZOS")
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
        
        # Pre-resize images
        logger.info(f"🖼️ Pre-processing {num_images} images...")
        clips = []
        for i, image_path in enumerate(image_paths):
            logger.info(f"🖼️ Loading image {i+1}: {image_path}")
            img = Image.open(image_path).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
            clip = mpe.ImageClip(np.array(img)).set_duration(duration_per_image)
            if i > 0:
                clip = clip.crossfadein(duration_per_image * 0.1)  # Reduced crossfade to 10%
            clips.append(clip)
        
        # Concatenate clips
        video = mpe.concatenate_videoclips(clips, method="compose", padding=-duration_per_image * 0.1)
        video = video.set_audio(audio)
        
        # Simplified gradient background
        def gradient_frame(t):
            r = int(25 + 20 * np.sin(t))
            g = int(25 + 20 * np.cos(t))
            b = int(112 + 20 * np.sin(t + 1))
            return np.array([[[r, g, b]] * 1080] * 1920, dtype=np.uint8)
        
        animated_bg = mpe.VideoClip(gradient_frame, duration=target_duration).resize((1080, 1920)).set_opacity(0.5)
        video = mpe.CompositeVideoClip([animated_bg, video])
        
        # Create subtitles with fallback for missing SubtitlesClip
        logger.info("📝 Generating subtitles...")
        words = script_text.split()
        subtitles = []
        current_time = 0
        word_duration = target_duration / max(len(words), 1)
        
        for word in words:
            subtitles.append(((current_time, current_time + word_duration), word))
            current_time += word_duration
        
        try:
            subtitle_clip = mpe.SubtitlesClip(subtitles, lambda txt: mpe.TextClip(
                txt,
                fontsize=70,
                color='white',
                stroke_color='black',
                stroke_width=1,
                size=(1080, None),
                method='caption',
                align='center'
            ).set_position(('center', 'bottom')).set_duration(word_duration).fadein(0.3).fadeout(0.3))
            video = mpe.CompositeVideoClip([video, subtitle_clip.set_duration(target_duration)])
        except AttributeError:
            logger.warning("⚠️ SubtitlesClip not available, skipping subtitles")
            # Fallback: Add a simple text overlay if subtitles fail
            try:
                text_clip = mpe.TextClip(
                    script_text[:50] + "..." if len(script_text) > 50 else script_text,
                    fontsize=50,
                    color='white',
                    bg_color='rgba(0, 0, 0, 0.5)',
                    size=(1080, 200),
                    method='caption',
                    align='center'
                ).set_position(('center', 'bottom')).set_duration(target_duration).fadein(0.5).fadeout(0.5)
                video = mpe.CompositeVideoClip([video, text_clip])
            except Exception as e:
                logger.warning(f"⚠️ Fallback text overlay failed: {str(e)}")

        # Minimal dynamic effects
        video = video.resize(lambda t: 1 + 0.05 * np.sin(t / 2))  # Reduced amplitude and frequency
        
        # Generate output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")
        
        # Write video with optimized settings
        logger.info(f"💾 Writing video to {output_path}...")
        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            bitrate="2000k",  # Reduced bitrate
            threads=2,  # Adjusted for runner
            fps=30,
            logger=None  # Disable MoviePy logging
        )
        
        # Clean up resources
        audio.close()
        video.close()
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