import os
import logging
from typing import Optional
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

def generate_script(topic: str, length: str = "short") -> Optional[str]:
    """
    Generate a script for a YouTube Short using OpenAI's API.
    
    Args:
        topic (str): The topic for the video script.
        length (str): The desired length of the script ("short", "medium", "long").
    
    Returns:
        Optional[str]: The generated script, or None if generation fails.
    """
    try:
        logger.info("Initializing OpenAI client")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Define script length parameters
        length_params = {
            "short": {"max_tokens": 150, "script_length": "15-30 seconds"},
            "medium": {"max_tokens": 300, "script_length": "30-60 seconds"},
            "long": {"max_tokens": 500, "script_length": "60-90 seconds"}
        }
        
        if length not in length_params:
            logger.warning(f"Invalid length '{length}'. Using 'short' as default.")
            length = "short"
        
        params = length_params[length]
        
        prompt = f"""
        Create a YouTube Shorts script about "{topic}" for a {params['script_length']} video.
        The script should have:
        1. A hook to grab attention (1-2 sentences).
        2. A brief body with 2-3 key points or facts.
        3. A call to action (e.g., like, subscribe, or comment).
        Keep the tone engaging, concise, and suitable for a short video format.
        """
        
        logger.info(f"Generating script for topic: {topic} (length: {length})")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=params["max_tokens"],
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        
        if not script:
            logger.error("Generated script is empty")
            return None
            
        logger.info(f"Script generated successfully ({len(script)} characters)")
        return script
        
    except Exception as e:
        logger.error(f"Failed to generate script: {str(e)}", exc_info=True)
        return None