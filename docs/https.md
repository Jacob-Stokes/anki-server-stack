# HTTPS

Phones need the sync server at an address they can reach, and over HTTPS unless they're on the same local network. Each option puts **the sync server at the domain's root** (what Anki apps are given) and **the MCP server at `/mcp`**. Choose one in the installer, or set `COMPOSE_PROFILES` in `.env`.

## A domain (Caddy)

`COMPOSE_PROFILES=caddy`, with `DOMAIN` (pointing at this server) and `ACME_EMAIL`. Caddy gets certificates from Let's Encrypt and needs ports 80 and 443. The sync server's uploads can be large; Caddy accepts up to 512 MB.

## Tailscale

`COMPOSE_PROFILES=tailscale`, with `TS_AUTHKEY` and `TS_HOSTNAME`. The stack joins the tailnet as its own machine, at `https://<name>.<tailnet>.ts.net`, reachable only from the tailnet. Phones need the Tailscale app.

## Cloudflare Tunnel

`COMPOSE_PROFILES=cloudflare`, with `CF_TUNNEL_TOKEN` and `DOMAIN`. No open ports. In Cloudflare, add two public hostname routes for the tunnel: `<domain>` → `http://anki-sync:8080`, and `<domain>/mcp` → `http://anki-mcp:8080`. Cloudflare limits uploads to 100 MB on free plans: a large collection's first upload may need to happen another way.

## A reverse proxy already here

Leave `COMPOSE_PROFILES` empty, set `PUBLIC_URL`, and point the proxy at `SYNC_BIND` (`127.0.0.1:8070`) for `/`, and at `MCP_BIND` (`127.0.0.1:7012`) for `/mcp`. Allow large request bodies on `/` (uploads of whole collections).

## The desktop and AnkiConnect

Neither is routed through these options: both are for this machine or a private network. Reach them over Tailscale, an SSH tunnel or a proxy of your own, and keep the desktop's login.
