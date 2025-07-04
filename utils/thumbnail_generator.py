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
import random  # Added to fix 'name "random" is not defined' error

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
    return list(set(keywords))[:10]  # Increased to 10 unique keywords

def generate_image_sequence(topic: str, script: str, category: str, output_dir: str = "output", num_images: int = 10, duration_per_image: float = 5, max_retries: int = 5) -> list:
    """
    Generate a sequence of images using Pexels API based on topic and script keywords, with Pexels script as fallback.
    
    Args:
        topic (str): The topic for the video
        script (str): The script text to derive image prompts
        category (str): The category of the video for fallback script
        output_dir (str): Directory to save images
        num_images (int): Number of images to generate (10 to 60)
        duration_per_image (float): Duration in seconds for each image in the video
        max_retries (int): Maximum number of retry attempts per image
    
    Returns:
        list: List of paths to generated images
    """
    # Ensure num_images is within the 10 to 60 range
    num_images = max(10, min(60, num_images))
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize Pexels API client
    pexels_api_key = os.getenv('PEXELS_API_KEY')
    if not pexels_api_key:
        logger.error("❌ PEXELS_API_KEY not found in environment variables")
        raise FileNotFoundError("PEXELS_API_KEY missing")
    
    headers = {"Authorization": pexels_api_key}
    base_url = "https://api.pexels.com/v1/search"
    image_paths = []
    
    logger.info(f"🖼️ Generating between 10 and 60 images for topic: {topic}, requested: {num_images}")
    
    try:
        # First attempt with provided script
        keywords = extract_keywords(script)
        queries = [topic] + keywords[:num_images-1]  # Use up to num_images-1 keywords
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
        
        if len(image_paths) < num_images:
            logger.warning(f"⚠️ Only {len(image_paths)} images generated with primary script, falling back to Pexels script")
            # Fallback script using Pexels-derived content
            fallback_script = f"Explore stunning visuals of {topic} in the {category} category, featuring natural scenes and highlights."
            fallback_keywords = extract_keywords(fallback_script)
            fallback_queries = [f"{topic} {category}"] + fallback_keywords[:num_images-len(image_paths)-1]
            if len(fallback_queries) < num_images - len(image_paths):
                fallback_queries.extend([f"{topic} {category} scene {i}" for i in range(len(fallback_queries), num_images-len(image_paths))])
            
            for i, query in enumerate(fallback_queries, len(image_paths)+1):
                attempt = 0
                while attempt < max_retries:
                    logger.info(f"Generating fallback image {i} with query: {query} (Attempt {attempt + 1}/{max_retries})")
                    params = {
                        "query": query,
                        "per_page": 1,
                        "page": random.randint(1, 100),
                        "orientation": "portrait"
                    }
                    response = requests.get(base_url, headers=headers, params=params)
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Failed to fetch fallback images for query '{query}': {response.status_code} - {response.text}")
                        attempt += 1
                        if attempt < max_retries and response.status_code in [429, 503]:
                            time.sleep(2 ** attempt + 2)
                        elif attempt < max_retries:
                            time.sleep(2 ** attempt)
                        continue
                    
                    data = response.json()
                    photos = data.get("photos", [])
                    
                    if not photos:
                        logger.error(f"❌ No photos found for fallback query: {query}")
                        attempt += 1
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                        continue
                    
                    image_url = photos[0]["src"]["original"]
                    logger.info(f"Downloading fallback image {i} from URL: {image_url}")
                    
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
                                logger.error(f"❌ Empty response for fallback image {i} from {image_url}")
                                attempt += 1
                                if attempt < max_retries:
                                    time.sleep(2 ** attempt)
                                continue
                            
                            content_type = img_response.headers.get('content-type', '')
                            if not content_type.startswith('image/'):
                                logger.error(f"❌ Invalid content type '{content_type}' for fallback image {i} from {image_url}")
                                attempt += 1
                                if attempt < max_retries:
                                    time.sleep(2 ** attempt)
                                continue
                            
                            img_data = io.BytesIO()
                            for chunk in img_response.iter_content(chunk_size=8192):
                                if chunk:
                                    img_data.write(chunk)
                            
                            if img_data.tell() == 0:
                                logger.error(f"❌ No data received for fallback image {i} from {image_url}")
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
                                    logger.error(f"❌ Fallback image {i} dimensions {img.size} too small")
                                    attempt += 1
                                    if attempt < max_retries:
                                        time.sleep(2 ** attempt)
                                    continue
                                
                                img.save(image_path, format='JPEG', quality=95)
                                debug_path = os.path.join(output_dir, f"debug_frame_{timestamp}_{i}.png")
                                img.save(debug_path, format='PNG')
                                logger.info(f"✅ Fallback image saved and validated: {image_path}")
                                logger.info(f"🖼️ Saved debug image: {debug_path}")
                                image_paths.append(image_path)
                                if len(image_paths) >= num_images:
                                    break
                                break
                                
                            except (IOError, OSError, AttributeError, ValueError) as img_error:
                                logger.error(f"❌ Invalid fallback image data for query '{query}': {str(img_error)}")
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
                            logger.error(f"❌ Failed to download fallback image {i}: {img_response.status_code}")
                            attempt += 1
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)
                    
                    except requests.exceptions.RequestException as req_error:
                        logger.error(f"❌ Request failed for fallback image {i}: {str(req_error)}")
                        attempt += 1
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                    
                    except Exception as unexpected_error:
                        logger.error(f"❌ Unexpected error for fallback image {i}: {str(unexpected_error)}")
                        attempt += 1
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                
                if attempt >= max_retries:
                    logger.error(f"❌ Failed to generate fallback image {i} after {max_retries} attempts")
        
        if len(image_paths) < 10:  # Ensure minimum 10 images
            logger.warning(f"⚠️ Only {len(image_paths)} images generated, below minimum of 10. Using available images.")
        elif len(image_paths) > 60:  # Cap at 60 images
            image_paths = image_paths[:60]
            logger.warning(f"⚠️ Generated {len(image_paths)} images, capped at maximum of 60.")
        
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
    images = generate_image_sequence(topic, script_placeholder, category, num_images=1)
    return images[0] if images else None

if __name__ == "__main__":
    # Test image sequence generation
    test_topic = "Plants That Can Count to Twenty"
    test_script = "Did you know about Plants That Can Count to Twenty? It's fascinating! Learn more in this quick Nature video about their unique abilities."
    test_category = "Nature"
    images = generate_image_sequence(test_topic, test_script, test_category, num_images=15)  # Test with 15 images
    if images:
        logger.info(f"✅ Generated {len(images)} test images: {images}")
    else:
        logger.error("❌ Test image generation failed")