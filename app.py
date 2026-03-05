from flask import Flask, render_template, request, jsonify, send_file, abort, g
import sqlite3
import csv
import io
import os
from datetime import datetime

DB_PATH = "rsvp.db"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "replace_this_token")  # замените при деплое
BOT_USERNAME = os.environ.get("BOT_USERNAME", "your_bot_username")  # без @

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["JSON_AS_ASCII"] = False

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS guests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                  )""")
    db.commit()

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.before_request
def setup():
    init_db()

@app.route("/")
def index():
    # Передаём username бота, и дату церемонии
    ceremony_date = "2026-06-20T15:30:00"  # можно изменить
    return render_template("index.html",
                           bot_username=BOT_USERNAME,
                           ceremony_date=ceremony_date)

@app.route("/rsvp", methods=["POST"])
def rsvp():
    data = request.get_json() or {}
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    status = (data.get("status") or "").strip()  # ожидается "буду" или "возможно"

    if not first or not last or status not in ("буду", "возможно"):
        return jsonify({"ok": False, "error": "invalid_input"}), 400

    db = get_db()
    created_at = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO guests (first_name, last_name, status, created_at) VALUES (?, ?, ?, ?)",
        (first, last, status, created_at)
    )
    db.commit()
    # Возвращаем deep link на бота, можно добавить start-параметр если нужно
    bot_link = f"https://t.me/{BOT_USERNAME}"
    return jsonify({"ok": True, "bot_link": bot_link})

@app.route("/admin/export")
def admin_export():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        abort(403)
    db = get_db()
    cur = db.execute("SELECT id, first_name, last_name, status, created_at FROM guests ORDER BY created_at")
    rows = cur.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "first_name", "last_name", "status", "created_at"])
    for r in rows:
        writer.writerow([r["id"], r["first_name"], r["last_name"], r["status"], r["created_at"]])

    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8")),
                     mimetype="text/csv",
                     download_name="guests.csv",
                     as_attachment=True)

if __name__ == "__main__":
    # Для локального запуска на Windows: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)