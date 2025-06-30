import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

def generate_script(topic: str) -> str:
    """Generate a short video script for the given topic using OpenAI"""
    logger.info(f"✍️ Generating script for topic: {topic}")
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = (
            f"Create a concise YouTube Shorts script (150-200 characters) for the topic '{topic}'. "
            "Include a hook, a brief fact or insight, and a call to action. "
            "Format as: Hook: [hook]. Fact: [fact]. Call to Action: [CTA]."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        logger.info(f"✅ Script generated successfully ({len(script)} characters)")
        return script
    
    except Exception as e:
        logger.error(f"❌ Failed to generate script: {str(e)}")
        logger.debug("Stack trace:", exc_info=True)
        # Fallback script
        fallback = (
            f"Hook: Did you know about {topic.lower()}? "
            f"Fact: It's a fascinating topic with surprising details! "
            f"Learn more about {topic.lower()} and why it matters. "
            "Call to Action: Subscribe for more! #Shorts"
        )
        logger.info(f"✅ Using fallback script ({len(fallback)} characters)")
        return fallback
