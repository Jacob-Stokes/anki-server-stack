# One image, three roles (see compose.yml): Anki's own sync server, the
# worker (a headless collection behind an AnkiConnect-style API) and the MCP
# server. All on the same Anki version, which the sync protocol likes.
FROM python:3.12-slim

ARG ANKI_VERSION=26.9.3
ARG MCP_VERSION=2.3.0

RUN pip install --no-cache-dir "anki==${ANKI_VERSION}" "mcp==${MCP_VERSION}" "uvicorn==0.38.0" \
 && useradd --uid 1000 --create-home anki \
 && mkdir -p /data && chown anki:anki /data

COPY app /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER anki

# the sync server, by default; the worker and MCP set their own command
ENV SYNC_BASE=/data SYNC_HOST=0.0.0.0 SYNC_PORT=8080
CMD ["python", "-m", "anki.syncserver"]
