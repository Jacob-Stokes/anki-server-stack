# Docker Compose

The installer only writes `.env`; `compose.yml` is the whole stack. To set it up by hand:

```bash
cp .env.example .env && chmod 600 .env
# fill in, at least:
#   ANKI_USER, ANKI_PASSWORD        the sync account
#   ANKICONNECT_KEY                 openssl rand -hex 32
#   MCP_BEARER_TOKEN                openssl rand -hex 32
mkdir -p data/sync data/worker && sudo chown 1000:1000 data/sync data/worker
docker compose up -d --build
```

The first start builds one image (Anki, pinned, for the sync server, the worker and the MCP server). The worker then signs in to the sync server and syncs.

## Settings

All in `.env`, explained in `.env.example`. The ones most often changed:

| Setting | Default | |
|---|---|---|
| `SYNC_BIND` | `127.0.0.1:8070` | The sync server, on this machine |
| `MCP_BIND` | `127.0.0.1:7012` | The MCP server |
| `ANKICONNECT_BIND` | `127.0.0.1:8765` | The worker's AnkiConnect API |
| `ANKICONNECT_CORS` | empty | Browser origins allowed to call it |
| `COMPOSE_PROFILES` | empty | `caddy`, `tailscale` or `cloudflare`, and/or `desktop` |
| `SYNC_INTERVAL` | `5` | Minutes between the worker's routine syncs |
| `MAX_SYNC_PAYLOAD_MEGS` | `250` | Largest upload the sync server accepts |
| `INSTANCE_PREFIX` | empty | A prefix for a second copy on the same machine |

More sync accounts go in `users.env` as `SYNC_USER2=name:password`, `SYNC_USER3=…` (or `anki-stack users add`).

## Without the CLI

Everything the CLI does is Compose underneath: `docker compose ps`, `logs`, `up -d`, `down`. `anki-stack` adds the questions, the checks and backups.
