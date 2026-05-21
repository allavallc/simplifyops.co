# Paperclip Patches for SimplifyOps

Custom patches to Paperclip source code. Apply these to `~/paperclip-wsl/paperclip-source/`.

## Patch 1: Anthropic Cost Tracking

**Purpose:** Query Anthropic Admin API for actual billed costs instead of calculating from pricing tables.

### Files:

1. `anthropic-cost-tracker.ts` → Copy to `server/src/services/anthropic-cost-tracker.ts`
2. `heartbeat-cost-patch.diff` → Apply to `server/src/services/heartbeat.ts`

### Setup:

1. Add admin key to SimplifyOps project `.env`:
   ```
   ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-...
   ```

2. Copy the cost tracker module:
   ```bash
   cp /workspace/simplifyops/plan-architecture/paperclip-patches/anthropic-cost-tracker.ts \
      ~/paperclip-wsl/paperclip-source/server/src/services/
   ```

3. Apply heartbeat patch (see below)

4. Rebuild:
   ```bash
   cd ~/paperclip-wsl/paperclip-source && docker compose up -d server --build
   ```

### How it works:

1. After each run completes, `updateRuntimeState()` is called
2. If adapter doesn't provide `costUsd`, we query the Anthropic Admin API
3. API returns actual billed cost for the time window of the run
4. Cost event is created with real cost, not calculated estimate

### Security:

- Admin key read from `/workspace/simplifyops/.env` only
- Key never logged
- Key stays in SimplifyOps project, not global Paperclip config
