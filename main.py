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
import importlib.util
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure the utils directory is in sys.path
utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils')
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

def check_dependencies():
    """Check if required dependencies are installed with robust detection"""
    
    required_packages = {
        'openai': 'openai',
        'gtts': 'gtts',
        'pydub': 'pydub',
        'Pillow': 'PIL',
        'moviepy': 'moviepy.editor',
        'numpy': 'numpy',
        'google-auth': 'google.auth',
        'google-auth-oauthlib': 'google_auth_oauthlib',
        'google-api-python-client': 'googleapiclient',
        'requests': 'requests'
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            # Import the module
            if '.' in import_name:
                parts = import_name.split('.')
                module = __import__(parts[0])
                for part in parts[1:]:
                    module = getattr(module, part)
            else:
                module = __import__(import_name)
            
            # Verify the module is loaded
            version = getattr(module, '__version__', 'unknown')
            logger.info(f"✅ {package_name} ({import_name}) - OK (v{version})")
            print(f"✅ {package_name} ({import_name}) - OK (v{version})")
            
        except (ImportError, AttributeError) as e:
            logger.error(f"❌ {package_name} ({import_name}) - Failed: {str(e)}")
            print(f"❌ {package_name} ({import_name}) - Failed: {str(e)}")
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error("❌ Missing required packages:")
        print("❌ Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        
        # Additional debugging info
        print("\n🔍 Python environment info:")
        print(f"   Python version: {sys.version}")
        print(f"   Python executable: {sys.executable}")
        print(f"   Site packages: {[p for p in sys.path if 'site-packages' in p]}")
        
        return False
    
    logger.info("✅ All required dependencies are installed")
    print("✅ All required dependencies are installed")
    return True

def validate_credentials_file():
    """Validate the credentials.json file"""
    
    if not os.path.exists('credentials.json'):
        logger.warning("⚠️ credentials.json not found")
        return False
    
    try:
        with open('credentials.json', 'r', encoding='utf-8') as f:
            creds_data = json.load(f)
        
        # Check for required fields
        if 'type' not in creds_data:
            logger.error("❌ credentials.json missing 'type' field")
            return False
        
        # Handle different credential types
        if creds_data.get('type') == 'service_account':
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            logger.info("📝 Detected service account credentials")
        else:
            # Installed application credentials
            required_fields = ['type', 'project_id', 'client_id', 'client_secret']
            if 'installed' in creds_data:
                required_fields = ['installed']
                creds_data = creds_data['installed']
            logger.info("📝 Detected installed application credentials")
        
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            logger.error(f"❌ credentials.json missing required fields: {missing_fields}")
            return False
        
        logger.info("✅ credentials.json validation passed")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ credentials.json is not valid JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error validating credentials.json: {e}")
        return False

def check_environment():
    """Check if required environment variables are set"""
    
    required_vars = [
        'OPENAI_API_KEY'
    ]
    
    optional_vars = [
        'UPLOAD_TO_YOUTUBE',
        'VIDEO_PRIVACY', 
        'VIDEO_CATEGORY_ID',
        'DISCORD_WEBHOOK_URL',
        'TOPIC_OVERRIDE',
        'CATEGORY_OVERRIDE'
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            logger.debug(f"✅ {var} is set (length: {len(value)})")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            logger.debug(f"✅ {var} = {value}")
        else:
            logger.debug(f"ℹ️ {var} not set (optional)")
    
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
    
    if not check_dependencies():
        return False
    
    if not check_environment():
        return False
    
    upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
    
    if upload_enabled:
        if validate_credentials_file():
            logger.info("✅ credentials.json found and validated")
            print("✅ credentials.json found and validated")
        else:
            logger.warning("⚠️ credentials.json validation failed")
            print("⚠️ credentials.json validation failed")
            print("💡 YouTube upload will be disabled")
            print("💡 To enable upload, fix your Google API credentials.json file")
            os.environ['UPLOAD_TO_YOUTUBE'] = 'false'
    else:
        logger.info("ℹ️ YouTube upload disabled by configuration")
        print("ℹ️ YouTube upload disabled by configuration")
    
    # Create output directories
    os.makedirs('output', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    logger.info("✅ Setup checks completed")
    print("✅ Setup checks completed")
    return True

def import_modules():
    """Import required modules with error handling"""
    global get_today_topic, generate_script, generate_voice, create_video, generate_thumbnail, YouTubeUploader, generate_video_metadata
    
    try:
        from topic_rotator import get_today_topic
        from scripting import generate_script
        from voice import generate_voice
        from video import create_video
        from thumbnail_generator import generate_thumbnail
        from youtube_uploader import YouTubeUploader, generate_video_metadata
        logger.info("✅ All utility modules imported successfully")
        return True
    except ImportError as e:
        logger.error(f"Failed to import modules: {e}")
        print(f"❌ Failed to import modules: {e}")
        print("💡 Make sure all required files are in the utils directory:")
        print("   - topic_rotator.py")
        print("   - scripting.py") 
        print("   - voice.py")
        print("   - video.py")
        print("   - thumbnail_generator.py")
        print("   - youtube_uploader.py")
        
        if os.path.exists(utils_path):
            print(f"\n📁 Files in {utils_path}:")
            for file in os.listdir(utils_path):
                if file.endswith('.py'):
                    print(f"   - {file}")
        else:
            print(f"\n❌ Utils directory not found: {utils_path}")
        
        return False

def main():
    """Main function to orchestrate the entire process"""
    logger.info("🚀 Starting YouTube Automation...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        logger.info("📝 Step 1: Getting today's topic...")
        print("\n" + "="*50)
        print("📝 Step 1: Getting today's topic...")
        print("="*50)
        
        # Handle topic override
        topic_override = os.getenv('TOPIC_OVERRIDE')
        category_override = os.getenv('CATEGORY_OVERRIDE')
        
        if topic_override:
            topic = topic_override
            category = category_override or 'general'
            logger.info(f"✅ Using override - Topic: {topic}, Category: {category}")
            print(f"✅ Using override - Topic: {topic}, Category: {category}")
        else:
            topic, category = get_today_topic()
            logger.info(f"✅ Topic: {topic}, Category: {category}")
            print(f"✅ Topic: {topic}")
            print(f"✅ Category: {category}")
        
        logger.info("✍️ Step 2: Generating script...")
        print("\n" + "="*50)
        print("✍️ Step 2: Generating script...")
        print("="*50)
        
        script = generate_script(topic, category)
        logger.info(f"✅ Generated script ({len(script)} characters)")
        print(f"✅ Generated script ({len(script)} characters)")
        print(f"📄 Script preview: {script[:200]}...")
        
        logger.info("🎙️ Step 3: Generating voice narration...")
        print("\n" + "="*50)
        print("🎙️ Step 3: Generating voice narration...")
        print("="*50)
        
        audio_path = generate_voice(script)
        logger.info(f"✅ Audio generated: {audio_path}")
        print(f"✅ Audio generated: {audio_path}")
        
        logger.info("🖼️ Step 4: Generating thumbnail...")
        print("\n" + "="*50)
        print("🖼️ Step 4: Generating thumbnail...")
        print("="*50)
        
        thumbnail_path = generate_thumbnail(topic, category)
        logger.info(f"✅ Thumbnail generated: {thumbnail_path}")
        print(f"✅ Thumbnail generated: {thumbnail_path}")
        
        logger.info("🎬 Step 5: Creating video...")
        print("\n" + "="*50)
        print("🎬 Step 5: Creating video...")
        print("="*50)
        
        video_path = create_video(script, audio_path, thumbnail_path, topic)
        logger.info(f"✅ Video created: {video_path}")
        print(f"✅ Video created: {video_path}")
        
        logger.info("📤 Step 6: Uploading to YouTube...")
        print("\n" + "="*50)
        print("📤 Step 6: Uploading to YouTube...")
        print("="*50)
        
        upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
        
        if not upload_enabled:
            logger.warning("⚠️ Upload disabled (UPLOAD_TO_YOUTUBE=false)")
            print("⚠️ Upload disabled (UPLOAD_TO_YOUTUBE=false)")
            print(f"📁 Video saved locally: {video_path}")
            print(f"📁 Thumbnail saved locally: {thumbnail_path}")
            print("✅ Automation completed (upload skipped)")
            return 0
        
        try:
            uploader = YouTubeUploader()
            
            if uploader.youtube:
                title, description, tags = generate_video_metadata(topic, category, script)
                
                logger.info(f"📝 Title: {title}")
                logger.info(f"🏷️ Tags: {', '.join(tags[:5])}...")
                print(f"📝 Title: {title}")
                print(f"🏷️ Tags: {', '.join(tags[:5])}...")
                
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
                
        except Exception as upload_error:
            logger.error(f"❌ Upload process failed: {upload_error}")
            print(f"❌ Upload process failed: {upload_error}")
            print(f"📁 Video saved locally: {video_path}")
            print(f"📁 Thumbnail saved locally: {thumbnail_path}")
            print("✅ Automation completed (upload failed)")
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

if __name__ == "__main__":
    """Entry point for the script"""
    print("🤖 YouTube Automation Script")
    print("="*50)
    
    try:
        if not setup_check():
            print("\n❌ Setup checks failed. Please fix the issues above and try again.")
            sys.exit(1)
        
        if not import_modules():
            print("\n❌ Module import failed. Please check your utils directory.")
            sys.exit(1)
        
        exit_code = main()
        
        if exit_code == 0:
            print("\n🎉 Script completed successfully!")
        else:
            print("\n⚠️ Script completed with errors.")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\n🔍 Full error details:")
        traceback.print_exc()
        sys.exit(1)