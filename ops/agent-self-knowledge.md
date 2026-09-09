# Self-knowledge generator — operating procedure

`scripts/build_agent_self_knowledge.py` deterministically assembles James's self-knowledge document
from allowlisted source sections (story-64 Phase B).

## Commands
```bash
python3 scripts/build_agent_self_knowledge.py generate   # write the output
python3 scripts/build_agent_self_knowledge.py check       # nonzero if missing/stale (CI-enforced)
```

## Files
- **Allowlist:** `knowledge/about-myself/sources.md` — `## Output` (exactly one path) + `## Sources`
  (each `### <repo-relative path>` with a `Reason:` and a `Sections:` list of exact headings).
- **Source content:** e.g. `knowledge/about-myself/capabilities.md` (reviewed, non-secret).
- **Output (generated, tracked, do NOT hand-edit):**
  `knowledge/about-myself/generated/self-knowledge.md` — `minimum_authority: admin`.

## To change what James knows about himself
1. Edit the source doc(s) and/or `sources.md`.
2. `generate`, review the diff, `check`.
3. Commit sources **and** the regenerated output together (CI runs `check`).

## Guarantees / limits
- Deterministic, stdlib only, no LLM/network. A named section extracts the heading's body up to the
  next heading of equal/higher level; a missing or empty section **fails** (never falls back to the
  whole file).
- Source paths are validated: no absolute/traversal paths, and a denylist blocks env/config/auth/
  session/audit/infra locations. Extracts and final output are secret-scanned.
- The generated doc is admin-level; the runtime (Phase C) discloses it only to admin/super_admin and
  gives others a public capability summary.
- The generated file is **not** auto-imported into the knowledge DB — it's a runtime-context input,
  separate from the admin knowledge store.
