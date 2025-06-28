from moviepy.editor import TextClip, AudioFileClip, concatenate_videoclips

def create_video(script, voice_path="output/voice.mp3", video_path="output/video.mp4"):
    lines = [l.strip() for l in script.split('.') if l.strip()]
    clips = [TextClip(txt, fontsize=50, color='white', size=(1080,1920), bg_color='black').set_duration(2.5) for txt in lines]
    video = concatenate_videoclips(clips)
    audio = AudioFileClip(voice_path)
    final = video.set_audio(audio)
    final.write_videofile(video_path, fps=24)
