# Story 53 - Hermes Session History Token Bloat

## Archived Status

Completed and shipped to staging in commit
`fa39ac8 Add Hermes session health rotation controls`.

Story 53 added Hermes Session Health admin controls and Hana-side physical
Hermes session rotation when session message count, tool-result character
counts, or rough session token estimates cross configured caps.

## Goal

Make governed Hana replies usable again by diagnosing and fixing Hermes session
history growth that causes very large provider input token counts and slow
responses.

This story starts from a proven staging case: Hana Brain sent a tiny governed
Telegram payload, but Hermes assembled a prompt with hundreds of prior
conversation messages and more than 300k provider input tokens.

## Why This Matters

Phone and Telegram replies are too slow for normal use when the provider input
prompt is hundreds of thousands of tokens. Story 45 and Story 51 proved that the
large token count is not coming from the Hana Brain gateway payload. It is being
created inside Hermes prompt assembly, primarily from conversation history.

The next fix must target Hermes session history retention, session reset,
history compaction, or per-channel history limits. Do not spend this story
optimizing Millis, Telegram, phone timeout values, or Hana Brain gateway payload
size unless the investigation disproves the current evidence.

## Known Staging Case

Operator message:

```text
Hi Hana, it is 8:06pm EST, how are you?
```

Observed on staging:

- Date/time: July 5, 2026 around 8:06 PM Eastern
- Internal request ID: `112879`
- Channel: `telegram`
- Telegram message ID: `593`
- Trace ID: `telegram:8633043564:593`
- Logical session ID: `hana-thread:telegram:8633043564`
- Hermes physical session ID: `20260624_210342_7b6435`
- Person ID: `3bc73a4c-3791-4338-aeff-6fc728248082`
- Model: `gpt-5.4`
- Provider: `openai-codex`
- API mode: `codex_responses`
- Hana replied successfully, but slowly.

Runtime timing:

| Stage | Value |
| --- | ---: |
| Gateway job total | `32668 ms` |
| Hermes chat POST | `30395 ms` |
| Runtime handling | `31287 ms` |
| Hermes session ensure | `158 ms` |
| Provider/API status | `200` |

Hana Brain bridge payload:

| Component | Value |
| --- | ---: |
| User message chars | `39` |
| User message token estimate | `10` |
| Hana Brain system metadata chars | `595` |
| Hana Brain system metadata token estimate | `149` |
| Bridge payload chars | `634` |
| Bridge payload token estimate | `158` |

Hermes component diagnostic events:

Hermes emitted two `hermes_prompt_diagnostics_pre_provider` events for the one
runtime turn.

API call 1:

| Component | Value |
| --- | ---: |
| API call count | `1` |
| API message count | `320` |
| Non-system message count | `319` |
| Conversation history message count | `318` |
| API messages chars | `814592` |
| API messages token estimate | `203648` |
| Current user message token estimate | `10` |
| Sanitized user message token estimate | `10` |
| Active system prompt chars | `32130` |
| Active system prompt token estimate | `8032` |
| Hermes stable prompt chars | `31270` |
| Hermes stable prompt token estimate | `7818` |
| Hermes context prompt chars | `0` |
| Hermes context prompt token estimate | `0` |
| Hermes volatile prompt chars | `3290` |
| Hermes volatile prompt token estimate | `822` |
| Tool count | `25` |
| Tool schema chars | `53888` |
| Tool schema token estimate | `13472` |
| Conversation messages token estimate | `195335` |
| Final request token estimate | `217022` |

API call 2:

| Component | Value |
| --- | ---: |
| API call count | `2` |
| API message count | `322` |
| Non-system message count | `321` |
| Conversation history message count | `318` |
| API messages chars | `815217` |
| API messages token estimate | `203805` |
| Current user message token estimate | `10` |
| Sanitized user message token estimate | `10` |
| Active system prompt chars | `32130` |
| Active system prompt token estimate | `8032` |
| Hermes stable prompt chars | `31270` |
| Hermes stable prompt token estimate | `7818` |
| Hermes context prompt chars | `0` |
| Hermes context prompt token estimate | `0` |
| Hermes volatile prompt chars | `3290` |
| Hermes volatile prompt token estimate | `822` |
| Tool count | `25` |
| Tool schema chars | `53888` |
| Tool schema token estimate | `13472` |
| Conversation messages token estimate | `195492` |
| Final request token estimate | `217179` |

Provider-reported usage after response:

| Component | Value |
| --- | ---: |
| Provider exact input tokens | `312192` |
| Provider exact output tokens | `83` |
| Provider exact total tokens | `312275` |

## Current Conclusion

The dominant token source is Hermes conversation history:

| Source | Approximate Tokens |
| --- | ---: |
| Hana Brain bridge payload | `158` |
| Hermes stable prompt | `7818` |
| Hermes volatile prompt | `822` |
| Tool schemas | `13472` |
| Conversation history | `195492` |
| Provider exact input | `312192` |

Conversation history is the largest known component by far. Tool schemas are
large and may need later work, but they are not the first-order issue in this
case.

## Required Investigation

1. Create a feature branch/worktree from latest `origin/staging`.
2. Inspect Hermes session storage and conversation-history assembly for API
   server sessions.
3. Determine why Telegram session `hana-thread:telegram:8633043564` maps to a
   physical Hermes session that contains `318` prior conversation messages.
4. Determine whether history accumulation is:
   - expected Hermes API-session behavior with no cap
   - caused by Hana Brain reusing one long-lived physical session forever
   - caused by session IDs not rotating when they should
   - caused by old pre-gateway/Hermes history still attached to this session
   - caused by tool-loop/provider retry messages being persisted unexpectedly
5. Determine whether the two provider calls for one Telegram turn are expected.
6. Identify the supported Hermes surface for limiting, summarizing, compacting,
   resetting, or rotating session history. Prefer official Hermes APIs or config
   behavior over patching internals.
7. If no supported Hermes surface exists, propose the smallest Hana-side
   mitigation that preserves governed thread continuity while bounding prompt
   growth.

Also check these upstream/context-management leads before choosing a fix:

- [x] Verify the exact Hermes version/ref running locally and on staging.
  Verified local and staging both use Docker pin
  `2bd1977d8fad185c9b4be47884f7e87f1add0ce3` and report
  `Hermes Agent v0.17.0 (2026.6.19)`, one commit behind upstream. This means
  the v0.17.0 session-health features are present enough to investigate before
  adding Hana-side code for the same job.
- [x] Verify which Hermes compression settings are supported by the pinned
  runtime, especially message-count cleanup such as
  `hygiene_hard_message_limit`. Verified local/staging v0.17.0 supports the
  compression knobs. Staging live config had `compression.threshold: 0.3`,
  `model.context_length: 1050000`, and
  `compression.hygiene_hard_message_limit: 400`. The known bad case had about
  `217179` estimated final request tokens and `318` history messages, so it was
  painful but below both live cleanup triggers.
- Verify whether large retained tool, web, skill, log, or session-search
  outputs are present in the hot Hermes conversation history. If they are,
  prefer a supported offload/truncate/summarize approach so future short
  messages do not carry old giant outputs.
- [x] Keep Hana-side physical session rotation as the fallback guardrail. This
  implementation path has moved to Story 79:
  `product/stories/story79-admin-session-caps.md`.
- Verify existing tool-schema reduction remains active on staging. The tracked
  baseline now enables `tools.tool_search`, so this should be treated as a
  verification item unless Prompt Diagnostics still show a large model-visible
  tool list.

## Follow-Up Story

Story 79 now owns the chosen implementation path for lower, channel-aware
message-count caps, Admin controls, ops documentation, and Hana-side physical
session rotation before Hermes handoff.

Story 53 remains open for forensic verification that is not automatically
answered by Story 79:

- whether large retained tool/web/skill/session-search outputs are present in
  the bad physical session
- whether the two provider calls for one Telegram turn are expected
- whether `tools.tool_search` is still reducing the model-visible tool schema
  list on staging
- final Prompt Diagnostics proof that Story 79 materially reduces the known
  bad Telegram prompt size

## Candidate Fix Directions

The chosen first fix is Story 79. Other possible fixes remain follow-ups if
Story 79 does not sufficiently reduce prompt size:

- Add an Admin API control to reset a channel/person Hermes session mapping.
- Add a runtime bridge cap that starts a fresh physical Hermes session when
  prompt diagnostics show conversation history above a configured token
  threshold, not only a message-count threshold.
- Add a one-time staging cleanup/reset for the bloated Telegram physical session
  if the root cause is stale historical data rather than ongoing growth.
- Use a supported Hermes compaction/summarization/history-limit setting if one
  exists.

Do not delete all Hermes state or wipe runtime project data without explicit
operator approval. Do not drop databases.

## Required Design Constraints

- Keep the governed channel path intact:

  ```text
  channel -> Hana Brain Gateway -> governance -> runtime bridge -> Hermes
  ```

- Keep numeric `request_id` correlation intact.
- Keep logical session IDs stable for audit and channel/thread continuity.
- If a physical Hermes session ID changes, preserve the mapping history needed
  for logs and debugging.
- Do not expose raw conversation history, prompt text, secrets, phone numbers,
  tokens, or raw config in logs.
- Any admin control that changes runtime/session behavior must write audit logs.
- Any UI change requires local Docker/browser approval before commit.

## Tests

Automated tests should cover whichever fix is chosen. At minimum, add or update
tests proving:

- Existing safe sessions still reuse physical Hermes sessions when under the
  configured limit.
- A bloated or over-limit governed thread rotates/resets to a fresh physical
  Hermes session.
- The logical session ID and channel/provider refs remain unchanged.
- The runtime bridge logs old/new physical Hermes session IDs without raw user
  content.
- Request ID correlation remains intact.
- Existing email, phone, Telegram, Discord, and Google Chat session behavior is
  not regressed.

If an Admin API reset/control is added, also test:

- only authorized admins can use it
- audit logging includes actor, environment, target, and non-secret before/after
- the UI renders clearly and uses existing confirmation patterns

## Manual Verification

After deploy to staging:

1. Enable Prompt Diagnostics.
2. Restart Hana runtime.
3. Send a Telegram message in the same conversation.
4. Confirm `hermes_prompt_diagnostics_pre_provider` appears.
5. Confirm conversation history token estimate is materially reduced from the
   known bad case.
6. Confirm provider input tokens are materially reduced from `312192`.
7. Confirm Hana still replies correctly.
8. Repeat once to confirm the fix does not immediately start re-growing the
   same bloated prompt.

## Acceptance Criteria

- The known Telegram conversation no longer sends hundreds of thousands of
  provider input tokens for a simple short message.
- A short Telegram message should not include hundreds of prior history messages
  unless explicitly intended and documented.
- The fix is channel-safe and does not break phone, email, Discord, or Google
  Chat runtime handoff.
- Operators have a clear way to understand or reset/limit bloated sessions if
  the problem recurs.
- Prompt Diagnostics can prove the improvement with before/after component
  tables.

## Out Of Scope

- Tool schema reduction
- Stable prompt reduction
- Millis webhook auth alignment
- Phone timeout changes
- Voice recording, diarization, enrollment, or call summaries
- Changing model/provider solely to hide the token growth problem
