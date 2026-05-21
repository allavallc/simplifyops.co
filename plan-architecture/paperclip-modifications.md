# Paperclip Modifications

All custom changes to `~/paperclip-wsl/paperclip-source/`.

## Frontend Changes

- **2026-04-05: Comment sort order (newest first)**
  - File: `ui/src/components/CommentThread.tsx`
  - Changed `a.createdAtMs - b.createdAtMs` → `b.createdAtMs - a.createdAtMs`
  - Why: Newest comments at top, oldest at bottom

- **2026-04-05: Comment input at top, sticky**
  - File: `ui/src/components/CommentThread.tsx`
  - Moved comment editor above TimelineList
  - Added `sticky top-0 z-10 bg-background pb-4` to editor container
  - Why: Comment input always visible at top when scrolling through comments

- **2026-04-06: Inbox "Mine" tab status filter**
  - File: `ui/src/pages/Inbox.tsx`
  - Added `mineStatusFilter` state and dropdown on "Mine" tab
  - Options: All, Backlog, Todo, In Progress, In Review, Blocked, Done, Cancelled
  - Why: "Mine" tab shows everything by default, need to filter by status to see only relevant items

## Backend Changes

- **2026-04-05: Allowed hostnames env var**
  - File: `docker-compose.yml`
  - Added `PAPERCLIP_ALLOWED_HOSTNAMES: "server"` to server environment
  - Why: Permanent fix for Hermes → Paperclip API calls

## Environment Setup (Windows + WSL + Docker)

**Architecture:**
- Windows 11 with Docker Desktop
- WSL2 (Ubuntu) for running docker compose commands
- Docker containers run via Docker Desktop's WSL integration

**Permanent fix: Docker credential helper error**
- Problem: `fork/exec /usr/bin/docker-credential-desktop.exe: exec format error`
- Cause: Docker Desktop sets `credsStore: "desktop"` which WSL can't execute
- Fix: Remove `credsStore` from `C:\Users\adefilippo\.docker\config.json`
- This persists across Docker restarts (unlike the WSL-side fix)

**Key paths:**
- Windows Docker config: `C:\Users\adefilippo\.docker\config.json`
- WSL Paperclip source: `~/paperclip-wsl/paperclip-source/`
- SimplifyOps project: `/mnt/c/Users/adefilippo/MyDocuments/17_projects/simplifyOps.co/`

**Important:** Always run `docker compose` commands from WSL, not PowerShell or Git Bash.

## Configuration Changes

- **2026-04-06: Disabled heartbeat timer on CEO agent**
  - Setting: Agent → Run Policy → Heartbeat enabled = false
  - Was: `intervalSec: 3600` (wake every hour automatically)
  - Why: Agent was waking up every hour unprompted, draining API credits. Heartbeat should only be enabled if you want the agent to proactively check for work on a schedule.

