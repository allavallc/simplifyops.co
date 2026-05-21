# Starting Up SimplifyOps

## Quick Start

All services run via Docker. Start from **WSL**:

```bash
# Start Honcho (memory layer) - if not running
cd ~/honcho && docker compose up -d

# go to the home folder
cd ~/paperclip-wsl/paperclip-source

# Start Hermes + Paperclip
docker start paperclip-source-hermes-1 paperclip-source-server-1 paperclip-source-db-1
```

Or if you need to rebuild:
```bash
cd ~/paperclip-wsl/paperclip-source && docker compose up -d
```

## Verify Services

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(paperclip|hermes|honcho)"
```

Expected:
| Service | Port | Purpose |
|---------|------|---------|
| `paperclip-source-server-1` | 3100 | Task dashboard |
| `paperclip-source-hermes-1` | 8642 | Telegram gateway + API |
| `paperclip-source-db-1` | 5433 | Paperclip database |
| `honcho-api-1` | 8000 | Memory API |

## Access Points

- **Paperclip Dashboard:** http://localhost:3100
- **Honcho API Docs:** http://localhost:8000/docs
- **Telegram:** Message your bot, use `/personality ceo`

## Stopping

```bash
docker stop paperclip-source-server-1 paperclip-source-hermes-1
```

To stop everything including Honcho:
```bash
cd ~/paperclip-wsl/paperclip-source && docker compose down
cd ~/honcho && docker compose down
```

## Logs

**View recent logs:**
```bash
docker logs paperclip-source-hermes-1 --tail 50 #Telegram messages, agent responses, API calls to Paperclip 
docker logs paperclip-source-server-1 --tail 50 #Task execution, API requests from Hermes
```

**Watch logs in real-time (follow mode):**
```bash
# Hermes (Telegram messages, API calls)
docker logs -f paperclip-source-hermes-1

# Paperclip server (task execution)
docker logs -f paperclip-source-server-1

# Both at once (in separate terminals, or combined)
docker logs -f paperclip-source-hermes-1 &
docker logs -f paperclip-source-server-1
```

**Filter logs for errors:**
```bash
docker logs paperclip-source-hermes-1 2>&1 | grep -i error
```

## Configuration

All persistent config is in `~/paperclip-wsl/paperclip-source/docker-compose.yml`:
- `PAPERCLIP_ALLOWED_HOSTNAMES: "server"` — allows Hermes to call Paperclip API
- `HONCHO_*` env vars — memory connection settings
- Volume mounts for workspace and Hermes data

No manual setup commands needed after first install.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Hostname not allowed" | Already fixed in docker-compose.yml — just restart server |
| VPN + Docker conflict | Disconnect VPN before starting Docker Desktop |
| Config changes not applied | `docker compose up -d --force-recreate` |

## Full Setup

See `ceo-architecture.md` for complete system documentation.
