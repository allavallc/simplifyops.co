"""Regression test for the SSE reply mojibake bug (story-62).

The Hermes runtime streams replies as `text/event-stream` with no charset. `requests` then defaults
`Response.encoding` to ISO-8859-1, so `iter_lines(decode_unicode=True)` mis-decodes the UTF-8 reply
as Latin-1 — turning curly quotes/apostrophes/em-dashes into mojibake. The fix in
`gateway/hermes_client.py` forces `resp.encoding = "utf-8"`. This test pins both halves.
"""

import requests
from requests.utils import get_encoding_from_headers


def test_text_event_stream_defaults_to_latin1():
    # This is the trap: a text/* content type with no charset → ISO-8859-1, not UTF-8.
    assert get_encoding_from_headers({"content-type": "text/event-stream"}) == "ISO-8859-1"


def _sse_response() -> requests.Response:
    r = requests.models.Response()
    # a curly-quoted phrase + em-dash, UTF-8 encoded, as the runtime actually sends it
    r._content = "data: he said “hi” — ok".encode()
    r.headers["Content-Type"] = "text/event-stream"
    # simulate what requests does on the wire: derive encoding from the headers
    r.encoding = get_encoding_from_headers(r.headers)
    return r


def test_default_decoding_mojibakes_smart_punctuation():
    r = _sse_response()  # encoding = ISO-8859-1 (the bug)
    assert "“hi”" not in r.text          # curly quotes lost
    assert "â" in r.text                        # tell-tale 'â' mojibake byte


def test_utf8_override_restores_smart_punctuation():
    r = _sse_response()
    r.encoding = "utf-8"                              # the fix
    assert "he said “hi” — ok" in r.text
