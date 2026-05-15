from fastapi import FastAPI, UploadFile, File, WebSocket
import requests
import tempfile
import os

from db import init_db, buscar_error
from audio import transcribir

app = FastAPI()

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "phi3:mini"

init_db()


# ─────────────────────────────
# OLLAMA
# ─────────────────────────────

def call_ollama(prompt):

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )

    return r.json()["response"]


# ─────────────────────────────
# HEALTH
# ─────────────────────────────

@app.get("/ping")
def ping():
    return {"status": "ok"}


# ─────────────────────────────
# AUDIO NORMAL
# ─────────────────────────────

@app.post("/audio")
async def audio(file: UploadFile = File(...)):

    path = f"/tmp/{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    # TRANSCRIBIR
    texto = transcribir(path)

    # BUSCAR ERRORES
    errores = buscar_error(texto)

    # PROMPT
    prompt = f"""
Eres un ingeniero experto en sistemas.

TRANSCRIPCIÓN:
{texto}

ERRORES DETECTADOS:
{errores}

Responde:
- diagnóstico probable
- causa
- solución paso a paso
- comandos Linux si aplica
"""

    # IA
    respuesta = call_ollama(prompt)

    # BORRAR TEMP
    os.remove(path)

    return {
        "texto": texto,
        "errores_db": errores,
        "respuesta": respuesta
    }


# ─────────────────────────────
# WEBSOCKET REALTIME
# ─────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    while True:

        try:

            audio_bytes = await ws.receive_bytes()

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".wav"
            ) as tmp:

                tmp.write(audio_bytes)

                tmp_path = tmp.name

            # TRANSCRIBIR
            texto = transcribir(tmp_path)

            # DB
            errores = buscar_error(texto)

            # PROMPT IA
            prompt = f"""
Eres un ingeniero experto en soporte TI.

USUARIO:
{texto}

ERRORES ENCONTRADOS:
{errores}

Responde corto y útil.
"""

            respuesta = call_ollama(prompt)

            # RESPUESTA
            await ws.send_json({
                "texto": texto,
                "errores": errores,
                "respuesta": respuesta
            })

            os.remove(tmp_path)

        except Exception as e:

            await ws.send_json({
                "error": str(e)
            })