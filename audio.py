from faster_whisper import WhisperModel
import ffmpeg
import tempfile
import os

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


def convertir_audio(input_path):

    output_path = tempfile.mktemp(suffix=".wav")

    (
        ffmpeg
        .input(input_path)
        .output(
            output_path,
            format="wav",
            acodec="pcm_s16le",
            ac=1,
            ar="16000"
        )
        .overwrite_output()
        .run(quiet=True)
    )

    return output_path


def transcribir(audio_path):

    wav_path = convertir_audio(audio_path)

    segments, _ = model.transcribe(
        wav_path,
        beam_size=1,
        vad_filter=True
    )

    texto = " ".join([s.text for s in segments])

    os.remove(wav_path)

    return texto.strip()