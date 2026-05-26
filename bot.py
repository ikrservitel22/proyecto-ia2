from dotenv import load_dotenv
import os
import numpy as np
import requests
import psycopg2
import webrtcvad
from faster_whisper import WhisperModel

load_dotenv()

# ====================================================
# WHISPER
# ====================================================

whisper_model = WhisperModel(
    os.getenv("WHISPER_MODEL", "small"),
    device="cpu",
    compute_type="int8"
)

# ====================================================
# POSTGRES
# ====================================================

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "postgres"),
    database=os.getenv("POSTGRES_DB", "ia_support"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    port=os.getenv("POSTGRES_PORT", 5432)
)

print("✅ PostgreSQL conectado")

# ====================================================
# TRANSCRIBIR AUDIO
# ====================================================

def transcribir_audio(audio_np):

    audio_np = audio_np.flatten()

    audio_float = (
        audio_np.astype(np.float32) / 32768.0
    )

    segments, _ = whisper_model.transcribe(
        audio_float,
        language="es",
        vad_filter=True,
        beam_size=1
    )

    texto = " ".join(
        [s.text for s in segments]
    ).strip()

    return texto


# ====================================================
# VAD CONFIG
# ====================================================

vad = webrtcvad.Vad(2)

SAMPLE_RATE = 16000

# webrtcvad SOLO soporta:
# 10,20,30 ms
FRAME_DURATION_MS = 30

# 30ms @ 16khz = 480
VAD_FRAME_SIZE = 480

# frontend manda 512
INPUT_FRAME_SIZE = 512

# silencio antes de cortar
SILENCE_LIMIT = 30

# volumen mínimo
MIN_VOLUME = 1300

# chunks inteligentes
MIN_CHUNK_SECONDS = 0.5
IDEAL_CHUNK_SECONDS = 5
MAX_CHUNK_SECONDS = 15

# overlap
OVERLAP_SECONDS = 1

audio_buffer = []

silence_counter = 0
grabando = False


# ====================================================
# UTILIDADES AUDIO
# ====================================================

def volumen_audio(frame_np):

    return np.sqrt(
        np.mean(
            frame_np.astype(np.float32) ** 2
        )
    )


# ====================================================
# VAD PROCESSOR
# ====================================================

def procesar_audio(frame_np):

    global audio_buffer
    global silence_counter
    global grabando

    # =========================================
    # VALIDAR FRAME
    # =========================================

    if len(frame_np) < VAD_FRAME_SIZE:
        return None

    # usamos solo 480 para VAD
    vad_frame = frame_np[:VAD_FRAME_SIZE]

    # =========================================
    # VOLUMEN
    # =========================================

    volume = volumen_audio(frame_np)

    # =========================================
    # DETECCIÓN VOZ
    # =========================================

    try:

        is_speech = vad.is_speech(
            vad_frame.tobytes(),
            SAMPLE_RATE
        )

    except Exception as e:

        print("❌ ERROR VAD:", e)
        return None

    hay_voz = (
        is_speech
        and volume > MIN_VOLUME
    )

    print(
        f"voz={hay_voz} "
        f"speech={is_speech} "
        f"vol={int(volume)} "
        f"grabando={grabando}"
    )

    # =========================================
    # INICIO GRABACIÓN
    # =========================================

    if hay_voz and not grabando:

        print("🎙️ INICIO VOZ")

        grabando = True
        audio_buffer = []
        silence_counter = 0

    # =========================================
    # SI ESTÁ GRABANDO
    # =========================================

    if grabando:

        audio_buffer.append(frame_np)

        duracion = (
            len(audio_buffer)
            * INPUT_FRAME_SIZE
            / SAMPLE_RATE
        )

        # =====================================
        # SIGUE HABLANDO
        # =====================================

        if hay_voz:

            silence_counter = 0

        else:

            silence_counter += 1

        print(
            f"🎤 duración={duracion:.2f}s "
            f"silencio={silence_counter}"
        )

        # =====================================
        # CORTE POR SILENCIO
        # =====================================

        if (
            silence_counter >= SILENCE_LIMIT
            and duracion >= MIN_CHUNK_SECONDS
        ):

            print("✂️ FIN POR SILENCIO")

            chunk = np.concatenate(audio_buffer)

            audio_buffer = []
            silence_counter = 0
            grabando = False

            return chunk

        # =====================================
        # SUBDIVISIÓN INTELIGENTE
        # =====================================

        if duracion >= IDEAL_CHUNK_SECONDS:

            print("✂️ SUBDIVISIÓN")

            chunk = np.concatenate(audio_buffer)

            overlap_frames = int(
                OVERLAP_SECONDS
                * SAMPLE_RATE
                / INPUT_FRAME_SIZE
            )

            audio_buffer = (
                audio_buffer[-overlap_frames:]
            )

            silence_counter = 0

            return chunk

        # =====================================
        # CORTE FORZADO
        # =====================================

        if duracion >= MAX_CHUNK_SECONDS:

            print("✂️ CORTE FORZADO")

            chunk = np.concatenate(audio_buffer)

            audio_buffer = []
            silence_counter = 0
            grabando = False

            return chunk

    return None


# ====================================================
# BUSCAR EN DB
# ====================================================
def buscar_contexto(user_text):

    try:

        print("🔍 buscando contexto para:", user_text)

        mensaje = user_text.lower().strip()

        palabras_usuario = set(
            mensaje.split()
        )

        cur = conn.cursor()

        query = """
        SELECT error_text, solution, tags
        FROM error_solutions
        """

        cur.execute(query)

        rows = cur.fetchall()

        cur.close()

        if not rows:

            print("❌ NO HAY FILAS")

            return None

        mejor_score = 0
        mejor_resultado = None

        # =========================================
        # BUSCAR MEJOR MATCH
        # =========================================

        for error_text, solution, tags in rows:

            texto_db = f"""
            {error_text}
            {tags}
            """.lower()

            palabras_db = set(
                texto_db.split()
            )

            coincidencias = len(
                palabras_usuario &
                palabras_db
            )

            print(
                f"Comparando con: {error_text}"
            )

            print(
                f"score={coincidencias}"
            )

            if coincidencias > mejor_score:

                mejor_score = coincidencias

                mejor_resultado = {
                    "error": error_text,
                    "solution": solution,
                    "tags": tags
                }

        # =========================================
        # SIN MATCH
        # =========================================

        if not mejor_resultado:

            print("❌ SIN MATCH")

            return None

        print("✅ MEJOR MATCH:")
        print(mejor_resultado)

        return mejor_resultado

    except Exception as e:

        print("❌ ERROR DB:", e)

        return None

# ====================================================
# IA (OLLAMA)
# ====================================================

def ask_llm(user_text: str, history):

    contexto = buscar_contexto(user_text)

    # =========================================
    # SI HAY MATCH DB
    # =========================================

    if contexto:

        prompt = f"""
Usuario:
{user_text}

Problema detectado:
{contexto['error']}

Solución oficial:
{contexto['solution']}

IMPORTANTE:
- usa SOLO esa solución
- no mezcles información
- responde natural
"""

    else:

        prompt = f"""
Usuario:
{user_text}

Responde breve y natural.
"""

    # =========================================
    # HISTORIAL
    # =========================================

    messages = [

        {
            "role": "system",
            "content": """
Eres un asistente técnico.

Si existe una solución oficial:
- úsala exactamente
- no mezcles datos
"""
        }

    ]

    # historial conversación
    messages.extend(history)

    # mensaje actual
    messages.append({

        "role": "user",
        "content": prompt

    })

    # =========================================
    # REQUEST OLLAMA
    # =========================================

    response = requests.post(

        os.getenv(
            "OLLAMA_URL",
            "http://host.docker.internal:11435/api/chat"
        ),

        json={

            "model": "qwen2.5:latest",

            "messages": messages,

            "stream": False,

            "options": {
                "temperature": 0.4
            }
        },

        timeout=500
    )

    data = response.json()

    if "message" in data:
        return data["message"]["content"]

    if "response" in data:
        return data["response"]

    return "Error IA"

# ====================================================
# PIPELINE FINAL
# ====================================================

def pipeline_audio(frame_np, history):

    chunk = procesar_audio(frame_np)

    if chunk is not None:

        print("🎤 Chunk final detectado")

        duracion_audio = (
            len(chunk) / SAMPLE_RATE
        )

        if duracion_audio < 0.5:

            print("⚠️ chunk muy corto")

            return None

        texto = transcribir_audio(chunk)

        print("📝 Texto:", texto)

        if not texto.strip():

            return None

        respuesta = ask_llm(
            texto,
            history
        )

        print("🤖 Respuesta:", respuesta)

        return {

            "texto": texto,

            "respuesta": respuesta
        }

    return None