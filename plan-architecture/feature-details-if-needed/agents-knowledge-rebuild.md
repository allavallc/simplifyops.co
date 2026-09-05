# Agent Instructions: Rebuild the Knowledge Setup

Use this guide to rebuild the complete knowledge feature in another agent project.
It covers curated Markdown, generated self-knowledge, database storage, admin
editing, governed retrieval, runtime context, packaging, and verification.

Verified against the local source at commit
`f2406f6425a907790dfb46323696986abf370508` on 2026-09-05. The existing Graphify
report describes an older commit; current source and tests take precedence.
This is a source-based reconstruction guide, not a claim that the local or
deployed runtime passed an end-to-end test during this document's preparation.

Target examples use generic names. Links in the evidence map retain the actual
reference repository filenames so an agent can inspect the implementation.
If this document is copied alone, its contracts and examples remain usable, but
relative evidence links require access to the reference repository.

## 1. Instructions for the Implementing Agent

1. Read the target repository's agent rules, current architecture, and applicable
   coding and deployment rules. Confirm the target agent name, application
   database, runtime, admin authentication, and tool authorization mechanism.
2. Present an end-to-end implementation plan before coding. Follow the target's
   approval and feature-branch process. This guide does not authorize changes to
   a live database, credentials, tool grants, runtime boundaries, or deployment.
3. Preserve the ownership and disclosure contracts below. Reuse the target's
   services, design system, audit logger, and governed tool bridge.
4. Rebuild the documented baseline. Treat items explicitly marked **gap** or
   **extension** as separate decisions requiring the target operator's review.
   Do not silently claim that unused source adapters are part of the baseline.
5. Use current source inspection and official documentation when adapting a
   dependency. Do not copy environment-owned configuration or secrets.
6. Deliver code, migrations, curated seed documents, generator, tests, operating
   instructions, and an evidence report together. Report skipped tests and
   incomplete lifecycle coverage as incomplete verification.

For Python parity, the reference uses Python 3.11+, FastAPI, Jinja2, Psycopg 3,
PyYAML, Pydantic Settings, and the MCP Python SDK's `mcp.server.fastmcp` interface.
Its MCP dependency is constrained to `>=1.9.0,<2.0.0`; do not assume a major SDK
upgrade preserves the entrypoint contract. The generator itself uses the Python
standard library. Reuse the target's compatible dependency lock and verify
versions against [the reference project manifest](pyproject.toml).

## 2. Ownership and Data Flow

The baseline has two related delivery paths:

```text
Reviewed knowledge/*.md
  -> seed an empty application knowledge store
  -> application Postgres records <-> super-admin editor
  -> governed list/read/search tools -> agent runtime

Allowlisted architecture/capability document sections
  -> deterministic generator -> about-myself/generated/self-knowledge.md
  -> authority-filtered runtime context
```

The generated file can also be included in the initial database seed, but that
database copy and the runtime's direct file read have different refresh paths.

| Information | Owner and access path |
| --- | --- |
| Reviewed, distributable guidance | Human-reviewed Markdown under `knowledge/` |
| Operational knowledge records after initial seeding | Application database; super-admin UI edits; governed agent reads |
| Generated setup description | Allowlisted source documents plus deterministic generator |
| Current tools, enabled capabilities, valid options, live state | Live application services and computed capability registry |
| Raw conversation experience | Self-hosted memory system and operational logs |
| Current conversation | Runtime session |
| Brand/company facts and external source authority | Separate context repository through its approved connector |
| Proposed learning or self-improvement | Future human approval workflow; not an implemented knowledge write path |

Keep the knowledge tables in the application database, separate from the
self-hosted memory database. The agent's baseline access to curated knowledge
is **read-only**, constrained by the governed requester's authority. The
super-admin UI owns create, update, archive, and reactivate operations.

**Ownership detail:** current admin saves change database records only. They do
not write a local Markdown file or create a GitHub commit. `source_path` is also
a logical identity for documents created through the UI; its presence does not
prove that a corresponding file exists. Preserve this distinction in operator
instructions and backups.

Evidence: [folder ownership](knowledge/README.md),
[architecture](product/product-decisions/current-architecture.md),
[store](admin_api/knowledge_store.py), and
[admin routes](admin_api/routes/admin_web.py).

## 3. Create the Curated Folder Structure

Use this target layout:

```text
knowledge/
  README.md
  INDEX.md
  sources.md
  about-myself/
    README.md
    sources.md
    generated/
      self-knowledge.md
  principles/README.md
  processes/README.md
  patterns/README.md
  playbooks/README.md
  real-life-examples/README.md
  case-studies/README.md
  reference/README.md
scripts/
  build_self_knowledge.py
```

| Folder | Meaning |
| --- | --- |
| `about-myself` | Agent capabilities, setup, and disclosure boundaries |
| `principles` | Core rules and decision truths |
| `processes` | Repeatable mechanical steps |
| `patterns` | Recurring signals to recognize |
| `playbooks` | Complete scenario guidance |
| `real-life-examples` | Mistakes, lessons, costs, and fixes |
| `case-studies` | Specific narratives of success or failure |
| `reference` | Neutral definitions, concepts, options, and schema summaries |

`README.md` explains ownership and maintenance for humans. `INDEX.md` is a short
map for the agent: locate the smallest relevant document rather than loading the
whole corpus. Root `sources.md` points to external context, memory, and live
services without duplicating their contents. It is distinct from the generator
input at `about-myself/sources.md`.

Add a brief README to every category. Start infrastructure and setup documents
at `minimum_authority: admin`, matching the reference folder map. Assign a lower
authority only to reviewed guidance appropriate for that audience. Do not copy
the reference project's business content merely to populate the folders.

### Markdown contract

Every seed document must start with exactly these two front-matter keys:

```markdown
---
minimum_authority: member
status: active
---

# Example Process

Reviewed instructions for the intended audience.
```

Allowed authorities, in ascending order: `contact`, `member`, `admin`,
`super_admin`. Allowed statuses: `active`, `archived`. Reject missing keys,
unknown keys, non-mapping YAML, invalid values, empty content, NUL characters,
and secret-like content. Parse YAML safely.

The first level-one heading supplies the title; otherwise derive it from the
filename. `knowledge/playbooks/example.md` has slug `playbooks/example` and
category `playbooks`. Root files have category `root`. Slugs and source paths
are unique; preserve case as the reference implementation does.

Canonical paths stay under `knowledge/`. Reject parent traversal, hidden path
components, forbidden directories, spaces, and unsupported characters. Path
components use letters, numbers, dots, underscores, and hyphens, beginning with
a letter or number. The create form accepts a single `.md` filename and a
separate approved folder. A `/generated/` path marks a document read-only.

Metadata is stored in structured fields; `content_md` stores the Markdown body.
When downloading, render canonical front matter from those structured fields.
Pasted front matter in the editor is stripped; it does not override the form's
authority selection or the separate archive/reactivate action.

Evidence: [folder map](knowledge/INDEX.md),
[source boundaries](knowledge/sources.md), and the parsing, rendering, path,
category, and content helpers in [knowledge_store.py](admin_api/knowledge_store.py).

## 4. Build Deterministic Self-Knowledge Generation

Implement a target `scripts/build_self_knowledge.py` with two commands:

```bash
python3 scripts/build_self_knowledge.py generate
python3 scripts/build_self_knowledge.py check
```

These are target filenames. The corresponding reference generator is linked
below. Resolve the repository root from the script's location so execution does
not depend on a developer's working directory.

Use this source-list format in `knowledge/about-myself/sources.md`:

```markdown
---
minimum_authority: admin
status: active
---

# Self-Knowledge Sources

## Output

- `knowledge/about-myself/generated/self-knowledge.md`

## Sources

### docs/architecture.md

Reason: Reviewed runtime boundaries and supported capabilities.

Sections:
- Runtime Boundary
- Supported Capabilities
```

The example source file and headings must be created or replaced with verified
target sources. A listed heading includes its section body and nested sections,
ending at the next heading of equal or higher level. Do not ingest entire files
as a fallback when a heading is missing.

Generator behavior:

- Require an output path, at least one source, a `Reason:`, and explicit section
  headings per source. Fail on missing files or missing/empty named sections.
- Reject absolute source paths, parent traversal, and secret-bearing locations.
  The denylist includes environment files, channel configuration, live runtime
  configuration, runtime home/session/auth data, audit logs, infrastructure
  inventories, and health snapshots. Never add credentials to the allowlist.
- Emit `minimum_authority: admin` and `status: active`, a generated-file notice,
  a disclosure policy, a reviewed plain summary, and labeled source extracts.
- Check source extracts and final output for secret-like material. Keep fixed
  summary text under review too; source extraction does not update that text.
- Make `generate` deterministic and `check` compare the exact rendered output
  against the file. Missing/stale output must produce a nonzero result.
- Never hand-edit generated output. Edit approved sources or the source list,
  regenerate, review the diff, then run `check`.

This is deterministic extraction and formatting; it does not call an LLM.
Its disclosure rules allow approved non-admin people high-level capability
answers, while operational setup context is restricted to admin and super-admin
people. Secrets remain excluded at every authority level.

Evidence: [generator](scripts/build_hana_self_knowledge.py),
[actual source-list syntax](knowledge/about-myself/sources.md),
[generator tests](tests/test_hana_self_knowledge.py), and
[operating procedure](ops/hana-self-knowledge.md).

## 5. Implement Persistence and the Complete Admin Lifecycle

Build a shared knowledge store/service; routes and tools must not implement
independent validation or storage rules. Use injected interfaces for tests.
Keep authentication and authorization at the trusted service boundaries.

### Database contract

| Table | Fields |
| --- | --- |
| `knowledge_documents` | `id` UUID; `category`, unique `slug`, `title`, `content_md`, `source_type`; `read_only`; `created_at`, `updated_at`, `updated_by`; `status`, `minimum_authority`; unique `source_path`; `sync_state`; nullable `file_sha`, `git_commit_sha`, `synced_at` |
| `knowledge_document_versions` | `id` UUID; document FK; `version_number`; `content_sha256`, `content_md`; `actor_email`, `created_at`, `change_summary`; unique document/version pair |

Use timezone-aware timestamps and database uniqueness/check constraints for
identity, valid status, and valid authority. Keep schema initialization
idempotent. The reference has compatibility ALTER/backfill statements; a fresh
project need not recreate obsolete migration history. PostgreSQL constraints
enforce these invariants independently of application checks.
[PostgreSQL constraints documentation](https://www.postgresql.org/docs/current/ddl-constraints.html)

Record an initial content version on creation and a new version when body
content changes. Metadata-only saves and archive/reactivate do not create a
content version in the reference; they rely on mutation audit events. Version
rows alone are not a complete backup of document metadata or authority.

### Initialization and explicit import

`seed_from_repo_if_empty()` checks the document count. When any document already
exists, it returns without importing files, including when all rows are
archived. On an empty store it reads safe Markdown under the seed root and
imports it. Both opening the admin page and requesting knowledge through tools
can trigger this first-use seed; these reads can therefore initialize storage.

The explicit `sync_from_source_files()` helper imports a complete inventory,
updates matching paths, and archives missing `repo_seed`/`repo_file` records
with `sync_state: missing_from_source`. It returns created/updated/archived counts
and per-file errors. It can commit valid imports while reporting other errors.
It is not a background synchronizer or normal page refresh operation.

**Repair boundary:** do not invoke full-inventory sync casually against an
edited database. An incomplete inventory can archive records; an empty inventory
can archive all eligible records. Changed source files can overwrite database
edits. Review the intended inventory and affected records before authorizing
any explicit reconciliation.

### Admin routes and fields

All reference Knowledge page routes, including viewing and download, require an
active super-admin person resolved from the audited admin session. An admin
may receive setup context at runtime but cannot use this super-admin page.

| Surface | Input and behavior |
| --- | --- |
| `GET /admin/knowledge` | Filters: `folder`, `status`, `authority`; selection: document UUID; `new=true` opens creation. Seed only if empty, then render database records. |
| `POST /admin/knowledge` | `source_folder`, `source_filename`, `minimum_authority`, `content`; validate and create an active record with initial version and audit event. |
| `POST /admin/knowledge/{document_id}` | Edit `content` and `minimum_authority`; preserve path and current status; derive title from body; audit before/after. |
| `POST /admin/knowledge/{document_id}/archive` | Change saved record to archived; preserve its content, identity, and authority. |
| `POST /admin/knowledge/{document_id}/reactivate` | Change saved record to active; preserve its content, identity, and authority. |
| `GET /admin/knowledge/{document_id}/download` | Return saved Markdown with canonical metadata and an attachment filename. |

The reference create form defaults to `contact`; folder-map and generated setup
documents explicitly use `admin`. Verify these defaults in acceptance tests.
Existing-document forms do not expose rename/move. There is no hard-delete or
version-restore UI. Archive/reactivate operate on saved content, not unsaved
textarea edits submitted alongside the action.

Use the target's existing admin components. The reference uses server-rendered
HTML with a folder/document list, filters, an editor, metadata details,
notifications, download, and disabled mutation controls for generated documents.
Enforce read-only rules on the server as well. Request approval before changing
the target's interaction patterns or wording.

Successful mutations redirect with HTTP 303. Create validation errors render
the form with entered values; update validation errors redirect with an error.
Missing document IDs return 404 at the route boundary. The reference's authority
filter treats the selected level as a requester authority: selecting `admin`
includes documents requiring `contact`, `member`, or `admin`. It uses the same
authority threshold helper as tool visibility; it is not an exact metadata match.

Evidence: [store and schema](admin_api/knowledge_store.py),
[routes and audit helpers](admin_api/routes/admin_web.py),
[template](admin_api/templates/admin/knowledge.html), and
[admin acceptance examples](tests/test_admin_api.py).

## 6. Expose Governed Read-Only Tools

Register narrow tools through the target's existing governed connector and
deferred tool bridge. Preserve the reference launch pattern
`connectors.<server_name>.mcp_server` when rebuilding in this architecture.
Do not bypass tool availability, session scope, or authorization by exposing a
direct filesystem or provider path.

| Tool | Arguments | Successful application payload |
| --- | --- | --- |
| `list_knowledge_docs` | Required opaque `tool_context`; optional `category` | `status: ok`, `documents: [summary]` |
| `read_knowledge_doc` | Required `tool_context`, `slug` | `status: ok`, `document: summary + content_md` |
| `search_knowledge_docs` | Required `tool_context`, nonempty `query`; optional `category`, `max_results=20` | `status: ok`, `query`, `matches` |

Document summaries contain `id` as a string, `category`, `slug`, `title`,
`source_type`, `read_only`, `status`, `minimum_authority`, `source_path`,
`sync_state`, ISO `updated_at`, and `updated_by`. Search matches contain `slug`,
`title`, `category`, one-based body `line`, and `snippet`.

Search is case-insensitive substring matching over body lines in visible
documents, with a result limit clamped to 1–50. It returns shortened line
snippets. There is no embedding pipeline, vector database, semantic ranking,
or PostgreSQL full-text search dependency in this baseline.

The opaque token resolves server-side to trusted request ID, person, authority,
and context metadata. The reference stores a hash of the token and checks its
expiry, with a default lifetime of two hours. Do not accept actor identity or
authority supplied separately by the model. The token is secret and must not
appear in logs, documents, screenshots, or returned summaries.

Filter out archived records and insufficient-authority records before listing,
reading, or searching. A request for an invisible or missing slug produces the
same not-found error. Do not leak restricted titles or snippets through search.
These controls are server-side; a prompt telling the agent to be discreet is
not an authorization mechanism.

### Boundary contract

- **Caller/callee:** runtime tool bridge -> connector entrypoint -> shared
  knowledge service -> application database.
- **Persistent state:** knowledge documents, content versions, trusted tool
  context records, and audit/log records. First-use reads may seed the database.
- **Transient state:** opaque call token, validated filters, query, returned
  document/snippets. No knowledge-specific job, delivery target, or run record.
- **Identifiers:** preserve the governed internal request ID in tool logs; use
  document UUID internally and slug for lookup. Provider IDs are not substitutes.
- **Credentials:** environment-owned database access and server-side context
  resolution; no new model/provider credential for this feature.
- **Errors/status:** successful dictionaries use `status: ok`; invalid/expired
  context, invalid arguments, and invisible/missing documents raise service
  errors. Verify the actual MCP SDK error envelope in integration tests.
- **Timeout/retry:** no knowledge-specific timeout, retry queue, or worker is
  implemented. Inherit bounded target tool/database budgets and surface errors;
  read retries re-evaluate the current visible data and are not snapshot reads.
- **Idempotency:** no separate tool idempotency key. Repeat retrieval should not
  change an already initialized corpus. Initial-seed races are a known gap.
- **Delivery ownership:** tool results return to the runtime; the existing
  governed message/outbound pipeline owns any user-visible answer. Knowledge
  tools do not send channel messages themselves.

MCP defines tool input schemas and result/error envelopes; it does not supply
this application's person-authority policy. Verify both layers.
[MCP tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

Evidence: [entrypoint](connectors/hana_brain/mcp_server.py),
[service](admin_api/hana_brain_service.py),
[trusted context implementation](hana_brain_contracts/tool_context.py), and
[tool tests](tests/test_hana_brain_mcp.py).

## 7. Connect Runtime Context and Package the Files

The runtime context builder combines a computed capability snapshot with the
generated setup file only for `admin` and `super_admin`. Other approved people
receive the public capability description. Missing, unreadable, or secret-like
generated content is omitted with a warning; do not substitute unrestricted
source documents as a fallback.

The curated knowledge index is available through knowledge retrieval. It is not
evidence that every document is automatically injected into every conversation.
Keep external company context, live state, and raw memory on their own governed
paths. This feature does not require a new direct LLM caller or a change to the
runtime handoff contract.

Configure the target's equivalent of `knowledge_path` and `about_myself_path`.
Use repository-relative defaults resolved within the container, not host-specific
paths. Include `knowledge/` in the admin and runtime images. Include the
generator and **every allowlisted source document** in the image where drift
checks will run. Check this without bind mounts masking missing image files.

**Packaging gap:** the inspected runtime Dockerfile copies several source docs
but does not explicitly copy the `docs/mcp/` files named by the current source
list. A successful checkout drift check does not prove the image can run it.
Verify and complete the target's dependency packaging before claiming parity.

Local Compose in the reference mounts the knowledge folder into both services.
That does not make admin database edits write back to the mounted directory.
Keep secrets in environment-owned mounts/configuration and inspect only safe
Compose output such as `docker compose config --services`.

Evidence: [capability/context formatting](admin_api/capabilities.py),
[runtime context composition](hana_runtime/message_context.py),
[settings](hana_brain_contracts/settings.py),
[admin image](Dockerfile.admin), [runtime image](Dockerfile.hermes), and
[Compose](docker-compose.yml).

## 8. Logging, Failure Handling, and Recovery

Reuse the application audit mechanism for each admin mutation. Record actor,
timestamp, action, target UUID, environment, request metadata, and non-secret
before/after summaries. The reference summaries include authority, status,
path, content hash/length, and whether file/commit hashes exist; they exclude
the Markdown body. Content versions intentionally contain the body in the
application database, not the general audit log.

Tool read/search logs include request ID, authority, relevant category/slug,
and result count or content length. Search logs record query presence, not raw
query text. The reference uses structured operational logs for these reads;
do not describe them as equivalent to mutation audit events.

| Situation | Baseline behavior and operator response |
| --- | --- |
| Missing/invalid seed file | Import can report errors while accepting valid files. Review errors; do not treat partial import as complete. |
| Existing database differs from Markdown | Ordinary reads preserve database state. Export/review records before choosing an explicit reconciliation. |
| Source inventory omitted files | Explicit sync can archive missing records. Restore reviewed content/status without clearing the database. |
| Generated output stale | Fix sources locally, regenerate, inspect the diff, and check before normal delivery. Never auto-commit generated output from a server. |
| Generated database copy stale | Runtime file refresh and database refresh are separate. Plan an authorized targeted repair; full sync can affect unrelated edits. |
| Database or tool-context lookup unavailable | Fail the call; do not fall back to ungoverned filesystem reads. |
| Repeated create | Sequential duplicate paths are rejected; database constraints also guard uniqueness. Do not promise graceful handling of every race. |
| Overlapping saves | No optimistic edit token or explicit serialization exists in the reference. Concurrent version allocation can conflict; metadata saves can overwrite one another. |
| Repeated archive/reactivate | Final status converges, but repeated actions can still update timestamps and generate audit entries. |
| Mutation committed but audit/response failed | Audit append and database transaction are separate. Inspect the saved record and audit evidence before retrying; no atomic outbox guarantees this boundary. |

Back up documents, all metadata, and version records through the target's normal
database backup process. Preserve source documents and generator in version
control. Download is a per-document export, not a full database backup.
There is no built-in version rollback UI. Repair a reviewed body through normal
super-admin save, preserving audit history; repair metadata explicitly too.
Restoring application code alone does not revert saved knowledge.

Never wipe a database to reseed knowledge. The reference project requires two
explicit permissions in the same conversation for database destruction. Prefer
targeted, reviewed repairs and observe the target's stronger rules when present.

Evidence: [store/version behavior](admin_api/knowledge_store.py),
[audit calls](admin_api/routes/admin_web.py), and
[retrieval logs](admin_api/hana_brain_service.py).

## 9. Separate Implemented Behavior from Extensions and Gaps

The following distinctions must remain visible in the rebuild plan:

1. **GitHub adapters exist but are not connected to admin saves or ordinary
   retrieval.** The reference has local/GitHub file adapters, SHA-aware GitHub
   updates, and a settings-based factory. No active admin/tool caller uses that
   factory. Do not require a GitHub write token for the baseline feature.
2. **Some UI wording overstates Git synchronization.** The template describes
   Git-backed files and file creation, while current routes write only database
   records. Its “Last Sync” display uses `updated_at`. Preserve actual contracts
   in this guide; obtain target UX approval before choosing corrected wording.
3. **Agent mutations are not implemented.** Durable policy reserves possible
   protocol-knowledge mutations for super-admin users, but the actual connector
   exposes only list/read/search knowledge tools. Policy is not evidence of an
   implemented API. Do not invent create/update/archive tools for this rebuild.
4. **No background learning/import worker exists.** No schedule, notification,
   retry queue, overlapping-job policy, or Run Once action belongs to baseline
   knowledge. Such work requires its own complete lifecycle contract.
5. **Concurrency is not fully handled.** Initial seeding checks count before
   importing; version numbers use `MAX(...) + 1`. Uniqueness protects identity
   but does not provide a friendly concurrent-edit protocol. Report these
   limits instead of claiming safe parallel writes.
6. **Path/content checks are limited.** Existing lexical checks and regexes are
   not a complete secret detector or symlink-containment guarantee. The source
   normalizer can canonicalize leading separators; the generator also trusts
   the output location from its source list. Review resolved input/output paths
   and symlink policy in the target plan before extending trusted inputs.
7. **Generated refresh is split.** A regenerated runtime file is not automatically
   reimported into an already populated database.
8. **CI policy and implementation differ.** The inspected staging workflow runs
   Ruff/pytest for its full-check path, but does not run the required Schemathesis
   gate. Do not label that gate implemented merely because agent rules require it.

For a separately approved Git-backed editing extension, define source ownership,
branch, credential ownership, conflict checks, file/DB commit ordering, partial
failure repair, retries, complete inventory handling, and audit before writing
code. GitHub's contents API requires the current blob SHA when replacing a file;
that alone does not prevent a stale editor from overwriting a newer user change
if the application fetches a fresh SHA immediately before writing stale content.
[GitHub repository contents API](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents)

For a separately reviewed filesystem hardening change, resolve paths and verify
containment before reading or writing, including the output path. Python's
`Path.resolve()` resolves symlinks and eliminates `..`; a containment policy
must still be applied by the application.
[Python pathlib documentation](https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve)

Evidence: [unused source adapters](admin_api/knowledge_sources.py),
[architecture decisions](product/product-decisions/architecture-decisions.md),
[staging workflow](.github/workflows/deploy-staging.yml), and source links above.

## 10. Rebuild Order and Acceptance Evidence

Plan the whole lifecycle above first. Then implement in dependency order:

1. Folder map, curated templates, and source ownership rules.
2. Metadata/path/content validation and canonical Markdown rendering.
3. Application database schema, first-use seeding, versions, and store methods.
4. Super-admin create/edit/archive/reactivate/download using shared validation.
5. Trusted tool context integration and read-only list/read/search.
6. Allowlisted generator, public/admin capability context, and runtime loading.
7. Image packaging, drift checks, failure/repair instructions, and acceptance
   tests across UI, database, tools, and runtime authority boundaries.

Do not mark the feature complete until the following matrix has evidence:

| Area | Required verification |
| --- | --- |
| Folder/metadata | Every category and root; missing/unknown front matter; invalid authority/status; title derivation; canonical Markdown round trip |
| Create | Every input field reaches the service, persists in real Postgres, reads back, and displays correctly; derived slug/path/category/title/status/read-only fields checked |
| Edit | Body and every authority choice round-trip; title updates; identity/status preserved; changed body creates a version; unchanged body does not |
| Archive/reactivate | Status round-trip, retained content/authority/identity, list filters, tool invisibility while archived, visibility restored afterward |
| Download | Saved body and canonical metadata match database values, correct attachment filename; generated documents remain downloadable but immutable |
| Authorization | Logged-out, inactive, admin, super-admin UI cases; contact/member/admin/super-admin tool matrix; missing/invalid/expired tool context |
| Retrieval | Visible summaries and full bodies; nonempty query; case-insensitive line matches; category/result limits; no restricted titles/snippets; missing and invisible slug behavior |
| Seeding/import | Empty-store initialization; existing edits survive reads/restarts; repeated seed; partial invalid import; missing/empty inventory behavior in a disposable database |
| Failure/concurrency | Duplicate create, simultaneous first use/saves, failed transaction, audit failure after save, and retry observations; record unsupported guarantees explicitly |
| Generator | Determinism, exact drift check, missing source/heading, blocked paths/content, output-path assumptions, generated admin metadata |
| Runtime | Public users receive only public capabilities; admin+ receives safe setup context; missing/unsafe generated file omitted; request ID preserved through tools |
| Audit | Actor/time/environment/request/target and before/after metadata; body and opaque tokens absent from general logs |
| Packaging | Clean images contain all seed/generated/source files needed; check succeeds without checkout bind mounts; restart preserves database edits |

Reference tests are useful specifications, not proof of complete target
coverage: [store](tests/test_knowledge_store.py),
[source adapters](tests/test_knowledge_sources.py),
[generator](tests/test_hana_self_knowledge.py),
[governed tools](tests/test_hana_brain_mcp.py),
[admin lifecycle](tests/test_admin_api.py), and
[capability context](tests/test_capabilities.py).

**Test database boundary:** reference knowledge-store integration tests include
table-wide cleanup in `finally` blocks. Run them only against an isolated,
disposable test database with no operator or other-agent data. Some skip when
Postgres is absent or populated; a green run with skips does not prove durable
field coverage. Do not point a copied test command at normal local/staging data.

For implementation work in the reference architecture, use the ordered gates:

```text
Brooks Audit > Focused Ruff > Focused Pytest > Full Ruff > Full Pytest
  > Local Docker validation > Schemathesis API gate > User smoke test
```

Scope Schemathesis to verified safe operations on normal data. Use a disposable
database for writes/stateful coverage, and remember first-use knowledge reads
can seed storage. Explicit browser/form and MCP tests remain necessary; OpenAPI
coverage does not cover the stdio tool bridge or every HTML form field.
Use the target's approved authentication fixtures without exposing credentials.
Schemathesis can run against the live schema in CI and emit test reports; use
that evidence alongside the explicit lifecycle tests.
[Schemathesis CI/CD guide](https://schemathesis.readthedocs.io/en/stable/guides/cicd/)

Check host ports before starting Docker. In this repo, implementation work uses
a new branch/worktree from latest `origin/staging`, while user-facing local
Docker tests use the main checkout's disposable integration branch unless an
isolated stack is explicitly approved. Obtain local user confirmation before
committing UI work. Follow the actual
[feature development process](product/agent-feature-dev-process.md).

Only after local checks and user testing pass should the operator proceed
through the target's staging process. Gate the exact build before deployment,
then verify deployed code, image files, generator check, authority-separated
retrieval, and one approved lifecycle smoke test. Preserve test evidence and
repair instructions; do not infer deployment success from Git alone.

For updates to this guide alone, verify referenced paths, Markdown formatting,
and claims against source. Do not run database-mutating tests or start a
deployment merely to validate a documentation change.

## 11. Maintenance Checklist

- New guidance: choose the correct category and audience, review content, then
  use the approved source or admin lifecycle according to ownership.
- Source/architecture change: update the explicit self-knowledge allowlist as
  needed, regenerate, check, and verify image source inclusion.
- Access change: update structured authority through the permitted lifecycle;
  test list/read/search and runtime disclosure at both sides of the boundary.
- Retirement: archive through the owner service; preserve identity and history.
- New environment: provision the application database and normal governed
  runtime context; ship curated files; do not copy live memory or credentials.
- New retrieval or write capability: review its complete ownership, trust,
  lifecycle, failure, and audit contract before adding a tool.
- Document refresh: update the verification date/commit and evidence map;
  distinguish intended policy, active call paths, unused helpers, and known gaps.

The reference generated self-knowledge passed its local `check` command during
preparation of this guide. No database, Docker, staging, or complete feature
acceptance run was performed for this Markdown-only task.
