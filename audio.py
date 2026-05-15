from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu")

def transcribir(audio_path):
    segments, _ = model.transcribe(audio_path)

    return " ".join([s.text for s in segments])