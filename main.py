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


def call_ollama(prompt):

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    return r.json()["response"]


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.post("/audio")
async def audio(file: UploadFile = File(...)):

    path = f"/tmp/{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    texto = transcribir(path)

    errores = buscar_error(texto)

    prompt = f"""
Eres un ingeniero experto en sistemas.

TRANSCRIPCIÓN:
{texto}

ERRORES:
{errores}

Dame:
- diagnóstico
- causa
- solución
"""

    respuesta = call_ollama(prompt)

    os.remove(path)

    return {
        "texto": texto,
        "respuesta": respuesta
    }


# =========================
# WEBSOCKET
# =========================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    print("cliente conectado")

    try:

        while True:

            audio_bytes = await ws.receive_bytes()

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".webm"
            ) as temp:

                temp.write(audio_bytes)
                webm_path = temp.name

            try:

                texto = transcribir(webm_path)

                if texto.strip():

                    print("TEXTO:", texto)

                    await ws.send_json({
                        "texto": texto
                    })

            except Exception as e:

                print("ERROR TRANSCRIPCION:", str(e))

                await ws.send_json({
                    "error": str(e)
                })

            finally:

                if os.path.exists(webm_path):
                    os.remove(webm_path)

    except Exception as e:

        print("WS DESCONECTADO:", str(e))