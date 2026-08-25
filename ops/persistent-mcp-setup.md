# Persistent MCP Server Setup for James

**STATUS: ATTEMPTED BUT NOT WORKING**

This approach was attempted on 2026-07-16 but failed. Hermes is unable to connect to the mcp-proxy HTTP/SSE endpoint (connection errors after 3 retries). The version of Hermes installed may not support HTTP transport for MCP servers, or mcp-proxy SSE format is incompatible.

**Current workaround**: Using consolidated stdio transport (4 services in one NPX call) which gives ~20-23s response times.

**Original Goal**: Reduce James response time from 20-23 seconds to 5-10 seconds by running Google Workspace MCP as a persistent HTTP service instead of spawning fresh NPX processes on each request.

## Problem

Current architecture spawns a fresh `npx @dguido/google-workspace-mcp` process every time Hermes is invoked:
- **~3s** NPX startup overhead
- **~2s** MCP server initialization
- **~15s** Hermes processing
- **Total: 20-23 seconds per response**

## Solution

Use `mcp-proxy` to wrap the stdio MCP server with an SSE/HTTP endpoint, run it as a systemd service, and configure Hermes to connect via HTTP instead of stdio.

---

## Implementation Steps

### Step 1: Install mcp-proxy

```bash
sudo npm install -g mcp-proxy
```

**What it does**: `mcp-proxy` is an SSE proxy that wraps stdio-based MCP servers and exposes them over HTTP, enabling persistent connections.

### Step 2: Create systemd service file

Create `/etc/systemd/system/google-workspace-mcp-proxy.service`:

```ini
[Unit]
Description=Google Workspace MCP Proxy (SSE)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
Environment="HOME=/home/pi/.hermes/profiles/simplifyops/home"
Environment="GOOGLE_WORKSPACE_SERVICES=gmail,calendar,drive,sheets"
ExecStart=/usr/bin/npx mcp-proxy --port 3100 -- npx @dguido/google-workspace-mcp
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Key points**:
- Runs as user `pi`
- Port `3100` for the SSE endpoint
- Uses same `HOME` path as Hermes profile (shares auth tokens)
- Combines all 4 Google services: `gmail,calendar,drive,sheets`
- Auto-restarts on failure

### Step 3: Install and start the service

```bash
sudo cp /tmp/google-workspace-mcp-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable google-workspace-mcp-proxy.service
sudo systemctl start google-workspace-mcp-proxy.service
```

### Step 4: Verify the service is running

```bash
systemctl status google-workspace-mcp-proxy.service
```

Expected output:
```
● google-workspace-mcp-proxy.service - Google Workspace MCP Proxy (SSE)
   Active: active (running) since ...
   ...
   starting server on port 3100
```

### Step 5: Update Hermes config

Edit `/home/pi/.hermes/profiles/simplifyops/config.yaml`:

**Before** (stdio transport - spawns fresh process each time):
```yaml
mcp_servers:
  google-workspace:
    command: npx
    args:
    - '@dguido/google-workspace-mcp'
    env:
      HOME: /home/pi/.hermes/profiles/simplifyops/home
      GOOGLE_WORKSPACE_SERVICES: gmail,calendar,drive,sheets
    enabled: true
```

**After** (HTTP transport - connects to persistent service):
```yaml
mcp_servers:
  google-workspace:
    url: http://localhost:3100/sse
    enabled: true
```

### Step 6: Restart James gateway

```bash
sudo systemctl restart james-gateway.service
```

### Step 7: Test response time

Send a message to James in Telegram and measure response time. Expected improvement:
- **Before**: 20-23 seconds
- **After**: 5-10 seconds

---

## Verification Commands

Check all services are running:
```bash
systemctl status google-workspace-mcp-proxy hindsight james-gateway --no-pager
```

Check recent James responses:
```bash
journalctl -u james-gateway -n 20 --no-pager | grep "Hermes responded"
```

Check MCP proxy logs:
```bash
journalctl -u google-workspace-mcp-proxy -n 50 --no-pager
```

---

## Troubleshooting

### MCP proxy won't start

Check logs:
```bash
journalctl -u google-workspace-mcp-proxy -n 50 --no-pager
```

Verify port 3100 is available:
```bash
ss -tlnp | grep 3100
```

### Hermes can't connect to MCP proxy

Test the SSE endpoint directly:
```bash
curl http://localhost:3100/sse
```

Check Hermes logs:
```bash
tail -50 /home/pi/.hermes/profiles/simplifyops/logs/mcp-stderr.log
```

### Still seeing 20+ second responses

Check if Hermes is using HTTP transport:
```bash
grep -A5 "google-workspace" /home/pi/.hermes/profiles/simplifyops/config.yaml
```

Verify no stdio processes are spawning:
```bash
ps aux | grep -E "npx.*google-workspace" | grep -v mcp-proxy
```

---

## Architecture Diagram

**Before (stdio transport)**:
```
Telegram → Gateway → Hermes → spawn npx (3s) → MCP server (2s) → Response (15s)
                                ↑
                                Spawned fresh every request
```

**After (HTTP transport)**:
```
Telegram → Gateway → Hermes → HTTP connection → MCP Proxy (persistent) → Response (5-10s)
                               ↑                        ↑
                               No spawn overhead        Always running
```

---

## Additional Optimizations Already Applied

1. **Consolidated MCP servers**: Combined 4 separate Google MCP entries (gmail, calendar, drive, sheets) into one
2. **Tool Search enabled**: Defers loading MCP tool schemas until needed (saves context window)
3. **History increased**: Gateway now keeps last 25 user/assistant exchanges (was 15)

---

## Rollback Plan

If the persistent MCP setup causes issues:

1. Stop and disable the MCP proxy service:
   ```bash
   sudo systemctl stop google-workspace-mcp-proxy.service
   sudo systemctl disable google-workspace-mcp-proxy.service
   ```

2. Restore stdio transport in Hermes config:
   ```yaml
   mcp_servers:
     google-workspace:
       command: npx
       args:
       - '@dguido/google-workspace-mcp'
       env:
         HOME: /home/pi/.hermes/profiles/simplifyops/home
         GOOGLE_WORKSPACE_SERVICES: gmail,calendar,drive,sheets
       enabled: true
   ```

3. Restart James:
   ```bash
   sudo systemctl restart james-gateway.service
   ```

---

## Files Modified

- `/etc/systemd/system/google-workspace-mcp-proxy.service` (new)
- `/home/pi/.hermes/profiles/simplifyops/config.yaml` (updated `mcp_servers` section)

## Files Referenced

- `/home/pi/logs/james-gateway.log` (gateway logs)
- `/home/pi/.hermes/profiles/simplifyops/logs/mcp-stderr.log` (MCP server logs)
- `/home/pi/.hermes/profiles/simplifyops/logs/agent.log` (Hermes agent logs)
