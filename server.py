#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  Ebenezer Worship Centre — Taifa                            ║
║  Church Management System — Cloud Server                    ║
║  The Church of Pentecost · Greater Accra   ║
║                                                              ║
║  Zero external dependencies — Pure Python 3 stdlib only     ║
║  Works on:  Railway · Render · VPS · localhost              ║
║                                                              ║
║  SECURITY / RELIABILITY FIXES APPLIED:                      ║
║   - SQL injection in /api/dashboard fixed (parameterized)   ║
║   - SQL injection via arbitrary column names in generic     ║
║     insert/update fixed (schema-validated whitelist)        ║
║   - Path traversal in static file serving fixed             ║
║   - All requests wrapped in error handling — a bad request  ║
║     returns a clean JSON error instead of crashing the      ║
║     server                                                   ║
║   - Server now handles concurrent requests (threaded)       ║
║   - Bulk member import restricted to known member columns   ║
║   - Native HTTPS/TLS support added (optional cert/key)      ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, sys, json, sqlite3, hashlib, hmac, base64, uuid, re, time, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────────
PORT       = int(os.environ.get("PORT", 3000))
HOST       = "0.0.0.0"
SECRET_KEY = os.environ.get("EWC_SECRET", "EWC_TAIFA_COP_2024_CHANGE_THIS_IN_PRODUCTION")

# ── HTTPS / TLS ─────────────────────────────────────────────────────
# If you're on Railway / Render / most PaaS providers, TLS is already
# terminated for you at their edge — you don't need to set these, just
# use the https:// URL they give you and this server can stay on plain
# HTTP behind it.
#
# If you're on a bare VPS (or want the Python process itself to speak
# HTTPS), set these two environment variables to the paths of your
# certificate and private key (e.g. from Let's Encrypt / certbot):
#
#   SSL_CERT_FILE=/etc/letsencrypt/live/yourdomain/fullchain.pem
#   SSL_KEY_FILE=/etc/letsencrypt/live/yourdomain/privkey.pem
#
# When both are set, the server will listen for HTTPS directly.
SSL_CERT = os.environ.get("SSL_CERT_FILE", "").strip()
SSL_KEY  = os.environ.get("SSL_KEY_FILE", "").strip()

# Data dir: /data for Railway/Render (persistent volume), else current dir
_DATA_DIR  = Path("/data") if Path("/data").exists() else Path(__file__).parent
DB_PATH    = str(_DATA_DIR / "ewc_database.db")
STATIC_DIR = Path(__file__).parent.resolve()

# ─── DATABASE ─────────────────────────────────────────────────────────
def db_conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c

def db_init():
    c = db_conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        ph TEXT DEFAULT '', em TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        ge TEXT DEFAULT 'Male', dob TEXT DEFAULT '',
        ph TEXT DEFAULT '', ph2 TEXT DEFAULT '',
        em TEXT DEFAULT '', oc TEXT DEFAULT '',
        emp TEXT DEFAULT '', mar TEXT DEFAULT 'Single',
        nch INTEGER DEFAULT 0, adr TEXT DEFAULT '',
        gps TEXT DEFAULT '', ht TEXT DEFAULT '',
        cel TEXT DEFAULT 'None', min TEXT DEFAULT 'None',
        rank TEXT DEFAULT 'Member', hgb TEXT DEFAULT 'No',
        jd TEXT DEFAULT '', hj TEXT DEFAULT 'Baptism',
        bap TEXT DEFAULT '', st TEXT DEFAULT 'active',
        ecn TEXT DEFAULT '', ecp TEXT DEFAULT '',
        ecr TEXT DEFAULT '', nid TEXT DEFAULT '',
        nokN TEXT DEFAULT '', nokP TEXT DEFAULT '',
        nokR TEXT DEFAULT '', nts TEXT DEFAULT '',
        photo TEXT DEFAULT '',
        registration_source TEXT DEFAULT 'admin',
        assembly TEXT DEFAULT 'English',
        created TEXT DEFAULT (datetime('now')),
        updated TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS tithes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT DEFAULT '', mid INTEGER DEFAULT 0,
        cat TEXT DEFAULT '', amt REAL DEFAULT 0,
        mth TEXT DEFAULT 'Cash', rcv TEXT DEFAULT '',
        ref TEXT DEFAULT '', not_ TEXT DEFAULT '',
        assembly TEXT DEFAULT 'English',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT DEFAULT '', cat TEXT DEFAULT '',
        desc TEXT DEFAULT '', amt REAL DEFAULT 0,
        paid TEXT DEFAULT '', vph TEXT DEFAULT '',
        memId INTEGER DEFAULT 0, mth TEXT DEFAULT 'Cash',
        appr TEXT DEFAULT '', rec TEXT DEFAULT '',
        fund TEXT DEFAULT 'General Fund', budg REAL DEFAULT 0,
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', service TEXT DEFAULT '',
        saved TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        att_id INTEGER, member_id INTEGER, status TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS converts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        ge TEXT DEFAULT '', dt TEXT DEFAULT '',
        ph TEXT DEFAULT '', age INTEGER DEFAULT 0,
        inv TEXT DEFAULT '', how TEXT DEFAULT '',
        adr TEXT DEFAULT '', prev TEXT DEFAULT '',
        fuby TEXT DEFAULT '', fust TEXT DEFAULT 'Pending',
        cell TEXT DEFAULT 'Not assigned',
        bap TEXT DEFAULT 'No', bapdx TEXT DEFAULT '',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS beneficiaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nm TEXT DEFAULT '', ph TEXT DEFAULT '',
        dt TEXT DEFAULT '', type TEXT DEFAULT '',
        need TEXT DEFAULT '', supp TEXT DEFAULT '',
        amt REAL DEFAULT 0, memId INTEGER DEFAULT 0,
        rel TEXT DEFAULT '', appr TEXT DEFAULT '',
        st TEXT DEFAULT 'Pending', nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT DEFAULT '', dt TEXT DEFAULT '',
        end_dt TEXT DEFAULT '', time_ TEXT DEFAULT '',
        ven TEXT DEFAULT '', cat TEXT DEFAULT '',
        org TEXT DEFAULT '', desc TEXT DEFAULT '',
        budg REAL DEFAULT 0, exp INTEGER DEFAULT 0,
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS prayer_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mid INTEGER DEFAULT 0, dt TEXT DEFAULT '',
        req TEXT DEFAULT '', cat TEXT DEFAULT '',
        st TEXT DEFAULT 'Open', upd TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS weekly_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL DEFAULT '',
        svcType TEXT DEFAULT '', preacher TEXT DEFAULT '',
        men INTEGER DEFAULT 0, women INTEGER DEFAULT 0,
        children INTEGER DEFAULT 0, youth INTEGER DEFAULT 0,
        visitors INTEGER DEFAULT 0, offering REAL DEFAULT 0,
        souls INTEGER DEFAULT 0, hgb INTEGER DEFAULT 0,
        waterBap INTEGER DEFAULT 0, lordSupper INTEGER DEFAULT 0,
        followup INTEGER DEFAULT 0, bibleRead INTEGER DEFAULT 0,
        bibleClass INTEGER DEFAULT 0, bibleAtt INTEGER DEFAULT 0,
        cell1 INTEGER DEFAULT 0, cell2 INTEGER DEFAULT 0,
        cell3 INTEGER DEFAULT 0, cellMtg INTEGER DEFAULT 0,
        cellSouls INTEGER DEFAULT 0, prayerMtg INTEGER DEFAULT 0,
        outreach INTEGER DEFAULT 0, outSouls INTEGER DEFAULT 0,
        outAtt INTEGER DEFAULT 0, tracts INTEGER DEFAULT 0,
        minMtg INTEGER DEFAULT 0, minSouls INTEGER DEFAULT 0,
        tithe REAL DEFAULT 0, welfare REAL DEFAULT 0,
        health REAL DEFAULT 0, educ REAL DEFAULT 0,
        donate REAL DEFAULT 0, schol REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', type TEXT DEFAULT '',
        memId INTEGER DEFAULT 0, name TEXT DEFAULT '',
        ge TEXT DEFAULT '', ph TEXT DEFAULT '',
        rank TEXT DEFAULT '', from_assembly TEXT DEFAULT '',
        to_assembly TEXT DEFAULT '', dist TEXT DEFAULT '',
        area TEXT DEFAULT '', reason TEXT DEFAULT '',
        recBy TEXT DEFAULT '', st TEXT DEFAULT 'Pending',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS outreach (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', loc TEXT DEFAULT '',
        type TEXT DEFAULT '', led TEXT DEFAULT '',
        team INTEGER DEFAULT 0, att INTEGER DEFAULT 0,
        souls INTEGER DEFAULT 0, hgb INTEGER DEFAULT 0,
        tracts INTEGER DEFAULT 0, followup TEXT DEFAULT '',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS ministry_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', min TEXT DEFAULT '',
        type TEXT DEFAULT '', fac TEXT DEFAULT '',
        att INTEGER DEFAULT 0, souls INTEGER DEFAULT 0,
        hgb INTEGER DEFAULT 0, dur REAL DEFAULT 0,
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS holy_ghost_baptisms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', memId INTEGER DEFAULT 0,
        name TEXT DEFAULT '', ge TEXT DEFAULT '',
        age INTEGER DEFAULT 0, svc TEXT DEFAULT '',
        minister TEXT DEFAULT '', conv TEXT DEFAULT '',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS special_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', cat TEXT DEFAULT '',
        title TEXT DEFAULT '', desc TEXT DEFAULT '',
        person TEXT DEFAULT '', wit TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS scholarships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', type TEXT DEFAULT '',
        name TEXT DEFAULT '', memId INTEGER DEFAULT 0,
        inst TEXT DEFAULT '', level TEXT DEFAULT '',
        amt REAL DEFAULT 0, period TEXT DEFAULT '',
        appr TEXT DEFAULT '', st TEXT DEFAULT 'Pending',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT '', cat TEXT DEFAULT '',
        brand TEXT DEFAULT '', model TEXT DEFAULT '',
        serial TEXT DEFAULT '', qty INTEGER DEFAULT 1,
        date TEXT DEFAULT '', how TEXT DEFAULT 'Purchased',
        val REAL DEFAULT 0, supplier TEXT DEFAULT '',
        receipt TEXT DEFAULT '', loc TEXT DEFAULT '',
        assigned TEXT DEFAULT '', status TEXT DEFAULT 'Good',
        warranty TEXT DEFAULT '', lastSvc TEXT DEFAULT '',
        nextSvc TEXT DEFAULT '', notes TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now')),
        updated TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', eqId INTEGER DEFAULT 0,
        desc TEXT DEFAULT '', by TEXT DEFAULT '',
        cost REAL DEFAULT 0, next TEXT DEFAULT '',
        status TEXT DEFAULT 'Resolved', notes TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS member_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT DEFAULT '',
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        ge TEXT DEFAULT '', dob TEXT DEFAULT '',
        ph TEXT DEFAULT '', ph2 TEXT DEFAULT '',
        em TEXT DEFAULT '', oc TEXT DEFAULT '',
        emp TEXT DEFAULT '', mar TEXT DEFAULT '',
        nch INTEGER DEFAULT 0, adr TEXT DEFAULT '',
        gps TEXT DEFAULT '', ht TEXT DEFAULT '',
        rank TEXT DEFAULT 'Member',
        nokN TEXT DEFAULT '', nokP TEXT DEFAULT '',
        nokR TEXT DEFAULT '', nts TEXT DEFAULT '',
        photo TEXT DEFAULT '', status TEXT DEFAULT 'pending',
        submitted TEXT DEFAULT (datetime('now')),
        reviewed TEXT DEFAULT '', reviewed_by TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS water_baptisms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT DEFAULT '', memId INTEGER DEFAULT 0,
        convertId INTEGER DEFAULT 0,
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        ge TEXT DEFAULT '', age INTEGER DEFAULT 0,
        ph TEXT DEFAULT '', svc TEXT DEFAULT '',
        minister TEXT DEFAULT '', venue TEXT DEFAULT '',
        assembly TEXT DEFAULT 'English',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS backsliders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memId INTEGER DEFAULT 0,
        fn TEXT DEFAULT '', ln TEXT DEFAULT '',
        ge TEXT DEFAULT '', ph TEXT DEFAULT '',
        adr TEXT DEFAULT '',
        dateLeft TEXT DEFAULT '', reason TEXT DEFAULT '',
        lastSeen TEXT DEFAULT '',
        follower TEXT DEFAULT '', cell TEXT DEFAULT '',
        status TEXT DEFAULT 'Being Followed',
        dateWon TEXT DEFAULT '',
        assembly TEXT DEFAULT 'English',
        nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now')),
        updated TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS church_config (
        key TEXT PRIMARY KEY, value TEXT DEFAULT ''
    );
    INSERT OR IGNORE INTO church_config VALUES
        ('name','Ebenezer Worship Centre - Taifa'),
        ('district',''),
        ('area','Greater Accra Area'),
        ('pastor',''), ('elder',''), ('phone',''),
        ('email',''), ('addr',''), ('svcTime','8:00 AM'),
        ('adminKey','COP2024TAIFA'),
        ('c1l',''), ('c1d','Tuesday'),
        ('c2l',''), ('c2d','Wednesday'),
        ('c3l',''), ('c3d','Thursday'),
        ('mtnName',''),('mtnNo',''),('mtnNote',''),
        ('telName',''),('telNo',''),('telNote',''),
        ('atName',''),('atNo',''),('atNote',''),
        ('bankName',''),('bankNo',''),('bankAcct',''),('bankBranch','');
    """)
    c.commit()

    # ══════════════════════════════════════════════════════════════════
    # SAFE MIGRATIONS — runs on EVERY startup
    # ══════════════════════════════════════════════════════════════════
    # Rule: NEVER drops tables, NEVER deletes data.
    # ALTER TABLE ADD COLUMN is non-destructive — if column exists,
    # SQLite raises OperationalError which we silently catch and skip.
    # This means you can deploy a new server.py at any time without
    # losing any existing data in the database.
    # ══════════════════════════════════════════════════════════════════
    _safe_migrations = [
        # tithes — assembly support (Akan / English)
        "ALTER TABLE tithes ADD COLUMN assembly TEXT DEFAULT 'English'",

        # members — extra fields added over time
        "ALTER TABLE members ADD COLUMN registration_source TEXT DEFAULT 'admin'",
        "ALTER TABLE members ADD COLUMN assembly TEXT DEFAULT 'English'",
        "ALTER TABLE members ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN updated TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE members ADD COLUMN ph2 TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN em TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nokN TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nokP TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nokR TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecn TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecp TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecr TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nid TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN gps TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ht TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN emp TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN hgb TEXT DEFAULT 'No'",
        "ALTER TABLE members ADD COLUMN rank TEXT DEFAULT 'Member'",
        "ALTER TABLE members ADD COLUMN nts TEXT DEFAULT ''",

        # expenses — budget tracking
        "ALTER TABLE expenses ADD COLUMN fund TEXT DEFAULT 'General Fund'",
        "ALTER TABLE expenses ADD COLUMN budg REAL DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN nts TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN vph TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN memId INTEGER DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN appr TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN rec TEXT DEFAULT ''",

        # equipment — added later
        "ALTER TABLE equipment ADD COLUMN updated TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE equipment ADD COLUMN receipt TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN warranty TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN lastSvc TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN nextSvc TEXT DEFAULT ''",

        # maintenance — added later
        "ALTER TABLE maintenance ADD COLUMN notes TEXT DEFAULT ''",

        # converts — extra follow-up fields
        "ALTER TABLE converts ADD COLUMN prev TEXT DEFAULT ''",
        "ALTER TABLE converts ADD COLUMN fuby TEXT DEFAULT ''",
        "ALTER TABLE converts ADD COLUMN bapdx TEXT DEFAULT ''",

        # transfers — extra fields
        "ALTER TABLE transfers ADD COLUMN from_assembly TEXT DEFAULT ''",
        "ALTER TABLE transfers ADD COLUMN to_assembly TEXT DEFAULT ''",
        "ALTER TABLE transfers ADD COLUMN recBy TEXT DEFAULT ''",

        # weekly_records — extra metrics
        "ALTER TABLE weekly_records ADD COLUMN svcType TEXT DEFAULT ''",
        "ALTER TABLE weekly_records ADD COLUMN preacher TEXT DEFAULT ''",
        "ALTER TABLE weekly_records ADD COLUMN youth INTEGER DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN visitors INTEGER DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN welfare REAL DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN health REAL DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN educ REAL DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN donate REAL DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN schol REAL DEFAULT 0",

        # member_registrations — review tracking
        "ALTER TABLE member_registrations ADD COLUMN reviewed_by TEXT DEFAULT ''",
        "ALTER TABLE member_registrations ADD COLUMN photo TEXT DEFAULT ''",

        # users — extra profile fields
        "ALTER TABLE users ADD COLUMN ph TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN em TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN created TEXT DEFAULT (datetime('now'))",
    ]

    mig_ok = 0
    mig_skip = 0
    for sql in _safe_migrations:
        try:
            c.execute(sql)
            c.commit()
            mig_ok += 1
        except Exception:
            mig_skip += 1  # Column already exists — completely safe

    if mig_ok > 0:
        print(f"  ✅ Applied {mig_ok} database migrations ({mig_skip} already existed)")

    # Create default admin
    row = c.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if not row:
        pw = _hash_pw("admin123")
        c.execute("INSERT OR IGNORE INTO users(fn,ln,username,password,role) VALUES(?,?,?,?,?)",
                  ("Admin","User","admin",pw,"admin"))
        c.commit()
        print("  ✅ Admin created: username=admin  password=admin123")
    c.close()

# ─── AUTH HELPERS ──────────────────────────────────────────────────────
def _hash_pw(pw):
    salt = uuid.uuid4().hex
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"

def _check_pw(pw, stored):
    try:
        if ':' in stored:
            salt, h = stored.split(':', 1)
            return hmac.compare_digest(
                h, hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000).hex())
        # legacy base64 fallback
        return hmac.compare_digest(base64.b64encode(pw.encode()).decode(), stored)
    except:
        return False

def _make_token(user):
    payload = json.dumps({
        "id": user["id"], "fn": user["fn"],
        "username": user["username"], "role": user["role"],
        "exp": int(time.time()) + 30 * 86400
    })
    b64 = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"

def _verify_token(token):
    try:
        b64, sig = token.rsplit('.', 1)
        expected = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.b64decode(b64).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except:
        return None

# ─── GENERIC DB HELPERS ────────────────────────────────────────────────
ALLOWED_TABLES = {
    "members", "tithes", "expenses", "converts", "beneficiaries",
    "events", "prayer_requests", "weekly_records", "transfers",
    "outreach", "ministry_meetings", "holy_ghost_baptisms",
    "special_events", "scholarships", "users",
    "equipment", "maintenance",
    "water_baptisms", "backsliders"
}

# Columns allowed for bulk member import (whitelist — never trust
# arbitrary keys from an uploaded file/JSON body as SQL column names)
MEMBER_IMPORT_FIELDS = {
    "fn","ln","ge","dob","ph","ph2","em","oc","emp","mar","nch","adr",
    "gps","ht","cel","min","rank","hgb","jd","hj","bap","st","ecn","ecp",
    "ecr","nid","nokN","nokP","nokR","nts","photo","registration_source",
    "assembly"
}

_table_cols_cache = {}

def _table_columns(table):
    """Return the real set of column names for a table, straight from
    SQLite's own schema. Used to whitelist any dict of incoming data
    before it's used to build an INSERT/UPDATE statement, so a request
    body can never inject arbitrary column/SQL via its JSON keys."""
    if table in _table_cols_cache:
        return _table_cols_cache[table]
    if table not in ALLOWED_TABLES:
        return set()
    c = db_conn()
    cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    c.close()
    _table_cols_cache[table] = cols
    return cols

def db_all(table, order="id DESC"):
    c = db_conn()
    rows = [dict(r) for r in c.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()]
    c.close()
    return rows

def db_insert(table, data):
    valid = _table_columns(table)
    data = {k: v for k, v in data.items() if k != "id" and k in valid}
    if table == "users" and "password" in data:
        data["password"] = _hash_pw(data["password"])
    if not data:
        return None
    cols = list(data.keys())
    c = db_conn()
    cur = c.execute(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        [data[k] for k in cols])
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid

def db_update(table, rid, data):
    valid = _table_columns(table)
    data = {k: v for k, v in data.items() if k != "id" and k in valid}
    # Hash password if updating users table
    if table == "users" and "password" in data:
        data["password"] = _hash_pw(data["password"])
    if not data:
        return
    cols = list(data.keys())
    c = db_conn()
    c.execute(
        f"UPDATE {table} SET {','.join(col+'=?' for col in cols)} WHERE id=?",
        [data[k] for k in cols] + [rid])
    c.commit()
    c.close()

def db_delete(table, rid):
    c = db_conn()
    c.execute(f"DELETE FROM {table} WHERE id=?", [rid])
    c.commit()
    c.close()

# ─── HTTP REQUEST HANDLER ──────────────────────────────────────────────
class EWCHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime('%H:%M:%S')
        msg = (args[0] if args else '')[:70]
        if '/api/' in msg or msg.startswith('GET / ') or msg.startswith('GET /r'):
            print(f"  [{ts}] {msg}")

    # ── Response helpers ─────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")

    def send_json(self, code, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def send_ok(self, data=None):
        self.send_json(200, data if data is not None else {"success": True})

    def send_err(self, code, msg):
        self.send_json(code, {"error": str(msg)})

    def read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in request body")

    def get_user(self):
        tok = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
        return _verify_token(tok) if tok else None

    def serve_file(self, name):
        # ── Path traversal protection ──────────────────────────────
        # Resolve the requested path and make sure it's still inside
        # STATIC_DIR before ever touching the filesystem. Rejects
        # things like "../../etc/passwd" or absolute paths.
        name = (name or "").split("?")[0].lstrip("/")
        if not name:
            name = "EbenezerWC_CMS.html"
        try:
            candidate = (STATIC_DIR / name).resolve()
            candidate.relative_to(STATIC_DIR)
        except (ValueError, OSError):
            return self.send_err(403, "Forbidden")

        if not candidate.exists() or not candidate.is_file():
            self.send_err(404, f"File not found: {name}")
            return

        ext_map = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript",
            ".css":  "text/css",
            ".json": "application/json",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".ico":  "image/x-icon",
            ".txt":  "text/plain"
        }
        ct = ext_map.get(candidate.suffix, "application/octet-stream")
        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        # ── Cache-busting ───────────────────────────────────────────
        # This app is a single evolving HTML/JS file. Without explicit
        # no-cache headers, browsers and any CDN/reverse proxy in front
        # of the site (Cloudflare, Railway/Render edge, etc.) can keep
        # serving an OLD cached copy after a deploy — which looks
        # exactly like "the site is broken" even though the new code
        # is live. These headers force every request to always fetch
        # the current version straight from this server.
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Surrogate-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    # ── OPTIONS (CORS preflight) ─────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ── Top-level dispatchers: catch ANY exception so a single bad   ──
    # ── request (malformed JSON, unexpected value, DB hiccup, etc.)  ──
    # ── returns a clean JSON error instead of crashing the request   ──
    # ── thread or hanging the connection.                            ──
    def do_GET(self):
        try:
            self._do_GET()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self._safe_err(500, f"Internal server error: {e}")

    def do_POST(self):
        try:
            self._do_POST()
        except ValueError as e:
            self._safe_err(400, str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self._safe_err(500, f"Internal server error: {e}")

    def do_PUT(self):
        try:
            self._do_PUT()
        except ValueError as e:
            self._safe_err(400, str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self._safe_err(500, f"Internal server error: {e}")

    def do_DELETE(self):
        try:
            self._do_DELETE()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self._safe_err(500, f"Internal server error: {e}")

    def _safe_err(self, code, msg):
        try:
            self.send_err(code, msg)
        except Exception:
            pass  # headers may already be partially sent; nothing more we can do

    # ── GET ──────────────────────────────────────────────────────────
    def _do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        # Static files
        if path == "/" or path == "":
            return self.serve_file("EbenezerWC_CMS.html")
        if path in ("/register", "/register.html"):
            return self.serve_file("register.html")
        if not path.startswith("/api"):
            return self.serve_file(path.lstrip("/"))

        # API — require auth
        user = self.get_user()
        if not user:
            return self.send_err(401, "Unauthorised — please log in")

        # /api/dashboard  — supports ?assembly=English|Akan|all
        if path == "/api/dashboard":
            qs = parse_qs(urlparse(self.path).query)
            asm = qs.get("assembly", ["all"])[0]
            c = db_conn()
            if asm == "all":
                mem  = c.execute("SELECT COUNT(*) FROM members WHERE st='active'").fetchone()[0]
                inc  = c.execute("SELECT COALESCE(SUM(amt),0) FROM tithes").fetchone()[0]
                inc_eng = c.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='English' OR assembly IS NULL OR assembly=''").fetchone()[0]
                inc_akn = c.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='Akan'").fetchone()[0]
                mem_eng = c.execute("SELECT COUNT(*) FROM members WHERE st='active' AND (assembly='English' OR assembly IS NULL OR assembly='')").fetchone()[0]
                mem_akn = c.execute("SELECT COUNT(*) FROM members WHERE st='active' AND assembly='Akan'").fetchone()[0]
            elif asm == "English":
                # Parameterized — no more f-string SQL injection here.
                mem  = c.execute(
                    "SELECT COUNT(*) FROM members WHERE st='active' AND (assembly='English' OR assembly IS NULL OR assembly='')"
                ).fetchone()[0]
                inc  = c.execute(
                    "SELECT COALESCE(SUM(amt),0) FROM tithes WHERE (assembly='English' OR assembly IS NULL OR assembly='')"
                ).fetchone()[0]
                inc_eng = inc_akn = 0
                mem_eng = mem_akn = 0
            else:
                mem  = c.execute(
                    "SELECT COUNT(*) FROM members WHERE st='active' AND assembly=?", [asm]
                ).fetchone()[0]
                inc  = c.execute(
                    "SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly=?", [asm]
                ).fetchone()[0]
                inc_eng = inc_akn = 0
                mem_eng = mem_akn = 0
            exp  = c.execute("SELECT COALESCE(SUM(amt),0) FROM expenses").fetchone()[0]
            souls= c.execute("SELECT COALESCE(SUM(souls+outSouls+minSouls+cellSouls),0) FROM weekly_records").fetchone()[0]
            hgb  = c.execute("SELECT COUNT(*) FROM holy_ghost_baptisms").fetchone()[0]
            pend = c.execute("SELECT COUNT(*) FROM member_registrations WHERE status='pending'").fetchone()[0]
            bday = c.execute("""SELECT COUNT(*) FROM members WHERE
                strftime('%m-%d',dob) BETWEEN
                strftime('%m-%d','now') AND
                strftime('%m-%d','now','+7 days')""").fetchone()[0]

            # ── New metrics: baptisms, souls won, backsliders ─────────
            baptisms       = c.execute("SELECT COUNT(*) FROM water_baptisms").fetchone()[0]
            souls_won      = c.execute("SELECT COUNT(*) FROM converts").fetchone()[0]
            backsliders_following = c.execute(
                "SELECT COUNT(*) FROM backsliders WHERE status='Being Followed'"
            ).fetchone()[0]
            backsliders_won = c.execute(
                "SELECT COUNT(*) FROM backsliders WHERE status='Won Back'"
            ).fetchone()[0]
            backsliders_total = c.execute("SELECT COUNT(*) FROM backsliders").fetchone()[0]

            c.close()
            return self.send_ok({
                "members":mem, "income":float(inc), "expenses":float(exp),
                "balance":float(inc)-float(exp), "souls":int(souls or 0),
                "hgb":int(hgb), "pending":int(pend), "birthdays":int(bday),
                "income_english":float(inc_eng), "income_akan":float(inc_akn),
                "members_english":int(mem_eng), "members_akan":int(mem_akn),
                "baptisms":int(baptisms), "souls_won":int(souls_won),
                "backsliders_following":int(backsliders_following),
                "backsliders_won":int(backsliders_won),
                "backsliders_total":int(backsliders_total)
            })

        # /api/config
        if path == "/api/config":
            c = db_conn()
            cfg = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM church_config").fetchall()}
            c.close()
            return self.send_ok(cfg)

        # /api/attendance
        if path == "/api/attendance":
            c = db_conn()
            sessions = [dict(r) for r in c.execute("SELECT * FROM attendance ORDER BY date DESC").fetchall()]
            recs     = c.execute("SELECT * FROM attendance_records").fetchall()
            c.close()
            rec_map = {}
            for r in recs:
                rec_map.setdefault(r["att_id"], {})[str(r["member_id"])] = r["status"]
            for s in sessions:
                s["records"] = rec_map.get(s["id"], {})
            return self.send_ok(sessions)

        # /api/pending-registrations
        if path == "/api/pending-registrations":
            c = db_conn()
            rows = [dict(r) for r in c.execute(
                "SELECT * FROM member_registrations WHERE status='pending' ORDER BY submitted DESC"
            ).fetchall()]
            c.close()
            return self.send_ok(rows)

        # /api/<table>
        seg = path.replace("/api/", "").split("/")[0]
        if seg in ALLOWED_TABLES:
            order_map = {
                "tithes":"dt DESC","expenses":"dt DESC",
                "weekly_records":"date DESC","outreach":"date DESC","transfers":"date DESC",
                "water_baptisms":"date DESC","backsliders":"dateLeft DESC"
            }
            return self.send_ok(db_all(seg, order_map.get(seg, "id DESC")))

        self.send_err(404, "Not found")

    # ── POST ─────────────────────────────────────────────────────────
    def _do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        data = self.read_body()

        # ── Public endpoints (no auth) ────────────────────────────
        if path == "/api/login":
            c = db_conn()
            u = c.execute("SELECT * FROM users WHERE username=? AND active=1",
                          [data.get("username","")]).fetchone()
            c.close()
            if not u or not _check_pw(data.get("password",""), u["password"]):
                return self.send_err(401, "Invalid username or password")
            token = _make_token(dict(u))
            return self.send_ok({"token": token, "user": {
                "id":u["id"],"fn":u["fn"],"ln":u["ln"],
                "username":u["username"],"role":u["role"]
            }})

        if path == "/api/register":
            fn,ln = data.get("fn","").strip(), data.get("ln","").strip()
            uname = data.get("username","").strip()
            pw    = data.get("password","")
            if not all([fn,ln,uname,pw]):
                return self.send_err(400, "Missing required fields")
            if len(pw) < 6:
                return self.send_err(400, "Password must be at least 6 characters")
            c = db_conn()
            cfg = c.execute("SELECT value FROM church_config WHERE key='adminKey'").fetchone()
            akey = cfg["value"] if cfg else "COP2024TAIFA"
            ex   = c.execute("SELECT id FROM users WHERE username=?", [uname]).fetchone()
            c.close()
            if ex:
                return self.send_err(409, "Username already taken")
            if data.get("role") == "admin" and data.get("adminKey","") != akey:
                return self.send_err(403, "Invalid admin registration key")
            rid = db_insert("users", {
                "fn":fn,"ln":ln,"username":uname,
                "password":pw,
                "role":data.get("role","user"),
                "ph":data.get("ph",""),"em":data.get("em","")
            })
            return self.send_ok({"success":True,"id":rid})

        if path == "/api/self-register":
            token = data.get("token","")
            c = db_conn()
            v = c.execute("SELECT value FROM church_config WHERE key=?",
                          ["reg_token_"+token]).fetchone()
            c.close()
            if not v or v["value"] != "active":
                return self.send_err(403, "Invalid or expired registration link")
            fields = ["fn","ln","ge","dob","ph","ph2","em","oc","emp","mar","nch",
                      "adr","gps","ht","rank","nokN","nokP","nokR","nts","photo"]
            row = {f: data.get(f,"") for f in fields}
            row.update({"token":token,"status":"pending"})
            db_insert("member_registrations", row)
            return self.send_ok({"success":True,"message":"Registration submitted!"})

        # ── Authenticated endpoints ───────────────────────────────
        user = self.get_user()
        if not user:
            return self.send_err(401, "Unauthorised — please log in")

        # Registration link generator
        if path == "/api/registration-link":
            token = uuid.uuid4().hex
            c = db_conn()
            c.execute("INSERT OR REPLACE INTO church_config(key,value) VALUES(?,?)",
                      ["reg_token_"+token,"active"])
            c.commit(); c.close()
            base = f"https://{self.headers.get('Host','localhost')}"
            link = f"{base}/register.html?token={token}"
            msg  = (f"Dear church member,\n\nPlease register your membership details "
                    f"with Ebenezer Worship Centre — Taifa using this link:\n\n{link}\n\n"
                    f"Fill in all details carefully on your phone or computer.\n\nGod bless you!")
            return self.send_ok({"link":link,"token":token,"message":msg})

        # Approve pending registration
        m = re.match(r'^/api/approve-registration/(\d+)$', path)
        if m:
            rid = int(m.group(1))
            c = db_conn()
            reg = c.execute("SELECT * FROM member_registrations WHERE id=?", [rid]).fetchone()
            c.close()
            if not reg:
                return self.send_err(404, "Registration not found")
            reg = dict(reg)
            fields = ["fn","ln","ge","dob","ph","ph2","em","oc","emp","mar","nch",
                      "adr","gps","ht","rank","nokN","nokP","nokR","nts","photo"]
            member = {f: reg.get(f,"") for f in fields}
            member.update({
                "jd": datetime.now().strftime("%Y-%m-%d"),
                "hj":"New birth","st":"active",
                "registration_source":"self_registration"
            })
            db_insert("members", member)
            c = db_conn()
            c.execute("UPDATE member_registrations SET status='approved',"
                      "reviewed=datetime('now'),reviewed_by=? WHERE id=?",
                      [user.get("fn","admin"), rid])
            c.commit(); c.close()
            return self.send_ok()

        # Reject registration
        m = re.match(r'^/api/reject-registration/(\d+)$', path)
        if m:
            c = db_conn()
            c.execute("UPDATE member_registrations SET status='rejected',"
                      "reviewed=datetime('now'),reviewed_by=? WHERE id=?",
                      [user.get("fn","admin"), int(m.group(1))])
            c.commit(); c.close()
            return self.send_ok()

        # Attendance save
        if path == "/api/attendance":
            date_, svc = data.get("date",""), data.get("service","")
            records    = data.get("records",{})
            c = db_conn()
            ex = c.execute("SELECT id FROM attendance WHERE date=? AND service=?",
                           [date_,svc]).fetchone()
            if ex:
                att_id = ex["id"]
                c.execute("DELETE FROM attendance_records WHERE att_id=?", [att_id])
            else:
                cur    = c.execute("INSERT INTO attendance(date,service) VALUES(?,?)",[date_,svc])
                att_id = cur.lastrowid
            for mid,status in records.items():
                c.execute("INSERT INTO attendance_records(att_id,member_id,status) VALUES(?,?,?)",
                          [att_id,mid,status])
            c.commit(); c.close()
            return self.send_ok({"success":True,"id":att_id})

        # Bulk member import — column names are whitelisted against
        # MEMBER_IMPORT_FIELDS (and again against the real schema
        # inside db_insert) so an uploaded file can never smuggle in
        # arbitrary SQL via its column/key names.
        if path == "/api/import-members":
            rows = data if isinstance(data, list) else data.get("members", [])
            imported = 0
            skipped = 0
            for row in rows:
                if not isinstance(row, dict):
                    skipped += 1
                    continue
                row = {k: v for k, v in row.items() if k in MEMBER_IMPORT_FIELDS}
                ph  = str(row.get("ph","")).strip()
                asm = row.get("assembly","English")
                fn  = str(row.get("fn","")).strip()
                ln  = str(row.get("ln","")).strip()
                conn2 = db_conn()
                exists = conn2.execute(
                    "SELECT id FROM members WHERE fn=? AND ln=? AND assembly=?",
                    [fn, ln, asm]
                ).fetchone()
                conn2.close()
                if exists:
                    skipped += 1
                    continue
                db_insert("members", row)
                imported += 1
            return self.send_ok({"success": True, "imported": imported, "skipped": skipped})

        # Weekly records — upsert on duplicate date
        if path == "/api/weekly_records":
            date_ = data.get("date","")
            data.pop("id",None)
            if date_:
                c = db_conn()
                ex = c.execute("SELECT id FROM weekly_records WHERE date=?",[date_]).fetchone()
                c.close()
                if ex:
                    db_update("weekly_records", ex["id"], data)
                    return self.send_ok({"success":True,"id":ex["id"]})
            rid = db_insert("weekly_records", data)
            return self.send_ok({"success":True,"id":rid})

        # Generic table insert
        seg = path.replace("/api/","").split("/")[0]
        if seg in ALLOWED_TABLES:
            data.pop("id",None)
            rid = db_insert(seg, data)
            return self.send_ok({"success":True,"id":rid})

        self.send_err(404, "Not found")

    # ── PUT ──────────────────────────────────────────────────────────
    def _do_PUT(self):
        path = urlparse(self.path).path.rstrip("/")
        user = self.get_user()
        if not user:
            return self.send_err(401, "Unauthorised")
        data = self.read_body()

        # Config update
        if path == "/api/config":
            c = db_conn()
            for k,v in data.items():
                c.execute("INSERT OR REPLACE INTO church_config(key,value) VALUES(?,?)",[k,v])
            c.commit(); c.close()
            return self.send_ok()

        # Generic table update
        m = re.match(r'^/api/(\w+)/(\d+)$', path)
        if m and m.group(1) in ALLOWED_TABLES:
            data.pop("id",None)
            db_update(m.group(1), int(m.group(2)), data)
            return self.send_ok()

        self.send_err(404, "Not found")

    # ── DELETE ───────────────────────────────────────────────────────
    def _do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        user = self.get_user()
        if not user:
            return self.send_err(401, "Unauthorised")

        m = re.match(r'^/api/(\w+)/(\d+)$', path)
        if m and m.group(1) in ALLOWED_TABLES:
            db_delete(m.group(1), int(m.group(2)))
            return self.send_ok()

        self.send_err(404, "Not found")


# ─── THREADED SERVER ────────────────────────────────────────────────
# Plain http.server.HTTPServer handles one request at a time. Under
# any real concurrency (a few phones hitting the dashboard together,
# a slow client, a long import) later requests just stall. This mixes
# in threading so each connection gets its own thread; SQLite
# connections are opened per-call in db_conn(), so this is safe.
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


# ─── ENTRY POINT ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║  Ebenezer Worship Centre — Taifa CMS Server                 ║
║  The Church of Pentecost · Greater Accra                    ║
╚══════════════════════════════════════════════════════════════╝""")

    print(f"\n  📂 Database: {DB_PATH}")
    db_init()

    server = ThreadingHTTPServer((HOST, PORT), EWCHandler)

    scheme = "http"
    if SSL_CERT and SSL_KEY:
        if not Path(SSL_CERT).exists() or not Path(SSL_KEY).exists():
            print(f"\n  ⚠️  SSL_CERT_FILE or SSL_KEY_FILE path does not exist — "
                  f"falling back to plain HTTP.\n"
                  f"     SSL_CERT_FILE={SSL_CERT}\n"
                  f"     SSL_KEY_FILE={SSL_KEY}\n")
        else:
            try:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(certfile=SSL_CERT, keyfile=SSL_KEY)
                # Reasonable modern defaults
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                server.socket = ctx.wrap_socket(server.socket, server_side=True)
                scheme = "https"
            except Exception as e:
                print(f"\n  ⚠️  Failed to load SSL cert/key ({e}) — falling back to plain HTTP.\n")

    print(f"""
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📱  Local:   {scheme}://localhost:{PORT}
  🌐  Network: {scheme}://0.0.0.0:{PORT}
  🔑  Login:   admin / admin123
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
    if scheme == "http":
        print("""  ℹ️   Running over plain HTTP.
      • On Railway / Render / most PaaS hosts: this is fine — their
        edge proxy already terminates HTTPS for you, so the public
        URL they give you is already https:// even though this
        process itself speaks HTTP.
      • On a bare VPS and want THIS process to speak HTTPS directly:
        set environment variables SSL_CERT_FILE and SSL_KEY_FILE to
        point at a certificate/key pair (e.g. from Let's Encrypt),
        then restart.
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
    print("""  ✅  Server running (multi-threaded) — press Ctrl+C to stop
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  🙏 Server stopped. Database saved. Goodbye!")
        server.server_close()
