# Image of the application for a server or for Google Cloud Run.
# If data/cache/radar.db exists at build time, the image contains it. Otherwise the database is empty.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .
RUN uv pip sync --system --no-cache requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Cloud Run gives the port in $PORT.
CMD ["sh", "-c", "exec uvicorn src.app:app --host 0.0.0.0 --port ${PORT}"]
