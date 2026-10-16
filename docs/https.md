# HTTPS

Phones need the sync server at an address they can reach, and over HTTPS unless they're on the same local network. Each option puts **the sync server at the domain's root** (what Anki apps are given) and **the MCP server at `/mcp`**. Choose one in the installer, or later with `anki-stack address`.

The installer first checks what this machine already has: something listening on ports 80/443, Tailscale, cloudflared. Options 1–4 add a container to the stack; 5–7 use what's already there, with no extra container, and the installer suggests the one that fits.

| | Option | Runs |
|---|---|---|
| 1 | This machine only | nothing extra |
| 2 | A domain with HTTPS | the stack's own Caddy (needs ports 80/443 free) |
| 3 | Tailscale, as its own machine | the stack's own Tailscale container |
| 4 | A Cloudflare Tunnel | the stack's own cloudflared |
| 5 | This machine's Tailscale | `tailscale serve`, or listening on the Tailscale address |
| 6 | This machine's Cloudflare Tunnel | nothing: two routes to add, shown |
| 7 | This machine's reverse proxy | nothing: a config snippet for it, shown |

## A domain (Caddy)

`COMPOSE_PROFILES=caddy`, with `DOMAIN` (pointing at this server) and `ACME_EMAIL`. Caddy gets certificates from Let's Encrypt and needs ports 80 and 443. The sync server's uploads can be large; Caddy accepts up to 512 MB.

## Tailscale

`COMPOSE_PROFILES=tailscale`, with `TS_AUTHKEY` and `TS_HOSTNAME`. The stack joins the tailnet as its own machine, at `https://<name>.<tailnet>.ts.net`, reachable only from the tailnet. Phones need the Tailscale app.

## Cloudflare Tunnel

`COMPOSE_PROFILES=cloudflare`, with `CF_TUNNEL_TOKEN` and `DOMAIN`. No open ports. In Cloudflare, add two public hostname routes for the tunnel: `<domain>` → `http://anki-sync:8080`, and `<domain>/mcp` → `http://anki-mcp:8080`. Cloudflare limits uploads to 100 MB on free plans: a large collection's first upload may need to happen another way.

## This machine's Tailscale

For a machine already on a tailnet. With `tailscale serve` (the default), the stack stays on `127.0.0.1` and Tailscale serves it with a certificate at `https://<machine>.<tailnet>.ts.net`, on port 443 or, if something else is served there, the next free port from 10443. Without it, the stack listens on the machine's Tailscale address (plain HTTP inside the tailnet, which WireGuard already encrypts). Either way it can also put the desktop and AnkiConnect on the Tailscale address. `anki-stack uninstall` (or choosing another address) removes the serve routes it added.

## This machine's Cloudflare Tunnel

For a machine already running cloudflared: no second tunnel. The installer shows the two routes to add (the hostname to the sync server, `/mcp` to the MCP server) and saves them in `data/proxy-example.txt`.

## A reverse proxy already here

The installer recognises what's on ports 80/443 and writes a matching snippet (Caddy, nginx, or generic) to `data/proxy-example.txt`. By hand: leave `COMPOSE_PROFILES` empty, set `PUBLIC_URL`, and point the proxy at `SYNC_BIND` (`127.0.0.1:8070`) for `/`, and at `MCP_BIND` (`127.0.0.1:7012`) for `/mcp`. Allow large request bodies on `/` (uploads of whole collections).

## The desktop and AnkiConnect

Neither is routed through these options: both are for this machine or a private network. Reach them over Tailscale, an SSH tunnel or a proxy of your own, and keep the desktop's login.
