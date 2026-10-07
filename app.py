import os
import sqlite3
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
import requests

# Configure logging for production and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("TempNumbersApp")

# Panel API & User Credentials
BASE_URL = "https://tempnumbers.net"
MASTER_API_TOKEN = "cd178b8a81baad5256e9792ccbdb5feb3b18fea75dca3302b57f80dc8c9c97e"

# Client Credentials for dynamic authentication
CLIENT_USERNAME = "comebackotp"
CLIENT_PASSWORD = "comebackotp"

# Database path for storing incoming SMS
DB_PATH = "sms_records.db"

app = Flask(__name__)

def init_db():
    """Initializes local SQLite database to store incoming live OTPs."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT,
                phone_number TEXT,
                sender_cli TEXT,
                message_text TEXT,
                client_id TEXT,
                payout TEXT,
                raw_payload TEXT
            )
        """)
        conn.commit()

init_db()

# Cached client bearer token
cached_client_token = None

def get_client_bearer_token(force_refresh=False):
    """
    Authenticates client using username & password via /api/gentoken.php
    and obtains the Bearer token for client-level API operations.
    """
    global cached_client_token
    if cached_client_token and not force_refresh:
        return cached_client_token

    url = f"{BASE_URL}/api/gentoken.php"
    payload = {
        "username": CLIENT_USERNAME,
        "password": CLIENT_PASSWORD
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        logger.info(f"Authenticating client '{CLIENT_USERNAME}' at {url}...")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()

        if data.get("access_token"):
            cached_client_token = data.get("access_token")
            logger.info("Successfully received client Bearer token.")
            return cached_client_token
        elif data.get("token"):
            cached_client_token = data.get("token")
            return cached_client_token
        else:
            logger.error(f"Failed to obtain client token: {data}")
            return None
    except Exception as exc:
        logger.error(f"Error connecting to gentoken.php: {exc}")
        return None

def fetch_client_numbers(page=1, limit=50, client_id=None):
    """
    Fetches numbers allocated or available using tempnumbers API.
    Uses Master Token by default or fallbacks to client token.
    """
    url = f"{BASE_URL}/api/view_mynumbers"
    token = MASTER_API_TOKEN
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    params = {
        "page": page,
        "limit": limit
    }
    if client_id:
        params["clientid"] = client_id

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        return response.json()
    except Exception as exc:
        logger.error(f"Error fetching numbers: {exc}")
        return {"status": "error", "message": str(exc)}

@app.route('/webhook', methods=['POST'])
@app.route('/', methods=['POST'])
def receive_webhook():
    """
    Main Webhook endpoint configured on tempnumbers.net dashboard.
    Captures incoming SMS/OTP sent by the platform.
    """
    payload = request.get_json(silent=True) or request.form.to_dict()
    logger.info(f"Incoming Webhook Payload: {payload}")

    if not payload:
        return jsonify({"status": "error", "message": "No payload received"}), 400

    # Extract fields from webhook format
    client_id = payload.get("clientid", "")
    data_block = payload.get("data", {})

    # If payload is flat or nested
    if isinstance(data_block, dict) and data_block:
        date_time = data_block.get("datetime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        phone_num = data_block.get("num", "")
        sender_cli = data_block.get("cli", "")
        sms_text = data_block.get("sms", "")
        payout = data_block.get("clpayout", data_block.get("inpayout", "0.00"))
    else:
        date_time = payload.get("datetime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        phone_num = payload.get("num", payload.get("phone", ""))
        sender_cli = payload.get("cli", payload.get("sender", ""))
        sms_text = payload.get("sms", payload.get("message", ""))
        payout = payload.get("clpayout", "0.00")

    # Store message in SQLite database
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (received_at, phone_number, sender_cli, message_text, client_id, payout, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date_time, phone_num, sender_cli, sms_text, client_id, str(payout), str(payload)))
            conn.commit()
    except Exception as exc:
        logger.error(f"Error saving message to database: {exc}")

    return jsonify({
        "status": "success",
        "message": "Webhook received and stored successfully"
    }), 200

@app.route('/api/sms', methods=['GET'])
def get_stored_sms():
    """Returns all received SMS/OTPs as JSON."""
    limit = request.args.get('limit', 50, type=int)
    messages = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        for row in cursor.fetchall():
            messages.append(dict(row))
    return jsonify({"status": "success", "count": len(messages), "data": messages})

@app.route('/api/numbers', methods=['GET'])
def get_numbers_endpoint():
    """API endpoint to view allocated numbers for this client."""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    data = fetch_client_numbers(page=page, limit=limit)
    return jsonify(data)

@app.route('/api/token', methods=['GET', 'POST'])
def get_token_endpoint():
    """Generates and returns the latest client bearer token."""
    token = get_client_bearer_token(force_refresh=True)
    if token:
        return jsonify({
            "status": "success",
            "username": CLIENT_USERNAME,
            "token_type": "Bearer",
            "access_token": token
        })
    return jsonify({"status": "error", "message": "Failed to generate client token"}), 500

@app.route('/', methods=['GET'])
def dashboard():
    """Interactive visual dashboard to view live OTPs and allocated numbers."""
    messages = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 30")
        for row in cursor.fetchall():
            messages.append(dict(row))

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TempNumbers - Client OTP & SMS Panel</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background: #0f172a; color: #f8fafc; padding: 20px; }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid #334155; margin-bottom: 24px; }
            .badge { background: #10b981; color: #022c22; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 999px; }
            .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
            .card h3 { color: #38bdf8; margin-bottom: 12px; }
            .btn { background: #2563eb; color: white; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; font-weight: 500; }
            .btn:hover { background: #1d4ed8; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { text-align: left; padding: 12px; border-bottom: 1px solid #334155; font-size: 14px; }
            th { color: #94a3b8; font-weight: 600; }
            .sms-highlight { background: #0284c7; color: white; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 15px; }
            .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .info-box { background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid #334155; }
            .info-box span { font-size: 12px; color: #94a3b8; display: block; }
            .info-box strong { font-size: 14px; word-break: break-all; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h2>OTP & SMS Live Client Receiver</h2>
                    <p style="color: #94a3b8; font-size: 14px;">TempNumbers.net Integrated Receiver</p>
                </div>
                <span class="badge">Online & Active</span>
            </div>

            <div class="info-grid">
                <div class="info-box">
                    <span>Client Username</span>
                    <strong>{{ username }}</strong>
                </div>
                <div class="info-box">
                    <span>Webhook Status</span>
                    <strong style="color: #4ade80;">Listening on /webhook</strong>
                </div>
                <div class="info-box">
                    <span>Quick Links</span>
                    <div style="margin-top: 5px;">
                        <a href="/api/numbers" target="_blank" class="btn" style="padding: 4px 8px; font-size: 12px;">View Numbers</a>
                        <a href="/api/token" target="_blank" class="btn" style="padding: 4px 8px; font-size: 12px; background: #059669;">Get Token</a>
                    </div>
                </div>
            </div>

            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>Live Received OTPs / Messages ({{ messages|length }})</h3>
                    <button onclick="location.reload()" class="btn">Refresh Now</button>
                </div>
                {% if messages %}
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Number</th>
                            <th>Sender (CLI)</th>
                            <th>Message / OTP</th>
                            <th>Payout</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for msg in messages %}
                        <tr>
                            <td>{{ msg['received_at'] }}</td>
                            <td><strong>{{ msg['phone_number'] }}</strong></td>
                            <td><span style="color: #f59e0b;">{{ msg['sender_cli'] }}</span></td>
                            <td><span class="sms-highlight">{{ msg['message_text'] }}</span></td>
                            <td>${{ msg['payout'] }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color: #94a3b8; padding: 20px 0; text-align: center;">No messages received yet. Send a test SMS from the TempNumbers panel.</p>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, messages=messages, username=CLIENT_USERNAME)

if __name__ == '__main__':
    # Initial token generation check on startup
    get_client_bearer_token()
    
    # Run server on port 8080 (standard for Railway, Render, etc.)
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting application on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
