---
minimum_authority: admin
status: active
---

# Self-Knowledge Sources

Allowlist for `scripts/build_agent_self_knowledge.py`. Each source lists explicit section headings to
extract (the heading plus its body, up to the next heading of equal or higher level). Only reviewed,
non-secret documents belong here. Never add environment files, live runtime config, auth/session data,
audit logs, or infrastructure inventories.

## Output

- `knowledge/about-myself/generated/self-knowledge.md`

## Sources

### knowledge/about-myself/capabilities.md

Reason: Reviewed description of James's identity, capabilities, and disclosure boundaries.

Sections:
- What I Am
- What I Can Do
- How I Work
- What I Will Not Do
