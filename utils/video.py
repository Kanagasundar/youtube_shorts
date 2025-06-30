import os
import logging
from datetime import datetime
from pathlib import Path
import moviepy.editor as mpe
from moviepy.config import change_settings

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
    Create a YouTube Shorts video with narration and text overlays.
    
    Args:
        audio_path (str): Path to the narration audio file.
        thumbnail_path (str): Path to the thumbnail image.
        output_dir (str): Directory to save the output video.
        script_text (str): Script text for text overlays.
        max_retries (int): Maximum number of retries for text clip creation.
    
    Returns:
        str: Path to the created video file, or False if creation fails.
    """
    try:
        logger.info("🎬 Starting video creation...")
        
        # Validate inputs
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not os.path.exists(thumbnail_path):
            raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_path}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"✅ Created output directory: {output_dir}")
        
        # Load audio
        logger.info(f"🔊 Loading audio: {audio_path}")
        audio = mpe.AudioFileClip(audio_path)
        duration = audio.duration
        
        # Load and resize thumbnail to YouTube Shorts resolution (1080x1920)
        logger.info(f"🖼️ Loading thumbnail: {thumbnail_path}")
        thumbnail = mpe.ImageClip(thumbnail_path).set_duration(duration).resize((1080, 1920))
        
        # Split script into words for text overlays
        words = script_text.split()
        text_clips = []
        current_time = 0
        time_per_word = duration / max(len(words), 1)  # Avoid division by zero
        
        for i, word in enumerate(words):
            for attempt in range(max_retries):
                try:
                    logger.info(f"📝 Creating text clip for word '{word}'...")
                    text_clip = mpe.TextClip(
                        word,
                        fontsize=50,
                        color='white',
                        stroke_color='black',
                        stroke_width=2,
                        font='Arial-Bold',
                        size=(1080, 1920 // 4),
                        method='caption',
                        align='center'
                    ).set_position(('center', 'bottom')).set_start(current_time).set_duration(time_per_word)
                    text_clips.append(text_clip)
                    logger.info(f"✅ Text clip created for '{word}'")
                    break
                except Exception as e:
                    logger.error(f"❌ Failed to create text clip for word '{word}': {str(e)}")
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed. Retrying in {2 ** attempt}s...")
                        time.sleep(2 ** attempt)
                    else:
                        logger.error(f"❌ Failed after {max_retries} attempts for word '{word}'")
                        # Fallback: Create a blank clip
                        text_clip = mpe.ColorClip(
                            size=(1080, 1920 // 4),
                            color=(0, 0, 0, 0),  # Transparent
                            duration=time_per_word
                        ).set_position(('center', 'bottom')).set_start(current_time)
                        text_clips.append(text_clip)
                        logger.info(f"✅ Fallback blank clip created for '{word}'")
                        break
            current_time += time_per_word
        
        # Composite video with thumbnail and text overlays
        logger.info("🎥 Compositing video...")
        video = mpe.CompositeVideoClip([thumbnail] + text_clips)
        video = video.set_audio(audio)
        
        # Generate sanitized output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")
        
        # Write video
        logger.info(f"💾 Writing video to {output_path}...")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=str(Path(output_dir) / f"temp-audio-{timestamp}.m4a"),
            remove_temp=True,
            fps=24,
            preset='medium',
            threads=4
        )
        
        # Clean up resources
        try:
            audio.close()
            thumbnail.close()
            for clip in text_clips:
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
                logger.warning(f"⚠️ Failed to remove {file}: {str(e)}")
        logger.info(f"✅ Cleaned up {len(temp_files)} temporary files")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}", exc_info=True)