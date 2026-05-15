FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    requests \
    faster-whisper \
    sqlalchemy

RUN apt-get update && apt-get install -y openssh-server sudo
RUN mkdir /var/run/sshd

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]