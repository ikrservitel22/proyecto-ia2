#!/bin/bash
set -e

echo "Iniciando contenedor proyecto-ia..."

# ─────────────────────────────
# SSH SERVER
# ─────────────────────────────
mkdir -p /var/run/sshd

/usr/sbin/sshd

echo "SSH iniciado en puerto 22"

# ─────────────────────────────
# OLLAMA
# ─────────────────────────────
ollama serve &

echo "Esperando Ollama..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama listo"

# ─────────────────────────────
# MODELO
# ─────────────────────────────
ollama pull phi3:mini

# ─────────────────────────────
# FASTAPI
# ─────────────────────────────
cd /app/ia

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --reload