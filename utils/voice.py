#!/usr/bin/env python3
"""
MoviePy Audio Fix - Addresses the _NoValueType error in audio and video clip processing
"""

import os
import logging
import moviepy
from moviepy.editor import *
from moviepy.audio.AudioClip import AudioClip
from moviepy.video.VideoClip import VideoClip
import numpy as np
from gtts import gTTS
from TTS.api import TTS
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Log MoviePy version for debugging
logger.info(f"MoviePy version: {moviepy.__version__}")

def generate_voice(script: str, output_dir: str = "output") -> str:
    """
    Generate voice narration from script text using Mozilla TTS with fallback to gTTS.
    
    Args:
        script (str): The text script to convert to audio
        output_dir (str): Directory to save the audio file
    
    Returns:
        str: Path to the generated audio file
    """
    try:
        logger.info("🎙️ Starting voice generation...")

        # Ensure output directory exists
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = str(output_dir / f"narration_{timestamp}.mp3")

        # Try Mozilla TTS first
        try:
            logger.info("🔄 Attempting to use Mozilla TTS...")
            tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
            tts.tts_to_file(text=script, file_path=audio_path)
            logger.info(f"✅ Mozilla TTS generated audio: {audio_path}")
            
            # Verify audio file
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                raise FileNotFoundError("Mozilla TTS generated empty or missing audio file")
            
            # Create safe audio clip and verify duration
            audio_clip = create_safe_audio_clip(audio_path)
            if audio_clip.duration <= 0:
                raise ValueError(f"Generated audio has invalid duration: {audio_clip.duration}")
            
            audio_clip.close()
            return audio_path

        except Exception as tts_error:
            logger.warning(f"⚠️ Mozilla TTS failed: {str(tts_error)}")
            logger.info("🔄 Falling back to gTTS...")

            # Fallback to gTTS
            try:
                gtts = gTTS(text=script, lang='en', slow=False)
                gtts.save(audio_path)
                logger.info(f"✅ gTTS generated audio: {audio_path}")

                # Verify audio file
                if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                    raise FileNotFoundError("gTTS generated empty or missing audio file")

                # Create safe audio clip and verify duration
                audio_clip = create_safe_audio_clip(audio_path)
                if audio_clip.duration <= 0:
                    raise ValueError(f"Generated audio has invalid duration: {audio_clip.duration}")

                audio_clip.close()
                return audio_path

            except Exception as gtts_error:
                logger.error(f"❌ gTTS failed: {str(gtts_error)}")
                raise RuntimeError("Failed to generate audio with both Mozilla TTS and gTTS")

    except Exception as e:
        logger.error(f"❌ Voice generation failed: {str(e)}", exc_info=True)
        raise

def fix_audio_clip_duration(audio_clip, fallback_duration=30.0):
    """
    Fix audio clip duration issues that cause _NoValueType errors
    
    Args:
        audio_clip: MoviePy AudioClip
        fallback_duration: Default duration if clip duration is invalid
        
    Returns:
        AudioClip with properly set duration
    """
    try:
        # Check if clip has valid duration
        if hasattr(audio_clip, 'duration') and audio_clip.duration is not None:
            try:
                duration = float(audio_clip.duration)
                if duration > 0:
                    logger.info(f"✅ Audio clip has valid duration: {duration:.2f}s")
                    return audio_clip.set_duration(duration)
            except (TypeError, ValueError):
                logger.warning("⚠️ Invalid duration detected, attempting to fix...")
        
        # If no valid duration, try to get it from the audio file
        logger.warning("⚠️ Audio clip missing or invalid duration, attempting to calculate...")
        
        # Try to get duration from audio file if it's a file-based clip
        if hasattr(audio_clip, 'filename') and audio_clip.filename:
            from pydub import AudioSegment
            try:
                audio_seg = AudioSegment.from_file(audio_clip.filename)
                duration = len(audio_seg) / 1000.0
                logger.info(f"📊 Calculated duration from file: {duration:.2f}s")
            except Exception as e:
                logger.warning(f"⚠️ Failed to calculate duration from file: {e}")
                duration = fallback_duration
        else:
            # Use fallback duration
            duration = fallback_duration
            logger.warning(f"🔄 Using fallback duration: {duration:.2f}s")
        
        # Set the duration explicitly
        audio_clip = audio_clip.set_duration(duration)
        logger.info(f"✅ Fixed audio clip duration: {duration:.2f}s")
        
        return audio_clip
        
    except Exception as e:
        logger.error(f"❌ Error fixing audio clip duration: {e}")
        # Create a silent clip as fallback
        return AudioClip(make_frame=lambda t: np.array([0.0]), duration=fallback_duration)

def create_safe_audio_clip(audio_path, target_duration=None):
    """
    Create a safe AudioClip that won't cause _NoValueType errors
    
    Args:
        audio_path: Path to audio file
        target_duration: Desired duration (optional)
        
    Returns:
        AudioClip with guaranteed valid duration
    """
    try:
        # Load audio file
        logger.info(f"🔊 Loading audio file: {audio_path}")
        audio_clip = AudioFileClip(audio_path)
        
        # Fix duration issues
        audio_clip = fix_audio_clip_duration(audio_clip)
        
        # Validate duration
        if audio_clip.duration is None or audio_clip.duration <= 0:
            raise ValueError(f"Invalid audio duration: {audio_clip.duration}")
        
        # Adjust duration if needed
        if target_duration and abs(float(target_duration) - float(audio_clip.duration)) > 0.01:
            logger.info(f"🔄 Adjusting audio duration from {audio_clip.duration:.2f}s to {target_duration:.2f}s")
            if target_duration > audio_clip.duration:
                # Loop audio to reach target duration
                loops_needed = int(np.ceil(target_duration / audio_clip.duration))
                audio_clip = concatenate_audioclips([audio_clip] * loops_needed)
                audio_clip = audio_clip.subclip(0, target_duration)
            else:
                # Trim audio to target duration
                audio_clip = audio_clip.subclip(0, target_duration)
        
        # Ensure duration is properly set
        audio_clip = audio_clip.set_duration(float(audio_clip.duration))
        
        # Debug clip properties
        debug_audio_clip(audio_clip, f"AudioClip from {audio_path}")
        
        logger.info(f"✅ Created safe audio clip: {audio_clip.duration:.2f}s")
        return audio_clip
        
    except Exception as e:
        logger.error(f"❌ Error creating safe audio clip from {audio_path}: {e}")
        # Create silent fallback
        duration = target_duration if target_duration else 30.0
        logger.warning(f"🔄 Creating silent fallback clip with duration: {duration:.2f}s")
        return AudioClip(make_frame=lambda t: np.array([0.0]), duration=duration)

def fix_composite_audio_clips(clips):
    """
    Fix all audio clips in a composite to prevent _NoValueType errors
    
    Args:
        clips: List of audio clips
        
    Returns:
        List of fixed audio clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            # Fix duration
            fixed_clip = fix_audio_clip_duration(clip)
            
            # Check for _NoValueType or invalid attributes
            if hasattr(fixed_clip, 'start') and isinstance(fixed_clip.start, moviepy.NoValue):
                logger.warning(f"⚠️ Clip {i+1} has _NoValueType start, setting to 0")
                fixed_clip.start = 0
            elif not hasattr(fixed_clip, 'start') or fixed_clip.start is None:
                logger.info(f"🔄 Setting start time for clip {i+1} to 0")
                fixed_clip = fixed_clip.set_start(0)
            
            # Ensure duration is valid
            if hasattr(fixed_clip, 'duration') and fixed_clip.duration is not None:
                try:
                    duration = float(fixed_clip.duration)
                    if isinstance(duration, moviepy.NoValue) or duration <= 0:
                        logger.warning(f"⚠️ Invalid duration for clip {i+1}, using fallback duration 30.0")
                        fixed_clip = fixed_clip.set_duration(30.0)
                except (TypeError, ValueError):
                    logger.warning(f"⚠️ Invalid duration for clip {i+1}, using fallback duration 30.0")
                    fixed_clip = fixed_clip.set_duration(30.0)
            
            # Ensure end time is set
            try:
                fixed_clip = fixed_clip.set_end(fixed_clip.start + float(fixed_clip.duration))
            except (TypeError, ValueError):
                logger.warning(f"⚠️ Invalid end time for clip {i+1}, setting based on duration")
                fixed_clip = fixed_clip.set_end(fixed_clip.start + 30.0)
            
            # Recursively fix nested composite clips
            if isinstance(fixed_clip, CompositeAudioClip) and hasattr(fixed_clip, 'clips'):
                logger.debug(f"🔄 Fixing {len(fixed_clip.clips)} sub-clips for clip {i+1}")
                fixed_clip.clips = fix_composite_audio_clips(fixed_clip.clips)
            
            # Debug clip properties
            debug_audio_clip(fixed_clip, f"Composite Clip {i+1}")
            
            fixed_clips.append(fixed_clip)
            logger.info(f"✅ Fixed audio clip {i+1}/{len(clips)}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing audio clip {i+1}: {e}")
            # Create silent fallback
            silent_clip = AudioClip(make_frame=lambda t: np.array([0.0]), duration=30.0)
            fixed_clips.append(silent_clip)
    
    return fixed_clips

def validate_clip_properties(clip, clip_name="Unknown"):
    """
    Recursively validate and fix clip properties to eliminate _NoValueType issues with minimal recreation.
    
    Args:
        clip: MoviePy clip (VideoClip, TextClip, CompositeVideoClip, etc.)
        clip_name: Name for logging
        
    Returns:
        Clip with validated properties
    """
    try:
        logger.debug(f"🔍 Validating clip: {clip_name} (type: {type(clip).__name__})")
        
        # Check for None clip
        if clip is None:
            logger.warning(f"⚠️ Clip {clip_name} is None, creating fallback black clip")
            return ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=0.5)
        
        # Fix duration
        duration = getattr(clip, 'duration', None)
        if duration is None or isinstance(duration, moviepy.NoValue) or (isinstance(duration, (int, float)) and duration <= 0.5):
            logger.warning(f"⚠️ Invalid or short duration for {clip_name}, setting to 0.5")
            clip = clip.set_duration(0.5)
        else:
            try:
                duration = float(duration)
                clip = clip.set_duration(max(duration, 0.5))
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Cannot convert duration for {clip_name}: {e}, setting to 0.5")
                clip = clip.set_duration(0.5)
        
        # Fix start time
        start = getattr(clip, 'start', None)
        if start is None or isinstance(start, moviepy.NoValue):
            logger.debug(f"🔄 Setting start time for {clip_name} to 0")
            clip = clip.set_start(0)
        
        # Fix end time
        try:
            clip = clip.set_end(float(clip.start) + float(clip.duration))
        except (TypeError, ValueError) as e:
            logger.warning(f"⚠️ Invalid end time for {clip_name}: {e}, setting based on duration")
            clip = clip.set_end(float(clip.start) + float(clip.duration))
        
        # Fix size
        if isinstance(clip, (ImageClip, CompositeVideoClip, TextClip)) and (not hasattr(clip, 'size') or clip.size is None):
            logger.debug(f"🔄 Setting size for {clip_name} to (1080, 1920)")
            clip = clip.resize((1080, 1920))
        
        # Fix position for TextClip
        if isinstance(clip, TextClip):
            pos = getattr(clip, 'pos', None)
            if pos is None or isinstance(pos, moviepy.NoValue):
                logger.debug(f"🔄 Setting position for {clip_name} to ('center', 'bottom')")
                clip = clip.set_position(('center', 'bottom'))
        
        # Fix FPS
        fps = getattr(clip, 'fps', None)
        if fps is None or isinstance(fps, moviepy.NoValue) or (isinstance(fps, (int, float)) and fps <= 0):
            logger.debug(f"🔄 Setting FPS for {clip_name} to 30")
            clip = clip.set_fps(30)
        
        # Validate TextClip-specific properties
        if isinstance(clip, TextClip):
            text = getattr(clip, 'text', None)
            font = getattr(clip, 'font', None)
            fontsize = getattr(clip, 'fontsize', None)
            color = getattr(clip, 'color', None)
            
            if text is None or isinstance(text, moviepy.NoValue) or font is None or isinstance(font, moviepy.NoValue) or fontsize is None or isinstance(fontsize, moviepy.NoValue) or color is None or isinstance(color, moviepy.NoValue):
                logger.warning(f"⚠️ Invalid critical attributes for {clip_name} (text={text}, font={font}, fontsize={fontsize}, color={color}), recreating TextClip")
                try:
                    clip = TextClip(
                        text if text and not isinstance(text, moviepy.NoValue) else "Fallback",
                        font='FreeSerif',
                        fontsize=60 if fontsize is None or isinstance(fontsize, moviepy.NoValue) else fontsize,
                        color='white' if color is None or isinstance(color, moviepy.NoValue) else color,
                        stroke_color='black',
                        stroke_width=1,
                        size=(1080, 1920),
                        method='caption',
                        align='center'
                    )
                    clip = clip.set_duration(max(float(clip.duration), 0.5)).set_position(('center', 'bottom')).set_fps(30)
                    logger.info(f"✅ Recreated TextClip for {clip_name} with FreeSerif")
                except Exception as e:
                    logger.error(f"❌ Failed to recreate TextClip for {clip_name}: {e}")
                    clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=0.5)
            else:
                logger.debug(f"✅ TextClip {clip_name} has valid attributes: text={text}, font={font}, fontsize={fontsize}, color={color}")
        
        # Recursively validate sub-clips for CompositeVideoClip
        if isinstance(clip, CompositeVideoClip) and hasattr(clip, 'clips'):
            logger.debug(f"🔄 Validating {len(clip.clips)} sub-clips for {clip_name}")
            clip.clips = [validate_clip_properties(subclip, f"Sub-clip {i+1} of {clip_name}") for i, subclip in enumerate(clip.clips)]
        
        # Log validated properties
        logger.debug(f"✅ Validated {clip_name}: duration={getattr(clip, 'duration', 'NOT SET')}, "
                    f"start={getattr(clip, 'start', 'NOT SET')}, "
                    f"end={getattr(clip, 'end', 'NOT SET')}, "
                    f"size={getattr(clip, 'size', 'NOT SET')}, "
                    f"fps={getattr(clip, 'fps', 'NOT SET')}, "
                    f"pos={getattr(clip, 'pos', 'NOT SET')}")
        
        return clip
    except Exception as e:
        logger.error(f"❌ Error validating clip {clip_name}: {e}", exc_info=True)
        return ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=0.5)

def fix_composite_video_clips(clips, fallback_duration=0.5):
    """
    Fix all video clips (including TextClip) in a composite to prevent _NoValueType errors
    
    Args:
        clips: List of video clips (VideoClip, TextClip, etc.)
        fallback_duration: Default duration if clip duration is invalid
        
    Returns:
        List of fixed video clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            # Validate and fix clip properties
            fixed_clip = validate_clip_properties(clip, f"Clip {i+1}")
            
            # Ensure duration is valid
            if hasattr(fixed_clip, 'duration') and fixed_clip.duration is not None:
                try:
                    duration = float(fixed_clip.duration)
                    if duration <= 0.5:
                        logger.warning(f"⚠️ Video clip {i+1} has short duration, using minimum 0.5s")
                        fixed_clip = fixed_clip.set_duration(0.5)
                except (TypeError, ValueError) as e:
                    logger.warning(f"⚠️ Invalid duration for clip {i+1}: {e}, using fallback duration")
                    fixed_clip = fixed_clip.set_duration(fallback_duration)
            else:
                logger.warning(f"⚠️ Video clip {i+1} missing duration, using fallback duration")
                fixed_clip = fixed_clip.set_duration(fallback_duration)
            
            # Ensure start time is set
            if not hasattr(fixed_clip, 'start') or fixed_clip.start is None or isinstance(fixed_clip.start, moviepy.NoValue):
                logger.debug(f"🔄 Setting start time for clip {i+1} to 0")
                fixed_clip = fixed_clip.set_start(0)
            
            # Ensure end time is set
            try:
                fixed_clip = fixed_clip.set_end(float(fixed_clip.start) + float(fixed_clip.duration))
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Invalid end time for clip {i+1}: {e}, setting based on fallback duration")
                fixed_clip = fixed_clip.set_end(float(fixed_clip.start) + fallback_duration)
            
            # Ensure size is set
            if isinstance(fixed_clip, (ImageClip, CompositeVideoClip, TextClip)) and (not hasattr(fixed_clip, 'size') or fixed_clip.size is None):
                logger.debug(f"🔄 Setting size for clip {i+1} to (1080, 1920)")
                fixed_clip = fixed_clip.resize((1080, 1920))
            
            # Debug clip properties
            logger.debug(f"🔍 Video clip {i+1} properties: duration={getattr(fixed_clip, 'duration', 'NOT SET')}, "
                        f"start={getattr(fixed_clip, 'start', 'NOT SET')}, "
                        f"end={getattr(fixed_clip, 'end', 'NOT SET')}, "
                        f"size={getattr(fixed_clip, 'size', 'NOT SET')}, "
                        f"fps={getattr(fixed_clip, 'fps', 'NOT SET')}, "
                        f"pos={getattr(fixed_clip, 'pos', 'NOT SET')}")
            
            fixed_clips.append(fixed_clip)
            logger.info(f"✅ Fixed video clip {i+1}/{len(clips)}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing video clip {i+1}: {e}", exc_info=True)
            # Create black video clip as fallback
            black_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=fallback_duration)
            fixed_clips.append(black_clip)
    
    return fixed_clips

def safe_write_videofile(video_clip, output_path, **kwargs):
    """
    Safely write video file with proper audio and video clip handling
    
    Args:
        video_clip: MoviePy VideoClip
        output_path: Output file path
        **kwargs: Additional arguments for write_videofile
        
    Returns:
        bool: Success status
    """
    try:
        # Validate video clip
        if video_clip is None:
            logger.error("❌ Video clip is None")
            return False
        
        # Fix and validate main video clip properties
        logger.info("🔄 Fixing and validating main video clip properties...")
        video_clip = validate_clip_properties(video_clip, "Main Video Clip")
        
        # Ensure duration is valid
        if not hasattr(video_clip, 'duration') or video_clip.duration is None or isinstance(video_clip.duration, moviepy.NoValue):
            logger.error("❌ Invalid video clip duration")
            return False
        
        # Ensure size is valid
        if not hasattr(video_clip, 'size') or video_clip.size is None:
            logger.debug("🔄 Setting video clip size to (1080, 1920)")
            video_clip = video_clip.resize((1080, 1920))
        
        # Fix composite video clips (including subtitles)
        if isinstance(video_clip, CompositeVideoClip):
            logger.info("🔄 Detected CompositeVideoClip, fixing all sub-clips...")
            video_clip.clips = fix_composite_video_clips(video_clip.clips)
        
        # Check if video has audio
        if video_clip.audio is not None:
            logger.info("🔊 Video has audio, fixing audio issues...")
            
            # Handle composite audio clips
            if isinstance(video_clip.audio, CompositeAudioClip):
                logger.info("🔄 Detected CompositeAudioClip, fixing all sub-clips...")
                video_clip.audio.clips = fix_composite_audio_clips(video_clip.audio.clips)
            
            # Fix audio duration
            fixed_audio = fix_audio_clip_duration(video_clip.audio)
            
            # Ensure audio matches video duration
            if abs(float(fixed_audio.duration) - float(video_clip.duration)) > 0.01:
                logger.warning(f"⚠️ Audio duration ({fixed_audio.duration:.2f}s) != Video duration ({video_clip.duration:.2f}s)")
                
                if fixed_audio.duration > video_clip.duration:
                    # Trim audio
                    fixed_audio = fixed_audio.subclip(0, video_clip.duration)
                    logger.info(f"✂️ Trimmed audio to match video duration")
                else:
                    # Loop audio
                    loops_needed = int(np.ceil(video_clip.duration / fixed_audio.duration))
                    fixed_audio = concatenate_audioclips([fixed_audio] * loops_needed)
                    fixed_audio = fixed_audio.subclip(0, video_clip.duration)
                    logger.info(f"🔄 Looped audio to match video duration")
            
            # Set fixed audio back to video
            video_clip = video_clip.set_audio(fixed_audio)
        
        # Log final clip properties
        logger.debug(f"🔍 Final video clip properties: duration={getattr(video_clip, 'duration', 'NOT SET')}, "
                    f"start={getattr(video_clip, 'start', 'NOT SET')}, "
                    f"size={getattr(video_clip, 'size', 'NOT SET')}, "
                    f"fps={getattr(video_clip, 'fps', 'NOT SET')}, "
                    f"pos={getattr(video_clip, 'pos', 'NOT SET')}")
        
        # Set default parameters for stable output
        default_params = {
            'fps': 30,
            'codec': 'libx264',
            'audio_codec': 'aac',
            'temp_audiofile': 'temp-audio.m4a',
            'remove_temp': True,
            'verbose': False,
            'logger': None
        }
        
        # Update with user parameters
        default_params.update(kwargs)
        
        # Write video file
        logger.info(f"💾 Writing video to: {output_path}")
        video_clip.write_videofile(output_path, **default_params)
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✅ Video successfully written: {output_path}")
            return True
        else:
            logger.error(f"❌ Video file not created or empty: {output_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error writing video file: {str(e)}", exc_info=True)
        return False
    
    finally:
        # Clean up clips
        try:
            if hasattr(video_clip, 'close'):
                video_clip.close()
        except:
            pass

def debug_audio_clip(audio_clip, clip_name="Unknown"):
    """
    Debug audio clip properties to identify issues
    
    Args:
        audio_clip: AudioClip to debug
        clip_name: Name for logging
    """
    logger.debug(f"🔍 Debugging audio clip: {clip_name}")
    
    try:
        # Check basic properties
        logger.debug(f"   - Duration: {getattr(audio_clip, 'duration', 'NOT SET')}")
        logger.debug(f"   - Start: {getattr(audio_clip, 'start', 'NOT SET')}")
        logger.debug(f"   - End: {getattr(audio_clip, 'end', 'NOT SET')}")
        logger.debug(f"   - FPS: {getattr(audio_clip, 'fps', 'NOT SET')}")
        
        # Check if it's a composite clip
        if hasattr(audio_clip, 'clips'):
            logger.debug(f"   - Composite with {len(audio_clip.clips)} clips")
            for i, subclip in enumerate(audio_clip.clips):
                logger.debug(f"     Clip {i+1}: duration={getattr(subclip, 'duration', 'NOT SET')}, "
                            f"start={getattr(subclip, 'start', 'NOT SET')}")
        
        # Try to get a frame
        try:
            frame = audio_clip.get_frame(0)
            logger.debug(f"   - Frame at t=0: shape={np.shape(frame)}")
        except Exception as e:
            logger.error(f"   - Cannot get frame: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error debugging audio clip: {e}", exc_info=True)

def create_video_with_fixed_audio(video_path, audio_path, output_path):
    """
    Create video with properly handled audio to avoid _NoValueType errors
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file  
        output_path: Output video path
        
    Returns:
        bool: Success status
    """
    try:
        # Load video
        video_clip = VideoFileClip(video_path)
        logger.info(f"📹 Loaded video: {video_clip.duration:.2f}s")
        
        # Create safe audio clip
        audio_clip = create_safe_audio_clip(audio_path, target_duration=video_clip.duration)
        
        # Debug audio before composition
        debug_audio_clip(audio_clip, "Generated Audio")
        
        # Set audio to video
        final_video = video_clip.set_audio(audio_clip)
        
        # Write with safe method
        success = safe_write_videofile(final_video, output_path)
        
        # Clean up
        video_clip.close()
        audio_clip.close()
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error creating video with audio: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Test the fix
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Example usage
    print("🧪 Testing audio fix utilities...")
    
    # Create a test silent clip
    test_clip = AudioClip(make_frame=lambda t: np.array([0.0]), duration=30.0)
    debug_audio_clip(test_clip, "Test Silent Clip")
    
    print("✅ Audio fix utilities ready!")