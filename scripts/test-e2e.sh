#!/usr/bin/env bash
# End-to-end test, as CI runs it. Needs Docker, curl, python3, git and root
# (or sudo); leaves nothing behind. E2E_DESKTOP=1 also tests the desktop
# (a 2–3 GB image).
#
#   1. compose only: a .env filled in by hand, `docker compose up -d`
#   2. the MCP server: every tool
#   3. another device (an Anki client of its own): changes both ways, and
#      a full sync it forces while the worker has an unsynced change
#   4. the CLI: status, endpoint, sync, users, backup and restore
#   5. the desktop, with AnkiConnect (E2E_DESKTOP=1)
#   6. the installer, non-interactively, in a second folder
#   7. uninstall
set -euo pipefail
trap 'echo "  stopped at line $LINENO: $BASH_COMMAND" >&2' ERR

SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
A="$WORK/compose-only" B="$WORK/installer"
pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; for d in "$A" "$B"; do [ -f "$d/compose.yml" ] && (cd "$d" && COMPOSE_PROFILES=desktop docker compose logs --tail 15 2>&1 | tail -40); done; exit 1; }

copy_stack() {
  mkdir -p "$1"
  (cd "$SRC" && git ls-files -z | xargs -0 -I{} cp --parents {} "$1/")
  (cd "$SRC" && cp -r anki-stack install.sh compose.yml .env.example app images config scripts "$1/")   # untracked edits too, when run by hand
}

cleanup() {
  for d in "$A" "$B"; do [ -f "$d/compose.yml" ] && (cd "$d" && COMPOSE_PROFILES=desktop docker compose down -v --remove-orphans >/dev/null 2>&1 || true); done
  docker image rm e2e-a-anki-stack:26.9.3 e2e-b-anki-stack:26.9.3 e2e-a-anki-stack-desktop:26.9.3 >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# one MCP tool call (JSON-RPC over Streamable HTTP); prints the result text,
# or fails with the tool's error
mcp() {
  local url="$1" token="$2" tool="$3" args="$4"
  curl -s -m 120 "$url" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":$args}}" \
  | python3 -c 'import json,sys
d=json.load(sys.stdin); r=d.get("result") or {}
t=(r.get("content") or [{}])[0].get("text", json.dumps(d))
print(t); sys.exit(1 if r.get("isError") or "error" in d else 0)'
}
# another Anki device, with its own collection in $WORK/device (see e2e-device.py)
device() {
  docker run --rm --network e2e-a-anki_default -v "$WORK/device:/device" -v "$SRC/scripts/e2e-device.py:/e2e.py:ro" \
    --user 0 --entrypoint python e2e-a-anki-stack:26.9.3 /e2e.py http://anki-sync:8080/ "${DEVICE_USER:-ada}" "${DEVICE_PW:-$PW_A}" "$@"
}
ac() { curl -s -m 120 "http://127.0.0.1:18765" -d "{\"action\":\"$1\",\"version\":6,\"key\":\"key-a\",\"params\":${2:-{\}}}"; }

echo "== 1. compose only"
copy_stack "$A"
cd "$A"
cp .env.example .env
PW_A="$(openssl rand -hex 8)"
sed -i "s|^INSTANCE_PREFIX=.*|INSTANCE_PREFIX=e2e-a-|; s|^ANKI_USER=.*|ANKI_USER=ada|; s|^ANKI_PASSWORD=.*|ANKI_PASSWORD=$PW_A|;
  s|^ANKICONNECT_KEY=.*|ANKICONNECT_KEY=key-a|; s|^MCP_BEARER_TOKEN=.*|MCP_BEARER_TOKEN=bearer-a|;
  s|^SYNC_BIND=.*|SYNC_BIND=127.0.0.1:18070|; s|^MCP_BIND=.*|MCP_BIND=127.0.0.1:17012|; s|^ANKICONNECT_BIND=.*|ANKICONNECT_BIND=127.0.0.1:18765|;
  s|^DESKTOP_BIND=.*|DESKTOP_BIND=127.0.0.1:13000|; s|^DESKTOP_ANKICONNECT_BIND=.*|DESKTOP_ANKICONNECT_BIND=127.0.0.1:18766|" .env
mkdir -p data/sync data/worker && chown 1000:1000 data/sync data/worker
docker compose up -d --build --quiet-pull >"$WORK/up.log" 2>&1 || { tail -30 "$WORK/up.log"; fail "docker compose up -d"; }
for _ in $(seq 1 60); do curl -sf http://127.0.0.1:18765/health >/dev/null && break; sleep 2; done
curl -sf http://127.0.0.1:18765/health | grep -q '"ok": true' || fail "the worker synced on start"
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:17012/health >/dev/null && break; sleep 2; done
pass "docker compose up -d: sync server, worker, MCP server"
[ "$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:17012/mcp -d '{}')" = 401 ] || fail "the MCP server needs the bearer token"
ac deckNames | grep -q 'valid api key' && fail "AnkiConnect without the key"
[ "$(curl -s http://127.0.0.1:18765 -d '{"action":"deckNames","version":6,"key":"wrong"}')" = '{"result": null, "error": "valid api key must be provided"}' ] || fail "AnkiConnect refuses a wrong key"
pass "the MCP server and AnkiConnect refuse requests without their secrets"

echo "== 2. the MCP server"
M="http://127.0.0.1:17012/mcp"
mcp $M bearer-a anki_metadata '{"action":"list_decks"}' | grep -q Default || fail "anki_metadata list_decks"
mcp $M bearer-a anki_metadata '{"action":"model_fields","model_name":"Basic"}' | grep -q Front || fail "anki_metadata model_fields"
mcp $M bearer-a anki_metadata '{"action":"create_deck","deck_name":"Spanish::Verbs"}' >/dev/null || fail "anki_metadata create_deck"
nid="$(mcp $M bearer-a anki_notes '{"action":"add","deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"hablar","Back":"to speak"},"tags":["e2e"]}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["note_id"])')" || fail "anki_notes add"
dup="$(mcp $M bearer-a anki_notes '{"action":"add","deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"hablar","Back":"again"}}' 2>&1)" && fail "a duplicate is refused"
grep -q duplicate <<<"$dup" || fail "a duplicate is refused, saying why: $dup"
mcp $M bearer-a anki_notes '{"action":"bulk_add","notes":[{"deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"comer","Back":"to eat"}},{"deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"vivir","Back":"to live"}}]}' | grep -q '"succeeded": 2' || fail "anki_notes bulk_add"
mcp $M bearer-a anki_notes '{"action":"find","query":"deck:Spanish::Verbs"}' | python3 -c 'import json,sys; assert len(json.load(sys.stdin)["note_ids"])==3' || fail "anki_notes find"
mcp $M bearer-a anki_notes "{\"action\":\"update\",\"note_id\":$nid,\"fields\":{\"Back\":\"to talk\"},\"tags\":[\"e2e\",\"edited\"]}" >/dev/null || fail "anki_notes update"
mcp $M bearer-a anki_notes "{\"action\":\"get_info\",\"note_ids\":[$nid]}" | grep -q 'to talk' || fail "anki_notes get_info shows the update"
mcp $M bearer-a anki_notes "{\"action\":\"delete\",\"note_ids\":[$nid]}" | grep -q confirm_needed || fail "anki_notes delete asks for confirm"
mcp $M bearer-a anki_metadata '{"action":"list_tags"}' | grep -q edited || fail "anki_metadata list_tags"
mcp $M bearer-a anki_sync '{}' >/dev/null || fail "anki_sync"
pass "every MCP tool"

echo "== 3. another device"
mkdir -p "$WORK/device"
device sync | grep -q FULL_DOWNLOAD || fail "a new device downloads the collection"
device find "deck:Spanish::Verbs" | grep -q comer || fail "the device has the MCP's notes"
device add "from the device" >/dev/null || fail "the device adds a note"
ac sync >/dev/null || fail "AnkiConnect sync"
mcp $M bearer-a anki_notes '{"action":"find","query":"\"from the device\""}' | grep -q '\[$' || fail "the worker has the device's note"
pass "changes go both ways"
device edit-notetype >/dev/null && device upload >/dev/null || fail "the device uploads its collection"
mcp $M bearer-a anki_notes '{"action":"add","deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"made during a full sync","Back":"x"}}' >/dev/null || fail "add during a full sync"
for _ in $(seq 1 15); do curl -s http://127.0.0.1:18765/health | grep -q 're-applied' && break; sleep 2; done
curl -s http://127.0.0.1:18765/health | grep -q 'full download.*re-applied 1 of 1' || fail "the worker takes the server's copy and re-applies its own change: $(curl -s http://127.0.0.1:18765/health)"
mcp $M bearer-a anki_metadata '{"action":"model_fields","model_name":"Basic"}' | grep -q Extra || fail "the worker has the device's note type change"
device find '"made during a full sync"' | grep -q 'made during' || fail "the device has the worker's re-applied note"
pass "a full sync forced by a device: the server's copy wins, the worker's change is kept"

echo "== 4. the CLI"
./anki-stack status </dev/null >"$WORK/status.log" 2>&1 || { cat "$WORK/status.log"; fail "status"; }
grep -q "Syncing" "$WORK/status.log" || fail "status: $(cat "$WORK/status.log")"
grep -q bearer-a <<<"$(./anki-stack endpoint --show-token </dev/null 2>&1)" || fail "endpoint --show-token"
grep -qE 'no changes|synced' <<<"$(./anki-stack sync </dev/null 2>&1)" || fail "sync"
pass "status, endpoint, sync"
ANKI_NEW_PASSWORD=grace-pw-123 ./anki-stack users add grace </dev/null >/dev/null || fail "users add"
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:18070/health >/dev/null && break; sleep 2; done
mkdir -p "$WORK/device-grace"
docker run --rm --network e2e-a-anki_default -v "$WORK/device-grace:/device" -v "$SRC/scripts/e2e-device.py:/e2e.py:ro" --user 0 --entrypoint python \
  e2e-a-anki-stack:26.9.3 /e2e.py http://anki-sync:8080/ grace grace-pw-123 add "grace's card" >/dev/null || fail "a second account syncs"
grep -q grace <<<"$(./anki-stack users list </dev/null 2>&1)" || fail "users list"
ANKI_NEW_PASSWORD=ada-new-pw-123 ./anki-stack users passwd ada </dev/null >/dev/null || fail "users passwd (the stack's own account)"
for _ in $(seq 1 60); do curl -sf http://127.0.0.1:18765/health >/dev/null && break; sleep 2; done
out="$(mcp $M bearer-a anki_sync '{}' 2>&1)" || fail "the worker syncs with the new password: $out"
curl -s http://127.0.0.1:18765/health | grep -q '"last_error": null' || fail "no sync error after the password change: $(curl -s http://127.0.0.1:18765/health)"
./anki-stack users remove grace </dev/null >/dev/null || fail "users remove"
pass "users: add, list, passwd, remove"
./anki-stack backup </dev/null >/dev/null || fail "backup"
backup="$(ls backups/*.tar.gz)"
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:18070/health >/dev/null && break; sleep 2; done
mcp $M bearer-a anki_notes '{"action":"add","deck_name":"Spanish::Verbs","model_name":"Basic","fields":{"Front":"after the backup","Back":"x"}}' >/dev/null || fail "add a note after the backup"
out="$(mcp $M bearer-a anki_sync '{}' 2>&1)" || fail "sync after the backup: $out $(curl -s http://127.0.0.1:18765/health)"
./anki-stack restore "$backup" --yes </dev/null >"$WORK/restore.log" 2>&1 || { tail -20 "$WORK/restore.log"; fail "restore"; }
for _ in $(seq 1 30); do curl -sf http://127.0.0.1:17012/health >/dev/null && break; sleep 2; done
found="$(mcp $M bearer-a anki_notes '{"action":"find","query":"\"after the backup\" or comer"}')"
python3 -c 'import json,sys; assert len(json.loads(sys.argv[1])["note_ids"])==1' "$found" || fail "restore brought back the backup's collection: $found"
pass "backup and restore"

if [ "${E2E_DESKTOP:-}" = 1 ]; then
  echo "== 5. the desktop"
  ./anki-stack desktop on </dev/null >"$WORK/desktop.log" 2>&1 || { tail -20 "$WORK/desktop.log"; fail "desktop on"; }
  ./anki-stack desktop ankiconnect on </dev/null >/dev/null || fail "desktop ankiconnect on"
  for _ in $(seq 1 90); do curl -s -m 3 http://127.0.0.1:18766 -d '{"action":"version","version":6,"key":"key-a"}' | grep -q '"result": 6' && break; sleep 3; done
  curl -s http://127.0.0.1:18766 -d '{"action":"findNotes","version":6,"key":"key-a","params":{"query":"comer"}}' | grep -q '\[1' || fail "the desktop starts with the collection, and its AnkiConnect answers"
  [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:13000)" = 401 ] || fail "the desktop's page needs its login"
  ./anki-stack desktop off </dev/null >/dev/null || fail "desktop off"
  pass "desktop: signed in, collection there, AnkiConnect on, login required"
fi

echo "== 6. the installer (non-interactive)"
copy_stack "$B"
cd "$B"
cp .env.example .env
sed -i 's/^INSTANCE_PREFIX=.*/INSTANCE_PREFIX=e2e-b-/; s/^SYNC_BIND=.*/SYNC_BIND=127.0.0.1:18071/; s/^MCP_BIND=.*/MCP_BIND=127.0.0.1:17013/; s/^ANKICONNECT_BIND=.*/ANKICONNECT_BIND=127.0.0.1:18767/' .env
export PW_B="$(openssl rand -hex 8)"
./anki-stack install --yes --user grace@example.com --password-env PW_B --tz Europe/London --https none --desktop no </dev/null >"$WORK/install.log" 2>&1 \
  || { tail -30 "$WORK/install.log"; fail "install --yes"; }
token_b="$(sed -n 's/^MCP_BEARER_TOKEN="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' .env)"
[ "${#token_b}" = 64 ] || fail "the installer generated the bearer token"
mcp http://127.0.0.1:17013/mcp "$token_b" anki_metadata '{"action":"list_decks"}' | grep -q Default || fail "the installed MCP server answers"
[ "$(stat -c %a .env)" = 600 ] || fail ".env is private (600)"
pass "install --yes: secrets generated, MCP server answering"

echo "== 7. uninstall"
./anki-stack uninstall --yes </dev/null >/dev/null
[ -z "$(docker ps -aq --filter name=e2e-b-)" ] || fail "uninstall removed the containers"
[ -d data/sync ] || fail "uninstall --yes keeps the data"
pass "uninstall (data kept)"

echo "== all passed"
