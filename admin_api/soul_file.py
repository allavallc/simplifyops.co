"""Soul (identity) file service (story-60).

The soul file *is* the agent's personality — loaded verbatim by the runtime as `SOUL.md`
(a symlink → `souls/soul.md`). This service reads it, validates a proposed replacement, and writes
it atomically. Content is never logged. No DB import (audit + restart are the caller's job).
"""

import hashlib
import re
import tempfile
from pathlib import Path

SOUL_PATH = Path(__file__).resolve().parent.parent / "souls" / "soul.md"
MAX_BYTES = 256 * 1024

# High-signal secret markers — reject an upload that obviously contains a credential. Kept narrow to
# avoid false positives on legitimate persona prose.
_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),      # OpenAI-style keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),          # AWS access key id
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),      # GitHub token
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  # Slack token
]


def read() -> str:
    return SOUL_PATH.read_text(encoding="utf-8") if SOUL_PATH.exists() else ""


def validate(content: str) -> list[str]:
    """Return a list of problems; empty list means the content is acceptable to write."""
    errors = []
    if not content or not content.strip():
        errors.append("soul file is empty")
    if len(content.encode("utf-8")) > MAX_BYTES:
        errors.append(f"soul file exceeds {MAX_BYTES // 1024} KB limit")
    if any(p.search(content) for p in _SECRET_PATTERNS):
        errors.append("soul file appears to contain secret-like material (keys/tokens)")
    return errors


def write_atomic(content: str) -> dict:
    """Validate then atomically replace the soul file. Returns non-secret metadata (bytes, sha256).
    Raises ValueError on validation failure — nothing is written."""
    errors = validate(content)
    if errors:
        raise ValueError("; ".join(errors))
    data = content.encode("utf-8")
    SOUL_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mktemp(dir=SOUL_PATH.parent, prefix=".soul.md."))
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(SOUL_PATH)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
