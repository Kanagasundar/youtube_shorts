import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import tempfile

def create_text_image(text, width=1080, height=200, fontsize=50):
    """Create a text image using PIL instead of ImageMagick"""
    # Create a black image
    img = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font, fall back to default if not available
    try:
        # Try common system fonts
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/System/Library/Fonts/Arial.ttf',  # macOS
            'C:/Windows/Fonts/arial.ttf'  # Windows
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, fontsize)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Word wrap text
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= width - 40:  # 20px margin on each side
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Calculate total text height
    line_height = fontsize + 10
    total_height = len(lines) * line_height
    start_y = (height - total_height) // 2
    
    # Draw each line
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, font=font, fill='white')
    
    return np.array(img)

def create_video(voice_path, script, output_path):
    """Create video with text overlays using PIL instead of ImageMagick"""
    try:
        # Load audio
        audio = mp.AudioFileClip(voice_path)
        duration = audio.duration
        
        # Split script into sentences
        sentences = [s.strip() for s in script.replace('?', '?|').replace('!', '!|').replace('.', '.|').split('|') if s.strip()]
        
        if not sentences:
            sentences = [script]  # Fallback to full script
        
        # Calculate duration per sentence
        time_per_sentence = duration / len(sentences)
        
        # Create text clips using PIL
        clips = []
        for i, sentence in enumerate(sentences):
            # Create text image using PIL
            text_img = create_text_image(sentence, width=1080, height=200, fontsize=40)
            
            # Save temporary image
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                img_pil = Image.fromarray(text_img)
                img_pil.save(tmp_file.name)
                
                # Create clip from image
                img_clip = mp.ImageClip(tmp_file.name, duration=time_per_sentence)
                img_clip = img_clip.set_position('center')
                clips.append(img_clip)
                
                # Clean up temp file
                os.unlink(tmp_file.name)
        
        # Concatenate all text clips
        if clips:
            video = mp.concatenate_videoclips(clips)
        else:
            # Fallback: create a simple black video
            video = mp.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=duration)
        
        # Set audio
        final_video = video.set_audio(audio)
        
        # Write video file
        final_video.write_videofile(
            output_path, 
            fps=24, 
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        # Clean up
        audio.close()
        video.close()
        final_video.close()
        
        print(f"Video created successfully: {output_path}")
        
    except Exception as e:
        print(f"Error creating video: {e}")
        # Create a minimal fallback video
        try:
            audio = mp.AudioFileClip(voice_path)
            black_clip = mp.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=audio.duration)
            final_video = black_clip.set_audio(audio)
            final_video.write_videofile(output_path, fps=24, verbose=False, logger=None)
            print(f"Fallback video created: {output_path}")
        except Exception as fallback_error:
            print(f"Fallback video creation failed: {fallback_error}")
            raise