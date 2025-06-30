import os
import logging
import shutil
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
from moviepy.config import change_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dynamically detect ImageMagick binary
def find_imagemagick_binary():
    """Find the ImageMagick binary path."""
    possible_paths = ['/usr/bin/magick', '/usr/bin/convert', '/usr/local/bin/magick', '/usr/local/bin/convert']
    for path in possible_paths:
        if shutil.which(path):
            logger.info(f"Found ImageMagick binary at: {path}")
            return path
    logger.error("❌ ImageMagick binary not found. Text rendering will fail.")
    return None

# Configure ImageMagick for MoviePy
IMAGEMAGICK_BINARY = find_imagemagick_binary()
if IMAGEMAGICK_BINARY:
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

def create_video(script, audio_path, thumbnail_path, topic, output_dir="output"):
    """
    Create a video by combining script, audio, and thumbnail.
    
    Args:
        script (str): The script text for the video.
        audio_path (str): Path to the audio narration file.
        thumbnail_path (str): Path to the thumbnail image.
        topic (str): Topic of the video for naming.
        output_dir (str): Directory to save the output video.
    
    Returns:
        str: Path to the created video file, or None if failed.
    """
    try:
        logger.info("🎬 Starting video creation...")

        # Validate audio file
        if not os.path.exists(audio_path):
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        if not audio_path.lower().endswith(('.mp3', '.wav')):
            logger.error(f"❌ Invalid audio file format: {audio_path}")
            return None

        # Validate thumbnail
        if not os.path.exists(thumbnail_path):
            logger.error(f"❌ Thumbnail file not found: {thumbnail_path}")
            return None
        if not thumbnail_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.error(f"❌ Invalid thumbnail format: {thumbnail_path}")
            return None

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{topic.replace(' ', '_')}_video.mp4")

        # Load audio
        logger.info(f"🔊 Loading audio: {audio_path}")
        try:
            audio = AudioFileClip(audio_path, fps=44100)
        except Exception as e:
            logger.error(f"❌ Failed to load audio: {str(e)}")
            return None

        # Create text clips from script
        text_clips = []
        words = script.split()
        duration_per_word = audio.duration / len(words)
        for i, word in enumerate(words):
            try:
                if not IMAGEMAGICK_BINARY:
                    logger.error("❌ ImageMagick not available. Skipping text clip creation.")
                    audio.close()
                    return None
                text_clip = TextClip(
                    word,
                    fontsize=70,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    font='Arial',
                    size=(1280, 720)
                ).set_duration(duration_per_word).set_position('center').set_start(i * duration_per_word)
                text_clips.append(text_clip)
            except Exception as e:
                logger.error(f"❌ Failed to create text clip for word '{word}': {str(e)}")
                audio.close()
                for clip in text_clips:
                    clip.close()
                return None

        # Load thumbnail as background
        logger.info(f"🖼️ Loading thumbnail as background: {thumbnail_path}")
        try:
            background = VideoFileClip(thumbnail_path).set_duration(audio.duration)
            background = background.resize((1280, 720))
        except Exception as e:
            logger.error(f"❌ Failed to load thumbnail: {str(e)}")
            audio.close()
            for clip in text_clips:
                clip.close()
            return None

        # Combine video and audio
        logger.info("🎥 Combining video elements...")
        try:
            video = CompositeVideoClip([background] + text_clips)
            video = video.set_audio(audio)
            video.write(output_path, codec='libx264', audio_codec='aac')
            logger.info(f"✅ Video created successfully: {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create video: {str(e)}")
            video.close()
            audio.close()
            background.close()
            for clip in text_clips:
                clip.close()
            return None

        # Clean up
        video.close()
        audio.close()
        background.close()
        for clip in text_clips:
            clip.close()

        return output_path

    except Exception as e:
        logger.error(f"❌ Unexpected error in video creation: {str(e)}", exc_info=True)
        return None