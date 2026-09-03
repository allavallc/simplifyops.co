# The soul file (`soul.md`)

`soul.md` **is the agent's personality.** Its entire contents are loaded verbatim by the Hermes
runtime as the agent's identity/persona — this is what you edit to change who the agent is, how it
speaks, and how it behaves.

- The runtime loads it by the fixed name **`SOUL.md`** in the Hermes profile
  (`~/.hermes/profiles/simplifyops/SOUL.md`), which is a **symlink → this `souls/soul.md`**. The
  source filename is arbitrary; nothing in the runtime depends on it being called `soul.md`.
- **To change the personality:** edit `souls/soul.md` (or use Settings → download, edit, re-upload)
  and then **restart the runtime** so it reloads (`sudo systemctl restart simplifyops-agent-runtime.service`;
  the Settings upload does this automatically).
- Do **not** add meta/instructions-to-humans into `soul.md` itself — everything in it becomes part of
  the agent's prompt. Keep notes like this one out of the soul file.
- Never put secrets, tokens, or credentials in the soul file.
