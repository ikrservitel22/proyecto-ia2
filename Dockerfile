FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

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

RUN mkdir -p /var/run/sshd

RUN useradd -ms /bin/bash devuser && \
    echo "devuser:1234" | chpasswd && \
    usermod -aG sudo devuser && \
    echo "devuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# 👇 IMPORTANTE: primero copiar requirements
WORKDIR /app

COPY requirements.txt /app/

RUN pip3 install --no-cache-dir -r requirements.txt

# OLLAMA
RUN curl -fsSL https://ollama.com/install.sh | sh

# APP
COPY . /app

RUN chmod +x /app/start.sh

EXPOSE 22 8002 11434

CMD ["/app/start.sh"]