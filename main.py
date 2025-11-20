from flask import Flask, request, render_template, session, redirect, url_for, flash
import requests
from threading import Thread, Event
import time, random, string, os, sqlite3, json

app = Flask(__name__)
app.secret_key = 'k8m2p9x7w4n6q1v5z3c8b7f2j9r4t6y1u3i5o8e2a7s9d4g6h1l3'
app.debug = True

# =============================
# ✅ PERSISTENT APPROVAL SYSTEM
# =============================
DB_APPROVAL = "approvals.db"

def init_approval_db():
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id TEXT PRIMARY KEY,
            username TEXT,
            approved INTEGER
        )
    """)
    conn.commit()
    conn.close()

def is_approved(user_id):
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("SELECT approved FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1

def save_request(user_id, username):
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES(?,?,0)", (user_id, username))
    conn.commit()
    conn.close()

def approve_user_db(user_id):
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("UPDATE users SET approved=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def reject_user_db(user_id):
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE approved=0")
    rows = c.fetchall()
    conn.close()
    return rows

def get_approved_users():
    conn = sqlite3.connect(DB_APPROVAL)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE approved=1")
    rows = c.fetchall()
    conn.close()
    return rows

# =============================
# OLD CODE CONTINUES BELOW — SAFE
# =============================

running_tasks = {}
stop_events = {}
threads = {}

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': '*/*',
}

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
    if 'user_id' not in session:
        session['user_id'] = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return session['user_id']

# =============================
# Middleware (Modified)
# =============================
@app.before_request
def check_approval():
    path = request.path

    if path.startswith('/static') or path == '/favicon.ico':
        return
    if path.startswith('/admin'):
        if path == '/admin/login':
            return
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return
    if path.startswith('/approval'):
        return

    user_id = get_user_id()

    # 🔥 Persistent approval check
    if not is_approved(user_id):
        return redirect(url_for('approval_request'))

# ========== Approval Request ==============
@app.route('/approval_request', methods=['GET','POST'])
def approval_request():
    user_id = get_user_id()

    if is_approved(user_id):
