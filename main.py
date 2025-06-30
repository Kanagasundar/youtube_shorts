import os
import logging
from dotenv import load_dotenv
from utils.scripting import generate_script
from utils.video import create_video
from utils.voice import generate_voice
from utils.youtube import upload_to_youtube

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check if required environment variables are set."""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing {len(missing_vars)} required environment variables:")
        for var in missing_vars:
            logger.error(f"    - {var}")
        logger.error("💡 Set environment variables:")
        logger.error("   export OPENAI_API_KEY=sk-your_openai_api_key_here")
        raise EnvironmentError("Environment variables check failed")
    logger.info("✅ All required environment variables are set")

def main():
    """Main function to run the YouTube automation pipeline."""
    logger.info("🤖 YouTube Automation Script - Enhanced Version")
    logger.info("============================================================")

    try:
        # Load environment variables
        load_dotenv()
        logger.info("🔍 Performing setup checks...")

        # Check environment variables
        logger.info("   Checking Environment Variables...")
        check_environment_variables()

        # Generate script
        topic = os.getenv('TOPIC_OVERRIDE', 'AI advancements in 2025')
        logger.info(f"✅ Topic: {topic}")
        script = generate_script(topic, length='short')
        if not script:
            logger.error("❌ Failed to generate script")
            return 1

        # Generate voice narration
        audio_path = generate_voice(script, topic)
        if not audio_path:
            logger.error("❌ Failed to generate voice narration")
            return 1

        # Generate thumbnail (placeholder, assuming a static image for now)
        thumbnail_path = 'thumbnail.jpg'  # Replace with actual thumbnail generation logic
        if not os.path.exists(thumbnail_path):
            logger.error(f"❌ Thumbnail file not found: {thumbnail_path}")
            return 1

        # Create video
        video_path = create_video(script, audio_path, thumbnail_path, topic)
        if not video_path:
            logger.error("❌ Failed to create video")
            return 1

        # Upload to YouTube
        if os.getenv('UPLOAD_TO_YOUTUBE', 'false').lower() == 'true':
            video_id = upload_to_youtube(video_path, topic)
            if video_id:
                logger.info(f"✅ Video uploaded with ID: {video_id}")
            else:
                logger.error("❌ Failed to upload video to YouTube")
                return 2  # Partial success (video created but upload failed)
        else:
            logger.info("ℹ️ Upload to YouTube disabled")
        
        logger.info("✅ Automation completed successfully")
        return 0

    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)