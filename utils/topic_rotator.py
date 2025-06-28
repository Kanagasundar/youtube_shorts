#!/usr/bin/env python3
"""
Topic Rotator - Selects topics based on date rotation
"""

import hashlib
from datetime import datetime

# Diverse topic pool for YouTube Shorts
TOPICS_POOL = [
    # Historical Events
    ("The Day Photography Changed History Forever", "History"),
    ("Ancient Lost City Discovered by Accident", "History"),
    ("The Secret Message That Started WWI", "History"),
    ("Lost Civilization Found in Amazon Rainforest", "History"),
    ("Ancient Roman Concrete Still Stronger Than Modern", "Science"),
    
    # Science & Technology
    ("The Internet Was Almost Called Something Else", "Technology"),
    ("Scientists Accidentally Created Time Crystals", "Science"),
    ("The Sound That Can Kill You Instantly", "Science"),
    ("Why Airplane Windows Are Round Not Square", "Science"),
    ("The Color That Doesn't Actually Exist", "Science"),
    
    # Mysteries & Unexplained
    ("The Ship That Reappeared After 90 Years", "Mystery"),
    ("The Town That Vanished Overnight", "Mystery"),
    ("Radio Signal from Space Repeats Every 16 Days", "Mystery"),
    ("The Door That Should Never Be Opened", "Mystery"),
    ("Antarctica's Blood Falls Mystery Solved", "Mystery"),
    
    # Amazing Facts
    ("Trees Can Actually Talk to Each Other", "Nature"),
    ("Your Body Produces Diamonds Every Day", "Science"),
    ("There's a Place Where Gravity Doesn't Work", "Science"),
    ("Animals That Can Literally See Time", "Nature"),
    ("The Ocean Floor Has WiFi", "Technology"),
    
    # Space & Universe
    ("The Planet Made Entirely of Diamond", "Space"),
    ("Black Hole That Shouldn't Exist", "Space"),
    ("The Sound of Saturn Will Haunt You", "Space"),
    ("Mars Has Snow That's Not Water", "Space"),
    ("Star Older Than the Universe Itself", "Space"),
    
    # Human Body & Mind
    ("Your Brain Deletes Memories While You Sleep", "Health"),
    ("Why You Can't Remember Being Born", "Psychology"),
    ("The Organ That Grows Back Like Magic", "Health"),
    ("Your Eyes Have a Built-in Night Vision", "Health"),
    ("The Emotion That Can Actually Heal You", "Psychology"),
    
    # Technology & Future
    ("AI Just Solved a 50-Year-Old Problem", "Technology"),
    ("The Invention That Accidentally Saved Millions", "Technology"),
    ("Computer Code Found in Human DNA", "Science"),
    ("The App That Can Read Your Thoughts", "Technology"),
    ("Robot That Feels Physical Pain", "Technology"),
    
    # Nature & Environment
    ("Tree That's Been Alive for 5000 Years", "Nature"),
    ("Animal That Never Dies of Old Age", "Nature"),
    ("The Rain That Falls Upward", "Nature"),
    ("Plants That Can Count to Twenty", "Nature"),
    ("The Lake That Kills Everything", "Nature"),
    
    # Pop Culture & Entertainment
    ("Movie Scene That Was Actually Real", "Entertainment"),
    ("Song That Was Banned by Every Country", "Entertainment"),
    ("Actor Who Lived Their Movie Role", "Entertainment"),
    ("Video Game That Predicted the Future", "Entertainment"),
    ("TV Show That Changed Real Laws", "Entertainment"),
    
    # Food & Culture
    ("Food That's Illegal in Most Countries", "Food"),
    ("Ancient Recipe That Still Works Today", "Food"),
    ("Spice Worth More Than Gold", "Food"),
    ("Restaurant That Serves Extinct Animals", "Food"),
    ("Drink That Can Make You Immortal", "Food"),
]

def get_today_topic():
    """
    Get today's topic based on date-based rotation
    Returns: tuple (topic, category)
    """
    # Use current date to determine topic
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Create hash of today's date for consistent daily selection
    date_hash = hashlib.md5(today.encode()).hexdigest()
    
    # Convert hash to index
    topic_index = int(date_hash[:8], 16) % len(TOPICS_POOL)
    
    topic, category = TOPICS_POOL[topic_index]
    
    print(f"🗓️ Date: {today}")
    print(f"🎯 Selected topic index: {topic_index}")
    
    return topic, category

def get_all_topics():
    """Return all available topics for reference"""
    return TOPICS_POOL

def get_topics_by_category(category):
    """Get all topics from a specific category"""
    return [topic for topic, cat in TOPICS_POOL if cat.lower() == category.lower()]

if __name__ == "__main__":
    # Test the topic rotator
    topic, category = get_today_topic()
    print(f"\nToday's Topic: {topic}")
    print(f"Category: {category}")
    
    # Show some stats
    categories = list(set([cat for _, cat in TOPICS_POOL]))
    print(f"\nAvailable categories: {', '.join(categories)}")
    print(f"Total topics: {len(TOPICS_POOL)}")