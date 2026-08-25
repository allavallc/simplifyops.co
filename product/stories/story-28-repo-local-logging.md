# Story 28 - Replace the host-wide `pi_logging` import with a repo-local logging module

## Status
**Proposed.** Addresses the R5 undeclared-dependency 🟡 finding from the 2026-08-22 architecture
audit. Decision: owner, 2026-08-22 — **logging is per-repo, not machine-wide.**

## Problem
`gateway/gateway.py:48` does `from pi_logging import get_logger`, but `pi_logging` is
**`/home/pi/pi_logging.py`** — a host-global module in the pi's home directory, shared across
unrelated projects and picked up only because the systemd unit runs from there. It is **not** in the
repo and **not** declared in `requirements-dev.txt`/`pyproject.toml`, so a fresh checkout or CI
cannot import the gateway, and the logger's behavior is invisible to the repo. Logging should be
owned by this repo, not by the machine.

## Proposed approach
1. Add a repo-local logging module, e.g. `gateway/logging_setup.py` (or a shared
   `simplifyops` logging helper if admin_api later needs the same), exposing the same
   `get_logger(name, stderr=True)` interface the gateway already uses.
2. Port the behavior from `/home/pi/pi_logging.py` (31 lines: `logging` + `logging.handlers`) —
   confirm the handler/format/rotation and replicate exactly so log output is unchanged.
3. Repoint `gateway.py` (and any other importer) at the repo-local module; delete the
   `pi_logging` import.
4. Do **not** delete `/home/pi/pi_logging.py` — it may be used by other repos on the box; this
   story only decouples *this* repo from it.

## Acceptance
- No repo module imports a host-global path; `python -c "import gateway.gateway"` (or equivalent)
  resolves purely from the repo + declared deps.
- Log output (destination, format, level) is unchanged from the current `pi_logging` behavior.
- Gate: `brooks-review` + `brooks-audit` clean, then focused + full `ruff`/`pytest`, on a
  `story-28-…` work branch (rule 10).

## Review
_(fill before commit/push: brooks-review + brooks-audit scores/Criticals, then focused + full
ruff/pytest green.)_

## Notes
Coordinate with [[story-26-decompose-gateway-module]] (both edit gateway imports).
