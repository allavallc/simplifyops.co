# Hana Unified Ingress (FastAPI)

Single entry point for all inbound channels.

## Canonical endpoint
- `POST /messages`

## Supported sources now
- `millis`
- `telegram` (webhook relay mode)

## Compatibility endpoint
- `POST /hana/respond` (maps to `source=millis`)

## Env
```bash
PORT=8080
HERMES_API_URL=http://localhost:3000/chat
HERMES_API_KEY=
MILLIS_WEBHOOK_SECRET=
TELEGRAM_WEBHOOK_SECRET=
HERMES_TIMEOUT_SECONDS=2.3
```

## Run
```bash
cd /home/pi/simplifyops/hana-bridge-millis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Millis config
- URL: `https://<public>/messages`
- Method: `POST`
- Add header: `X-Source: millis`
- Response JSON field: `response`

## Telegram relay mode (for true single ingress)
- Set Telegram bot webhook to `https://<public>/messages`
- Add header or payload marker so source resolves to `telegram`
- Keep a relay sender to post Hermes reply back to Telegram chat

## Notes
- `session_id` is normalized per source (`millis_<call_id>`, `telegram_<chat_id>`)
- Service is stateless. Context lives in Hermes.
