## Stack Setup Guide

For a full explanation of how the James stack works (Hermes, Hindsight, the Telegram gateway, profiles, secrets, and service startup order), read:

**`plan/james-stack-setup.md`**

Start there before making any changes to this system.

---

## Hermes Gateway — Known Issues & Fixes

### codex_runtime.py — SDK TypeError on get_final_response() (2026-05-26)

**Symptom:** `hermes-gateway.service` crashes in a restart loop. Journal shows:
```
error_type=TypeError ... summary='NoneType' object is not iterable
provider=openai-codex  model=gpt-5.3-codex
```

**Cause:** The OpenAI SDK's `stream.get_final_response()` returns `output=None` instead of `output=[]` when the Codex backend streams items via events. The existing backfill patch only guarded against an empty list, so `None` fell through and caused the TypeError downstream.

**Fix:** Edit `/home/pi/.hermes/hermes-agent/agent/codex_runtime.py`:

1. In `run_codex_stream()` — wrap `get_final_response()` in a `try/except TypeError` so a `None` final_response is caught, then widen the backfill condition from `isinstance(_out, list) and not _out` to `not _out` (covers both `None` and `[]`). If `final_response` is `None`, synthesize a `SimpleNamespace` from `collected_output_items` or `_codex_streamed_text_parts`.

2. Same widened condition (`not _out`) in `run_codex_create_stream_fallback()`.

**Warning:** `hermes update` overwrites `codex_runtime.py` and regenerates the service file. After any Hermes update you must:
- Re-apply the patch above
- Re-add `EnvironmentFile=/home/pi/.config/relay.env` to `/etc/systemd/system/hermes-gateway.service` (hermes strips it on reinstall)
- Run `sudo systemctl daemon-reload && sudo systemctl restart hermes-gateway.service`

---

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
