FROM python:3.12-slim

WORKDIR /app

# system deps for chromadb native extensions (onnxruntime needs gcc)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt warmup.py ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-warm the sentence-transformer embedding model used by ChromaDB
# (~80MB model baked into image — avoids cold-start network call in cluster)
RUN python warmup.py

COPY server.py .

ENV MEMPALACE_PALACE_PATH=/palace
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "server.py"]
