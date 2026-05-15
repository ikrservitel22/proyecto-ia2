from fastapi import FastAPI, UploadFile, File
import os
import requests

from db import init_db, buscar_error
from audio import transcribir

app = FastAPI()

OLLAMA_URL = "http://proyecto-ia:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"

init_db()


def call_ollama(prompt):
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })

    return r.json()["response"]


@app.post("/audio")
async def audio(file: UploadFile = File(...)):

    path = f"/tmp/{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    # 1. transcribir
    texto = transcribir(path)

    # 2. detectar posible error
    errores = buscar_error(texto)

    # 3. construir prompt inteligente
    prompt = f"""
Eres un ingeniero experto en sistemas.

TRANSCRIPCIÓN DEL USUARIO:
{texto}

ERRORES EN BASE DE DATOS:
{errores}

Dame:
- diagnóstico probable
- causa
- solución paso a paso
- comandos si aplica
"""

    # 4. IA responde
    respuesta = call_ollama(prompt)

    return {
        "texto": texto,
        "errores_db": errores,
        "respuesta": respuesta
    }