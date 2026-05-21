#!/bin/bash
set -e

mkdir -p /var/run/sshd

/usr/sbin/sshd

echo "SSH iniciado"

ollama serve &

until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama listo"

ollama pull qwen2.5:latest

echo "Modelo listo"

cd /app

exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8002