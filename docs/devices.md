# Phones and desktops

Every Anki app can sync with a server of your own instead of AnkiWeb. Give it the sync server's address and the account (`anki-stack status` shows the address).

| App | Where |
|---|---|
| **Anki desktop** (Windows, macOS, Linux) | Preferences → Syncing → *Self-hosted sync server*: the address. Then Sync, and sign in with the account. |
| **AnkiDroid** | Settings → Sync → *Custom sync server*: the address as the sync URL (versions that also ask for a media sync URL: the address followed by `msync/`). Then sign in. |
| **AnkiMobile** (iOS) | Settings → Syncing → *Custom server*: the address. Then sign in. |

The address needs to be reachable from the device: on the same machine, `http://127.0.0.1:8070`; elsewhere, the HTTPS address from [HTTPS](https.md) (phones need HTTPS for anything but a local network).

## The first sync

- **A brand-new server and a device with cards**: the device uploads its collection. The worker downloads it on its next sync.
- **A server that already has a collection**: the device is asked whether to upload or download. Download, unless that device's copy is the one to keep.

The worker never uploads an empty collection over a server that has one, so the first device with cards always sets the server up.

## Moving from AnkiWeb

Sync the device that has everything with AnkiWeb first, then switch it to this server and sync: it uploads the whole collection, media included. Point the other devices here and let them download.
