import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_script(topic, category):
    """
    Generate a short script for a YouTube Short video using OpenAI's API.
    
    Args:
        topic (str): The topic for the video
        category (str): The category of the video
        
    Returns:
        str: Generated script text
    """
    logger.info(f"✍️ Generating script for topic: {topic}")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Create prompt
        prompt = (
            f"Create a concise script (150-250 characters) for a YouTube Short video "
            f"about '{topic}' in the {category} category. Make it engaging, clear, and "
            f"suitable for a 15-60 second video."
        )
        
        # Generate script using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        
        if len(script) < 100:
            logger.warning(f"Script too short ({len(script)} characters), retrying...")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                    {"role": "user", "content": prompt + " Ensure the script is at least 100 characters."}
                ],
                max_tokens=60,
                temperature=0.8
            )
            script = response.choices[0].message.content.strip()
        
        logger.info(f"✅ Script generated ({len(script)} characters)")
        return script
    
    except Exception as e:
        logger.error(f"❌ Failed to generate script: {str(e)}")
        # Fallback script
        fallback_script = (
            f"Did you know about {topic}? It's fascinating! Learn more in this quick {category} Short!"
        )
        logger.info(f"✅ Using fallback script ({len(fallback_script)} characters)")
        return fallback_script