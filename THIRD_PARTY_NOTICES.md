# Third-party notices

This repository's own files (the compose file, configuration, the Python in `app/`, the desktop's start-up scripts and `anki-stack`) are MIT-licensed. The images the stack builds install this software, unmodified, from its usual sources; none is copied into this repository:

| Software | Where from | License |
|---|---|---|
| [Anki](https://github.com/ankitects/anki) (the `anki` library and its sync server; `aqt`, the desktop app) | PyPI, pinned version | AGPL-3.0-or-later |
| [AnkiConnect](https://github.com/FooSoft/anki-connect) (desktop, optional) | GitHub, pinned commit | GPL-3.0 |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [Uvicorn](https://www.uvicorn.org) | PyPI | MIT, BSD-3-Clause |
| [Python](https://www.python.org) | `python:3.12-slim` | PSF-2.0 |
| [linuxserver.io KasmVNC base](https://github.com/linuxserver/docker-baseimage-kasmvnc) (desktop, optional) | `lscr.io/linuxserver/baseimage-kasmvnc` | GPL-3.0 |
| [Caddy](https://caddyserver.com) (optional) | `caddy:2.10` | Apache-2.0 |
| [Tailscale](https://tailscale.com) (optional) | `tailscale/tailscale` | BSD-3-Clause |
| [cloudflared](https://github.com/cloudflare/cloudflared) (optional) | `cloudflare/cloudflared` | Apache-2.0 |

Anki's AGPL-3.0 applies to Anki itself, including its sync server: anyone offering a modified Anki over a network must offer its source. This stack doesn't modify it. The worker in `app/` uses Anki's library as a program would; an image built from this repository contains Anki and so is distributed under Anki's terms.

"Anki" is a trademark of its owner. This project is not affiliated with or endorsed by Ankitects.
