# Story 42 - Schemathesis API gate

## Status
**Parked 2026-09-02 by owner** — moved to `product/stories/parking-lot/`. Revisit when the admin
API surface is larger / more churny and property-based contract testing earns its keep.

## Scope (when resumed)
Run Schemathesis against the admin OpenAPI schema as a quality gate:
- read-only / safe operations against normal data;
- write/stateful coverage against an **isolated disposable database** (never the live DB);
- report validation errors, response-shape mismatches, edge cases, and server errors;
- wire into CI as its own gate (label as a known gap until enforced).

Ref: `plan-architecture/agents-whitelabel-instructions.md` §"Runtime and API gate"; blueprint P1.

## Why parked
Needs infra (a running app instance + a disposable DB) to add real value, and the current admin API
is small and stable. Lower ROI than the config/Settings/soul work. No blockers — resume anytime.
