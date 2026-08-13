# SimplifyOps — Discussion / TODO

---

## Gateway: behavior for unknown senders

When a message arrives from someone not on the whitelist, what should happen?

Current behavior: **silent drop** — no reply, sender gets no indication the bot exists.

Options to discuss:
1. **Silent drop** (current) — most secure, no surface area
2. **Rejection message** — send "You're not authorized to use this service"
3. **Waitlist flow** — sender gets "You've been added to the waitlist", request queued in people-whitelist web UI for admin approval
4. **Forward to owner** — Tony gets a Telegram notification: "Unknown user X tried to reach James — approve?" with inline approve/deny

Option 3 or 4 would make full use of the people-whitelist app (which was built for this).
