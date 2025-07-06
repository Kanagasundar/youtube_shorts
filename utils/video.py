#!/usr/bin/env python3
"""
MoviePy _NoValueType Error Fix - Comprehensive solution for MoviePy clip property issues
"""

import os
import logging
import numpy as np
from moviepy.editor import *
from moviepy.audio.AudioClip import AudioClip
from moviepy.video.VideoClip import VideoClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.video.fx.resize import resize
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class _NoValueType:
    """Mock _NoValueType for detection"""
    pass

def is_no_value(value):
    """Check if value is _NoValueType or similar undefined value"""
    return (
        value is None or 
        str(type(value)).find('_NoValueType') != -1 or
        str(value).find('_NoValueType') != -1 or
        isinstance(value, type(None))
    )

def safe_float(value, default=0.0):
    """Safely convert value to float, handling _NoValueType"""
    if is_no_value(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def fix_clip_properties(clip, fallback_duration=30.0, fallback_start=0.0):
    """
    Fix all clip properties to prevent _NoValueType errors
    
    Args:
        clip: MoviePy clip (Video or Audio)
        fallback_duration: Default duration if invalid
        fallback_start: Default start time if invalid
        
    Returns:
        Fixed clip with proper properties
    """
    try:
        # Get current properties safely
        current_duration = getattr(clip, 'duration', None)
        current_start = getattr(clip, 'start', None)
        current_end = getattr(clip, 'end', None)
        
        # Fix duration
        if is_no_value(current_duration):
            logger.warning(f"⚠️ Clip has invalid duration, using fallback: {fallback_duration}s")
            clip = clip.set_duration(fallback_duration)
        else:
            try:
                duration = safe_float(current_duration, fallback_duration)
                if duration <= 0:
                    duration = fallback_duration
                clip = clip.set_duration(duration)
            except:
                clip = clip.set_duration(fallback_duration)
        
        # Fix start time
        if is_no_value(current_start):
            logger.info(f"🔄 Setting start time to: {fallback_start}s")
            clip = clip.set_start(fallback_start)
        else:
            try:
                start = safe_float(current_start, fallback_start)
                clip = clip.set_start(start)
            except:
                clip = clip.set_start(fallback_start)
        
        # Fix end time based on start + duration
        try:
            start_time = safe_float(clip.start, fallback_start)
            duration = safe_float(clip.duration, fallback_duration)
            end_time = start_time + duration
            clip = clip.set_end(end_time)
        except:
            clip = clip.set_end(fallback_start + fallback_duration)
        
        # Log fixed properties
        logger.info(f"✅ Fixed clip properties: duration={clip.duration:.2f}s, start={clip.start:.2f}s, end={clip.end:.2f}s")
        
        return clip
        
    except Exception as e:
        logger.error(f"❌ Error fixing clip properties: {e}")
        # Return a basic clip with safe properties
        if hasattr(clip, 'make_frame'):
            return clip.set_duration(fallback_duration).set_start(fallback_start)
        else:
            # Create a silent audio clip as fallback
            return AudioClip(make_frame=lambda t: np.array([0.0]), duration=fallback_duration).set_start(fallback_start)

def fix_composite_video_clips(clips, fallback_duration=30.0):
    """
    Fix all video clips in a composite to prevent _NoValueType errors
    
    Args:
        clips: List of video clips
        fallback_duration: Default duration for invalid clips
        
    Returns:
        List of fixed video clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            logger.info(f"🔄 Fixing video clip {i+1}/{len(clips)}")
            
            # Handle different clip types
            if hasattr(clip, 'clips'):  # Composite clip
                logger.info(f"   - Composite clip with {len(clip.clips)} sub-clips")
                clip.clips = fix_composite_video_clips(clip.clips, fallback_duration)
            
            # Fix basic properties
            fixed_clip = fix_clip_properties(clip, fallback_duration, fallback_start=0.0)
            
            # Special handling for TextClip
            if hasattr(clip, 'txt') or str(type(clip)).find('TextClip') != -1:
                logger.info(f"   - TextClip detected, ensuring proper duration")
                # TextClips sometimes have issues with duration
                if is_no_value(fixed_clip.duration):
                    fixed_clip = fixed_clip.set_duration(min(5.0, fallback_duration))
            
            # Ensure position is set for overlay clips
            if not hasattr(fixed_clip, 'pos') or fixed_clip.pos is None:
                fixed_clip = fixed_clip.set_position('center')
            
            fixed_clips.append(fixed_clip)
            logger.info(f"✅ Fixed video clip {i+1}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing video clip {i+1}: {e}")
            # Create black clip as fallback
            try:
                black_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=fallback_duration)
                black_clip = black_clip.set_start(0)
                fixed_clips.append(black_clip)
                logger.info(f"🔄 Created fallback black clip for clip {i+1}")
            except:
                logger.error(f"❌ Failed to create fallback for clip {i+1}")
    
    return fixed_clips

def fix_composite_audio_clips(clips, fallback_duration=30.0):
    """
    Fix all audio clips in a composite to prevent _NoValueType errors
    
    Args:
        clips: List of audio clips
        fallback_duration: Default duration for invalid clips
        
    Returns:
        List of fixed audio clips
    """
    fixed_clips = []
    
    for i, clip in enumerate(clips):
        try:
            logger.info(f"🔊 Fixing audio clip {i+1}/{len(clips)}")
            
            # Handle composite audio clips
            if hasattr(clip, 'clips'):
                logger.info(f"   - Composite audio clip with {len(clip.clips)} sub-clips")
                clip.clips = fix_composite_audio_clips(clip.clips, fallback_duration)
            
            # Fix basic properties
            fixed_clip = fix_clip_properties(clip, fallback_duration, fallback_start=0.0)
            
            # Ensure audio has proper sample rate
            if not hasattr(fixed_clip, 'fps') or fixed_clip.fps is None:
                fixed_clip.fps = 44100
            
            fixed_clips.append(fixed_clip)
            logger.info(f"✅ Fixed audio clip {i+1}")
            
        except Exception as e:
            logger.error(f"❌ Error fixing audio clip {i+1}: {e}")
            # Create silent clip as fallback
            try:
                silent_clip = AudioClip(make_frame=lambda t: np.array([0.0]), duration=fallback_duration)
                silent_clip = silent_clip.set_start(0)
                fixed_clips.append(silent_clip)
                logger.info(f"🔄 Created fallback silent clip for clip {i+1}")
            except:
                logger.error(f"❌ Failed to create fallback for audio clip {i+1}")
    
    return fixed_clips

def create_safe_text_clip(text, duration, fontsize=60, color='white', stroke_color='black', stroke_width=1):
    """
    Create a safe TextClip that won't cause _NoValueType errors
    
    Args:
        text: Text to display
        duration: Duration of the text clip
        fontsize: Font size
        color: Text color
        stroke_color: Stroke color
        stroke_width: Stroke width
        
    Returns:
        Safe TextClip with proper properties
    """
    try:
        # Ensure duration is valid
        duration = safe_float(duration, 3.0)
        if duration <= 0:
            duration = 3.0
        
        logger.info(f"📝 Creating text clip: '{text}' for {duration:.2f}s")
        
        # Try different fonts
        fonts = ['Arial', 'DejaVu-Sans', 'Liberation-Sans', 'FreeSans']
        
        for font in fonts:
            try:
                clip = TextClip(
                    text,
                    fontsize=fontsize,
                    color=color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    font=font,
                    size=(1000, None),
                    method='caption',
                    align='center'
                )
                
                # Explicitly set all properties
                clip = clip.set_duration(duration)
                clip = clip.set_start(0)
                clip = clip.set_end(duration)
                clip = clip.set_position(('center', 'bottom'))
                
                # Add fade effects
                clip = clip.fadein(0.3).fadeout(0.3)
                
                logger.info(f"✅ Created text clip with font: {font}")
                return clip
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to create text clip with font {font}: {e}")
                continue
        
        # If all fonts fail, create a simple colored rectangle as fallback
        logger.warning("🔄 All fonts failed, creating fallback rectangle")
        fallback_clip = ColorClip(size=(400, 100), color=(128, 128, 128), duration=duration)
        fallback_clip = fallback_clip.set_start(0).set_position(('center', 'bottom'))
        return fallback_clip
        
    except Exception as e:
        logger.error(f"❌ Error creating text clip: {e}")
        # Create minimal fallback
        fallback_clip = ColorClip(size=(200, 50), color=(64, 64, 64), duration=duration)
        fallback_clip = fallback_clip.set_start(0).set_position('center')
        return fallback_clip

def safe_write_videofile(video_clip, output_path, **kwargs):
    """
    Safely write video file with comprehensive _NoValueType error prevention
    
    Args:
        video_clip: MoviePy VideoClip
        output_path: Output file path
        **kwargs: Additional arguments for write_videofile
        
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"💾 Starting safe video write to: {output_path}")
        
        # Fix main video clip properties
        video_clip = fix_clip_properties(video_clip)
        
        # Fix composite video clips
        if isinstance(video_clip, CompositeVideoClip):
            logger.info("🔄 Fixing composite video clips...")
            video_clip.clips = fix_composite_video_clips(video_clip.clips, video_clip.duration)
            
            # Ensure main clip is first and has proper duration
            if video_clip.clips:
                main_clip = video_clip.clips[0]
                main_duration = safe_float(main_clip.duration, 30.0)
                
                # Fix all clip timings relative to main clip
                for i, clip in enumerate(video_clip.clips):
                    if i == 0:
                        continue  # Skip main clip
                    
                    # Ensure overlay clips don't exceed main clip duration
                    clip_duration = safe_float(clip.duration, 3.0)
                    clip_start = safe_float(clip.start, 0.0)
                    
                    if clip_start + clip_duration > main_duration:
                        new_duration = main_duration - clip_start
                        if new_duration > 0:
                            video_clip.clips[i] = clip.set_duration(new_duration)
                        else:
                            video_clip.clips[i] = clip.set_start(0).set_duration(min(clip_duration, main_duration))
        
        # Fix audio if present
        if hasattr(video_clip, 'audio') and video_clip.audio is not None:
            logger.info("🔊 Fixing audio clips...")
            
            # Handle composite audio
            if hasattr(video_clip.audio, 'clips'):
                video_clip.audio.clips = fix_composite_audio_clips(
                    video_clip.audio.clips, 
                    video_clip.duration
                )
            
            # Fix main audio properties
            video_clip.audio = fix_clip_properties(video_clip.audio, video_clip.duration)
            
            # Ensure audio duration matches video duration
            audio_duration = safe_float(video_clip.audio.duration, video_clip.duration)
            video_duration = safe_float(video_clip.duration, 30.0)
            
            if abs(audio_duration - video_duration) > 0.1:  # More than 0.1s difference
                logger.warning(f"⚠️ Audio duration ({audio_duration:.2f}s) != Video duration ({video_duration:.2f}s)")
                
                if audio_duration > video_duration:
                    # Trim audio
                    video_clip.audio = video_clip.audio.subclip(0, video_duration)
                    logger.info("✂️ Trimmed audio to match video duration")
                else:
                    # Extend audio by looping
                    try:
                        loops_needed = int(np.ceil(video_duration / audio_duration))
                        extended_audio = concatenate_audioclips([video_clip.audio] * loops_needed)
                        video_clip.audio = extended_audio.subclip(0, video_duration)
                        logger.info(f"🔄 Extended audio by looping ({loops_needed} loops)")
                    except:
                        logger.warning("⚠️ Failed to extend audio, keeping original")
        
        # Set safe default parameters
        safe_params = {
            'fps': 30,
            'codec': 'libx264',
            'audio_codec': 'aac',
            'temp_audiofile': 'temp-audio.m4a',
            'remove_temp': True,
            'verbose': False,
            'logger': None,
            'preset': 'medium',
            'threads': 2
        }
        
        # Update with user parameters
        safe_params.update(kwargs)
        
        # Final validation
        final_duration = safe_float(video_clip.duration, 30.0)
        if final_duration <= 0:
            raise ValueError(f"Invalid final video duration: {final_duration}")
        
        logger.info(f"📊 Final video properties: duration={final_duration:.2f}s")
        
        # Write the video file
        logger.info("🎬 Writing video file...")
        video_clip.write_videofile(output_path, **safe_params)
        
        # Verify output
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"✅ Video successfully written: {output_path} ({os.path.getsize(output_path)} bytes)")
            return True
        else:
            logger.error(f"❌ Video file not created or empty: {output_path}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in safe_write_videofile: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def debug_clip_properties(clip, clip_name="Unknown"):
    """
    Debug clip properties to identify _NoValueType issues
    
    Args:
        clip: MoviePy clip
        clip_name: Name for logging
    """
    logger.info(f"🔍 Debugging clip: {clip_name}")
    
    try:
        # Check basic properties
        duration = getattr(clip, 'duration', 'NOT_SET')
        start = getattr(clip, 'start', 'NOT_SET')
        end = getattr(clip, 'end', 'NOT_SET')
        
        logger.info(f"   - Duration: {duration} (type: {type(duration)})")
        logger.info(f"   - Start: {start} (type: {type(start)})")
        logger.info(f"   - End: {end} (type: {type(end)})")
        
        # Check for _NoValueType
        if is_no_value(duration):
            logger.warning(f"   - ⚠️ Duration is _NoValueType or None")
        if is_no_value(start):
            logger.warning(f"   - ⚠️ Start is _NoValueType or None")
        if is_no_value(end):
            logger.warning(f"   - ⚠️ End is _NoValueType or None")
        
        # Check if composite
        if hasattr(clip, 'clips'):
            logger.info(f"   - Composite with {len(clip.clips)} sub-clips")
            for i, subclip in enumerate(clip.clips):
                sub_duration = getattr(subclip, 'duration', 'NOT_SET')
                sub_start = getattr(subclip, 'start', 'NOT_SET')
                logger.info(f"     Sub-clip {i+1}: duration={sub_duration}, start={sub_start}")
                
    except Exception as e:
        logger.error(f"❌ Error debugging clip: {e}")

# Test function
def test_fix():
    """Test the fix with a simple example"""
    try:
        logger.info("🧪 Testing _NoValueType fix...")
        
        # Create a test clip that might have issues
        test_clip = ColorClip(size=(1080, 1920), color=(255, 0, 0), duration=5.0)
        
        # Debug original
        debug_clip_properties(test_clip, "Original Test Clip")
        
        # Fix it
        fixed_clip = fix_clip_properties(test_clip)
        
        # Debug fixed
        debug_clip_properties(fixed_clip, "Fixed Test Clip")
        
        logger.info("✅ Test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    test_fix()