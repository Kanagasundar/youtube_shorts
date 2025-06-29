#!/usr/bin/env python3
"""
YouTube Automation Main Script
Generates and uploads daily YouTube Shorts content
"""

import os
import sys
import traceback
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the utils directory is in sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils'))

# Import modules from the utils directory
try:
    from topic_rotator import get_today_topic
    from scripting import generate_script
    from voice import generate_voice
    from video import create_video
    from thumbnail_generator import generate_thumbnail
    from youtube_uploader import YouTubeUploader, generate_video_metadata
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)

def main():
    """Main function to orchestrate the entire process"""
    logger.info("🚀 Starting YouTube Automation...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Get today's topic
        logger.info("📝 Step 1: Getting today's topic...")
        print("\n" + "="*50)
        print("📝 Step 1: Getting today's topic...")
        print("="*50)
        
        topic, category = get_today_topic()
        logger.info(f"✅ Topic: {topic}, Category: {category}")
        print(f"✅ Topic: {topic}")
        print(f"✅ Category: {category}")
        
        # Step 2: Generate script
        logger.info("✍️ Step 2: Generating script...")
        print("\n" + "="*50)
        print("✍️ Step 2: Generating script...")
        print("="*50)
        
        script = generate_script(topic, category)
        logger.info(f"✅ Generated script ({len(script)} characters)")
        print(f"✅ Generated script ({len(script)} characters)")
        print(f"📄 Script preview: {script[:200]}...")
        
        # Step 3: Generate voice narration
        logger.info("🎙️ Step 3: Generating voice narration...")
        print("\n" + "="*50)
        print("🎙️ Step 3: Generating voice narration...")
        print("="*50)
        
        audio_path = generate_voice(script)
        logger.info(f"✅ Audio generated: {audio_path}")
        print(f"✅ Audio generated: {audio_path}")
        
        # Step 4: Generate thumbnail
        logger.info("🖼️ Step 4: Generating thumbnail...")
        print("\n" + "="*50)
        print("🖼️ Step 4: Generating thumbnail...")
        print("="*50)
        
        thumbnail_path = generate_thumbnail(topic, category)
        logger.info(f"✅ Thumbnail generated: {thumbnail_path}")
        print(f"✅ Thumbnail generated: {thumbnail_path}")
        
        # Step 5: Create video
        logger.info("🎬 Step 5: Creating video...")
        print("\n" + "="*50)
        print("🎬 Step 5: Creating video...")
        print("="*50)
        
        video_path = create_video(script, audio_path, thumbnail_path, topic)
        logger.info(f"✅ Video created: {video_path}")
        print(f"✅ Video created: {video_path}")
        
        # Step 6: Upload to YouTube
        logger.info("📤 Step 6: Uploading to YouTube...")
        print("\n" + "="*50)
        print("📤 Step 6: Uploading to YouTube...")
        print("="*50)
        
        # Check if we should upload (can be disabled for testing)
        upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
        
        if not upload_enabled:
            logger.warning("⚠️ Upload disabled (UPLOAD_TO_YOUTUBE=false)")
            print("⚠️ Upload disabled (UPLOAD_TO_YOUTUBE=false)")
            print(f"📁 Video saved locally: {video_path}")
            print(f"📁 Thumbnail saved locally: {thumbnail_path}")
            print("✅ Automation completed (upload skipped)")
            return 0
        
        # Initialize uploader
        uploader = YouTubeUploader()
        
        if uploader.youtube:
            # Generate metadata
            title, description, tags = generate_video_metadata(topic, category, script)
            
            logger.info(f"📝 Title: {title}")
            logger.info(f"🏷️ Tags: {', '.join(tags[:5])}...")
            print(f"📝 Title: {title}")
            print(f"🏷️ Tags: {', '.join(tags[:5])}...")
            
            # Upload video
            video_id = uploader.upload_video(
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                title=title,
                description=description,
                tags=tags
            )
            
            if video_id:
                logger.info(f"🎉 SUCCESS! Video uploaded with ID: {video_id}")
                print(f"\n🎉 SUCCESS! Video uploaded!")
                print(f"📺 Video ID: {video_id}")
                print(f"🔗 Watch at: https://www.youtube.com/watch?v={video_id}")
                print(f"🔗 YouTube Shorts: https://youtube.com/shorts/{video_id}")
                
                # Save upload info
                save_upload_info(video_id, title, topic, category, video_path, thumbnail_path)
                
            else:
                logger.error("❌ Video upload failed")
                print("❌ Video upload failed")
                return 1
        else:
            logger.error("❌ YouTube authentication failed - cannot upload")
            print("❌ YouTube authentication failed - cannot upload")
            print("💡 Check your credentials.json and make sure you've authorized the app")
            return 1
        
        logger.info("✅ AUTOMATION COMPLETED SUCCESSFULLY!")
        print("\n" + "="*50)
        print("✅ AUTOMATION COMPLETED SUCCESSFULLY!")
        print("="*50)
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Process interrupted by user")
        print("\n⚠️ Process interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"\n❌ Automation failed: {str(e)}")
        print(f"\n❌ Automation failed: {str(e)}")
        print("\n🔍 Error details:")
        print(traceback.format_exc())
        return 1

def save_upload_info(video_id, title, topic, category, video_path, thumbnail_path):
    """Save upload information to a log file"""
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "upload_history.txt")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"""
{timestamp}
Video ID: {video_id}
Title: {title}
Topic: {topic}
Category: {category}
Video Path: {video_path}
Thumbnail Path: {thumbnail_path}
YouTube URL: https://www.youtube.com/watch?v={video_id}
Shorts URL: https://youtube.com/shorts/{video_id}
{'='*80}
"""
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        logger.info(f"📝 Upload info saved to: {log_file}")
        print(f"📝 Upload info saved to: {log_file}")
    except Exception as e:
        logger.error(f"⚠️ Could not save upload info: {e}")
        print(f"⚠️ Could not save upload info: {e}")

def check_dependencies():
    """Check if required dependencies are installed"""
    
    # Map of package names to their import names
    required_packages = {
        'openai': 'openai',
        'gtts': 'gtts', 
        'pydub': 'pydub',
        'Pillow': 'PIL',  # Pillow is imported as PIL
        'moviepy': 'moviepy',
        'google-auth': 'google.auth',  # google-auth is imported as google.auth
        'google-auth-oauthlib': 'google_auth_oauthlib',
        'google-api-python-client': 'googleapiclient'  # google-api-python-client is imported as googleapiclient
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            # Handle nested imports like google.auth
            if '.' in import_name:
                parts = import_name.split('.')
                module = __import__(parts[0])
                for part in parts[1:]:
                    module = getattr(module, part)
            else:
                __import__(import_name)
            logger.debug(f"✅ {package_name} ({import_name}) - OK")
        except (ImportError, AttributeError) as e:
            missing_packages.append(package_name)
            logger.debug(f"❌ {package_name} ({import_name}) - Missing: {e}")
    
    if missing_packages:
        logger.error("❌ Missing required packages:")
        print("❌ Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("✅ All required dependencies are installed")
    return True

def check_environment():
    """Check if required environment variables are set"""
    
    required_vars = [
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
            print(f"   - {var}")
        print("\n💡 Set environment variables:")
        for var in missing_vars:
            print(f"   export {var}=your_value_here")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def setup_check():
    """Perform setup checks before running automation"""
    
    logger.info("🔍 Performing setup checks...")
    print("🔍 Performing setup checks...")
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check environment variables
    if not check_environment():
        return False
    
    # Check if credentials.json exists for YouTube upload
    if not os.path.exists('credentials.json'):
        logger.warning("⚠️ credentials.json not found")
        print("⚠️ credentials.json not found")
        print("💡 YouTube upload will be disabled")
        print("💡 To enable upload, add your Google API credentials.json file")
        os.environ['UPLOAD_TO_YOUTUBE'] = 'false'
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    logger.info("✅ Setup checks completed")
    print("✅ Setup checks completed")
    return True

if __name__ == "__main__":
    logger.info("🎬 YouTube Automation System")
    print("🎬 YouTube Automation System")
    print("=" * 50)
    
    # Perform setup checks
    if not setup_check():
        logger.error("❌ Setup checks failed. Please fix the issues above.")
        print("❌ Setup checks failed. Please fix the issues above.")
        sys.exit(1)
    
    # Run main automation
    exit_code = main()
    
    if exit_code == 0:
        logger.info("\n🎉 Have a great day!")
        print("\n🎉 Have a great day!")
    else:
        logger.error("\n😞 Better luck next time!")
        print("\n😞 Better luck next time!")
    
    sys.exit(exit_code)