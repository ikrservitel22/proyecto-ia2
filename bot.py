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
# HISTORIAL CHAT
# ====================================================

chat_history = [
    {
        "role": "system",
        "content": """
Eres un asistente conversacional útil, breve y natural.

Usa SIEMPRE el contexto entregado desde la base de datos
para responder preguntas del usuario.

Si el contexto no contiene información suficiente,
responde normalmente.
"""
    }
]

# ====================================================
# TRANSCRIBIR
# ====================================================

def transcribir_audio(audio_np):

    audio_np = audio_np.flatten()

    audio_float = audio_np.astype(np.float32) / 32768.0

    segments, _ = whisper_model.transcribe(
        audio_float,
        language="es"
    )

    texto = " ".join([s.text for s in segments]).strip()

    return texto

# ====================================================
# BUSCAR CONTEXTO DB
# ====================================================

def buscar_contexto(user_text):

    try:

        print("🔍 buscando contexto para:", user_text)

        cur = conn.cursor()

        query = """
        SELECT error_text, solution, tags
        FROM error_solutions
        LIMIT 5
        """

        cur.execute(query)

        rows = cur.fetchall()

        print("📚 filas encontradas:", rows)

        cur.close()

        if not rows:
            print("❌ NO HAY FILAS")
            return "Sin contexto relevante."

        contexto = []

        for error_text, solution, tags in rows:

            contexto.append(
                f"""
Error: {error_text}

Solución: {solution}

Tags: {tags}
"""
            )

        contexto_final = "\n".join(contexto)

        print("✅ CONTEXTO FINAL:")
        print(contexto_final)

        return contexto_final

    except Exception as e:

        print("❌ ERROR DB:", e)

        return "Error obteniendo contexto."
# ====================================================
# IA
# ====================================================

def ask_llm(user_text: str):

    # buscar contexto en postgres
    contexto_db = buscar_contexto(user_text)

    print("========== CONTEXTO DB ==========")
    print(contexto_db)
    print("=================================")

    # prompt enriquecido
    prompt = f"""
CONTEXTO BASE DE DATOS:

{contexto_db}


PREGUNTA USUARIO:

{user_text}
"""

    chat_history.append({
        "role": "user",
        "content": prompt
    })

    print("📨 enviando a ollama...")

    response = requests.post(
        os.getenv(
            "OLLAMA_URL",
            "http://host.docker.internal:11435/api/chat"
        ),
        json={
            "model": os.getenv(
                "IA_MODEL",
                "qwen2.5:latest"
            ),
            "messages": chat_history,
            "stream": False
        },
        timeout=300
    )

    data = response.json()

    print("📦 respuesta ollama:", data)

    if "message" in data:

        respuesta = data["message"]["content"]

    elif "response" in data:

        respuesta = data["response"]

    elif "error" in data:

        raise Exception(data["error"])

    else:

        raise Exception(f"Respuesta inesperada: {data}")

    chat_history.append({
        "role": "assistant",
        "content": respuesta
    })

    return respuesta