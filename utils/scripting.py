from openai import OpenAI
import os

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_script(topic):
    prompt = f"""Write a short, punchy 60-second YouTube Shorts script based on the topic: '{topic}'.
Start with a strong curiosity hook. Keep the tone mysterious, factual, or nostalgic depending on the topic.
Focus on one interesting fact or story. End with a call-to-action like:
"Did you know this? Comment below." or "Want more hidden facts? Follow for more." 
Do NOT include any affiliate links."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating script: {e}")
        # Fallback script in case of API failure
        return f"""🤔 Did you know about {topic}?

This fascinating piece of history will blow your mind! 

Throughout history, there have been incredible moments that most people never heard about. Today's topic shows us how creative humans can be when solving problems.

The story behind this is absolutely amazing and shows how different things were back then.

What do you think about this? Comment below with your thoughts! 

Follow for more incredible historical facts you've never heard before! 🔥"""