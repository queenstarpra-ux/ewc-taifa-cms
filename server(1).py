#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  Ebenezer Worship Centre — Taifa                                ║
║  Church Management System — Production Server                   ║
║  The Church of Pentecost · Taifa District · Greater Accra       ║
║                                                                  ║
║  ✅ HTTPS-ready (works on Railway, Render, VPS, localhost)       ║
║  ✅ Zero external dependencies — pure Python 3 stdlib            ║
║  ✅ Threaded — handles multiple users simultaneously             ║
║  ✅ Safe migrations — existing data never lost on update         ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, sys, json, sqlite3, hashlib, hmac, base64, uuid, re, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────
PORT       = int(os.environ.get("PORT", 3000))
HOST       = "0.0.0.0"
SECRET_KEY = os.environ.get("EWC_SECRET", "EWC_TAIFA_COP_2024_EBENEZER_CHANGE_THIS")

# DB path: /data for Railway/Render persistent volume, else same folder as script
_DATA_DIR = Path("/data") if Path("/data").exists() else Path(__file__).parent.resolve()
DB_PATH   = str(_DATA_DIR / "ewc_database.db")

# Static files served from same folder as this script
STATIC_DIR = Path(__file__).parent.resolve()


# ─── THREADED SERVER ─────────────────────────────────────────────
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handles each request in a separate thread for concurrent users."""
    daemon_threads = True
    allow_reuse_address = True


# ─── DATABASE ─────────────────────────────────────────────────────
def db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def db_init():
    conn = db_conn()
    conn.executescript("""
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
        fn TEXT DEFAULT '', ln TEXT DEFAULT '', ge TEXT DEFAULT '',
        dt TEXT DEFAULT '', ph TEXT DEFAULT '', age INTEGER DEFAULT 0,
        inv TEXT DEFAULT '', how TEXT DEFAULT '', adr TEXT DEFAULT '',
        prev TEXT DEFAULT '', fuby TEXT DEFAULT '',
        fust TEXT DEFAULT 'Pending', cell TEXT DEFAULT 'Not assigned',
        bap TEXT DEFAULT 'No', bapdx TEXT DEFAULT '', nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS beneficiaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nm TEXT DEFAULT '', ph TEXT DEFAULT '', dt TEXT DEFAULT '',
        type TEXT DEFAULT '', need TEXT DEFAULT '', supp TEXT DEFAULT '',
        amt REAL DEFAULT 0, memId INTEGER DEFAULT 0,
        rel TEXT DEFAULT '', appr TEXT DEFAULT '',
        st TEXT DEFAULT 'Pending', nts TEXT DEFAULT '',
        created TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT DEFAULT '', dt TEXT DEFAULT '', end_dt TEXT DEFAULT '',
        time_ TEXT DEFAULT '', ven TEXT DEFAULT '', cat TEXT DEFAULT '',
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
        date TEXT DEFAULT '', loc TEXT DEFAULT '', type TEXT DEFAULT '',
        led TEXT DEFAULT '', team INTEGER DEFAULT 0,
        att INTEGER DEFAULT 0, souls INTEGER DEFAULT 0,
        hgb INTEGER DEFAULT 0, tracts INTEGER DEFAULT 0,
        followup TEXT DEFAULT '', nts TEXT DEFAULT '',
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
        fn TEXT DEFAULT '', ln TEXT DEFAULT '', ge TEXT DEFAULT '',
        dob TEXT DEFAULT '', ph TEXT DEFAULT '', ph2 TEXT DEFAULT '',
        em TEXT DEFAULT '', oc TEXT DEFAULT '', emp TEXT DEFAULT '',
        mar TEXT DEFAULT '', nch INTEGER DEFAULT 0,
        adr TEXT DEFAULT '', gps TEXT DEFAULT '', ht TEXT DEFAULT '',
        rank TEXT DEFAULT 'Member', assembly TEXT DEFAULT 'English',
        nokN TEXT DEFAULT '', nokP TEXT DEFAULT '',
        nokR TEXT DEFAULT '', nts TEXT DEFAULT '',
        photo TEXT DEFAULT '', status TEXT DEFAULT 'pending',
        submitted TEXT DEFAULT (datetime('now')),
        reviewed TEXT DEFAULT '', reviewed_by TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS church_config (
        key TEXT PRIMARY KEY, value TEXT DEFAULT ''
    );
    INSERT OR IGNORE INTO church_config VALUES
        ('name','Ebenezer Worship Centre - Taifa'),
        ('district',''),('area','Greater Accra Area'),
        ('pastor',''),('elder',''),('phone',''),
        ('email',''),('addr',''),('svcTime','8:00 AM'),
        ('adminKey','COP2024TAIFA'),
        ('c1l',''),('c1d','Tuesday'),
        ('c2l',''),('c2d','Wednesday'),
        ('c3l',''),('c3d','Thursday'),
        ('mtnName',''),('mtnNo',''),('mtnNote',''),
        ('telName',''),('telNo',''),('telNote',''),
        ('atName',''),('atNo',''),('atNote',''),
        ('bankName',''),('bankNo',''),('bankAcct',''),('bankBranch','');
    """)
    conn.commit()

    # ── Safe migrations — add new columns without losing data ────
    _migrations = [
        "ALTER TABLE tithes ADD COLUMN assembly TEXT DEFAULT 'English'",
        "ALTER TABLE members ADD COLUMN assembly TEXT DEFAULT 'English'",
        "ALTER TABLE members ADD COLUMN registration_source TEXT DEFAULT 'admin'",
        "ALTER TABLE members ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN updated TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE members ADD COLUMN ph2 TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN gps TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ht TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN emp TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN hgb TEXT DEFAULT 'No'",
        "ALTER TABLE members ADD COLUMN rank TEXT DEFAULT 'Member'",
        "ALTER TABLE members ADD COLUMN nokN TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nokP TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nokR TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecn TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecp TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN ecr TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nid TEXT DEFAULT ''",
        "ALTER TABLE members ADD COLUMN nts TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN fund TEXT DEFAULT 'General Fund'",
        "ALTER TABLE expenses ADD COLUMN budg REAL DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN nts TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN vph TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN memId INTEGER DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN appr TEXT DEFAULT ''",
        "ALTER TABLE expenses ADD COLUMN rec TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN receipt TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN warranty TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN lastSvc TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN nextSvc TEXT DEFAULT ''",
        "ALTER TABLE equipment ADD COLUMN updated TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE maintenance ADD COLUMN notes TEXT DEFAULT ''",
        "ALTER TABLE member_registrations ADD COLUMN assembly TEXT DEFAULT 'English'",
        "ALTER TABLE member_registrations ADD COLUMN reviewed_by TEXT DEFAULT ''",
        "ALTER TABLE member_registrations ADD COLUMN photo TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN ph TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN em TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN created TEXT DEFAULT (datetime('now'))",
        "ALTER TABLE weekly_records ADD COLUMN svcType TEXT DEFAULT ''",
        "ALTER TABLE weekly_records ADD COLUMN preacher TEXT DEFAULT ''",
        "ALTER TABLE weekly_records ADD COLUMN youth INTEGER DEFAULT 0",
        "ALTER TABLE weekly_records ADD COLUMN visitors INTEGER DEFAULT 0",
        "ALTER TABLE church_config ADD COLUMN value TEXT DEFAULT ''",
    ]
    ok = skip = 0
    for sql in _migrations:
        try:
            conn.execute(sql); conn.commit(); ok += 1
        except Exception:
            skip += 1
    if ok:
        print(f"  ✅ {ok} migration(s) applied ({skip} already existed)")

    # Create default admin if none exists
    row = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if not row:
        pw = _hash_pw("admin123")
        conn.execute(
            "INSERT OR IGNORE INTO users(fn,ln,username,password,role) VALUES(?,?,?,?,?)",
            ("Admin", "User", "admin", pw, "admin"))
        conn.commit()
        print("  ✅ Default admin: username=admin  password=admin123")
        print("     ⚠️  Change this password after first login!")
    conn.close()


# ─── AUTH ─────────────────────────────────────────────────────────
def _hash_pw(pw):
    salt = uuid.uuid4().hex
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"


def _check_pw(pw, stored):
    try:
        if ':' in stored:
            salt, h = stored.split(':', 1)
            return hmac.compare_digest(
                h, hashlib.pbkdf2_hmac(
                    'sha256', pw.encode(), salt.encode(), 100000).hex())
        # Legacy base64 fallback
        return hmac.compare_digest(
            base64.b64encode(pw.encode()).decode(), stored)
    except Exception:
        return False


def _make_token(user):
    payload = json.dumps({
        "id": user["id"], "fn": user["fn"],
        "ln": user.get("ln", ""),
        "username": user["username"], "role": user["role"],
        "exp": int(time.time()) + 30 * 86400
    })
    b64 = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def _verify_token(token):
    try:
        b64, sig = token.rsplit('.', 1)
        expected = hmac.new(
            SECRET_KEY.encode(), b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.b64decode(b64).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ─── DB HELPERS ───────────────────────────────────────────────────
ALLOWED_TABLES = {
    "members", "tithes", "expenses", "converts", "beneficiaries",
    "events", "prayer_requests", "weekly_records", "transfers",
    "outreach", "ministry_meetings", "holy_ghost_baptisms",
    "special_events", "scholarships", "users", "equipment", "maintenance"
}

ORDER_MAP = {
    "tithes": "dt DESC", "expenses": "dt DESC",
    "weekly_records": "date DESC", "outreach": "date DESC",
    "transfers": "date DESC", "attendance": "date DESC",
}


def db_all(table, order="id DESC"):
    conn = db_conn()
    rows = [dict(r) for r in
            conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()]
    conn.close()
    return rows


def db_insert(table, data):
    data = {k: v for k, v in data.items() if k != "id" and v is not None}
    if not data:
        return None
    cols = list(data.keys())
    conn = db_conn()
    cur = conn.execute(
        f"INSERT INTO {table} ({','.join(cols)}) "
        f"VALUES ({','.join(['?']*len(cols))})",
        [data[k] for k in cols])
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def db_update(table, rid, data):
    data = {k: v for k, v in data.items() if k != "id" and v is not None}
    if table == "users" and "password" in data:
        data["password"] = _hash_pw(data["password"])
    if not data:
        return
    cols = list(data.keys())
    conn = db_conn()
    conn.execute(
        f"UPDATE {table} SET {','.join(c+'=?' for c in cols)} WHERE id=?",
        [data[k] for k in cols] + [rid])
    conn.commit()
    conn.close()


def db_delete(table, rid):
    conn = db_conn()
    conn.execute(f"DELETE FROM {table} WHERE id=?", [rid])
    conn.commit()
    conn.close()


def _get_base_url(handler):
    """
    Detect the correct base URL including HTTPS.
    Handles Railway, Render, Nginx reverse proxies via X-Forwarded headers.
    """
    # X-Forwarded-Proto is set by Railway, Render, Nginx, Cloudflare etc.
    proto = handler.headers.get("X-Forwarded-Proto", "")
    if not proto:
        proto = handler.headers.get("X-Forwarded-Ssl", "")
        proto = "https" if proto == "on" else "http"
    if not proto:
        proto = "https" if PORT in (443, 8443) else "http"

    # X-Forwarded-Host or Host header
    host = handler.headers.get("X-Forwarded-Host", "") or \
           handler.headers.get("Host", f"localhost:{PORT}")

    # Remove default ports from display
    if (proto == "http" and host.endswith(":80")) or \
       (proto == "https" and host.endswith(":443")):
        host = host.rsplit(":", 1)[0]

    return f"{proto}://{host}"


# ─── HTTP HANDLER ─────────────────────────────────────────────────
class EWCHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime('%H:%M:%S')
        msg = (args[0] if args else "")[:80]
        if "/api/" in msg or msg.startswith(("GET / ", "GET /r")):
            print(f"  [{ts}] {msg}")

    # ── Helpers ───────────────────────────────────────────────────
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type,Authorization,X-Requested-With")
        self.send_header("Access-Control-Allow-Methods",
                         "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Max-Age", "86400")
        # Security headers for HTTPS
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def send_json(self, code, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def ok(self, data=None):
        self.send_json(200, data if data is not None else {"success": True})

    def err(self, code, msg):
        self.send_json(code, {"error": msg})

    def body(self):
        n = int(self.headers.get("Content-Length", 0))
        if n == 0:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def user(self):
        tok = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
        return _verify_token(tok) if tok else None

    def serve_static(self, name):
        # Sanitize path — prevent directory traversal
        safe = Path(name).name
        p = STATIC_DIR / safe
        if not p.exists() or not p.is_file():
            self.err(404, f"File not found: {safe}")
            return
        ext_ct = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".json": "application/json",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".ico":  "image/x-icon",
            ".txt":  "text/plain; charset=utf-8",
            ".svg":  "image/svg+xml",
        }
        ct = ext_ct.get(p.suffix, "application/octet-stream")
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    # ── OPTIONS (CORS preflight) ──────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        qs     = parse_qs(parsed.query)

        # Static files
        if path in ("/", ""):
            return self.serve_static("EbenezerWC_CMS.html")
        if path in ("/register", "/register.html"):
            return self.serve_static("register.html")
        if not path.startswith("/api"):
            return self.serve_static(path.lstrip("/"))

        # All API routes require auth
        u = self.user()
        if not u:
            return self.err(401, "Unauthorised — please log in")

        # ── GET /api/dashboard ────────────────────────────────────
        if path == "/api/dashboard":
            asm = qs.get("assembly", ["all"])[0]
            conn = db_conn()
            if asm == "all":
                mem     = conn.execute("SELECT COUNT(*) FROM members WHERE st='active'").fetchone()[0]
                inc     = conn.execute("SELECT COALESCE(SUM(amt),0) FROM tithes").fetchone()[0]
                mem_eng = conn.execute("SELECT COUNT(*) FROM members WHERE st='active' AND (assembly='English' OR assembly IS NULL OR assembly='')").fetchone()[0]
                mem_akn = conn.execute("SELECT COUNT(*) FROM members WHERE st='active' AND assembly='Akan'").fetchone()[0]
                inc_eng = conn.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='English' OR assembly IS NULL OR assembly=''").fetchone()[0]
                inc_akn = conn.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='Akan'").fetchone()[0]
            elif asm == "Akan":
                mem     = conn.execute("SELECT COUNT(*) FROM members WHERE st='active' AND assembly='Akan'").fetchone()[0]
                inc     = conn.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='Akan'").fetchone()[0]
                mem_eng = mem_akn = 0; inc_eng = inc_akn = 0
            else:
                mem     = conn.execute("SELECT COUNT(*) FROM members WHERE st='active' AND (assembly='English' OR assembly IS NULL OR assembly='')").fetchone()[0]
                inc     = conn.execute("SELECT COALESCE(SUM(amt),0) FROM tithes WHERE assembly='English' OR assembly IS NULL OR assembly=''").fetchone()[0]
                mem_eng = mem_akn = 0; inc_eng = inc_akn = 0

            exp   = conn.execute("SELECT COALESCE(SUM(amt),0) FROM expenses").fetchone()[0]
            souls = conn.execute("SELECT COALESCE(SUM(souls+outSouls+minSouls+cellSouls),0) FROM weekly_records").fetchone()[0]
            hgb   = conn.execute("SELECT COUNT(*) FROM holy_ghost_baptisms").fetchone()[0]
            pend  = conn.execute("SELECT COUNT(*) FROM member_registrations WHERE status='pending'").fetchone()[0]
            bday  = conn.execute(
                "SELECT COUNT(*) FROM members WHERE dob!='' AND "
                "strftime('%m-%d',dob) BETWEEN "
                "strftime('%m-%d','now') AND strftime('%m-%d','now','+7 days')"
            ).fetchone()[0]
            conn.close()
            return self.ok({
                "members": mem, "income": float(inc), "expenses": float(exp),
                "balance": float(inc) - float(exp), "souls": int(souls or 0),
                "hgb": int(hgb), "pending": int(pend), "birthdays": int(bday),
                "members_english": int(mem_eng), "members_akan": int(mem_akn),
                "income_english": float(inc_eng), "income_akan": float(inc_akn),
            })

        # ── GET /api/config ───────────────────────────────────────
        if path == "/api/config":
            conn = db_conn()
            cfg  = {r["key"]: r["value"] for r in
                    conn.execute("SELECT key,value FROM church_config").fetchall()}
            conn.close()
            return self.ok(cfg)

        # ── GET /api/attendance ───────────────────────────────────
        if path == "/api/attendance":
            conn     = db_conn()
            sessions = [dict(r) for r in
                        conn.execute("SELECT * FROM attendance ORDER BY date DESC").fetchall()]
            recs     = conn.execute("SELECT * FROM attendance_records").fetchall()
            conn.close()
            rec_map  = {}
            for r in recs:
                rec_map.setdefault(r["att_id"], {})[str(r["member_id"])] = r["status"]
            for s in sessions:
                s["records"] = rec_map.get(s["id"], {})
            return self.ok(sessions)

        # ── GET /api/pending-registrations ────────────────────────
        if path == "/api/pending-registrations":
            conn = db_conn()
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM member_registrations WHERE status='pending' "
                "ORDER BY submitted DESC").fetchall()]
            conn.close()
            return self.ok(rows)

        # ── GET /api/<table> ──────────────────────────────────────
        seg = path.replace("/api/", "").split("/")[0]
        if seg in ALLOWED_TABLES:
            return self.ok(db_all(seg, ORDER_MAP.get(seg, "id DESC")))

        self.err(404, "Endpoint not found")

    # ── POST ──────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        data   = self.body()

        # ── Public: login ─────────────────────────────────────────
        if path == "/api/login":
            conn = db_conn()
            row  = conn.execute(
                "SELECT * FROM users WHERE username=? AND active=1",
                [data.get("username", "")]).fetchone()
            conn.close()
            if not row or not _check_pw(data.get("password", ""), row["password"]):
                return self.err(401, "Invalid username or password")
            tok = _make_token(dict(row))
            return self.ok({"token": tok, "user": {
                "id": row["id"], "fn": row["fn"], "ln": row["ln"],
                "username": row["username"], "role": row["role"]
            }})

        # ── Public: register account ──────────────────────────────
        if path == "/api/register":
            fn    = data.get("fn", "").strip()
            ln    = data.get("ln", "").strip()
            uname = data.get("username", "").strip()
            pw    = data.get("password", "")
            if not all([fn, ln, uname, pw]):
                return self.err(400, "Missing required fields")
            if len(pw) < 6:
                return self.err(400, "Password must be at least 6 characters")
            if not re.match(r'^[a-zA-Z0-9_.\-]+$', uname):
                return self.err(400, "Username may only contain letters, numbers, dots, dashes, underscores")
            conn  = db_conn()
            cfg   = conn.execute("SELECT value FROM church_config WHERE key='adminKey'").fetchone()
            akey  = cfg["value"] if cfg else "COP2024TAIFA"
            ex    = conn.execute("SELECT id FROM users WHERE username=?", [uname]).fetchone()
            conn.close()
            if ex:
                return self.err(409, "Username already taken")
            if data.get("role") == "admin" and data.get("adminKey", "") != akey:
                return self.err(403, "Invalid admin registration key")
            rid = db_insert("users", {
                "fn": fn, "ln": ln, "username": uname,
                "password": _hash_pw(pw),
                "role": data.get("role", "user"),
                "ph": data.get("ph", ""), "em": data.get("em", "")
            })
            return self.ok({"success": True, "id": rid})

        # ── Public: member self-registration ──────────────────────
        if path == "/api/self-register":
            token = data.get("token", "")
            conn  = db_conn()
            valid = conn.execute(
                "SELECT value FROM church_config WHERE key=?",
                ["reg_token_" + token]).fetchone()
            conn.close()
            if not valid or valid["value"] != "active":
                return self.err(403, "Invalid or expired registration link")
            fields = ["fn","ln","ge","dob","ph","ph2","em","oc","emp",
                      "mar","nch","adr","gps","ht","rank","assembly",
                      "nokN","nokP","nokR","nts","photo"]
            row = {f: data.get(f, "") for f in fields if data.get(f) is not None}
            row["token"]  = token
            row["status"] = "pending"
            db_insert("member_registrations", row)
            return self.ok({"success": True, "message": "Registration submitted!"})

        # All remaining routes need auth
        u = self.user()
        if not u:
            return self.err(401, "Unauthorised — please log in")

        # ── Generate registration link ────────────────────────────
        if path == "/api/registration-link":
            token    = uuid.uuid4().hex
            base_url = _get_base_url(self)   # ← HTTPS-aware
            link     = f"{base_url}/register.html?token={token}"
            conn     = db_conn()
            conn.execute(
                "INSERT OR REPLACE INTO church_config(key,value) VALUES(?,?)",
                ["reg_token_" + token, "active"])
            conn.commit(); conn.close()
            church = ""
            try:
                conn2 = db_conn()
                row2  = conn2.execute("SELECT value FROM church_config WHERE key='name'").fetchone()
                church = row2["value"] if row2 else "Ebenezer Worship Centre - Taifa"
                conn2.close()
            except Exception:
                church = "Ebenezer Worship Centre - Taifa"
            msg = (f"Dear church member,\n\nPlease register your membership details "
                   f"with {church} using this link:\n\n{link}\n\n"
                   f"Fill in all your details carefully on your phone or computer.\n\n"
                   f"God bless you!")
            return self.ok({"link": link, "token": token, "message": msg})

        # ── Approve pending registration ──────────────────────────
        m = re.match(r'^/api/approve-registration/(\d+)$', path)
        if m:
            rid  = int(m.group(1))
            conn = db_conn()
            reg  = conn.execute(
                "SELECT * FROM member_registrations WHERE id=?", [rid]).fetchone()
            conn.close()
            if not reg:
                return self.err(404, "Registration not found")
            reg = dict(reg)
            fields = ["fn","ln","ge","dob","ph","ph2","em","oc","emp",
                      "mar","nch","adr","gps","ht","rank","assembly",
                      "nokN","nokP","nokR","nts","photo"]
            member = {f: reg.get(f, "") for f in fields}
            member.update({
                "jd": datetime.now().strftime("%Y-%m-%d"),
                "hj": "New birth", "st": "active",
                "registration_source": "self_registration"
            })
            db_insert("members", member)
            conn2 = db_conn()
            conn2.execute(
                "UPDATE member_registrations SET status='approved',"
                "reviewed=datetime('now'),reviewed_by=? WHERE id=?",
                [u.get("fn", "admin"), rid])
            conn2.commit(); conn2.close()
            return self.ok()

        # ── Reject pending registration ───────────────────────────
        m = re.match(r'^/api/reject-registration/(\d+)$', path)
        if m:
            conn = db_conn()
            conn.execute(
                "UPDATE member_registrations SET status='rejected',"
                "reviewed=datetime('now'),reviewed_by=? WHERE id=?",
                [u.get("fn", "admin"), int(m.group(1))])
            conn.commit(); conn.close()
            return self.ok()

        # ── Attendance save ───────────────────────────────────────
        if path == "/api/attendance":
            date_   = data.get("date", "")
            service = data.get("service", "")
            records = data.get("records", {})
            conn    = db_conn()
            ex = conn.execute(
                "SELECT id FROM attendance WHERE date=? AND service=?",
                [date_, service]).fetchone()
            if ex:
                att_id = ex["id"]
                conn.execute("DELETE FROM attendance_records WHERE att_id=?", [att_id])
            else:
                cur    = conn.execute(
                    "INSERT INTO attendance(date,service) VALUES(?,?)", [date_, service])
                att_id = cur.lastrowid
            for mid, status in records.items():
                conn.execute(
                    "INSERT INTO attendance_records(att_id,member_id,status) VALUES(?,?,?)",
                    [att_id, mid, status])
            conn.commit(); conn.close()
            return self.ok({"success": True, "id": att_id})

        # ── Weekly records — upsert on duplicate date ─────────────
        if path == "/api/weekly_records":
            date_ = data.get("date", "")
            data.pop("id", None)
            if date_:
                conn = db_conn()
                ex   = conn.execute(
                    "SELECT id FROM weekly_records WHERE date=?", [date_]).fetchone()
                conn.close()
                if ex:
                    db_update("weekly_records", ex["id"], data)
                    return self.ok({"success": True, "id": ex["id"]})
            rid = db_insert("weekly_records", data)
            return self.ok({"success": True, "id": rid})

        # ── Bulk member import ────────────────────────────────────
        if path == "/api/import-members":
            rows = data if isinstance(data, list) else data.get("members", [])
            imported = skipped = 0
            for row in rows:
                row.pop("id", None)
                fn  = (row.get("fn") or "").strip()
                ln  = (row.get("ln") or "").strip()
                asm = row.get("assembly", "English")
                if not fn or not ln:
                    skipped += 1; continue
                conn = db_conn()
                ex   = conn.execute(
                    "SELECT id FROM members WHERE fn=? AND ln=? AND assembly=?",
                    [fn, ln, asm]).fetchone()
                conn.close()
                if ex:
                    skipped += 1; continue
                db_insert("members", row)
                imported += 1
            return self.ok({"success": True, "imported": imported, "skipped": skipped})

        # ── Config update ─────────────────────────────────────────
        if path == "/api/config":
            conn = db_conn()
            for k, v in data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO church_config(key,value) VALUES(?,?)", [k, v])
            conn.commit(); conn.close()
            return self.ok()

        # ── Generic table INSERT ──────────────────────────────────
        seg = path.replace("/api/", "").split("/")[0]
        if seg in ALLOWED_TABLES:
            data.pop("id", None)
            rid = db_insert(seg, data)
            return self.ok({"success": True, "id": rid})

        self.err(404, "Endpoint not found")

    # ── PUT ───────────────────────────────────────────────────────
    def do_PUT(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        u      = self.user()
        if not u:
            return self.err(401, "Unauthorised")
        data = self.body()

        # Config update
        if path == "/api/config":
            conn = db_conn()
            for k, v in data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO church_config(key,value) VALUES(?,?)", [k, v])
            conn.commit(); conn.close()
            return self.ok()

        # Generic UPDATE
        m = re.match(r'^/api/(\w+)/(\d+)$', path)
        if m and m.group(1) in ALLOWED_TABLES:
            data.pop("id", None)
            db_update(m.group(1), int(m.group(2)), data)
            return self.ok()

        self.err(404, "Endpoint not found")

    # ── DELETE ────────────────────────────────────────────────────
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        u      = self.user()
        if not u:
            return self.err(401, "Unauthorised")
        m = re.match(r'^/api/(\w+)/(\d+)$', path)
        if m and m.group(1) in ALLOWED_TABLES:
            db_delete(m.group(1), int(m.group(2)))
            return self.ok()
        self.err(404, "Endpoint not found")


# ─── ENTRY POINT ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  Ebenezer Worship Centre — Taifa CMS Server                     ║
║  The Church of Pentecost · Taifa District · Greater Accra       ║
╚══════════════════════════════════════════════════════════════════╝""")
    print(f"\n  📂 Database : {DB_PATH}")
    print(f"  📁 Files    : {STATIC_DIR}")
    db_init()
    server = ThreadedHTTPServer((HOST, PORT), EWCHandler)
    print(f"""
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📱  Local:   http://127.0.0.1:{PORT}
  🌐  Cloud:   https://your-app.onrender.com
  🔑  Login:   admin / admin123
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅  Threaded server — handles multiple users
  🔒  HTTPS-ready via X-Forwarded-Proto header
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Press Ctrl+C to stop
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  🙏 Server stopped. Database saved. Goodbye!")
        server.server_close()
