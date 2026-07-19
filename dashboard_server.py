"""
dashboard_server.py — ArtheeNoi Stock Dashboard (Multi-User Web App)
ระบบ login ของใครของมัน: portfolio แยก + dashboard เป็นส่วนตัว
Deploy ขึ้น Render ฟรี — เพื่อนเปิด URL ได้เลย

Usage:
  python dashboard_server.py          # รันที่ port 5052
  PORT=8080 python dashboard_server.py
"""
import os, sys, json, time, threading, logging
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import (Flask, request, session, redirect,
                   render_template_string, jsonify, Response)

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

USERS_FILE     = BASE / "dashboard_users.json"
PORT           = int(os.environ.get("PORT", 5052))
REFRESH_MIN    = int(os.environ.get("REFRESH_MINUTES", "30"))
FLASK_SECRET   = os.environ.get("FLASK_SECRET", "artheenoi_dashboard_2026_xK9")

app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.permanent_session_lifetime = timedelta(days=30)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

ETFS   = ["QQQ", "IVV", "DIA"]
GOLD   = "GC=F"
CRYPTO = "BTC-USD"

# ─── Password ────────────────────────────────────────────────────────────────

def _hash(pwd: str) -> str:
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pwd)

def _check(pwd: str, hashed: str) -> bool:
    from werkzeug.security import check_password_hash
    return check_password_hash(hashed, pwd)

# ─── User DB ─────────────────────────────────────────────────────────────────

_DEFAULT_PORTFOLIO = {
    "NVDA":  {"shares": 2, "cost": 850},
    "MSFT":  {"shares": 3, "cost": 420},
    "GOOGL": {"shares": 2, "cost": 175},
    "META":  {"shares": 2, "cost": 550},
    "AMZN":  {"shares": 3, "cost": 200},
}
_DEFAULT_WATCHLIST = ["AVGO", "MRVL", "AMD", "TSLA", "NOW", "SOFI", "VST"]

def _default_users() -> dict:
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "artheenoi2026")
    return {
        "olarn": {
            "password_hash": _hash(admin_pwd),
            "display_name":  "Olarn",
            "role":          "admin",
            "portfolio":     _DEFAULT_PORTFOLIO,
            "watchlist":     _DEFAULT_WATCHLIST,
            "dashboard_html": None,
            "last_updated":   None,
        }
    }

_users_lock = threading.Lock()

def load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    users = _default_users()
    _save_users_raw(users)
    return users

def _save_users_raw(users: dict):
    data = {k: {f: v for f, v in u.items() if f != "dashboard_html"}
            for k, u in users.items()}
    USERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def save_users(users: dict):
    _save_users_raw(users)

def get_user(username: str) -> dict | None:
    with _users_lock:
        return load_users().get(username)

def update_user_fields(username: str, fields: dict):
    """Update specific fields for a user (does not touch dashboard_html in file)."""
    with _users_lock:
        users = load_users()
        if username in users:
            users[username].update(fields)
            save_users(users)

# ─── Auth Decorators ──────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect("/login")
        user = get_user(session["username"])
        if not user or user.get("role") != "admin":
            return "<h2>Access denied</h2>", 403
        return f(*args, **kwargs)
    return decorated

# ─── Market Data Cache ────────────────────────────────────────────────────────

_mkt_lock  = threading.Lock()
_mkt_cache = {"data": None, "macro": None, "thb": 35.0, "updated": None}
_gen_lock  = threading.Lock()   # ป้องกัน generate() race condition
_refreshing = threading.Event()

def _all_user_symbols() -> list:
    syms = set(ETFS + [GOLD, CRYPTO])
    with _users_lock:
        users = load_users()
    for u in users.values():
        syms.update(u.get("portfolio", {}).keys())
        syms.update(u.get("watchlist", []))
    return list(syms)

def _do_market_refresh():
    _refreshing.set()
    try:
        import daily_wiki_update as dwu

        all_syms = _all_user_symbols()
        log.info(f"[Market] Fetching {len(all_syms)} symbols ...")
        thb = dwu.get_thb_rate()

        mkt = dwu.fetch_all(all_syms)
        for s in all_syms:
            if not mkt.get(s, {}).get("price"):
                mkt[s] = dwu.get_quote(s)

        # Enrich (optional, graceful fail)
        try:
            from at_analysis import fetch_finviz, fetch_earnings_date
            enrich = [s for s in all_syms if "=" not in s and s != "BTC-USD"]
            for s in enrich:
                try:
                    fv = fetch_finviz(s)
                    if fv: mkt.setdefault(s, {}).update(fv)
                    ed = fetch_earnings_date(s)
                    if ed.get("earnings_days_away") is not None:
                        mkt.setdefault(s, {}).update(ed)
                    time.sleep(0.3)
                except Exception:
                    pass
        except ImportError:
            pass

        macro = {}
        try:
            from at_analysis import fetch_macro
            macro = fetch_macro()
        except Exception as e:
            log.warning(f"[Macro] {e}")

        qqq_chg = (mkt.get("QQQ") or {}).get("change_pct", 0)
        macro.setdefault("qqq_chg", qqq_chg)
        macro.setdefault("mood", "BULL" if qqq_chg > 0.5 else "BEAR" if qqq_chg < -0.5 else "NEUTRAL")

        with _mkt_lock:
            _mkt_cache.update({"data": mkt, "macro": macro, "thb": thb,
                               "updated": datetime.now()})

        log.info(f"[Market] Refresh done — {len(mkt)} symbols, THB={thb:.2f}")
        return True

    except Exception as e:
        log.exception(f"[Market] Refresh error: {e}")
        return False
    finally:
        _refreshing.clear()

_refresh_trigger = threading.Event()

def _refresh_loop():
    """Background thread: auto-refresh every REFRESH_MIN minutes."""
    while True:
        _refresh_trigger.wait(timeout=REFRESH_MIN * 60)
        _refresh_trigger.clear()
        _do_market_refresh()

# ─── Per-User Dashboard Generation ───────────────────────────────────────────

def _build_port_rows(user: dict, mkt: dict, thb: float):
    import daily_wiki_update as dwu
    port_rows  = []
    total_val  = 0.0
    total_cost = 0.0

    for sym, info in user.get("portfolio", {}).items():
        d = mkt.get(sym, {})
        if not d.get("price"):
            continue
        shares   = float(info.get("shares", 0))
        cost     = float(info.get("cost", 0))
        val      = d["price"] * shares
        cost_tot = cost * shares
        pnl_usd  = val - cost_tot
        pnl_pct  = pnl_usd / cost_tot * 100 if cost_tot else 0
        pnl_thb  = pnl_usd * thb
        total_val  += val
        total_cost += cost_tot
        try:
            sig, reason = dwu.get_signal(
                d.get("rsi"), d.get("change_pct", 0),
                d.get("high_52w"), d.get("low_52w"), d["price"]
            )
        except Exception:
            sig, reason = "NEUTRAL", ""
        port_rows.append({
            "sym": sym, "shares": shares, "cost": cost,
            "price": d["price"], "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 2), "pnl_thb": round(pnl_thb, 0),
            "sig": sig, "rsi": d.get("rsi"),
            "chg": d.get("change_pct", 0), "reason": reason,
        })

    total_pnl     = total_val - total_cost
    total_pnl_thb = total_pnl * thb
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    return port_rows, total_pnl, total_pnl_thb, total_pnl_pct, total_val

def generate_for_user(username: str) -> str | None:
    """Generate dashboard HTML for a specific user. Returns HTML string or None."""
    with _mkt_lock:
        mkt   = _mkt_cache.get("data")
        macro = _mkt_cache.get("macro") or {}
        thb   = _mkt_cache.get("thb", 35.0)

    if not mkt:
        return None

    user = get_user(username)
    if not user:
        return None

    port_rows, total_pnl, total_pnl_thb, total_pnl_pct, total_val = (
        _build_port_rows(user, mkt, thb)
    )

    try:
        import dashboard as dash
        with _gen_lock:
            out_path = dash.generate(
                mkt, port_rows, user.get("watchlist", []),
                ETFS, GOLD, CRYPTO,
                total_pnl, total_pnl_thb, total_pnl_pct, total_val, thb,
                macro=macro,
            )
            html = Path(str(out_path)).read_text(encoding="utf-8")

        # Inject username banner
        banner = (
            f'<div style="position:fixed;bottom:12px;right:16px;z-index:9999;'
            f'background:#0f1623cc;border:1px solid #1c2a3a;border-radius:8px;'
            f'padding:6px 12px;font-size:11px;color:#94a3b8">'
            f'👤 {user["display_name"]} &nbsp;|&nbsp; '
            f'<a href="/settings" style="color:#d97757;text-decoration:none">Settings</a>'
            f' &nbsp;|&nbsp; <a href="/logout" style="color:#64748b;text-decoration:none">Logout</a>'
            f'</div>'
        )
        html = html.replace("</body>", banner + "</body>")
        return html

    except Exception as e:
        log.exception(f"[Generate] {username}: {e}")
        return None

# ─── HTML Templates ───────────────────────────────────────────────────────────

_LOGIN_TPL = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArtheeNoi — Login</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;background:#090d16;display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif}
.card{background:#0f1623;border:1px solid #1c2a3a;border-radius:16px;padding:44px 36px;width:340px}
.logo{text-align:center;font-size:36px;margin-bottom:10px}
h1{text-align:center;color:#e2e8f0;font-size:20px;font-weight:700;margin-bottom:4px}
.sub{text-align:center;color:#64748b;font-size:12px;margin-bottom:28px}
label{display:block;color:#94a3b8;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin:16px 0 6px}
input{width:100%;padding:10px 14px;background:#111d2e;border:1px solid #243040;border-radius:8px;color:#e2e8f0;font-size:14px;outline:none;transition:border .2s}
input:focus{border-color:#d97757}
button{width:100%;margin-top:24px;padding:12px;background:#d97757;border:none;border-radius:8px;color:#fff;font-size:15px;font-weight:700;cursor:pointer;transition:.2s}
button:hover{background:#c96040}
.err{background:#ef444422;border:1px solid #ef444466;border-radius:6px;color:#ef4444;font-size:12px;text-align:center;padding:8px;margin-top:14px}
</style>
</head>
<body>
<div class="card">
  <div class="logo">📈</div>
  <h1>ArtheeNoi Dashboard</h1>
  <p class="sub">ระบบวิเคราะห์หุ้น — สำหรับเพื่อน</p>
  <form method="POST">
    <label>Username</label>
    <input name="username" type="text" autocomplete="username" placeholder="ใส่ username" required>
    <label>Password</label>
    <input name="password" type="password" autocomplete="current-password" placeholder="ใส่ password" required>
    <button type="submit">เข้าสู่ระบบ →</button>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
  </form>
</div>
</body></html>"""

_SETTINGS_TPL = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Settings — ArtheeNoi</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#090d16;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px}
.wrap{max-width:700px;margin:0 auto}
h1{font-size:20px;font-weight:700;margin-bottom:4px}
.sub{color:#64748b;font-size:13px;margin-bottom:28px}
.card{background:#0f1623;border:1px solid #1c2a3a;border-radius:12px;padding:24px;margin-bottom:20px}
h2{font-size:14px;font-weight:700;color:#d97757;margin-bottom:16px;text-transform:uppercase;letter-spacing:.5px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;padding:0 8px 8px}
td{padding:6px 8px;vertical-align:middle}
input[type=text],input[type=number]{background:#111d2e;border:1px solid #243040;border-radius:6px;color:#e2e8f0;font-size:13px;padding:6px 10px;width:100%}
input:focus{border-color:#d97757;outline:none}
.btn{padding:8px 18px;border:none;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer}
.btn-primary{background:#d97757;color:#fff}.btn-primary:hover{background:#c96040}
.btn-danger{background:#ef444422;color:#ef4444;border:1px solid #ef444466}.btn-danger:hover{background:#ef444444}
.btn-add{background:#10b98122;color:#10b981;border:1px solid #10b98166;margin-top:8px}.btn-add:hover{background:#10b98133}
.nav{display:flex;gap:12px;margin-bottom:24px}
.nav a{color:#64748b;text-decoration:none;font-size:13px}.nav a:hover{color:#e2e8f0}
.msg{padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:16px}
.msg.ok{background:#10b98122;border:1px solid #10b98166;color:#10b981}
.msg.err{background:#ef444422;border:1px solid #ef444466;color:#ef4444}
.wl-wrap{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.wl-tag{background:#111d2e;border:1px solid #243040;border-radius:6px;padding:5px 10px;font-size:12px;display:flex;align-items:center;gap:8px}
.wl-tag button{background:none;border:none;color:#ef4444;cursor:pointer;font-size:14px;padding:0}
</style>
</head>
<body>
<div class="wrap">
  <div class="nav">
    <a href="/">← Dashboard</a>
    <a href="/logout">Logout</a>
    {% if is_admin %}<a href="/admin">👑 Admin</a>{% endif %}
  </div>
  <h1>⚙️ Settings</h1>
  <p class="sub">ตั้งค่า portfolio และ watchlist ของ {{ display_name }}</p>
  {% if msg %}<div class="msg {{ msg_type }}">{{ msg }}</div>{% endif %}

  <!-- Portfolio -->
  <div class="card">
    <h2>📊 Portfolio ของฉัน</h2>
    <form method="POST" action="/settings/portfolio">
      <table>
        <thead><tr><th>Symbol</th><th>จำนวนหุ้น</th><th>ต้นทุน/หุ้น (USD)</th><th></th></tr></thead>
        <tbody id="portBody">
        {% for sym, info in portfolio.items() %}
        <tr>
          <td><input type="text" name="sym" value="{{ sym }}" style="text-transform:uppercase" maxlength="10"></td>
          <td><input type="number" name="shares" value="{{ info.shares }}" step="0.01" min="0"></td>
          <td><input type="number" name="cost" value="{{ info.cost }}" step="0.01" min="0"></td>
          <td><button type="button" class="btn btn-danger" onclick="this.closest('tr').remove()">✕</button></td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
      <button type="button" class="btn btn-add" onclick="addRow()">+ เพิ่มหุ้น</button>
      <div style="margin-top:16px">
        <button type="submit" class="btn btn-primary">💾 บันทึก Portfolio</button>
      </div>
    </form>
  </div>

  <!-- Watchlist -->
  <div class="card">
    <h2>👀 Watchlist</h2>
    <form method="POST" action="/settings/watchlist">
      <div class="wl-wrap" id="wlWrap">
        {% for sym in watchlist %}
        <div class="wl-tag">
          {{ sym }}
          <input type="hidden" name="sym" value="{{ sym }}">
          <button type="button" onclick="this.parentElement.remove()">✕</button>
        </div>
        {% endfor %}
      </div>
      <div style="display:flex;gap:8px;margin-bottom:16px">
        <input type="text" id="newSym" placeholder="เพิ่ม symbol เช่น NVDA" style="width:160px" maxlength="10">
        <button type="button" class="btn btn-add" onclick="addWl()">+ เพิ่ม</button>
      </div>
      <button type="submit" class="btn btn-primary">💾 บันทึก Watchlist</button>
    </form>
  </div>

  <!-- Change Password -->
  <div class="card">
    <h2>🔒 เปลี่ยน Password</h2>
    <form method="POST" action="/settings/password">
      <table><tbody>
        <tr>
          <td style="width:160px;padding-right:16px;color:#94a3b8;font-size:13px">Password เดิม</td>
          <td><input type="password" name="old_pwd"></td>
        </tr>
        <tr>
          <td style="color:#94a3b8;font-size:13px">Password ใหม่</td>
          <td><input type="password" name="new_pwd"></td>
        </tr>
        <tr>
          <td style="color:#94a3b8;font-size:13px">ยืนยัน Password ใหม่</td>
          <td><input type="password" name="confirm_pwd"></td>
        </tr>
      </tbody></table>
      <div style="margin-top:16px"><button type="submit" class="btn btn-primary">🔒 เปลี่ยน Password</button></div>
    </form>
  </div>
</div>
<script>
function addRow(){
  const t=document.getElementById('portBody');
  const r=document.createElement('tr');
  r.innerHTML='<td><input type="text" name="sym" style="text-transform:uppercase" maxlength="10" placeholder="AAPL"></td>'
    +'<td><input type="number" name="shares" step="0.01" min="0" value="1"></td>'
    +'<td><input type="number" name="cost" step="0.01" min="0" value="0"></td>'
    +'<td><button type="button" class="btn btn-danger" onclick="this.closest(\'tr\').remove()">✕</button></td>';
  t.appendChild(r);
}
function addWl(){
  const v=document.getElementById('newSym').value.trim().toUpperCase();
  if(!v)return;
  const w=document.getElementById('wlWrap');
  const d=document.createElement('div');d.className='wl-tag';
  d.innerHTML=v+'<input type="hidden" name="sym" value="'+v+'"><button type="button" onclick="this.parentElement.remove()">✕</button>';
  w.appendChild(d);
  document.getElementById('newSym').value='';
}
</script>
</body></html>"""

_ADMIN_TPL = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin — ArtheeNoi</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#090d16;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px}
.wrap{max-width:800px;margin:0 auto}
.nav{display:flex;gap:12px;margin-bottom:24px}
.nav a{color:#64748b;text-decoration:none;font-size:13px}.nav a:hover{color:#e2e8f0}
h1{font-size:20px;font-weight:700;margin-bottom:4px}
.sub{color:#64748b;font-size:13px;margin-bottom:28px}
.card{background:#0f1623;border:1px solid #1c2a3a;border-radius:12px;padding:24px;margin-bottom:20px}
h2{font-size:14px;font-weight:700;color:#d97757;text-transform:uppercase;letter-spacing:.5px;margin-bottom:16px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:11px;color:#64748b;text-transform:uppercase;padding:0 12px 8px}
td{padding:10px 12px;border-bottom:1px solid #1c2a3a;font-size:13px;vertical-align:middle}
tr:last-child td{border-bottom:none}
.badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;text-transform:uppercase}
.admin-badge{background:#d9775722;color:#d97757;border:1px solid #d9775766}
.user-badge{background:#3b82f622;color:#3b82f6;border:1px solid #3b82f666}
input[type=text],input[type=password]{background:#111d2e;border:1px solid #243040;border-radius:6px;color:#e2e8f0;font-size:13px;padding:7px 12px}
input:focus{border-color:#d97757;outline:none}
select{background:#111d2e;border:1px solid #243040;border-radius:6px;color:#e2e8f0;font-size:13px;padding:7px 12px}
.btn{padding:7px 16px;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer}
.btn-primary{background:#d97757;color:#fff}.btn-primary:hover{background:#c96040}
.btn-danger{background:#ef444422;color:#ef4444;border:1px solid #ef444466}.btn-danger:hover{background:#ef444444}
.msg{padding:10px 14px;border-radius:7px;font-size:13px;margin-bottom:16px}
.msg.ok{background:#10b98122;border:1px solid #10b98166;color:#10b981}
.msg.err{background:#ef444422;border:1px solid #ef444466;color:#ef4444}
.row{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap}
.fld label{display:block;color:#94a3b8;font-size:11px;text-transform:uppercase;margin-bottom:5px}
</style>
</head>
<body>
<div class="wrap">
  <div class="nav">
    <a href="/">← Dashboard</a>
    <a href="/settings">Settings</a>
    <a href="/logout">Logout</a>
  </div>
  <h1>👑 Admin Panel</h1>
  <p class="sub">จัดการบัญชีผู้ใช้ทั้งหมด</p>
  {% if msg %}<div class="msg {{ msg_type }}">{{ msg }}</div>{% endif %}

  <!-- User list -->
  <div class="card">
    <h2>👥 ผู้ใช้ทั้งหมด</h2>
    <table>
      <thead><tr><th>Username</th><th>ชื่อ</th><th>Role</th><th>Portfolio</th><th>อัปเดตล่าสุด</th><th></th></tr></thead>
      <tbody>
      {% for uname, u in users.items() %}
      <tr>
        <td><b>{{ uname }}</b></td>
        <td>{{ u.display_name }}</td>
        <td><span class="badge {% if u.role=='admin' %}admin-badge{% else %}user-badge{% endif %}">{{ u.role }}</span></td>
        <td style="color:#64748b">{{ u.portfolio|length }} หุ้น</td>
        <td style="color:#64748b;font-size:11px">{{ u.last_updated or 'ยังไม่ refresh' }}</td>
        <td>
          {% if uname != current_user %}
          <form method="POST" action="/admin/delete" style="display:inline">
            <input type="hidden" name="username" value="{{ uname }}">
            <button type="submit" class="btn btn-danger" onclick="return confirm('ลบ {{ uname }}?')">ลบ</button>
          </form>
          {% else %}
          <span style="color:#64748b;font-size:11px">(ตัวเอง)</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Add User -->
  <div class="card">
    <h2>➕ เพิ่มผู้ใช้ใหม่</h2>
    <form method="POST" action="/admin/create">
      <div class="row">
        <div class="fld"><label>Username</label><input type="text" name="username" placeholder="friend1" required></div>
        <div class="fld"><label>ชื่อแสดง</label><input type="text" name="display_name" placeholder="เพื่อน 1" required></div>
        <div class="fld"><label>Password</label><input type="password" name="password" placeholder="รหัสผ่าน" required></div>
        <div class="fld"><label>Role</label>
          <select name="role">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div class="fld"><label>&nbsp;</label><button type="submit" class="btn btn-primary">➕ สร้าง</button></div>
      </div>
    </form>
  </div>

  <!-- Reset Password -->
  <div class="card">
    <h2>🔑 Reset Password</h2>
    <form method="POST" action="/admin/reset-password">
      <div class="row">
        <div class="fld"><label>Username</label>
          <select name="username">
            {% for uname in users %}<option value="{{ uname }}">{{ uname }}</option>{% endfor %}
          </select>
        </div>
        <div class="fld"><label>Password ใหม่</label><input type="password" name="new_password" placeholder="รหัสใหม่" required></div>
        <div class="fld"><label>&nbsp;</label><button type="submit" class="btn btn-primary">🔑 Reset</button></div>
      </div>
    </form>
  </div>

  <!-- Market Cache Status -->
  <div class="card">
    <h2>📡 สถานะข้อมูลตลาด</h2>
    <table><tbody>
      <tr><td style="color:#94a3b8;width:160px">อัปเดตล่าสุด</td><td>{{ mkt_updated or 'ยังไม่มีข้อมูล' }}</td></tr>
      <tr><td style="color:#94a3b8">จำนวน Symbols</td><td>{{ mkt_count }}</td></tr>
      <tr><td style="color:#94a3b8">กำลัง refresh</td><td>{{ '🔄 กำลังโหลด...' if refreshing else '✅ พร้อมใช้งาน' }}</td></tr>
    </tbody></table>
    <form method="POST" action="/admin/refresh-market" style="margin-top:14px">
      <button type="submit" class="btn btn-primary">🔄 Force Refresh ข้อมูลตลาด</button>
    </form>
  </div>
</div>
</body></html>"""

_LOADING_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta http-equiv="refresh" content="10">
<title>กำลังโหลด — ArtheeNoi</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;background:#090d16;display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif;color:#e2e8f0}
.box{text-align:center;max-width:400px}
.spin{font-size:48px;animation:s 1.5s linear infinite;display:inline-block;margin-bottom:20px}
@keyframes s{from{transform:rotate(0)}to{transform:rotate(360deg)}}
h2{font-size:22px;margin-bottom:8px}
p{color:#64748b;margin-bottom:4px;font-size:14px}
.note{margin-top:20px;font-size:12px;color:#475569}
</style>
</head>
<body>
<div class="box">
  <div class="spin">📡</div>
  <h2>กำลังโหลดข้อมูล</h2>
  <p>ดึงราคาหุ้น + คำนวณ AI score</p>
  <p>ใช้เวลาประมาณ 2-3 นาที (ครั้งแรก)</p>
  <p class="note">หน้าจะ refresh อัตโนมัติทุก 10 วินาที</p>
</div>
</body></html>"""

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect("/")
    error = None
    if request.method == "POST":
        uname = request.form.get("username", "").strip().lower()
        pwd   = request.form.get("password", "")
        user  = get_user(uname)
        if user and _check(pwd, user["password_hash"]):
            session.permanent = True
            session["username"] = uname
            return redirect("/")
        error = "Username หรือ Password ไม่ถูกต้อง"
    return render_template_string(_LOGIN_TPL, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def index():
    uname = session["username"]
    user  = get_user(uname)
    if not user:
        return redirect("/logout")

    # ถ้าไม่มีข้อมูลตลาด → แสดง loading
    with _mkt_lock:
        has_data = _mkt_cache.get("data") is not None

    if not has_data:
        return _LOADING_HTML

    # สร้าง dashboard ถ้ายังไม่มี cache
    html = user.get("dashboard_html")
    if not html:
        html = generate_for_user(uname)
        if html:
            update_user_fields(uname, {"dashboard_html": html,
                                       "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")})

    return html or _LOADING_HTML

@app.route("/refresh", methods=["POST", "GET"])
@login_required
def refresh_user():
    uname = session["username"]
    with _mkt_lock:
        has_data = _mkt_cache.get("data") is not None

    if not has_data:
        # Trigger market refresh first
        t = threading.Thread(target=_do_market_refresh, daemon=True)
        t.start()
        return _LOADING_HTML

    html = generate_for_user(uname)
    if html:
        update_user_fields(uname, {"dashboard_html": html,
                                   "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return redirect("/")

# ─── Settings ─────────────────────────────────────────────────────────────────

@app.route("/settings")
@login_required
def settings():
    uname = session["username"]
    user  = get_user(uname)
    return render_template_string(
        _SETTINGS_TPL,
        display_name=user["display_name"],
        portfolio=user.get("portfolio", {}),
        watchlist=user.get("watchlist", []),
        is_admin=user.get("role") == "admin",
        msg=request.args.get("msg"),
        msg_type=request.args.get("mt", "ok"),
    )

@app.route("/settings/portfolio", methods=["POST"])
@login_required
def save_portfolio():
    uname = session["username"]
    syms    = request.form.getlist("sym")
    shares_ = request.form.getlist("shares")
    costs_  = request.form.getlist("cost")

    portfolio = {}
    for s, sh, c in zip(syms, shares_, costs_):
        s = s.strip().upper()
        if not s:
            continue
        try:
            portfolio[s] = {"shares": float(sh), "cost": float(c)}
        except (ValueError, TypeError):
            pass

    update_user_fields(uname, {"portfolio": portfolio, "dashboard_html": None})
    return redirect("/settings?msg=บันทึก+Portfolio+แล้ว&mt=ok")

@app.route("/settings/watchlist", methods=["POST"])
@login_required
def save_watchlist():
    uname = session["username"]
    syms  = [s.strip().upper() for s in request.form.getlist("sym") if s.strip()]
    syms  = list(dict.fromkeys(syms))  # deduplicate, preserve order
    update_user_fields(uname, {"watchlist": syms, "dashboard_html": None})
    return redirect("/settings?msg=บันทึก+Watchlist+แล้ว&mt=ok")

@app.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    uname    = session["username"]
    old_pwd  = request.form.get("old_pwd", "")
    new_pwd  = request.form.get("new_pwd", "")
    confirm  = request.form.get("confirm_pwd", "")
    user     = get_user(uname)

    if not _check(old_pwd, user["password_hash"]):
        return redirect("/settings?msg=Password+เดิมไม่ถูกต้อง&mt=err")
    if len(new_pwd) < 6:
        return redirect("/settings?msg=Password+ต้องมีอย่างน้อย+6+ตัวอักษร&mt=err")
    if new_pwd != confirm:
        return redirect("/settings?msg=Password+ใหม่ไม่ตรงกัน&mt=err")

    update_user_fields(uname, {"password_hash": _hash(new_pwd)})
    return redirect("/settings?msg=เปลี่ยน+Password+สำเร็จ&mt=ok")

# ─── Admin ────────────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin():
    with _users_lock:
        users = load_users()
    with _mkt_lock:
        upd   = _mkt_cache.get("updated")
        count = len(_mkt_cache.get("data") or {})

    return render_template_string(
        _ADMIN_TPL,
        users=users,
        current_user=session["username"],
        msg=request.args.get("msg"),
        msg_type=request.args.get("mt", "ok"),
        mkt_updated=upd.strftime("%Y-%m-%d %H:%M") if upd else None,
        mkt_count=count,
        refreshing=_refreshing.is_set(),
    )

@app.route("/admin/create", methods=["POST"])
@admin_required
def admin_create_user():
    uname   = request.form.get("username", "").strip().lower()
    dname   = request.form.get("display_name", "").strip()
    pwd     = request.form.get("password", "")
    role    = request.form.get("role", "user")

    if not uname or not pwd:
        return redirect("/admin?msg=กรุณากรอกข้อมูลให้ครบ&mt=err")
    if len(pwd) < 6:
        return redirect("/admin?msg=Password+ต้องมีอย่างน้อย+6+ตัวอักษร&mt=err")

    with _users_lock:
        users = load_users()
        if uname in users:
            return redirect(f"/admin?msg=Username+'{uname}'+มีอยู่แล้ว&mt=err")
        users[uname] = {
            "password_hash": _hash(pwd),
            "display_name":  dname or uname,
            "role":          role,
            "portfolio":     {},
            "watchlist":     [],
            "dashboard_html": None,
            "last_updated":   None,
        }
        save_users(users)

    return redirect(f"/admin?msg=สร้างบัญชี+'{uname}'+สำเร็จ&mt=ok")

@app.route("/admin/delete", methods=["POST"])
@admin_required
def admin_delete_user():
    target = request.form.get("username", "")
    me     = session["username"]
    if target == me:
        return redirect("/admin?msg=ลบตัวเองไม่ได้&mt=err")
    with _users_lock:
        users = load_users()
        if target not in users:
            return redirect("/admin?msg=ไม่พบผู้ใช้&mt=err")
        del users[target]
        save_users(users)
    return redirect(f"/admin?msg=ลบผู้ใช้+'{target}'+แล้ว&mt=ok")

@app.route("/admin/reset-password", methods=["POST"])
@admin_required
def admin_reset_password():
    target   = request.form.get("username", "")
    new_pwd  = request.form.get("new_password", "")
    if len(new_pwd) < 6:
        return redirect("/admin?msg=Password+ต้องมีอย่างน้อย+6+ตัวอักษร&mt=err")
    update_user_fields(target, {"password_hash": _hash(new_pwd)})
    return redirect(f"/admin?msg=Reset+password+'{target}'+สำเร็จ&mt=ok")

@app.route("/admin/refresh-market", methods=["POST"])
@admin_required
def admin_refresh_market():
    if not _refreshing.is_set():
        t = threading.Thread(target=_do_market_refresh, daemon=True)
        t.start()
    return redirect("/admin?msg=เริ่ม+refresh+ข้อมูลตลาดแล้ว+รอ+2-3+นาที&mt=ok")

@app.route("/status")
@login_required
def status():
    with _mkt_lock:
        upd   = _mkt_cache.get("updated")
        count = len(_mkt_cache.get("data") or {})
    return jsonify({
        "refreshing":   _refreshing.is_set(),
        "symbols":      count,
        "last_updated": upd.isoformat() if upd else None,
    })

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure wiki/ dir exists (for dashboard.py to write into)
    (BASE / "wiki").mkdir(exist_ok=True)

    log.info("─" * 50)
    log.info("ArtheeNoi Dashboard Server starting...")
    log.info(f"  Port: {PORT}  |  Auto-refresh: {REFRESH_MIN} min")
    log.info(f"  Users file: {USERS_FILE}")
    log.info("─" * 50)

    # Load / init users
    with _users_lock:
        users = load_users()
    log.info(f"Loaded {len(users)} user(s): {list(users.keys())}")

    # Background market refresh thread
    threading.Thread(target=_refresh_loop, daemon=True).start()

    # Initial market data fetch (async)
    threading.Thread(target=_do_market_refresh, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False)
