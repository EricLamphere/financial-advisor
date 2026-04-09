# Architecture

## What Plaid Does

Plaid is a third-party service that sits between this app and your banks. It handles everything that would otherwise be impossible:

- **Bank authentication** — when you click "Connect Account," Plaid's Link widget (a JS popup) handles the login to Capital One or Fidelity. Your bank credentials never touch this app or its code.
- **Screen scraping / API translation** — Plaid has integrations with thousands of banks. It knows how to talk to each bank's systems and normalizes everything into a consistent format.
- **Transaction data** — Plaid fetches your raw transactions and enriches them: it adds a `merchant_name` (cleaned up from the raw bank string like "WF *WHOLEFDS MKT #123"), and categorizes each transaction (e.g. `FOOD_AND_DRINK`, `TRAVEL`).
- **Access token** — after you authenticate, Plaid gives this app a long-lived `access_token`. From that point on, the app can fetch your transactions at any time without you logging in again.

## What This Repo Does

Everything else — the app's job is essentially "talk to Plaid, store the results, show them nicely."

**Account linking flow** (`src/link/server.py`):
- Hosts a small Flask webpage that loads Plaid's Link JS widget
- When you finish linking, Plaid sends a one-time `public_token` to this server
- The server exchanges it for a permanent `access_token` and saves it to SQLite

**Transaction sync** (`src/plaid_client.py` + `src/sync/transaction_sync.py`):
- Calls Plaid's `/transactions/sync` endpoint with a cursor
- On first sync: fetches all historical transactions
- On subsequent syncs: only fetches what changed since the last cursor (new, modified, deleted) — efficient and incremental
- Stamps each transaction with the local `account_id` and saves to SQLite

**Storage** (`src/db/`):
- SQLite database with three tables: `accounts`, `transactions`, `sync_cursors`
- The repository handles all queries — aggregations by category, merchant, time period

**Dashboard** (`src/dashboard/`):
- Reads from SQLite (never calls Plaid directly)
- Renders charts and tables in Streamlit

## Data Flow

```
Your Bank
    │
    │  (Plaid handles this — you never see it)
    ▼
 Plaid API
    │  access_token + raw transactions
    │
    ▼
PlaidService          ← plaid_client.py wraps the SDK
    │  normalized Transaction objects
    ▼
TransactionSyncer     ← sync engine, manages cursor
    │  upsert/delete
    ▼
SQLite (local DB)     ← repository.py, all SQL here
    │  aggregation queries
    ▼
Streamlit Dashboard   ← reads only from SQLite, never Plaid
```

The key design choice: the dashboard never calls Plaid. Once data is synced into SQLite, everything — charts, filters, merchant breakdowns — is just SQL queries on local data. This makes the dashboard fast and means it works without an internet connection after the last sync.
