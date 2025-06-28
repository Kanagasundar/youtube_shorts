
from utils.topic_rotator import get_today_topic
from utils.scripting import generate_script
from utils.voice import generate_voiceover
from utils.video import create_video
from utils.thumbnail_generator import generate_thumbnail
import os

def main():
    # Get today's topic and category
    category, topic = get_today_topic()
    print(f"Generating content for: {category} -> {topic}")

    # Generate script
    script = generate_script(topic)
    print("Script generated.")

    # Generate voiceover from script
    voice_path = "output/voice.mp3"
    generate_voiceover(script, voice_path)
    print("Voiceover generated.")

    # Create video
    video_path = "output/video.mp4"
    create_video(voice_path, script, video_path)
    print("Video created.")

    # Generate thumbnail with overlay
    base_image_path = "output/frame.jpg"  # Ensure your video generator exports a key frame
    thumbnail_path = "output/thumbnail.jpg"
    generate_thumbnail(base_image_path, thumbnail_path, overlay_text=category)
    print("Thumbnail with overlay generated.")

if __name__ == "__main__":
    main()
