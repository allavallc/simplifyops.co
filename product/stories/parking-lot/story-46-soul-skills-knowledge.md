# Story 46 - Soul/skills/knowledge restructure + self-knowledge

## Status
**Parked 2026-09-04 by owner** — ahead of consumption. (The soul-file part was already carved out and
shipped as [[story-60]].)

## Scope (when resumed)
Restructure identity into `soul/` + `skills/` + `knowledge/` + a `governance/` policy dir, and add
`scripts/build_agent_self_knowledge.py` (generate/check) that builds an **authority-filtered**
`knowledge/about-myself/generated/agent-self-knowledge.md` from an allowlisted
`knowledge/about-myself/sources.md`.

## Why parked
Verified 2026-09-04: **nothing consumes it.** No `knowledge/` dir exists; `config.yaml` has no
skills/knowledge keys; the Hermes profile's `skills/` is a Hermes-native dir (not the repo `skills/`);
there is no runtime wiring that loads a repo `knowledge/` tree or a generated self-knowledge file. The
one identity input the runtime actually loads — the soul (`SOUL.md` → `souls/soul.md`) — is already
done ([[story-60]]). Building a knowledge tree + self-knowledge generator that nothing reads is
scaffolding (CLAUDE.md "minimal code / no short-term fixes").

## Prerequisite to resume
A runtime-side consumer: wiring `knowledge/` (and the generated self-knowledge, authority-filtered)
into the agent's context — part of the runtime-plane work (P2 [[story-51]]). Do 46 when that consumer
exists, so the generated docs are actually used.
