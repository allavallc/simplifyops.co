"""Internal HTTP server — receives approval callbacks from the admin UI at /internal/reply.

Extracted from the gateway.py god-module (story-26).
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from intake import enqueue_message, new_request_id
from logging_setup import get_logger

log = get_logger("simplifyops-gateway")

INTERNAL_PORT = int(os.environ.get("GATEWAY_INTERNAL_PORT", "3001"))


class InternalHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path != "/internal/reply":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))

        channel    = body.get("channel", "telegram")
        from_id    = str(body.get("from_id", ""))
        from_name  = str(body.get("from_name", ""))
        chat_id    = str(body.get("chat_id", ""))
        text       = body.get("text", "")
        request_id = str(body.get("request_id") or new_request_id())

        enqueue_message(request_id, channel, from_id, from_name, chat_id, text, {})

        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def start_internal_server():
    server = HTTPServer(("127.0.0.1", INTERNAL_PORT), InternalHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="internal-server")
    t.start()
    log.info("Internal reply server listening on 127.0.0.1:%d", INTERNAL_PORT)
