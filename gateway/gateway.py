#!/usr/bin/env python3
"""
SimplifyOps controlled gateway for James (Hermes).

Flow:
  Telegram poll -> identity check -> whitelist/governance -> runtime bridge -> Hermes -> reply -> Telegram
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, "/home/pi")
from pi_logging import get_logger

log = get_logger("james-gateway")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN not set")
    sys.exit(1)

HERMES_BIN = "/home/pi/.local/bin/hermes"
WHITELIST_FILE = Path(__file__).parent / "whitelist" / "whitelist.md"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mKJHF]")
TIMEOUT = 300


def load_whitelist() -> set[int]:
    """Load allowed Telegram user IDs from whitelist.md."""
    ids = set()
    if not WHITELIST_FILE.exists():
        log.warning("Whitelist file not found: %s", WHITELIST_FILE)
        return ids
    for line in WHITELIST_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                ids.add(int(line))
            except ValueError:
                log.warning("Invalid whitelist entry: %s", line)
    return ids


def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{API}/getUpdates", params=params, timeout=35)
    r.raise_for_status()
    return r.json().get("result", [])


def send_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    if r.ok:
        log.info("Sent reply to chat_id=%s (%d chars)", chat_id, len(text))
    else:
        log.error("sendMessage failed: %d %s", r.status_code, r.text[:200])


def send_typing(chat_id):
    try:
        requests.post(f"{API}/sendChatAction",
                      json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except Exception as e:
        log.warning("send_typing failed: %s", e)


def governance_check(user_id: int, whitelist: set[int]) -> tuple[bool, str]:
    """Returns (approved, reason)."""
    if user_id not in whitelist:
        return False, f"user {user_id} not in whitelist"
    return True, "approved"


def call_hermes(text: str) -> str:
    """Runtime bridge: call Hermes simplifyops profile with the approved message."""
    cmd = [HERMES_BIN, "-p", "simplifyops", "-z", text]
    env = {**os.environ, "TERM": "dumb", "NO_COLOR": "1"}
    log.info("Runtime handoff to Hermes: %.80s", text)
    t0 = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env)
        elapsed = int((time.time() - t0) * 1000)
        output = ANSI_RE.sub("", result.stdout + result.stderr).strip()
        if result.returncode != 0 and not output:
            log.error("Hermes exited %d with no output after %dms", result.returncode, elapsed)
            return "(James encountered an error — check /home/pi/logs/james-gateway.log)"
        log.info("Hermes responded in %dms (%d chars)", elapsed, len(output))
        return output or "(no response)"
    except subprocess.TimeoutExpired:
        log.error("Hermes timed out after %ds", TIMEOUT)
        return "(request timed out)"
    except Exception as e:
        log.error("Hermes call failed: %s", e, exc_info=True)
        return f"(error: {e})"


def main():
    log.info("James gateway started")
    offset = None

    while True:
        try:
            # Reload whitelist each poll loop so changes take effect without restart
            whitelist = load_whitelist()

            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user_id = msg["from"]["id"]
                text = msg.get("text", "").strip()

                if not text:
                    continue

                # --- Identity + governance check ---
                approved, reason = governance_check(user_id, whitelist)
                log.info("Message from user_id=%s: governance=%s reason=%s", user_id, approved, reason)

                if not approved:
                    log.warning("Blocked message from user_id=%s: %s", user_id, reason)
                    continue  # silently drop — don't reveal the gateway exists

                # --- Runtime handoff ---
                send_typing(chat_id)
                reply = call_hermes(text)

                # --- Outbound control ---
                send_message(chat_id, reply)

        except requests.RequestException as e:
            log.warning("Network error: %s — retrying in 5s", e)
            time.sleep(5)
        except Exception as e:
            log.error("Unexpected error: %s", e, exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
