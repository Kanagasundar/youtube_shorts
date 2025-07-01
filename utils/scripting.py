import os
import logging
import requests
import json
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
        
        # Initialize OpenAI client if API key exists
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            except Exception as e:
                logger.warning(f"OpenAI client initialization warning: {str(e)}")

    def generate_with_openai(self, topic: str, category: str) -> Optional[str]:
        """Generate script using OpenAI"""
        if not self.openai_client:
            return None
            
        try:
            prompt = (
                f"Create a concise script (150-250 characters) for a YouTube Short video "
                f"about '{topic}' in the {category} category. Make it engaging, clear, and "
                f"suitable for a 15-60 second video. Include a hook, body, and call to action."
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative scriptwriter for YouTube Shorts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            script = response.choices[0].message.content.strip()
            if len(script) >= 50:
                logger.info("✅ OpenAI script generated successfully")
                return script
            return None
            
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {str(e)}")
            return None

    def generate_with_llama(self, topic: str, category: str) -> Optional[str]:
        """Generate script using free Llama API (Replicate)"""
        try:
            # Using Replicate's free tier for Llama
            api_url = "https://api.replicate.com/v1/predictions"
            headers = {
                "Authorization": f"Token {os.getenv('REPLICATE_API_KEY', '')}",
                "Content-Type": "application/json"
            }
            
            prompt = (
                f"Create a short YouTube script (under 250 characters) about {topic} "
                f"in the {category} category. Include hook, body and call to action."
            )
            
            payload = {
                "version": "a16z-infra/llama7b-v2-chat:4f0a4744c7295c024a1de15e1a63c880d3da035fa1f49bfd344fe076074c8eea",
                "input": {
                    "prompt": prompt,
                    "max_length": 150,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result_url = response.json()["urls"]["get"]
            for _ in range(5):  # Poll for result
                result_response = requests.get(result_url, headers=headers, timeout=30)
                if result_response.json()["status"] == "succeeded":
                    script = " ".join(result_response.json()["output"]).strip()
                    if len(script) >= 50:
                        logger.info("✅ Llama script generated successfully")
                        return script
                    break
                time.sleep(2)
            return None
            
        except Exception as e:
            logger.warning(f"Llama generation failed: {str(e)}")
            return None

    def generate_with_pegasus(self, topic: str, category: str) -> Optional[str]:
        """Generate script using Hugging Face's Pegasus model"""
        try:
            api_url = "https://api-inference.huggingface.co/models/google/pegasus-xsum"
            headers = {
                "Authorization": f"Bearer {os.getenv('HF_API_KEY', '')}",
                "Content-Type": "application/json"
            }
            
            input_text = (
                f"Summarize this topic for a YouTube Short: {topic} in {category} category. "
                "Keep it under 250 characters with hook, body and call to action."
            )
            
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": input_text},
                timeout=30
            )
            response.raise_for_status()
            
            script = response.json()[0]["summary_text"].strip()
            if len(script) >= 50:
                logger.info("✅ Pegasus script generated successfully")
                return script
            return None
            
        except Exception as e:
            logger.warning(f"Pegasus generation failed: {str(e)}")
            return None

    def generate_with_pexels(self, topic: str, category: str) -> Optional[str]:
        """Generate a simple script based on Pexels search results"""
        if not self.pexels_api_key:
            return None
            
        try:
            # First get related images to inspire the script
            search_url = f"https://api.pexels.com/v1/search?query={topic}&per_page=1"
            headers = {"Authorization": self.pexels_api_key}
            
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            photos = response.json().get("photos", [])
            if photos:
                photo_desc = photos[0].get("alt", topic)
                script = (
                    f"Check this out: {photo_desc}. "
                    f"Amazing {category} content coming your way! "
                    f"Like and subscribe for more about {topic}!"
                )
                if len(script) >= 50:
                    logger.info("✅ Pexels-inspired script generated")
                    return script
            return None
            
        except Exception as e:
            logger.warning(f"Pexels generation failed: {str(e)}")
            return None

    def generate_script_fallback(self, topic: str, category: str) -> str:
        """Final fallback if all API methods fail"""
        fallback_scripts = {
            "Nature": f"🌿 Did you know? {topic}! Nature never stops amazing us. What's the most surprising nature fact you know? Share below! 🌱",
            "Science": f"🔬 Fact: {topic}! Science reveals amazing mysteries. What scientific discovery fascinates you most? 🧪",
            "History": f"📚 History fact: {topic}! The past shapes our present. What historical event interests you? 🏛️",
            "Technology": f"💻 Tech: {topic}! Innovation never stops. What tech excites you? 🚀",
            "Space": f"🚀 Space fact: {topic}! The universe is full of wonders. What space mystery intrigues you? 🌌"
        }
        return fallback_scripts.get(category, 
            f"🤔 Fact: {topic}! Always something new to learn. What should we explore next? 💭")

    def generate_script(self, topic: str, category: str) -> str:
        """Generate script with multiple fallback options"""
        logger.info(f"✍️ Generating script for: {topic} ({category})")
        
        # Try OpenAI first
        script = self.generate_with_openai(topic, category)
        if script:
            return script
            
        # Try free alternatives
        for method in [
            self.generate_with_llama,
            self.generate_with_pegasus,
            self.generate_with_pexels
        ]:
            script = method(topic, category)
            if script:
                return script
                
        # Final fallback
        logger.warning("⚠️ All API methods failed, using local fallback")
        return self.generate_script_fallback(topic, category)

def generate_script(topic: str, category: str) -> str:
    """Public interface for script generation"""
    return ScriptGenerator().generate_script(topic, category)

if __name__ == "__main__":
    # Test the generator
    test_topic = "Plants That Can Count to Twenty"
    test_category = "Nature"
    
    generator = ScriptGenerator()
    script = generator.generate_script(test_topic, test_category)
    print(f"Generated Script:\n{script}\nLength: {len(script)}")