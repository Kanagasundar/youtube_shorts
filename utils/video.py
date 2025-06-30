import os
import logging
from datetime import datetime
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from PIL import Image
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_video(script: str, audio_path: str, thumbnail_path: str, topic: str) -> Optional[str]:
    """
    Create a YouTube Shorts video from script, audio, and thumbnail.
    
    Args:
        script (str): The video script
        audio_path (str): Path to the narration audio file
        thumbnail_path (str): Path to the thumbnail image
        topic (str): The video topic
    
    Returns:
        Optional[str]: Path to the generated video file or None if failed
    """
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    video_path = os.path.join(output_dir, f'youtube_short_{timestamp}.mp4')
    simple_video_path = os.path.join(output_dir, f'youtube_short_simple_{timestamp}.mp4')

    try:
        logger.info("🎬 Creating video...")
        start_time = datetime.now()

        # Load audio
        audio = VideoFileClip(audio_path)
        duration = audio.duration
        logger.info(f"⏱️ Video duration: {duration:.1f} seconds")

        # Load thumbnail and resize
        with Image.open(thumbnail_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to 1080x1920 (YouTube Shorts resolution)
            img = img.resize((1080, 1920), Image.LANCZOS)  # Replaced ANTIALIAS with LANCZOS
            thumbnail_temp = os.path.join(output_dir, f'temp_thumbnail_{timestamp}.jpg')
            img.save(thumbnail_temp, 'JPEG')

        # Create video from thumbnail
        thumbnail_clip = VideoFileClip(thumbnail_temp).set_duration(duration)

        # Add text overlay (script)
        text_clip = TextClip(
            script,
            fontsize=40,
            color='white',
            font='Arial',
            size=(1080, 1920),
            method='caption',
            align='south'
        ).set_duration(duration)

        # Combine clips
        video = CompositeVideoClip([thumbnail_clip, text_clip.set_position('center')])

        # Add audio
        video = video.set_audio(audio)

        # Write video
        video.write_videofile(video_path, codec='libx264', audio_codec='aac', fps=24)
        logger.info(f"✅ Video created: {video_path}")

        # Clean up temporary files
        for temp_file in [thumbnail_temp]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"🧹 Removed temporary file: {temp_file}")

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️ Video creation took: {duration:.1f} seconds")

        return video_path

    except Exception as e:
        logger.error(f"❌ Error creating video: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        logger.info("🔄 Trying fallback video creation...")
        
        try:
            logger.info("🎬 Creating simple fallback video...")
            # Create a simple color background video
            color_clip = ColorClip(size=(1080, 1920), color=(0, 0, 255), duration=duration)
            text_clip = TextClip(
                script,
                fontsize=40,
                color='white',
                font='Arial',
                size=(1080, 1920),
                method='caption',
                align='south'
            ).set_duration(duration)
            
            video = CompositeVideoClip([color_clip, text_clip.set_position('center')])
            video = video.set_audio(VideoFileClip(audio_path))
            video.write_videofile(simple_video_path, codec='libx264', audio_codec='aac', fps=24)
            logger.info(f"✅ Simple video created: {simple_video_path}")
            return simple_video_path
        
        except Exception as fallback_e:
            logger.error(f"❌ Failed to create fallback video: {str(fallback_e)}")
            logger.debug("Stack trace:", exc_info=True)
            return None