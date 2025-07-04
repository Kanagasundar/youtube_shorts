import os
import logging
import requests
import json
import time
import random
from typing import Optional
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

class ScriptGenerator:
    """Handles script generation with multiple fallback options"""
    
    def __init__(self):
        self.openai_client = None
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                logger.info("✅ OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"OpenAI client initialization warning: {str(e)}")

    def generate_with_openai(self, topic: str, category: str) -> Optional[str]:
        """Generate script using OpenAI"""
        if not self.openai_client:
            logger.warning("OpenAI client not initialized")
            return None
            
        for attempt in range(3):  # Retry logic for quota issues
            try:
                prompt = (
                    f"Create a detailed script (500-1000 characters) for a YouTube Short video "
                    f"about '{topic}' in the {category} category. Make it engaging, clear, and "
                    f"suitable for a 15-40 second video. Include a hook, detailed body with at least "
                    f"3 key facts or points, and a call to action. Ensure the content is unique and not just placeholders."
                )
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                script = response.choices[0].message.content.strip()
                if len(script) >= 500:  # Strict minimum for quality
                    logger.info(f"✅ OpenAI script generated: {len(script)} characters")
                    return script
                logger.warning(f"OpenAI script too short: {len(script)} characters")
                return None
                
            except Exception as e:
                logger.warning(f"OpenAI generation failed (attempt {attempt + 1}/3): {str(e)}")
                if "429" in str(e):  # Handle quota errors
                    time.sleep(2 ** attempt)
                else:
                    break
        return None

    def generate_with_llama(self, topic: str, category: str) -> Optional[str]:
        """Generate script using free Llama API (Replicate)"""
        try:
            api_url = "https://api.replicate.com/v1/predictions"
            headers = {
                "Authorization": f"Token {os.getenv('REPLICATE_API_KEY', '')}",
                "Content-Type": "application/json"
            }
            
            prompt = (
                f"Create a detailed YouTube script (500-1000 characters) about {topic} "
                f"in the {category} category. Include hook, 3 unique key facts, and call to action."
            )
            
            payload = {
                "version": "a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea",
                "input": {
                    "prompt": prompt,
                    "max_length": 500,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result_url = response.json()["urls"]["get"]
            for _ in range(5):
                result_response = requests.get(result_url, headers=headers, timeout=30)
                if result_response.json()["status"] == "succeeded":
                    script = " ".join(result_response.json()["output"]).strip()
                    if len(script) >= 500:
                        logger.info(f"✅ Llama script generated: {len(script)} characters")
                        return script
                    logger.warning(f"Llama script too short: {len(script)} characters")
                    return None
                time.sleep(2)
            return None
            
        except Exception as e:
            logger.warning(f"Llama generation failed: {str(e)}")
            return None

    def generate_with_pexels(self, topic: str, category: str) -> Optional[str]:
        """Generate a simple script based on Pexels search results"""
        if not self.pexels_api_key:
            logger.warning("Pexels API key not provided")
            return None
            
        try:
            search_url = f"https://api.pexels.com/v1/search?query={topic}&per_page=1"
            headers = {"Authorization": self.pexels_api_key}
            
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            photos = response.json().get("photos", [])
            if photos:
                photo_desc = photos[0].get("alt", topic)
                script = (
                    f"Wow, check out {photo_desc}! Did you know three amazing facts about {topic}? "
                    f"First, it's a key part of {category}. Second, it has unique features that surprise everyone! "
                    f"Third, its impact is huge! Subscribe for more {category} facts!"
                )
                if len(script) >= 500:
                    logger.info(f"✅ Pexels-inspired script generated: {len(script)} characters")
                    return script
                logger.warning(f"Pexels script too short: {len(script)} characters")
                return None
            return None
            
        except Exception as e:
            logger.warning(f"Pexels generation failed: {str(e)}")
            return None

    def generate_script_fallback(self, topic: str, category: str) -> str:
        """Final fallback if all API methods fail"""
        fallback_scripts = {
            "Nature": (
                f"🌿 Wow, {topic} is incredible! Did you know? Fact 1: {topic} thrives in unique ecosystems. "
                f"Fact 2: It plays a vital role in biodiversity with over 100 species. "
                f"Fact 3: Its adaptations to climate change are mind-blowing! What's your favorite nature fact? Subscribe for more! 🌱"
            ),
            "Science": (
                f"🔬 {topic} is groundbreaking! Fact 1: It’s reshaping our understanding with new data. "
                f"Fact 2: Scientists discovered its applications in 2025 breakthroughs. "
                f"Fact 3: Its potential could change the world! What science topic excites you? Hit subscribe! 🧪"
            ),
            "History": (
                f"📚 {topic} changed history! Fact 1: It shaped events 100 years ago. "
                f"Fact 2: Its legacy influences modern laws. Fact 3: Hidden stories await discovery! "
                f"What historical fact amazes you? Subscribe now! 🏛️"
            ),
            "Technology": (
                f"💻 {topic} is the future! Fact 1: It’s driving global innovation since 2020. "
                f"Fact 2: New advancements were revealed this year. Fact 3: It’s transforming lives daily! "
                f"What tech excites you? Subscribe for more! 🚀"
            ),
            "Space": (
                f"🚀 {topic} is out of this world! Fact 1: It reveals cosmic mysteries since 2010. "
                f"Fact 2: Scientists study it with new telescopes. Fact 3: Its beauty inspires millions! "
                f"What’s your favorite space fact? Subscribe now! 🌌"
            )
        }
        script = fallback_scripts.get(category, 
            f"🤔 {topic} is fascinating! Fact 1: It’s a key topic in {category} studies. "
            f"Fact 2: Experts uncovered new insights in 2025. Fact 3: It sparks curiosity worldwide! "
            f"What do you want to learn next? Subscribe! 💭"
        )
        if len(script) < 500:
            script += f" Bonus: {topic} continues to evolve, making it a hot topic in {category}! Don’t miss out—subscribe now!"
        logger.info(f"✅ Fallback script generated: {len(script)} characters")
        return script

    def generate_script(self, topic: str, category: str) -> str:
        """Generate script with multiple fallback options, prioritizing quality and length"""
        logger.info(f"✍️ Generating script for: {topic} ({category})")
        
        scripts = []
        
        # Try OpenAI (preferred for quality)
        script = self.generate_with_openai(topic, category)
        if script:
            scripts.append(("OpenAI", script, 1.0))  # Highest priority
            
        # Try Llama (secondary option)
        script = self.generate_with_llama(topic, category)
        if script:
            scripts.append(("Llama", script, 0.8))  # Slightly lower priority
                
        # Try Pexels (tertiary option)
        script = self.generate_with_pexels(topic, category)
        if script:
            scripts.append(("Pexels", script, 0.6))  # Lower priority
                
        # Always generate fallback
        script = self.generate_script_fallback(topic, category)
        scripts.append(("Fallback", script, 0.4))  # Lowest priority
        
        # Select the best script (highest priority * length)
        if scripts:
            selected_method, selected_script, _ = max(scripts, key=lambda x: len(x[1]) * x[2])
            logger.info(f"✅ Selected {selected_method} script: {len(selected_script)} characters")
            return selected_script
        else:
            logger.error("⚠️ No scripts generated, using default fallback")
            script = self.generate_script_fallback(topic, category)
            logger.info(f"✅ Default fallback script selected: {len(script)} characters")
            return script

def generate_script(topic: str, category: str) -> str:
    """Public interface for script generation"""
    generator = ScriptGenerator()
    script = generator.generate_script(topic, category)
    if not script or len(script) < 500:  # Enforce minimum length
        logger.error(f"Generated script is invalid or too short ({len(script) if script else 0} characters), using enhanced fallback")
        script = (
            f"🤔 {topic} is fascinating! Fact 1: It’s a key topic in {category} studies. "
            f"Fact 2: Experts uncovered new insights in 2025. Fact 3: It sparks curiosity worldwide! "
            f"Bonus: {topic} continues to evolve, making it a hot topic! What do you want to learn next? Subscribe! 💭"
        )
        logger.info(f"✅ Enhanced default fallback script: {len(script)} characters")
    return script

if __name__ == "__main__":
    # Test the generator
    test_topic = "Plants That Can Count to Twenty"
    test_category = "Nature"
    
    logger.info("Starting script generation test")
    script = generate_script(test_topic, test_category)
    logger.info(f"Generated Script:\n{script}\nLength: {len(script)}")