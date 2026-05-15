FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ─────────────────────────────
# PAQUETES
# ─────────────────────────────
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    zstd \
    sudo \
    git \
    openssh-server \
    openssh-client \
    && apt-get clean

# ─────────────────────────────
# SSH
# ─────────────────────────────
RUN mkdir -p /var/run/sshd

RUN useradd -ms /bin/bash devuser && \
    echo "devuser:1234" | chpasswd && \
    usermod -aG sudo devuser && \
    echo "devuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# ─────────────────────────────
# OLLAMA
# ─────────────────────────────
RUN curl -fsSL https://ollama.com/install.sh | sh

# ─────────────────────────────
# PYTHON
# ─────────────────────────────
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    faster-whisper \
    python-multipart

# ─────────────────────────────
# APP
# ─────────────────────────────
WORKDIR /app

COPY . /app

RUN chmod +x /app/start.sh

# ─────────────────────────────
# PUERTOS
# ─────────────────────────────
EXPOSE 22 8002 11434

# ─────────────────────────────
# START
# ─────────────────────────────
CMD ["/app/start.sh"]