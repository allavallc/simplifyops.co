"""Tests for scripts/sync_story_summaries.py (story-37)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync_story_summaries as s  # noqa: E402


def test_check_passes_and_no_duplicate_numbers():
    # _check() returns [] when summaries are in sync and story numbers are unique.
    assert s._check() == []


def test_stories_parse_cleanly():
    active = s.list_stories(s.STORIES)
    archived = s.list_stories(s.ARCHIVE)
    assert active, "expected active story files"
    assert archived, "expected archived story files"
    for st in active + archived:
        assert st["num"] != "?", f"unparsed number in {st['file']}"
        assert st["title"], f"missing title in {st['file']}"


def test_archive_block_is_current():
    # The generated block must be present in the committed stories-archive.md.
    assert s._archive_block() in s.ARCHIVE_MD.read_text()
