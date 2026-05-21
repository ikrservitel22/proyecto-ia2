from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

import numpy as np
from collections import deque

from bot import transcribir_audio, ask_llm

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# =========================
# CONFIG AUDIO STREAM
# =========================

SAMPLE_RATE = 16000
WINDOW_SECONDS = 5
OVERLAP_SECONDS = 1

WINDOW_SIZE = SAMPLE_RATE * WINDOW_SECONDS
OVERLAP_SIZE = SAMPLE_RATE * OVERLAP_SECONDS

# =========================
# HOME
# =========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

# =========================
# REALTIME WS
# =========================

@app.websocket("/ws/realtime")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()
    print("Cliente conectado")

    audio_buffer = np.array([], dtype=np.int16)

    try:

        while True:

            data = await ws.receive_bytes()

            print("📦 chunk recibido:", len(data))

            chunk = np.frombuffer(data, dtype=np.int16)

            # buffer continuo (NO lista)
            audio_buffer = np.concatenate([audio_buffer, chunk])

            print("🎤 samples acumulados:", len(audio_buffer))

            # suficiente audio para procesar
            if len(audio_buffer) >= WINDOW_SIZE:

                window_audio = audio_buffer[:WINDOW_SIZE]

                print("🧠 transcribiendo...")

                texto = transcribir_audio(window_audio)

                print("📝 texto:", texto)

                # ❌ FIX: si no hay texto, reset parcial
                if not texto:
                    audio_buffer = audio_buffer[WINDOW_SIZE - OVERLAP_SIZE:]
                    continue

                await ws.send_json({
                    "type": "final",
                    "texto": texto
                })

                try:

                    print("🤖 preguntando IA...")

                    respuesta = ask_llm(texto)

                    print("✅ respuesta:", respuesta)

                    await ws.send_json({
                        "type": "ia",
                        "texto": respuesta
                    })

                except Exception as e:

                    print("❌ ERROR IA:", e)

                    await ws.send_json({
                        "type": "error",
                        "texto": str(e)
                    })

                # 🔥 SLIDING WINDOW (NO RESET BRUSCO)
                audio_buffer = audio_buffer[WINDOW_SIZE - OVERLAP_SIZE:]

    except Exception as e:

        print("WS ERROR:", e)
        await ws.close()