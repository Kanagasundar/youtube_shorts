import os
import logging
import moviepy.editor as mpe
from moviepy.config import change_settings
import time

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

def create_video(audio_path, thumbnail_path, output_path, script_text, max_retries=5):
    """
    Create a YouTube Shorts video with narration and text overlays.
    
    Args:
        audio_path (str): Path to the narration audio file.
        thumbnail_path (str): Path to the thumbnail image.
        output_path (str): Path to save the output video.
        script_text (str): Script text for text overlays.
        max_retries (int): Maximum number of retries for text clip creation.
    
    Returns:
        bool: True if video creation succeeds, False otherwise.
    """
    try:
        logger.info("🎬 Starting video creation...")
        logger.info(f"🔊 Loading audio: {audio_path}")
        audio = mpe.AudioFileClip(audio_path)
        duration = audio.duration

        logger.info(f"🖼️ Loading thumbnail: {thumbnail_path}")
        thumbnail = mpe.ImageClip(thumbnail_path).set_duration(duration)

        # Split script into words for text overlays
        words = script_text.split()
        text_clips = []
        current_time = 0
        time_per_word = duration / len(words)

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
                        size=(thumbnail.w, thumbnail.h // 4),
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
                        # Fallback: Create a blank clip to avoid breaking the video
                        text_clip = mpe.ColorClip(
                            size=(thumbnail.w, thumbnail.h // 4),
                            color=(0, 0, 0, 0),
                            duration=time_per_word
                        ).set_position(('center', 'bottom')).set_start(current_time)
                        text_clips.append(text_clip)
                        logger.info(f"✅ Fallback blank clip created for '{word}'")
                        break
            current_time += time_per_word

        # Composite video with thumbnail and text overlays
        video = mpe.CompositeVideoClip([thumbnail] + text_clips)
        video = video.set_audio(audio)

        logger.info(f"💾 Writing video to {output_path}...")
        video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            fps=24
        )
        video.close()
        audio.close()
        thumbnail.close()
        for clip in text_clips:
            clip.close()

        logger.info(f"✅ Video created successfully: {output_path}")
        return True

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