from faster_whisper import WhisperModel
import numpy as np

model = WhisperModel(
    "turbo",
    device="cpu",
    compute_type="int8"
)

def transcribir_array(audio_array, prompt=None):

    segments, info = model.transcribe(
        audio_array,
        language="es",
        beam_size=1,
        best_of=1,
        vad_filter=False,
        condition_on_previous_text=True,
        temperature=0.0,
        initial_prompt=prompt
    )

    texto = " ".join(s.text.strip() for s in segments)

    return texto.strip()