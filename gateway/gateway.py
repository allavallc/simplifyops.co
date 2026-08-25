#!/usr/bin/env python3
"""SimplifyOps message gateway — composition root.

Channel-agnostic router for James (Hermes). This file only wires the pieces
together and runs them; the real work lives in focused modules (story-26 split):

  gwdb.py            DB connection + schema
  intake.py          new_request_id / enqueue_message / build_prompt
  governance.py      people governance + unknown-sender queueing + person context
  sessions.py        session history + Hermes session mappings + message cap
  tool_context.py    short-lived MCP tool-context tokens
  hermes_client.py   the ONLY place we talk to the Hermes runtime API (rule 10)
  worker.py          DurableWorkflowWorker (governance -> Hermes -> outbound)
  telegram.py        Telegram adapter + send_outbound
  internal_server.py /internal/reply approval callbacks from the admin UI

Message flow:
  [telegram adapter] -> POST /messages (admin) -> work_items row
  [DurableWorkflowWorker] -> governance -> Hermes -> reply_ready -> outbound send

Adding a new channel: write an adapter module that normalises inbound messages
and calls the admin intake API (or enqueue_message), add a send path to
telegram.send_outbound's dispatch, and start the adapter in main().
"""

import os
import sys

from gwdb import apply_schema
from internal_server import start_internal_server
from logging_setup import get_logger
from telegram import telegram_adapter
from worker import DurableWorkflowWorker

log = get_logger("simplifyops-gateway")


def main():
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        log.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    log.info("James gateway started")
    apply_schema()
    DurableWorkflowWorker().start()
    start_internal_server()
    telegram_adapter()


if __name__ == "__main__":
    main()
