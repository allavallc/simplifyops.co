# Settings Page Build Story

This is the consolidated final-state build story for the `agent-brain` Settings
page. It replaces the need to copy many historical source-system stories into a
new implementation prompt.

Use this as a current build target, not as history. Story numbers are included
only as provenance so an implementation LLM knows which old source threads
informed the final state.

## Table Of Contents

1. [Source Story Provenance](#source-story-provenance)
2. [Goal](#goal)
3. [Key Decisions](#key-decisions)
4. [Config File, Not Env Var Sprawl](#config-file-not-env-var-sprawl)
5. [Required Settings Sections](#required-settings-sections)
6. [API Contract](#api-contract)
7. [Authorization And Audit](#authorization-and-audit)
8. [Persistence Ownership](#persistence-ownership)
9. [Working With Hermes](#working-with-hermes)
10. [Channel Rules](#channel-rules)
11. [Workspace Access Rules](#workspace-access-rules)
12. [Identity-File Upload Rules](#identity-file-upload-rules)
13. [Field-Save Standard](#field-save-standard)
14. [Key Mistakes To Avoid](#key-mistakes-to-avoid)
15. [Acceptance Tests](#acceptance-tests)
16. [Official Docs To Recheck](#official-docs-to-recheck)
17. [Build Order](#build-order)

## Source Story Provenance

The final state below synthesizes these story threads:

| Story | Final-State Use |
| --- | --- |
| Story 12 | Environment-owned runtime config and safe structural apply. |
| Story 40 | Identity-file upload/download and restart-after-upload behavior. |
| Story 41 | Channel-specific config fields and secret-reference handling. |
| Story 42 | Shared Workspace OAuth for direct-message chat where applicable. |
| Story 43 | Every editable field must save, persist, read back, display, and audit correctly. |
| Story 51 | Prompt diagnostics toggle and content-free diagnostics. |
| Story 53 | Historical diagnosis for Hermes session-history/token bloat and session-health rotation. |
| Story 57 | Workspace health/smoke checks through connector service paths. |
| Story 63 | Shared Workspace OAuth reliability risk from cloud-platform scopes. |
| Story 79 | Session cap UI and runtime rotation rationale. |
| Story 96 | Settings page organization and visual grouping. |
| Story 113 | Related Tools-page grouping for repo-owned toolsets. |
| Story 123 | Related Tools-page performance when loading editable tool data. |

Current code and current architecture/ops docs outrank all story text. If an old
story conflicts with this build story, treat the old story as historical
background.

## Goal

Build Settings as an API-first operator control surface:

- `<CONTROL_API>` owns auth, validation, persistence, audit, runtime
  coordination, and JSON contracts.
- `<ADMIN_CLIENT>` renders the browser UI from typed JSON APIs.
- The rebuild must not require server-rendered admin HTML.
- Runtime and channel behavior must match the source system's current
  boundaries, not old one-off setup states.

Settings is not a marketing page. It is an operational control surface for
admins who need to inspect health, change runtime settings, connect providers,
configure channels, verify Workspace access, and recover from runtime/config
drift.

## Key Decisions

- The Settings UI is API-first. Build typed JSON endpoints before the client.
- The UI may be one page with sections, one page with tabs, or a split
  Status/Settings flow. Preserve behavior, audit, and restart semantics.
- Settings and Tools are adjacent but distinct. Settings shows system, runtime,
  provider, channel, Workspace, identity-file, and admin-contact controls. Tools
  owns editable Hermes toolsets, MCP tool toggles, MCP health, and tool-data
  loading unless a later product decision merges them.
- Runtime provider/model/config choices are environment-owned. Tracked config
  templates are structural bootstrap only.
- Settings values drive environment-owned config files through typed services.
  `.env` is not the Settings store.
- If older source-system notes say the tracked runtime config file is the live
  source of truth, treat that as historical background. The rebuild target is
  live environment-owned runtime config plus a tracked structural base template.
- Channel non-secret settings are environment-owned per-channel config.
- Channel secrets live in environment-owned secret storage or secret files.
  Settings shows presence/status only.
- Provider API keys, device-code tokens, and OAuth refresh/access tokens belong
  in a credential/auth store or secret store. If the runtime requires provider
  values as environment variables at process start, materialize them privately
  from that store; do not make operators maintain a separate `.env` variable for
  every provider field.
- Blank secret fields preserve existing secret values when the UI says blank
  means "keep existing".
- Channel session caps are environment-owned channel settings with a built-in
  default fallback. Do not store them in Hermes config.
- Session-health thresholds are environment-owned runtime settings. They must be
  read and written through one shared settings service and applied before runtime
  handoff.
- The canonical identity file is `<SOUL_FILE>`. Runtime `<RUNTIME_HOME>/SOUL.md`
  is a materialized copy that updates only after restart/materialization.
- Shared Workspace OAuth is high-blast-radius runtime state because one grant
  can power mail, calendar, drive, docs, sheets, slides, tasks, meet, and chat.
- Provider health/smoke checks must use safe connector service paths and never
  print tokens, raw responses, `.env`, or expanded config.
- All settings mutations require non-secret audit with actor, target,
  environment, request metadata when available, before summary, and after
  summary.
- Destructive, disconnect, restart, provider switch, diagnostics save, and
  identity-file upload actions require typed confirmation.

## Config File, Not Env Var Sprawl

The Settings page should make operational config editable without turning every
field into a separate environment variable.

Use this rule:

- `.env` is for bootstrap, deployment wiring, service URLs, auth/session
  secrets, provider credential references, and values that must differ before
  the app can boot.
- Runtime settings changed by admins belong in the environment-owned runtime
  config file, written through one shared settings/config service.
- Channel settings changed by admins belong in environment-owned channel config
  files, written through channel-specific settings services.
- Secrets belong in secret storage or secret files. Settings shows presence and
  status only.
- Tracked templates provide non-secret structural defaults for fresh bootstrap.
  They must not become the live writable Settings target.
- If the live runtime config file is missing, Settings may read the tracked base
  template for read-only display or fresh bootstrap. The first Settings write
  must create/update the live environment config file; it must not mutate the
  tracked base template.

Examples of values that should be config-file-backed, not new `.env` variables:
active provider, active model, context length, prompt diagnostics state, session
health thresholds, channel enablement, channel public identifiers, processing
mode, process-after timestamp, provider-specific non-secret channel fields,
per-channel session cap, Workspace smoke-test resource IDs, document-workspace
settings, and admin contact selection when not stored in the app database.

Only add a new `.env` variable when the value is needed before config files can
be read, belongs to deployment/service wiring, or is a secret/reference that the
runtime must receive from the environment. The rebuild agent should be able to
change normal Settings values from the admin UI/API and then observe the same
values on the next read without editing `.env` or redeploying.

Config writers must use structured file parsing rather than text replacement.
They must preserve unrelated keys, keep YAML-equivalent existing values intact,
write atomically where practical, maintain restrictive permissions for secret
files, and emit audit/log output with paths, fields, hashes, sizes, or presence
status only. They must not print whole config files or fully resolved config.

## Required Settings Sections

Build these sections or equivalent tabs.

| Section | Required Contents |
| --- | --- |
| Health | Non-secret status for `<CONTROL_API>`, `<AGENT_RUNTIME>`, memory service, database, and important internal health checks. |
| Session Health | Channel message caps plus retained tool-result and rough session-token guardrails when supported. |
| File Locations | Presence/status for runtime home, runtime config, tracked config template, and `<SOUL_FILE>` without raw config or secrets. |
| Runtime Controls | Runtime restart/reload, prompt diagnostics toggle, restart-required notices, and safe status feedback. |
| Provider And Model | Provider connection state, active provider/model, optional context length, memory URL, API-key presence, connect/disconnect, and switch actions. |
| Channels | Per-channel enablement, public identifier, provider, processing mode, process-after timestamp, provider settings, secret presence, and session cap. |
| Workspace Access | Shared OAuth state, connected-account mismatch warning, connect/disconnect, calendar test, smoke config/status, and document-workspace validation. |
| Admin Contact | Primary and optional secondary operational contacts selected from active admin/super-admin people. |
| Tools Summary | Link/status for the Tools view and cached MCP health. Do not duplicate full tool editing unless intentionally merged. |

## API Contract

Define schemas that return only non-secret state. Do not make the browser infer
runtime truth from rendered text.

Minimum read endpoints:

- `GET /api/admin/settings/overview`
- `GET /api/admin/settings/runtime`
- `GET /api/admin/settings/providers`
- `GET /api/admin/settings/channels`
- `GET /api/admin/settings/workspace`
- `GET /api/admin/settings/admin-contact`
- `GET /api/admin/tools/summary`

Minimum mutation endpoints:

- `POST /api/admin/runtime/restart`
- `PATCH /api/admin/settings/runtime`
- `PATCH /api/admin/settings/session-health`
- `POST /api/admin/settings/identity-file/upload`
- `GET /api/admin/settings/identity-file/download`
- `PUT /api/admin/settings/providers/{provider_id}/credentials`
- `DELETE /api/admin/settings/providers/{provider_id}/credentials`
- `POST /api/admin/settings/runtime/provider`
- `PATCH /api/admin/settings/channels/{channel}`
- `DELETE /api/admin/settings/channels/{channel}`
- `POST /api/admin/settings/workspace/connect`
- `GET /api/admin/settings/workspace/callback`
- `DELETE /api/admin/settings/workspace/connection`
- `POST /api/admin/settings/workspace/calendar-test`
- `PUT /api/admin/settings/workspace/smoke-config`
- `POST /api/admin/settings/workspace/smoke-test`
- `PUT /api/admin/settings/workspace/document-workspace`
- `PUT /api/admin/settings/admin-contact`

If `<ADMIN_CLIENT>` is served from a different origin, configure explicit CORS
origins and credentials behavior. Do not use wildcard CORS for authenticated
admin requests.

## Authorization And Audit

Settings is an admin-only control surface.

Required authorization:

- all Settings read endpoints require an authenticated admin or super admin;
- runtime restart/reload, provider/model changes, provider connect/disconnect,
  prompt diagnostics, session-health settings, channel settings, Workspace
  connect/disconnect, smoke-test config, document-workspace config, and
  admin-contact saves require authenticated admin or super admin authority;
- identity-file upload/download requires super admin authority;
- any future Settings mutation exposed to the agent at runtime requires a
  separate product decision and a governed tool path. Settings mutation should
  otherwise remain human-admin owned.

Every accepted, rejected, failed, and no-op mutation must write non-secret audit
with actor, target, environment, request metadata when available, action type,
result, and before/after summary. Audit must redact raw runtime config,
`.env`, OAuth values, provider credentials, channel secrets, session cookies,
auth headers, prompt text, user text, and uploaded identity-file contents.

## Persistence Ownership

| Data | Source Of Truth |
| --- | --- |
| Runtime provider/model/context/memory config | Environment-owned runtime config file, written through the shared settings/config service. |
| Runtime structural defaults | Tracked template for fresh bootstrap only. |
| Provider credentials | Provider credential table, provider auth store, or secret store; Settings shows presence only and runtime injection is private. |
| Channel non-secret settings | Environment-owned channel config file, written through channel-specific settings services. |
| Channel secrets | Environment-owned secret storage or secret files. |
| Channel session caps | Environment-owned channel config with built-in fallback. |
| Session-health thresholds | Environment-owned runtime settings written through the shared settings service. |
| Identity file | `<SOUL_FILE>` canonical source. |
| Workspace smoke/document-workspace config | Environment-owned non-secret operational config. |
| Admin contact | App database or governed settings store. |
| Audit | App-owned non-secret audit store. |

Never let tracked templates overwrite environment-owned runtime or channel
config during startup or deploy. Never make routine Settings edits depend on
manual `.env` edits. Structural runtime config additions require an explicit,
allowlisted apply path with dry-run and backup behavior.

## Working With Hermes

Settings may coordinate Hermes, but it must not become a shadow runtime.

- Use supported Hermes API/runtime surfaces where they exist.
- Runtime restart/reload is explicit operator action or explicit API response
  behavior, not an invisible side effect.
- Provider/model saves that require reload must either request restart or return
  `restart_required=true`.
- Prompt diagnostics are diagnostics-only. They must not change prompts, model
  choices, tools, governance, routing, sessions, or replies.
- Prompt diagnostics may log counts and correlation fields only: provider/model,
  API message counts, prompt/token estimates, tool count/schema estimates,
  history counts, and timing.
- Prompt diagnostics must not log raw user text, prompt text, tool result
  contents, conversation history, tokens, secrets, auth headers, or raw config.
- Session caps rotate physical runtime sessions while preserving logical
  conversation continuity.
- Physical session rotation must preserve request ID, logical session ID,
  channel, sender/thread refs, person ID, mapping history, and rotation reason.
- Do not expose raw Hermes compression internals as normal Settings controls.
- Do not edit runtime-materialized identity/config files directly when the
  canonical source file/config has an owner.
- Do not follow old source notes that made tracked runtime config the writable
  live source. Write the live environment-owned config and keep tracked config as
  structural bootstrap only.

## Channel Rules

Build channel settings from channel-specific schemas, not a single generic
`value` field.

Required behavior:

- enabling/disabling a channel preserves unrelated saved values;
- channel public identifiers save to the channel-specific key that reads them
  back;
- processing modes are explicit for poll-based channels;
- `process_after` gates old inbound messages at cutover;
- provider-specific fields save under provider-specific config;
- any derived runtime-config sync for a channel is secondary to the
  channel-specific config file; the channel file remains the owner;
- blank secret/reference fields preserve existing values;
- secret status is presence-only;
- delete/disconnect actions require typed confirmation and audit;
- local, staging, and production must not process the same live inbox/feed at
  the same time unless a product decision explicitly supports shared ownership.

Provider IDs, message IDs, conversation IDs, OAuth account IDs, and channel
resource names are provider metadata. They are not internal request IDs and must
not be used raw as physical runtime session path segments.

## Workspace Access Rules

The shared Workspace OAuth connection is operationally sensitive. Treat it as a
single high-blast-radius dependency.

Required behavior:

- show connected/not-connected without revealing token values;
- show connected-account mismatch warnings;
- connect only when OAuth client settings are present;
- disconnect only with typed confirmation;
- reconnect is operator-owned, not automatic;
- use service-layer connector checks for smoke tests;
- report `ok`, `failed`, or `skipped_config_missing` per product;
- store optional smoke-test resource IDs in environment-owned non-secret config;
- never run live provider checks inside ordinary unit tests;
- avoid cloud-platform scopes in the shared user grant unless current source
  docs and operator policy explicitly allow them.

## Identity-File Upload Rules

Only super admins can upload a new identity file.

Required behavior:

- upload replaces exactly `<SOUL_FILE>`;
- uploaded filename never decides the destination path;
- valid files are UTF-8 Markdown/plain text, non-empty, below the configured
  size limit, and free of obvious secret-like material;
- invalid files are rejected before write;
- accepted writes are atomic where practical;
- upload and download never expose secrets through logs/audit;
- successful upload shows that runtime restart/materialization is required
  before `<RUNTIME_HOME>/SOUL.md` updates.

## Field-Save Standard

Every editable Settings field must prove this lifecycle:

1. The read endpoint returns the currently saved value or presence status.
2. The client sends the edited value under the backend's expected payload key.
3. The backend validates and persists to the correct destination.
4. The next read returns the persisted value.
5. The UI displays the persisted value or presence status.
6. Blank secret/reference fields preserve existing data when promised.
7. Audit contains a non-secret before/after summary.

No visible field is complete until this lifecycle is tested.

## Key Mistakes To Avoid

- Do not rebuild Settings as server-rendered admin HTML.
- Do not create a second runtime/provider config source of truth.
- Do not create one `.env` variable per Settings field.
- Do not make ordinary Settings changes require `.env` edits, container rebuilds,
  or redeploys.
- Do not ask operators to maintain provider API keys in `.env` when a governed
  credential store/auth store exists for Settings.
- Do not let tracked templates overwrite live environment-owned config.
- Do not edit the tracked structural base template from a Settings save.
- Do not print or return raw runtime config, `.env`, OAuth tokens, refresh
  tokens, access tokens, API keys, provider auth blobs, or channel secrets.
- Do not show secret values in text inputs after save.
- Do not treat a blank secret field as "clear secret" unless the UI explicitly
  says that and the user confirms it.
- Do not use one generic channel `value` field for all channels.
- Do not save to one config key and read back from another.
- Do not let duplicate form keys or generated payload fields overwrite each
  other.
- Do not wire channel enablement directly to Hermes without the governed app
  channel path.
- Do not use provider conversation IDs as physical runtime session IDs.
- Do not expose raw Hermes compression internals as admin controls.
- Do not mix live provider smoke tests into ordinary unit tests.
- Do not add cloud-platform scopes to a shared Workspace user grant casually.
- Do not ask operators for service-account files when current architecture uses
  shared user OAuth for that channel.
- Do not auto-reconnect OAuth or auto-upload identity files.
- Do not skip audit for rejected, failed, or no-op settings actions.

## Acceptance Tests

Automated tests must cover:

- every Settings response omits secrets;
- authorization rejects non-admin Settings access and non-super-admin
  identity-file upload/download;
- every editable field follows the field-save lifecycle;
- blank secret preservation;
- duplicate payload-key detection for generated forms/client payloads;
- runtime config writer behavior: live config is written, tracked base is not
  modified, unrelated config keys are preserved, and full config is never
  returned or logged;
- provider credential saves preserve blank-secret behavior, store credentials in
  the credential/auth store, expose presence only, and do not require new
  operator-maintained `.env` variables;
- runtime/provider save, provider switch, restart-required behavior, and audit;
- session-health save and runtime rotation guardrail behavior;
- channel enablement, public identifier, provider settings, process-after,
  processing mode, secret status, delete/disconnect, and session cap validation;
- Workspace OAuth redirect/callback redaction, disconnect, smoke config,
  smoke-check states, and document-workspace validation without live provider
  calls;
- identity-file upload authorization, validation, secret-like rejection, atomic
  write, audit, download, and restart notice;
- admin-contact save/read-back and invalid contact rejection.

Manual/local verification must cover:

- desktop and mobile Settings layout;
- section navigation or tabs;
- keyboard focus and accessible status/error states;
- typed confirmations;
- provider/model save and restart flow;
- representative channel edits;
- Workspace connect/disconnect/status surfaces using safe test credentials or
  mocked provider paths;
- identity-file upload using a harmless local Markdown file.

Do not consider staging until local Docker verification passes.

## Official Docs To Recheck

Recheck current official docs before implementation:

- FastAPI larger-app/router structure:
  <https://fastapi.tiangolo.com/tutorial/bigger-applications/>
- FastAPI response models:
  <https://fastapi.tiangolo.com/tutorial/response-model/>
- FastAPI CORS:
  <https://fastapi.tiangolo.com/tutorial/cors/>
- MDN HTML `form` attribute:
  <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/form>
- MDN `FormData.getAll()`:
  <https://developer.mozilla.org/en-US/docs/Web/API/FormData/getAll>
- Google OAuth 2.0 overview:
  <https://developers.google.com/identity/protocols/oauth2>
- Google OAuth 2.0 web-server applications:
  <https://developers.google.com/identity/protocols/oauth2/web-server>
- Model Context Protocol architecture:
  <https://modelcontextprotocol.io/docs/learn/architecture>
- MCP tools specification:
  <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>

## Build Order

1. Define the config ownership map, settings schemas, and response redaction.
2. Build read endpoints for overview/runtime/providers/channels/workspace/admin
   contact.
3. Build shared service-layer writers with audit.
4. Add mutation endpoints one area at a time.
5. Add Settings client sections over the typed APIs.
6. Add field lifecycle tests for every section as it lands.
7. Add browser verification across desktop/mobile and restart/confirmation
   flows.
8. Run local Docker verification before staging.
