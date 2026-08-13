# Story 16 - Fix `approvals.mode` + expose it as an admin Settings control

## Status
✅ Built 2026-08-12. Part A (set `smart` + restart) done. Part B (admin control) done.

### Part B — what was built
- `GET/PATCH /api/admin/settings/approvals` (`routes/settings.py`): validates mode
  ∈ {smart, off, manual}, writes `config.yaml` via existing atomic `_write_config`,
  restarts runtime, audits (`settings_approvals_mode_update`). **No** session clear.
- Settings → **Tool approvals** section: dropdown showing current mode; selecting
  `manual` reveals an inline warning; Save requires a confirm + restarts runtime.
- `settings_page` passes `runtime.approvals_mode` (read from config.yaml).
- Endpoint verified registered (401 unauth, not 404); PATCH not invoked by Claude
  (would restart the runtime) — driven from the UI by Anthony.

## Problem
`/home/pi/.hermes/profiles/simplifyops/config.yaml` sets:

```yaml
approvals:
  mode: auto      # <-- not a valid value
  timeout: 60
```

`auto` is not a recognized `approvals.mode`. The runtime logs
`Unknown approvals.mode 'auto' — defaulting to 'manual'` and falls back to
**manual**, where tool calls pause waiting for an approval that never arrives
(no human is in that loop). Those stalls burn the agent turn's time budget and
contribute to turns hitting the wall-clock timeout (see the async-turns story).

### `approvals.mode` values
- **smart** — auto-run safe tools, pause only for genuinely risky actions (guardrail)
- **off** — never pause; run every tool immediately (fastest, no guardrail)
- **manual** — always pause for human approval (correct only if an approval UI exists)

## Decision (Anthony)
Set `mode: smart` now. Revisit if the risk/guardrail behavior needs tuning.

## Part A — immediate fix ✅ DONE (2026-08-12)
1. ✅ Edited `config.yaml`: `approvals.mode: auto → smart` (`timeout: 60` kept).
2. ✅ Restarted `simplifyops-agent-runtime.service`.
3. ✅ Verified: runtime `active`, no `Unknown approvals.mode` warning in logs.

## Part B — expose as admin Settings control (proposed)
Anthony asked for a control to change this from the admin UI. It fits the existing
Settings **Provider and Model** pattern (writes `config.yaml` atomically → restarts
runtime), so reuse that machinery rather than build new plumbing.

- **UI:** a "Tool approvals" control in Settings — dropdown `smart / off / manual`
  showing the current value, with a typed-confirmation on save (same guard the
  brain-doc requires for runtime-affecting changes, since it restarts the runtime).
- **Backend:** extend the settings runtime-config writer to also read/write
  `approvals.mode`. Atomic temp+rename write (as Provider+Model already does),
  then `sudo systemctl restart simplifyops-agent-runtime.service`.
- **Read-back:** display the effective value after restart; surface a "restart
  required / applied" notice.
- **Audit:** log the change (old→new, actor) like other Settings mutations.

### Resolved (Anthony, 2026-08-12)
- Dropdown offers all three — `smart / off / manual` — and **`manual` shows an
  inline warning** that it will stall tool calls until an approval surface exists.

## Acceptance
- Part A: `config.yaml` has `mode: smart`; no fallback warning in runtime logs.
- Part B: Settings shows current mode, lets Anthony switch `smart`/`off`, writes
  config atomically, restarts runtime, reads back the applied value, audits it.

## Key Files
- `/home/pi/.hermes/profiles/simplifyops/config.yaml` — `approvals.mode`
- `admin_api/routes/settings.py` — runtime-config PATCH (extend for approvals.mode)
- `admin_api/templates/admin/settings.html` — Provider/Model section (add control)

## Notes
- Raised by the concurrent LLM (2026-08-12); value + fix confirmed against config.
