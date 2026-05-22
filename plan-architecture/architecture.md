# SimplifyOps Architecture

## Overview

Automated weekly blog system with a persistent AI CEO that:
1. Scans for trending topics
2. Checks brain folder for related content
3. Sends numbered requests to Human via Telegram
4. Delegates writing to Content Manager
5. Passes drafts to Human for approval
6. Publishes to GitHub Pages

## Components

```
┌─────────────────────────────────────────────────┐
│  Hermes Gateway (WSL)                           │
│  ├─ CEO Personality (persistent)                │
│  ├─ Claude API (model provider)                 │
│  ├─ Telegram (communication)                    │
│  ├─ ddgs (web search)                           │
│  ├─ Hindsight (cross-session memory)               │
│  └─ Skills (project-specific)                   │
│       └─ billing/ (invoice generation)          │
└──────────┬──────────────────────────────────────┘
           │
           ├─► Read: brain_business/ (knowledge base)
           ├─► Search: ddgs (trending topics)
           ├─► Memory: Hindsight (local embedded)
           ├─► Generate: Blog post draft
           ├─► Send: Draft to Human via Telegram
           ├─► Receive: "approve" or "revise: feedback"
           ├─► Publish: Commit to simplifyops.co repo
           │            │
           │            ▼
           │   ┌────────────────────────────┐
           │   │ GitHub Pages               │
           │   │ simplifyops.co             │
           │   │ Jekyll (auto-renders MD)   │
           │   └────────────────────────────┘
           │
           └─► Billing Skill
                ├─► Read: Google Sheet (hours)
                ├─► Generate: Invoice PDF
                └─► Send: Email via SMTP

┌─────────────────────────────────────────────────┐
│  Hindsight (local embedded daemon)              │
│  ├─ Knowledge graph + entity resolution         │
│  ├─ Multi-strategy retrieval                    │
│  └─ Auto-starts on first use, no config needed  │
└─────────────────────────────────────────────────┘
```

## Directory Structure

```
brain_business/                    # Knowledge base (separate repo)
├── roles/
│   ├── ceo/
│   │   ├── README.md              # CEO instructions
│   │   └── learnings.md           # CEO learnings from feedback
│   └── content-manager/
│       ├── README.md              # Content Manager instructions
│       └── learnings.md           # CM learnings
└── logs/
    └── requests.md                # Numbered topic requests

simplifyOps.co/                    # Website (this repo)
├── index.html                     # Landing page (Jekyll-enabled)
├── _config.yml                    # Jekyll configuration
├── _layouts/
│   └── post.html                  # Blog post template
├── _posts/                        # Blog posts (YYYY-MM-DD-title.md)
├── blog/
│   └── index.html                 # Blog listing (auto-populates)
├── billing/                       # Billing skill (project-specific)
│   ├── billing-skill.md           # Hermes skill definition
│   ├── clients.yaml               # Client config (rates, emails)
│   ├── invoice-template.md        # Invoice layout template
│   └── generate_invoice.py        # Invoice generation script
├── logs/
│   └── requests.md                # CEO request log
├── .hermes.md                     # Project config for Hermes
└── plan-architecture/             # Documentation
```

## Starting the System

All commands run in **WSL**.

### Start Hermes Gateway

```bash
cd /mnt/c/Users/adefilippo/MyDocuments/17_projects/simplifyOps.co
hermes gateway run
```

Starting from the project folder loads `.hermes.md` with project-specific paths and rules. Keep this terminal open.

### First-time Setup

If gateway fails to connect Telegram, run:

```bash
hermes setup
```

Select "Messaging Platforms (Gateway)" and configure Telegram.

### Set CEO Personality

On Telegram, send to your bot:

```
/personality ceo
```

Hermes remembers this across sessions.

## Web Search

The CEO uses ddgs (DuckDuckGo CLI) for web searches.

### Install ddgs (one-time)

```bash
sudo apt install pipx -y && pipx install duckduckgo-search
```

### Usage

The CEO can run:
```bash
ddgs news 'business operations trends 2026'
ddgs text 'startup management best practices'
```

## Weekly Workflow

1. **CEO scans trends** — Uses ddgs to find trending topics
2. **CEO checks brain** — Looks in brain_business/ for related content
3. **CEO sends request** — "REQ-001: Topic X. Relevant files: Y. Approve?"
4. **Human approves** — Reply on Telegram
5. **CEO delegates** — Gives brief to Content Manager
6. **Content Manager writes** — Drafts blog post
7. **CEO passes to Human** — Sends draft for final approval
8. **Human approves** — Reply "approve" or "revise: feedback"
9. **CEO publishes** — Saves to blog folder, commits to GitHub

## Configuration Files

### ~/.hermes/.env

```
ANTHROPIC_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ALLOWED_USERS=your_chat_id
TELEGRAM_HOME_CHANNEL=your_chat_id
```

### ~/.hermes/config.yaml

CEO personality is defined under `agent: personalities: ceo:`

```yaml
ceo: |
  You are the CEO of SimplifyOps.co, a consulting business for startups and mid-sized growing companies. You report to the Human owner via Telegram.
  Character: Straight-talking but not a jerk. Hands-on experience across many areas - not book knowledge, real work.
  Job: Scan for trending topics in operations/management/strategy. Check brain folder for related content. Send numbered requests (REQ-XXX) to Human for topic approval. Delegate writing to Content Manager. Pass drafts to Human for final approval. Learn from feedback.
  Hard rules: No repeating topics two weeks in a row. No plagiarism - honor over content. Cite 1-2 approved sources per post. No generic, rude, or random content. Always get Human approval before publishing.
  Brain folder: /mnt/c/Users/adefilippo/MyDocuments/17_projects/brain_business
```

### ~/.hermes/SOUL.md

Backup persona file (not auto-loaded by gateway, but CEO can read it).

## Troubleshooting

### Gateway exits immediately
Check logs: `cat ~/.hermes/logs/gateway.log | tail -30`

Common issue: Telegram token malformed (duplicated or missing).

### CEO doesn't know its role
Send `/personality ceo` on Telegram.

### ddgs not found
Install: `pipx install duckduckgo-search`

### Gateway won't start (systemd error)
Use `hermes gateway run` instead of `hermes gateway start` in WSL.

## Hindsight (Cross-Session Memory)

Hindsight is Hermes's built-in memory plugin — knowledge graph, entity resolution, and multi-strategy retrieval. Running in local embedded mode (no separate service needed; daemon starts automatically on first use).

### Setup (WSL)

```bash
hermes memory setup
# Select "hindsight" → local_embedded mode
```

Or manually:
```bash
hermes config set memory.provider hindsight
echo "HINDSIGHT_LLM_API_KEY=your-anthropic-key" >> ~/.hermes/.env
```

### Config File

`~/.hermes/hindsight/config.json` — created by setup wizard.

Key settings:

| Key | Value | Description |
|-----|-------|-------------|
| `mode` | `local_embedded` | Daemon runs locally, no external service |
| `llm_provider` | `anthropic` | Used for memory extraction |
| `auto_recall` | `true` | Recalls memories before each turn |
| `auto_retain` | `true` | Retains conversation turns automatically |

### Tools Available to Agent

| Tool | Purpose |
|------|---------|
| `hindsight_recall` | Search memories (semantic + entity graph) |
| `hindsight_reflect` | LLM-synthesized answer across memories |
| `hindsight_retain` | Store a new memory with entity extraction |

## Billing Skill

Hermes can generate and send invoices from Google Sheet time tracking.

### Setup

1. **Google service account** at `~/.config/gcloud/simplifyops-co-*.json`
2. **Sheet shared** with service account email
3. **Config** in `billing/clients.yaml` (client details, SMTP settings)
4. **External skill dir** added to `~/.hermes/config.yaml`:
   ```yaml
   skills:
     external_dirs:
       - /mnt/c/Users/adefilippo/MyDocuments/17_projects/simplifyOps.co/billing
   ```

### Usage

Via CEO on Telegram:
- "Prepare an invoice for ManagePro for March"
- "Bill ManagePro for March and send it"

Direct (WSL):
```bash
cd /mnt/c/Users/adefilippo/MyDocuments/17_projects/simplifyOps.co
python3 billing/generate_invoice.py ManagePro March        # generate only
python3 billing/generate_invoice.py ManagePro March --send # generate + email
```

### Config Files

| File | Purpose |
|------|---------|
| `billing/clients.yaml` | Client names, rates, emails, SMTP config |
| `billing/invoice-template.md` | Invoice layout (Jinja2 template) |
| `billing/billing-skill.md` | Hermes skill instructions |

## Future Enhancements

- **Tavily API**: Native web search — add `TAVILY_API_KEY` to `.env` for built-in search (1000 free/month)
- **Ollama**: Local LLM for offline/cheaper usage
- **Scheduled runs**: Cron job to trigger weekly blog automatically
- **Discord**: Multi-agent channels for different agent conversations
- **Firebase**: User auth + database if site needs login
