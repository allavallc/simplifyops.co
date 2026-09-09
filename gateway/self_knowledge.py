"""Self-knowledge runtime context (story-64 Phase C1).

Loads the generated, authority-filtered self-knowledge for injection into the runtime handoff:
admin/super_admin receive the full document body; other approved people receive only the public
Summary. Missing, unreadable, or secret-like content is omitted (never a fallback to raw sources).
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SELF_KNOWLEDGE_PATH = REPO_ROOT / "knowledge" / "about-myself" / "generated" / "self-knowledge.md"

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
]

_ADMIN = ("admin", "super_admin")


def _strip_front_matter(text: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def _summary_only(body: str) -> str:
    m = re.search(r"##\s+Summary\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    return m.group(1).strip() if m else ""


def _has_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


def self_knowledge_context(authority: str, path: Path = SELF_KNOWLEDGE_PATH) -> str | None:
    """Authority-filtered self-knowledge for the runtime, or None if it should be omitted.

    admin/super_admin -> full body; others -> public Summary only. Returns None if the file is
    missing/unreadable or looks secret-like (omit, don't fall back)."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if _has_secret(text):
        return None
    body = _strip_front_matter(text)
    result = body if authority in _ADMIN else _summary_only(body)
    return result or None
