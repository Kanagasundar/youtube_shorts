#!/usr/bin/env python3
"""
Script Generator - Uses OpenAI to generate engaging YouTube Shorts scripts
"""

import os
import logging
from openai import OpenAI

# Configure logging to match main.py
logger = logging.getLogger(__name__)

def generate_script(topic, category, max_duration=45):
    """
    Generate a YouTube Shorts script using OpenAI
    
    Args:
        topic (str): The topic for the video
        category (str): The category/genre
        max_duration (int): Maximum duration in seconds
        
    Returns:
        str: Generated script
    """
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    if not client.api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Create the prompt for script generation
    prompt = f"""
Create an engaging YouTube Shorts script about: "{topic}"
Category: {category}

Requirements:
- Duration: {max_duration} seconds maximum (about 120-150 words)
- Hook viewers in the first 3 seconds
- Use storytelling format with buildup and payoff
- Include surprising facts or plot twists
- End with a call-to-action for engagement
- Write in an enthusiastic, conversational tone
- Use short, punchy sentences
- Include natural pauses for dramatic effect
- Make it viral-worthy and shareable

Structure:
1. Opening hook (3 seconds)
2. Setup/context (10 seconds)
3. Main revelation/story (25 seconds)
4. Conclusion/impact (5 seconds)
5. Call-to-action (2 seconds)

Write only the script text that will be spoken. No stage directions or formatting.
Make it sound natural when read aloud.
"""

    try:
        logger.info("🤖 Generating script with OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert YouTube Shorts scriptwriter who creates viral, engaging content. Your scripts consistently get millions of views because they hook viewers immediately and keep them watching until the end."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=400,
            temperature=0.8,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        script = response.choices[0].message.content.strip()
        
        # Clean up the script
        script = clean_script(script)
        
        logger.info(f"✅ Script generated successfully ({len(script)} characters)")
        return script
        
    except Exception as e:
        logger.error(f"❌ Error generating script: {e}")
        # Fallback to template-based script
        return generate_fallback_script(topic, category)

def clean_script(script):
    """Clean and format the script"""
    # Remove any unwanted formatting
    script = script.replace('\n\n', '\n')
    script = script.replace('  ', ' ')
    
    # Remove any stage directions or formatting markers
    lines_to_remove = ['[', ']', '(', ')', '*', '#']
    for char in lines_to_remove:
        if script.startswith(char):
            # Remove lines that start with formatting characters
            lines = script.split('\n')
            script = '\n'.join([line for line in lines if not any(line.strip().startswith(c) for c in lines_to_remove)])
    
    return script.strip()

def generate_fallback_script(topic, category):
    """Generate a simple fallback script if OpenAI fails"""
    
    fallback_scripts = {
        "History": f"Did you know that {topic.lower()}? This incredible historical event changed everything. Here's what really happened that most people don't know about. The story begins when... and then something amazing occurred that shocked the world. This discovery proves that history is full of surprises. What do you think about this? Let me know in the comments!",
        
        "Science": f"Scientists just discovered something mind-blowing about {topic.lower()}! This changes everything we thought we knew. The research shows that... and the implications are incredible. This breakthrough could revolutionize how we understand our world. The most shocking part? This was hiding in plain sight all along. What's your theory about this? Share your thoughts below!",
        
        "Technology": f"You won't believe what just happened in tech! {topic} is about to change everything. This innovation works by... and it's already disrupting entire industries. The crazy part is that this technology has been possible for years, but nobody tried it until now. This could be the future we've been waiting for. Are you excited or worried about this? Comment below!",
        
        "Mystery": f"This unsolved mystery will give you chills. {topic} has baffled experts for decades. Here's what we know... But here's the twist that nobody saw coming. The evidence points to something that shouldn't be possible. Scientists are still trying to figure this out. What's your theory? Drop it in the comments and let's solve this together!",
        
        "Nature": f"Nature just blew my mind again! {topic} - and it's more incredible than you think. This phenomenon occurs when... The most amazing part? This happens right under our noses but most people never notice. Scientists say this proves nature is way more intelligent than we realized. Have you ever seen this in person? Tell me about it in the comments!",
    }
    
    script = fallback_scripts.get(category, f"Here's something incredible about {topic}! This amazing fact will change how you see the world. The story goes like this... And the most surprising part is what happened next. This proves that our world is full of wonders waiting to be discovered. What do you think about this? Let me know below!")
    
    logger.info("⚠️ Using fallback script due to API error")
    return script

def estimate_duration(script, words_per_minute=160):
    """Estimate script duration in seconds"""
    word_count = len(script.split())
    duration = (word_count / words_per_minute) * 60
    return round(duration, 1)

if __name__ == "__main__":
    # Test the script generator
    test_topic = "The Day Photography Changed History Forever"
    test_category = "History"
    
    script = generate_script(test_topic, test_category)
    duration = estimate_duration(script)
    
    logger.info(f"\nGenerated Script:")
    logger.info("=" * 50)
    logger.info(script)
    logger.info("=" * 50)
    logger.info(f"Estimated duration: {duration} seconds")
    logger.info(f"Word count: {len(script.split())} words")