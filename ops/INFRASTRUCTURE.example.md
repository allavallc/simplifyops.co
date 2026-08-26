# Infrastructure Inventory (TEMPLATE)

Copy this to `ops/INFRASTRUCTURE.md` (gitignored) and fill in the real values. **Never commit the
real file** — the repo is public. Read `ops/INFRASTRUCTURE.md` before deploy/infra work.

## Host
- Machine: `<e.g. Raspberry Pi 5, hostname>`
- OS / arch: `<...>`
- Tailscale IP / hostname: `<100.x.x.x>`
- SSH: `<user@host, key location>`

## Services (systemd)
- `simplifyops-admin.service` — FastAPI control plane, port 3000
- `simplifyops-gateway.service` — Telegram adapter + durable worker, internal 3001
- `simplifyops-agent-runtime.service` — Hermes runtime + API server, port 8642
- `hindsight.service` — memory, port 8888

## Data
- Postgres: `<socket / DSN, databases: whitelist_app, hindsight>`
- Hermes home: `<~/.hermes/profiles/simplifyops>`

## Secrets (locations only — never values)
- `<~/.config/relay.env, ~/.config/simplifyops-runtime.env, ...>`

## Deploy / Git
- Remote: `<github repo>` — `main` is trunk (staging/prod split = story-30)
- Deploy method: `<pull + systemctl restart, or CI/CD>`

## Restart / repair quick-ref
- `sudo systemctl restart <service>`
- Stuck work items: `UPDATE work_items SET status='ready', locked_until=NULL WHERE status='processing' AND locked_until<now();`
