# Story 19 - Gateway consolidation (retire the resurrected legacy james-gateway)

## Status
✅ Done 2026-08-12 (incident response). **Written retroactively** — the work was
executed under a live incident before a story existed, which violated stories-first.
This story exists so the changes + decisions are on the permanent record.

## Problem (live incident, 2026-08-12)
Two gateways were running and **fighting over the same Telegram bot token**:
- `simplifyops-gateway.service` — the durable gateway (`/home/pi/projects/simplifyops/gateway/gateway.py`), correct architecture.
- `james-gateway.service` — a **resurrected legacy** 4KB gateway at the recreated
  `/home/pi/simplifyops/gateway/gateway.py`, running the old `hermes -p simplifyops -z`
  subprocess-per-message path.

Telegram allows only one `getUpdates` poller per bot, so both logged continuous
**409 Conflict**. Whichever won each race handled the message — and when the legacy
one won, James was reached via a **cold subprocess with no durable context**
(no persistent runtime session, no governance/person context, no memory link,
fresh browser each time).

## Root cause
Not an automated trigger. The systemd sudo audit log shows a **one-time manual
install** from `/home/pi/claude-relay-home` (the other agent's workspace) at 16:31:
```
cp /home/pi/james-gateway.service /etc/systemd/system/   (source: stale June-2 leftover)
systemctl daemon-reload
systemctl enable james-gateway
systemctl start james-gateway
```
Verified there is **no** cron job, systemd timer, or installer script; `james-gateway`
was started exactly once ever. The legacy `/home/pi/simplifyops/` tree was recreated
manually at 16:30 as the ExecStart target.

## Decisions (Anthony, explicit)
- Stop immediately to clear the 409. ✅
- Identify + neutralize the resurrection trigger before deciding on disable. ✅ (none exists)
- **Disable** only with Anthony's explicit OK (crosses the never-delete/disable rule). ✅ approved
- Prefer fixing recurrence over disabling; keep the unit file in place (never delete). ✅
- Hold deletion of the legacy tree pending other-agent WIP confirmation. ✅

## What was done
1. `systemctl stop james-gateway` — cleared the 409; durable gateway became sole poller.
2. `systemctl disable james-gateway` — removed the boot wants-symlink (closes the
   reboot-resurrection vector). **Unit file left in `/etc/systemd/system/`** (reversible).
3. Deleted the stale source copy `/home/pi/james-gateway.service` (June-2 leftover) —
   removes the trivial re-install source.
4. Left the legacy tree `/home/pi/simplifyops/` in place (inert — nothing starts it),
   pending the other agent confirming it is not work-in-progress.
5. Coordination note (signed c1) left at
   `/home/pi/claude-relay-home/NOTE-from-c1-gateway-consolidation.md`.

## Verification
- `simplifyops-gateway`: active, sole `gateway.py` process (PID from projects path).
- `james-gateway`: inactive + disabled; unit file still present in `/etc`.
- No 409 in `simplifyops-gateway` logs after the stop.
- James context path intact: runtime session `api_1786481669_36fa147a` (GET→200),
  SOUL.md symlink resolves, Hindsight `/health` 200, runtime on `-p simplifyops`.

## Dependency
This consolidation (single durable gateway holding one persistent API session across
turns) is a prerequisite for **story-18** — owned by the other agent. See that story
for its own scope and rationale; not restated here.

## Open / follow-up
- Remove the inert legacy `/home/pi/simplifyops/` tree once the other agent confirms
  it is not WIP (deletion — needs Anthony OK).
- Multi-agent coordination is an ongoing risk (two Claude agents share the box).

## Multi-agent note
I am agent **c1**; a second Claude agent works the same box from
`/home/pi/claude-relay-home`. Before infra changes, check the sudo audit log
(`journalctl | grep PWD=/home/pi/claude-relay-home`) to see the other agent's actions.
