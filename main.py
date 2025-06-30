#!/usr/bin/env python3
import os
import sys
import random
from datetime import datetime
from dotenv import load_dotenv

# Import utility modules
from scripting import generate_script
from youtube_uploader import YouTubeUploader, generate_video_metadata

# Load environment variables
load_dotenv()

def get_daily_topic():
    """Get topic for today (with override support)"""
    if os.getenv('TOPIC_OVERRIDE'):
        return os.getenv('TOPIC_OVERRIDE'), os.getenv('CATEGORY_OVERRIDE', 'General')
    
    # Topic categories
    topics = {
        'Science': [
            'Black Holes', 'Quantum Physics', 'Space Exploration', 'Human Brain',
            'Ocean Mysteries', 'DNA Secrets', 'Climate Change', 'Renewable Energy'
        ],
        'History': [
            'Ancient Civilizations', 'World War Secrets', 'Lost Cities', 'Historical Mysteries',
            'Famous Inventions', 'Ancient Technologies', 'Historical Figures', 'Archaeological Discoveries'
        ],
        'Technology': [
            'Artificial Intelligence', 'Future Tech', 'Robotics', 'Virtual Reality',
            'Blockchain', 'Internet History', 'Gaming Evolution', 'Social Media Impact'
        ],
        'Nature': [
            'Amazing Animals', 'Rare Species', 'Natural Phenomena', 'Ecosystems',
            'Weather Extremes', 'Plant Wonders', 'Conservation', 'Evolution'
        ]
    }
    
    # Select based on day of year for consistency
    day_of_year = datetime.now().timetuple().tm_yday
    categories = list(topics.keys())
    category = categories[day_of_year % len(categories)]
    
    topic_list = topics[category]
    topic = topic_list[day_of_year % len(topic_list)]
    
    return topic, category

def create_simple_video(script: str, topic: str, output_path: str):
    """Create a simple text-based video using MoviePy"""
    try:
        from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip
        from moviepy.config import check_and_download_cmd
        
        # Basic video settings
        duration = 30  # 30 seconds for shorts
        size = (1080, 1920)  # 9:16 aspect ratio
        
        # Create background
        background = ColorClip(size=size, color=(20, 20, 30), duration=duration)
        
        # Create text clip
        txt_clip = TextClip(script,
                           fontsize=60,
                           color='white',
                           font='Arial',
                           size=size,
                           method='caption').set_duration(duration)
        
        # Compose video
        video = CompositeVideoClip([background, txt_clip])
        
        # Write video file
        video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio=False,
            preset='medium',
            verbose=False,
            logger=None
        )
        
        return True
        
    except Exception as e:
        print(f"Video creation failed: {e}")
        return False

def create_thumbnail(topic: str, output_path: str):
    """Create a simple thumbnail"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create image
        img = Image.new('RGB', (1280, 720), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        words = topic.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) <= 15:  # Approximate character limit per line
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Draw text lines
        y_offset = (720 - len(lines) * 100) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (1280 - text_width) // 2
            y = y_offset + i * 100
            draw.text((x, y), line, fill=(255, 255, 255), font=font)
        
        img.save(output_path, 'JPEG', quality=95)
        return True
        
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
        return False

def main():
    print("🚀 Starting YouTube Shorts Automation")
    
    try:
        # Get today's topic
        topic, category = get_daily_topic()
        print(f"✅ Topic: {topic}")
        print(f"✅ Category: {category}")
        
        # Generate script
        print("✍️ Generating script...")
        script = generate_script(topic)
        if not script:
            print("❌ Failed to generate script")
            return 1
        
        print(f"✅ Script generated ({len(script)} chars)")
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
        
        # Create video
        video_path = f"output/video_{datetime.now().strftime('%Y%m%d')}.mp4"
        print("🎬 Creating video...")
        
        if not create_simple_video(script, topic, video_path):
            print("❌ Video creation failed")
            return 1
        
        print("✅ Video created successfully")
        
        # Create thumbnail
        thumbnail_path = f"output/thumbnail_{datetime.now().strftime('%Y%m%d')}.jpg"
        print("🖼️ Creating thumbnail...")
        
        if not create_thumbnail(topic, thumbnail_path):
            print("❌ Thumbnail creation failed")
            return 1
        
        print("✅ Thumbnail created successfully")
        
        # Upload to YouTube (if enabled)
        upload_enabled = os.getenv('UPLOAD_TO_YOUTUBE', 'false').lower() == 'true'
        
        if upload_enabled:
            print("📤 Uploading to YouTube...")
            
            try:
                uploader = YouTubeUploader()
                title, description, tags = generate_video_metadata(topic, category)
                
                video_id = uploader.upload_video(
                    video_path, thumbnail_path, title, description, tags
                )
                
                if video_id:
                    print(f"✅ Video uploaded! ID: {video_id}")
                    print(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")
                else:
                    print("❌ Upload failed")
                    return 1
                    
            except Exception as e:
                print(f"❌ Upload error: {e}")
                return 1
        else:
            print("⚠️ Upload disabled (check UPLOAD_TO_YOUTUBE environment variable)")
        
        print("🎉 Automation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)