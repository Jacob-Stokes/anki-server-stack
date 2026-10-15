"""The MCP server: Anki notes, decks and sync as MCP tools, over Streamable
HTTP at /mcp with a bearer token.

It talks the AnkiConnect protocol to ANKI_URL: the worker by default, or the
desktop's real AnkiConnect add-on if pointed there. Same tools either way:

  anki_notes     add, bulk_add, find, get_info, update, bulk_update, delete
  anki_metadata  list_decks, create_deck, list_models, model_fields, list_tags
  anki_sync      sync with the sync server now
"""

import hmac
import json
import logging
import os
import sys
import urllib.request
from typing import Any, Literal

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("mcp")

ANKI_URL = os.environ.get("ANKI_URL", "http://anki-worker:8765")
ANKI_KEY = os.environ.get("ANKICONNECT_KEY", "")
BEARER = os.environ.get("MCP_BEARER_TOKEN") or sys.exit("MCP_BEARER_TOKEN is required")


class AnkiError(ToolError):
    """Shown to the client as the tool's error message."""


def anki(action: str, **params) -> Any:
    body = json.dumps({"action": action, "version": 6, "key": ANKI_KEY, "params": params}).encode()
    req = urllib.request.Request(ANKI_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except OSError as e:
        raise AnkiError(f"can't reach Anki at {ANKI_URL}: {e}")
    if out.get("error"):
        raise AnkiError(f"{action}: {out['error']}")
    return out.get("result")


def _spec(deck_name, model_name, fields, tags, allow_duplicate):
    return {"deckName": deck_name, "modelName": model_name, "fields": fields or {}, "tags": tags or [],
            "options": {"allowDuplicate": bool(allow_duplicate), "duplicateScope": "deck"}}


server = MCPServer(name="anki-mcp", version="1.0.0",
                   instructions="Anki flashcards. Use anki_metadata to find deck names, note types and their "
                                "fields before adding notes with anki_notes. Searches use Anki's search syntax.")


@server.tool(description=(
    "Anki notes (flashcards). Actions: "
    "add: one note; needs deck_name, model_name (note type, e.g. 'Basic' or 'Cloze'), fields "
    "{field name: content} and optional tags; a missing deck is created. "
    "bulk_add: up to 50 notes in `notes` ([{deck_name, model_name, fields, tags}]). "
    "find: note ids matching `query` in Anki search syntax (e.g. 'deck:Spanish tag:verbs', 'added:1'). "
    "get_info: fields, tags, note type and cards of `note_ids`. "
    "update: replace some `fields` of `note_id` (and its `tags` if given). "
    "bulk_update: up to 50 {note_id, fields} in `updates`. "
    "delete: remove `note_ids` (needs confirm: true). "
    "Duplicates (same first field, same deck) are refused unless allow_duplicate is true."),
    annotations=ToolAnnotations(destructiveHint=True))
def anki_notes(
    action: Literal["add", "bulk_add", "find", "get_info", "update", "bulk_update", "delete"],
    deck_name: str | None = None, model_name: str | None = None, fields: dict[str, str] | None = None,
    tags: list[str] | None = None, allow_duplicate: bool = False,
    notes: list[dict[str, Any]] | None = None, query: str | None = None,
    note_ids: list[int] | None = None, note_id: int | None = None,
    updates: list[dict[str, Any]] | None = None, confirm: bool = False,
) -> dict:
    if action == "add":
        if not (deck_name and model_name and fields):
            raise ToolError("add needs deck_name, model_name and fields")
        nid = anki("addNote", note=_spec(deck_name, model_name, fields, tags, allow_duplicate))
        return {"note_id": nid, "deck": deck_name, "model": model_name}
    if action == "bulk_add":
        if not notes or len(notes) > 50:
            raise ToolError("bulk_add needs 1 to 50 notes")
        specs = [_spec(n.get("deck_name"), n.get("model_name"), n.get("fields"), n.get("tags"), allow_duplicate) for n in notes]
        ids = anki("addNotes", notes=specs)
        results = [{"ok": i is not None, "note_id": i, "deck": n.get("deck_name")} for i, n in zip(ids, notes)]
        return {"total": len(results), "succeeded": sum(r["ok"] for r in results), "failed": sum(not r["ok"] for r in results),
                "results": results}
    if action == "find":
        if query is None:
            raise ToolError("find needs a query")
        return {"note_ids": anki("findNotes", query=query)}
    if action == "get_info":
        if not note_ids:
            raise ToolError("get_info needs note_ids")
        return {"notes": anki("notesInfo", notes=note_ids)}
    if action == "update":
        if note_id is None or not (fields or tags is not None):
            raise ToolError("update needs note_id and fields (or tags)")
        note: dict[str, Any] = {"id": note_id, "fields": fields or {}}
        if tags is not None:
            note["tags"] = tags
        anki("updateNote", note=note)
        return {"ok": True, "note_id": note_id}
    if action == "bulk_update":
        if not updates or len(updates) > 50:
            raise ToolError("bulk_update needs 1 to 50 updates")
        results = []
        for u in updates:
            try:
                anki("updateNoteFields", note={"id": u["note_id"], "fields": u.get("fields") or {}})
                results.append({"ok": True, "note_id": u["note_id"]})
            except (AnkiError, KeyError) as e:
                results.append({"ok": False, "note_id": u.get("note_id"), "error": str(e)})
        return {"total": len(results), "updated": sum(r["ok"] for r in results), "failed": sum(not r["ok"] for r in results),
                "results": results}
    if action == "delete":
        if not note_ids:
            raise ToolError("delete needs note_ids")
        if not confirm:
            return {"confirm_needed": f"This deletes {len(note_ids)} note(s) and their cards. Call again with confirm: true."}
        anki("deleteNotes", notes=note_ids)
        return {"deleted": len(note_ids)}
    raise ToolError(f"unknown action {action}")


@server.tool(description=(
    "Anki decks, note types and tags. Actions: list_decks; create_deck (deck_name, e.g. 'Spanish::Verbs'); "
    "list_models (note types); model_fields (the fields of model_name: check these before adding notes); "
    "list_tags."),
    annotations=ToolAnnotations(readOnlyHint=False))
def anki_metadata(action: Literal["list_decks", "create_deck", "list_models", "model_fields", "list_tags"],
                  deck_name: str | None = None, model_name: str | None = None) -> dict:
    if action == "list_decks":
        return {"decks": anki("deckNames")}
    if action == "create_deck":
        if not deck_name:
            raise ToolError("create_deck needs deck_name")
        return {"deck": deck_name, "deck_id": anki("createDeck", deck=deck_name)}
    if action == "list_models":
        return {"models": anki("modelNames")}
    if action == "model_fields":
        if not model_name:
            raise ToolError("model_fields needs model_name")
        return {"model": model_name, "fields": anki("modelFieldNames", modelName=model_name)}
    if action == "list_tags":
        return {"tags": anki("getTags")}
    raise ToolError(f"unknown action {action}")


@server.tool(description="Sync the collection with the sync server now, so changes reach phones and other devices "
                         "(it also happens on its own a few seconds after every change).")
def anki_sync() -> dict:
    anki("sync")
    return {"ok": True, "synced": True}


@server.custom_route("/health", methods=["GET"])
async def health(request):
    try:
        anki("version")
        return JSONResponse({"ok": True, "anki": ANKI_URL})
    except Exception as e:
        return JSONResponse({"ok": False, "anki": ANKI_URL, "error": str(e)}, status_code=503)


def bearer_guard(app):
    """Bearer token on /mcp; /health is open (it says nothing about the collection)."""
    want = f"Bearer {BEARER}".encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            got = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(got, want):
                resp = JSONResponse({"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
                return await resp(scope, receive, send)
        return await app(scope, receive, send)
    return guarded


def main():
    app = server.streamable_http_app(
        stateless_http=True, json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    log.info("MCP server on :%s/mcp, Anki at %s", os.environ.get("PORT", "8080"), ANKI_URL)
    uvicorn.run(bearer_guard(app), host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), log_level="warning")
