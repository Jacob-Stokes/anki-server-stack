<p align="center">
  <img src="assets/logo.svg" alt="Anki Server Stack logo" width="90">
</p>

<h1 align="center">Anki Server Stack</h1>

<p align="center">A self-hosted <a href="https://apps.ankiweb.net">Anki</a> sync server, a headless Anki collection with an AnkiConnect-style API, and an MCP server, in one Docker Compose project.</p>

<p align="center">
  <a href="https://github.com/Jacob-Stokes/anki-server-stack/actions/workflows/e2e.yml"><img src="https://github.com/Jacob-Stokes/anki-server-stack/actions/workflows/e2e.yml/badge.svg" alt="e2e"></a>
  <a href="https://jacob-stokes.github.io/anki-server-stack/"><img src="https://img.shields.io/badge/docs-online-009688" alt="Documentation"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Jacob-Stokes/anki-server-stack" alt="MIT license"></a>
</p>

[Anki](https://apps.ankiweb.net) is a flashcard app with spaced repetition. Its phones and desktops sync through AnkiWeb, or through a sync server of your own. This stack runs that sync server, plus what an AI client needs to work with the cards: a copy of the collection that's always open, and an MCP server on top of it. No desktop app has to be running for any of it.

## Features

**Anki's own sync server.** AnkiDroid, AnkiMobile and Anki desktop sync with it as they would with AnkiWeb. More accounts with `anki-stack users add`.

**No desktop needed.** Tools that drive Anki usually go through AnkiConnect, an add-on that only runs inside the desktop app. Here a small service (the worker) holds its own copy of the collection, syncs it like any other device, and answers AnkiConnect's API for decks, notes, cards, tags and media.

**3 MCP tools.** Notes (add, bulk add, find, read, update, delete), decks and note types, and sync. Deleting needs confirming; a duplicate is refused with the reason.

**Safe when devices disagree.** When a change can't be merged and one side's copy has to replace the other, the server's copy wins and the worker applies its own unsynced changes again on top. It never uploads an empty collection over a server that has one.

**Desktop optional.** Full Anki in a browser tab, already signed in and holding the collection, for the card browser, add-ons and editing note types, with the real AnkiConnect add-on if needed. Off unless chosen.

**Plain Docker Compose.** `compose.yml` is the whole stack; the installer only writes `.env`. Everything it keeps is in the install folder, nothing in Docker volumes.

**HTTPS built in.** Optional Caddy, Tailscale or Cloudflare Tunnel, with the sync server at the domain's root and the MCP server at `/mcp`.

**Backups and updates.** `anki-stack backup` and `restore`, `update`, `status`, accounts and passwords, the desktop on and off.

**Tested end to end.** CI installs the stack, runs every MCP tool, syncs with a second device (including a full sync it forces mid-change), exercises the CLI and the desktop, on every change.

## Install

Two ways, giving the same compose project. Requires Linux with Docker and Compose 2.24 or newer.

**Installer**: asks for the sync account, the address and whether to add the desktop, then starts everything.

```bash
git clone https://github.com/Jacob-Stokes/anki-server-stack.git
cd anki-server-stack
./install.sh
```

**Docker Compose**: copy `.env.example` to `.env`, fill in the account and the secrets, then `docker compose up -d`. See [Docker Compose](https://jacob-stokes.github.io/anki-server-stack/compose/).

Then point phones and desktops at the sync server (`anki-stack status` shows its address). The MCP endpoint is `http://127.0.0.1:7012/mcp`; `anki-stack endpoint --show-token` prints its bearer token.

## Documentation

**[jacob-stokes.github.io/anki-server-stack](https://jacob-stokes.github.io/anki-server-stack/)**

- [Installer](https://jacob-stokes.github.io/anki-server-stack/installer/) and [Docker Compose](https://jacob-stokes.github.io/anki-server-stack/compose/)
- [Phones and desktops](https://jacob-stokes.github.io/anki-server-stack/devices/): pointing Anki at the sync server
- [How it works](https://jacob-stokes.github.io/anki-server-stack/how-it-works/): the services, syncing, where data lives
- [Connecting AI tools](https://jacob-stokes.github.io/anki-server-stack/mcp/) and [AnkiConnect](https://jacob-stokes.github.io/anki-server-stack/ankiconnect/)
- [The desktop](https://jacob-stokes.github.io/anki-server-stack/desktop/)
- [HTTPS](https://jacob-stokes.github.io/anki-server-stack/https/): Caddy, Tailscale, Cloudflare Tunnel, an existing proxy
- [Managing with anki-stack](https://jacob-stokes.github.io/anki-server-stack/managing/): status, accounts, backups, updates

## License

MIT, for this repository. Anki (AGPL-3.0), AnkiConnect (GPL-3.0) and the other software are used as published, unmodified; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
