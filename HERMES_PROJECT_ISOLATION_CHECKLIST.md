# Hermes Project Isolation Checklist

Use this checklist when working in this repo to keep Hermes/email setup scoped to SimplifyOps.

## Verify the active Hermes profile

Run:

```bash
echo "$HERMES_HOME"
hermes config path
hermes config env-path
```

Expected:
- `HERMES_HOME` points to a SimplifyOps-specific profile directory
- `hermes config path` points inside that same profile
- `hermes config env-path` points to that profile's `.env`

## Verify email config is project-scoped

Check the mail client config and secret sources:

```bash
readlink -f ~/.config/himalaya/config.toml
```

Then confirm any auth commands or secret lookups are repo/project-specific, not shared with another project.

For this repo, the SimplifyOps mail setup uses:
- `pass show simplifyops/gmail/imap`
- `pass show simplifyops/gmail/smtp`

## Verify local workflow files stay in this repo

These should remain project-local:
- `scripts/email-workflow.sh`
- `.email-workflow/`

## Quick rule of thumb

If another project needs Hermes or email automation, give it:
- its own Hermes profile
- its own config/env files
- its own secret entries
- its own local workflow files

Do not reuse the SimplifyOps workflow unless you explicitly want shared behavior.
