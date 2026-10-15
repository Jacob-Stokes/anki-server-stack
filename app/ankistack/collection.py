"""The worker's own copy of the collection, kept in step with the sync server.

The worker is a sync client like a phone or a desktop: it holds a collection
file of its own and syncs it with the stack's sync server. Everything goes
through one lock, so a sync never runs in the middle of a change.

Full syncs (one side's copy replaces the other) are decided like this:
  - FULL_DOWNLOAD (this copy is new, the server has a collection): download.
  - FULL_UPLOAD (the server is empty): upload only if this copy has notes.
    An empty copy is never uploaded, so the first real device to sync (a
    phone, the desktop) sets up the server instead of being asked whether
    to replace its cards with an empty collection.
  - FULL_SYNC (both sides changed in a way that can't be merged, e.g. a note
    type edited on two devices): the server wins and this copy downloads.

Changes made through the API since the last sync are journalled. After a
full download they're applied again on top of the server's copy and synced,
so a change the API has confirmed isn't silently lost (a note it added comes
back with a new id; one that can no longer apply, say an edit to a note
deleted elsewhere, is logged and dropped).
"""

import hashlib
import json
import logging
import os
import threading
import time

from anki.collection import Collection
from anki.sync_pb2 import SyncAuth, SyncCollectionResponse

log = logging.getLogger("worker")
Req = SyncCollectionResponse.ChangesRequired


class SyncError(Exception):
    pass


def _is_auth_error(e: Exception) -> bool:
    m = str(e).lower()
    return any(w in m for w in ("password", "auth", "403", "401", "log in", "login"))


class Store:
    def __init__(self, data_dir: str, endpoint: str, user: str, password: str):
        self.data_dir = data_dir
        self.endpoint = endpoint.rstrip("/") + "/"
        self.user, self.password = user, password
        self.lock = threading.RLock()
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "collection.anki2")
        self.auth_file = os.path.join(data_dir, "sync-auth.json")
        self.col = Collection(self.path)
        self.auth: SyncAuth | None = None
        self.last_sync = 0.0          # time of the last successful sync
        self.last_error: str | None = None
        self.last_result = ""         # what the last sync did, in words
        self.dirty = False            # changed since the last sync
        self.journal: list[tuple[str, dict]] = []   # API changes since the last sync
        self.replay = None            # set by the API: applies one journal entry

    # --- auth -----------------------------------------------------------------

    def _fingerprint(self) -> str:
        # which password the saved login came from, without keeping the password
        return hashlib.sha256(f"{self.user}:{self.password}:{self.endpoint}".encode()).hexdigest()[:16]

    def _login(self) -> SyncAuth:
        try:
            with open(self.auth_file) as f:
                saved = json.load(f)
            if saved.get("for") == self._fingerprint():
                return SyncAuth(hkey=saved["hkey"], endpoint=saved["endpoint"])
        except (OSError, ValueError, KeyError):
            pass
        auth = self.col.sync_login(self.user, self.password, self.endpoint)
        auth = SyncAuth(hkey=auth.hkey, endpoint=self.endpoint)
        fd = os.open(self.auth_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"user": self.user, "endpoint": self.endpoint, "hkey": auth.hkey, "for": self._fingerprint()}, f)
        log.info("logged in to the sync server as %s", self.user)
        return auth

    def _forget_login(self):
        self.auth = None
        try:
            os.remove(self.auth_file)
        except OSError:
            pass

    # --- sync -----------------------------------------------------------------

    def note_count(self) -> int:
        return self.col.note_count()

    def sync(self, force: str | None = None) -> str:
        """Sync now. force="download" or "upload" replaces one side with the
        other (the CLI's `sync --download/--upload`). Returns what happened."""
        with self.lock:
            try:
                pending = list(self.journal)
                result = self._sync(force)
                if result.startswith("full download") and pending and self.replay:
                    result += self._replay(pending)
                self.journal.clear()
                self.last_sync, self.last_error, self.last_result, self.dirty = time.time(), None, result, False
                return result
            except Exception as e:  # kept for /health; the caller decides what to say
                self.last_error = f"{type(e).__name__}: {e}"
                raise

    def _sync(self, force):
        if self.auth is None:
            self.auth = self._login()
        if force:
            return self._full(upload=(force == "upload"), server_usn=None, why=f"asked to {force}")
        try:
            out = self.col.sync_collection(self.auth, False)
        except Exception as e:
            if not _is_auth_error(e):
                raise
            # the saved login no longer works (password changed, server reset): sign in again, once
            log.info("the sync server refused the saved login (%s); signing in again", e)
            self._forget_login()
            self.auth = self._login()
            out = self.col.sync_collection(self.auth, False)
        if out.new_endpoint:
            self.auth = SyncAuth(hkey=self.auth.hkey, endpoint=out.new_endpoint)
        req = out.required
        if req == Req.NO_CHANGES:
            result = "no changes"
        elif req == Req.NORMAL_SYNC:
            result = "synced"
        elif req == Req.FULL_DOWNLOAD:
            result = self._full(upload=False, server_usn=out.server_media_usn, why="this copy is new")
        elif req == Req.FULL_UPLOAD:
            if self.note_count() == 0:
                return "the server has no collection yet; waiting for a device to upload one"
            result = self._full(upload=True, server_usn=out.server_media_usn, why="the server is empty")
        else:  # FULL_SYNC: can't merge, the server's copy wins
            log.warning("full sync needed (changes can't be merged): downloading the server's collection")
            result = self._full(upload=False, server_usn=out.server_media_usn, why="the changes couldn't be merged; the server's copy won")
        self._media()
        return result

    def _replay(self, pending) -> str:
        done = 0
        for action, params in pending:
            try:
                self.replay(action, params)
                done += 1
            except Exception as e:
                log.warning("couldn't re-apply %s after the full download: %s", action, e)
        log.info("re-applied %d of %d changes made since the last sync", done, len(pending))
        out = self.col.sync_collection(self.auth, False)   # and send them
        if out.required not in (Req.NO_CHANGES, Req.NORMAL_SYNC):
            log.warning("re-applied changes need another full sync (%s); next sync will handle it", Req.Name(out.required))
        self._media()
        return f"; re-applied {done} of {len(pending)} change(s) made here since the last sync"

    def _full(self, upload: bool, server_usn, why: str) -> str:
        log.info("full %s (%s)", "upload" if upload else "download", why)
        self.col.close_for_full_sync()
        try:
            self.col.full_upload_or_download(auth=self.auth, server_usn=server_usn, upload=upload)
        finally:
            self.col.reopen(after_full_sync=True)
        self._media()
        return f"full {'upload' if upload else 'download'} ({why})"

    def _media(self, timeout=300):
        self.col.sync_media(self.auth)
        end = time.time() + timeout
        time.sleep(0.2)
        while time.time() < end:
            if not self.col.media_sync_status().active:
                return
            time.sleep(0.5)
        log.warning("media sync still running after %ss; carrying on", timeout)

    def close(self):
        with self.lock:
            self.col.close()
