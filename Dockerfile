# MCP Faz 1 — geliştirme / bağımlılık doğrulama imajı (pod imajlarından bağımsız)
FROM python:3.12-slim

WORKDIR /work

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Faz 1: konteyner ayakta kalır; geliştirici exec ile script / Inspector çalıştırır
CMD ["sleep", "infinity"]
