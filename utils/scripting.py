import os
import logging
import time
import sys
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_script(topic: str, length: str = "short", max_retries: int = int(os.getenv('MAX_RETRIES', '3'))) -> Optional[str]:
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
        logger.info(f"OpenAI version: {getattr(OpenAI, '__version__', 'unknown')}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.debug(f"Environment variables: { {k: '***' if k == 'OPENAI_API_KEY' else v for k, v in os.environ.items()} }")
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # Removed proxies parameter
        logger.info(f"OpenAI client initialized: {client}")
        
        prompt = f"""
        Create a concise, engaging script for a YouTube Shorts video about '{topic}'.
        The script should be {length} (aim for 30-60 seconds if short, 1-2 minutes if medium, 2-3 minutes if long).
        Use a conversational tone, include a hook to grab attention, and end with a call to action.
        Format the script as plain text with clear sections for the hook, body, and call to action.
        Ensure the script is at least 50 characters long to meet minimum content requirements.
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
                if not script or len(script) < 50:
                    raise ValueError(f"Generated script is too short or empty ({len(script)} characters)")
                
                logger.info(f"Script generated successfully ({len(script)} characters)")
                return script
            
            except Exception as e:
                if attempt < max_retries:
                    sleep_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
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