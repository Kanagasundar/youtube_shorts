#!/usr/bin/env python3
"""
YouTube Automation Main Script
Generates and uploads daily YouTube Shorts content
"""

import os
import sys
import traceback
from datetime import datetime

# Import modules from the same directory
from utils.topic_rotator import get_today_topic
from utils.scripting import generate_script
from utils.voice import generate_voice
from utils.video import create_video
from utils.thumbnail_generator import generate_thumbnail
from utils.youtube_uploader import YouTubeUploader, generate_video_metadata

def main():
    """Main function to orchestrate the entire process"""
    print("🚀 Starting YouTube Automation...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Get today's topic
        print("\n" + "="*50)
        print("📝 Step 1: Getting today's topic...")
        print("="*50)
        
        topic, category = get_today_topic()
        print(f"✅ Topic: {topic}")
        print(f"✅ Category: {category}")
        
        # Step 2: Generate script
        print("\n" + "="*50)
        print("✍️ Step 2: Generating script...")
        print("="*50)
        
        script = generate_script(topic, category)
        print(f"✅ Generated script ({len(script)} characters)")
        print(f"📄 Script preview: {script[:200]}...")
        
        # Step 3: Generate voice narration
        print("\n" + "="*50)
        print("🎙️ Step 3: Generating voice narration...")
        print("="*50)
        
        audio_path = generate_voice(script)
        print(f"✅ Audio generated: {audio_path}")
        
        # Step 4: Generate thumbnail
        print("\n" + "="*50)
        print("🖼️ Step 4: Generating thumbnail...")
        print("="*50)
        
        thumbnail_path = generate_thumbnail(topic, category)
        print(f"✅ Thumbnail generated: {thumbnail_path}")
        
        # Step 5: Create video
        print("\n" + "="*50)
        print("🎬 Step 5: Creating video...")
        print("="*50)
        
        video_path = create_video(script, audio_path, thumbnail_path, topic)
        print(f"✅ Video created: {video_path}")
        
        # Step 6: Upload to YouTube
        print("\n" + "="*50)
        print("📤 Step 6: Uploading to YouTube...")
        print("="*50)
        
        # Check if we should upload (can be disabled for testing)
        upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'true').lower() == 'true'
        
        if not upload_enabled:
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
                print(f"\n🎉 SUCCESS! Video uploaded!")
                print(f"📺 Video ID: {video_id}")
                print(f"🔗 Watch at: https://www.youtube.com/watch?v={video_id}")
                print(f"🔗 YouTube Shorts: https://youtube.com/shorts/{video_id}")
                
                # Save upload info
                save_upload_info(video_id, title, topic, category, video_path, thumbnail_path)
                
            else:
                print("❌ Video upload failed")
                return 1
        else:
            print("❌ YouTube authentication failed - cannot upload")
            print("💡 Check your credentials.json and make sure you've authorized the app")
            return 1
        
        print("\n" + "="*50)
        print("✅ AUTOMATION COMPLETED SUCCESSFULLY!")
        print("="*50)
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        return 1
        
    except Exception as e:
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
        print(f"📝 Upload info saved to: {log_file}")
    except Exception as e:
        print(f"⚠️ Could not save upload info: {e}")

def check_dependencies():
    """Check if required dependencies are installed"""
    
    required_packages = [
        'openai',
        'gtts',
        'pydub',
        'Pillow',
        'moviepy',
        'google-auth',
        'google-auth-oauthlib',
        'google-api-python-client'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
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
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Set environment variables:")
        for var in missing_vars:
            print(f"   export {var}=your_value_here")
        return False
    
    return True

def setup_check():
    """Perform setup checks before running automation"""
    
    print("🔍 Performing setup checks...")
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check environment variables
    if not check_environment():
        return False
    
    # Check if credentials.json exists for YouTube upload
    if not os.path.exists('credentials.json'):
        print("⚠️ credentials.json not found")
        print("💡 YouTube upload will be disabled")
        print("💡 To enable upload, add your Google API credentials.json file")
        os.environ['UPLOAD_TO_YOUTUBE'] = 'false'
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    print("✅ Setup checks completed")
    return True

if __name__ == "__main__":
    print("🎬 YouTube Automation System")
    print("=" * 50)
    
    # Perform setup checks
    if not setup_check():
        print("❌ Setup checks failed. Please fix the issues above.")
        sys.exit(1)
    
    # Run main automation
    exit_code = main()
    
    if exit_code == 0:
        print("\n🎉 Have a great day!")
    else:
        print("\n😞 Better luck next time!")
    
    sys.exit(exit_code)