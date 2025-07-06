#!/usr/bin/env python3
"""
Video creation utilities for YouTube Shorts automation
"""

import os
import logging
import cv2
import numpy as np
from pathlib import Path
import moviepy
from moviepy.editor import *
from moviepy.config import change_settings
from PIL import Image
import random
from datetime import datetime
import subprocess
from voice import fix_composite_audio_clips, debug_audio_clip, safe_write_videofile, fix_composite_video_clips, validate_clip_properties

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Detailed logging for debugging
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log MoviePy version for debugging
logger.info(f"MoviePy version: {moviepy.__version__}")

# Set ImageMagick binary path
IMAGEMAGICK_BINARY = None
for path in ['/usr/bin/convert', '/usr/local/bin/convert', '/bin/convert']:
    if os.path.exists(path):
        IMAGEMAGICK_BINARY = path
        break

if IMAGEMAGICK_BINARY:
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
    logger.info(f"✅ Found ImageMagick binary at: {IMAGEMAGICK_BINARY}")
else:
    logger.warning("⚠️ ImageMagick binary not found, text rendering may fail")

def create_safe_text_clip(text: str, duration: float, **kwargs) -> TextClip:
    """
    Create a TextClip with safe font handling using FreeSerif and optimized parameters.

    Args:
        text: Text to display
        duration: Duration of the text clip
        **kwargs: Additional TextClip parameters (fontsize, color, etc.)

    Returns:
        MoviePy TextClip or fallback ColorClip if creation fails
    """
    try:
        logger.debug(f"📝 Attempting to create TextClip for text: '{text}'")
        text_clip = TextClip(
            text,
            font='FreeSerif',  # Use FreeSerif directly
            fontsize=kwargs.get('fontsize', 50),
            color=kwargs.get('color', 'white'),
            stroke_color=kwargs.get('stroke_color', 'black'),
            stroke_width=kwargs.get('stroke_width', 1),
            size=(1080, 200),  # Fixed size for captions
            method='label',  # Faster rendering
            align=kwargs.get('align', 'center')
        )
        text_clip = validate_clip_properties(text_clip, f"Caption '{text}'")
        text_clip = text_clip.set_duration(max(float(duration), 0.5)).set_position(('center', 'bottom')).fadein(0.1).fadeout(0.1)
        logger.debug(f"✅ Successfully created TextClip: duration={text_clip.duration:.2f}s")
        return text_clip
    except Exception as e:
        logger.error(f"❌ Failed to create TextClip for '{text}': {str(e)}", exc_info=True)
        return ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=max(float(duration), 0.5))

def add_overlays(image, logo_path=None, sticker_path=None):
    """
    Add logo and sticker overlays to an image using OpenCV.

    Args:
        image: NumPy array of the image
        logo_path (str): Path to logo image
        sticker_path (str): Path to sticker image

    Returns:
        NumPy array with overlays
    """
    img = image.copy()
    h, w = img.shape[:2]

    # Add logo (top-left corner)
    if logo_path and os.path.exists(logo_path):
        try:
            logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
            if logo is not None:
                logo_h, logo_w = logo.shape[:2]
                logo = cv2.resize(logo, (int(logo_w * 0.2), int(logo_h * 0.2)))
                logo_h, logo_w = logo.shape[:2]
                roi = img[10:10+logo_h, 10:10+logo_w]
                if logo.shape[2] == 4:  # Handle transparency
                    alpha = logo[:, :, 3] / 255.0
                    for c in range(3):
                        roi[:, :, c] = (1.0 - alpha) * roi[:, :, c] + alpha * logo[:, :, c]
                else:
                    roi[:] = logo
                img[10:10+logo_h, 10:10+logo_w] = roi
                logger.debug("✅ Added logo overlay")
            else:
                logger.warning(f"⚠️ Failed to load logo: {logo_path}")
        except Exception as e:
            logger.error(f"❌ Error adding logo: {str(e)}", exc_info=True)

    # Add sticker (top-right corner)
    if sticker_path and os.path.exists(sticker_path):
        try:
            sticker = cv2.imread(sticker_path, cv2.IMREAD_UNCHANGED)
            if sticker is not None:
                sticker_h, sticker_w = sticker.shape[:2]
                sticker = cv2.resize(sticker, (int(sticker_w * 0.2), int(sticker_h * 0.2)))
                sticker_h, sticker_w = sticker.shape[:2]
                roi = img[10:10+sticker_h, w-sticker_w-10:w-10]
                if sticker.shape[2] == 4:  # Handle transparency
                    alpha = sticker[:, :, 3] / 255.0
                    for c in range(3):
                        roi[:, :, c] = (1.0 - alpha) * roi[:, :, c] + alpha * sticker[:, :, c]
                else:
                    roi[:] = sticker
                img[10:10+sticker_h, w-sticker_w-10:w-10] = roi
                logger.debug("✅ Added sticker overlay")
            else:
                logger.warning(f"⚠️ Failed to load sticker: {sticker_path}")
        except Exception as e:
            logger.error(f"❌ Error adding sticker: {str(e)}", exc_info=True)

    return img

def create_video(audio_path: str, image_paths: list, output_dir: str, script_text: str, max_retries: int = 3) -> str:
    """
    Create a YouTube Shorts video with overlays, transitions, captions, and 9:16 aspect ratio.

    Args:
        audio_path (str): Path to narration audio
        image_paths (list): List of image paths
        output_dir (str): Directory to save video
        script_text (str): Script text for captions
        max_retries (int): Maximum retry attempts

    Returns:
        str: Path to generated video or None if failed
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🎬 Starting video creation (Attempt {attempt}/{max_retries})...")

            # Validate inputs
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            if not isinstance(image_paths, list) or not all(os.path.exists(p) for p in image_paths):
                raise FileNotFoundError(f"Image sequence not found or invalid: {image_paths}")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"✅ Created output directory: {output_dir}")

            # Load audio
            logger.info(f"🔊 Loading audio: {audio_path}")
            audio = AudioFileClip(audio_path)
            audio = fix_composite_audio_clips([audio])[0]  # Fix audio clip
            debug_audio_clip(audio, "Main Audio")
            audio_duration = float(audio.duration)

            # Ensure video duration is 15-60 seconds (YouTube Shorts max)
            target_duration = max(15.0, min(60.0, audio_duration))
            if abs(audio_duration - target_duration) > 0.01:
                logger.warning(f"⚠️ Audio duration ({audio_duration:.2f}s) != Video duration ({target_duration:.2f}s)")
                audio = audio.set_duration(target_duration)
                audio = fix_composite_audio_clips([audio])[0]
                debug_audio_clip(audio, "Adjusted Audio")

            num_images = len(image_paths)

            # Calculate variable image durations (0.5-6s)
            if num_images > 0:
                min_duration_per_image = 0.5
                max_duration_per_image = 6.0
                durations = [random.uniform(min_duration_per_image, max_duration_per_image) for _ in range(num_images)]
                total_image_duration = sum(durations)
                if total_image_duration != target_duration:
                    scale_factor = target_duration / total_image_duration
                    durations = [min(d * scale_factor, max_duration_per_image) for d in durations]
            else:
                durations = [target_duration]

            # Process images with OpenCV
            logger.info(f"🖼️ Pre-processing {num_images} images...")
            clips = []
            logo_path = os.path.join(output_dir, "logo.png")
            sticker_path = os.path.join(output_dir, "sticker.png")

            for i, (image_path, duration) in enumerate(zip(image_paths, durations)):
                logger.info(f"🖼️ Processing image {i+1}: {image_path}")
                img = Image.open(image_path).convert("RGB")
                img_w, img_h = img.size
                target_w, target_h = 1080, 1920
                if img_w / img_h > target_w / target_h:
                    new_w = int(target_h * img_w / img_h)
                    img = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
                    left = (new_w - target_w) // 2
                    img = img.crop((left, 0, left + target_w, target_h))
                else:
                    new_h = int(target_w * img_h / img_w)
                    img = img.resize((target_w, new_h), Image.Resampling.LANCZOS)
                    top = (new_h - target_h) // 2
                    img = img.crop((0, top, target_w, top + target_h))

                img_np = np.array(img)
                logger.debug(f"Initial image shape: {img_np.shape}, dtype: {img_np.dtype}")

                if img_np.shape[2] != 3:
                    raise ValueError(f"Image {image_path} has unexpected channel count: {img_np.shape[2]}")

                img_np = add_overlays(img_np, logo_path, sticker_path)

                debug_path = os.path.join(output_dir, f"debug_frame_{i+1}.png")
                cv2.imwrite(debug_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
                logger.info(f"🖼️ Saved debug image: {debug_path}")

                clip = ImageClip(img_np).set_duration(duration)
                clip = validate_clip_properties(clip, f"Image Clip {i+1}")
                clip = clip.set_duration(max(float(duration), 0.5))  # Explicitly set duration after validation

                if i > 0:
                    transition_type = random.choice(['fade', 'zoom', 'slide'])
                    if transition_type == 'fade':
                        clip = clip.crossfadein(0.3)
                    elif transition_type == 'zoom':
                        clip = clip.resize(lambda t: 1 + 0.05 * t / duration)
                    elif transition_type == 'slide':
                        clip = clip.set_position(lambda t: ('center', -50 + 50 * t / duration))

                clips.append(clip)

            # Concatenate clips
            logger.info("🔗 Concatenating image clips...")
            video = concatenate_videoclips(clips, method="compose", padding=-0.3)
            video = validate_clip_properties(video, "Concatenated Video")
            video = video.set_audio(audio)
            video = video.set_duration(float(target_duration))

            # Generate captions with MoviePy
            logger.info("📝 Generating captions...")
            try:
                import nltk
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
                words = nltk.word_tokenize(script_text)
                # Combine words into phrases (6 words per caption)
                words_per_caption = 6
                phrases = [' '.join(words[i:i+words_per_caption]) for i in range(0, len(words), words_per_caption)]
                logger.info(f"📊 Generated {len(phrases)} caption phrases")
                phrase_duration = target_duration / max(len(phrases), 1)
                subtitles = []
                current_time = 0
                for phrase in phrases:
                    subtitles.append(((current_time, current_time + phrase_duration), phrase))
                    current_time += max(phrase_duration, 0.5)
                # Adjust subtitle timings to fit target_duration
                if subtitles:
                    last_end = subtitles[-1][0][1]
                    if last_end > target_duration:
                        scale_factor = target_duration / last_end
                        subtitles = [((start * scale_factor, min(end * scale_factor, target_duration)), phrase)
                                    for (start, end), phrase in subtitles]
            except Exception as e:
                logger.error(f"❌ Failed to generate captions with NLTK: {str(e)}", exc_info=True)
                subtitles = [((0, target_duration), script_text)]  # Fallback to single caption

            subtitle_clips = []
            for (start, end), phrase in subtitles:
                try:
                    caption_clip = create_safe_text_clip(
                        phrase,
                        duration=end - start,
                        fontsize=50,
                        color='white',
                        stroke_color='black',
                        stroke_width=1
                    )
                    caption_clip = caption_clip.set_start(float(start))
                    subtitle_clips.append(caption_clip)
                    logger.info(f"✅ Set caption '{phrase}' start time to {start:.2f}s")
                except Exception as e:
                    logger.error(f"❌ Failed to create caption for phrase '{phrase}': {str(e)}", exc_info=True)
                    continue

            # Create composite video
            logger.info("🔄 Creating composite video with subtitles...")
            video = CompositeVideoClip([video] + subtitle_clips, size=(1080, 1920))
            video = validate_clip_properties(video, "Final Composite Video")

            # Fix all video clips in composite
            video.clips = fix_composite_video_clips(video.clips, fallback_duration=target_duration)

            # Ensure video audio is fixed
            if video.audio is not None:
                video.audio = fix_composite_audio_clips([video.audio])[0]
                debug_audio_clip(video.audio, "Final Video Audio")

            # Log final video properties
            logger.info(f"🔍 Final video clip: duration={getattr(video, 'duration', 'NOT SET'):.2f}s, "
                       f"start={getattr(video, 'start', 'NOT SET')}, "
                       f"size={getattr(video, 'size', 'NOT SET')}, "
                       f"fps={getattr(video, 'fps', 'NOT SET')}")

            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(output_dir) / f"video_{timestamp}.mp4")

            # Write video using safe_write_videofile
            logger.info(f"💾 Writing video to {output_path}...")
            success = safe_write_videofile(
                video,
                output_path,
                codec="libx264",
                audio_codec="aac",
                preset="fast",
                bitrate="3000k",
                threads=2,
                fps=24
            )

            if not success:
                raise RuntimeError("Failed to write video file")

            # Clean up resources
            audio.close()
            video.close()
            for clip in clips + subtitle_clips:
                try:
                    clip.close()
                except:
                    pass
            logger.info(f"✅ Video created successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Failed to create video (Attempt {attempt}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries:
                logger.info(f"🔄 Retrying in 1.0s...")
                import time
                time.sleep(1.0)
            else:
                logger.error("❌ Max retries reached. Video creation failed.")
                if 'img_np' in locals():
                    debug_path = os.path.join(output_dir, f"debug_last_frame.png")
                    cv2.imwrite(debug_path, cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
                    logger.info(f"🖼️ Saved last processed frame for debugging: {debug_path}")
                return None
        finally:
            # Ensure resources are released
            if 'audio' in locals():
                try:
                    audio.close()
                except:
                    pass
            if 'video' in locals():
                try:
                    video.close()
                except:
                    pass
            for clip in locals().get('clips', []) + locals().get('subtitle_clips', []):
                try:
                    clip.close()
                except:
                    pass

def cleanup():
    """
    Clean up temporary files.
    """
    try:
        logger.info("🧹 Cleaning up temporary files...")
        temp_files = [f for f in os.listdir() if f.startswith('temp-') or f.endswith('.m4a') or f.startswith('temp_caption')]
        for file in temp_files:
            try:
                os.remove(file)
                logger.info(f"✅ Removed {file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {file}: {e}")
        logger.info(f"✅ Cleaned up {len(temp_files)} temporary files")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    audio_path = "output/narration_20250704_084011.mp3"
    image_paths = [
        f"output/frame_20250704_084016_1.png",
        f"output/frame_20250704_084022_2.png",
        f"output/frame_20250704_084031_3.png",
        f"output/frame_20250704_084035_4.png",
        f"output/frame_20250704_084047_5.png"
    ]
    output_dir = "output"
    script_text = "AI just solved a 50-year-old problem in mathematics, opening new possibilities for research."
    video_path = create_video(audio_path, image_paths, output_dir, script_text)
    if video_path:
        print(f"✅ Video created at: {video_path}")
    else:
        print("❌ Video creation failed.")