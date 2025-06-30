import os
import logging
import time
import random
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Predefined topics and categories (example list, adjust as needed)
TOPICS = [
    ("The Color That Doesn't Actually Exist", "Science"),
    ("Why Time Travel Might Be Impossible", "Science"),
    ("The Mystery of the Bermuda Triangle", "Mystery"),
    ("How Black Holes Work", "Science"),
    ("The Psychology of Dreams", "Psychology"),
    ("Unsolved Mysteries of the Universe", "Science"),
    ("The History of the Internet", "Technology"),
    ("Why We Procrastinate", "Psychology"),
    ("The Science of Happiness", "Psychology"),
    ("Strange Ocean Phenomena", "Science")
]

def get_today_topic() -> Tuple[str, str]:
    """
    Select a topic and category for today's video based on the current date.
    
    Returns:
        Tuple[str, str]: A tuple containing the selected topic and category.
    """
    try:
        # Use date-based indexing for deterministic topic selection
        day_of_year = datetime.now().timetuple().tm_yday
        index = (day_of_year - 1) % len(TOPICS)  # Cycle through topics
        topic, category = TOPICS[index]
        logger.info(f"🗓️ Date: {datetime.now().strftime('%Y-%m-%d')}")
        logger.info(f"🎯 Selected topic index: {index}")
        logger.info(f"✅ Topic: {topic}")
        logger.info(f"✅ Category: {category}")
        return topic, category
    except Exception as e:
        logger.error(f"Failed to select topic: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        return "Default Topic", "General"

def generate_script(topic: str, length: str = "short", max_retries: int = 4) -> Optional[str]:
    """
    Generate a YouTube Shorts script for the given topic with retry logic.
    
    Args:
        topic (str): The topic for the video
        length (str): The desired length of the script ('short', 'medium', 'long')
        max_retries (int): Maximum number of retry attempts for API calls
    
    Returns:
        Optional[str]: The generated script or None if an error occurs
    """
    try:
        logger.info("Initializing OpenAI client")
        logger.info(f"Environment variables: { {k: '***' if k == 'OPENAI_API_KEY' else v for k, v in os.environ.items()} }")
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        logger.info(f"OpenAI client initialized: {client}")
        
        prompt = f"""
        Create a concise, engaging script for a YouTube Shorts video about '{topic}'.
        The script should be {length} (aim for 30-60 seconds if short, 1-2 minutes if medium, 2-3 minutes if long).
        Use a conversational tone, include a hook to grab attention, and end with a call to action.
        Format the script as plain text with clear sections for the hook, body, and call to action.
        """
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Generating script for topic: {topic} (Attempt {attempt})")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a creative scriptwriter specializing in YouTube Shorts."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500 if length == "short" else 1000,
                    temperature=0.7
                )
                
                script = response.choices[0].message.content.strip()
                logger.info(f"Script generated successfully ({len(script)} characters)")
                return script
            
            except Exception as e:
                if attempt < max_retries:
                    sleep_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s, 8s
                    logger.warning(f"Attempt {attempt} failed: {str(e)}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to generate script after {max_retries} attempts: {str(e)}")
                    logger.debug("Stack trace:", exc_info=True)
                    return None
    
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        return None