# Margin API. Runs on Hugging Face Spaces (Docker SDK, port 7860) or any container host.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/app/.cache \
    FASTEMBED_CACHE_PATH=/home/app/.cache/fastembed \
    DATA_DIR=/home/app/data \
    PORT=7860

# Spaces run containers as uid 1000.
RUN useradd --create-home --uid 1000 app
WORKDIR /home/app/api

COPY requirements.txt .
RUN pip install -r requirements.txt

# Download the embedding model at build time so the first request isn't slow.
USER app
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY --chown=app:app app ./app
RUN mkdir -p /home/app/data

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/api/health')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
