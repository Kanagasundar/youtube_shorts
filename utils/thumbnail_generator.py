import os
import logging
import requests
from dotenv import load_dotenv
import time
from datetime import datetime
from PIL import Image
import io
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def extract_keywords(script: str) -> list:
    """
    Extract key nouns and phrases from script for Pexels API queries.
    
    Args:
        script (str): Script text
    
    Returns:
        list: List of keywords
    """
    tokens = word_tokenize(script)
    tagged = pos_tag(tokens)
    keywords = [word for word, pos in tagged if pos in ['NN', 'NNS', 'NNP', 'NNPS']]
    return list(set(keywords))[:5]  # Limit to 5 unique keywords

def generate_image_sequence(topic: str, script: str, output_dir: str = "output", num_images: int = 5, duration_per_image: float = 5, max_retries: int = 5) -> list:
    """
    Generate a sequence of images using Pexels API based on topic and script keywords.
    
    Args:
        topic (str): The topic for the video
        script (str): The script text to derive image prompts
        output_dir (str): Directory to save images
        num_images (int): Number of images to generate
        duration_per_image (float): Duration in seconds for each image in the video
        max_retries (int): Maximum number of retry attempts per image
    
    Returns:
        list: List of paths to generated images
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize Pexels API client
    pexels_api_key = os.getenv('PEXELS_API_KEY')
    if not pexels_api_key:
        logger.error("❌ PEXELS_API_KEY not found in environment variables")
        raise FileNotFoundError("PEXELS_API_KEY missing")
    
    headers = {"Authorization": pexels_api_key}
    base_url = "https://api.pexels.com/v1/search"
    image_paths = []
    
    logger.info(f"🖼️ Generating up to {num_images} images for topic: {topic}")
    
    try:
        # Extract keywords from script
        queries = [topic] + extract_keywords(script)[:num_images-1]
        if len(queries) < num_images:
            queries.extend([f"{topic} scene {i}" for i in range(len(queries), num_images)])
        
        for i, query in enumerate(queries, 1):
            attempt = 0
            while attempt < max_retries:
                logger.info(f"Generating image {i} with query: {query} (Attempt {attempt + 1}/{max_retries})")
                params = {
                    "query": query,
                    "per_page": 1,
                    "page": random.randint(1, 100),  # Randomize page to avoid repetition
                    "orientation": "portrait"
                }
                response = requests.get(base_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    logger.error(f"❌ Failed to fetch images for query '{query}': {response.status_code} - {response.text}")
                    attempt += 1
                    if attempt < max_retries and response.status_code in [429, 503]:
                        time.sleep(2 ** attempt + 2)
                    elif attempt < max_retries:
                        time.sleep(2 ** attempt)
                    continue
                
                data = response.json()
                photos = data.get("photos", [])
                
                if not photos:
                    logger.error(f"❌ No photos found for query: {query}")
                    attempt += 1
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                    continue
                
                image_url = photos[0]["src"]["original"]
                logger.info(f"Downloading image {i} from URL: {image_url}")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_path = os.path.join(output_dir, f"temp_frame_{timestamp}_{i}.png")
                image_path = os.path.join(output_dir, f"frame_{timestamp}_{i}.png")
                
                try:
                    img_response = requests.get(image_url, stream=True, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    
                    if img_response.status_code == 200:
                        content_length = int(img_response.headers.get('content-length', 0))
                        if content_length == 0:
                            logger.error(f"❌ Empty response for image {i} from {image_url}")
                            attempt += 1
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                            continue
                        
                        content_type = img_response.headers.get('content-type', '')
                        if not content_type.startswith('image/'):
                            logger.error(f"❌ Invalid content type '{content_type}' for image {i} from {image_url}")
                            attempt += 1
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                            continue
                        
                        img_data = io.BytesIO()
                        for chunk in img_response.iter_content(chunk_size=8192):
                            if chunk:
                                img_data.write(chunk)
                        
                        if img_data.tell() == 0:
                            logger.error(f"❌ No data received for image {i} from {image_url}")
                            attempt += 1
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                            continue
                        
                        img_data.seek(0)
                        
                        try:
                            img = Image.open(img_data)
                            img.load()
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            if img.size[0] < 100 or img.size[1] < 100:
                                logger.error(f"❌ Image {i} dimensions {img.size} too small")
                                attempt += 1
                                if attempt < max_retries:
                                    time.sleep(2 ** attempt)
                                continue
                            
                            img.save(image_path, format='JPEG', quality=95)
                            debug_path = os.path.join(output_dir, f"debug_frame_{timestamp}_{i}.png")
                            img.save(debug_path, format='PNG')
                            logger.info(f"✅ Image saved and validated: {image_path}")
                            logger.info(f"🖼️ Saved debug image: {debug_path}")
                            image_paths.append(image_path)
                            break
                            
                        except (IOError, OSError, AttributeError, ValueError) as img_error:
                            logger.error(f"❌ Invalid image data for query '{query}': {str(img_error)}")
                            attempt += 1
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                            continue
                        
                        finally:
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                    
                    else:
                        logger.error(f"❌ Failed to download image {i}: {img_response.status_code}")
                        attempt += 1
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                
                except requests.exceptions.RequestException as req_error:
                    logger.error(f"❌ Request failed for image {i}: {str(req_error)}")
                    attempt += 1
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                
                except Exception as unexpected_error:
                    logger.error(f"❌ Unexpected error for image {i}: {str(unexpected_error)}")
                    attempt += 1
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
            
            if attempt >= max_retries:
                logger.error(f"❌ Failed to generate image {i} after {max_retries} attempts")
        
        if not image_paths:
            logger.error("❌ No images generated after all attempts - terminating process")
            raise FileNotFoundError("Failed to generate any images after all retries")
        
        return image_paths
    
    except Exception as e:
        logger.error(f"❌ Failed to generate image sequence: {str(e)}")
        raise

def generate_thumbnail(topic: str, category: str):
    """
    Generate a single thumbnail image.
    
    Args:
        topic (str): The topic for the video
        category (str): The category of the video
    
    Returns:
        str or None: Path to the generated thumbnail
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