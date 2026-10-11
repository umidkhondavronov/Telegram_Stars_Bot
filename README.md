# Telegram Stars Bot — Stage 1

Stage 1 includes:
- Telegram user registration
- PostgreSQL database
- Internal wallet
- Stars package catalog
- Transaction history
- Admin balance credit/debit
- Basic Stars order creation

## 1. Requirements

- Python 3.11+
- Docker Desktop
- A Telegram bot token from @BotFather

## 2. Setup

Copy `.env.example` to `.env` and fill in:
- `BOT_TOKEN`
- `ADMIN_ID`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (must use the same password)

Example:
`postgresql+asyncpg://stars_bot:change_me@localhost:5432/stars_bot`

## 3. Start PostgreSQL

```bash
docker compose up -d
```

## 4. Install Python dependencies

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Run

```bash
python -m bot.main
```

## Notes

This is deliberately Stage 1. The "Buy Stars" action creates an order and deducts the wallet balance, but it does NOT yet deliver Stars. Stage 2 will add the payment/deposit workflow, and the Stars fulfillment mechanism should be integrated only after confirming the current official Telegram mechanism.

For production, add migrations (Alembic), stronger audit logging, idempotency, and deployment secrets management before handling real customer funds.
