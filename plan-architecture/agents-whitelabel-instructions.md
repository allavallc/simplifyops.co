# Agent Context and Reconstruction Guide - Whitelabel Project

> This file has two jobs: it defines the operating rules for an AI agent working
> on this repository, and it documents the architecture that another team can
> rebuild under a different name, provider, channel set, or deployment target.
>
> The first sections are reusable agent-governance rules. The implementation
> blueprint later in this file is the current Agent Brain reference
> implementation. When adapting it to a new project, preserve the invariants
> and boundary contracts, then replace project-specific names, paths, policy,
> providers, and deployment settings.

## Instructions For Updating This Document

This section is for the next agent or next document revision. Treat this file as
a living reconstruction guide. Update it from verified repository evidence; do
not update it from memory, assumptions, or a stale prior version.

Before editing:

1. Read the repository's active `AGENTS.md` and any applicable product or
   architecture instructions.
2. Read `product/handoff.md` when it exists and confirm that the current task is
   consistent with the handoff. If it is missing, continue from the current
   request and repository state.
3. Read `graphify-out/GRAPH_REPORT.md` and compare its recorded commit with the
   current Git `HEAD`.
4. Use Graphify queries for orientation, then inspect the actual source files,
   tests, configuration templates, and authoritative docs before writing claims.
5. Check `git status --short --untracked-files=all` and preserve unrelated user
   changes. Never use this document as permission to overwrite another file.
6. Identify what changed since the last update and classify each fact as an
   invariant, current implementation, operational procedure, deployment
   adapter, or known gap.

When editing:

- Preserve the reusable agent-governance rules at the beginning of the file.
- Keep project-specific implementation detail in the reconstruction blueprint.
- Describe complete lifecycles, not isolated buttons, routes, commands, or
  modules. Include ownership, persistence, reads, updates, retries, duplicate
  behavior, audit, status, testing, deployment, rollback, and repair where the
  subject has those concerns.
- Update the product-folder lifecycle, Hermes upgrade protocol, Graphify process,
  quality gates, deployment profiles, and source-of-truth map whenever any of
  those systems change.
- Link to the authoritative source file or test for every important claim. Do
  not copy large blocks of implementation that will drift.
- Mark policy that is not automated as a known gap. Do not describe a required
  gate as CI-enforced unless the current workflow actually runs it.
- Keep deployment instructions portable. Separate architecture from Docker,
  native process management, cloud hosting, and provider-specific adapters.
- Preserve the distinction between tracked structural files and environment-owned
  secrets/configuration. Never add secret values, OAuth material, tokens, raw
  environment files, provider auth, session state, audit logs, or live database
  data.
- Do not force-add this ignored whitelabel file or generated Graphify output to
  Git unless the user explicitly requests that change.

After editing:

1. Re-read the changed sections for contradictions with `AGENTS.md`, product
   decisions, current architecture, tests, and deployment procedures.
2. Verify every referenced path, route, command, environment variable, and
   external URL. Remove stale paths rather than preserving them as facts.
3. If source or architecture files changed, refresh Graphify:

   ```bash
   graphify update . --force
   ```

4. Run the Graphify safety check and confirm that generated output contains no
   secret-bearing or local-runtime paths:

   ```bash
   rg -n "hermes/projects|auth\.json|\.env|channels/.*\.yaml|governance/audit|ops/snapshots" \
     graphify-out/GRAPH_REPORT.md graphify-out/graph.json graphify-out/manifest.json
   ```

   The check must return no matches. Never use unsafe generated output as
   context or commit it.
5. For Markdown-only edits, perform a document/path/link sanity check. For any
   code, configuration, schema, or runtime change, run the repository's full
   quality and runtime gates before calling the update complete.
6. Report the document sections changed, evidence inspected, validation run,
   Graphify status, and any unresolved drift or known gap.

When whitelabeling this guide for another project, copy the generic rules and
this update procedure first. Then replace the project-specific blueprint,
identities, paths, providers, databases, channels, product workflow, deployment
profiles, and tests. Do not copy <agent name>'s identity, users, credentials, memory,
runtime state, or infrastructure details.

## Ask Questions

- Ask questions before acting whenever instructions, ownership, user-facing
  behavior, file movement, deployment impact, data, config, OAuth, credentials,
  or safety boundaries are ambiguous.
- Do not guess when a wrong assumption could break staging, production, user
  data, config, channels, runtime behavior, or the agent's behavior.

## Research Requirement

- Ground non-trivial plans and code-change suggestions in repo/source
  inspection and official documentation when available.
- Use online research when suggesting externally dependent technical choices,
  provider behavior, API behavior, dependencies, deploy practices, or anything
  likely to have changed.
- If web access is unavailable, say so explicitly and do not present the
  suggestion as fully researched.

## Infrastructure

- Keep project, VM, IP, SSH, deploy, and environment setup details in a local
  gitignored infrastructure file such as `ops/INFRASTRUCTURE.md`.
- Read that file before deploy work.
- Never print or commit secrets, `.env` contents, OAuth material, tokens,
  provider auth files, channel secret files, session cookies, or expanded config.

## Core Rules

- **All changes require explicit approval** - do not write, edit, move, or delete
  any file until the user has approved the plan or directly instructed the
  change. Discussion is not authorization.
- **Plan the whole feature before slicing work** - plans must cover the complete
  user-facing and runtime lifecycle before implementation begins. A valid plan
  covers data ownership, save/edit/read/run paths, background work, retries,
  duplicate/overlap behavior, logging, audit, status surfaces, tests, local
  verification, staging verification, and rollback or repair behavior.
- **Implementation work starts from latest staging** - use a dedicated feature
  branch or worktree based on the latest `origin/staging` for feature, bug fix,
  cleanup, non-Markdown docs, and multi-file implementation work.
- **Markdown-only work may stay in the main checkout** - creating or editing
  Markdown files can happen in the main local checkout after explicit approval.
  If the change includes both Markdown and implementation files, use the normal
  feature branch/worktree process.
- **Never reuse permanent story or proposal numbers** - once a story or proposal
  number is created, completed, committed, abandoned, rejected, parked, or
  archived, it is permanently consumed.
- **Coordinate before commit, merge, or push** - ask whether another agent is
  active. If yes, collect branch/worktree path, changed files, pushed/unpushed
  status, and test status, then compare overlapping files before proceeding.
- **Local before staging** - do not deploy or propose staging verification for
  user-facing behavior until local Docker/browser or channel verification passes.
- **Do not touch production without explicit instruction** - staging is the
  default deployment target unless the user explicitly says otherwise.
- **Commit code and tests together** - implementation, templates, routes,
  services, and tests for the same behavior must ship in the same commit.
- **Run required tests before code commits** - run the repo's full required test
  command before committing code. Markdown-only changes do not need full code
  tests unless the repo's process says otherwise.
- **Do not perform destructive data/config actions** - never drop, wipe,
  recreate, reset, or overwrite a database or live config without explicit,
  repeated permission when risk is high.

## Story Files

- Full story files live only in the main local checkout under
  `product/stories/`.
- Completed, rejected, superseded, or abandoned story files move to
  `product/stories/archive/`.
- Parked or deferred story files move to `product/stories/parking-lot/` if the
  project uses that folder.
- Do not recreate, copy, or add missing full story files inside implementation
  worktrees. Stories are planning/reference instructions, not implementation
  artifacts.
- When choosing a new story number, check active stories, archived stories, and
  parked stories, find the highest existing number, and use the next number.
- If the user approves editing a story, edit it in the main checkout only.
- Do not bundle full story-file changes into implementation commits unless the
  project explicitly uses tracked full story files.

## Product Summaries And Proposals

Use compact tracked product summary files so the agent can understand product
state without ingesting full local story files:

- `product/stories-list.md` - active/open planned stories.
- `product/stories-archive.md` - completed, rejected, superseded, abandoned, or
  otherwise archived stories and proposal outcomes.
- `product/stories-parkinglot.md` - parked or deferred stories.
- `product/stories-proposals.md` - active agent-created proposals awaiting human
  review.

Rules:

- Full story files are local planning artifacts for humans and implementation
  agents.
- Tracked summary files are the compact product surface exposed to hosted tools
  or the runtime agent.
- The runtime agent may create proposal records only through a governed
  product-planning tool with a narrow write target.
- The runtime agent must not create official story files, archive stories, edit
  full story files, or edit summary files unless a specific governed tool and
  product decision allow it.
- A human or local implementation agent promotes accepted proposals into normal
  numbered stories.
- Proposal writes should use permanent `proposal<N>` numbering and never reuse
  proposal IDs.
- When promoting a proposal, create a numbered story, reference the originating
  proposal, remove or mark the active proposal row, and record the outcome in
  `product/stories-archive.md`.
- Update `product/stories-list.md`, `product/stories-archive.md`, and
  `product/stories-parkinglot.md` only during cleanup, after the final
  active/archive/parked state is known.
- During cleanup after stories are created, archived, unarchived, parked, or
  materially changed, run the repo's summary generator/check command, for
  example:

```bash
python3 scripts/sync_story_summaries.py generate
python3 scripts/sync_story_summaries.py check
```

## Feature Development Flow

Use a separate process document such as `product/agent-feature-dev-process.md`
for exact local commands. The default flow is:

1. Fetch latest `origin/staging`.
2. Create a dedicated feature branch or worktree.
3. Read required repo context and architecture decisions.
4. Confirm the plan and get explicit approval before edits.
5. Implement in the feature branch/worktree.
6. Run focused checks, then full required checks before code commit.
7. Commit locally on the feature branch.
8. Test user-facing behavior from the main checkout on a disposable
   `local/test-<story-or-feature>` branch.
9. Get user confirmation from local Docker/browser or channel testing.
10. Fetch and compare against `origin/staging`.
11. Run the repo's pre-push report.
12. Show the final commit list and get push approval.
13. Push to `origin/staging`.
14. Watch CI/deploy to completion.
15. Verify staging health and smoke tests.
16. After user confirms staging, clean up worktrees/branches and archive the
    story.

## Local Docker And Runtime Testing

- Run Docker user testing from the main checkout unless the user explicitly
  approves an isolated feature-worktree stack.
- Before starting Docker, check current services and host ports to avoid
  collisions.
- Do not run commands that print fully resolved environment/config values.
- Use safe checks such as `docker compose ps`, `docker compose config --services`,
  targeted health checks, and non-secret presence checks.
- UI changes require local Docker/browser confirmation before commit.

## Product And Architecture Decisions

- Durable product and architecture decisions live under
  `product/product-decisions/`.
- Before suggesting or changing channels, runtime, config, memory, governance,
  tool access, user-facing workflow, or high-level product behavior, read the
  relevant product-decision files.
- New durable architecture or high-level product decisions should be recorded in
  product-decision docs, not buried only in stories, handoff notes, or chat.

## Agent-Operable Data

If a feature creates data the runtime agent can see, reference, rely on, or act
on, the story must define the agent's access level:

- none
- read-only
- owner-scoped write
- admin-only
- super-admin-only

Expose governed tool/API paths for the lifecycle operations allowed at that
access level: create, read, update, run, archive/deactivate, and field-level
changes as relevant. Reuse the same service, validation, authorization, and
audit logging as admin surfaces. Do not create broad `change_anything` tools.
Prefer deactivate/archive/close states over hard delete.

## Handoffs And Runtime Boundaries

Any handoff between the app, runtime, model gateway, channel, connector, or
automation must define the exact boundary contract before code changes:

- caller
- callee
- route, CLI, or API surface
- input schema
- output schema
- persisted state
- transient state
- required identifiers
- idempotency key
- timeout
- retry behavior
- credential owner
- user-visible delivery owner
- status mapping
- audit/log fields
- secret-redaction rules

Do not rely on prompts, implied context, filename conventions, or model
inference for data the system already knows.

## Channels And Durable Work

User-facing channels should use one durable controlled path:

```text
channel adapter/webhook
  -> create or preserve request ID
  -> provider-event claim / idempotency state
  -> gateway durable intake
  -> work item
  -> worker-owned governance and safety
  -> runtime handoff only when allowed
  -> reply-ready or outbound-send stage
  -> channel provider send
  -> completion/audit/timing
```

Do not enable direct channel-to-runtime paths that bypass governance, durable
work state, request IDs, audit logging, or outbound send ownership. Channel
adapters should not wait inline for final runtime replies as the normal path.
Runtime, provider, and network timeouts are attempt-level outcomes on the same
work item.

## Admin, Governance, And Audit

- Admin work must include audit logging for who acted, when, target object,
  environment, request metadata when available, and a non-secret before/after
  summary.
- Never log OAuth tokens, session cookies, API keys, secrets, raw `.env`, or
  fully expanded runtime config.
- Governance records should be database-backed unless a project-specific
  decision says otherwise.
- Do not reintroduce file-based allowlists when the project has moved to
  database-backed governance.

## MCP And Connector Work

- Keep connector rules in `docs/mcp/` and connector-specific docs.
- Before touching a connector, read the connector's source-of-truth doc, auth
  setup, test pattern, and current tool inventory.
- Use injected clients/fakes in tests instead of live provider calls.
- Do not restore legacy direct runtime skill paths when repo-owned connectors
  are the approved integration path.

## Handoff Notes

- Use `product/handoff.md` only for session shutdown or explicit handoff.
- Do not update handoff notes merely because a feature finished, tests passed,
  a deploy completed, or a story was archived.
- Completion belongs in git history, story archive notes, deployment records, or
  chat unless the user asks for a handoff.

## Cleanup Checklist

After work is shipped, CI/deploy passes, and user staging verification is
confirmed:

1. Remove the feature worktree.
2. Delete the local feature branch.
3. Delete the disposable `local/test-*` branch.
4. Leave other agents' branches and worktrees alone.
5. Move completed/rejected/superseded/abandoned stories to archive.
6. Regenerate/check product summary files.
7. Commit and push cleanup if the summaries are tracked.
8. Confirm the main checkout is clean and matches `origin/staging`.

## Old Mistakes To Avoid

- Do not commit or print secrets, tokens, OAuth files, provider auth files,
  channel secret files, audit logs, snapshots, or expanded config.
- Do not let tracked config templates overwrite staging or production operator
  choices.
- Do not bypass governed request, work item, audit, or outbound delivery paths.
- Do not hard-delete governed user/work objects unless a product decision
  explicitly approves hard delete.
- Do not create broad tools that bypass typed services, validation,
  authorization, persistence, and audit.
- Do not let short-term implementation notes become the only source of durable
  architecture truth.

# Implementation Blueprint

## Purpose

This project is a governed agent system, not only a chatbot. It combines:

- a control plane for operators and durable governance data;
- a runtime plane that gives one agent an identity, memory, skills, tools, and
  sessions;
- channel adapters that normalize external messages;
- a durable request/work workflow that survives slow providers and restarts;
- an MCP integration layer for typed tools;
- operational procedures for upgrades, testing, deployment, and repair.

The rebuild target is behaviorally equivalent to this architecture. Individual
frameworks may change, but the ownership boundaries, identifiers, authorization
rules, audit trail, and failure semantics must remain explicit.

## How To Read This Document

Every statement should be understood as one of these:

- **Invariant** — must remain true in every deployment and implementation.
- **Current implementation** — the live Agent Brain file or module that provides
  the behavior today.
- **Operational procedure** — how an agent or operator performs a change.
- **Deployment adapter** — one way to run the same architecture, such as Docker.
- **Known gap** — a policy or intended gate that is not yet fully automated.

The source code and tests are authoritative for behavior. Product decisions are
authoritative for durable architectural intent. This document is a navigable
reconstruction guide, not a replacement for either source.

## System Topology

The architecture has three major internal planes and three trust boundaries.

```text
                         operators / approved users
                                  |
                         admin UI and HTTP API
                                  |
                         +--------v---------+
                         |   Control plane  |
                         | auth, governance |
                         | config, audit    |
                         +--------+---------+
                                  |
external channels                 | approved handoff
email / Telegram / Discord /      |
Google Chat / phone / web         v
        |                  +------+-------+
        +----------------->| Agent Gateway| POST /messages
                           | request_id  |
                           | work_items  |
                           +------+-------+
                                  |
                          worker-owned stages
                                  v
                           +------+-------+
                           | Governance  |
                           | safety      |
                           | audit       |
                           +------+-------+
                                  |
                         private runtime bridge
                         POST /runtime/messages
                                  v
                           +------+-------+
                           | Hermes      |
                           | Agent       |
                           | soul/skills |
                           | sessions    |
                           +---+------+--+
                               |      |
                         memory       MCP tools
                               |      |
                         +-----v------+-----+
                         | Hindsight /      |
                         | repo connectors  |
                         +------------------+
                                  |
                         reply_ready / send
                                  v
                           original channel
```

Trust boundaries:

1. **Inside the project** — control plane, runtime, soul, skills, knowledge,
   governance, audit, and persistence.
2. **Trusted external services** — selected model provider, self-hosted
   Hindsight, Google APIs, and any approved data gateway.
3. **Untrusted or semi-trusted inputs** — public channels, provider webhooks,
   external users, third-party systems, and the open web.

The control plane must never be bypassed by a new channel. The runtime must
never receive an ungoverned user message. An MCP tool must never become a
second hidden path around authorization, persistence, or audit.

## Non-Negotiable Architecture Invariants

### One governed message path

Every user-facing request follows this logical path:

```text
channel adapter or webhook
  -> create or preserve requests.id
  -> claim provider event / idempotency state
  -> POST /messages
  -> durable work_items row
  -> worker claim
  -> people governance and safety
  -> private Hermes runtime handoff when allowed
  -> reply_ready persistence
  -> channel-owned outbound send
  -> completed, retryable failure, or review state
  -> audit and timing records
```

The provider message ID is not the internal workflow identity. The same internal
`request_id` must connect gateway intake, work item, governance, runtime attempt,
reply, outbound send, audit, and timing records. Provider IDs and Hermes session
IDs remain separate fields.

Channel adapters may parse provider events, claim idempotency, create a request,
and enqueue work. They must not wait inline for Hermes to produce the final
reply. A provider or runtime timeout is an attempt result on the same work item,
not permission to create a disconnected duplicate request.

### Governance before runtime

The gateway resolves the sender against database-backed people and identities,
then applies conversation and safety policy. `can_converse` determines whether
<agent name> may respond. `can_influence` determines whether the exchange may shape
memory. Unknown or unauthorized inputs fail closed or enter the approved contact
request path.

Hermes provides runtime/tool security. Agent Brain provides business identity,
company access, communication policy, action approval, and audit history.

### Durable work and idempotency

Long-running work is represented in Postgres before runtime execution. Workers
claim rows using transactional locking, preserve attempt identity, and move work
through explicit states. Duplicate provider events and duplicate clicks must be
safe. Outbound delivery must be idempotent or have a durable send record that
prevents a second reply.

### Strict runtime boundary

The only Agent Brain-to-Hermes user-message handoff is the private runtime
bridge, currently `POST /runtime/messages`. The bridge receives explicit
metadata; it must not infer person IDs, channels, request IDs, timezones,
automation IDs, or notification policy from prompt wording or filenames.

When `runtime_tool_policy=deferred_tools` is active, the model receives only the
three bridge operations `tool_search`, `tool_describe`, and `tool_call`. Hermes
session scope remains authoritative for which underlying tools are searchable
and callable. Disabled, excluded, ungranted, or unavailable tools stay
inaccessible.

### Database ownership

The same Postgres server may host separate databases, but ownership remains
separate:

- `agent_brain` — people, identities, companies, company access, contact
  requests, request IDs, work items, channel-event claims, audit/timing state,
  and other Agent Brain governance or workflow data.
- `hindsight` — Hindsight memory internals only.

Never place Agent Brain governance tables in Hindsight's database. Never use
memory state as a substitute for authorization or workflow state.

### Configuration ownership

Tracked structural defaults and environment-owned runtime choices are different:

- `hermes/config.base.yaml` is the tracked structural template.
- `hermes/config.yaml` is environment-owned and gitignored.
- `HERMES_HOME` is project-scoped; the global Hermes profile is not used.
- provider credentials, OAuth material, channel secrets, and session state are
  stored outside tracked source.

The supervisor creates missing runtime config from the base template and copies
the authoritative repo config and soul into the project-scoped Hermes home.
Routine provider/model/operator choices must not be committed as structural
config changes.

## Component and File Map

| Area | Current implementation | Responsibility |
| --- | --- | --- |
| Admin composition root | `admin_api/main.py` | FastAPI app, static files, public health, `/messages`, request logging |
| Admin routes/UI | `admin_api/routes/`, `admin_api/templates/`, `admin_api/static/` | Authenticated control plane and operator workflows |
| Governance | `admin_api/people.py`, `admin_api/safety.py`, `admin_api/gateway.py` | Identity resolution, authority, conversation/action decisions, safety |
| Gateway | `admin_api/gateway.py`, `admin_api/gateway_types.py` | Normalize message contracts, attach context, hand off or enqueue |
| Durable workflow | `admin_api/work_items.py` | Work item persistence, claims, stage/status transitions, retry state |
| Request correlation | `admin_api/request_ids.py`, `admin_api/channel_events.py` | Internal request IDs and provider-event idempotency |
| Audit/timing | `admin_api/audit.py`, `admin_api/job_timings.py` | Non-secret audit events and request timing records |
| Runtime composition | `agent_runtime/app.py` | Thin FastAPI composition root and router inclusion |
| Runtime contracts | `agent_runtime/contracts.py` | Runtime request/response models and typed boundary values |
| Runtime handoff | `agent_runtime/message_bridge.py`, `message_context.py`, `session_context.py` | Hermes API-server handoff, context, logical/physical session mapping |
| Runtime process supervisor | `agent_runtime/supervisor.py` | Project home setup and runtime subprocess lifecycle |
| Workflow worker | `agent_runtime/workflow_worker.py` | Claim work, run governance/runtime stages, persist reply/status |
| Automation worker | `agent_runtime/automation_worker.py` | Scheduled runs, attempts, output capture, notifications |
| Channel adapters | `agent_runtime/*_adapter.py` | Provider intake, normalization, gateway submission, outbound delivery |
| Automation bridge | `agent_runtime/cron_bridge.py`, `cron_notifications.py`, `routes/cron.py` | Hermes cron/automation boundary and notification classification |
| Runtime operations | `agent_runtime/hermes_tools.py`, `mcp_health.py`, `runtime_config.py`, `runtime_diagnostics.py` | Tool settings, MCP checks, diagnostics, and runtime operations |
| Provider-neutral contracts | `agent_brain_contracts/` | Settings, logging, runtime context, tool context, Google Workspace values |
| MCP connectors | `connectors/` | Local stdio MCP servers and typed provider/service layers |
| Identity and behavior | `soul/`, `skills/`, `knowledge/` | <agent name>'s identity, reusable skills, curated knowledge and self-knowledge |
| Runtime config | `hermes/config.base.yaml` | Provider/model structure and MCP server registrations |
| Governance policy | `governance/` | Communication and company-access rules |
| Schema/bootstrap | `migrations/`, `admin_api/schema_init.py` | Database schema and compatibility initialization |
| Operations | `scripts/`, `ops/`, `docs/` | Deployment, snapshots, upgrades, smoke tests, process rules |

The composition roots are deliberately small. Runtime message handling must not
import cron operations, Hermes tool settings, or MCP health surfaces. Contracts
must not import FastAPI, MCP server code, provider clients, admin routes, or
runtime workers.

The dependency direction is:

```text
routes / adapters
  -> application services and workers
    -> typed contracts and stores
      -> external clients / persistence
```

Shared contracts may be imported inward. Low-level contracts must not import
application packages merely to reuse a convenience helper.

## Boundary Contracts

Every boundary in a rebuild must document the following before implementation:

- caller and callee;
- route, CLI, or process entry point;
- input schema and output schema;
- persisted state versus transient state;
- required identifiers and the canonical `request_id`;
- idempotency key and duplicate behavior;
- timeout and retry behavior;
- credential owner;
- user-visible delivery owner;
- status mapping;
- audit and log fields;
- secret-redaction rules.

### Admin API to gateway

`POST /messages` is the canonical Agent Brain gateway boundary. It accepts a
normalized message payload with channel, sender, provider references, thread
references, request correlation, attachments, and any explicitly resolved
identity/context fields. It returns a structured result containing the request
ID, governance/runtime status, optional reply, and work-item status.

The route delegates to `handle_gateway_message()`; business decisions do not
belong in the FastAPI route itself.

### Gateway to durable workflow

For work that may take more than a short request/response interval, the gateway
creates or updates one `work_items` row. The worker owns governance, safety,
runtime handoff, reply persistence, outbound sending, retry classification, and
completion. Work items must retain the original payload needed to retry without
losing the request ID or provider correlation.

### Gateway to Hermes runtime

`POST /runtime/messages` receives a typed runtime message containing, as
applicable:

- channel and sender identity;
- request ID and runtime attempt ID;
- person, authority, company, email, calendar identity, and timezone;
- subject, message/thread references, and normalized text;
- attachment/image metadata and content where approved;
- Discord or other channel context;
- automation and run IDs;
- the explicit governance decision.

The response contains a status, optional reply, routing metadata, and bounded
timing/usage metadata. The runtime does not own channel delivery.

### Runtime to Hermes sessions

Human-readable logical IDs may contain provider data such as `/`, but URL path
segments must use a URL-safe physical Hermes session ID. The mapping persists
logical session ID, physical Hermes session ID, channel, person, sender, thread,
and rotation reason. Raw provider thread references remain metadata, not route
path segments.

### MCP boundary

Each MCP connector has a client/service/server separation:

```text
Hermes MCP client
  -> local stdio MCP server
    -> typed connector service
      -> injected provider client
        -> provider API
```

The MCP server exposes narrow typed tools. The service owns validation and
business behavior. The client owns provider HTTP/auth details. Tests inject
fake clients rather than calling live providers. Agent Brain-owned data tools
reuse shared stores, authorization, validation, and audit logging.

MCP is a tool transport and discovery boundary; it does not replace request
tracking, governance, audit, or outbound delivery. The official MCP model
distinguishes model-controlled tools from application-controlled resources and
user-controlled prompts: <https://modelcontextprotocol.io/specification/2025-06-18/server/index>.

## Identity, Soul, Skills, and Knowledge

The runtime's behavioral identity is composed from separate concerns:

- `soul/agent-soul.md` — canonical identity and values.
- `skills/` — repo-owned reusable capabilities and operating instructions.
- `knowledge/` — curated reference material, indexes, and domain knowledge.
- `knowledge/about-myself/sources.md` — allowlisted inputs to the generated
  self-knowledge file.
- `knowledge/about-myself/generated/agent-self-knowledge.md` — generated output;
  never edit it by hand.
- Hermes-native capabilities — framework-provided tools and skills, subject to
  the configured runtime/tool policy.

Self-knowledge is authority-filtered. Approved non-admin users may receive only
high-level capability context. Setup, architecture, credential, and operational
details are reserved for authorized administrators. No secret, raw config,
OAuth material, token, audit log, or code-line implementation detail belongs in
runtime self-knowledge.

After changing architecture/capability source documents or the source list:

```bash
python3 scripts/build_agent_self_knowledge.py generate
python3 scripts/build_agent_self_knowledge.py check
```

## Channels and Outbound Delivery

Current channel adapters include email, Telegram, Discord, and Google Chat, with
additional phone/meeting surfaces in the runtime and admin routes. Each adapter
must:

1. parse provider input;
2. preserve or create the agent-owned request ID;
3. claim the provider event where applicable;
4. submit the normalized payload to `POST /messages`;
5. return quickly to the provider polling/webhook loop;
6. let the durable worker own long-running runtime work;
7. send only the reply that belongs to the original work item;
8. record outbound status, provider reference, request ID, and non-secret timing.

Inbound and proactive Google Workspace capability are separate concerns. For
example, Gmail inbound polling/replies belong to the channel adapter, while
proactive search/read/send operations belong to the Gmail MCP connector. They
may share approved credentials but must not share an uncontrolled execution
path.

## Automations and Scheduled Work

Automations require an A-to-Z lifecycle, not only a cron command. The design must
cover:

- create/save and edit;
- stored schedule, timezone, prompt, owner, notification policy, and state;
- execution identity and tool context;
- Hermes run handoff;
- output capture and bounded summaries;
- notification decision and outbound delivery;
- last-run status and operator logs;
- audit events;
- retries and maximum attempts;
- duplicate clicks and overlapping runs;
- paused jobs;
- failed, skipped, partial, and late runs;
- local tests and staging smoke tests.

The detailed current contract is [ops/cron-jobs-automations.md](ops/cron-jobs-automations.md).
The automation worker owns execution state. Hermes must not send owner/status
notifications directly when Agent Brain owns notification policy and delivery.

## Product Folder Operating Model

The `product/` tree is part of the system's operating model. It separates
durable decisions, planning detail, runtime-visible summaries, and session
continuity.

### Product decisions

`product/product-decisions/` contains durable product and architecture decisions.
Use it for changes to channels, runtime, configuration ownership, memory,
governance, tool access, data ownership, or other system-wide behavior. The key
files are:

- `current-architecture.md` — concise current-state architecture;
- `architecture-decisions.md` — dated decision log and rationale;
- `agent-actions.md` — governed action decisions;
- `mcp-setup-and-status.md` — MCP status and setup decisions.

Do not hide durable architecture decisions only in a story, handoff, or TODO.

### Full stories

Full planning stories live under `product/stories/` in the main checkout. They
are local planning/reference artifacts, not implementation artifacts. Do not
copy or recreate them in feature worktrees.

When creating a story:

1. inspect both `product/stories/` and `product/stories/archive/`;
2. find the highest existing story number;
3. use the next number permanently;
4. write the whole end-to-end lifecycle before implementation;
5. include data ownership, save/edit/read/run, background work, retries,
   duplicates/overlaps, logging, audit, status surfaces, tests, local and
   staging verification, and rollback/repair;
6. reference any originating proposal.

Story numbers are never reused, including for abandoned or rejected stories.

### Tracked summaries and proposals

The four tracked summaries are the compact product surface available to <agent name> and
GitHub-facing tools:

- `product/stories-list.md` — active/open stories;
- `product/stories-archive.md` — completed, rejected, superseded, or abandoned
  stories and proposal outcomes;
- `product/stories-parkinglot.md` — parked/deferred work;
- `product/stories-proposals.md` — active agent-created proposals.

The `agent-product` connector may write only a proposal record to
`product/stories-proposals.md`, normally by a direct commit to the configured
proposal branch. Proposal IDs use permanent `proposal<N>` numbering based on
active proposals and proposal history; they are never reused.

When promoting a proposal:

1. create a normal numbered story in the main checkout;
2. reference the originating proposal;
3. remove or mark the active proposal;
4. record the outcome in `product/stories-archive.md`;
5. leave summary cleanup until the final story state is known.

After stories are created, archived, unarchived, parked, or materially changed:

```bash
python3 scripts/sync_story_summaries.py generate
python3 scripts/sync_story_summaries.py check
```

Do not hand-edit generated summaries when the sync tool is the source of truth.

### Feature branches and cleanup

Implementation starts from the latest `origin/staging` in a dedicated branch or
worktree. The story remains in the main checkout. User-facing local Docker tests
normally run from a disposable `local/test-*` branch in the main checkout.

Before commit, merge, or push, coordinate with any other active AI agent and
compare overlapping files. After staging deploy verification and user testing,
remove the feature worktree/branch and disposable local branch, then perform
final story summary cleanup.

`product/handoff.md` is not a general status file. Update it only when the user
explicitly requests session shutdown or a handoff.

## Hermes Runtime and Upgrade Protocol

Hermes is the agent runtime. Agent Brain owns the governance and integration
boundary around it; Hermes owns post-approval model interaction, session
continuity, and tool planning.

### Runtime startup

`agent_runtime/supervisor.py`:

1. resolves the project-scoped `HERMES_HOME`;
2. creates missing runtime config from `hermes/config.base.yaml`;
3. copies repo `hermes/config.yaml` into the Hermes project home;
4. copies `soul/agent-soul.md` to `SOUL.md`;
5. disables/archives legacy direct Google Workspace skill/auth paths;
6. writes the Hindsight plugin configuration;
7. starts Hermes Gateway;
8. starts enabled channel adapters;
9. starts the durable workflow worker;
10. starts the automation worker;
11. starts the private runtime FastAPI bridge on port `8090`;
12. terminates child processes together on shutdown.

The current supervisor starts these process modules: Hermes Gateway, Telegram,
email, workflow worker, automation worker, Discord, Google Chat, and the runtime
Uvicorn bridge. A native process manager may replace the supervisor, but it must
preserve the same process ownership, shutdown behavior, project-scoped home,
and configuration copy rules.

### Upgrade procedure

Use [docs/update-hermes-protocol.md](docs/update-hermes-protocol.md) before and
after every Hermes upgrade:

1. choose the environment and maintenance window;
2. capture a non-secret healthy-state snapshot;
3. inspect the current pinned `HERMES_AGENT_REF` in `Dockerfile.hermes`;
4. consult the official Hermes documentation and release/source changes;
5. update the pinned ref deliberately;
6. rebuild the runtime artifact;
7. let `scripts/apply_hermes_runtime_patches.py` apply, accept already-upstream
   fixes, or fail loudly when Hermes source layout changed;
8. run patch idempotency/layout tests;
9. confirm project-scoped `HERMES_HOME`, copied soul, config ownership, MCP
   registrations, and Hindsight wiring;
10. run focused and full automated checks;
11. run the governed `/messages` smoke test;
12. inspect bounded runtime logs and health endpoints;
13. perform the human smoke test through the intended channel;
14. capture and compare a post-upgrade snapshot;
15. retain the prior ref and artifact information for rollback.

Never use the global `~/.hermes` profile, commit `hermes/config.yaml`, or allow
an update to replace environment-owned configuration with generated defaults.
The official Hermes documentation is the external runtime reference:
<https://hermes-agent.nousresearch.com/docs/>.

### Runtime patches

Runtime patches are compatibility and observability controls, not a second
application runtime. The patch script currently protects areas including:

- OpenAI Codex compatibility;
- prompt/provider diagnostics;
- MCP tool-call diagnostics;
- tool execution diagnostics;
- deferred tool filtering;
- enabled/granted tool catalog search;
- tool-call scope guards;
- web-crawl restrictions;
- automation completion notification hooks.

Patch behavior must be marker-based, idempotent, tested against known layouts,
and fail closed when the installed Hermes source layout is unknown. A patch must
never silently change provider selection, expose a disabled tool, print a secret,
or bypass the Agent Brain gateway.

## Graphify Architecture Discovery

Graphify is agent-local working context. It helps an agent navigate the codebase
and understand relationships; <agent name> runtime does not depend on it.

### Required workflow

Before proposing a plan or architecture change:

1. read `graphify-out/GRAPH_REPORT.md`;
2. compare its recorded commit with `git rev-parse HEAD`;
3. use `graphify query`, `graphify path`, or `graphify explain` for orientation;
4. inspect the actual source files and tests before treating a relationship as
   authoritative.

After structural code or architecture-document changes:

```bash
graphify update . --force
```

Then verify that generated output did not include local/runtime/secret-bearing
paths:

```bash
rg -n "hermes/projects|auth\.json|\.env|channels/.*\.yaml|governance/audit|ops/snapshots" \
  graphify-out/GRAPH_REPORT.md graphify-out/graph.json graphify-out/manifest.json
```

That command must return no matches. Maintain `.graphifyignore` so it excludes
`.env*`, channel secret files, `hermes/config.yaml`, Hermes project state,
OAuth/provider auth files, audit logs, and snapshots. If unsafe paths appear,
repair the ignore rules, regenerate the graph, and do not use or share the
unsafe output.

Generated Graphify files remain ignored and must not be committed unless the
user explicitly asks for them. Graphify is never a substitute for source code,
tests, product decisions, or runtime health checks. A stale or inferred graph
edge must be verified against the live file.

## Configuration and Secret Ownership

The rebuild must separate these categories:

### Tracked structural files

- `pyproject.toml` and `uv.lock`;
- `hermes/config.base.yaml`;
- `soul/`, `skills/`, `knowledge/`, `governance/`;
- source code, migrations, tests, non-secret docs, and design assets;
- scripts and manifests that enforce safe operations.

### Environment-owned files and values

- `.env` and `.env.*`;
- `hermes/config.yaml`;
- `hermes/projects/agent-brain/` state;
- `channels/*.yaml` and `channels/*.secret.yaml`;
- OAuth/provider auth files;
- session cookies, API keys, tokens, audit logs, and runtime snapshots;
- infrastructure inventory such as `ops/INFRASTRUCTURE.md`.

Use presence checks instead of printing values. Structural Hermes changes use
the metadata-only pull/check and narrowly allowlisted apply process in
`scripts/runtime_config.py`. Never use a plain `docker compose config` command
when it could expand secrets; use `docker compose config --services` and other
bounded checks.

## Rebuild Order From an Empty Repository

The following order minimizes hidden coupling while preserving the full
lifecycle.

### 1. Establish governance and source-of-truth rules

Create the agent policy, decision log, product lifecycle, secret exclusions,
Graphify exclusions, coding rules, and deployment ownership rules before writing
runtime code.

### 2. Establish the Python project

Create `pyproject.toml`, lock dependencies with `uv.lock`, define Python 3.11+
compatibility, and separate runtime dependencies from development dependencies.
Use native project environments with `uv sync` and `uv run`; `uv` documents the
lockfile/environment model at <https://docs.astral.sh/uv/guides/projects/>.

### 3. Establish persistence

Provision Postgres and create two databases with distinct ownership. Add schema
migrations/bootstrap for governance, requests, work items, channel claims,
people, identities, company access, audit, timing, automation, and session
mapping. Provision Hindsight separately with its own database and vector
extension. Hindsight supports Docker and bare-metal installation with external
PostgreSQL; see <https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/installation.md>.

### 4. Establish provider-neutral contracts

Create the contracts package first. Define settings, logging context, runtime
message/response values, tool context, identity values, and external-client
protocols without importing the application, web framework, MCP framework, or
provider clients.

### 5. Build the control plane

Implement admin authentication, people/identity/company stores, contact-request
review, audit logging, settings/config ownership, health checks, and the plain
FastAPI/Jinja admin panel. Every durable admin form needs create/save, edit,
read-back, archive/deactivate where applicable, and persisted-field acceptance
coverage.

### 6. Build the gateway and durable work bucket

Implement request creation/preservation, provider-event idempotency, normalized
gateway payloads, work-item persistence/claims, stage transitions, retry/review
states, timing, and audit. Test duplicate events, retry attempts, late runtime
results, and outbound-send deduplication before adding more channels.

### 7. Build the Hermes runtime bridge

Implement the private `/runtime/messages` route, typed runtime contracts, strict
context handoff, safe physical session IDs, mapping/rotation, timeout behavior,
and runtime response classification. Add the supervisor only after the bridge
works independently in tests.

### 8. Add soul, skills, knowledge, and self-knowledge

Add the canonical soul, custom skills, curated knowledge index, allowlisted
self-knowledge generator, and authority-filtered capability context. Verify
that generated context cannot disclose secrets or implementation-only details.

### 9. Add MCP connectors

Implement each connector as client → service → FastMCP server, register it in
`hermes/config.base.yaml`, and add injected-client tests. Keep Google Workspace
connectors provider-agnostic with respect to the admin application and use the
repo-owned auth/context contracts.

### 10. Add channels and delivery

Implement one adapter at a time, but require every adapter to use the same
request/work/gateway/worker/outbound model. Add provider event claims, thread
continuity, attachment handling, provider retry behavior, outbound ownership,
and channel-specific smoke tests.

### 11. Add automations

Implement save/edit/archive/run-once, schedule parsing/timezones, owner and
notification policy, execution records, output capture, retry/overlap handling,
status surfaces, audit, and outbound notification through the A-to-Z contract.

### 12. Add operational tooling

Add health snapshots, runtime config metadata checks, migration/repair tools,
bounded logs, deployment verification, Graphify refresh instructions, and
Hermes upgrade safeguards. Do not treat Docker commands as the only operational
interface.

### 13. Apply quality gates and release

Run the full quality sequence below. Test native execution and the optional
container profile against the same contracts and acceptance criteria.

## Deployment Profiles

Docker is optional. It is a packaging and process-orchestration adapter, not an
architectural dependency.

### Native profile

The native profile requires:

- Python 3.11+ and `uv`;
- a persistent Postgres server with the required databases/extensions;
- a separately running self-hosted Hindsight API;
- a pinned Hermes installation compatible with the patch script;
- a process manager for the admin API, Hermes/runtime bridge, adapters, and
  workers;
- persistent project-scoped Hermes state and audit/workflow storage;
- environment variables and secret files supplied by the host secret manager;
- a reverse proxy or equivalent TLS boundary for public HTTP surfaces.

The native process commands are deployment-specific, but the logical process
map is:

```text
admin_api.main:app                         admin API / control plane
agent_runtime.supervisor                   Hermes + adapters + workers + bridge
agent_runtime.workflow_worker              durable request worker
agent_runtime.automation_worker            automation worker
hindsight-api                              self-hosted memory API
postgres                                   governance/workflow + memory storage
```

If the supervisor owns the worker children, do not also launch duplicate worker
processes from the host process manager. Use environment URLs that point to
localhost, Unix sockets, or service DNS as appropriate; application code must
not require Docker service names.

### Docker profile

The current Docker Compose profile packages the same logical components as
`admin-api`, `agent-brain`, `hindsight`, `postgres`, `postgres-init`, and the
optional web-search service. `Dockerfile.admin` builds the control plane.
`Dockerfile.hermes` installs a pinned Hermes ref, applies runtime patches, and
starts `agent_runtime.supervisor`.

Docker is useful for reproducible local/staging topology and user-facing local
testing. It must not be the only place where contracts, migrations, health
checks, or process ownership are defined. FastAPI's deployment guidance treats
containers as one deployment strategy among several:
<https://fastapi.tiangolo.com/deployment/>.

### Staging and production

Staging is the default deployment target for this project. Production requires
separate explicit authorization. Each environment owns its own secrets,
runtime config, database, channel ownership, and public URL. In particular,
staging and production must not both consume the same live inbound email or
Telegram channel.

Do not prove deployment only from VM Git metadata. Verify the deployed commit
stamp, source hashes, image/container files, Compose status, health endpoint,
and the exact runtime artifact used by the deploy workflow.

## Quality, Testing, and Release Gates

### Required order

Use this ordered sequence for implementation readiness:

```text
Brooks Audit > Focused Ruff > Focused Pytest > Full Ruff > Full Pytest
  > Local Docker build/health > Schemathesis API gate > User smoke test
  > Pre-push report > Commit/push
```

The current process and progress-line convention live in
`product/agent-feature-dev-process.md`.

### Brooks Audit

Brooks is the architecture gate. It evaluates module dependencies, layering,
structural decay, testability seams, and ownership boundaries. Run it before
focusing on line-level test failures when the change affects architecture,
routes, runtime boundaries, connectors, or data ownership.

Brooks audit mode is diagnostic only. It must not edit files, create history or
suppression files, apply remedies, or mutate the database. The report should
show the module graph first, then findings and recommended remedies.

### Focused Ruff and pytest

Run Ruff on touched files/directories first, then the relevant test modules:

```bash
uv run ruff check admin_api/gateway.py agent_runtime/message_bridge.py
uv run pytest tests/test_gateway_runtime_client.py tests/test_runtime_bridge.py -q
```

Use the actual changed paths and corresponding tests. Do not skip tests because
the change appears to be documentation-adjacent if code or runtime behavior was
touched.

### Full Ruff and pytest

Before a code commit, run the complete repository checks:

```bash
uv run ruff check .
uv run pytest
```

This repository configures Ruff in `pyproject.toml` with a 100-character line
length, Python 3.11 target, and `E`, `F`, `I`, `UP`, and `B` rule families. Pytest
discovers `tests/` with quiet output and automatic asyncio mode. Ruff's official
`ruff check` supports both directory and file-targeted linting:
<https://docs.astral.sh/ruff/linter/>. Pytest's official command reference
covers file, test-name, keyword, and marker selection:
<https://docs.pytest.org/en/stable/how-to/usage.html>.

The repository's isolated-check environment may use:

```bash
UV_PROJECT_ENVIRONMENT=/tmp/agent-brain-uv-env \
UV_CACHE_DIR=/tmp/uv-cache \
uv run pytest
```

Adapt the temporary paths for a different project; never put secrets in them.

### Runtime and API gate

After automated checks, rebuild or start the selected local runtime profile and
verify:

- admin health;
- private runtime health;
- Hindsight reachability and database ownership;
- project-scoped Hermes home;
- soul/config copy behavior;
- MCP server health and tool scope;
- one governed `/messages` request;
- one blocked/unauthorized request;
- one retry or review classification where relevant;
- one outbound or reply-ready path where relevant.

Schemathesis exercises the live OpenAPI contract for validation errors, response
shape, edge cases, and server errors. Use read-only/safe operations against
normal data; use an isolated disposable database for write/stateful coverage.
Its CI/CD guide supports running against a live schema and producing reports:
<https://schemathesis.readthedocs.io/en/stable/guides/cicd/>.

### Acceptance tests

Any UI, API, governed tool, or durable workflow that creates or edits data needs
full lifecycle acceptance coverage:

1. create/new;
2. save and persist every field;
3. read back every field through the owning service/runtime contract;
4. display every field correctly;
5. edit/update;
6. archive/deactivate, or delete only when explicitly approved;
7. audit actor, timestamp, target, environment, and non-secret before/after.

Provider integrations use injected fakes. Connector tests cover auth refresh,
request URL/method/headers/body, service delegation, missing-auth failure, and
non-secret logging. Database tests must not point at Agent Brain's normal local
database when they create or mutate test data.

### CI and pre-push reporting

The current CI workflow runs dependency setup, Ruff, pytest, and safe Compose
service validation. It should be kept aligned with the process policy; if a
gate is described here but not automated in CI, label it as a known gap rather
than implying enforcement.

Before merge or push:

```bash
bash scripts/agent_pre_push_check.sh
```

Immediately before pushing, fetch `origin/staging`, compare divergence, inspect
other-agent worktrees, rerun required checks, and show the final commit list.
After pushing, run:

```bash
bash scripts/agent_post_push_check.sh <commit-sha>
```

Verify both GitHub's deploy result and the runtime's actual deployed source,
container hashes, Compose status, and health response.

## Failure, Rollback, and Repair

Failures must preserve the durable object and its audit trail:

- provider/runtime timeout → retryable or review state on the same work item;
- repeated failure → bounded attempts and `failed_needs_review` or equivalent;
- late runtime result → attach to the original request/work item when possible;
- duplicate inbound event → provider-event claim prevents duplicate work;
- duplicate outbound attempt → durable send identity prevents a second reply;
- stale worker claim → lease/lock expiry and safe reclaim;
- overlapping automation → explicit skip, coalesce, or queued policy;
- paused automation → no new execution, clear status;
- failed migration/config apply → preserve backup and do not continue silently;
- Hermes layout change → fail the build and require patch review;
- deployment drift → compare snapshot/source/container state and repair before
  accepting traffic.

Never repair by dropping, wiping, recreating, or silently backfilling a database.
Database operations require explicit approval and a reversible runbook. Never
discard a reply because an HTTP caller timed out; resolve it through the same
request/work-item identity.

## Whitelabel Adaptation Checklist

For a new project, replace or confirm each item explicitly:

- project and agent name;
- canonical soul and behavioral policy;
- people/identity authority model;
- organization/company access model;
- communication and safety policy;
- channels and provider ownership;
- model/provider and Hermes version/ref;
- Hindsight deployment and memory banks;
- Postgres database names and migrations;
- MCP connector inventory and tool authorization;
- outbound delivery owner;
- request/work-item state machine;
- admin users and OAuth provider;
- public/private endpoints and TLS boundary;
- native process manager;
- optional container profile;
- local, CI, staging, and production environment differences;
- health checks, smoke tests, repair procedures, and rollback artifact;
- product story/decision/proposal workflow;
- Graphify ignore rules and refresh procedure.

Do not copy <agent name>'s soul, users, provider credentials, OAuth files, channel
secrets, runtime state, memory data, audit logs, or environment-specific
infrastructure into the new project. Copy the contracts and procedures, then
bootstrap new identity, storage, secrets, and policy.

## Source-of-Truth Map

Use these files in this order when rebuilding or reviewing the implementation:

1. `AGENTS.md` — active repository rules;
2. `graphify-out/GRAPH_REPORT.md` — current structural navigation context;
3. `product/product-decisions/current-architecture.md` — current architecture;
4. `product/product-decisions/architecture-decisions.md` — durable rationale;
5. `product/agent-feature-dev-process.md` — branch, testing, and cleanup process;
6. `docs/update-hermes-protocol.md` — Hermes upgrade/update procedure;
7. `ops/cron-jobs-automations.md` — automation lifecycle contract;
8. `docs/mcp/agent-mcp-master-doc.md` — MCP ownership and tool rules;
9. `ops/durable-message-workflow.md` — durable request/work semantics;
10. `ops/channel-message-tracking.md` — channel event and request correlation;
11. `README.md` and `SETUP.md` — human setup and current Docker-first workflow;
12. source modules and tests — exact implementation behavior.

When this blueprint and a live source file disagree, classify the disagreement
as drift, verify the intended behavior against product decisions and tests, then
update the appropriate durable source of truth. Do not silently make the
blueprint the authority by copying stale implementation detail.
