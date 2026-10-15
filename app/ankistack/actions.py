"""AnkiConnect-compatible actions on a headless collection.

The request and response formats are AnkiConnect's (version 6), so tools
written for AnkiConnect work against the worker unchanged. This covers the
actions those tools use most: decks, note types, notes (add, find, read,
update, delete), cards, tags, media and sync. Anything else answers
"unsupported action"; for the full add-on, run the optional desktop.
"""

import base64
import fnmatch
import os
import time
import urllib.request

from anki.collection import Collection, SearchNode
from anki.notes import Note, NoteFieldsCheckResult

VERSION = 6


class ActionError(Exception):
    pass


def _deck_id(col: Collection, name: str, create: bool = True) -> int:
    did = col.decks.id_for_name(name)
    if did:
        return did
    if not create:
        raise ActionError(f"deck was not found: {name}")
    return col.decks.id(name, create=True)


def _model(col: Collection, name: str):
    m = col.models.by_name(name)
    if not m:
        raise ActionError(f"model was not found: {name}")
    return m


def _note(col: Collection, nid) -> Note:
    try:
        return col.get_note(int(nid))
    except Exception:
        raise ActionError(f"note was not found: {nid}")


def _is_duplicate(col: Collection, note: Note, deck: str, scope: str) -> bool:
    first = note.fields[0]
    if not first.strip():
        return False
    nodes = [SearchNode(note=note.note_type()["name"]),
             SearchNode(field=SearchNode.Field(field_name=note.note_type()["flds"][0]["name"], text=first))]
    if scope == "deck":
        nodes.append(SearchNode(deck=deck))
    return bool(col.find_notes(col.build_search_string(*nodes)))


def _build_note(col: Collection, spec: dict) -> tuple[Note, int]:
    model = _model(col, spec.get("modelName", ""))
    note = col.new_note(model)
    names = [f["name"] for f in model["flds"]]
    for k, v in (spec.get("fields") or {}).items():
        if k not in names:
            raise ActionError(f"field not found in model {model['name']}: {k}")
        note[k] = v
    note.tags = [t for t in (spec.get("tags") or []) if t]
    deck = spec.get("deckName", "")
    if not deck:
        raise ActionError("deckName is required")
    did = _deck_id(col, deck)
    check = note.fields_check()
    if check == NoteFieldsCheckResult.EMPTY:
        raise ActionError("cannot create note because it is empty")
    opts = spec.get("options") or {}
    if not opts.get("allowDuplicate") and _is_duplicate(col, note, deck, opts.get("duplicateScope", "collection")):
        raise ActionError("cannot create note because it is a duplicate")
    return note, did


def _note_info(col: Collection, nid) -> dict:
    n = _note(col, nid)
    m = n.note_type()
    return {
        "noteId": n.id,
        "profile": "User 1",
        "modelName": m["name"],
        "tags": n.tags,
        "fields": {f["name"]: {"value": n.fields[i], "order": i} for i, f in enumerate(m["flds"])},
        "mod": n.mod,
        "cards": list(n.card_ids()),
    }


def _card_info(col: Collection, cid) -> dict:
    c = col.get_card(int(cid))
    n = c.note()
    m = n.note_type()
    return {
        "cardId": c.id, "note": n.id, "deckName": col.decks.name(c.did), "modelName": m["name"],
        "fieldOrder": c.ord, "ord": c.ord,
        "fields": {f["name"]: {"value": n.fields[i], "order": i} for i, f in enumerate(m["flds"])},
        "question": c.question(), "answer": c.answer(),
        "interval": c.ivl, "due": c.due, "reps": c.reps, "lapses": c.lapses, "left": c.left,
        "type": int(c.type), "queue": int(c.queue), "factor": c.factor, "mod": c.mod,
    }


def _media_bytes(p: dict) -> bytes:
    if p.get("data") is not None:
        return base64.b64decode(p["data"])
    if p.get("path"):
        with open(p["path"], "rb") as f:
            return f.read()
    if p.get("url"):
        with urllib.request.urlopen(p["url"], timeout=60) as r:
            return r.read()
    raise ActionError("storeMediaFile needs data, path or url")


# Each action: (function(col, **params), changes the collection?)
def _actions(sync):
    a = {}

    def action(name, writes=False):
        def deco(fn):
            a[name] = (fn, writes)
            return fn
        return deco

    @action("version")
    def version(col):
        return VERSION

    @action("requestPermission")
    def request_permission(col, **_):
        return {"permission": "granted", "requireApikey": True, "version": VERSION}

    @action("sync")
    def do_sync(col, **_):
        sync()
        return None

    # decks
    @action("deckNames")
    def deck_names(col):
        return [d.name for d in col.decks.all_names_and_ids()]

    @action("deckNamesAndIds")
    def deck_names_and_ids(col):
        return {d.name: d.id for d in col.decks.all_names_and_ids()}

    @action("createDeck", writes=True)
    def create_deck(col, deck):
        return _deck_id(col, deck)

    @action("deleteDecks", writes=True)
    def delete_decks(col, decks, cardsToo=False):
        if not cardsToo:
            raise ActionError("since AnkiConnect 6, cardsToo must be true")
        col.decks.remove([d for d in (col.decks.id_for_name(n) for n in decks) if d])
        return None

    @action("changeDeck", writes=True)
    def change_deck(col, cards, deck):
        col.set_deck([int(c) for c in cards], _deck_id(col, deck))
        return None

    @action("getDecks")
    def get_decks(col, cards):
        out = {}
        for cid in cards:
            out.setdefault(col.decks.name(col.get_card(int(cid)).did), []).append(int(cid))
        return out

    # note types
    @action("modelNames")
    def model_names(col):
        return [m.name for m in col.models.all_names_and_ids()]

    @action("modelNamesAndIds")
    def model_names_and_ids(col):
        return {m.name: m.id for m in col.models.all_names_and_ids()}

    @action("modelFieldNames")
    def model_field_names(col, modelName):
        return [f["name"] for f in _model(col, modelName)["flds"]]

    # notes
    @action("addNote", writes=True)
    def add_note(col, note):
        n, did = _build_note(col, note)
        col.add_note(n, did)
        return n.id

    @action("addNotes", writes=True)
    def add_notes(col, notes):
        out = []
        for spec in notes:
            try:
                n, did = _build_note(col, spec)
                col.add_note(n, did)
                out.append(n.id)
            except ActionError:
                out.append(None)
        return out

    @action("canAddNotes")
    def can_add_notes(col, notes):
        out = []
        for spec in notes:
            try:
                _build_note(col, spec)
                out.append(True)
            except ActionError:
                out.append(False)
        return out

    @action("findNotes")
    def find_notes(col, query):
        return list(col.find_notes(query))

    @action("notesInfo")
    def notes_info(col, notes=None, query=None):
        ids = notes if notes is not None else list(col.find_notes(query or ""))
        return [_note_info(col, n) for n in ids]

    @action("updateNoteFields", writes=True)
    def update_note_fields(col, note):
        n = _note(col, note["id"])
        names = [f["name"] for f in n.note_type()["flds"]]
        for k, v in (note.get("fields") or {}).items():
            if k not in names:
                raise ActionError(f"field not found: {k}")
            n[k] = v
        col.update_note(n)
        return None

    @action("updateNote", writes=True)
    def update_note(col, note):
        n = _note(col, note["id"])
        names = [f["name"] for f in n.note_type()["flds"]]
        for k, v in (note.get("fields") or {}).items():
            if k not in names:
                raise ActionError(f"field not found: {k}")
            n[k] = v
        if "tags" in note:
            n.tags = list(note["tags"])
        col.update_note(n)
        return None

    @action("updateNoteTags", writes=True)
    def update_note_tags(col, note, tags):
        n = _note(col, note)
        n.tags = list(tags)
        col.update_note(n)
        return None

    @action("deleteNotes", writes=True)
    def delete_notes(col, notes):
        col.remove_notes([int(n) for n in notes])
        return None

    # cards
    @action("findCards")
    def find_cards(col, query):
        return list(col.find_cards(query))

    @action("cardsInfo")
    def cards_info(col, cards):
        return [_card_info(col, c) for c in cards]

    @action("cardsToNotes")
    def cards_to_notes(col, cards):
        return sorted({col.get_card(int(c)).nid for c in cards})

    @action("suspend", writes=True)
    def suspend(col, cards):
        col.sched.suspend_cards([int(c) for c in cards])
        return True

    @action("unsuspend", writes=True)
    def unsuspend(col, cards):
        col.sched.unsuspend_cards([int(c) for c in cards])
        return True

    @action("areSuspended")
    def are_suspended(col, cards):
        return [col.get_card(int(c)).queue == -1 for c in cards]

    @action("getNumCardsReviewedToday")
    def reviewed_today(col):
        start = (col.sched.day_cutoff - 86400) * 1000
        return col.db.scalar("select count() from revlog where id > ?", start)

    # tags
    @action("getTags")
    def get_tags(col):
        return col.tags.all()

    @action("addTags", writes=True)
    def add_tags(col, notes, tags):
        col.tags.bulk_add([int(n) for n in notes], tags)
        return None

    @action("removeTags", writes=True)
    def remove_tags(col, notes, tags):
        col.tags.bulk_remove([int(n) for n in notes], tags)
        return None

    # media
    @action("storeMediaFile", writes=True)
    def store_media(col, filename, data=None, path=None, url=None, deleteExisting=True):
        if deleteExisting and os.path.exists(os.path.join(col.media.dir(), filename)):
            col.media.trash_files([filename])
        return col.media.write_data(filename, _media_bytes({"data": data, "path": path, "url": url}))

    @action("retrieveMediaFile")
    def retrieve_media(col, filename):
        p = os.path.join(col.media.dir(), os.path.basename(filename))
        if not os.path.isfile(p):
            return False
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()

    @action("getMediaFilesNames")
    def media_names(col, pattern="*"):
        return sorted(n for n in os.listdir(col.media.dir()) if fnmatch.fnmatch(n, pattern))

    @action("deleteMediaFile", writes=True)
    def delete_media(col, filename):
        col.media.trash_files([filename])
        return None

    @action("getMediaDirPath")
    def media_dir(col):
        return col.media.dir()

    return a


class Dispatcher:
    """Runs AnkiConnect requests against the store, one at a time."""

    def __init__(self, store, stale_after: float, on_write):
        self.store = store
        self.stale_after = stale_after
        self.on_write = on_write
        self.table = _actions(lambda: store.sync())
        store.replay = self._apply   # for re-applying journalled changes after a full download

    def _apply(self, action, params):
        fn, _ = self.table[action]
        return fn(self.store.col, **params)

    def handle(self, req: dict):
        action = req.get("action")
        if action == "multi":
            results = []
            for sub in (req.get("params") or {}).get("actions") or []:
                try:
                    results.append(self._one(sub.get("action"), sub.get("params") or {}))
                except Exception as e:
                    results.append({"result": None, "error": str(e)})
            return results
        return self._one(action, req.get("params") or {})

    def _one(self, action, params):
        if action not in self.table:
            raise ActionError("unsupported action")
        fn, writes = self.table[action]
        with self.store.lock:
            # pick up changes from other devices first, if it's been a while
            if action != "sync" and time.time() - self.store.last_sync > self.stale_after:
                try:
                    self.store.sync()
                except Exception:
                    pass  # answer from this copy; the error shows in /health
            try:
                result = fn(self.store.col, **params)
            except TypeError as e:
                raise ActionError(f"bad parameters for {action}: {e}")
            if writes:
                self.store.dirty = True
                self.store.journal.append((action, params))
        if writes:
            self.on_write()
        return result
