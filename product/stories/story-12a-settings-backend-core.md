# Story 12a - Settings Backend: Core Runtime Settings

## Status
In progress

## Scope
First backend increment for Story 12. Three fields that directly drive James's behavior:
1. Provider and model — writes config.yaml, restarts runtime, clears session mappings
2. Memory URL (Hindsight) — writes config.yaml
3. Session message cap — writes to admin_settings table

## Flow After Save
1. Validate inputs
2. Write to config.yaml (structured read-modify-write, preserve unrelated keys, atomic)
3. Audit with before/after non-secret summary
4. Restart simplifyops-agent-runtime.service via passwordless sudo
5. Clear hermes_session_mappings so next message gets a fresh session with new config
6. Return success

## Passwordless Sudo
Add `/etc/sudoers.d/simplifyops-admin`:
```
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart simplifyops-agent-runtime.service
```

## API Routes
- `GET /api/admin/settings/runtime` — current provider, model, memory URL (non-secret)
- `PATCH /api/admin/settings/runtime` — save provider/model/memory URL
- `PATCH /api/admin/settings/session-health` — save session message cap

## Config Writer Rules
- Use yaml.safe_load / yaml.dump — never text replacement
- Read → modify only target keys → write atomically (temp file + rename)
- Never print or return full config contents
- Never write tracked base template
- Preserve all unrelated keys

## Key Constraints
- config.yaml is environment-owned — never committed to git
- Blank fields preserve existing config values
- All mutations require audit (actor, target, before summary, after summary — no secret values)
- Super admin authority required for runtime/provider changes
