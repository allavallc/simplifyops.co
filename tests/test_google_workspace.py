"""Tests for the Google Workspace OAuth service (story-59). Pure — only build_auth_url (no I/O)."""

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "admin_api"))

import google_workspace as gw  # noqa: E402


def test_build_auth_url_has_offline_consent_and_scopes():
    url = gw.build_auth_url("st4te", client_id="cid.apps", redirect_uri="https://h/integrations/google/callback")
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert q["access_type"] == ["offline"]          # required to receive a refresh_token
    assert q["prompt"] == ["consent"]
    assert q["response_type"] == ["code"]
    assert q["client_id"] == ["cid.apps"]
    assert q["redirect_uri"] == ["https://h/integrations/google/callback"]
    assert q["state"] == ["st4te"]
    scope = q["scope"][0]
    for s in ("calendar", "gmail.modify", "drive", "spreadsheets"):
        assert s in scope


def test_default_redirect_uri_is_separate_from_login_callback():
    # Derived workspace callback must differ from the admin-login /auth/callback path.
    assert gw.WORKSPACE_REDIRECT_URI.endswith("/integrations/google/callback")
    assert "/auth/callback" not in gw.WORKSPACE_REDIRECT_URI
