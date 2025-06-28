from gtts import gTTS

def generate_voice(script, filename='output/voice.mp3'):
    tts = gTTS(script, lang='en')
    tts.save(filename)
