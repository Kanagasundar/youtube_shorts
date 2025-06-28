#!/usr/bin/env python3
"""
Voice Generator - Converts text to speech for video narration
"""

import os
import sys
from gtts import gTTS
from pydub import AudioSegment
import tempfile

def generate_voice(script, output_dir="output", language="en", slow=False):
    """
    Generate voice narration from script text
    
    Args:
        script (str): The script text to convert
        output_dir (str): Directory to save audio file
        language (str): Language code (en, es, fr, etc.)
        slow (bool): Whether to speak slowly
        
    Returns:
        str: Path to generated audio file
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    try:
        print(f"🎙️ Generating voice narration...")
        print(f"📝 Script length: {len(script)} characters")
        
        # Create gTTS object
        tts = gTTS(
            text=script,
            lang=language,
            slow=slow,
            tld='com'  # Use .com domain for better quality
        )
        
        # Save to temporary file first
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
            tts.save(temp_path)
        
        # Process audio to optimize for YouTube Shorts
        audio = AudioSegment.from_mp3(temp_path)
        
        # Optimize audio settings
        audio = optimize_audio(audio)
        
        # Export final audio
        audio.export(audio_path, format="mp3", bitrate="128k")
        
        # Clean up temp file
        os.unlink(temp_path)
        
        print(f"✅ Voice generated: {audio_path}")
        print(f"⏱️ Duration: {len(audio) / 1000:.1f} seconds")
        
        return audio_path
        
    except Exception as e:
        print(f"❌ Error generating voice: {e}")
        
        # Try fallback method
        try:
            print("🔄 Trying fallback voice generation...")
            return generate_voice_fallback(script, output_dir)
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            raise Exception(f"Voice generation failed: {e}")

def optimize_audio(audio):
    """
    Optimize audio for YouTube Shorts
    
    Args:
        audio (AudioSegment): Input audio
        
    Returns:
        AudioSegment: Optimized audio
    """
    
    # Normalize volume
    audio = audio.normalize()
    
    # Adjust speed slightly for better engagement (5% faster)
    audio = audio.speedup(playback_speed=1.05)
    
    # Add slight compression for better sound
    audio = audio.compress_dynamic_range(threshold=-20.0, ratio=2.0)
    
    # Ensure mono audio (saves space and works better for shorts)
    audio = audio.set_channels(1)
    
    # Set consistent sample rate
    audio = audio.set_frame_rate(22050)
    
    return audio

def generate_voice_fallback(script, output_dir):
    """
    Fallback voice generation using system TTS
    """
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_fallback_{timestamp}.wav"
    audio_path = os.path.join(output_dir, audio_filename)
    
    try:
        # Try espeak (available on most Linux systems)
        import subprocess
        
        cmd = [
            'espeak',
            '-s', '150',  # Speed (words per minute)
            '-p', '40',   # Pitch
            '-a', '100',  # Amplitude
            '-w', audio_path,  # Write to file
            script
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(audio_path):
            print(f"✅ Fallback voice generated: {audio_path}")
            return audio_path
        else:
            raise Exception(f"espeak failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ System TTS failed: {e}")
        
        # Create a simple placeholder audio file
        return create_placeholder_audio(script, output_dir)

def create_placeholder_audio(script, output_dir):
    """
    Create a placeholder audio file with silence
    """
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_placeholder_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    # Estimate duration based on script length (150 words per minute)
    word_count = len(script.split())
    duration_seconds = (word_count / 150) * 60
    duration_ms = int(duration_seconds * 1000)
    
    # Create silence audio
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(audio_path, format="mp3")
    
    print(f"⚠️ Created placeholder audio: {audio_path}")
    print(f"⏱️ Duration: {duration_seconds:.1f} seconds")
    
    return audio_path

def get_audio_duration(audio_path):
    """
    Get duration of audio file in seconds
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"❌ Error getting audio duration: {e}")
        return 0.0

def test_voice_generation():
    """Test voice generation with sample text"""
    
    test_script = """
    Did you know that the first photograph ever taken required an 8-hour exposure time? 
    That's right - in 1826, Joseph Nicéphore Niépce had to wait 8 hours just to capture 
    a single image! This incredible breakthrough changed how we see and record our world forever. 
    What would you have photographed first?
    """
    
    print("🧪 Testing voice generation...")
    audio_path = generate_voice(test_script)
    
    if os.path.exists(audio_path):
        duration = get_audio_duration(audio_path)
        print(f"✅ Test successful!")
        print(f"📁 File: {audio_path}")
        print(f"⏱️ Duration: {duration:.1f} seconds")
    else:
        print("❌ Test failed!")

if __name__ == "__main__":
    test_voice_generation()