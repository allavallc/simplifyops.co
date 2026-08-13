# Story 10 - Safety Gate and Action Confirmation

## Status
Not started

## Problem
James has no safety gate. Sensitive external actions (send email, share file, post, forward) go straight to runtime without confirmation. There is no `waiting_for_confirmation` state, no pending action ledger, and no way for Anthony to approve or deny before James acts.

## Goal
Before runtime handoff, inspect the request for sensitive external actions. If found and the sender is `super_admin`, park the work item in `waiting_for_confirmation`, send a numbered confirmation prompt, and store the original runtime packet. A later "yes" resumes from the original request — not from the confirmation text.

## Required Tables
- `agent_actions` — action type, status, requester, topics, risk, recipients, request ID
- `pending_runtime_packets` — original governed packet awaiting confirmation, status, expiry

## Safety Outcomes
- `no_request` — nothing actionable detected, do not call runtime
- `allow_runtime` — no protected topic or sensitive action detected
- `confirmation_required` — sensitive external action, super_admin sender → park
- `confirmed` — later message approves one pending action → resume original packet
- `confirmation_denied` — later message denies → mark denied, complete without runtime
- `held_for_review` — sensitive request lacks access → Inbox

## Key Constraint
The confirmation message must resume the ORIGINAL full request, not just send "yes" to Hermes. `pending_runtime_packets` stores the full governed packet so the "yes" turn can replay it.
