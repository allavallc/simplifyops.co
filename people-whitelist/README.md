# People Whitelist App

Admin-only Google login + whitelist manager.

## Stack
- HTML/CSS/JS frontend
- Node.js + Express backend
- Postgres database
- Google OAuth for admins

## Data model
- `people` is the core table
- each row is a person record
- optional alias/contact fields live on the person row, including Telegram ID and phone number details
- `admin` is a boolean flag on that person, default `false`
- the first person is bootstrapped from `BOOTSTRAP_ADMIN_EMAIL` and is created with `admin = true`

## Run
1. Copy `.env.example` to `.env`
2. Fill in Google OAuth, database, and optional Telegram settings
3. Install dependencies
4. Start the server

## Deployment
- Systemd service: `people-whitelist.service`
- Tailscale access: browse to `http://100.76.27.28:3000/` from a device on the tailnet
- The app also listens on the Pi locally at `http://127.0.0.1:3000/`
- Google OAuth callback follows the current browser host, so the authorized redirect URI must match the URL you actually use to open the app
