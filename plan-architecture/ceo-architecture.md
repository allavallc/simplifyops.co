# SimplifyOps CEO Agent Architecture

## Overview

SimplifyOps runs an AI CEO agent (James Bott) that handles day-to-day operations across multiple channels. The architecture enables:

- **Unified memory** — James remembers context across all interactions
- **Multi-channel access** — Telegram, Paperclip tasks, future Discord/email
- **Persistent identity** — Same agent, same personality, same knowledge everywhere

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HUMAN LAYER                                  │
│                                                                      │
│    Anthony (Founder)          Future Workers (Bob, etc.)            │
│         │                              │                             │
│         ▼                              ▼                             │
│    ┌─────────┐                   ┌─────────┐                        │
│    │Telegram │                   │Telegram │                        │
│    │  DM     │                   │  DM     │                        │
│    └────┬────┘                   └────┬────┘                        │
└─────────┼────────────────────────────┼──────────────────────────────┘
          │                            │
          ▼                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GATEWAY LAYER (Presistent Style)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Hermes Gateway (Docker Container)                │   │
│  │                                                               │   │
│  │   - Telegram Bot Interface                                    │   │
│  │   - OpenAI-compatible API Server (port 8642)                  │   │
│  │   - Message routing                                           │   │
│  │   - Session management                                        │   │
│  │   - Future: Discord, WhatsApp, Email                         │   │
│  └───────────────────────┬──────────────────────────────────────┘   │
│                          │                                           │
│     ┌────────────────────┴────────────────────┐                     │
│     │ All channels route through same gateway │                     │
│     │ (consistent environment & memory)       │                     │
│     └────────────────────┬────────────────────┘                     │
│                          │                                           │
└──────────────────────────┼───────────────────────────────────────────┘
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
      ▼                    ▼                    ▼
┌───────────┐       ┌───────────┐       ┌───────────┐
│ Telegram  │       │ Paperclip │       │  Future   │
│   Bot     │       │   Tasks   │       │ Channels  │
│  (direct) │       │ (via API) │       │           │
└───────────┘       └───────────┘       └───────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INTELLIGENCE LAYER                               │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐   │
│  │   James Bott    │    │     Hermes      │    │    Honcho      │   │
│  │   (SOUL.md)     │───▶│   Agent Core    │───▶│    Memory      │   │
│  │                 │    │                 │    │                │   │
│  │  - Identity     │    │  - LLM calls    │    │  - Cross-      │   │
│  │  - Personality  │    │  - Tool use     │    │    session     │   │
│  │  - Relationships│    │  - Skills       │    │  - User        │   │
│  │  - Standards    │    │                 │    │    modeling    │   │
│  └─────────────────┘    └─────────────────┘    └────────────────┘   │
│                                                        │             │
└────────────────────────────────────────────────────────┼─────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                   │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐   │
│  │   PostgreSQL    │    │     Redis       │    │  Local Files   │   │
│  │   (pgvector)    │    │    (cache)      │    │                │   │
│  │                 │    │                 │    │  - Transcripts │   │
│  │  - Embeddings   │    │  - Sessions     │    │  - MEMORY.md   │   │
│  │  - Messages     │    │  - Rate limits  │    │  - Skills      │   │
│  │  - User models  │    │                 │    │                │   │
│  └─────────────────┘    └─────────────────┘    └────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Hermes Gateway Container

**Purpose:** Routes messages between humans and the AI agent

**Responsibilities:**
- Receive messages from Telegram (and future platforms)
- Manage conversation sessions
- **Style:** Run agent tasks via API server (not CLI spawning)
- Deliver responses back to the originating channel

**Docker service:** `paperclip-source-hermes-1`

**Key config:**
- `TELEGRAM_BOT_TOKEN` — Bot authentication
- `TELEGRAM_ALLOWED_USERS` — Authorized user IDs
- `HONCHO_BASE_URL` — Points to memory service
- `API_SERVER_ENABLED=true` — Enable OpenAI-compatible API
- `API_SERVER_HOST=0.0.0.0` — Bind to all interfaces
- `API_SERVER_PORT=8642` — API server port

**Exposed ports:**
- `8642` — OpenAI-compatible API (used by Paperclip server)

### 2. Honcho Memory Service

**Purpose:** Provides persistent, cross-session memory

**Responsibilities:**
- Store conversation history
- Build user models (learn about each human)
- Provide context retrieval for the agent
- Enable memory to persist across restarts

**Docker services:**
- `honcho-api-1` — Main API (port 8000)
- `honcho-database-1` — PostgreSQL with pgvector
- `honcho-redis-1` — Session cache
- `honcho-deriver-1` — Background reasoning (optional)

**Key concepts:**
- **Workspace** — Isolates SimplifyOps from other projects (`simplifyops`)
- **Peer** — Identity (James Bott is `james-bott`, humans are derived from their user IDs)
- **Session** — Conversation context (per-directory or global)

### 3. James Bott (SOUL.md)

**Purpose:** Defines the agent's identity and behavior

**Location:** `souls/james-bott.md`

**Contains:**
- Identity and role definition
- Communication style
- Relationship context (who Anthony is, future team members)
- Standards and boundaries

### 4. Paperclip Task Server

**Purpose:** Task orchestration and scheduling

**Responsibilities:**
- Schedule recurring tasks (weekly blog posts)
- Manage task queues
- Track task completion
- Provide dashboard UI
- **Route agent work through Hermes gateway API**

**Docker service:** `paperclip-source-server-1`

**Key config:**
- `HERMES_API_URL` — Points to gateway API (`http://hermes:8642`)
- `PAPERCLIP_AGENT_JWT_SECRET` — For API authentication

**Style Architecture:**

Paperclip does NOT spawn Hermes CLI processes. Instead:
1. Paperclip server builds the prompt (with issue context, comments, etc.)
2. Calls `POST http://hermes:8642/v1/chat/completions` (OpenAI format)
3. Hermes gateway runs the agent (same environment as Telegram)
4. Response returned via HTTP

This ensures:
- Consistent environment (same tools, same memory config)
- Shared Honcho context (agent sees Telegram conversation history)
- No process spawn overhead

## Memory Architecture

### How Memory Flows

```
Human sends message
       │
       ▼
Hermes receives via Gateway
       │
       ▼
Hermes queries Honcho for context
       │
       ├── Recent conversation history
       ├── User profile/preferences
       └── Relevant past interactions
       │
       ▼
Hermes + James Bott generate response
       │
       ▼
Response sent to human
       │
       ▼
Conversation saved to Honcho
       │
       ▼
Honcho updates user model (async)
```

### Session Identity

| Source | Session Key | User Peer ID |
|--------|-------------|--------------|
| Anthony via Telegram | `agent:main:telegram:dm:8633043564` | `user-telegram-8633043564` |
| Bob via Telegram | `agent:main:telegram:dm:XXXXX` | `user-telegram-XXXXX` |
| CLI (local) | `simplifyops` | `user-simplifyops` |

All sessions share the same:
- **Workspace:** `simplifyops`
- **AI Peer:** `james-bott`

This means James Bott can:
- Remember each human individually
- Access shared company context
- Maintain consistent identity across channels

## Configuration Files

### Honcho Config

**Location:** `/opt/data/honcho.json` (inside Hermes container)

```json
{
  "baseUrl": "http://host.docker.internal:8000",
  "apiKey": "local-dev",
  "workspace": "simplifyops",
  "aiPeer": "james-bott",
  "enabled": true,
  "saveMessages": true,
  "memoryMode": "hybrid",
  "writeFrequency": "async",
  "recallMode": "hybrid",
  "sessionStrategy": "per-directory",
  "hosts": {
    "hermes": {
      "enabled": true,
      "workspace": "simplifyops",
      "aiPeer": "james-bott"
    }
  }
}
```

**Known Issue: Docker Volume Sync**

The WSL path `~/.hermes/` is mounted to `/opt/data/` in the container, but Docker Desktop's WSL integration doesn't always sync file changes properly. Files created in WSL may not appear in the container and vice versa.

**To update config, edit inside the container:**

```bash
docker exec -it paperclip-source-hermes-1 sh -c 'cat > /opt/data/honcho.json << EOF
{
  "baseUrl": "http://host.docker.internal:8000",
  ...your config...
}
EOF'

# Then restart to apply
docker restart paperclip-source-hermes-1
```

**To verify config:**

```bash
docker exec paperclip-source-hermes-1 hermes honcho status
```

### Model Config

**Location:** `/opt/data/config.yaml` (inside Hermes container)

The default LLM model is set here:

```yaml
model:
  default: "anthropic/claude-sonnet-4-5"
```

**To change the model:**

```bash
docker exec paperclip-source-hermes-1 sh -c 'sed -i "s|default: \"OLD_MODEL\"|default: \"NEW_MODEL\"|g" /opt/data/config.yaml'

# Then start a new session in Telegram with /new
```

**Common model names (OpenRouter format):**
- `anthropic/claude-sonnet-4-5` — Fast, cost-effective
- `anthropic/claude-opus-4-6` — Most capable
- `google/gemini-2.5-flash` — Very fast, cheap

### Docker Compose

**Location:** `~/paperclip-wsl/paperclip-source/docker-compose.yml` (WSL)

**Services:**
- `db` — Paperclip PostgreSQL (port 5433)
- `server` — Paperclip server (port 3100) — currently stopped
- `hermes` — Gateway container (Telegram bot)

### Project Config

**Location:** `.hermes.md` (project root)

Contains project-specific settings for blog posts, content rules, and paths.

## Multi-User Support

James Bott supports multiple human collaborators:

1. **Automatic user identification** — Each Telegram user gets a unique peer ID derived from their chat ID
2. **Per-user memory** — Honcho tracks preferences and history per human
3. **Shared context** — Company-wide knowledge accessible to all interactions
4. **Relationship awareness** — SOUL.md describes key relationships; James learns new ones through conversation

### Adding a New Team Member

1. Add their Telegram user ID to `TELEGRAM_ALLOWED_USERS` in docker-compose
2. They message James via Telegram
3. James asks who they are (if not introduced)
4. Honcho creates their user profile automatically
5. Optionally update SOUL.md with relationship context

## Running the System

### Start Honcho (if not running)

```powershell
cd $env:USERPROFILE\honcho
docker compose up -d
```

### Start Hermes Gateway

```bash
# WSL
cd ~/paperclip-wsl/paperclip-source
docker compose up -d hermes
```

### Verify Status

```bash
# Check containers
docker ps

# Check Honcho API
curl http://localhost:8000/docs

# Check Hermes logs
docker logs paperclip-source-hermes-1 --tail 50
```

## Fresh Setup Guide (New Platform)

Follow these steps when adding a new channel (Discord, etc.) or setting up from scratch.

### Prerequisites

- Docker Desktop running (disconnect VPN first - they conflict on Windows)
- WSL installed (all docker compose commands must run from WSL, not Git Bash)
- Honcho running locally (see "Start Honcho" above)

### Step 1: Configure Shared Honcho Settings

All platforms must use identical Honcho settings to share memory.

**Create/update `~/.hermes/honcho.json` (WSL):**

```json
{
  "baseUrl": "http://host.docker.internal:8000",
  "apiKey": "local-dev",
  "workspace": "simplifyops",
  "aiPeer": "james-bott",
  "enabled": true,
  "saveMessages": true,
  "memoryMode": "hybrid",
  "writeFrequency": "async",
  "recallMode": "hybrid",
  "sessionStrategy": "global",
  "hosts": {
    "hermes": {
      "enabled": true,
      "workspace": "simplifyops",
      "aiPeer": "james-bott"
    }
  }
}
```

**Critical settings:**
- `workspace`: Must be `simplifyops` on all platforms
- `aiPeer`: Must be `james-bott` on all platforms
- `sessionStrategy`: Must be `global` (not `per-directory`)
- `baseUrl`: Use `host.docker.internal:8000` from Docker containers

### Step 2: Mount Hermes Data in Docker

Each container needs access to the shared Hermes config directory.

**Add to `docker-compose.yml` for new service:**

```yaml
services:
  new-gateway:
    volumes:
      - /home/adefilippo/.hermes:/opt/data  # or /hermes-data
    environment:
      HERMES_HOME: /opt/data
      HONCHO_BASE_URL: "http://host.docker.internal:8000"
      HONCHO_API_KEY: "${HONCHO_API_KEY:-local-dev}"
      HONCHO_WORKSPACE: "simplifyops"
      HONCHO_AI_PEER: "james-bott"
```

### Step 3: Fix Memory File Permissions

After first use, memory files may have wrong permissions:

```bash
# Make memory files readable by all container users
docker exec <container-name> chmod 644 /opt/data/memories/*.md
```

**Why:** Different containers run as different users (root, node). Memory files created by one container may not be readable by another.

### Step 4: Verify Memory Sharing

Test from inside the new container:

```bash
docker exec <container-name> sh -c 'hermes honcho status'
# Should show: Connection... OK, workspace=simplifyops, aiPeer=james-bott

docker exec <container-name> sh -c 'hermes chat -q "What do you know about me?" -Q'
# Should recall information from other platforms
```

### Step 5: Platform-Specific Config

| Platform | Extra Config Needed |
|----------|---------------------|
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` |
| Discord | `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID` |
| Paperclip | JWT auth headers in prompt template (see below) |

---

## Setup Requirements

Configuration steps required to make the system work correctly.

### Shared Memory Across Platforms

For James Bott to share memory across Telegram, Paperclip, and other channels, ALL Hermes instances must use the same Honcho workspace and peer.

**Required env vars in Paperclip server (`docker-compose.yml`):**

```yaml
HONCHO_BASE_URL: "http://host.docker.internal:8000"
HONCHO_API_KEY: "${HONCHO_API_KEY:-local-dev}"
HONCHO_WORKSPACE: "simplifyops"
HONCHO_AI_PEER: "james-bott"
```

**Required in Hermes gateway (`/opt/data/honcho.json`):**

```json
{
  "workspace": "simplifyops",
  "aiPeer": "james-bott"
}
```

If these don't match, each platform creates separate memory — James won't remember conversations across channels.

### Paperclip Server Volume Mounts

The Paperclip server needs access to Hermes config. Must be started from **WSL** (not Git Bash) for mounts to work:

```bash
cd ~/paperclip-wsl/paperclip-source && docker compose up -d server
```

Required mounts in `docker-compose.yml`:

```yaml
volumes:
  - /home/adefilippo/.hermes:/hermes-data
  - /mnt/c/Users/adefilippo/MyDocuments/17_projects/simplifyOps.co:/workspace/simplifyops
```

If started from Git Bash, mounts fail silently and Hermes can't find its config.

### Honcho Storage-Only Mode

Honcho runs locally without LLM costs. Required `.env` in `~/honcho/`:

```
EMBED_MESSAGES=false
DERIVER_ENABLED=false
SUMMARY_ENABLED=false
DREAM_ENABLED=false
```

Dummy API keys required even when disabled (validation runs on startup).

### Docker + VPN Conflict

Disconnect VPN before starting Docker Desktop. They conflict on Windows.

### Honcho Session Strategy

Both containers must use `sessionStrategy: "global"` in `honcho.json`:

```json
{
  "sessionStrategy": "global"
}
```

If set to `"per-directory"`, each working directory creates a separate session and memory isn't shared.

### Paperclip Allowed Hostnames

Paperclip validates incoming API requests against an allowed hostname list. The Hermes container connects using the Docker network hostname `server`, which must be whitelisted.

**Permanent fix in `docker-compose.yml`:**

```yaml
server:
  environment:
    PAPERCLIP_ALLOWED_HOSTNAMES: "server"
```

Without this, James gets `Hostname 'server' is not allowed for this Paperclip instance` errors when trying to access the Paperclip API from the Hermes container.

**Note:** The `pnpm paperclipai allowed-hostname server` command is a temporary fix that gets wiped on container restart. Always use the environment variable for persistence.

### Paperclip API Authentication

Paperclip generates a JWT token for each agent run and injects it as `PAPERCLIP_API_KEY`. The agent must use this in API calls.

**The hermes-paperclip-adapter prompt template must include auth headers:**

```bash
curl -s -H "Authorization: Bearer $PAPERCLIP_API_KEY" "http://localhost:3100/api/..."
```

Without this, James gets "Unauthorized" errors when trying to read issues or update status.

### Memory Recall in Task Execution

The Paperclip prompt template must instruct James to check memory before working on tasks:

```
## Workflow

0. FIRST: Search your memory for any relevant context about this task
1. Work on the task using your tools
...
```

Without this, James won't automatically recall information from other platforms (Telegram, etc.) when processing Paperclip tasks.

### Hermes Adapter Patch File (Style)

Custom implementation of the hermes-paperclip-adapter:

```
~/paperclip-wsl/paperclip-source/patches/hermes-execute.js
```

This file is mounted into the server container at:
```
/app/node_modules/.pnpm/hermes-paperclip-adapter@0.2.0/node_modules/hermes-paperclip-adapter/dist/server/execute.js
```

**Style Implementation:**

The adapter calls the Hermes gateway API instead of spawning CLI processes:

```javascript
// Old approach (BAD - spawns new process each task):
// const result = await runChildProcess(ctx.runId, hermesCmd, args, {...});

// New approach (GOOD - routes through persistent gateway):
const response = await fetch(`${HERMES_API_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        model: "hermes-agent",
        messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userMessage }
        ],
        stream: false
    })
});
```

**Current features:**
1. Routes through gateway API (`http://hermes:8642/v1/chat/completions`)
2. Injects issue comments via `issueCommentsMarkdown` in prompt
3. Auth headers included in all curl commands
4. Memory recall instruction in task workflow
5. Debug logging for troubleshooting

After editing the patch, restart from WSL:

### Memory File Permissions

Both containers (Hermes gateway and Paperclip server) mount the same `~/.hermes/` directory. Memory files in `memories/` must be readable by all users:

```bash
chmod 644 ~/.hermes/memories/*.md
```

**Common issue:** USER.md gets created with root ownership (mode 600) which the Paperclip server (running as `node` user) cannot read. Symptoms:
- Telegram recalls memory correctly
- Paperclip says "I don't have any information about that"

Fix from either container:
```bash
docker exec paperclip-source-hermes-1 chmod 644 /opt/data/memories/*.md
```
```bash
cd ~/paperclip-wsl/paperclip-source && docker compose up -d server --force-recreate
```

---

## Future Enhancements

1. **Paperclip integration** — Scheduled tasks, recurring blog posts
2. **Discord gateway** — Team communication channel
3. **Email integration** — Inbox management
4. **Dashboard UI** — Visual task and memory management
5. **Skill library** — Reusable capabilities across tasks
