# How it works

One Docker Compose project, named `anki` (or `<prefix>anki`), with everything it keeps in the install folder.

## Services

- **`anki-sync`** is Anki's own sync server (`python -m anki.syncserver`), from the pinned `anki` release. It keeps each account's collection and media in `data/sync/<account>`.
- **`anki-worker`** holds its own copy of the stack account's collection in `data/worker`, syncs it with `anki-sync` like any other device, and answers [AnkiConnect's API](ankiconnect.md) on port 8765. It's a few hundred lines of Python on Anki's library: no desktop, no Qt, no screen.
- **`anki-mcp`** is the [MCP server](mcp.md). It talks AnkiConnect to the worker (or to the desktop's add-on, if pointed there).
- **`anki-desktop`** (profile `desktop`) is [the desktop app in a browser](desktop.md).
- **`caddy`**, **`tailscale`** or **`cloudflared`** start only with their [profile](https.md).

The sync server, the worker and the MCP server are one image, on one Anki version; the desktop is built for the same version. Anki's sync protocol is happiest when versions match, and Renovate moves them together.

## How the worker syncs

It syncs when it starts, a few seconds after every change made through its API (changes in a burst go together), before answering if it hasn't synced for a minute, and every `SYNC_INTERVAL` minutes (5 by default). When it stops, it syncs any unsynced change first.

Usually a sync merges both sides' changes. Some changes can't be merged (a note type edited on two devices, a device choosing "upload" when asked), and then one side's whole collection replaces the other's. The worker decides like this:

| The server says | The worker |
|---|---|
| The worker's copy is new | Downloads the server's collection |
| The server is empty | Uploads its own, but only if it has notes: an empty collection is never uploaded |
| Both changed, can't merge | Downloads: the server's copy wins |

Changes made through the API since the last sync are journalled. After a download that replaced its copy, the worker applies them again on top and syncs, so a change the API confirmed isn't silently lost. A note it added comes back with a new id; a change that no longer applies (an edit to a note deleted elsewhere) is logged and dropped. `anki-stack sync --download` or `--upload` forces either direction.

## Data

Everything is in the install folder, nothing in Docker volumes:

| Path | |
|---|---|
| `.env` | Settings and secrets |
| `users.env` | More sync accounts, if any |
| `data/sync` | **The collections**: the sync server's copy of every account's cards and media |
| `data/worker` | The worker's copy (downloaded again if lost) and its saved login |
| `data/desktop` | The desktop's profile (downloaded again if lost) |
| `data/caddy`, `data/tailscale` | HTTPS state, when used |
| `backups/` | [Backups](managing.md#backups) |

`data/sync` and `.env` are the install; everything else can be rebuilt from them. Moving to another server is copying the folder (with the stack stopped), or a backup and a restore.
