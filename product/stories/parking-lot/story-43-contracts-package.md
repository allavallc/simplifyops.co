# Story 43 - Provider-neutral contracts package

## Status
**Parked 2026-09-04 by owner** — premature abstraction for our scale.

## Scope (when resumed)
A `simplifyops_contracts/` package holding settings, logging context, runtime message/response values,
tool context, and identity/workspace value types — with **no** FastAPI/MCP/provider imports — so the
control plane, runtime, and connectors share typed boundary contracts (blueprint dependency direction).

## Why parked
A separate contracts package earns its keep when multiple packages/services need to share typed
contracts without import cycles. Today it's essentially one control plane (`admin_api`) + a gateway,
and the boundaries that matter are already clean seams: `gateway/hermes_client.py` (runtime adapter),
`admin_api/runtime_config.py`, `admin_api/people_service.py`, `admin_api/soul_file.py`. Extracting a
contracts package now would be indirection with no consumer — against CLAUDE.md "minimal code / no
short-term fixes". Revisit when the runtime plane is split out (P2 [[story-51]]/[[story-52]]) or a
second service needs the shared types.
