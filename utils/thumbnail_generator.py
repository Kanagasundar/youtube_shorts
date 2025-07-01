import os
import logging
import replicate
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
    Generate a sequence of images using Replicate API based on topic and script.
    
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
    
    # Initialize Replicate client
    replicate_api_token = os.getenv('REPLICATE_API_TOKEN')
    if not replicate_api_token:
        logger.error("❌ REPLICATE_API_TOKEN not found in environment variables")
        return []
    
    replicate_client = replicate.Client(api_token=replicate_api_token)
    
    # Generate prompts based on script and topic
    prompt_base = f"A vibrant scene related to {topic}, inspired by the script: {script[:100]}..."
    image_paths = []
    
    logger.info(f"🖼️ Generating {num_images} images for topic: {topic}")
    
    try:
        for i in range(num_images):
            prompt = f"{prompt_base} - variation {i+1}, hd, dramatic lighting"
            logger.info(f"Generating image {i+1} with prompt: {prompt}")
            
            # Use the specified Stable Diffusion version with K_EULER scheduler
            input_data = {
                "prompt": prompt,
                "width": 1080,
                "height": 1920,
                "scheduler": "K_EULER"
            }
            output = replicate_client.run(
                "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
                input=input_data
            )
            
            if isinstance(output, list) and output:
                image_url = output[0]  # Assuming the first URL is the image
            else:
                logger.error(f"❌ Unexpected output format from Replicate for image {i+1}")
                continue
            
            # Download and save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"frame_{timestamp}_{i+1}.png"
            image_path = os.path.join(output_dir, image_filename)
            
            # Simple download (assuming URL provides direct image access)
            import requests
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                logger.info(f"✅ Image saved: {image_path}")
                image_paths.append(image_path)
            else:
                logger.error(f"❌ Failed to download image {i+1}: {response.status_code}")
            
            time.sleep(2)  # Rate limiting to avoid API overuse
            
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
    test_topic = "The First Photograph"
    test_script = "Did you know the first photograph took 8 hours to capture?"
    images = generate_image_sequence(test_topic, test_script)
    if images:
        logger.info(f"✅ Generated {len(images)} test images: {images}")
    else:
        logger.error("❌ Test image generation failed")