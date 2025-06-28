from openai import OpenAI
import os

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_script(topic):
    prompt = f"""Write a short, punchy 60-second YouTube Shorts script based on the topic: '{topic}'.
Start with a strong curiosity hook. Keep the tone mysterious, factual, or nostalgic depending on the topic.
Focus on one interesting fact or story. End with a call-to-action like:
"Did you know this? Comment below." or "Want more hidden facts? Follow for more." 
Do NOT include any affiliate links."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()