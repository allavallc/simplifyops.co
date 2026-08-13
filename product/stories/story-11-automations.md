# Story 11 - Automations

## Status
Not started — requires Stories 7, 8

## Problem
James cannot proactively do scheduled work. All interaction is reactive. There is no mechanism for timed jobs, run-once tasks, or notification delivery.

## Goal
Admin-managed scheduled and run-once jobs. The automation worker claims queued runs, resolves execution owner context, calls the runtime bridge, captures output, and delivers notifications.

## Required Tables
- `automations` — schedule, owner, instructions, notification policy
- `automation_runs` — trigger type, status, lock, attempt, output, notification fields
- `automation_run_attempts` — per-attempt stage/status/error
- `automation_run_events` — append-only event log

## Key Constraints (per arch doc)
- Create/edit/pause/resume/archive start from audited admin APIs only
- App owns run state, owner context, notification policy, outbound delivery, and audit
- Hermes owns language/tool execution only
- Must define full handoff contract before implementation (trigger owner, input/output schema, schedule behavior, execution owner, tool context, output capture, notification, retry, overlap, paused job behavior)
