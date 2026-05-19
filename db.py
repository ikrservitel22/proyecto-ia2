from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

def transcribir_array(audio_array):

    segments, info = model.transcribe(

        audio_array,

        language="es",

        beam_size=1,

        vad_filter=False,

        condition_on_previous_text=True,

        temperature=0.0,

        initial_prompt="Conversación natural en español."
    )

    texto = " ".join([
        s.text for s in segments
    ])

    return texto.strip()