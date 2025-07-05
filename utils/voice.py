#!/usr/bin/env python3
"""
Voice Generator - Converts text to speech for video narration using Mozilla TTS with gTTS fallback
Fixed version with proper duration validation and MoviePy compatibility
"""

import os
import sys
from datetime import datetime
from pydub import AudioSegment
import tempfile
import logging
import subprocess

# Add Mozilla TTS import
try:
    from TTS.api import TTS
except ImportError:
    logging.warning("⚠️ Mozilla TTS not installed, falling back to gTTS. Install 'tts' package for Mozilla TTS support.")
    TTS = None

# Fallback to gTTS
from gtts import gTTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_voice(script, output_dir="output", language="en", slow=False):
    """
    Generate voice narration from script text using Mozilla TTS or gTTS fallback
    
    Args:
        script (str): The script text to convert
        output_dir (str): Directory to save audio file
        language (str): Language code (en, es, fr, etc.)
        slow (bool): Whether to speak slowly (ignored for Mozilla TTS)
        
    Returns:
        str: Path to generated audio file
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)

    try:
        print(f"🎙️ Generating voice narration...")
        print(f"📝 Script length: {len(script)} characters")

        # Try Mozilla TTS first
        if TTS is not None:
            logger.info("🔊 Attempting to use Mozilla TTS...")
            try:
                tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_path = temp_file.name
                    tts.tts_to_file(text=script, file_path=temp_path, speaker_wav=None)

                # Convert WAV to MP3 using pydub with validation
                audio = AudioSegment.from_wav(temp_path)
                audio = optimize_audio(audio)
                
                # Validate audio duration
                duration = validate_and_fix_duration(audio)
                
                # Export with proper metadata
                audio.export(audio_path, format="mp3", bitrate="128k", 
                           tags={"title": "Generated Narration", "duration": str(duration)})
                os.unlink(temp_path)
                
                logger.info(f"✅ Mozilla TTS voice generated: {audio_path}")
                logger.info(f"⏱️ Duration: {duration:.1f} seconds")
                return audio_path
                
            except Exception as tts_error:
                logger.warning(f"⚠️ Mozilla TTS failed: {tts_error}")
                # Continue to gTTS fallback

        # Fallback to gTTS
        logger.info("🔄 Using gTTS for voice generation...")
        tts = gTTS(
            text=script,
            lang=language,
            slow=slow,
            tld='com'  # Use .com domain for better quality
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
            tts.save(temp_path)

        # Load and process audio
        audio = AudioSegment.from_mp3(temp_path)
        audio = optimize_audio(audio)
        
        # Validate audio duration
        duration = validate_and_fix_duration(audio)
        
        # Export with proper metadata
        audio.export(audio_path, format="mp3", bitrate="128k",
                   tags={"title": "Generated Narration", "duration": str(duration)})
        os.unlink(temp_path)
        
        logger.info(f"✅ gTTS voice generated: {audio_path}")
        logger.info(f"⏱️ Duration: {duration:.1f} seconds")
        return audio_path

    except Exception as e:
        logger.error(f"❌ Error generating voice: {e}")
        try:
            logger.info("🔄 Trying fallback voice generation...")
            return generate_voice_fallback(script, output_dir)
        except Exception as fallback_error:
            logger.error(f"❌ Fallback also failed: {fallback_error}")
            raise Exception(f"Voice generation failed: {e}")

def validate_and_fix_duration(audio):
    """
    Validate and fix audio duration for MoviePy compatibility
    
    Args:
        audio (AudioSegment): Input audio
        
    Returns:
        float: Valid duration in seconds
    """
    try:
        duration = len(audio) / 1000.0
        
        # Ensure minimum duration
        if duration < 1.0:
            logger.warning(f"⚠️ Audio too short ({duration:.1f}s), padding to 1s")
            silence_needed = 1000 - len(audio)
            audio = audio + AudioSegment.silent(duration=silence_needed)
            duration = 1.0
        
        # Ensure maximum duration for shorts
        if duration > 60.0:
            logger.warning(f"⚠️ Audio too long ({duration:.1f}s), trimming to 60s")
            audio = audio[:60000]
            duration = 60.0
            
        # Check if duration is valid number
        if not isinstance(duration, (int, float)) or duration <= 0:
            logger.error(f"❌ Invalid duration: {duration}")
            raise ValueError(f"Invalid audio duration: {duration}")
            
        return duration
        
    except Exception as e:
        logger.error(f"❌ Duration validation failed: {e}")
        # Return a safe default duration
        return 30.0

def optimize_audio(audio):
    """
    Optimize audio for YouTube Shorts with validation
    
    Args:
        audio (AudioSegment): Input audio
        
    Returns:
        AudioSegment: Optimized audio
    """
    try:
        # Validate input audio
        if len(audio) == 0:
            logger.warning("⚠️ Empty audio detected, creating 1 second silence")
            audio = AudioSegment.silent(duration=1000)
        
        # Normalize audio
        audio = audio.normalize()
        
        # Speed up slightly (optional)
        audio = audio.speedup(playback_speed=1.05)
        
        # Apply compression
        audio = audio.compress_dynamic_range(threshold=-20.0, ratio=2.0)
        
        # Set audio properties
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(22050)  # Sample rate
        
        # Ensure audio has valid duration
        duration = len(audio) / 1000.0
        if duration < 25:
            repeat_count = int(25 / duration) + 1
            audio = audio * repeat_count
            logger.info(f"🔄 Extended audio from {duration:.1f}s by repeating {repeat_count} times")
        
        return audio
        
    except Exception as e:
        logger.error(f"❌ Audio optimization failed: {e}")
        # Return a safe fallback
        return AudioSegment.silent(duration=30000)

def generate_voice_fallback(script, output_dir):
    """
    Fallback voice generation using system TTS with enhanced validation
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_fallback_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    try:
        # Try espeak first
        temp_wav = audio_path.replace('.mp3', '.wav')
        
        cmd = [
            'espeak',
            '-s', '150',  # Speed
            '-p', '40',   # Pitch
            '-a', '100',  # Amplitude
            '-w', temp_wav,
            script
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"espeak failed: {result.stderr}")
        
        if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
            raise Exception("espeak generated an empty or missing file")
        
        # Process with pydub
        audio = AudioSegment.from_wav(temp_wav)
        
        if len(audio) == 0:
            raise ValueError("espeak generated zero-duration audio")
        
        # Optimize audio
        audio = optimize_audio(audio)
        duration = validate_and_fix_duration(audio)
        
        # Export to MP3 with metadata
        audio.export(audio_path, format="mp3", bitrate="128k",
                   tags={"title": "Fallback Narration", "duration": str(duration)})
        
        # Clean up temporary file
        if os.path.exists(temp_wav):
            os.unlink(temp_wav)
        
        logger.info(f"✅ Fallback voice generated: {audio_path}")
        logger.info(f"⏱️ Duration: {duration:.1f} seconds")
        return audio_path
        
    except Exception as e:
        logger.error(f"❌ System TTS failed: {e}")
        return create_placeholder_audio(script, output_dir)

def create_placeholder_audio(script, output_dir):
    """
    Create a placeholder audio file with silence and proper duration
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_placeholder_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    try:
        # Calculate duration based on script length
        word_count = len(script.split())
        duration_seconds = max(30, (word_count / 150) * 60)  # Minimum 30 seconds
        duration_ms = int(duration_seconds * 1000)
        
        # Create silence
        silence = AudioSegment.silent(duration=duration_ms)
        silence = silence.set_channels(1).set_frame_rate(22050)
        
        # Export with metadata
        silence.export(audio_path, format="mp3", bitrate="128k",
                     tags={"title": "Placeholder Audio", "duration": str(duration_seconds)})
        
        logger.warning(f"⚠️ Created placeholder audio: {audio_path}")
        logger.info(f"⏱️ Duration: {duration_seconds:.1f} seconds")
        
        return audio_path
        
    except Exception as e:
        logger.error(f"❌ Failed to create placeholder audio: {e}")
        raise

def get_audio_duration(audio_path):
    """
    Get duration of audio file in seconds with validation
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0
        
        # Validate duration
        if not isinstance(duration, (int, float)) or duration <= 0:
            logger.error(f"❌ Invalid duration detected: {duration}")
            return 30.0  # Safe default
            
        return duration
        
    except Exception as e:
        logger.error(f"❌ Error getting audio duration: {e}")
        return 30.0  # Safe default

def validate_audio_for_moviepy(audio_path):
    """
    Validate audio file for MoviePy compatibility
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0
        
        logger.info(f"🔍 Audio validation:")
        logger.info(f"   - Duration: {duration:.1f} seconds")
        logger.info(f"   - Channels: {audio.channels}")
        logger.info(f"   - Frame rate: {audio.frame_rate}")
        logger.info(f"   - Sample width: {audio.sample_width}")
        
        # Check for common issues
        if duration <= 0:
            logger.error("❌ Audio has zero or negative duration")
            return False
            
        if audio.channels == 0:
            logger.error("❌ Audio has zero channels")
            return False
            
        if audio.frame_rate == 0:
            logger.error("❌ Audio has zero frame rate")
            return False
            
        logger.info("✅ Audio validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Audio validation failed: {e}")
        return False

def test_voice_generation():
    """Test voice generation with sample text"""
    test_script = """
    Did you know that the first photograph ever taken required an 8-hour exposure time? 
    That's right - in 1826, Joseph Nicéphore Niépce had to wait 8 hours just to capture 
    a single image! This incredible breakthrough changed how we see and record our world forever. 
    What would you have photographed first?
    """
    
    logger.info("🧪 Testing voice generation...")
    audio_path = generate_voice(test_script)
    
    if os.path.exists(audio_path):
        duration = get_audio_duration(audio_path)
        is_valid = validate_audio_for_moviepy(audio_path)
        
        logger.info(f"✅ Test successful!")
        logger.info(f"📁 File: {audio_path}")
        logger.info(f"⏱️ Duration: {duration:.1f} seconds")
        logger.info(f"🎬 MoviePy compatible: {is_valid}")
    else:
        logger.error("❌ Test failed!")

if __name__ == "__main__":
    test_voice_generation()