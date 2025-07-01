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

def generate_script(topic: str, category: str) -> str:
    """
    Generate a short script for a YouTube Short video using OpenAI's API.
    
    Args:
        topic (str): The topic for the video
        category (str): The category of the video
        
    Returns:
        str: Generated script text
    
    Raises:
        ValueError: If the generated script is too short or invalid
        Exception: For other OpenAI API or runtime errors
    """
    logger.info(f"✍️ Generating script for topic: {topic}, category: {category}")
    
    try:
        # Initialize OpenAI client without proxies
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = OpenAI(api_key=api_key)  # Explicitly no proxies argument
        
        # Create prompt
        prompt = (
            f"Create a concise script (150-250 characters) for a YouTube Short video "
            f"about '{topic}' in the {category} category. Make it engaging, clear, and "
            f"suitable for a 15-60 second video. Include a hook, body, and call to action."
        )
        
        # Generate script using OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,  # Increased for longer scripts
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        
        # Check script length (aligned with main.py's 50-character threshold)
        if len(script) < 50:
            raise ValueError(f"Generated script too short: {len(script)} characters")
        
        logger.info(f"✅ Script generated successfully ({len(script)} characters)")
        logger.debug(f"Script content: {script}")
        return script
    
    except ValueError as ve:
        logger.error(f"❌ Failed to generate script due to invalid input: {str(ve)}")
        raise  # Re-raise to allow retry in main.py
    except Exception as e:
        logger.error(f"❌ Failed to generate script: {str(e)}")
        raise  # Re-raise to allow retry in main.py

if __name__ == "__main__":
    # Test the function
    test_topic = "Plants That Can Count to Twenty"
    test_category = "Nature"
    try:
        script = generate_script(test_topic, test_category)
        print(f"Script: {script} (Length: {len(script)})")
    except Exception as e:
        print(f"Test failed: {e}")