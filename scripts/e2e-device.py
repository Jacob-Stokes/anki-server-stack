"""A stand-in for another device (a phone, a desktop) in the end-to-end test:
an Anki client with its own collection in /device, syncing with the stack's
sync server. Run inside the stack's image:

  python e2e-device.py SYNC_URL USER PASSWORD COMMAND [ARG]

Commands: sync (prints what the sync needed), add FRONT, find QUERY (prints
note fronts), edit-notetype (adds a field to "Basic": a change that can't be
merged), upload (replaces the server's collection with this one).
"""

import os
import sys

from anki.collection import Collection
from anki.sync_pb2 import SyncCollectionResponse

Req = SyncCollectionResponse.ChangesRequired
url, user, password, cmd = sys.argv[1:5]
arg = sys.argv[5] if len(sys.argv) > 5 else ""
os.makedirs("/device", exist_ok=True)
col = Collection("/device/collection.anki2")
auth = col.sync_login(user, password, url)


def full(upload: bool, usn=None):
    col.close_for_full_sync()
    col.full_upload_or_download(auth=auth, server_usn=usn, upload=upload)
    col.reopen(after_full_sync=True)


def sync():
    out = col.sync_collection(auth, False)
    name = Req.Name(out.required)
    if out.required == Req.FULL_DOWNLOAD:
        full(False, out.server_media_usn)
    elif out.required == Req.FULL_UPLOAD:
        full(True, out.server_media_usn)
    elif out.required == Req.FULL_SYNC:
        full(False, out.server_media_usn)   # like choosing "download" on a phone
    return name


if cmd == "sync":
    print(sync())
elif cmd == "add":
    sync()
    note = col.new_note(col.models.by_name("Basic"))
    note["Front"], note["Back"] = arg, "from the device"
    col.add_note(note, col.decks.id("Device", create=True))
    print(sync())
elif cmd == "find":
    sync()
    print("\n".join(col.get_note(n)["Front"] for n in col.find_notes(arg)))
elif cmd == "edit-notetype":
    sync()
    m = col.models.by_name("Basic")
    col.models.add_field(m, col.models.new_field(f"Extra{len(m['flds'])}"))
    col.models.update_dict(m)
    print("edited")
elif cmd == "upload":
    full(True)   # no sync first: a phone choosing "upload" when asked
    print("uploaded")
else:
    sys.exit(f"unknown command {cmd}")
col.close()
