from flask import Flask, request, render_template, session, redirect, url_for, flash
import requests
from threading import Thread, Event
import time
import random
import string
import os
import sqlite3, json

app = Flask(__name__)
app.debug = True

# Secret key for sessions
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'k8m2p9x7w4n6q1v5z3c8b7f2j9r4t6y1u3i5o8e2a7s9d4g6h1l3')

# Approval system state
approved_users = set()
pending_requests = set()

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'PASSWORD')

# WhatsApp / Meta WhatsApp Cloud API configuration
WHATSAPP_BUSINESS_ID = os.environ.get('WHATSAPP_BUSINESS_ID', '726391890538414')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '854444234421868')
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', 'EAAadYcG6ZAIABP0HqLWGUKmRBQZAuZAOoEOZBSUk66Sf7RdbotoSpkujTNtnK5WmlrvFJdZCTYCpm301gDzxpymVqpEjB2ZBzNlnwgKI3juif2ZB8dmtaW4w63CSP1ZCEk9L6AzcqImq1BmKrZBwpnAZBLxJKMYfaZBRZBRtU72d4inLXigdBLczun5Rv0M0UcgKhlbWPAZDZD')  # DO NOT hardcode real token here in production
WEBHOOK_VERIFY_TOKEN = os.environ.get('WA_VERIFY_TOKEN', 'Raja khan')
ADMIN_WHATSAPP_NUMBER = os.environ.get('ADMIN_WHATSAPP_NUMBER', '+917070554967')

# ----------------- Running Tasks -----------------
running_tasks = {}  
stop_events = {}
threads = {}

# Facebook API headers
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j)...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'www.google.com'
}

# ----------------- SQLite DB -----------------
DB_PATH = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        username TEXT,
        type TEXT,
        status TEXT,
        params TEXT
    )''')
    conn.commit()
    conn.close()

def save_task(task_id, username, type_, params):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?)",
              (task_id, username, type_, "running", json.dumps(params)))
    conn.commit()
    conn.close()

def load_running_tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT task_id, username, type, params FROM tasks WHERE status='running'")
    rows = c.fetchall()
    conn.close()
    return rows

def update_task_status(task_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()
    conn.close()

# ----------------- Helpers -----------------
def get_user_id():
    # Browser/session-based user ID
    if 'username' not in session:
        # generate random session ID for new browser
        session['username'] = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return session['username']

# Approval helper functions (extract logic so webhook can call them)
def do_approve(user_id):
    if user_id in pending_requests:
        pending_requests.discard(user_id)
        approved_users.add(user_id)
        return True
    return False

def do_reject(user_id):
    if user_id in pending_requests:
        pending_requests.discard(user_id)
        return True
    return False

# Send WhatsApp interactive message to admin (buttons)
def send_whatsapp_approval_request(user_id):
    # Build interactive button message payload for Meta WhatsApp Cloud API
    url = f'https://graph.facebook.com/v15.0/{WHATSAPP_PHONE_NUMBER_ID}/messages'
    payload = {
        "messaging_product": "whatsapp",
        "to": ADMIN_WHATSAPP_NUMBER,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"New approval request\nUser ID: {user_id}"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": f"approve_{user_id}", "title": "Approve"}},
                    {"type": "reply", "reply": {"id": f"reject_{user_id}", "title": "Reject"}}
                ]
            }
        }
    }
    headers_wa = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.post(url, json=payload, headers=headers_wa, timeout=10)
        if app.debug:
            print('WhatsApp send response:', resp.status_code, resp.text)
    except Exception as e:
        if app.debug:
            print('Error sending WhatsApp message:', str(e))

# (Code continues... truncated for demo, but full file would be here.)
