"""The worker: a headless Anki collection behind an AnkiConnect-style API.

  POST /         AnkiConnect requests ({"action", "version", "params", "key"})
  GET  /health   status: notes, last sync, last error

It syncs with the sync server on start, a few seconds after every change,
before answering if it hasn't synced for a while, and every SYNC_INTERVAL
minutes. Settings come from the environment (see compose.yml).
"""

import hmac
import json
import logging
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .actions import ActionError, Dispatcher
from .collection import Store

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("worker")


def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and not v:
        sys.exit(f"{name} is required")
    return v


API_KEY = env("ANKICONNECT_KEY", required=True)
CORS = [o.strip() for o in env("ANKICONNECT_CORS", "").split(",") if o.strip()]
SYNC_INTERVAL = float(env("SYNC_INTERVAL", "5")) * 60
WRITE_DELAY = 3.0       # seconds after the last change before syncing it
STALE_AFTER = 60.0      # sync before answering if the last sync is older

store = Store(env("DATA_DIR", "/data"), env("SYNC_URL", "http://anki-sync:8080/"),
              env("ANKI_USER", required=True), env("ANKI_PASSWORD", required=True))


class Debounce:
    """Sync once, WRITE_DELAY seconds after the last of a burst of changes."""

    def __init__(self):
        self.timer = None
        self.mu = threading.Lock()

    def poke(self):
        with self.mu:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(WRITE_DELAY, safe_sync, args=("after a change",))
            self.timer.daemon = True
            self.timer.start()


def safe_sync(why: str):
    try:
        result = store.sync()
        log.info("sync (%s): %s", why, result)
    except Exception as e:
        log.warning("sync (%s) failed: %s", why, e)


debounce = Debounce()
dispatch = Dispatcher(store, STALE_AFTER, debounce.poke)


class Handler(BaseHTTPRequestHandler):
    server_version = "anki-stack-worker"

    def log_message(self, fmt, *args):  # quiet: one line per request is noise
        pass

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and (origin in CORS or "*" in CORS):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            with store.lock:
                notes = store.note_count()
            self._send(200, {
                "ok": store.last_error is None and store.last_sync > 0,
                "notes": notes,
                "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(store.last_sync)) if store.last_sync else None,
                "last_result": store.last_result,
                "last_error": store.last_error,
                "unsynced_changes": store.dirty,
            })
        else:
            # AnkiConnect answers GET / with its version; some clients probe it
            self._send(200, {"apiVersion": "AnkiConnect v.6"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(200, {"result": None, "error": "bad JSON"})
        if self.path.rstrip("/") == "/admin/sync":
            # the CLI's `anki-stack sync [--download|--upload]`
            if not hmac.compare_digest(str(req.get("key") or ""), API_KEY):
                return self._send(403, {"error": "valid api key must be provided"})
            force = req.get("force")
            if force not in (None, "download", "upload"):
                return self._send(400, {"error": "force is download or upload"})
            try:
                return self._send(200, {"result": store.sync(force=force), "notes": store.note_count()})
            except Exception as e:
                return self._send(500, {"error": f"{type(e).__name__}: {e}"})
        if req.get("action") == "requestPermission":
            return self._send(200, {"result": {"permission": "granted", "requireApikey": True, "version": 6}, "error": None})
        if not hmac.compare_digest(str(req.get("key") or ""), API_KEY):
            return self._send(200, {"result": None, "error": "valid api key must be provided"})
        try:
            result = dispatch.handle(req)
            if req.get("action") == "multi" or "version" in req:
                return self._send(200, {"result": result, "error": None})
            return self._send(200, result)  # version-less requests get the bare result, like AnkiConnect
        except ActionError as e:
            return self._send(200, {"result": None, "error": str(e)})
        except Exception as e:
            log.exception("%s failed", req.get("action"))
            return self._send(200, {"result": None, "error": f"{type(e).__name__}: {e}"})


def periodic():
    while True:
        time.sleep(SYNC_INTERVAL)
        if time.time() - store.last_sync >= SYNC_INTERVAL * 0.9:
            safe_sync("every %d min" % (SYNC_INTERVAL / 60))


def main():
    safe_sync("start")
    threading.Thread(target=periodic, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", int(env("PORT", "8765"))), Handler)

    def stop(*_):
        log.info("stopping: syncing unsynced changes first")
        if store.dirty:
            safe_sync("stopping")
        store.close()
        os._exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("AnkiConnect-compatible API on :%s (%d notes)", srv.server_port, store.note_count())
    srv.serve_forever()


if __name__ == "__main__":
    main()
