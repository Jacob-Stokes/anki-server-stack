"""Before the desktop app starts: a profile signed in to the stack's sync
server, the first-run language prompt skipped, and the AnkiConnect add-on
on or off (DESKTOP_ANKICONNECT). Safe to run on every start."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import anki.lang  # noqa: E402
from anki.collection import Collection  # noqa: E402
from aqt.profiles import ProfileManager  # noqa: E402

anki.lang.set_lang("en_US")   # the profile code names things through Anki's translations

BASE = Path("/config/.local/share/Anki2")
PROFILE = "User 1"
ADDON = BASE / "addons21" / "2055492159"   # AnkiConnect's add-on code
url = os.environ.get("ANKI_SYNC_URL", "http://anki-sync:8080/")
user, password = os.environ.get("ANKI_USER", ""), os.environ.get("ANKI_PASSWORD", "")

BASE.mkdir(parents=True, exist_ok=True)
pm = ProfileManager(BASE)
pm.setupMeta()
pm.meta["firstRun"] = False
pm.meta["defaultLang"] = pm.meta.get("defaultLang") or "en_US"
if PROFILE not in pm.profiles():
    pm.create(PROFILE)
pm.load(PROFILE)
pm.set_custom_sync_url(url)
pm.set_last_loaded_profile_name(PROFILE)
pm.profile["autoSync"] = True
pm.profile["syncMedia"] = True

# sign in, unless already signed in as this user
if user and password and (pm.profile.get("syncUser") != user or not pm.profile.get("syncKey")):
    tmpdir = tempfile.mkdtemp()
    tmp = Collection(os.path.join(tmpdir, "login.anki2"))   # only to sign in
    try:
        auth = tmp.sync_login(user, password, url)
        pm.set_sync_key(auth.hkey)
        pm.set_sync_username(user)
        print(f"anki-setup: signed in to {url} as {user}")
    except Exception as e:
        print(f"anki-setup: couldn't sign in to {url}: {e}", file=sys.stderr)
    finally:
        tmp.close()
        shutil.rmtree(tmpdir, ignore_errors=True)
pm.save()

# A new desktop starts with the server's collection already downloaded,
# rather than an empty one and Anki asking whether to download
col_path = BASE / PROFILE / "collection.anki2"
if not col_path.exists() and pm.profile.get("syncKey"):
    from anki.sync_pb2 import SyncAuth, SyncCollectionResponse
    Req = SyncCollectionResponse.ChangesRequired
    col_path.parent.mkdir(parents=True, exist_ok=True)
    col = Collection(str(col_path))
    try:
        auth = SyncAuth(hkey=pm.profile["syncKey"], endpoint=url)
        out = col.sync_collection(auth, False)
        if out.required in (Req.FULL_DOWNLOAD, Req.FULL_SYNC):
            col.close_for_full_sync()
            col.full_upload_or_download(auth=auth, server_usn=out.server_media_usn, upload=False)
            col.reopen(after_full_sync=True)
            print(f"anki-setup: downloaded the collection ({col.note_count()} notes); media follows when Anki syncs")
    except Exception as e:
        print(f"anki-setup: couldn't download the collection yet ({e}); Anki will offer to", file=sys.stderr)
    finally:
        col.close()

# AnkiConnect: installed and configured, or removed
if os.environ.get("DESKTOP_ANKICONNECT", "false").lower() in ("1", "true", "yes", "on"):
    if not (ADDON / "__init__.py").exists():
        shutil.copytree("/defaults/ankiconnect", ADDON, dirs_exist_ok=True)
    cors = [o.strip() for o in os.environ.get("ANKICONNECT_CORS", "").split(",") if o.strip()]
    (ADDON / "config.json").write_text(json.dumps({
        "apiKey": os.environ.get("ANKICONNECT_KEY") or None, "apiLogPath": None,
        "ignoreOriginList": [], "webBindAddress": "0.0.0.0", "webBindPort": 8765,
        "webCorsOriginList": cors or ["http://localhost"]}, indent=2))
    print("anki-setup: AnkiConnect on (port 8765)")
elif ADDON.exists():
    shutil.rmtree(ADDON)
    print("anki-setup: AnkiConnect removed")
