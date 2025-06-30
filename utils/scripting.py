import os
from openai import OpenAI

def generate_script(topic: str, max_length: int = 500) -> str:
    """Generate a YouTube Shorts script using OpenAI"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""Write a compelling 60-second YouTube Shorts script about '{topic}'.
Requirements:
- Hook in first 3 seconds
- Engaging facts/information
- Call-to-action at end
- Under {max_length} characters
- Natural, conversational tone"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a viral YouTube Shorts scriptwriter."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.8
        )
        
        script = response.choices[0].message.content.strip()
        
        # Ensure script fits length requirement
        if len(script) > max_length:
            script = script[:max_length].rsplit(' ', 1)[0] + "..."
        
        return script
        
    except Exception as e:
        print(f"Script generation failed: {e}")
        return get_fallback_script(topic)

def get_fallback_script(topic: str) -> str:
    """Fallback script if OpenAI fails"""
    return f"""🔥 Did you know about {topic}?

Here's something amazing: {topic} has incredible secrets most people don't know!

This will blow your mind...

👆 Like if this surprised you!
🔔 Follow for more shocking facts!

#Shorts #{topic.replace(' ', '').lower()}"""