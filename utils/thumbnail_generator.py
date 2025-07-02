import os
import logging
import requests
from dotenv import load_dotenv
import time
from datetime import datetime
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_image_sequence(topic: str, script: str, output_dir: str = "output", num_images: int = 5, duration_per_image: int = 5) -> list:
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
        # Split script into key phrases for diverse image queries
        script_phrases = script.split('\n')
        queries = [topic] + [phrase.strip() for phrase in script_phrases if phrase.strip() and len(phrase.strip()) > 5][:num_images-1]
        if len(queries) < num_images:
            queries.extend([f"{topic} scene {i}" for i in range(len(queries), num_images)])
        
        for i, query in enumerate(queries, 1):
            logger.info(f"Generating image {i} with query: {query}")
            params = {
                "query": query,
                "per_page": 1,
                "page": 1,
                "orientation": "portrait"  # Suitable for video thumbnails
            }
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to fetch images for query '{query}': {response.status_code} - {response.text}")
                continue
            
            data = response.json()
            photos = data.get("photos", [])
            
            if not photos:
                logger.error(f"❌ No photos found for query: {query}")
                continue
            
            image_url = photos[0]["src"]["original"]  # Use original size for better quality
            logger.info(f"Downloading image {i} from URL: {image_url}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"frame_{timestamp}_{i}.png"
            image_path = os.path.join(output_dir, image_filename)
            
            img_response = requests.get(image_url, stream=True)
            if img_response.status_code == 200:
                # Validate image content
                with open(image_path, 'wb') as f:
                    for chunk in img_response.iter_content(1024):
                        f.write(chunk)
                # Verify the image is valid
                try:
                    with Image.open(image_path) as img:
                        img.verify()  # Check if the file is a valid image
                        img = img.convert("RGB")  # Ensure it's processable
                        if img.size[0] < 1080 or img.size[1] < 1920:  # Minimum resolution check
                            logger.warning(f"⚠️ Image {i} resolution {img.size} is below 1080x1920, resizing may fail")
                        logger.info(f"✅ Image saved and validated: {image_path}")
                        image_paths.append(image_path)
                except (IOError, SyntaxError) as e:
                    logger.error(f"❌ Invalid image downloaded for query '{query}': {str(e)}")
                    if os.path.exists(image_path):
                        os.remove(image_path)
            else:
                logger.error(f"❌ Failed to download image {i}: {img_response.status_code}")
            
            time.sleep(1)  # Respect rate limits (200 requests/hour)
        
        if not image_paths:
            logger.error("❌ No images generated")
            return []
        
        total_duration = len(image_paths) * duration_per_image
        if not (25 <= total_duration <= 60):  # Updated to 25-60 seconds range
            logger.warning(f"⚠️ Total duration {total_duration}s is outside 25-60s range, adjusting")
            if total_duration < 25:
                duration_per_image = max(25 // len(image_paths), 5)
                total_duration = len(image_paths) * duration_per_image
            elif total_duration > 60:
                num_images = min(60 // duration_per_image, len(image_paths))
                image_paths = image_paths[:num_images]
                total_duration = num_images * duration_per_image
            logger.info(f"✅ Adjusted to {len(image_paths)} images, {total_duration}s total duration")
        
        return image_paths
    
    except Exception as e:
        logger.error(f"❌ Failed to generate image sequence: {str(e)}")
        return []

def generate_thumbnail(topic: str, category: str):
    """
    Generate a single thumbnail image (delegates to image sequence for compatibility).
    
    Args:
        topic (str): The topic for the video
        category (str): The category of the video
    
    Returns:
        str or None: Path to the generated thumbnail, or None if failed
    """
    script_placeholder = f"A short video about {topic} in {category} category."
    images = generate_image_sequence(topic, script_placeholder, num_images=1)
    return images[0] if images else None

if __name__ == "__main__":
    # Test image sequence generation
    test_topic = "Plants That Can Count to Twenty"
    test_script = "Did you know about Plants That Can Count to Twenty? It's fascinating! Learn more in this quick Nature video about their unique abilities."
    images = generate_image_sequence(test_topic, test_script)
    if images:
        logger.info(f"✅ Generated {len(images)} test images: {images}")
    else:
        logger.error("❌ Test image generation failed")