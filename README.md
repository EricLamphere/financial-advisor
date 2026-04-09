# Financial Advisor Dashboard

A local-first spending dashboard that connects to your credit cards (Capital One, Fidelity, etc.) via Plaid, syncs transactions into a local SQLite database, and displays interactive charts in a Streamlit UI.

## Prerequisites

- Python 3.11+
- A [Plaid account](https://dashboard.plaid.com/) (free for development/sandbox)

## Setup

**1. Clone and install**
```bash
cd financial-advisor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**2. Configure credentials**
```bash
cp .env.example .env
```

Edit `.env` with your Plaid credentials from [dashboard.plaid.com](https://dashboard.plaid.com/):
```
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox
DATABASE_PATH=./financial_advisor.db
```

> **Security note:** `.env` and `*.db` are gitignored. The database file contains your Plaid access tokens — keep it local and do not commit it. For production use, consider encrypting the database or storing access tokens in your OS keychain.

## Running the Dashboard

```bash
task start
```

This launches the Plaid Link server (port 5001) and Streamlit dashboard (port 8501) in parallel. Open [http://localhost:8501](http://localhost:8501) in your browser.

To start them individually:
```bash
task link       # Plaid Link server only
task dashboard  # Streamlit dashboard only
```

## Connecting Accounts

1. Go to the **Accounts** page in the dashboard
2. Click **+ Connect Account** — this opens the Plaid Link flow in a new tab
3. Search for your institution and log in securely
4. Return to the dashboard and click **Sync Now** in the sidebar

## Development: Seed Sandbox Data

To populate data without going through the Link UI:
```bash
python scripts/seed_sandbox.py
```

This creates sandbox accounts for Chase and Bank of America with realistic test transactions.

## Running Tests

```bash
task test
```

Runs unit and E2E tests with coverage (no Plaid credentials needed).

Additional test tasks:
```bash
task test:all    # Includes integration tests (requires Plaid sandbox credentials)
task test:unit   # Unit tests only
task test:watch  # Re-runs on file changes (requires pytest-watcher)
```

## Architecture

```
src/
├── config.py               # Env var loading with fail-fast validation
├── plaid_client.py         # Plaid API wrapper (link token, exchange, sync)
├── db/
│   ├── models.py           # Frozen dataclasses: Account, Transaction
│   ├── schema.py           # SQLite table creation
│   └── repository.py       # All SQL (repository pattern, parameterized queries)
├── sync/
│   └── transaction_sync.py # Cursor-based incremental sync engine
├── link/
│   └── server.py           # Flask server for Plaid Link OAuth flow
└── dashboard/
    ├── app.py              # Streamlit entry point + sidebar
    ├── pages/              # Overview, Categories, Merchants, Timeline, Accounts
    └── components/         # Reusable filters and chart builders
```

**Key design decisions:**
- **Cursor-based sync** — only fetches new/modified/deleted transactions after the first sync
- **Repository pattern** — all SQL isolated in one class; no SQL elsewhere
- **Immutable dataclasses** — `frozen=True` throughout; no mutation
- **Separate Flask server** — Plaid Link requires a browser JS widget that Streamlit can't host natively
- **Env-only secrets** — no credentials ever touch source code or get written to committed files
