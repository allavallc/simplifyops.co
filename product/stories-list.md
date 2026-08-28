# Stories — Prioritized Backlog (whitelabel blueprint adoption)

Prioritized, **selective/incremental** adoption of the genericized whitelabel blueprint
(`~/Desktop/architecture/agents-whitelabel.md`) for **simplifyops / James**. Covers the *entire*
document: every blueprint area is mapped to a story below (done, pending, new, or parked).

**Whitelabel mapping:** `<agent name>` → **James**; `agent_runtime` → `simplifyops_runtime`;
`agent_brain` (governance DB) → `whitelist_app`; `agent-soul` → `souls/james-bott.md`; reuse existing
names where they exist. **Defaults (approved):** keep current `gateway`+`hermes_client` (no runtime-bridge
yet); **skip Docker** (native/systemd); **MCP work needs Anthony** (CLAUDE.md).

**Flags:** 🔴 needs Anthony/owner sign-off · ⚠️ touches live/shared infra (rule 8) · 🧱 large/multi-part.
**Status:** ✅ done · ▶ pending (has full story) · ✎ new (needs full story before impl).

---

## ✅ Already done / aligned (blueprint core we already have)
One governed message path, `POST /messages` intake, DB-backed people/identity governance, durable
`work_items` + `request_id` + `channel_events` idempotency, audit, worker → **`hermes_client` adapter**
(strict runtime boundary), logical/physical session mapping, Telegram adapter, two DBs
(`whitelist_app` + `hindsight`), protected architecture invariants, `product/stories/`,
env-owned gitignored `config.yaml`, brooks + ruff + pytest gates.
**Completed stories (archive):** 25 (retire React), 26 (gateway split), 27 (settings dedup),
28 (repo-local logging), 29 (remove people-whitelist), 31 (People page core), 33 (Hermes 0.20.5),
35 (slim main.py).

---

## P0 — Process & governance foundation (do first; governs all later work)
| ID | Title | Blueprint area | Scope | Deps |
|----|----|----|----|----|
| 36 ✎ | Product-decisions folder | Product folder model | Create `product/product-decisions/` (`current-architecture.md` [from `ops/`], `architecture-decisions.md` dated log, `agent-actions.md`, `mcp-setup-and-status.md`); make it the durable decision home | — |
| 37 ✎ | Tracked story summaries + proposals | Product summaries/proposals | `product/stories-list.md`(this)/`stories-archive.md`/`stories-parkinglot.md`/`stories-proposals.md` + `scripts/sync_story_summaries.py` (generate/check); governed `proposal<N>` model | 36 |
| 38 ✎ | Feature-dev process + push checks | Feature flow, CI/pre-push | `product/agent-feature-dev-process.md` (branch/worktree, `local/test-*`, progress line), `scripts/agent_pre_push_check.sh` + `agent_post_push_check.sh`, gitignored `ops/INFRASTRUCTURE.md` | — |
| 39 ✎ | Align AGENTS.md to blueprint rules | Agent-governance rules | Fold in ask-first, plan-before-slice, gate order (Brooks→ruff→pytest→…), product-model + coordination rules; reconcile with existing rules 1–11 | 36,37,38 |

## P1 — Quality gates + core architecture gaps (fit now)
| ID | Title | Blueprint area | Scope | Deps |
|----|----|----|----|----|
| 40 ✎ | Expand ruff rule set | Quality gates | Ruff families `E,F,I,UP,B` @100/py3.11 (currently `E9,F,I`); fix resulting findings repo-wide | — |
| 41 ✎ | CI workflow | CI & pre-push | `.github/workflows`: ruff + pytest + safe service checks (no Docker → systemd/health checks). Mark uncovered gates as **known gaps** | 40 |
| 42 ✎ | Schemathesis API gate | Runtime/API gate | Schemathesis vs admin OpenAPI: read-only safe + disposable-DB write coverage | 40 |
| 43 ✎ 🧱 | Provider-neutral contracts pkg | Contracts / dependency direction | `simplifyops_contracts/`: settings, logging context, runtime msg/response, tool context, identity/workspace values — **no** FastAPI/MCP/provider imports | — |
| 44 ✎ ⚠️ | Config ownership + editor | Config ownership | Tracked `hermes/config.base.yaml` template + env-owned `config.yaml` + copy rules; `runtime_config.py` metadata pull/check/allowlisted-apply; **supersedes/absorbs [[story-34]]** (per-env editor, secrets presence-only) | 43 |
| 45 ✎ 🧱 | Settings page to spec | Settings | Existing **[[story-32]]** — rebuild all sections, remove UI-only shells, field-save lifecycle + audit; Provider/Model drives 44 | 44 |
| 46 ✎ 🧱 | Soul/skills/knowledge + self-knowledge | Identity/soul/skills/knowledge | Restructure `souls/james-bott.md` → `soul/` + `knowledge/` + `governance/` policy dir; `scripts/build_agent_self_knowledge.py` (generate/check) + `knowledge/about-myself/sources.md`; authority-filtered | 43 |
| 47 ✎ | Migrations + schema_init | Persistence/schema | `migrations/` + `admin_api/schema_init.py` replacing schema-on-startup; forward-only, repair-safe, backup-on-apply | — |
| 48 ⏸ 🧱 | Companies + company-access | People/companies model | **PARKED 2026-08-27** (see [[stories-parkinglot]]) — do the rest of P1 first, come back later. `companies`, `person_company_access`, `identity_claims` schema + shared service + admin UI; completes People spec (the deferred [[story-31]] follow-up) | 47 |
| 49 ✅ | Boundary-contract docs | Boundary contracts | `plan-architecture/feature-details-if-needed/durable-message-workflow.md`, `plan-architecture/feature-details-if-needed/channel-message-tracking.md`, `docs/mcp/agent-mcp-master-doc.md` — document each boundary per the contract checklist (build-spec docs relocated to `plan-architecture/` 2026-08-27; MCP doc kept in `docs/mcp/` per law) | 36 |
| 50 ✅ | Hermes upgrade protocol | Runtime upgrade | `plan-architecture/feature-details-if-needed/update-hermes-protocol-2026-08-27.md` (master, rewritten to our stack) + AGENTS.md/decisions-log updates; patch script **deferred** (no current patches — see [[stories-parkinglot]]); formalizes the 0.19→0.20.5 run + [[hermes-upgrade-pin-workflow]] | — |

## P2 — Larger restructures (own planning; sequence after P0/P1)
| ID | Title | Blueprint area | Scope | Deps |
|----|----|----|----|----|
| 51 ✎ 🧱 ⚠️ | Runtime plane package | Runtime composition/supervisor | `simplifyops_runtime/` + supervisor (project-scoped `HERMES_HOME`, config/soul copy, child processes) + private `/runtime/messages` bridge (:8090); migrate gateway/worker under it | 43 |
| 52 ✎ 🧱 | Runtime contracts + bridge split | Runtime handoff | `contracts.py`, `message_bridge.py`, `message_context.py`, `session_context.py` typed handoff; strict metadata, URL-safe session IDs | 51 |
| 53 ✎ 🧱 | Automations lifecycle | Automations/scheduled work | `automation_worker` + `ops/cron-jobs-automations.md` A-to-Z (schedule/tz/owner/notify/retry/overlap/pause/status/audit) + admin UI + `cron_bridge` | 51 |
| 54 ✎ 🧱 | Channel adapters | Channels & delivery | Add email, Discord, Google Chat, phone/meeting adapters — each on the same durable request/work/gateway/worker/outbound model | 51 |
| 55 ✎ 🔴🧱 | Repo-owned MCP connectors | MCP & connectors | `connectors/` (client→service→FastMCP server) replacing third-party google-workspace-mcp; `docs/mcp/`; injected-client tests. **Needs Anthony** | 43 |
| 56 ✎ 🔴 | Deferred-tools runtime policy | Strict runtime boundary | `runtime_tool_policy=deferred_tools` (`tool_search`/`tool_describe`/`tool_call` only) + scope guards. **Needs Anthony** (MCP) | 55 |
| 57 ✎ | Runtime diagnostics + MCP health | Runtime operations | `mcp_health.py`, `runtime_diagnostics.py`, prompt/provider/tool diagnostics toggles (content-free) | 51 |

## P3 — Deferred / parking lot
| ID | Title | Blueprint area | Scope | Deps |
|----|----|----|----|----|
| 30 ▶ ⚠️ | Local→staging→prod envs | Deployment profiles | Existing **[[story-30]]** — wire staging (GitHub) vs prod split + deploy verification (post-push source/hash/health) | 38 |
| 58 ✎ | Failure/rollback runbooks | Failure/rollback/repair | Document repair runbooks + deployment-drift verification + reversible DB-op policy (most state-machine behavior already exists in `work_items`) | — |
| — 🅿️ | Docker profile | Deployment (Docker) | `Dockerfile.admin`/`Dockerfile.hermes`/compose — **parked** (owner: skip Docker; native/systemd only). Revisit only if reproducible-topology need arises | — |

---

## Coverage map (entire blueprint → status)
- Agent-governance rules, product model, feature flow, handoffs → **36–39** · Gates order/CI/Schemathesis → **40–42, 50** · Acceptance-test lifecycle → practice enforced by 39/41
- System topology, invariants, one governed path, governance-before-runtime, durable work → **✅ have**
- Boundary contracts → documented in **49**; runtime bridge realized in **51–52**
- Component/file map & dependency direction → contracts **43**, runtime pkg **51**, connectors **55**
- Identity/soul/skills/knowledge/self-knowledge → **46** · Channels/outbound → **✅ Telegram**, more in **54**
- Automations → **53** · Product folder model → **36–37** · Hermes runtime+upgrade → **✅ 33**, protocol **50**
- Graphify workflow → **✅ in use** (add `.graphifyignore` safety check under **41/50**)
- Config/secret ownership → **44** · Rebuild order (13 steps) → distributed across P0–P2 above
- Deployment (native/docker/staging/prod) → native **✅**, staging **30**, Docker **parked**
- Quality/testing/release gates → **40–42**, CI **41**, pre/post-push **38** · Failure/rollback → **58**
- Whitelabel checklist & source-of-truth map → satisfied by **36** (decisions) + this list

_Next new-story number: **60** (59 = renumbered legacy Google-OAuth story, story-37). Full story
files are written when a story is picked up (stories-first)._
