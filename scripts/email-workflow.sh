#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HIMALAYA_BIN="${HIMALAYA_BIN:-himalaya}"
HIMALAYA_ACCOUNT="${HIMALAYA_ACCOUNT:-simplifyops}"
WORK_DIR="${EMAIL_WORKFLOW_DIR:-$ROOT_DIR/.email-workflow}"
DRAFT_DIR="$WORK_DIR/drafts"
JOB_DIR="$WORK_DIR/jobs"
mkdir -p "$DRAFT_DIR" "$JOB_DIR"

usage() {
  cat <<'EOF'
Usage:
  email-workflow.sh review [limit]
  email-workflow.sh draft <draft-file|->
  email-workflow.sh send-after-approval approved <draft-file|->

Environment:
  HIMALAYA_BIN        Himalaya executable (default: himalaya)
  HIMALAYA_ACCOUNT    Himalaya account name (default: simplifyops)
  EMAIL_WORKFLOW_DIR  Override local workflow storage directory

Behavior:
  review               Lists unread mail in INBOX so you can decide what to answer
  draft                Saves a raw RFC822 draft to Gmail Drafts via IMAP and keeps a local copy
  send-after-approval  Requires the literal word "approved" and schedules
                       the send for exactly one hour later in local time
EOF
}

require_himalaya() {
  command -v "$HIMALAYA_BIN" >/dev/null 2>&1 || {
    echo "Missing Himalaya executable: $HIMALAYA_BIN" >&2
    exit 1
  }
}

himalaya_cmd() {
  require_himalaya
  "$HIMALAYA_BIN" "$@"
}

now_stamp() {
  date +%Y%m%d-%H%M%S
}

python_schedule() {
  python3 - <<'PY'
from datetime import datetime, timedelta
future = datetime.now().astimezone() + timedelta(hours=1)
print(future.strftime('%Y-%m-%d %H:%M %Z'))
print(future.strftime('%M %H %d %m'))
PY
}

read_input_to_file() {
  local dest="$1"
  if [[ "${2:-}" == "-" || $# -eq 1 ]]; then
    cat > "$dest"
  else
    cp "$2" "$dest"
  fi
}

save_to_gmail_drafts() {
  local raw_file="$1"
  himalaya_cmd message save -a "$HIMALAYA_ACCOUNT" -f Drafts < "$raw_file"
}

review_inbox() {
  local limit="${1:-20}"
  local raw
  raw="$(himalaya_cmd envelope list -a "$HIMALAYA_ACCOUNT" --folder INBOX --output json)"

  RAW_JSON="$raw" LIMIT="$limit" python3 - <<'PY'
import json
import os
import re
import sys

raw = os.environ.get('RAW_JSON', '').strip()
limit = int(os.environ.get('LIMIT', '20'))

try:
    payload = json.loads(raw)
except Exception:
    print(raw)
    sys.exit(0)

if isinstance(payload, list):
    items = payload
elif isinstance(payload, dict):
    items = []
    for key in ('envelopes', 'items', 'messages', 'data', 'results'):
        val = payload.get(key)
        if isinstance(val, list):
            items = val
            break
    if not items:
        items = [payload]
else:
    items = []

unread = []
for item in items:
    if not isinstance(item, dict):
        continue
    flags = item.get('flags') or []
    seen = item.get('seen')
    unread_flag = item.get('unread')
    read_flag = item.get('read')
    is_unread = False
    if unread_flag is True:
        is_unread = True
    elif seen is False:
        is_unread = True
    elif read_flag is False:
        is_unread = True
    elif isinstance(flags, list) and 'Seen' not in flags and 'seen' not in flags:
        is_unread = True
    if is_unread:
        unread.append(item)

if not unread:
    print('No unread mail found in INBOX.')
    sys.exit(0)

for item in unread[:limit]:
    msg_id = str(item.get('id') or item.get('uid') or item.get('message_id') or item.get('seq') or '').strip()
    sender = item.get('from') or item.get('sender') or item.get('author') or item.get('mailbox') or '(unknown sender)'
    subject = item.get('subject') or '(no subject)'
    date = item.get('date') or item.get('received') or item.get('internal_date') or '(unknown date)'
    if isinstance(sender, dict):
        sender = sender.get('name') or sender.get('email') or str(sender)
    print(f'- ID: {msg_id} | From: {sender} | Subject: {subject} | Date: {date}')
PY
}

draft_message() {
  local source="${1:-}"
  [[ -n "$source" ]] || { usage; exit 1; }

  local draft_file="$DRAFT_DIR/draft-$(now_stamp).eml"
  if [[ "$source" == "-" ]]; then
    cat > "$draft_file"
  else
    cp "$source" "$draft_file"
  fi

  save_to_gmail_drafts "$draft_file"
  echo "$draft_file"
}

create_send_job() {
  local draft_file="$1"
  local send_script="$2"

  cat > "$send_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

HIMALAYA_BIN=${HIMALAYA_BIN@Q}
HIMALAYA_ACCOUNT=${HIMALAYA_ACCOUNT@Q}
DRAFT_FILE=${draft_file@Q}

command -v "\$HIMALAYA_BIN" >/dev/null 2>&1 || {
  echo "Missing Himalaya executable: \$HIMALAYA_BIN" >&2
  exit 1
}

"\$HIMALAYA_BIN" -a "\$HIMALAYA_ACCOUNT" message send < "\$DRAFT_FILE"
EOF
  chmod +x "$send_script"
}

schedule_send_after_approval() {
  local approval="$1"
  local draft_src="$2"
  if [[ "$approval" != "approved" ]]; then
    echo "Refusing to schedule send: first argument must be the literal word 'approved'." >&2
    exit 2
  fi

  local draft_file
  draft_file="$DRAFT_DIR/send-$(now_stamp).eml"
  if [[ "$draft_src" == "-" ]]; then
    cat > "$draft_file"
  else
    cp "$draft_src" "$draft_file"
  fi

  local send_script send_time cron_fields
  send_script="$JOB_DIR/send-$(basename "$draft_file" .eml).sh"
  mapfile -t schedule_info < <(python_schedule)
  send_time="${schedule_info[0]}"
  cron_fields="${schedule_info[1]}"

  create_send_job "$draft_file" "$send_script"

  if command -v crontab >/dev/null 2>&1; then
    local current
    current="$(crontab -l 2>/dev/null || true)"
    {
      printf '%s\n' "$current"
      printf '%s /bin/bash %s\n' "$cron_fields" "$send_script"
    } | crontab -
  else
    echo "crontab not found; here's the command to run at $send_time:"
    echo "/bin/bash $send_script"
  fi

  cat <<EOF
Approved email scheduled.
Send time: $send_time
Draft: $draft_file
Job: $send_script
EOF
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    review)
      review_inbox "${1:-20}"
      ;;
    draft)
      [[ $# -ge 1 ]] || { usage; exit 1; }
      draft_message "$1"
      ;;
    send-after-approval)
      [[ $# -ge 2 ]] || { usage; exit 1; }
      schedule_send_after_approval "$1" "$2"
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
