# Current Architecture (SimplifyOps)

Last updated: 2026-05-31

## Purpose
This is the canonical architecture snapshot for sharing with humans or other LLMs.

## Mandatory update rule
Before any architecture/system decision or architecture doc edit in this repo:

1. Run from repo root:
```bash
graphify update .
```
2. Read:
- `graphify-out/GRAPH_REPORT.md`
3. Update this file if anything architecture-relevant changed.

## What is live right now

### Runtime host and repo
- Host: Raspberry Pi Linux environment
- Main repo: `/home/pi/simplifyops`
- Graph artifacts: `/home/pi/simplifyops/graphify-out/`
- Canonical architecture file: `/home/pi/simplifyops/plan/current-architecture.md`

### Hermes agent runtime
- Active profile: `simplifyops`
- Profile root: `/home/pi/.hermes/profiles/simplifyops`
- Primary interface: Telegram DM
- Memory provider in Hermes config: `hindsight`

### Planned robotics control architecture (current decision)
- Hermes runs on the Raspberry Pi 5.
- ROS 2 control nodes run on the Raspberry Pi 5.
- Arduino Uno is the real-time motor-control bridge.
- Motor controller receives PWM commands from the Arduino Uno.
- Command chain: phone/user command -> Hermes on Pi -> ROS 2 node on Pi -> serial/USB link -> Arduino Uno -> PWM -> motor controller -> hub motor.
- Safety controls (on Pi side): command timeout (deadman), max throttle cap, ramp limiting, emergency stop.

### Memory stack (minimal mode)
Hermes memory is configured to use a local external Hindsight API.

- Hermes memory mode: `hindsight` provider + `local_external`
- Hindsight API URL used by Hermes: `http://localhost:8888`
- API bind: `127.0.0.1:8888` (loopback only)
- Database backend: local PostgreSQL
- Database extension: `pgvector` installed/enabled

### Hindsight provider behavior currently enabled
- LLM provider: `none`
- Embeddings provider: `openai`
- Reranker provider: `rrf`

### Hindsight features intentionally disabled right now
This is the “basic, memory-first” setup.

- MCP server: disabled
- MCP extension: disabled
- File upload API: disabled
- Auto consolidation: disabled
- Mental model history: disabled
- Observation history: disabled

Rationale: keep the system minimal and stable, then enable features only when needed.

## Data flow (current)
1. User message arrives in Hermes (Telegram).
2. Hermes uses Hindsight plugin for memory operations.
3. Plugin calls local Hindsight API at `127.0.0.1:8888`.
4. Hindsight API reads/writes memory data in local Postgres (`hindsight` DB, with pgvector).
5. Hermes continues response generation with recalled memory context.

## Operational checks
Use these exact checks for current-state validation:

```bash
# 1) Refresh architecture graph view
cd /home/pi/simplifyops
graphify update .

# 2) Verify Hermes memory provider
/home/pi/.hermes/hermes-agent/venv/bin/hermes memory status --profile simplifyops

# 3) Verify Hindsight API health
curl -s http://127.0.0.1:8888/health

# 4) Verify listener
ss -ltnp | grep 8888
```

Expected healthy state:
- Hermes shows `Provider: hindsight` and `Status: available`
- `/health` returns healthy + DB connected
- Port `127.0.0.1:8888` is listening

## Configuration locations
- Hermes profile config:
  - `/home/pi/.hermes/profiles/simplifyops/config.yaml`
- Hindsight provider config JSON:
  - `/home/pi/.hermes/profiles/simplifyops/hindsight/config.json`
- Profile env wiring (API/DB/providers):
  - `/home/pi/.hermes/profiles/simplifyops/.env`

## If sharing this architecture with another LLM
Tell it this explicitly:
- “Use `/home/pi/simplifyops/plan/current-architecture.md` as the canonical live architecture.”
- “Run `graphify update .` first, then read `graphify-out/GRAPH_REPORT.md` before proposing architecture changes.”
- “Assume minimal-memory mode is intentional; do not enable extra Hindsight features unless requested.”

## Change policy
Update this file immediately when any of the following changes:
- Memory provider mode, URL, bind address, or DB backend
- Any Hindsight feature toggle (enabled/disabled)
- Health-check commands or expected outputs
- Profile/repo paths used by operations

## Source-of-truth order
1. Live runtime checks (`health`, listener, Hermes memory status)
2. `graphify-out/GRAPH_REPORT.md`
3. This file
4. Legacy docs under `plan-architecture/`
