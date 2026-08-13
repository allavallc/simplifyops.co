# Story 18 - Persistent browser session across turns (stop tearing the browser down every reply)

## Status
**Implemented 2026-08-13 (Option A + dedicated Xvfb :1) — awaiting live verification.**
Applied: `xvfb-james.service` (Xvfb :1), runtime `DISPLAY=:1` + `After=xvfb-james.service`,
`config.yaml` `browser: {headed: true, inactivity_timeout: 3600}`, runtime restarted. Not
yet proven end-to-end — needs Anthony to run a real survey (Claude cannot message James).
Root cause was confirmed in runtime code; approach approved 2026-08-12/13.

## Problem
James can never finish a survey because the browser is destroyed after **every**
agent reply. Each Telegram message is a separate agent turn, and a post-reply hook
tears the browser down, so the next turn starts on `about:blank` / logged out. James
re-logs-in every message and never advances past the first question.

Confirmed in the Hermes runtime (installed at `~/.local/lib/python3.13/site-packages`,
read-only — not our repo):

```python
# agent/chat_completion_helpers.py:2183-2197  (runs after each reply)
headed = _is_headed_mode()
if headed:
    ...            # skip cleanup — browser survives between turns
else:
    _ra().cleanup_browser(task_id)     # ← tears the browser down every turn
```
```python
# tools/browser_tool.py:892-919
def _is_headed_mode() -> bool:
    _cached_headed_mode = False
    val = cfg.get("browser", {}).get("headed")      # config["browser"]["headed"]
    ... or env AGENT_BROWSER_HEADED                  # fallback
```

**Verified current state:** `config.yaml` has **no `browser:` section**, and
`AGENT_BROWSER_HEADED` is not set in `relay.env` / runtime env → `headed=False` →
`cleanup_browser` fires every turn. `task_id` keying *is* stable across turns, so the
session key isn't the problem — the teardown is.

**Evidence:** James self-diagnosed at work_item #206 ("the automation browser is
losing the page state between messages"). Survey attempts A (2026-08-11) and C
(2026-08-12) both failed this way. Full trace: `/home/pi/survey-attempt-bugs.md`.

Note: someone set `BROWSER_INACTIVITY_TIMEOUT=3600` in `relay.env`. That feeds the
idle reaper (`browser_tool._get_session_inactivity_timeout`:1463; used at :1553,
passed to agent-browser at :1103), **not** the per-turn hook (gated only by `headed`).
It's the right *secondary* lever but useless alone: while `headed=False` the browser
is destroyed after every reply, before the idle timer ever matters. Necessary once
headed is on; not sufficient by itself. (config `browser.inactivity_timeout` is
authoritative; that env is the legacy fallback.)

## Research findings (external standard — how working agents persist a browser)
Independent implementations converge on the same three requirements — a session
survives across turns only if you do all three:
1. **Keep the browser alive between turns** (don't tear down each reply)
2. **Anchor state to a persistent profile / user-data-dir** (cookies, login on disk)
3. **Reattach to the same session each turn** (connect, don't relaunch)

Proof (real code):
- **browser-use:** `Browser(user_data_dir=..., profile_directory=..., keep_alive=True)` —
  `keep_alive` prevents auto-close; `user_data_dir` reuses a logged-in profile.
- **Steel:** `sessions.create({persistProfile:true})` → `release()` →
  `create({profileId})` → `chromium.connectOverCDP()`.
- **Playwright (the primitive underneath):** `launch_persistent_context(user_data_dir)`.

Our stack already supports all three (Hermes `browser.headed`; agent-browser
`--restore`; stable `task_id`) — none are enabled.

## Proposed approach — Option A (recommended, minimal): enable headed mode
Add to `config.yaml` (config, not code — per project rules):
```yaml
browser:
  headed: true
```
This flips `_is_headed_mode()` → the per-turn `cleanup_browser` is **skipped**, so the
live browser (login **and** current survey page) survives between turns. Also set
`browser.inactivity_timeout` high (e.g. 3600) so the idle reaper doesn't kill it during
multi-minute gaps between user messages. Restart runtime + clear sessions (the flow the
Settings page already uses for provider/model).

**Hard dependency — verified in code:** `headed:true` also appends `--headed` to
agent-browser (`browser_tool.py:2386-2387`), i.e. it launches a **visible** Chromium,
not headless. There is **no** "keep-alive but headless" option — `headed` is the only
switch that skips the teardown. So Option A **requires a reliable X display**. We have
one now (`/tmp/.X11-unix/X0` + `labwc`/Xwayland on `:0`), but this Pi's display has been
fragile historically (see display memory: apt upgrades have broken the session before).
Option A ties survey reliability to display reliability.

### Option B (Chromium persistent profile) — NOT config-achievable
agent-browser supports `--profile <dir>` (persistent user-data-dir, the Playwright
pattern), but **Hermes never passes it** — the command builder emits only
`--session/--headed/--engine/--cdp` (verified in `browser_tool.py`). So keeping Chromium
*and* persisting a profile without headed would require **runtime code changes we don't
own.** Not a config option. Rules out the "A+B on Chromium" idea.

### Option C (display-free, config-only): Camofox managed persistence
```yaml
browser:
  camofox:
    managed_persistence: true
```
Switches James from agent-browser/Chromium to **Camofox (Firefox)**, whose cleanup skips
profile destruction so **cookies/login survive across turns — fully headless, no display**
(`browser_tool.py:4433-4441`).

**Verified 2026-08-12 — heavier than a config flip:** Camofox is **not installed** (no
binary, no package, no `CAMOFOX_URL`). Its module requires a **separate Docker container**
(`docker run -p 9377:9377 jo-inc/camofox-browser`) + `CAMOFOX_URL` env — i.e. deploy a new
containerized browser backend, then switch engines, then validate the survey site on
Firefox. Real infrastructure. And it still only persists **login**, not the live page.

**Verification outcome — recommend A.** C is a large lift (Docker service + engine switch +
site validation) for a login-only guarantee; B needs runtime changes we don't own; **A** is
config + standard infra (a dedicated Xvfb display) and preserves the *full* live state, which
also makes the "is the survey resumable by cookie vs URL" question **moot** (the page is never
torn down). Survey URLs weren't extractable from logs, but A doesn't need that answer.

## Open decisions for Anthony (architecture — needs your call)
"Do both" (headed Chromium + persistent Chromium profile) is **not achievable via config**
— Hermes doesn't pass `--profile` to agent-browser (Option B). So the real fork is **A vs C**:

1. **A — keep Chromium, `browser.headed: true`, on a dedicated display.**
   - Full live state (login + exact survey page).
   - Requires installing **Xvfb + x11vnc** and running James on **`:1`** (not the human's
     `:0`) so his visible browser can't interfere with Anthony's desktop, and Xvfb avoids
     the fragile physical session. Also set `browser.inactivity_timeout: 3600` and a
     `DISPLAY=:1` for the runtime (currently unset).
   - Cost: extra moving parts (virtual display + VNC), surveys depend on that display.
2. **C — switch to Camofox, `camofox.managed_persistence: true`.**
   - Fully headless → no display, no interference, nothing to "leave on."
   - Cost: different browser engine (Firefox) — must be validated on the survey site;
     bigger architectural change; unknown stealth/behaviour vs the current Chromium runs.
3. **My read:** if surveys need exact-page continuity → A (with the Xvfb isolation). If
   login-persistence is enough and we want to kill the display dependency entirely → C.
   This is a genuine architecture choice — needs your call, not "simplest."

### Verify next (I can, read-only, no service touches)
- Whether the OpinionMilesClub survey resumes from cookies/login alone (→ C viable) or
  needs the exact live page (→ favors A).
- Whether Camofox is installed/working in this runtime before committing to C.

## Acceptance
- Across a multi-message survey, James keeps the **same logged-in browser** — no
  re-login per message; the survey advances past question 1 to completion.
- The browser is **not** torn down between turns (verify: no per-turn `cleanup_browser`
  for the task; browser process persists across replies).
- Session is not reaped during normal multi-minute gaps between user messages.
- (Acceptance requires a real survey run, which only Anthony can trigger — per CLAUDE.md,
  Claude will not message James or inject messages.)

## Key Files
- `~/.hermes/profiles/simplifyops/config.yaml` — add `browser:` section (`headed`,
  `inactivity_timeout`).
- Runtime (read-only reference): `agent/chat_completion_helpers.py:2183-2197`
  (per-turn cleanup hook), `tools/browser_tool.py:892-919` (`_is_headed_mode`),
  `tools/browser_tool.py` `_cleanup_inactive_browser_sessions` (idle reaper).
- For Option B: agent-browser `--restore` / `user_data_dir`; state in `~/.agent-browser/`.

## Notes
- Root cause confirmed from runtime code on 2026-08-12 (not docs). External standard
  from browser-use / Steel / Playwright. Bug log: `/home/pi/survey-attempt-bugs.md`.
- Investigation was paused briefly for the concurrent 2-gateway 409 incident; this
  story is unaffected (morning attempt ran on the durable gateway, single session id).
- Recommend a `graphify` graph check before implementation per repo convention; this
  story is grounded in direct first-hand reading of the runtime source.
