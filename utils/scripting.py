import os
import logging
import sys
from datetime import datetime
from typing import Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Predefined topics and categories
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
        # Log environment for debugging
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.debug(f"Environment variables: { {k: '***' if k == 'OPENAI_API_KEY' else v for k, v in os.environ.items()} }")
        
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