"""Lightweight Flask server that handles the Plaid Link OAuth flow.

Run this separately from Streamlit:
    python -m src.link.server

The Streamlit Accounts page opens this server in a new browser tab.
After linking, the user returns to Streamlit and clicks "Sync Now".
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template_string, request

from src.config import load_config
from src.db.connection import get_connection
from src.db.models import Account
from src.db.repository import TransactionRepository
from src.db.schema import initialize_db
from src.plaid_client import PlaidError, PlaidService

app = Flask(__name__)

_LINK_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Connect Your Account</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex;
           justify-content: center; align-items: center; height: 100vh; margin: 0;
           background: #f0f2f5; }
    .card { background: white; border-radius: 12px; padding: 40px; text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); max-width: 400px; }
    button { background: #635bff; color: white; border: none; border-radius: 8px;
             padding: 14px 28px; font-size: 16px; cursor: pointer; margin-top: 16px; }
    button:hover { background: #4f46e5; }
    .status { margin-top: 16px; color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Connect Your Bank Account</h2>
    <p>Securely link your account via Plaid to start tracking your spending.</p>
    <button id="link-btn" onclick="openLink()">Connect Account</button>
    <div class="status" id="status"></div>
  </div>

  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    async function openLink() {
      document.getElementById('link-btn').disabled = true;
      document.getElementById('status').textContent = 'Opening Plaid Link...';

      const handler = Plaid.create({
        token: '{{ link_token }}',
        onSuccess: async function(public_token, metadata) {
          document.getElementById('status').textContent = 'Connecting account...';
          const resp = await fetch('/exchange', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ public_token, metadata }),
          });
          const data = await resp.json();
          if (data.success) {
            window.location.href = '/success';
          } else {
            document.getElementById('status').textContent = 'Error: ' + data.error;
            document.getElementById('link-btn').disabled = false;
          }
        },
        onExit: function(err, metadata) {
          document.getElementById('link-btn').disabled = false;
          if (err) {
            const msg = err.display_message || err.error_message || err.error_code || JSON.stringify(err);
            document.getElementById('status').innerHTML =
              'Error: ' + msg +
              (err.error_code ? ' <code style="font-size:11px;color:#999">[' + err.error_code + ']</code>' : '') +
              '<br><span style="font-size:11px;color:#999">Check the browser console and Flask server log for details.</span>';
            console.error('Plaid Link exit error:', err, metadata);
          } else {
            document.getElementById('status').textContent = 'Cancelled.';
          }
        },
      });
      handler.open();
    }
  </script>
</body>
</html>
"""

_SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Account Connected</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; display: flex;
           justify-content: center; align-items: center; height: 100vh; margin: 0;
           background: #f0f2f5; }
    .card { background: white; border-radius: 12px; padding: 40px; text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); max-width: 400px; }
    .check { font-size: 48px; }
    p { color: #666; }
  </style>
</head>
<body>
  <div class="card">
    <div class="check">✅</div>
    <h2>Account Connected!</h2>
    <p>You can close this tab and return to the dashboard.<br>
       Click <strong>Sync All Accounts</strong> to fetch your transactions.</p>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    config = load_config()
    plaid_service = PlaidService(config)
    try:
        link_token = plaid_service.create_link_token("dashboard_user")
    except PlaidError as exc:
        return f"<h2>Error creating link token: {exc}</h2>", 500
    return render_template_string(_LINK_HTML, link_token=link_token)


@app.route("/exchange", methods=["POST"])
def exchange():
    config = load_config()
    data = request.get_json()
    public_token = data.get("public_token")
    metadata = data.get("metadata", {})

    if not public_token:
        return jsonify({"success": False, "error": "Missing public_token"}), 400

    plaid_service = PlaidService(config)
    try:
        access_token, item_id = plaid_service.exchange_public_token(public_token)
    except PlaidError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

    institution = metadata.get("institution", {})
    institution_name = institution.get("name", "Unknown Institution")
    accounts = metadata.get("accounts", [{}])
    account_meta = accounts[0] if accounts else {}
    account_name = account_meta.get("name", "Account")
    account_type = account_meta.get("subtype", "credit")

    now = datetime.now(timezone.utc).isoformat()
    account = Account(
        id=None,
        plaid_item_id=item_id,
        plaid_access_token=access_token,
        institution_name=institution_name,
        account_name=account_name,
        account_type=account_type,
        created_at=now,
    )

    with get_connection(config.database_path) as conn:
        initialize_db(conn)
        repo = TransactionRepository(conn)
        repo.upsert_account(account)

    return jsonify({"success": True})


@app.route("/success")
def success():
    return render_template_string(_SUCCESS_HTML)


if __name__ == "__main__":
    config = load_config()
    app.run(port=config.link_server_port, debug=False)
