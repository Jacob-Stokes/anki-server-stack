# Connecting AI tools

The MCP server speaks Streamable HTTP at `/mcp`, with a bearer token:

```bash
anki-stack endpoint --show-token
```

| | |
|---|---|
| On this machine | `http://127.0.0.1:7012/mcp` |
| With [HTTPS](https.md) | `https://<domain>/mcp` |
| Header | `Authorization: Bearer <MCP_BEARER_TOKEN>` |

## Tools

| Tool | Actions |
|---|---|
| `anki_notes` | `add` (a missing deck is created), `bulk_add` (up to 50), `find` (Anki's [search syntax](https://docs.ankiweb.net/searching.html)), `get_info`, `update` (fields and tags), `bulk_update` (up to 50), `delete` (needs `confirm: true`) |
| `anki_metadata` | `list_decks`, `create_deck`, `list_models` (note types), `model_fields`, `list_tags` |
| `anki_sync` | Sync now (it also happens on its own after every change) |

A duplicate (same first field, same note type, same deck) is refused with the reason, unless `allow_duplicate` is set. Errors from Anki come back as the tool's error message.

## Clients

**Claude Code**:

```bash
claude mcp add --transport http anki https://<domain>/mcp --header "Authorization: Bearer <token>"
```

**Other clients** (Claude Desktop through a bridge, Cursor, an MCP gateway): an HTTP MCP server at the URL above, with the header.

## The desktop's AnkiConnect instead

With the [desktop](desktop.md) running the real AnkiConnect add-on, the MCP server can use it instead of the worker: `MCP_ANKI_URL=http://anki-desktop:8765` in `.env`, then `anki-stack restart mcp`. The tools are the same. The worker is the better default: it doesn't depend on a desktop app staying open.
