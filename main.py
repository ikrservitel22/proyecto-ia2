from fastapi import FastAPI, WebSocket
import asyncio
import numpy as np
from collections import deque

from audio import transcribir_array

app = FastAPI()

print("REALTIME SERVER OK")

# ====================================================
# CONFIG
# ====================================================

SAMPLE_RATE = 16000

MAX_SECONDS = 16
TRANSCRIBE_SECONDS = 1.5
STEP_SECONDS = 0.6

MAX_SAMPLES = SAMPLE_RATE * MAX_SECONDS
TRANSCRIBE_SAMPLES = int(SAMPLE_RATE * TRANSCRIBE_SECONDS)

MIN_VOLUME = 20

# ====================================================
# UTIL
# ====================================================

def merge_text(old, new):
    old_words = old.split()
    new_words = new.split()

    best_overlap = 0
    max_check = min(len(old_words), len(new_words))

    for i in range(1, max_check + 1):
        if old_words[-i:] == new_words[:i]:
            best_overlap = i

    return " ".join(old_words + new_words[best_overlap:])


# ====================================================
# WEBSOCKET
# ====================================================

@app.websocket("/ws/realtime")
async def ws_realtime(ws: WebSocket):

    await ws.accept()
    print("cliente conectado")

    pending_audio = deque(maxlen=MAX_SAMPLES)

    full_text = ""

    # 🔥 PUNTERO CLAVE (EVITA REPETICIÓN)
    last_processed_index = 0

    async def receive_audio():
        while True:
            data = await ws.receive_bytes()

            audio_np = np.frombuffer(data, dtype=np.int16)
            pending_audio.extend(audio_np)

    async def transcribe_loop():
        nonlocal full_text, last_processed_index

        while True:
            await asyncio.sleep(STEP_SECONDS)

            audio_list = list(pending_audio)

            # 🔥 SOLO AUDIO NUEVO (NO REPROCESAR PASADO)
            new_audio = audio_list[last_processed_index:]

            if len(new_audio) < TRANSCRIBE_SAMPLES * 1.2:
                continue

            # ventana actual SOLO del audio nuevo
            window = new_audio[-TRANSCRIBE_SAMPLES:]

            current_audio = np.array(window, dtype=np.int16)

            volume = np.abs(current_audio).mean()

            MIN_VOLUME = 40

            if volume < MIN_VOLUME:
                silence_counter += 1
                if silence_counter < SILENCE_FRAMES:
                    continue
            else:
                silence_counter = 0

            audio_float = current_audio.astype(np.float32) / 32768.0

            try:
                # ⚡ IMPORTANTE: sin contexto viejo
                text = await asyncio.to_thread(
                    transcribir_array,
                    audio_float,
                    None
                )

                text = text.strip()
                if not text:
                    continue

                # ==============================
                # 🟢 LIVE TEXT (opcional simple)
                # ==============================
                await ws.send_json({
                    "type": "partial",
                    "texto": text
                })

                # ==============================
                # ⚡ FINAL TEXT (estable)
                # ==============================
                merged = merge_text(full_text, text)

                if merged != full_text:
                    new_part = merged[len(full_text):].strip()
                    full_text = merged

                    if new_part:
                        await ws.send_json({
                            "type": "final",
                            "texto": new_part
                        })

                # 🔥 AVANZAR PUNTERO (CLAVE DEL SISTEMA)
                last_processed_index += len(window)

            except Exception as e:
                print("ERROR:", e)
                await ws.send_json({"error": str(e)})

    await asyncio.gather(
        receive_audio(),
        transcribe_loop()
    )