from utils.topic_rotator import get_today_topic
from utils.scripting import generate_script
from utils.voice import generate_voice
from utils.video import create_video
from utils.thumbnail_generator import generate_thumbnail
import os
import moviepy.editor as mp

openai_key = os.getenv("OPENAI_API_KEY")
yt_client_id = os.getenv("YOUTUBE_CLIENT_ID")
yt_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

def extract_frame_from_video(video_path, frame_path, time=1.0):
    """Extract a frame from the video to use for thumbnail"""
    try:
        if not os.path.exists(video_path):
            print(f"Video file not found: {video_path}")
            return False
            
        video = mp.VideoFileClip(video_path)
        # Extract frame at 1 second or 10% into video, whichever is smaller
        extract_time = min(time, video.duration * 0.1, video.duration - 0.1)
        frame = video.get_frame(extract_time)
        
        # Convert frame to PIL Image and save
        from PIL import Image
        img = Image.fromarray(frame.astype('uint8'))
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(frame_path), exist_ok=True)
        img.save(frame_path, "JPEG", quality=95)
        
        video.close()
        print(f"Frame extracted: {frame_path}")
        return True
        
    except Exception as e:
        print(f"Error extracting frame: {e}")
        return False

def main():
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    # Get today's topic and category
    category, topic = get_today_topic()
    print(f"Generating content for: {category} -> {topic}")

    # Generate script
    script = generate_script(topic)
    print("Script generated.")

    # Generate voiceover from script
    voice_path = "output/voice.mp3"
    generate_voice(script, voice_path)
    print("Voiceover generated.")

    # Create video
    video_path = "output/video.mp4"
    create_video(voice_path, script, video_path)
    print("Video created.")

    # Extract frame from video for thumbnail
    base_image_path = "output/frame.jpg"
    frame_extracted = extract_frame_from_video(video_path, base_image_path)
    
    # Generate thumbnail with overlay
    thumbnail_path = "output/thumbnail.jpg"
    if frame_extracted:
        # Use extracted frame as base
        generate_thumbnail(base_image_path, thumbnail_path, overlay_text=category)
    else:
        # Use None to trigger default background creation
        print("Using default background for thumbnail")
        generate_thumbnail(None, thumbnail_path, overlay_text=category)
    
    print("Thumbnail with overlay generated.")

if __name__ == "__main__":
    main()