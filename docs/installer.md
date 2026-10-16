# Installer

```bash
./install.sh          # the same as ./anki-stack install
```

It checks Docker (Compose 2.24 or newer) and then asks:

1. **The sync account**: a name (or email) and a password, or a generated one. Phones, desktops and the stack itself sign in to the sync server with it.
2. **Timezone.**
3. **The address**. It first looks at what this machine already has (something on ports 80/443, Tailscale, cloudflared) and suggests using that rather than running a second one. See [HTTPS](https.md).
4. **The desktop** (optional): full Anki in a browser tab, and whether to run AnkiConnect in it. See [The desktop](desktop.md).

It generates the secrets (the AnkiConnect key, the MCP bearer token, the desktop's login), writes `.env` (readable by root only), builds the images and starts everything. At the end it shows the sync server's address, the account, the MCP endpoint and the desktop's login, and offers to add an `anki-stack` command to `/usr/local/bin`.

Running it again on an existing install repairs it: missing secrets are generated, nothing that's set is changed, and the containers are brought up to date.

## Without questions

For scripts and automation, every answer can be given as an option, with `--yes` taking the defaults for the rest:

```bash
export ANKI_PW='a-long-password'
./anki-stack install --yes --user ada --password-env ANKI_PW --tz Europe/London \
  --https none --desktop no
```

| Option | |
|---|---|
| `--user NAME` | The sync account |
| `--password-env VAR` | Its password, from that environment variable (passwords never go in options) |
| `--tz ZONE` | Timezone |
| `--https none\|caddy\|tailscale\|cloudflare` | The address, run by the stack; with `--domain`, `--acme-email` (caddy), `--ts-hostname` (tailscale) |
| `--https host-tailscale\|host-cloudflare\|proxy` | The address, through what's already on this machine; with `--tailscale-serve yes\|no`, `--tailnet-extras yes\|no` (host-tailscale), `--domain` (host-cloudflare), `--url` (proxy) |
| `--desktop yes\|no`, `--desktop-ankiconnect yes\|no` | The desktop, and AnkiConnect in it |

Secrets for Tailscale and Cloudflare come from `TS_AUTHKEY` and `CF_TUNNEL_TOKEN` in the environment.
