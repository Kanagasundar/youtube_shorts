#!/usr/bin/env python3
"""
MoviePy Audio Fix - Addresses errors in audio and video clip processing
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
import time
from pydub import AudioSegment

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
            
            # Validate audio file with pydub
            try:
                audio_seg = AudioSegment.from_file(audio_path)
                duration = len(audio_seg) / 1000.0
                if duration <= 0:
                    raise ValueError("Mozilla TTS generated audio with invalid duration")
                logger.info(f"✅ Audio file validated with pydub: duration={duration:.2f}s")
            except Exception as validation_error:
                logger.warning(f"⚠️ Mozilla TTS audio validation failed: {str(validation_error)}")
                os.remove(audio_path) if os.path.exists(audio_path) else None
                raise FileNotFoundError("Mozilla TTS generated invalid audio file")

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

                # Validate audio file with pydub
                try:
                    audio_seg = AudioSegment.from_file(audio_path)
                    duration = len(audio_seg) / 1000.0
                    if duration <= 0:
                        raise ValueError("gTTS generated audio with invalid duration")
                    logger.info(f"✅ Audio file validated with pydub: duration={duration:.2f}s")
                except Exception as validation_error:
                    logger.warning(f"⚠️ gTTS audio validation failed: {str(validation_error)}")
                    os.remove(audio_path) if os.path.exists(audio_path) else None
                    raise FileNotFoundError("gTTS generated invalid audio file")

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
    Fix audio clip duration issues.
    
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
        
        if hasattr(audio_clip, 'filename') and audio_clip.filename:
            try:
                audio_seg = AudioSegment.from_file(audio_clip.filename)
                duration = len(audio_seg) / 1000.0
                logger.info(f"📊 Calculated duration from file: {duration:.2f}s")
            except Exception as e:
                logger.warning(f"⚠️ Failed to calculate duration from file: {e}")
                duration = fallback_duration
        else:
            duration = fallback_duration
            logger.warning(f"🔄 Using fallback duration: {duration:.2f}s")
        
        audio_clip = audio_clip.set_duration(duration)
        logger.info(f"✅ Fixed audio clip duration: {duration:.2f}s")
        
        return audio_clip
        
    except Exception as e:
        logger.error(f"❌ Error fixing audio clip duration: {e}")
        return AudioClip(make_frame=lambda t: np.array([0.0]), duration=fallback_duration)

def create_safe_audio_clip(audio_path, target_duration=None):
    """
    Create a safe AudioClip that won't cause errors.
    
    Args:
        audio_path: Path to audio file
        target_duration: Desired duration (optional)
        
    Returns:
        AudioClip with guaranteed valid duration
    """
    try:
        logger.info(f"🔊 Loading audio file: {audio_path}")
        audio_clip = AudioFileClip(audio_path)
        
        audio_clip = fix_audio_clip_duration(audio_clip)
        
        if audio_clip.duration is None or audio_clip.duration <= 0:
            raise ValueError(f"Invalid audio duration: {audio_clip.duration}")
        
        if target_duration and abs(float(target_duration) - float(audio_clip.duration)) > 0.01:
            logger.info(f"🔄 Adjusting audio duration from {audio_clip.duration:.2f}s to {target_duration:.2f}s")
            if target_duration > audio_clip.duration:
                loops_needed = int(np.ceil(target_duration / audio_clip.duration))
                audio_clip = concatenate_audioclips([audio_clip] * loops_needed)
                audio_clip = audio_clip.subclip(0, target_duration)
            else:
                audio_clip = audio_clip.subclip(0, target_duration)
        
        audio_clip = audio_clip.set_duration(float(audio_clip.duration))
        
        debug_audio_clip(audio_clip, f"AudioClip from {audio_path}")
        
        logger.info(f"✅ Created safe audio clip: {audio_clip.duration:.2f}s")
        return audio_clip
        
    except Exception as e:
        logger.error(f"❌ Error creating safe audio clip from {audio_path}: {e}")
        duration = target_duration if target_duration else 30.0
        logger.warning(f"🔄 Creating silent fallback clip with duration: {duration:.2f}s")
        return AudioClip(make_frame=lambda t: np.array([0.0]), duration=duration)

def fix_composite_audio_clips(clips):
    """
    Fix all audio clips in a composite to prevent errors, including handling _NoValueType.
    
    Args:
        clips: List of audio clips
        
    Returns:
        List of fixed audio clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            fixed_clip = fix_audio_clip_duration(clip)
            
            if not hasattr(fixed_clip, 'start') or fixed_clip.start is None or str(fixed_clip.start).startswith('_NoValueType'):
                logger.info(f"🔄 Setting start time for clip {i+1} to 0")
                fixed_clip = fixed_clip.set_start(0)
            
            if hasattr(fixed_clip, 'duration') and fixed_clip.duration is not None:
                try:
                    duration = float(fixed_clip.duration)
                    if duration <= 0:
                        logger.warning(f"⚠️ Invalid duration for clip {i+1}, using fallback duration 30.0")
                        fixed_clip = fixed_clip.set_duration(30.0)
                except (TypeError, ValueError):
                    logger.warning(f"⚠️ Invalid duration for clip {i+1}, using fallback duration 30.0")
                    fixed_clip = fixed_clip.set_duration(30.0)
            else:
                logger.warning(f"⚠️ Missing duration for clip {i+1}, using fallback duration 30.0")
                fixed_clip = fixed_clip.set_duration(30.0)
            
            try:
                end_time = float(fixed_clip.start) + float(fixed_clip.duration)
                fixed_clip = fixed_clip.set_end(end_time)
            except (TypeError, ValueError):
                logger.warning(f"⚠️ Invalid end time for clip {i+1}, setting based on duration")
                fixed_clip = fixed_clip.set_end(float(fixed_clip.start) + 30.0)
            
            if isinstance(fixed_clip, CompositeAudioClip) and hasattr(fixed_clip, 'clips'):
                logger.debug(f"🔄 Fixing {len(fixed_clip.clips)} sub-clips for clip {i+1}")
                fixed_clip.clips = fix_composite_audio_clips(fixed_clip.clips)
            
            debug_audio_clip(fixed_clip, f"Composite Clip {i+1}")
            
            fixed_clips.append(fixed_clip)
            logger.info(f"✅ Fixed audio clip {i+1}/{len(clips)}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing audio clip {i+1}: {e}")
            silent_clip = AudioClip(make_frame=lambda t: np.array([0.0]), duration=30.0)
            fixed_clips.append(silent_clip)
    
    return fixed_clips

def validate_clip_properties(clip, clip_name="Unknown"):
    """
    Recursively validate and fix clip properties to eliminate errors, including handling _NoValueType.
    
    Args:
        clip: MoviePy clip (VideoClip, TextClip, CompositeVideoClip, etc.)
        clip_name: Name for logging
        
    Returns:
        Clip with validated properties
    """
    try:
        logger.debug(f"🔍 Validating clip: {clip_name} (type: {type(clip).__name__})")
        
        if clip is None:
            logger.warning(f"⚠️ Clip {clip_name} is None, creating fallback black clip")
            return ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=0.5)
        
        # Fix duration
        duration = getattr(clip, 'duration', None)
        if duration is None or str(duration).startswith('_NoValueType') or (isinstance(duration, (int, float)) and duration <= 0.5):
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
        if start is None or str(start).startswith('_NoValueType'):
            logger.debug(f"🔄 Setting start time for {clip_name} to 0")
            clip = clip.set_start(0)
        
        # Fix end time
        try:
            clip = clip.set_end(float(clip.start) + float(clip.duration))
        except (TypeError, ValueError) as e:
            logger.warning(f"⚠️ Invalid end time for {clip_name}: {e}, setting based on duration")
            clip = clip.set_end(float(clip.start) + float(clip.duration))
        
        # Fix size
        if isinstance(clip, (ImageClip, CompositeVideoClip, TextClip)) and (not hasattr(clip, 'size') or clip.size is None or str(clip.size).startswith('_NoValueType')):
            logger.debug(f"🔄 Setting size for {clip_name} to (1080, 1920)")
            clip = clip.resize((1080, 1920))
        
        # Fix position (including lambda functions)
        pos = getattr(clip, 'pos', None)
        if pos is None or str(pos).startswith('_NoValueType'):
            logger.debug(f"🔄 Setting position for {clip_name} to ('center', 'center')")
            clip = clip.set_position(('center', 'center'))
        elif callable(pos):
            try:
                test_pos = pos(0)  # Test the position function
                if str(test_pos).startswith('_NoValueType'):
                    logger.warning(f"⚠️ Position function for {clip_name} returns _NoValueType, resetting to ('center', 'center')")
                    clip = clip.set_position(('center', 'center'))
            except Exception as e:
                logger.warning(f"⚠️ Invalid position function for {clip_name}: {e}, resetting to ('center', 'center')")
                clip = clip.set_position(('center', 'center'))
        
        # Fix FPS
        fps = getattr(clip, 'fps', None)
        if fps is None or str(fps).startswith('_NoValueType') or (isinstance(fps, (int, float)) and fps <= 0):
            logger.debug(f"🔄 Setting FPS for {clip_name} to 30")
            clip = clip.set_fps(30)
        
        # Fix mask for TextClip
        if isinstance(clip, TextClip) and hasattr(clip, 'mask') and (clip.mask is None or str(clip.mask).startswith('_NoValueType')):
            logger.warning(f"⚠️ Invalid mask for {clip_name}, removing mask")
            clip.mask = None
        
        # Validate TextClip-specific properties
        if isinstance(clip, TextClip):
            text = getattr(clip, 'text', 'Fallback')
            font = getattr(clip, 'font', 'FreeSerif')
            fontsize = getattr(clip, 'fontsize', 40)
            color = getattr(clip, 'color', 'white')
            stroke_width = getattr(clip, 'stroke_width', 1)
            
            invalid_attrs = []
            if text is None or str(text).startswith('_NoValueType'):
                invalid_attrs.append(f"text={text}")
                text = "Fallback"
            if font is None or str(font).startswith('_NoValueType'):
                invalid_attrs.append(f"font={font}")
                font = 'FreeSerif'
            if fontsize is None or str(fontsize).startswith('_NoValueType') or (isinstance(fontsize, (int, float)) and fontsize <= 0):
                invalid_attrs.append(f"fontsize={fontsize}")
                fontsize = 40
            if color is None or str(color).startswith('_NoValueType'):
                invalid_attrs.append(f"color={color}")
                color = 'white'
            if stroke_width is None or str(stroke_width).startswith('_NoValueType') or (isinstance(stroke_width, (int, float)) and stroke_width < 0):
                invalid_attrs.append(f"stroke_width={stroke_width}")
                stroke_width = 1
            
            if invalid_attrs:
                logger.warning(f"⚠️ Invalid attributes for {clip_name}: {', '.join(invalid_attrs)}, recreating TextClip")
                try:
                    clip = TextClip(
                        text,
                        font=font,
                        fontsize=int(fontsize),
                        color=color,
                        stroke_color='black',
                        stroke_width=float(stroke_width),
                        size=(1080, 1920),
                        method='caption',
                        align='center'
                    )
                    clip = clip.set_duration(max(float(clip.duration), 0.5)).set_position(('center', 'bottom')).set_fps(30)
                    logger.info(f"✅ Recreated TextClip for {clip_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to recreate TextClip for {clip_name}: {e}")
                    clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=0.5)
            else:
                logger.debug(f"✅ TextClip {clip_name} has valid attributes: text={text}, font={font}, fontsize={fontsize}, color={color}, stroke_width={stroke_width}")
        
        # Recursively validate sub-clips
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
    Fix all video clips (including TextClip) in a composite to prevent errors.
    
    Args:
        clips: List of video clips (VideoClip, TextClip, etc.)
        fallback_duration: Default duration if clip duration is invalid
        
    Returns:
        List of fixed video clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            fixed_clip = validate_clip_properties(clip, f"Clip {i+1}")
            
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
            
            if not hasattr(fixed_clip, 'start') or fixed_clip.start is None or str(fixed_clip.start).startswith('_NoValueType'):
                logger.debug(f"🔄 Setting start time for clip {i+1} to 0")
                fixed_clip = fixed_clip.set_start(0)
            
            try:
                fixed_clip = fixed_clip.set_end(float(fixed_clip.start) + float(fixed_clip.duration))
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ Invalid end time for clip {i+1}: {e}, setting based on fallback duration")
                fixed_clip = fixed_clip.set_end(float(fixed_clip.start) + fallback_duration)
            
            if isinstance(fixed_clip, (ImageClip, CompositeVideoClip, TextClip)) and (not hasattr(fixed_clip, 'size') or fixed_clip.size is None or str(fixed_clip.size).startswith('_NoValueType')):
                logger.debug(f"🔄 Setting size for clip {i+1} to (1080, 1920)")
                fixed_clip = fixed_clip.resize((1080, 1920))
            
            if isinstance(fixed_clip, (ImageClip, TextClip)) and (not hasattr(fixed_clip, 'pos') or fixed_clip.pos is None or str(fixed_clip.pos).startswith('_NoValueType')):
                logger.debug(f"🔄 Setting position for clip {i+1} to ('center', 'center')")
                fixed_clip = fixed_clip.set_position(('center', 'center'))
            elif isinstance(fixed_clip, (ImageClip, TextClip)) and callable(fixed_clip.pos):
                try:
                    test_pos = fixed_clip.pos(0)
                    if str(test_pos).startswith('_NoValueType'):
                        logger.warning(f"⚠️ Position function for clip {i+1} returns _NoValueType, resetting")
                        fixed_clip = fixed_clip.set_position(('center', 'center'))
                except Exception as e:
                    logger.warning(f"⚠️ Invalid position function for clip {i+1}: {e}, resetting")
                    fixed_clip = fixed_clip.set_position(('center', 'center'))
            
            # Fix mask for TextClip
            if isinstance(fixed_clip, TextClip) and hasattr(fixed_clip, 'mask') and (fixed_clip.mask is None or str(fixed_clip.mask).startswith('_NoValueType')):
                logger.warning(f"⚠️ Invalid mask for clip {i+1}, removing mask")
                fixed_clip.mask = None
            
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
            black_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=fallback_duration)
            fixed_clips.append(black_clip)
    
    return fixed_clips

def safe_write_videofile(video_clip, output_path, **kwargs):
    """
    Safely write video file with proper audio and video clip handling.
    
    Args:
        video_clip: MoviePy VideoClip
        output_path: Output file path
        **kwargs: Additional arguments for write_videofile
        
    Returns:
        bool: Success status
    """
    try:
        if video_clip is None:
            logger.error("❌ Video clip is None")
            return False
        
        logger.info("🔄 Fixing and validating main video clip properties...")
        video_clip = validate_clip_properties(video_clip, "Main Video Clip")
        
        if not hasattr(video_clip, 'duration') or video_clip.duration is None or str(video_clip.duration).startswith('_NoValueType'):
            logger.error("❌ Invalid video clip duration")
            return False
        
        if not hasattr(video_clip, 'size') or video_clip.size is None or str(video_clip.size).startswith('_NoValueType'):
            logger.debug("🔄 Setting video clip size to (1080, 1920)")
            video_clip = video_clip.resize((1080, 1920))
        
        if isinstance(video_clip, CompositeVideoClip) and hasattr(video_clip, 'clips'):
            logger.info("🔄 Detected CompositeVideoClip, fixing all sub-clips...")
            video_clip.clips = fix_composite_video_clips(video_clip.clips)
        
        # Debug all clip properties before writing
        logger.debug("🔍 Debugging final clip properties before writing...")
        logger.debug(f"Main clip: duration={getattr(video_clip, 'duration', 'NOT SET')}, "
                    f"start={getattr(video_clip, 'start', 'NOT SET')}, "
                    f"size={getattr(video_clip, 'size', 'NOT SET')}, "
                    f"fps={getattr(video_clip, 'fps', 'NOT SET')}, "
                    f"pos={getattr(video_clip, 'pos', 'NOT SET')}")
        if isinstance(video_clip, CompositeVideoClip):
            for i, subclip in enumerate(video_clip.clips):
                logger.debug(f"Sub-clip {i+1}: type={type(subclip).__name__}, "
                            f"duration={getattr(subclip, 'duration', 'NOT SET')}, "
                            f"start={getattr(subclip, 'start', 'NOT SET')}, "
                            f"size={getattr(subclip, 'size', 'NOT SET')}, "
                            f"fps={getattr(subclip, 'fps', 'NOT SET')}, "
                            f"pos={getattr(subclip, 'pos', 'NOT SET')}")
                if isinstance(subclip, TextClip):
                    logger.debug(f"TextClip {i+1}: text={getattr(subclip, 'text', 'NOT SET')}, "
                                f"font={getattr(subclip, 'font', 'NOT SET')}, "
                                f"fontsize={getattr(subclip, 'fontsize', 'NOT SET')}, "
                                f"color={getattr(subclip, 'color', 'NOT SET')}, "
                                f"mask={getattr(subclip, 'mask', 'NOT SET')}")
        
        if video_clip.audio is not None:
            logger.info("🔊 Video has audio, fixing audio issues...")
            if isinstance(video_clip.audio, CompositeAudioClip) and hasattr(video_clip.audio, 'clips'):
                logger.info("🔄 Detected CompositeAudioClip, fixing all sub-clips...")
                video_clip.audio.clips = fix_composite_audio_clips(video_clip.audio.clips)
            
            fixed_audio = fix_audio_clip_duration(video_clip.audio)
            
            if abs(float(fixed_audio.duration) - float(video_clip.duration)) > 0.01:
                logger.warning(f"⚠️ Audio duration ({fixed_audio.duration:.2f}s) != Video duration ({video_clip.duration:.2f}s)")
                if fixed_audio.duration > video_clip.duration:
                    fixed_audio = fixed_audio.subclip(0, video_clip.duration)
                    logger.info(f"✂️ Trimmed audio to match video duration")
                else:
                    loops_needed = int(np.ceil(video_clip.duration / fixed_audio.duration))
                    fixed_audio = concatenate_audioclips([fixed_audio] * loops_needed)
                    fixed_audio = fixed_audio.subclip(0, video_clip.duration)
                    logger.info(f"🔄 Looped audio to match video duration")
            
            video_clip = video_clip.set_audio(fixed_audio)
        
        default_params = {
            'fps': 30,
            'codec': 'libx264',
            'audio_codec': 'aac',
            'temp_audiofile': 'temp-audio.m4a',
            'remove_temp': True,
            'verbose': True,  # Enable verbose logging for debugging
            'logger': None
        }
        
        default_params.update(kwargs)
        
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"💾 Writing video to: {output_path} (Attempt {attempt}/{max_retries})")
                video_clip.write_videofile(output_path, **default_params)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"✅ Video successfully written: {output_path}")
                    return True
                else:
                    logger.error(f"❌ Video file not created or empty: {output_path}")
                    return False
                
            except Exception as e:
                logger.error(f"❌ Error writing video file (Attempt {attempt}/{max_retries}): {str(e)}")
                if attempt < max_retries:
                    logger.info(f"🔄 Retrying after 1.0s...")
                    time.sleep(1.0)
                else:
                    logger.error("❌ Max retries reached for writing video file")
                    return False
            
    except Exception as e:
        logger.error(f"❌ Error in safe_write_videofile: {str(e)}", exc_info=True)
        return False
    
    finally:
        try:
            if hasattr(video_clip, 'close'):
                video_clip.close()
        except:
            pass

def debug_audio_clip(audio_clip, clip_name="Unknown"):
    """
    Debug audio clip properties to identify issues.
    
    Args:
        audio_clip: AudioClip to debug
        clip_name: Name for logging
    """
    logger.debug(f"🔍 Debugging audio clip: {clip_name}")
    
    try:
        logger.debug(f"   - Duration: {getattr(audio_clip, 'duration', 'NOT SET')}")
        logger.debug(f"   - Start: {getattr(audio_clip, 'start', 'NOT SET')}")
        logger.debug(f"   - End: {getattr(audio_clip, 'end', 'NOT SET')}")
        logger.debug(f"   - FPS: {getattr(audio_clip, 'fps', 'NOT SET')}")
        
        if hasattr(audio_clip, 'clips'):
            logger.debug(f"   - Composite with {len(audio_clip.clips)} clips")
            for i, subclip in enumerate(audio_clip.clips):
                logger.debug(f"     Clip {i+1}: duration={getattr(subclip, 'duration', 'NOT SET')}, "
                            f"start={getattr(subclip, 'start', 'NOT SET')}")
        
        try:
            frame = audio_clip.get_frame(0)
            logger.debug(f"   - Frame at t=0: shape={np.shape(frame)}")
        except Exception as e:
            logger.error(f"   - Cannot get frame: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error debugging audio clip: {e}", exc_info=True)

def create_video_with_fixed_audio(video_path, audio_path, output_path):
    """
    Create video with properly handled audio to avoid errors.
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file  
        output_path: Output video path
        
    Returns:
        bool: Success status
    """
    try:
        video_clip = VideoFileClip(video_path)
        logger.info(f"📹 Loaded video: {video_clip.duration:.2f}s")
        
        audio_clip = create_safe_audio_clip(audio_path, target_duration=video_clip.duration)
        
        debug_audio_clip(audio_clip, "Generated Audio")
        
        final_video = video_clip.set_audio(audio_clip)
        
        success = safe_write_videofile(final_video, output_path)
        
        video_clip.close()
        audio_clip.close()
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error creating video with audio: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🧪 Testing audio fix utilities...")
    
    test_clip = AudioClip(make_frame=lambda t: np.array([0.0]), duration=30.0)
    debug_audio_clip(test_clip, "Test Silent Clip")
    
    print("✅ Audio fix utilities ready!")