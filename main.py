from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

import numpy as np

from bot import pipeline_audio

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)

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

    print("✅ Cliente conectado")

    # =====================================
    # MEMORIA CONVERSACIÓN
    # =====================================

    conversation_history = []

    try:

        while True:

            # =====================================
            # RECIBIR AUDIO
            # =====================================

            data = await ws.receive_bytes()

            frame_np = np.frombuffer(
                data,
                dtype=np.int16
            )

            print(
                "📦 frame recibido:",
                len(frame_np)
            )

            # =====================================
            # PIPELINE
            # =====================================

            resultado = pipeline_audio(
                frame_np,
                conversation_history
            )

            # =====================================
            # SI HAY RESULTADO
            # =====================================

            if resultado:

                print(
                    "📝 texto:",
                    resultado["texto"]
                )

                print(
                    "🤖 respuesta:",
                    resultado["respuesta"]
                )

                # ==============================
                # GUARDAR MEMORIA
                # ==============================

                conversation_history.append({

                    "role": "user",

                    "content": resultado["texto"]

                })

                conversation_history.append({

                    "role": "assistant",

                    "content": resultado["respuesta"]

                })

                # limitar memoria
                if len(conversation_history) > 20:

                    conversation_history = (
                        conversation_history[-20:]
                    )

                # ==============================
                # TEXTO ESCUCHADO
                # ==============================

                await ws.send_json({

                    "type": "final",

                    "texto": resultado["texto"]
                })

                # ==============================
                # RESPUESTA IA
                # ==============================

                await ws.send_json({

                    "type": "ia",

                    "texto": resultado["respuesta"]
                })

    except Exception as e:

        print("❌ WS ERROR:", e)

    finally:

        print("🔌 Cliente desconectado")