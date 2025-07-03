import os
import logging
import requests
import json
import time
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
            
        try:
            prompt = (
                f"Create a detailed script (500-1000 characters) for a YouTube Short video "
                f"about '{topic}' in the {category} category. Make it engaging, clear, and "
                f"suitable for a 15-40 second video. Include a hook, detailed body with at least "
                f"3 key facts or points, and a call to action."
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
            logger.info(f"✅ OpenAI script generated: {len(script)} characters")
            return script
            
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {str(e)}")
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
                f"in the {category} category. Include hook, 3 key facts, and call to action."
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
                    logger.info(f"✅ Llama script generated: {len(script)} characters")
                    return script
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
                logger.info(f"✅ Pexels-inspired script generated: {len(script)} characters")
                return script
            return None
            
        except Exception as e:
            logger.warning(f"Pexels generation failed: {str(e)}")
            return None

    def generate_script_fallback(self, topic: str, category: str) -> str:
        """Final fallback if all API methods fail"""
        fallback_scripts = {
            "Nature": (
                f"🌿 Wow, {topic} is incredible! Did you know? Fact 1: {topic} thrives in unique ecosystems. "
                f"Fact 2: It plays a vital role in biodiversity. Fact 3: Its adaptations are mind-blowing! "
                f"What's your favorite nature fact? Subscribe for more! 🌱"
            ),
            "Science": (
                f"🔬 {topic} is groundbreaking! Fact 1: It’s reshaping our understanding of the universe. "
                f"Fact 2: Scientists are uncovering new applications daily. Fact 3: Its potential is limitless! "
                f"What science topic excites you? Hit subscribe! 🧪"
            ),
            "History": (
                f"📚 {topic} changed history! Fact 1: It shaped key events in its era. "
                f"Fact 2: Its legacy influences us today. Fact 3: Hidden stories await discovery! "
                f"What historical fact amazes you? Subscribe now! 🏛️"
            ),
            "Technology": (
                f"💻 {topic} is the future! Fact 1: It’s driving innovation globally. "
                f"Fact 2: New advancements are announced regularly. Fact 3: It’s transforming lives! "
                f"What tech excites you? Subscribe for more! 🚀"
            ),
            "Space": (
                f"🚀 {topic} is out of this world! Fact 1: It reveals cosmic mysteries. "
                f"Fact 2: Scientists study it to understand the universe. Fact 3: Its beauty inspires us all! "
                f"What’s your favorite space fact? Subscribe now! 🌌"
            )
        }
        script = fallback_scripts.get(category, 
            f"🤔 {topic} is fascinating! Fact 1: It’s a key topic in {category}. "
            f"Fact 2: Experts are still exploring its depths. Fact 3: It sparks curiosity everywhere! "
            f"What do you want to learn next? Subscribe! 💭"
        )
        logger.info(f"✅ Fallback script generated: {len(script)} characters")
        return script

    def generate_script(self, topic: str, category: str) -> str:
        """Generate script with multiple fallback options, selecting the longest valid script"""
        logger.info(f"✍️ Generating script for: {topic} ({category})")
        
        scripts = []
        
        # Try OpenAI
        script = self.generate_with_openai(topic, category)
        if script:
            scripts.append(("OpenAI", script))
            
        # Try Llama
        script = self.generate_with_llama(topic, category)
        if script:
            scripts.append(("Llama", script))
                
        # Try Pexels
        script = self.generate_with_pexels(topic, category)
        if script:
            scripts.append(("Pexels", script))
                
        # Always generate fallback
        script = self.generate_script_fallback(topic, category)
        scripts.append(("Fallback", script))
        
        # Select the longest script
        if scripts:
            selected_method, selected_script = max(scripts, key=lambda x: len(x[1]))
            logger.info(f"✅ Selected {selected_method} script: {len(selected_script)} characters")
            return selected_script
        else:
            logger.warning("⚠️ No scripts generated, using fallback")
            script = self.generate_script_fallback(topic, category)
            logger.info(f"✅ Fallback script selected: {len(script)} characters")
            return script

def generate_script(topic: str, category: str) -> str:
    """Public interface for script generation"""
    generator = ScriptGenerator()
    script = generator.generate_script(topic, category)
    if not script or len(script) < 200:  # Minimum threshold to ensure usability
        logger.error("Generated script is invalid or too short, using default fallback")
        script = (
            f"🤔 {topic} is fascinating! Fact 1: It’s a key topic in {category}. "
            f"Fact 2: Experts are still exploring its depths. Fact 3: It sparks curiosity everywhere! "
            f"What do you want to learn next? Subscribe! 💭"
        )
        logger.info(f"✅ Default fallback script: {len(script)} characters")
    return script

if __name__ == "__main__":
    # Test the generator
    test_topic = "Plants That Can Count to Twenty"
    test_category = "Nature"
    
    logger.info("Starting script generation test")
    script = generate_script(test_topic, test_category)
    logger.info(f"Generated Script:\n{script}\nLength: {len(script)}")