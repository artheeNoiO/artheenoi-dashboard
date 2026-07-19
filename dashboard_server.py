"""
dashboard_server.py — ArtheeNoi Stock Dashboard v2 (Multi-User Web App)
ระบบ login ของใครของมัน + 5 pages: Stocks / Gold / Crypto / DCA / News
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
MARKETAUX_KEY    = os.environ.get("MARKETAUX_KEY", "")
OPENROUTER_KEY   = os.environ.get("OPENROUTER_API_KEY", "")   # system-wide key
_ai_cache: dict  = {}   # username → {"text": ..., "ts": datetime}

def _get_user_or_key(username: str) -> str:
    """คืน OpenRouter key ของ user ก่อน ถ้าไม่มีจึงใช้ system key"""
    user = get_user(username)
    return (user or {}).get("openrouter_key", "") or OPENROUTER_KEY

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
_mkt_cache = {"data": None, "macro": None, "thb": 35.0,
              "updated": None, "vault_picks": []}
_gen_lock  = threading.Lock()   # ป้องกัน generate() race condition
_refreshing = threading.Event()

def _enrich_with_closes(mkt: dict, syms: list):
    """Fetch 60-day closes + 52W high/low via yfinance and merge into mkt dict."""
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        batch = " ".join(syms)
        tickers = yf.Tickers(batch)
        for sym in syms:
            try:
                t = tickers.tickers.get(sym)
                if not t:
                    continue
                hist = t.history(period="1y", interval="1d")
                closes = hist["Close"].dropna().tolist()
                if not closes:
                    continue
                fi = t.fast_info
                entry = mkt.setdefault(sym, {})
                entry["closes"] = [round(c, 4) for c in closes]
                if not entry.get("price"):
                    entry["price"] = round(closes[-1], 4)
                entry.setdefault("high", round(fi.year_high or max(closes), 2))
                entry.setdefault("low",  round(fi.year_low  or min(closes), 2))
            except Exception:
                pass
    except Exception as e:
        log.warning(f"[Closes] enrich failed: {e}")

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

        # Enrich with historical closes (for RSI, sparklines, 52W range)
        _enrich_with_closes(mkt, all_syms)

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

        # Vault picks (top ArtheeNoi picks filtered by macro)
        vault_picks = []
        try:
            import at_stock_vault as vault_mod
            qqq_chg = (mkt.get("QQQ") or {}).get("change_pct", 0) or (mkt.get("QQQ") or {}).get("chg", 0)
            mood    = "BULL" if qqq_chg > 0.5 else "BEAR" if qqq_chg < -0.5 else "NEUTRAL"
            vault_picks = vault_mod.get_vault_picks(macro=macro, qqq_chg=qqq_chg,
                                                    market_mood=mood, n=60)
            # Merge vault stock prices into mkt cache
            vault_syms = [p.get("sym") or p.get("t","") for p in vault_picks]
            new_syms   = [s for s in vault_syms if s and not mkt.get(s)]
            if new_syms:
                extra = vault_mod.fetch_picks_lite(new_syms[:50])
                mkt.update(extra)
            log.info(f"[Vault] {len(vault_picks)} picks loaded")
        except Exception as e:
            log.warning(f"[Vault] {e}")

        with _mkt_lock:
            _mkt_cache.update({"data": mkt, "macro": macro, "thb": thb,
                               "updated": datetime.now(), "vault_picks": vault_picks})

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
    <a href="/stocks">← Dashboard</a>
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

  <!-- BYOK: OpenRouter Key -->
  <div class="card">
    <h2>🤖 OpenRouter API Key (ของตัวเอง)</h2>
    <p style="font-size:12px;color:#64748b;margin-bottom:14px">
      ใส่ key ตัวเองเพื่อให้ ArtheeNoi ฉลาดขึ้น (Chat + AI Analysis จะใช้ key ของคุณ)<br>
      ถ้าไม่ใส่ → ใช้ system key (อาจถูกจำกัดการใช้งาน) &nbsp;|&nbsp;
      <a href="https://openrouter.ai/keys" target="_blank" style="color:#d97757">สมัคร OpenRouter ฟรี →</a>
    </p>
    <form method="POST" action="/settings/api-key">
      <div style="display:flex;gap:8px;align-items:center">
        <input type="password" name="openrouter_key"
               value="{{ openrouter_key }}"
               placeholder="sk-or-v1-..."
               style="flex:1;background:#111d2e;border:1px solid #243040;border-radius:8px;color:#e2e8f0;font-size:13px;padding:10px 14px">
        <button type="submit" class="btn btn-primary">💾 บันทึก</button>
      </div>
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
    <a href="/stocks">← Dashboard</a>
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

def _get_mkt():
    """Return (mkt, macro, thb) from cache."""
    with _mkt_lock:
        return (
            _mkt_cache.get("data") or {},
            _mkt_cache.get("macro") or {},
            _mkt_cache.get("thb", 35.0),
        )

def _get_vault_picks():
    with _mkt_lock:
        return _mkt_cache.get("vault_picks") or []

def _require_mkt():
    """Return True if market data is ready, False if still loading."""
    with _mkt_lock:
        return bool(_mkt_cache.get("data"))

@app.route("/")
@login_required
def index():
    return redirect("/stocks")

@app.route("/stocks")
@login_required
def stocks():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, macro, thb = _get_mkt()
    user = get_user(session["username"])
    if not user:
        return redirect("/logout")
    return dw.stocks_page(user, mkt, macro, thb)

@app.route("/gold")
@login_required
def gold():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.gold_page(user, mkt)

@app.route("/crypto")
@login_required
def crypto():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.crypto_page(user, mkt)

@app.route("/dca")
@login_required
def dca():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.dca_page(user, mkt)

@app.route("/news")
@login_required
def news():
    import dashboard_web as dw
    _, macro, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.news_page(user, macro, MARKETAUX_KEY)

@app.route("/screener")
@login_required
def screener():
    import dashboard_web as dw
    mkt, macro, _ = _get_mkt()
    user  = get_user(session["username"])
    picks = _get_vault_picks()
    return dw.screener_page(user, mkt, macro, picks)

@app.route("/signals")
@login_required
def signals():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, thb = _get_mkt()
    user = get_user(session["username"])
    return dw.signals_page(user, mkt, thb)

# ─── Paper Trading ────────────────────────────────────────────────────────────

def _get_paper_trades(uname: str) -> list:
    user = get_user(uname)
    return user.get("paper_trades", [])

@app.route("/paper")
@login_required
def paper():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    uname = session["username"]
    user  = get_user(uname)
    trades = _get_paper_trades(uname)
    return dw.paper_page(user, mkt, thb, trades)

@app.route("/paper/open", methods=["POST"])
@login_required
def paper_open():
    uname  = session["username"]
    sym    = request.form.get("sym", "").upper()
    side   = request.form.get("side", "LONG")
    qty    = float(request.form.get("qty", 1) or 1)
    entry  = float(request.form.get("entry", 0) or 0)
    sl     = float(request.form.get("sl", 0) or 0)
    tp     = float(request.form.get("tp", 0) or 0)

    mkt, _, _ = _get_mkt()
    if not entry:
        entry = (mkt.get(sym) or {}).get("price", 0)
    if not entry:
        return redirect("/paper")

    cost  = entry * qty
    with _users_lock:
        users  = load_users()
        user   = users.get(uname, {})
        cash   = user.get("paper_cash", user.get("paper_cash_start", 10000))
        if cost > cash and side == "LONG":
            return redirect("/paper")   # insufficient cash
        trades = user.get("paper_trades", [])
        new_id = max((t.get("id", 0) for t in trades), default=0) + 1
        trades.append({
            "id": new_id, "sym": sym, "side": side,
            "qty": qty, "entry": round(entry, 4),
            "sl": sl, "tp": tp,
            "status": "open",
            "open_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        if side == "LONG":
            user["paper_cash"] = round(cash - cost, 4)
        user.setdefault("paper_cash_start", 10000)
        user["paper_trades"] = trades
        users[uname] = user
        save_users(users)
    return redirect("/paper")

@app.route("/paper/close", methods=["POST"])
@login_required
def paper_close():
    uname       = session["username"]
    trade_id    = int(request.form.get("trade_id", 0))
    close_price = float(request.form.get("close_price", 0) or 0)

    with _users_lock:
        users  = load_users()
        user   = users.get(uname, {})
        trades = user.get("paper_trades", [])
        cash   = user.get("paper_cash", 10000)
        for t in trades:
            if t["id"] == trade_id and t["status"] == "open":
                if not close_price:
                    mkt, _, _ = _get_mkt()
                    close_price = (mkt.get(t["sym"]) or {}).get("price", t["entry"])
                if t.get("side") == "LONG":
                    pnl = (close_price - t["entry"]) * t["qty"]
                    cash += t["entry"] * t["qty"] + pnl
                else:
                    pnl = (t["entry"] - close_price) * t["qty"]
                    cash += pnl
                t.update({
                    "status": "closed",
                    "close_price": round(close_price, 4),
                    "pnl": round(pnl, 4),
                    "close_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                break
        user["paper_cash"] = round(cash, 4)
        user["paper_trades"] = trades
        users[uname] = user
        save_users(users)
    return redirect("/paper")

@app.route("/paper/reset", methods=["POST"])
@login_required
def paper_reset():
    uname = session["username"]
    update_user_fields(uname, {
        "paper_trades": [],
        "paper_cash": 10000,
        "paper_cash_start": 10000,
    })
    return redirect("/paper")

# ─── AI Analysis ──────────────────────────────────────────────────────────────

@app.route("/ai")
@login_required
def ai_page():
    import dashboard_web as dw
    mkt, macro, thb = _get_mkt()
    uname = session["username"]
    user  = get_user(uname)
    cached = (_ai_cache.get(uname) or {}).get("text", "")
    return dw.ai_page(user, mkt, macro, thb, OPENROUTER_KEY, cached)

@app.route("/ai/analyze", methods=["POST"])
@login_required
def ai_analyze():
    import dashboard_web as dw
    mkt, macro, thb = _get_mkt()
    uname   = session["username"]
    user    = get_user(uname)
    or_key  = _get_user_or_key(uname)
    text    = dw._ai_analyze(mkt, user, or_key)
    if text:
        _ai_cache[uname] = {"text": text, "ts": datetime.now()}
    return redirect("/ai")

# ─── Settings: BYOK + Agent status ───────────────────────────────────────────

@app.route("/settings/api-key", methods=["POST"])
@login_required
def save_api_key():
    uname = session["username"]
    key   = request.form.get("openrouter_key", "").strip()
    update_user_fields(uname, {"openrouter_key": key})
    msg = "บันทึก API Key แล้ว — ArtheeNoi จะฉลาดขึ้นทันที 🎉" if key else "ลบ API Key แล้ว (ใช้ system key)"
    return redirect(f"/settings?msg={msg}&mt=ok")

@app.route("/agent/status")
@login_required
def agent_status():
    try:
        import artheenoi_agent
        state = artheenoi_agent.get_state()
    except Exception:
        state = {"running": False, "error": "agent module ไม่พบ"}
    return jsonify(state)

@app.route("/chat")
@login_required
def chat():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    uname  = session["username"]
    user   = get_user(uname)
    # Chat history stored in Flask session (cleared on logout)
    history = session.get("chat_history", [])
    return dw.chat_page(user, mkt, thb, history)

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    import dashboard_web as dw
    import requests as req
    uname   = session["username"]
    user    = get_user(uname)
    mkt, _, thb = _get_mkt()
    message = (request.json or {}).get("message", "").strip()
    if not message:
        return jsonify({"reply": "ส่งข้อความมาด้วยครับ"})

    history = session.get("chat_history", [])
    sys_prompt = dw._artheenoi_system_prompt(user, mkt, thb)
    recent = history[-20:]
    messages = [{"role": m["role"], "content": m["content"]} for m in recent]
    messages.append({"role": "user", "content": message})

    reply = ""
    or_key = _get_user_or_key(uname)   # ใช้ key ของ user ก่อน
    if or_key:
        try:
            r = req.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {or_key}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://artheenoi-dashboard.onrender.com"},
                json={"model": "claude-haiku-4-5-20251001",
                      "max_tokens": 700,
                      "system": sys_prompt,
                      "messages": messages},
                timeout=25, verify=False
            )
            reply = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning(f"[Chat] OpenRouter error: {e}")
            reply = "⚠️ เชื่อมต่อ AI ไม่ได้ตอนนี้ กรุณาลองใหม่"
    else:
        reply = _rule_based_reply(message, user, mkt, thb)

    # Save to session history
    history.append({"role": "user",      "content": message})
    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history[-40:]  # keep 40 turns max
    session.modified = True

    return jsonify({"reply": reply})

@app.route("/chat/clear", methods=["POST"])
@login_required
def chat_clear():
    session.pop("chat_history", None)
    return redirect("/chat")

def _rule_based_reply(msg: str, user: dict, mkt: dict, thb: float) -> str:
    """Simple rule-based chat fallback when no OpenRouter key."""
    import dashboard_web as dw
    msg_l = msg.lower()
    port  = user.get("portfolio", {})

    if any(w in msg_l for w in ["พอร์ต", "portfolio", "p&l", "กำไร", "ขาดทุน"]):
        total_v = total_c = 0
        lines = []
        for sym, info in port.items():
            d = mkt.get(sym, {})
            if not d.get("price"): continue
            v = d["price"] * float(info.get("shares", 0))
            c = float(info.get("cost", 0)) * float(info.get("shares", 0))
            pnl = v - c
            total_v += v; total_c += c
            lines.append(f"• {sym}: ${d['price']:,.2f} P&L {'+' if pnl>=0 else ''}${pnl:,.0f}")
        pnl_t = total_v - total_c
        s = f"รวม P&L: {'+' if pnl_t>=0 else ''}${pnl_t:,.0f} ({'+' if pnl_t>=0 else ''}{pnl_t/total_c*100:.1f}%)\n" if total_c else ""
        return s + "\n".join(lines) if lines else "ยังไม่มี portfolio ครับ ไปตั้งที่ Settings ก่อนนะ"

    if any(w in msg_l for w in ["ตลาด", "market", "qqq", "s&p", "nasdaq"]):
        d = mkt.get("QQQ", {})
        chg = d.get("chg", 0)
        mood = "บวก 🟢" if chg > 0.5 else "ลบ 🔴" if chg < -0.5 else "ทรงตัว ⚪"
        return f"ตลาดวันนี้{mood}\nQQQ: ${d.get('price',0):,.2f} ({chg:+.2f}%)\nIVV: ${mkt.get('IVV',{}).get('price',0):,.2f}"

    if any(w in msg_l for w in ["ทอง", "gold", "xau"]):
        d = mkt.get("GC=F", {})
        closes = d.get("closes", [])
        rsi = dw._calc_rsi(closes) if closes else None
        return f"ทองคำ: ${d.get('price',0):,.2f} ({d.get('chg',0):+.2f}%)\nRSI: {rsi or '—'}\n{'โซนซื้อ ✅' if rsi and rsi<45 else 'รอ pullback ⚠️' if rsi and rsi>65 else 'Neutral'}"

    if any(w in msg_l for w in ["btc", "bitcoin", "คริปโต", "crypto"]):
        d = mkt.get("BTC-USD", {})
        return f"BTC: ${d.get('price',0):,.0f} ({d.get('chg',0):+.2f}%)"

    return "ตอนนี้ยังไม่ได้ตั้ง OpenRouter API Key ครับ\nไป Render → Environment → เพิ่ม OPENROUTER_API_KEY\nจะตอบได้ทุกอย่างเลยครับ 🤖"

@app.route("/api/prices")
@login_required
def api_prices():
    """Live price JSON for frontend polling (every 90s)."""
    mkt, _, _ = _get_mkt()
    user  = get_user(session["username"])
    syms  = list(user.get("portfolio", {}).keys()) + user.get("watchlist", [])
    syms += ETFS + [GOLD, CRYPTO]
    data  = {}
    for sym in set(syms):
        d = mkt.get(sym)
        if d and d.get("price"):
            data[sym] = {
                "price": d["price"],
                "chg":   round(d.get("change_pct") or d.get("chg") or 0, 2),
            }
    return jsonify(data)

@app.route("/refresh", methods=["POST", "GET"])
@login_required
def refresh_user():
    uname = session["username"]
    if not _require_mkt():
        t = threading.Thread(target=_do_market_refresh, daemon=True)
        t.start()
        import dashboard_web as dw
        return dw.LOADING_PAGE
    # force invalidate user dashboard cache (legacy field)
    update_user_fields(uname, {"dashboard_html": None,
                               "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return redirect("/stocks")

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
        openrouter_key=user.get("openrouter_key", ""),
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

# ─── Charts ───────────────────────────────────────────────────────────────────

@app.route("/charts")
@login_required
def charts():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, thb = _get_mkt()
    user = get_user(session["username"])
    return dw.charts_page(user, mkt, thb)

@app.route("/api/chart/<sym>")
@login_required
def api_chart(sym):
    sym = sym.upper()
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        t = yf.Ticker(sym)
        hist = t.history(period="6mo", interval="1d")
        if hist.empty:
            return jsonify({"error": "no data"})
        closes  = [round(float(c), 4) for c in hist["Close"].dropna()]
        opens   = [round(float(c), 4) for c in hist["Open"].dropna()]
        highs   = [round(float(c), 4) for c in hist["High"].dropna()]
        lows    = [round(float(c), 4) for c in hist["Low"].dropna()]
        volumes = [int(v) for v in hist["Volume"].fillna(0)]
        dates   = [str(d.date()) for d in hist.index]
        # RSI
        from dashboard_web import _calc_rsi
        rsi_series = []
        for i in range(14, len(closes)):
            r = _calc_rsi(closes[:i+1])
            if r is not None:
                rsi_series.append(r)
        return jsonify({"dates": dates, "closes": closes, "opens": opens,
                        "highs": highs, "lows": lows, "volumes": volumes,
                        "rsi": rsi_series})
    except Exception as e:
        log.warning(f"[api/chart/{sym}] {e}")
        return jsonify({"error": str(e)})

# ─── Alerts ───────────────────────────────────────────────────────────────────

@app.route("/alerts")
@login_required
def alerts():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.alerts_page(user, mkt)

@app.route("/alerts/add", methods=["POST"])
@login_required
def alerts_add():
    uname = session["username"]
    sym   = request.form.get("sym", "").upper().strip()
    cond  = request.form.get("condition", "above")
    try:
        price = float(request.form.get("price", 0) or 0)
    except (ValueError, TypeError):
        price = 0.0
    note  = request.form.get("note", "").strip()
    if not sym or not price:
        return redirect("/alerts")
    with _users_lock:
        users = load_users()
        user  = users.get(uname, {})
        alerts_list = user.get("alerts", [])
        new_id = max((a.get("id", 0) for a in alerts_list), default=0) + 1
        alerts_list.append({
            "id": new_id, "sym": sym, "condition": cond, "price": price,
            "note": note, "active": True,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "triggered_at": None,
        })
        user["alerts"] = alerts_list
        users[uname] = user
        save_users(users)
    return redirect("/alerts")

@app.route("/alerts/delete", methods=["POST"])
@login_required
def alerts_delete():
    uname    = session["username"]
    alert_id = int(request.form.get("alert_id", 0))
    with _users_lock:
        users = load_users()
        user  = users.get(uname, {})
        user["alerts"] = [a for a in user.get("alerts", []) if a.get("id") != alert_id]
        users[uname] = user
        save_users(users)
    return redirect("/alerts")

@app.route("/alerts/toggle", methods=["POST"])
@login_required
def alerts_toggle():
    uname    = session["username"]
    alert_id = int(request.form.get("alert_id", 0))
    with _users_lock:
        users = load_users()
        user  = users.get(uname, {})
        for a in user.get("alerts", []):
            if a.get("id") == alert_id:
                a["active"] = not a.get("active", True)
                break
        users[uname] = user
        save_users(users)
    return redirect("/alerts")

# ─── Calendar ─────────────────────────────────────────────────────────────────

@app.route("/calendar")
@login_required
def calendar():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.calendar_page(user, mkt)

# ─── Options ──────────────────────────────────────────────────────────────────

@app.route("/options")
@app.route("/options/<sym>")
@login_required
def options(sym=None):
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    sym  = (sym or request.args.get("sym", "")).upper() or None
    return dw.options_page(user, mkt, sym)

@app.route("/api/options/<sym>")
@login_required
def api_options(sym):
    sym = sym.upper()
    exp = request.args.get("exp", "")
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        t = yf.Ticker(sym)
        expiries = list(t.options) if t.options else []
        if not exp or exp not in expiries:
            return jsonify({"expiries": expiries, "calls": [], "puts": []})
        chain = t.option_chain(exp)
        def _tbl(df):
            cols = ["strike","lastPrice","bid","ask","volume","openInterest","impliedVolatility"]
            rows = []
            for _, row in df.iterrows():
                r = {}
                for c in cols:
                    try:
                        v = row.get(c)
                        if v is not None and not (isinstance(v, float) and math.isnan(v)):
                            r[c] = float(v)
                        else:
                            r[c] = 0
                    except Exception:
                        r[c] = 0
                rows.append(r)
            return rows
        return jsonify({
            "expiries": expiries,
            "calls": _tbl(chain.calls),
            "puts":  _tbl(chain.puts),
        })
    except Exception as e:
        log.warning(f"[api/options/{sym}] {e}")
        return jsonify({"error": str(e), "expiries": [], "calls": [], "puts": []})

@app.route("/ping")
def ping():
    """UptimeRobot keep-alive endpoint — ไม่ต้อง login"""
    try:
        import artheenoi_agent
        state = artheenoi_agent.get_state()
        agent_ok = state.get("running", False)
    except Exception:
        agent_ok = False
    return jsonify({"status": "ok", "agent": agent_ok,
                    "ts": datetime.now().isoformat()})

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

    # ArtheeNoi 24/7 Agent
    try:
        import artheenoi_agent
        def _mkt_data_fn():
            with _mkt_lock:
                return _mkt_cache.get("data") or {}
        artheenoi_agent.start(load_users, _mkt_data_fn)
        log.info("ArtheeNoi Agent started ✅")
    except Exception as e:
        log.warning(f"ArtheeNoi Agent ไม่สามารถ start: {e}")

    app.run(host="0.0.0.0", port=PORT, debug=False)
