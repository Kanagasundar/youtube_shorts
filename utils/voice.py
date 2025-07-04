#!/usr/bin/env python3
"""
Voice Generator - Converts text to speech for video narration using Mozilla TTS with gTTS fallback
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
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_path = temp_file.name
                tts.tts_to_file(text=script, file_path=temp_path, speaker_wav=None)

            # Convert WAV to MP3 using pydub
            audio = AudioSegment.from_wav(temp_path)
            audio = optimize_audio(audio)
            duration = len(audio) / 1000.0

            # Check duration and repeat if less than 25 seconds
            if duration < 25:
                repeat_count = int(25 / duration) + 1
                audio = audio * repeat_count
                logger.warning(f"⚠️ Duration {duration:.1f}s too short, repeating {repeat_count} times")
                duration = len(audio) / 1000.0

            audio.export(audio_path, format="mp3", bitrate="128k")
            os.unlink(temp_path)
            logger.info(f"✅ Mozilla TTS voice generated: {audio_path}")
            logger.info(f"⏱️ Duration: {duration:.1f} seconds")
            return audio_path

        # Fallback to gTTS if Mozilla TTS is not available or fails
        logger.warning("⚠️ Falling back to gTTS due to Mozilla TTS unavailability or failure")
        tts = gTTS(
            text=script,
            lang=language,
            slow=slow,
            tld='com'  # Use .com domain for better quality
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
            tts.save(temp_path)

        audio = AudioSegment.from_mp3(temp_path)
        audio = optimize_audio(audio)
        duration = len(audio) / 1000.0

        if duration < 25:
            repeat_count = int(25 / duration) + 1
            audio = audio * repeat_count
            logger.warning(f"⚠️ Duration {duration:.1f}s too short, repeating {repeat_count} times")
            duration = len(audio) / 1000.0

        audio.export(audio_path, format="mp3", bitrate="128k")
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

def optimize_audio(audio):
    """
    Optimize audio for YouTube Shorts
    
    Args:
        audio (AudioSegment): Input audio
        
    Returns:
        AudioSegment: Optimized audio
    """
    audio = audio.normalize()
    audio = audio.speedup(playback_speed=1.05)
    audio = audio.compress_dynamic_range(threshold=-20.0, ratio=2.0)
    audio = audio.set_channels(1)
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
        import subprocess
        
        cmd = [
            'espeak',
            '-s', '150',
            '-p', '40',
            '-a', '100',
            '-w', audio_path,
            script
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"espeak failed: {result.stderr}")
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise Exception("espeak generated an empty or missing file")
        audio = AudioSegment.from_wav(audio_path)
        if len(audio) == 0:
            raise ValueError("espeak generated zero-duration audio")

        # Convert WAV to MP3 with explicit ffmpeg processing to ensure compatibility
        mp3_path = audio_path.replace('.wav', '.mp3')
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', audio_path,
            '-acodec', 'mp3',
            '-ab', '128k',
            '-ar', '22050',
            '-ac', '1',
            mp3_path,
            '-y'  # Overwrite output file if it exists
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        os.unlink(audio_path)  # Remove original WAV
        logger.info(f"✅ Fallback voice generated and converted: {mp3_path}")
        return mp3_path
            
    except Exception as e:
        logger.error(f"❌ System TTS failed: {e}")
        return create_placeholder_audio(script, output_dir)

def create_placeholder_audio(script, output_dir):
    """
    Create a placeholder audio file with silence
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"narration_placeholder_{timestamp}.mp3"
    audio_path = os.path.join(output_dir, audio_filename)
    
    word_count = len(script.split())
    duration_seconds = (word_count / 150) * 60
    duration_ms = int(duration_seconds * 1000)
    
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(audio_path, format="mp3")
    
    logger.warning(f"⚠️ Created placeholder audio: {audio_path}")
    logger.info(f"⏱️ Duration: {duration_seconds:.1f} seconds")
    
    return audio_path

def get_audio_duration(audio_path):
    """
    Get duration of audio file in seconds
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        logger.error(f"❌ Error getting audio duration: {e}")
        return 0.0

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
        logger.info(f"✅ Test successful!")
        logger.info(f"📁 File: {audio_path}")
        logger.info(f"⏱️ Duration: {duration:.1f} seconds")
    else:
        logger.error("❌ Test failed!")

if __name__ == "__main__":
    test_voice_generation()