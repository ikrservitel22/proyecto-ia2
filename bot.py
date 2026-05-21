from dotenv import load_dotenv
import os
import numpy as np
import requests
import psycopg2

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

    audio_float = audio_np.astype(np.float32) / 32768.0

    segments, _ = whisper_model.transcribe(
        audio_float,
        language="es"
    )

    texto = " ".join(
        [s.text for s in segments]
    ).strip()

    return texto

# ====================================================
# BUSCAR SOLUCION EN DB
# ====================================================

def buscar_contexto(user_text):

    try:

        print("🔍 buscando:", user_text)

        mensaje = user_text.lower().strip()

        cur = conn.cursor()

        # ============================================
        # TRAER TODAS LAS SOLUCIONES
        # ============================================

        query = """
        SELECT error_text, solution, tags
        FROM error_solutions
        """

        cur.execute(query)

        rows = cur.fetchall()

        cur.close()

        if not rows:

            print("❌ DB VACIA")

            return None

        # ============================================
        # BUSQUEDA SIMPLE POR PALABRAS
        # ============================================

        mejor_score = 0
        mejor_solucion = None

        palabras_usuario = set(
            mensaje.split()
        )

        for error_text, solution, tags in rows:

            texto_db = f"""
            {error_text}
            {tags}
            """.lower()

            palabras_db = set(
                texto_db.split()
            )

            coincidencias = (
                palabras_usuario &
                palabras_db
            )

            score = len(coincidencias)

            print("---------------")
            print("DB:", error_text)
            print("MATCH:", coincidencias)
            print("SCORE:", score)

            if score > mejor_score:

                mejor_score = score
                mejor_solucion = solution

        # ============================================
        # UMBRAL MINIMO
        # ============================================

        if mejor_score >= 1:

            print("✅ SOLUCION ENCONTRADA")
            print(mejor_solucion)

            return mejor_solucion

        print("❌ SIN MATCH")

        return None

    except Exception as e:

        print("❌ ERROR DB:", e)

        return None

# ====================================================
# IA / RESPUESTA
# ====================================================

def ask_llm(user_text: str):

    # ============================================
    # BUSCAR EN DB
    # ============================================

    solucion_db = buscar_contexto(user_text)

    # ============================================
    # SI ENCONTRO SOLUCION
    # ============================================

    if solucion_db:

        print("✅ SOLUCION DB:", solucion_db)

        prompt = f"""
El usuario dijo:

"{user_text}"

La siguiente información viene de la base de datos:

"{solucion_db}"

Responde al usuario:
- en español
- de forma natural
- breve
- amable
- usando la información dada como base
- puedes reformular la respuesta
- NO inventes pasos nuevos
"""

    else:

        print("🤖 SIN DB -> IA NORMAL")

        prompt = f"""
Usuario:

{user_text}

Responde en español de forma breve y natural.
"""

    # ============================================
    # REQUEST OLLAMA
    # ============================================

    response = requests.post(

        os.getenv(
            "OLLAMA_URL",
            "http://host.docker.internal:11435/api/chat"
        ),

        json={

            "model": "qwen2.5:latest",

            "messages": [

                {
                    "role": "system",
                    "content": """
Eres un asistente técnico.

REGLAS:
- Siempre responde en español.
- Nunca hables en otro idioma.
- Sé breve.
- No inventes soluciones.
"""
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            "stream": False,

            "options": {
                "temperature": 0.3
            }
        },

        timeout=300
    )

    data = response.json()

    print("📦 RESPUESTA IA:")
    print(data)

    if "message" in data:

        return data["message"]["content"]

    elif "response" in data:

        return data["response"]

    else:

        return "Ocurrió un error generando la respuesta."