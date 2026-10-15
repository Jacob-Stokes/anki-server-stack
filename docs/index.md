# Anki Server Stack

A self-hosted [Anki](https://apps.ankiweb.net) sync server, a headless Anki collection with an AnkiConnect-style API, and an MCP server, in one Docker Compose project.

Anki's phones and desktops sync through AnkiWeb, or through a sync server of your own. This stack runs that server, plus what an AI client needs to work with the cards: a copy of the collection that's always open (the **worker**), and an **MCP server** on top of it. No desktop app has to be running.

```text
  phones, desktops ──sync──▶  anki-sync  ◀──sync──  anki-worker  ◀──AnkiConnect API──  anki-mcp  ◀── AI clients
                                  ▲                                                    (/mcp)
                                  └──sync──  anki-desktop (optional: Anki in a browser, real AnkiConnect)
```

## What's in it

| Service | |
|---|---|
| `anki-sync` | Anki's own sync server. Phones and desktops sync with it as with AnkiWeb. |
| `anki-worker` | A copy of the collection, synced like any other device, behind AnkiConnect's API (decks, notes, cards, tags, media). |
| `anki-mcp` | MCP server: notes, decks and note types, sync. Bearer token. |
| `anki-desktop` | Optional. Full Anki in a browser tab, signed in and holding the collection; the real AnkiConnect add-on if wanted. |
| `caddy` / `tailscale` / `cloudflared` | Optional HTTPS: the sync server at the domain's root, the MCP server at `/mcp`. |

## Start

```bash
git clone https://github.com/Jacob-Stokes/anki-server-stack.git
cd anki-server-stack
./install.sh
```

Then [point phones and desktops at the sync server](devices.md) and [connect an AI client](mcp.md).
