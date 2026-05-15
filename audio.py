from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


def transcribir(audio_path):

    segments, _ = model.transcribe(
        audio_path,
        vad_filter=True
    )

    texto = ""

    for segment in segments:
        texto += segment.text + " "

    return texto.strip()