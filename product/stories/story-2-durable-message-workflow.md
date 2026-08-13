# Story 2 - Durable Message Workflow

## Status
Completed 2026-08-08

## Problem
The gateway called Hermes inline per message. If Hermes timed out or the process restarted, the message was silently lost. There was no retry, no audit trail, and no way to know what had failed.

## Goal
Every inbound message gets a durable `requests` + `work_items` row before Hermes is called. Channel adapters return immediately. The worker owns governance, runtime handoff, reply capture, outbound send, and retry.

## What Was Built
- `requests`, `channel_events`, `work_items`, `session_history` tables
- `DurableWorkflowWorker` with `FOR UPDATE SKIP LOCKED`, concurrency=1, batch=1
- `reply_ready` boundary before outbound send
- Max 3 retries → `failed_needs_review` + Telegram alert to operator
- Provider-event idempotency via `channel_events`
- Stuck `processing` item recovery (expired lock reclaimable)

## Key Files
- `gateway/gateway.py` — DurableWorkflowWorker, enqueue_message
- `gateway/sql/schema.sql` — table definitions
