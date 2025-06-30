import os
import logging
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_script(topic, max_length=500):
    """
    Generate a short script for a YouTube Shorts video using OpenAI.
    
    Args:
        topic (str): The topic for the script.
        max_length (int): Maximum length of the script in characters.
    
    Returns:
        str: Generated script or None if generation fails.
    """
    try:
        logger.info("✍️ Generating script...")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = (
            f"Write a concise script for a YouTube Shorts video (60 seconds or less) about '{topic}'. "
            "The script should be engaging, informative, and under 500 characters. "
            "Include a hook to grab attention and a call-to-action at the end."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        if len(script) > max_length:
            script = script[:max_length].rsplit(' ', 1)[0] + "..."
        
        logger.info(f"✅ Script generated ({len(script)} characters)")
        return script
    
    except Exception as e:
        logger.error(f"❌ Failed to generate script: {str(e)}", exc_info=True)
        return None

def get_fallback_script(topic):
    """
    Provide a fallback script if OpenAI generation fails.
    
    Args:
        topic (str): The topic for the script.
    
    Returns:
        str: Fallback script.
    """
    logger.info("✅ Using fallback script")
    return (
        f"Hook: Did you know about {topic}? "
        f"Fact: It's a fascinating topic with surprising details! "
        f"Learn more about {topic} and why it matters. "
        f"Subscribe for more! #Shorts"
    )