# Story 79 - Admin Session Caps

## Goal

Add Hana-owned message-count caps that let admins prevent long Hermes sessions
from bloating. Keep one logical session per channel thread, chat, or call, but
rotate the physical Hermes session before old history makes short replies slow.

This story supports Story 53. The fix must not depend on committing, pushing, or
rewriting `hermes/config.yaml`; that file is environment-owned runtime config.

## Background

Story 53 found a staging Telegram case where a short message used a Hermes
physical session with `318` prior conversation messages and more than `300k`
provider input tokens. Staging Hermes cleanup was enabled, but the known bad
case was still below the live cleanup triggers:

- token trigger estimate: about `315000`
- message-count cleanup: `400`
- known bad message count: `318`

Hana needs lower, channel-aware caps. Phone can grow quickly inside one live
call, email can have naturally longer threads, and chat channels need protection
from weeks of accumulated history.

## Required Configuration Ownership

Do not store these caps in `hermes/config.yaml` or `hermes/config.base.yaml`.

Use this ownership model:

- Global default cap: DB-backed Hana admin/runtime state.
- Per-channel override cap: the channel's environment-owned
  `channels/<channel>.yaml`.
- Hermes config: not used for these caps.

Add this ownership rule to `ops/env-var-to-change-by-environment.md` in a new
`Session Cap Settings` section. The ops doc must say local, staging, and
production may intentionally differ, and that cap changes do not change Hana's
logical session shape.

## Admin UI Requirements

Add a simple `Session Caps` section directly below `Runtime` on the Hana
Settings page.

Global default:

- Label: `Default session message cap`
- Initial default: `100`
- Stored in DB-backed Hana admin/runtime state
- Saved from the Settings page
- Audited with actor, environment, target, and non-secret before/after values

Per-channel override:

- Add `Session message cap` to the existing channel drawer/modal.
- Empty value means use the global default.
- Persist the override in that channel's `channels/<channel>.yaml`.
- Include the override in channel save audit summaries.
- Clearing the field removes the override.

Initial recommended overrides:

| Channel | Override |
| --- | ---: |
| phone | `50` |
| email | `200` |
| telegram | empty, uses default `100` |
| discord | empty, uses default `100` |
| google_chat | empty, uses default `100` |

Do not expose raw Hermes compression internals such as `target_ratio`,
`protect_last_n`, `protect_first_n`, or `hygiene_hard_message_limit`.

## Runtime Requirements

Resolve the effective cap in this order:

1. channel YAML override
2. global DB default
3. built-in fallback `100`

Before a governed message is sent to Hermes:

1. Resolve the logical session using the existing channel/thread rules.
2. Resolve the current physical Hermes session mapping.
3. Inspect the current physical Hermes session message count through a
   supported Hermes session API when available.
4. If the count is greater than or equal to the effective cap, rotate to a fresh
   physical Hermes session before chat handoff.
5. Preserve logical session ID, request ID, channel refs, person ID, and mapping
   history.

Use rotation reason `hana_message_count_cap`.

Logs must include only non-secret metadata:

- channel
- logical session ID
- old/new physical Hermes session IDs
- observed message count
- effective cap
- request ID

Do not log raw user text, prompt content, full conversation history, tokens,
secrets, or full runtime config.

If the Hermes message-count API is unavailable or unreliable, add a safe
fallback counter or use the latest available Prompt Diagnostics count. Log that
the fallback was used.

## Tests

Admin tests must prove:

- the Settings page renders `Session Caps` below `Runtime`
- saving the global default persists and audits
- the channel drawer renders `Session message cap`
- empty channel cap means global default
- saving a channel override writes the channel YAML and audits
- clearing a channel override removes it
- invalid caps are rejected

Runtime tests must prove:

- under-cap sessions reuse the current physical Hermes session
- at-cap sessions rotate before Hermes chat
- channel override beats global default
- cleared override falls back to global default
- phone can use a lower cap than email/chat
- request ID, logical session ID, channel, sender/thread refs, and person ID
  remain intact after rotation
- rotation logs do not contain raw user text or secrets

Documentation tests/checks must confirm:

- `ops/env-var-to-change-by-environment.md` states caps are not stored in
  `hermes/config.yaml`
- the documented source-of-truth split matches the implementation

## Manual Verification

Before commit, local Docker/browser verification is required because this
changes Admin UI.

1. Save the global default cap from Hana Settings.
2. Save a phone override and an email override from the channel drawer.
3. Clear one override and confirm it falls back to the global default.
4. Confirm audit log entries exist and do not contain secrets.
5. Send a normal governed test message and confirm runtime handoff still works.

After staging deploy:

1. Enable Prompt Diagnostics.
2. Send a Telegram message in the known long-running chat.
3. Confirm the session rotates or stays below cap before the provider call.
4. Confirm provider input tokens are materially lower than the Story 53 bad
   case.
5. Confirm Hana still replies correctly.

## Out Of Scope

- Changing Hermes `compression.*` settings
- Pushing or committing `hermes/config.yaml`
- Exposing raw Hermes compression controls in Admin
- Tool schema reduction
- Stable prompt reduction
- Phone timeout changes
