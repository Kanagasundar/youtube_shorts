import os
import logging
import requests
from dotenv import load_dotenv
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_image_sequence(topic, script, output_dir="output", num_images=5, duration_per_image=5):
    """
    Generate a sequence of images using Pexels API based on topic and script.
    
    Args:
        topic (str): The topic for the video
        script (str): The script text to derive image prompts
        output_dir (str): Directory to save images
        num_images (int): Number of images to generate
        duration_per_image (int): Duration in seconds for each image in the video
    
    Returns:
        list: List of paths to generated images
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize Pexels API client
    pexels_api_key = os.getenv('PEXELS_API_KEY')
    if not pexels_api_key:
        logger.error("❌ PEXELS_API_KEY not found in environment variables")
        return []
    
    headers = {"Authorization": pexels_api_key}
    base_url = "https://api.pexels.com/v1/search"
    image_paths = []
    
    logger.info(f"🖼️ Generating {num_images} images for topic: {topic}")
    
    try:
        params = {
            "query": topic,
            "per_page": num_images,
            "page": 1,
            "orientation": "portrait"  # Suitable for video thumbnails
        }
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to fetch images: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        photos = data.get("photos", [])
        
        if not photos:
            logger.error("❌ No photos found for the given topic")
            return []
        
        for i, photo in enumerate(photos[:num_images]):
            image_url = photo["src"]["large"]  # Use large size for better quality
            logger.info(f"Generating image {i+1} with URL: {image_url}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"frame_{timestamp}_{i+1}.png"
            image_path = os.path.join(output_dir, image_filename)
            
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                with open(image_path, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                logger.info(f"✅ Image saved: {image_path}")
                image_paths.append(image_path)
            else:
                logger.error(f"❌ Failed to download image {i+1}: {img_response.status_code}")
            
            time.sleep(1)  # Respect rate limits (200 requests/hour)
        
        if not image_paths:
            logger.error("❌ No images generated")
            return []
        
        total_duration = num_images * duration_per_image
        if not (15 <= total_duration <= 60):
            logger.warning(f"⚠️ Total duration {total_duration}s is outside 15-60s range, adjusting num_images")
            while total_duration > 60 and num_images > 1:
                num_images -= 1
                total_duration = num_images * duration_per_image
            if total_duration < 15:
                duration_per_image = 15 // num_images
                total_duration = num_images * duration_per_image
            logger.info(f"✅ Adjusted to {num_images} images, {total_duration}s total duration")
        
        return image_paths
    
    except Exception as e:
        logger.error(f"❌ Failed to generate image sequence: {str(e)}")
        return []

def generate_thumbnail(topic, category):
    # This function is kept for compatibility but delegates to image sequence
    script_placeholder = f"A short video about {topic} in {category} category."
    return generate_image_sequence(topic, script_placeholder)[0] if generate_image_sequence(topic, script_placeholder) else None

if __name__ == "__main__":
    # Test image sequence generation
    test_topic = "Plants That Can Count to Twenty"
    test_script = "Did you know about Plants That Can Count to Twenty? It's fascinating! Learn more in this quick Natur..."
    images = generate_image_sequence(test_topic, test_script)
    if images:
        logger.info(f"✅ Generated {len(images)} test images: {images}")
    else:
        logger.error("❌ Test image generation failed")