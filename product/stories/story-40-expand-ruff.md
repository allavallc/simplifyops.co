# Story 40 - Expand ruff rule set to E, F, I, UP, B

## Status
**Done (branch `story-40-expand-ruff`).** P1 of the blueprint adoption backlog.

## Goal
Adopt the blueprint's ruff families (`E, F, I, UP, B` @ line-length 100) up from the lean
`E9, F, I` baseline, and fix the genuine findings.

## What was done
- `pyproject.toml` `[tool.ruff.lint]`: `select = ["E","F","I","UP","B"]`.
- **FastAPI DI allowlist** — `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls` for
  `Depends/Query/Path/Body/Form/File/Header/Cookie/Security`, killing 32 **B008** false positives
  (`Depends(require_admin)` in route signatures is call-in-default by design).
- **Documented idiom ignores** (deviation from strict E-family, noted in pyproject): `E501`
  (long inline SQL/f-strings), `E701`/`E702` (the compact `if g := _guard(request): return g` guard
  one-liners across page routes).
- **Fixed the genuine findings:** UP017 (2, auto — `datetime.UTC`); E402 (16 — moved `main.py`
  `logging.basicConfig` below the imports); B904 (11 — added `from e` / `from None` to raises inside
  except blocks in `admin_people.py`, `people_service.py`, `admin_memories.py`, `settings.py`).

## Acceptance
- Full ruff clean under the expanded rule set; behavior-preserving; admin app imports (69 routes);
  full pytest green. Merged to `main` after the gate.

## Review
142 raw findings → adopted families with a FastAPI allowlist + 3 documented idiom ignores, then fixed
the 29 genuine ones (E402/B904/UP017). Full ruff **All checks passed**, pytest 9/9, admin imports OK
(import-order + exception-chaining changes only, no behavior change). No 🔴. **Done.**
