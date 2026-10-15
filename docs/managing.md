# Managing with anki-stack

`anki-stack` acts on the install it belongs to (or `--dir PATH`). `anki-stack help` lists everything.

## Day to day

| Command | |
|---|---|
| `anki-stack status` | Containers, the sync server's address, the worker's collection (notes, last sync, any error), the MCP server |
| `anki-stack logs [sync\|worker\|mcp\|desktop] [-f]` | Recent logs |
| `anki-stack restart [service]` | Restart one service, or everything |
| `anki-stack endpoint [--show-token]` | The MCP endpoint and token; the AnkiConnect addresses and key |
| `anki-stack sync` | Sync the worker now |
| `anki-stack sync --download` / `--upload` | Replace the worker's copy with the server's, or the server's with the worker's (asks first) |

## Accounts

The stack's own account (`ANKI_USER`) is the one the worker and the desktop use. More people can sync their own collections with the same server:

| Command | |
|---|---|
| `anki-stack users` | List the accounts |
| `anki-stack users add NAME` | A new account (asks for a password, or generates one) |
| `anki-stack users passwd NAME` | A new password. For the stack's own account, the worker and desktop are restarted with it and sign in again. Devices sign in again too. |
| `anki-stack users remove NAME` | Remove an account; its collection stays in `data/sync/NAME` |

## The desktop

`anki-stack desktop on|off`, `anki-stack desktop ankiconnect on|off`, `anki-stack desktop` for its address and login. See [The desktop](desktop.md).

## Backups

```bash
anki-stack backup                 # backups/anki-<date>.tar.gz
anki-stack restore backups/anki-<date>.tar.gz
```

A backup is the sync server's collections (every account's cards and media), `.env` and `users.env`. It syncs the worker's last changes first, and pauses the sync server for the moment it takes to copy them, so they're copied whole. It holds the passwords and keys: keep it safe.

A restore replaces the collections and accounts with the backup's, keeps the previous ones beside them (`data/*.before-restore-<date>`), and lets the worker download the restored collection. Devices then sync against it; some may be asked to download.

## Updates

```bash
anki-stack update
```

`git pull`, then the images are rebuilt on the new pinned versions and the stack restarted. Anki versions are pinned in `compose.yml` and the Dockerfiles, and kept current (all together) by Renovate pull requests, each tested end to end.

## Removing

`anki-stack uninstall` stops and removes the containers and the `anki-stack` command; the data stays unless asked (`delete` at the prompt).
