from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from sqlite3 import connect, Row
import os
import secrets
import bot

app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
)

SECRET_KEY_FILE = '.flask_secret_key'
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'rb') as f:
        app.secret_key = f.read()
else:
    app.secret_key = os.urandom(64)
    with open(SECRET_KEY_FILE, 'wb') as f:
        f.write(app.secret_key)

ADMIN_PASSWD_FILE = '.admin_passwd'
if os.path.exists(ADMIN_PASSWD_FILE):
    with open(ADMIN_PASSWD_FILE) as f:
        random_password = f.read().strip()
else:
    random_password = os.urandom(64).hex()
    with open(ADMIN_PASSWD_FILE, 'w') as f:
        f.write(random_password)

PASSWD_COL_FILE = '.passwd_col'
if os.path.exists(PASSWD_COL_FILE):
    with open(PASSWD_COL_FILE) as f:
        PASSWD_COL = f.read().strip()
else:
    PASSWD_COL = f'passwd_{secrets.token_hex(3)}'
    with open(PASSWD_COL_FILE, 'w') as f:
        f.write(PASSWD_COL)


def get_db():
    con = connect('data.db')
    con.row_factory = Row
    return con

def db_setup():
    con = get_db()
    cur = con.cursor()

    needs_rebuild = False
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cur.fetchall()]
        if PASSWD_COL not in cols:
            needs_rebuild = True
        else:
            cur.execute("SELECT COUNT(*) FROM users WHERE id BETWEEN 0 AND 255")
            if cur.fetchone()[0] < 256:
                needs_rebuild = True
        if needs_rebuild:
            cur.execute("DROP TABLE users")

    cur.execute(f'''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    {PASSWD_COL} TEXT NOT NULL,
                    message TEXT
                )''')

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        for i in range(256):
            cur.execute(
                f"INSERT INTO users (id, username, {PASSWD_COL}, message) VALUES (?, ?, ?, ?)",
                (i, f'_b{i}', '', chr(i))
            )
        cur.execute(f"INSERT INTO users (id, username, {PASSWD_COL}, message) VALUES (?, ?, ?, ?)", (1000, 'admin', random_password, 'Hello from admin!'))
        cur.execute(f"INSERT INTO users (id, username, {PASSWD_COL}, message) VALUES (?, ?, ?, ?)", (1001, 'bob', 'bob123', 'Hey its bob here!'))
        cur.execute(f"INSERT INTO users (id, username, {PASSWD_COL}, message) VALUES (?, ?, ?, ?)", (1002, 's1mple', 's1mple@123@123', 'Hey its s1mple here!'))
    else:
        cur.execute(f"UPDATE users SET {PASSWD_COL} = ? WHERE username = 'admin'", (random_password,))
    con.commit()
    con.close()


@app.route('/')
def home():
    return render_template('home.html', title=';)')


@app.route('/search')
def search():
    id = request.args.get('id')
    if not id:
        return jsonify({'error': 'Missing id parameter'}), 400

    banned = [
        "'", '"',
        "and", "or", "--", "#", "/*", "*/", "+", "-", " ", ";", "\n", "\r", "\t",
        "union", "insert", "update", "delete", "drop", "alter", "create", "replace", "truncate",
        "like", "|",
        "\x0b", "\x0c", "\xa0",
        "iif", "case", "when", "waitfor",
        "exec", "sp_", "xp_",
        "char(", "nchar(", "concat",
        "openrowset", "opendatasource","|"
    ]
    lowered = id.lower()
    if any(tok in lowered for tok in banned):
        return jsonify({'error': 'nice one'}), 403

    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(f"SELECT message FROM users WHERE id = {id}")
        row = cur.fetchone()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        con.close()

    if not row:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'message': row['message']}), 200



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username')
    password = request.form.get('password')

    con = get_db()
    cur = con.cursor()
    cur.execute(f"SELECT id, username FROM users WHERE username = ? AND {PASSWD_COL} = ?", (username, password))
    row = cur.fetchone()
    con.close()

    if not row:
        return render_template('login.html', error='Invalid credentials'), 401

    session['user_id'] = row['id']
    session['username'] = row['username']
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/s3cret', methods=['GET'])
def s3cret():
    if session.get('username') != 'admin':
        return redirect(url_for('login'))

    return render_template('s3cret.html')


@app.route('/notes', methods=['GET'])
def get_notes():
    if session.get('username') != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    notes = session.get('notes', [])
    search = request.args.get('search')
    filtered_notes = sorted([note for note in notes if note.startswith(search)]) if search else notes

    return jsonify(filtered_notes)


@app.route('/notes', methods=['POST'])
def post_notes():
    if session.get('username') != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(silent=True) or {}
    note = data.get('note')
    if not note:
        return jsonify({'error': 'empty note'}), 422

    notes = session.get('notes', [])
    notes.append(note)
    session['notes'] = notes

    search = request.args.get('search')
    filtered_notes = sorted([n for n in notes if n.startswith(search)]) if search else notes

    return jsonify(filtered_notes)


@app.route('/report', methods=['GET'])
def report():
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    return render_template('report.html')


@app.route('/api/bot', methods=['POST'])
def api_bot():
    if session.get('username') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'empty url'}), 422

    try:
        bot.visit(url, random_password)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'ok': True})


@app.route('/notes/clear', methods=['POST'])
@app.route('/api/notes/clear', methods=['POST'])
def clear_notes():
    if session.get('username') != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    session['notes'] = []
    return jsonify([])


db_setup()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')