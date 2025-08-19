# Incident Caller

Minimal on-call incident callout tool with automated and manual escalation flows via Twilio.

## Setup

1. Create and populate a `.env` file (see `.env.example`).
2. Install deps:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python app.py
   ```
4. Expose a public URL for Twilio (dev):
   ```bash
   ngrok http 5000
   ```
   Set `PUBLIC_BASE_URL` to the ngrok URL.

## Roster

Edit `roster.py` with your teams and phone tiers. You can add overrides at runtime via code (MVP).

## Twilio

Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. Configure Voice webhook to point to `PUBLIC_BASE_URL`.

