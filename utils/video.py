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
    level=logging.DEBUG,
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
    Create a TextClip with robust validation and fallback.

    Args:
        text: Text to display
        duration: Duration of the text clip
        **kwargs: Additional TextClip parameters (fontsize, color, etc.)

    Returns:
        MoviePy TextClip or ColorClip if creation fails
    """
    if not text or len(text.strip()) < 2 or text.strip().replace(':', '').replace(',', '').replace('.', '').isspace():
        logger.warning(f"⚠️ Invalid or too short text: '{text}', using fallback text")
        text = "Default Caption"
    
    # Cap duration for readability
    duration = min(max(float(duration), 0.5), 6.0)  # 0.5s to 6s
    logger.debug(f"📝 Adjusted caption duration to {duration:.2f}s for '{text}'")

    # Set default parameters with explicit validation
    default_params = {
        'font': kwargs.get('font', 'FreeSerif'),
        'fontsize': kwargs.get('fontsize', 40),
        'color': kwargs.get('color', 'white'),
        'stroke_color': kwargs.get('stroke_color', 'black'),
        'stroke_width': kwargs.get('stroke_width', 1),
        'size': (900, 150),
        'method': 'caption',
        'align': kwargs.get('align', 'center')
    }

    # Validate parameters
    if not isinstance(default_params['fontsize'], (int, float)) or default_params['fontsize'] <= 0:
        logger.warning(f"⚠️ Invalid fontsize {default_params['fontsize']}, using default 40")
        default_params['fontsize'] = 40
    if not isinstance(default_params['color'], str):
        logger.warning(f"⚠️ Invalid color {default_params['color']}, using default 'white'")
        default_params['color'] = 'white'
    if not isinstance(default_params['stroke_color'], str):
        logger.warning(f"⚠️ Invalid stroke_color {default_params['stroke_color']}, using default 'black'")
        default_params['stroke_color'] = 'black'
    if not isinstance(default_params['stroke_width'], (int, float)) or default_params['stroke_width'] < 0:
        logger.warning(f"⚠️ Invalid stroke_width {default_params['stroke_width']}, using default 1")
        default_params['stroke_width'] = 1

    try:
        logger.debug(f"📝 Creating TextClip for text: '{text}' with params: {default_params}")
        text_clip = TextClip(
            text.strip(),
            font=default_params['font'],
            fontsize=int(default_params['fontsize']),
            color=default_params['color'],
            stroke_color=default_params['stroke_color'],
            stroke_width=float(default_params['stroke_width']),
            size=default_params['size'],
            method=default_params['method'],
            align=default_params['align']
        )
        text_clip = validate_clip_properties(text_clip, f"Caption '{text}'")
        text_clip = text_clip.set_duration(duration).set_position(('center', 'bottom'))
        logger.info(f"✅ Created TextClip: duration={text_clip.duration:.2f}s, size={text_clip.size}, pos={text_clip.pos}")
        return text_clip
    except Exception as e:
        logger.error(f"❌ Failed to create TextClip for '{text}': {str(e)}", exc_info=True)
        try:
            fallback_clip = TextClip(
                "Fallback Caption",
                font='FreeSerif',
                fontsize=40,
                color='white',
                stroke_color='black',
                stroke_width=1,
                size=(900, 150),
                method='caption',
                align='center'
            )
            fallback_clip = validate_clip_properties(fallback_clip, f"Fallback Caption '{text}'")
            fallback_clip = fallback_clip.set_duration(duration).set_position(('center', 'bottom'))
            logger.info(f"✅ Created fallback TextClip")
            return fallback_clip
        except Exception as fallback_e:
            logger.error(f"❌ Failed to create fallback TextClip: {str(fallback_e)}")
            return ColorClip(size=(900, 150), color=(0, 0, 0), duration=duration)

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
                if logo.shape[2] == 4:
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
                if sticker.shape[2] == 4:
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
            if not script_text or len(script_text.strip()) < 10 or "narrative script about" in script_text.lower():
                logger.warning(f"⚠️ Invalid script_text: '{script_text}', using default")
                script_text = "AI advancements are transforming technology, creating new opportunities for innovation and research in various fields."

            # Load audio
            logger.info(f"🔊 Loading audio: {audio_path}")
            audio = AudioFileClip(audio_path)
            audio = fix_composite_audio_clips([audio])[0]
            debug_audio_clip(audio, "Main Audio")
            audio_duration = float(audio.duration)

            # Ensure video duration is 15-60 seconds
            target_duration = max(15.0, min(60.0, audio_duration))
            if abs(audio_duration - target_duration) > 0.01:
                logger.warning(f"⚠️ Audio duration ({audio_duration:.2f}s) != Video duration ({target_duration:.2f}s)")
                audio = audio.set_duration(target_duration)
                audio = fix_composite_audio_clips([audio])[0]
                debug_audio_clip(audio, "Adjusted Audio")

            # Additional validation for audio clip
            if not hasattr(audio, 'duration') or audio.duration is None:
                logger.error("❌ Audio clip has invalid duration")
                raise ValueError("Audio clip has invalid duration")
            if hasattr(audio, 'clips'):
                logger.debug(f"🔍 Audio clip is composite with {len(audio.clips)} sub-clips")
                for i, sub_clip in enumerate(audio.clips):
                    if not hasattr(sub_clip, 'start') or not isinstance(sub_clip.start, (int, float)):
                        logger.warning(f"⚠️ Sub-clip {i} has invalid start time: {sub_clip.start}, resetting to 0")
                        sub_clip.start = 0
                    if not hasattr(sub_clip, 'duration') or not isinstance(sub_clip.duration, (int, float)):
                        logger.warning(f"⚠️ Sub-clip {i} has invalid duration: {sub_clip.duration}, resetting to {target_duration}")
                        sub_clip.duration = target_duration

            num_images = len(image_paths)

            # Calculate image durations
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

            # Process images
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
                clip = clip.set_duration(max(float(duration), 0.5))

                if i > 0:
                    transition_type = random.choice(['fade', 'zoom', 'slide'])
                    if transition_type == 'fade':
                        clip = clip.crossfadein(0.2)
                    elif transition_type == 'zoom':
                        clip = clip.resize(lambda t: 1 + 0.03 * t / duration)
                    elif transition_type == 'slide':
                        clip = clip.set_position(lambda t: ('center', -30 + 30 * t / duration))

                clips.append(clip)

            # Concatenate clips
            logger.info("🔗 Concatenating image clips...")
            video = concatenate_videoclips(clips, method="compose", padding=-0.2)
            video = validate_clip_properties(video, "Concatenated Video")
            video = video.set_duration(float(target_duration))

            # Assign audio with fallback
            logger.info("🔊 Assigning audio to video...")
            if audio:
                try:
                    video = video.set_audio(audio)
                    logger.debug("✅ Audio successfully assigned to video")
                except Exception as e:
                    logger.error(f"❌ Failed to assign audio: {str(e)}", exc_info=True)
                    audio = AudioFileClip(audio_path).set_duration(target_duration)
                    video = video.set_audio(audio)
                    logger.info("✅ Fallback audio assignment successful")

            # Generate captions
            logger.info("📝 Generating captions...")
            try:
                import nltk
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)
                words = nltk.word_tokenize(script_text)
                # Aim for 8-12 captions, 6-8 words each
                words_per_caption = 6
                target_captions = max(8, min(12, int(target_duration / 5)))  # ~5s per caption
                phrases = [' '.join(words[i:i+words_per_caption]) for i in range(0, len(words), words_per_caption)][:target_captions]
                if not phrases or all(len(p.strip()) < 2 for p in phrases):
                    logger.warning("⚠️ No valid caption phrases generated, using fallback")
                    phrases = ["AI is transforming technology.", "New opportunities arise daily."] * (target_captions // 2)
                logger.info(f"📊 Generated {len(phrases)} caption phrases")
                phrase_duration = min(target_duration / max(len(phrases), 1), 6.0)  # Cap at 6s
                subtitles = []
                current_time = 0
                for phrase in phrases:
                    if len(phrase.strip()) >= 2:
                        duration = min(phrase_duration, 6.0)  # Cap duration
                        end_time = min(current_time + duration, target_duration)
                        subtitles.append(((current_time, end_time), phrase))
                        current_time = end_time
                if not subtitles:
                    subtitles = [((0, target_duration), "AI is transforming technology.")]
            except Exception as e:
                logger.error(f"❌ Failed to generate captions with NLTK: {str(e)}", exc_info=True)
                subtitles = [((0, target_duration), "AI is transforming technology.")]

            subtitle_clips = []
            for (start, end), phrase in subtitles:
                try:
                    caption_duration = max(float(end - start), 0.5)
                    caption_clip = create_safe_text_clip(
                        phrase,
                        duration=caption_duration,
                        fontsize=40,
                        color='white',
                        stroke_color='black',
                        stroke_width=1
                    )
                    if caption_clip:
                        caption_clip = validate_clip_properties(caption_clip, f"Caption '{phrase}'")
                        if caption_clip:
                            caption_clip = caption_clip.set_start(float(start)).set_duration(caption_duration)
                            subtitle_clips.append(caption_clip)
                            logger.info(f"✅ Set caption '{phrase}' start time to {start:.2f}s, duration {caption_duration:.2f}s")
                        else:
                            logger.warning(f"⚠️ Skipping caption '{phrase}' due to validation failure")
                    else:
                        logger.warning(f"⚠️ Skipping caption '{phrase}' due to creation failure")
                except Exception as e:
                    logger.error(f"❌ Failed to create caption for phrase '{phrase}': {str(e)}", exc_info=True)
                    continue

            # Validate subtitle clips
            subtitle_clips = [clip for clip in subtitle_clips if clip and hasattr(clip, 'duration') and clip.duration is not None]
            logger.info(f"📊 Using {len(subtitle_clips)} valid subtitle clips")

            # Create composite video
            logger.info("🔄 Creating composite video with subtitles...")
            video = CompositeVideoClip([video] + subtitle_clips, size=(1080, 1920))
            video = validate_clip_properties(video, "Final Composite Video")
            if not video or isinstance(video, ColorClip):
                logger.error("❌ Final composite video is invalid or a ColorClip, creating fallback")
                video = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=target_duration).set_audio(audio)

            # Fix composite video clips
            if isinstance(video, CompositeVideoClip) and hasattr(video, 'clips'):
                video.clips = fix_composite_video_clips(video.clips, fallback_duration=target_duration)

            # Ensure video audio is valid
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

            # Write video
            logger.info(f"💾 Writing video to {output_path}...")
            success = safe_write_videofile(
                video,
                output_path,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                bitrate="2000k",
                threads=2,
                fps=30
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
    audio_path = "output/narration_20250708_125535.mp3"
    image_paths = [
        "output/frame_20250708_125539_1.png",
        "output/frame_20250708_125546_2.png",
        "output/frame_20250708_125555_3.png",
        "output/frame_20250708_125601_4.png",
        "output/frame_20250708_125605_5.png",
        "output/frame_20250708_125610_6.png",
        "output/frame_20250708_125612_7.png",
        "output/frame_20250708_125617_8.png",
        "output/frame_20250708_125622_9.png",
        "output/frame_20250708_125628_10.png"
    ]
    output_dir = "output"
    script_text = "AI advancements are transforming technology, creating new opportunities for innovation and research in various fields."
    video_path = create_video(audio_path, image_paths, output_dir, script_text)
    if video_path:
        print(f"✅ Video created at: {video_path}")
    else:
        print("❌ Video creation failed.")