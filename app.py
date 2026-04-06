from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, make_response, abort)
import sqlite3, os, subprocess, hashlib, re, json, base64, pickle, xml.etree.ElementTree as ET, platform

app = Flask(__name__)
app.secret_key = "vulnsite_secret_2024"

DB = "vulnsite.db"

# ── DB HELPERS ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT,
        role TEXT DEFAULT 'user', email TEXT, is_paid INTEGER DEFAULT 0,
        api_key TEXT, balance REAL DEFAULT 100.0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT,
        content TEXT, is_private INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT, flag TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER,
        amount_paid REAL, status TEXT DEFAULT 'pending'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS password_reset (
        id INTEGER PRIMARY KEY, user_id INTEGER, token TEXT, used INTEGER DEFAULT 0
    )""")

    users = [
        (1,"admin", hashlib.md5(b"admin123").hexdigest(), "admin","admin@vulnsite.local",1,"ADMIN_KEY_SECRET_9x7z",9999.0),
        (2,"alice", hashlib.md5(b"password1").hexdigest(),"user", "alice@vulnsite.local",0,"ALICE_KEY_abc123",100.0),
        (3,"bob",   hashlib.md5(b"bob2024").hexdigest(),  "user", "bob@vulnsite.local",  1,"BOB_KEY_xyz456",  50.0),
        (4,"charlie",hashlib.md5(b"charlie99").hexdigest(),"moderator","charlie@vulnsite.local",0,"CHARLIE_KEY_def789",200.0),
    ]
    for u in users:
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,?,?)", u)

    notes = [
        (1,1,"Admin Secret","FLAG{bac_admin_notes_accessed} — internal config token: XK29-ALPHA",1),
        (2,2,"My diary","Today I learned about IDOR vulnerabilities. Very interesting!",1),
        (3,3,"Shopping","Buy milk, eggs, bread",0),
        (4,4,"Meeting notes","FLAG{idor_moderator_note_found} — discussed security audit",1),
    ]
    for n in notes:
        c.execute("INSERT OR IGNORE INTO notes VALUES (?,?,?,?,?)", n)

    products = [
        (1,"Basic Course",   0.0,  "Free intro to web security","FREE_COURSE_CONTENT"),
        (2,"Premium Course", 99.0, "Advanced bug bounty techniques","FLAG{payment_bypass_premium_unlocked}"),
        (3,"VIP Bundle",     299.0,"Everything + private Discord","FLAG{payment_bypass_vip_achieved}"),
    ]
    for p in products:
        c.execute("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", p)

    c.execute("INSERT OR IGNORE INTO password_reset VALUES (1,2,'reset-token-alice-abc123',0)")
    conn.commit()
    conn.close()

# ── HOME ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ════════════════════════════════════════════════════════════════════════════
# MODULE 1 — BROKEN ACCESS CONTROL (BAC)
# ════════════════════════════════════════════════════════════════════════════
@app.route("/bac")
def bac_home():
    return render_template("bac/home.html")

# Login helper for BAC module
@app.route("/bac/login", methods=["GET","POST"])
def bac_login():
    error = None
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        hashed = hashlib.md5(p.encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hashed)).fetchone()
        conn.close()
        if user:
            session["bac_user"] = dict(user)
            return redirect(url_for("bac_dashboard"))
        error = "Invalid credentials"
    return render_template("bac/login.html", error=error)

@app.route("/bac/logout")
def bac_logout():
    session.pop("bac_user", None)
    return redirect(url_for("bac_login"))

@app.route("/bac/dashboard")
def bac_dashboard():
    user = session.get("bac_user")
    if not user:
        return redirect(url_for("bac_login"))
    conn = get_db()
    # Load own notes only — but IDOR is on the /bac/note?id= route
    notes = conn.execute("SELECT * FROM notes WHERE user_id=?", (user["id"],)).fetchall()
    conn.close()
    return render_template("bac/dashboard.html", user=user, notes=[dict(n) for n in notes])

# IDOR — no ownership check
@app.route("/bac/note")
def bac_note():
    user = session.get("bac_user")
    if not user:
        return redirect(url_for("bac_login"))
    note_id = request.args.get("id","2")
    conn = get_db()
    note = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    return render_template("bac/note.html", note=dict(note) if note else None, note_id=note_id, user=user)

# Hidden admin API — only checks login, NOT role
@app.route("/api/admin/settings")
def api_admin_settings():
    if not session.get("bac_user"):
        return jsonify({"error":"Unauthorized"}), 401
    # BUG: no role check — any logged-in user can access this
    return jsonify({
        "flag": "FLAG{bac_admin_api_accessed}",
        "smtp_host": "mail.vulnsite.local",
        "smtp_pass": "S3cr3tMa1lPass!",
        "db_backup_url": "/backup/vulnsite_2024.sql",
        "internal_token": "INT-TOKEN-8f2a9b"
    })

@app.route("/api/admin/keys")
def api_admin_keys():
    if not session.get("bac_user"):
        return jsonify({"error":"Unauthorized"}), 401
    return jsonify({
        "flag": "FLAG{bac_api_keys_exposed}",
        "org_keys": [
            {"org": "Alpha Corp",  "key": "ORG_ALPHA_API_KEY_XYZ123"},
            {"org": "Beta Ltd",    "key": "ORG_BETA_API_KEY_ABC456"},
            {"org": "Gamma Inc",   "key": "ORG_GAMMA_API_KEY_DEF789"},
        ]
    })

@app.route("/api/admin/users/all")
def api_admin_users():
    if not session.get("bac_user"):
        return jsonify({"error":"Unauthorized"}), 401
    conn = get_db()
    users = conn.execute("SELECT id,username,email,role,is_paid,api_key FROM users").fetchall()
    conn.close()
    return jsonify({"flag":"FLAG{bac_all_users_dumped}", "users":[dict(u) for u in users]})

@app.route("/bac/admin")
def bac_admin_panel():
    user = session.get("bac_user")
    if not user:
        return redirect(url_for("bac_login"))
    if user.get("role") != "admin":
        return render_template("bac/forbidden.html", user=user)
    return render_template("bac/admin.html", user=user)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 2 — PAYMENT BYPASS
# ════════════════════════════════════════════════════════════════════════════
@app.route("/payment")
def payment_home():
    user = session.get("pay_user")
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("payment/home.html", user=user, products=[dict(p) for p in products])

@app.route("/payment/login", methods=["GET","POST"])
def payment_login():
    error = None
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        hashed = hashlib.md5(p.encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hashed)).fetchone()
        conn.close()
        if user:
            session["pay_user"] = dict(user)
            return redirect(url_for("payment_home"))
        error = "Invalid credentials"
    return render_template("payment/login.html", error=error)

@app.route("/payment/logout")
def payment_logout():
    session.pop("pay_user", None)
    return redirect(url_for("payment_login"))

# Lab 1: Price modification — price comes from client request body
@app.route("/api/payment/purchase", methods=["POST"])
def api_purchase():
    user = session.get("pay_user")
    if not user:
        return jsonify({"error": "Login required"}), 401
    data = request.get_json() or {}
    product_id = data.get("product_id")
    # VULN: price taken from client, not from DB
    price = float(data.get("price", 99.0))
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    conn.execute("INSERT INTO orders VALUES (NULL,?,?,?,'completed')", (user["id"], product_id, price))
    conn.execute("UPDATE users SET is_paid=1 WHERE id=?", (user["id"],))
    conn.commit()
    content = product["flag"] if price == 0 else product["description"]
    conn.close()
    return jsonify({"success": True, "message": f"Purchased for ${price}", "content": content,
                    "flag": "FLAG{payment_price_modified}" if price <= 0 else None})

# Lab 2: Direct path access — secret download URLs in API response
@app.route("/api/payment/course/<int:product_id>")
def api_course_info(product_id):
    user = session.get("pay_user")
    if not user:
        return jsonify({"error": "Login required"}), 401
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    if not product:
        return jsonify({"error": "Not found"}), 404
    # VULN: secret download path exposed in response regardless of paid status
    return jsonify({
        "id": product["id"],
        "name": product["name"],
        "description": product["description"],
        "download_url": f"/payment/download/{product_id}/secret-token-{product_id*7777}",
        "materials_url": f"/payment/materials/{product_id}"
    })

@app.route("/payment/download/<int:product_id>/secret-token-<int:token>")
def payment_download(product_id, token):
    if token != product_id * 7777:
        abort(404)
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return render_template("payment/download.html", product=dict(product) if product else None)

# Lab 3: Permission bypass — userType check is client-side
@app.route("/api/payment/access-status")
def api_access_status():
    user = session.get("pay_user")
    if not user:
        return jsonify({"error": "Login required"}), 401
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    conn.close()
    return jsonify({"user": u["username"], "userType": "free" if not u["is_paid"] else "paid",
                    "paid": bool(u["is_paid"])})

@app.route("/payment/premium")
def payment_premium():
    user = session.get("pay_user")
    if not user:
        return redirect(url_for("payment_login"))
    return render_template("payment/premium.html", user=user)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 3 — 403 BYPASS
# ════════════════════════════════════════════════════════════════════════════
@app.route("/bypass")
def bypass_home():
    return render_template("bypass/home.html")

def check_403_bypass():
    """Returns flag string if bypass succeeded, else None"""
    path = request.path
    method = request.method
    headers = request.headers

    # Challenge 1: HTTP Verb bypass — GET=403, POST=200
    if "/admin/secret" in path:
        if method == "POST":
            return "FLAG{bypass_verb_override}"
        return None

    # Challenge 2: X-Forwarded-For header bypass
    if "/internal/data" in path:
        xff = headers.get("X-Forwarded-For","")
        if xff in ("127.0.0.1","localhost"):
            return "FLAG{bypass_xff_header}"
        return None

    # Challenge 3: Path encoding — %2F or ../ tricks
    if "/protected/files" in path or "%2F" in request.full_path:
        if "%2e" in path.lower() or "%2f" in path.lower() or "//" in path:
            return "FLAG{bypass_path_encoding}"
        return None

    # Challenge 4: Case bypass — /Sensitive or /SENSITIVE
    raw = request.environ.get("PATH_INFO","")
    if "sensitive" in raw.lower() and raw != "/sensitive/info":
        return "FLAG{bypass_case_sensitive}"
    if raw == "/sensitive/info":
        return None

    # Challenge 5: Trailing slash
    if "/restricted/area/" in path:
        return "FLAG{bypass_trailing_slash}"
    if "/restricted/area" in path and not path.endswith("/"):
        return None

    # Challenge 6: Parameter pollution
    if "/api/user" in path:
        ids = request.args.getlist("id")
        if len(ids) > 1:
            return "FLAG{bypass_param_pollution}"
        return None

    # Challenge 7: X-Original-URL or X-Rewrite-URL header
    if "/local/admin" in path:
        xou = headers.get("X-Original-URL","") or headers.get("X-Rewrite-URL","")
        if xou:
            return "FLAG{bypass_host_header_rewrite}"
        return None

    # Challenge 8: X-HTTP-Method-Override
    if "/api/update" in path:
        override = headers.get("X-HTTP-Method-Override","")
        if override.upper() in ("DELETE","PUT","PATCH"):
            return "FLAG{bypass_method_override}"
        return None

    return None

@app.route("/admin/secret", methods=["GET","POST","PUT","DELETE","PATCH"])
def bypass_admin_secret():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag,"message":"Access granted via verb bypass!"})
    return jsonify({"status":"403 Forbidden","message":"GET requests are not allowed here"}), 403

@app.route("/internal/data")
def bypass_internal_data():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag,"data":{"internal_config":"exposed"}})
    return jsonify({"status":"403 Forbidden","message":"Only internal IPs allowed"}), 403

@app.route("/protected/files")
@app.route("/protected//files")
def bypass_protected_files():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag})
    return jsonify({"status":"403 Forbidden","message":"Access denied"}), 403

@app.route("/sensitive/info")
@app.route("/Sensitive/info")
@app.route("/SENSITIVE/info")
@app.route("/Sensitive/Info")
def bypass_sensitive_info():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag})
    return jsonify({"status":"403 Forbidden","message":"Case-sensitive path restriction"}), 403

@app.route("/restricted/area")
@app.route("/restricted/area/")
def bypass_restricted_area():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag,"message":"Trailing slash bypassed!"})
    return jsonify({"status":"403 Forbidden","message":"Access restricted"}), 403

@app.route("/api/user")
def bypass_api_user():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag,"users":["admin","alice","bob"]})
    return jsonify({"status":"403 Forbidden","message":"Parameter pollution not detected"}), 403

@app.route("/local/admin")
def bypass_local_admin():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag})
    return jsonify({"status":"403 Forbidden","message":"Only localhost admin access"}), 403

@app.route("/api/update", methods=["GET","POST","PUT","DELETE","PATCH"])
def bypass_api_update():
    flag = check_403_bypass()
    if flag:
        return jsonify({"status":"200 OK","flag":flag})
    return jsonify({"status":"403 Forbidden","message":"Method not allowed"}), 403

# ════════════════════════════════════════════════════════════════════════════
# MODULE 4 — SQL INJECTION
# ════════════════════════════════════════════════════════════════════════════
@app.route("/sqli", methods=["GET","POST"])
def sqli():
    result, error, query = None, None, None
    if request.method == "POST":
        username = request.form.get("username","")
        query = f"SELECT id,username,email,role FROM users WHERE username = '{username}'"
        try:
            conn = get_db()
            rows = conn.execute(query).fetchall()
            result = [dict(r) for r in rows]
            conn.close()
        except Exception as e:
            error = str(e)
    return render_template("sqli.html", result=result, error=error, query=query)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 5 — XSS
# ════════════════════════════════════════════════════════════════════════════
@app.route("/xss", methods=["GET","POST"])
def xss():
    message = None
    if request.method == "POST":
        message = request.form.get("message","")
    stored = session.get("xss_stored",[])
    if request.args.get("store"):
        stored.append(request.args.get("store"))
        session["xss_stored"] = stored[-5:]
    return render_template("xss.html", message=message, stored=stored)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 6 — COMMAND INJECTION
# ════════════════════════════════════════════════════════════════════════════
@app.route("/cmdi", methods=["GET","POST"])
def cmdi():
    output, error = None, None
    if request.method == "POST":
        host = request.form.get("host","")
        try:
            ping_flag = "-n" if platform.system() == "Windows" else "-c"
            r = subprocess.run(f"ping {ping_flag} 1 {host}", shell=True, capture_output=True, text=True, timeout=5)
            output = r.stdout + r.stderr
        except Exception as e:
            error = str(e)
    return render_template("cmdi.html", output=output, error=error)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 7 — SSRF
# ════════════════════════════════════════════════════════════════════════════
@app.route("/ssrf", methods=["GET","POST"])
def ssrf():
    result, error = None, None
    if request.method == "POST":
        url = request.form.get("url","")
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=3) as resp:
                result = resp.read(2000).decode(errors="replace")
        except Exception as e:
            error = str(e)
    return render_template("ssrf.html", result=result, error=error)

# Internal-only endpoint (SSRF target)
@app.route("/internal/secret")
def internal_secret():
    host = request.headers.get("Host","")
    if request.remote_addr in ("127.0.0.1","::1"):
        return jsonify({"flag":"FLAG{ssrf_internal_access}","db_password":"S3cr3tDB!","admin_token":"INT-9f2a"})
    return jsonify({"error":"Internal only"}), 403

# ════════════════════════════════════════════════════════════════════════════
# MODULE 8 — OPEN REDIRECT
# ════════════════════════════════════════════════════════════════════════════
@app.route("/redirect")
def open_redirect():
    next_url = request.args.get("next","")
    message = None
    if next_url:
        # VULN: no validation of redirect destination
        if next_url.startswith("http"):
            message = f"FLAG{{open_redirect_external}} — Redirecting to: {next_url}"
            return render_template("redirect.html", message=message, next_url=next_url, triggered=True)
    return render_template("redirect.html", message=message, next_url=next_url, triggered=False)

# ════════════════════════════════════════════════════════════════════════════
# MODULE 9 — SENSITIVE DATA EXPOSURE
# ════════════════════════════════════════════════════════════════════════════
@app.route("/exposure")
def exposure():
    return render_template("exposure.html")

# Backup file exposed (common misconfiguration)
@app.route("/backup/config.bak")
def backup_config():
    return """# Database Configuration - BACKUP FILE
DB_HOST=localhost
DB_NAME=vulnsite
DB_USER=root
DB_PASS=Sup3rS3cr3tPa$$w0rd!
SECRET_KEY=vulnsite_secret_2024
STRIPE_KEY=sk_live_FAKE_FLAG{exposed_backup_file}
SENDGRID_KEY=SG.FAKE_KEY_HERE
ADMIN_TOKEN=ADMIN-INT-TOKEN-8f2a
""", 200, {"Content-Type": "text/plain"}

@app.route("/.env")
def dotenv_exposure():
    return """APP_ENV=production
SECRET_KEY=vulnsite_secret_2024
DB_URL=sqlite:///vulnsite.db
FLAG=FLAG{dotenv_file_exposed}
ADMIN_EMAIL=admin@vulnsite.local
API_SECRET=secret_api_key_do_not_share
""", 200, {"Content-Type": "text/plain"}

@app.route("/api/debug/info")
def debug_info():
    # VULN: debug endpoint left in production
    return jsonify({
        "flag": "FLAG{debug_endpoint_exposed}",
        "python_version": "3.11",
        "db_path": os.path.abspath(DB),
        "secret_key": app.secret_key,
        "debug_mode": app.debug,
        "users_count": get_db().execute("SELECT count(*) FROM users").fetchone()[0]
    })

# ════════════════════════════════════════════════════════════════════════════
# MODULE 10 — INSECURE DESERIALIZATION
# ════════════════════════════════════════════════════════════════════════════
@app.route("/deser", methods=["GET","POST"])
def deser():
    result, error = None, None
    if request.method == "POST":
        data = request.form.get("data","")
        try:
            obj = pickle.loads(base64.b64decode(data))
            result = repr(obj)
        except Exception as e:
            error = str(e)
    safe = {"user":"guest","role":"viewer","score":42,"flag":"FLAG{safe_object_deserialized}"}
    example = base64.b64encode(pickle.dumps(safe)).decode()
    return render_template("deser.html", result=result, error=error, example=example)

if __name__ == "__main__":
    init_db()
    print("\n" + "="*55)
    print("   vulnsite — Web Security Practice Lab")
    print("   http://localhost:5000")
    print("   Educational use only!")
    print("="*55 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
