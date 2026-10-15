# The desktop

Optional: the Anki desktop app in a browser tab ([KasmVNC](https://kasmweb.com/kasmvnc)), on the same Anki version as the rest of the stack. Useful for what only the desktop does: the card browser, editing note types and templates, add-ons, reviewing on a computer without Anki installed.

```bash
anki-stack desktop on      # builds the image (2–3 GB) and starts it
anki-stack desktop         # its address and login
anki-stack desktop off     # stops it; its data stays
```

It's at `DESKTOP_BIND` (`http://127.0.0.1:3000` by default), behind a login (`DESKTOP_USER` / `DESKTOP_PASSWORD`, generated). It isn't routed through the HTTPS options: reach it over Tailscale, an SSH tunnel, or a proxy of your own.

## Ready on first open

On start, before Anki opens, it:

1. creates the profile and skips the first-run language prompt,
2. points it at the stack's sync server and signs in with the stack's account,
3. on a fresh desktop, downloads the collection, so Anki opens with the cards there rather than asking,
4. turns AnkiConnect on or off (`DESKTOP_ANKICONNECT`).

Anki syncs when it opens and closes and when Sync is pressed; with AnkiConnect on, also every 10 minutes. Closing Anki's window starts it again.

## AnkiConnect in it

```bash
anki-stack desktop ankiconnect on
```

The real add-on (a pinned version) at `DESKTOP_ANKICONNECT_BIND` (`http://127.0.0.1:8766`), with the stack's AnkiConnect key. See [AnkiConnect](ankiconnect.md) for when that's needed over the worker's API.

It uses about 350 MB of memory while running.
