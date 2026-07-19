"""
dashboard_server.py — ArtheeNoi Stock Dashboard v2 (Multi-User Web App)
ระบบ login ของใครของมัน + 5 pages: Stocks / Gold / Crypto / DCA / News
Deploy ขึ้น Render ฟรี — เพื่อนเปิด URL ได้เลย

Usage:
  python dashboard_server.py          # รันที่ port 5052
  PORT=8080 python dashboard_server.py
"""
import os, sys, json, time, threading, logging, math
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
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
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
            for k, u in users.items() if isinstance(u, dict) and not k.startswith("_")}
    # Preserve special root-level keys (not user records)
    if "_invite_codes" in users:
        data["_invite_codes"] = users["_invite_codes"]
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

# ─── Invite Codes ─────────────────────────────────────────────────────────────

def get_invite_codes() -> list:
    with _users_lock:
        data = load_users()
    return data.get("_invite_codes", [])

def save_invite_code(code: str):
    with _users_lock:
        users = load_users()
        codes = users.get("_invite_codes", [])
        codes.append({"code": code, "used": False, "created": datetime.now().isoformat()})
        users["_invite_codes"] = codes
        _save_users_raw(users)

def use_invite_code(code: str) -> bool:
    with _users_lock:
        users = load_users()
        codes = users.get("_invite_codes", [])
        for c in codes:
            if c["code"] == code and not c["used"]:
                c["used"] = True
                users["_invite_codes"] = codes
                _save_users_raw(users)
                return True
    return False

# ─── Multi-Portfolio Helpers ───────────────────────────────────────────────────

def _get_active_portfolio(user: dict) -> dict:
    """Return the currently active portfolio dict (backward-compatible)."""
    ports = user.get("portfolios")
    if ports and isinstance(ports, dict):
        active = user.get("active_portfolio", "default")
        return ports.get(active, ports.get("default", {}))
    return user.get("portfolio", {})

def _inject_active_portfolio(user: dict) -> dict:
    """Return a copy of user with 'portfolio' set to the active portfolio."""
    if user is None:
        return {}
    u = dict(user)
    u["portfolio"] = _get_active_portfolio(u)
    return u

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
        if not isinstance(u, dict):
            continue
        syms.update(u.get("portfolio", {}).keys())
        # Multi-portfolio support
        for p in u.get("portfolios", {}).values():
            if isinstance(p, dict):
                syms.update(p.keys())
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

        # Record daily portfolio snapshots for all users
        _record_portfolio_snapshots(mkt, thb)

        log.info(f"[Market] Refresh done — {len(mkt)} symbols, THB={thb:.2f}")
        return True

    except Exception as e:
        log.exception(f"[Market] Refresh error: {e}")
        return False
    finally:
        _refreshing.clear()

def _record_portfolio_snapshots(mkt: dict, thb: float):
    """Append daily portfolio value snapshot for every user (once per day)."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _users_lock:
            users = load_users()
            changed = False
            for uname, u in users.items():
                if not isinstance(u, dict) or uname.startswith("_"):
                    continue
                snaps = u.get("portfolio_snapshots", [])
                if snaps and snaps[-1].get("date") == today:
                    continue  # already recorded today
                # Calculate total portfolio value
                total = 0.0
                port = _get_active_portfolio(u)
                for sym, info in port.items():
                    d = mkt.get(sym, {})
                    if d.get("price"):
                        total += d["price"] * float(info.get("shares", 0))
                if total > 0:
                    snaps.append({"date": today, "value": round(total, 2),
                                  "thb": round(total * thb, 0)})
                    u["portfolio_snapshots"] = snaps[-365:]  # keep 1 year
                    changed = True
            if changed:
                _save_users_raw(users)
    except Exception as e:
        log.warning(f"[Snapshot] {e}")


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

    for sym, info in _get_active_portfolio(user).items():
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

  <!-- CSV Import / Export -->
  <div class="card">
    <h2>📥 Import / Export Portfolio (CSV)</h2>
    <p style="font-size:12px;color:#64748b;margin-bottom:14px">
      รูปแบบ CSV: <code style="background:#111d2e;padding:2px 6px;border-radius:4px">Symbol,Shares,Cost</code> (ต้องมี header row)<br>
      ตัวอย่าง: <code style="background:#111d2e;padding:2px 6px;border-radius:4px">NVDA,2,850.00</code>
    </p>
    <form method="POST" action="/settings/import-csv" enctype="multipart/form-data" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
      <input type="file" name="csv_file" accept=".csv" style="flex:1;background:#111d2e;border:1px solid #243040;color:#e2e8f0;border-radius:8px;padding:8px 12px;font-size:13px">
      <button type="submit" class="btn btn-primary">📥 Import</button>
    </form>
    <a href="/settings/export-csv" class="btn btn-secondary">📤 Export CSV ปัจจุบัน</a>
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
        <td style="color:#64748b">{{ (u.get('portfolio') or {})|length }} หุ้น</td>
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

  <!-- Invite Codes -->
  <div class="card">
    <h2>🔗 Invite Links (Self-Registration)</h2>
    <p style="font-size:12px;color:#64748b;margin-bottom:14px">สร้างลิงก์เชิญให้เพื่อน — ใช้ได้ครั้งเดียว</p>
    <button type="button" class="btn btn-primary" onclick="genInvite()">🔗 สร้าง Invite Link ใหม่</button>
    <div id="inviteResult" style="margin-top:12px;font-size:13px"></div>
    {% if invite_codes %}
    <table style="margin-top:14px;width:100%;border-collapse:collapse">
      <thead><tr><th style="text-align:left;font-size:11px;color:#64748b;padding:0 8px 6px">Code</th><th style="text-align:left;font-size:11px;color:#64748b;padding:0 8px 6px">Status</th><th style="text-align:left;font-size:11px;color:#64748b;padding:0 8px 6px">Created</th></tr></thead>
      <tbody>
      {% for ic in invite_codes|reverse %}
      <tr style="border-bottom:1px solid #1c2a3a">
        <td style="padding:7px 8px;font-family:monospace;font-size:12px;color:#e2e8f0">{{ ic.code }}</td>
        <td style="padding:7px 8px">
          {% if ic.used %}<span style="color:#64748b;font-size:11px">✓ ใช้แล้ว</span>
          {% else %}<span style="color:#10b981;font-size:11px;font-weight:700">● พร้อมใช้</span>{% endif %}
        </td>
        <td style="padding:7px 8px;font-size:11px;color:#64748b">{{ ic.created[:16] }}</td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% endif %}
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
<script>
async function genInvite() {
  const r = await fetch('/admin/invite', {method:'POST'});
  const d = await r.json();
  const box = document.getElementById('inviteResult');
  const url = window.location.origin + d.url;
  box.innerHTML = '<div style="background:#0f1623;border:1px solid #1c2a3a;border-radius:8px;padding:12px;margin-top:8px">'
    + '<div style="font-size:11px;color:#64748b;margin-bottom:6px">ลิงก์ใหม่ (ใช้ได้ 1 ครั้ง):</div>'
    + '<div style="display:flex;gap:8px;align-items:center">'
    + '<code style="flex:1;font-size:12px;color:#10b981;word-break:break-all">' + url + '</code>'
    + '<button onclick="navigator.clipboard.writeText(\''+url+'\').then(()=>this.textContent=\'✓\')" style="background:#d97757;color:#fff;border:none;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:12px">Copy</button>'
    + '</div></div>';
  setTimeout(() => location.reload(), 3000);
}
</script>
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
    user = _inject_active_portfolio(get_user(session["username"]))
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
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.gold_page(user, mkt)

@app.route("/crypto")
@login_required
def crypto():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, _ = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.crypto_page(user, mkt)

@app.route("/dca")
@login_required
def dca():
    import dashboard_web as dw
    if not _require_mkt():
        return dw.LOADING_PAGE
    mkt, _, _ = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
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
    user = _inject_active_portfolio(get_user(session["username"]))
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
    user  = _inject_active_portfolio(get_user(uname))
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
    user  = _inject_active_portfolio(get_user(uname))
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
    port  = _get_active_portfolio(user)

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

@app.route("/api/alerts")
@login_required
def api_alerts():
    """Return current user's active (non-triggered) alerts for browser polling."""
    user = get_user(session["username"])
    alerts = (user or {}).get("alerts", [])
    active = [a for a in alerts if a.get("active", True) and not a.get("triggered_at")]
    return jsonify({"active": active})


def _send_telegram(text: str) -> None:
    """Fire-and-forget Telegram message. Silently ignored if token not set."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import urllib.request as _ur
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID,
                              "text": text, "parse_mode": "HTML"}).encode()
        req = _ur.Request(url, data=payload,
                          headers={"Content-Type": "application/json"})
        _ur.urlopen(req, timeout=5)
    except Exception:
        pass


@app.route("/api/alert-log", methods=["POST"])
@login_required
def api_alert_log():
    """Browser calls this when a price alert triggers — append to alert_history + Telegram."""
    uname = session["username"]
    data  = request.json or {}
    sym   = data.get("sym", "").upper()
    if not sym:
        return jsonify({"ok": False})
    condition = data.get("condition", "")
    target    = data.get("target", 0)
    actual    = data.get("actual", 0)
    ts        = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = {"sym": sym, "condition": condition,
             "target": target, "actual": actual, "ts": ts}
    with _users_lock:
        users = load_users()
        hist = users[uname].setdefault("alert_history", [])
        hist.append(entry)
        users[uname]["alert_history"] = hist[-200:]
        save_users(users)
    # Telegram notification (non-blocking)
    arrow = "🔴" if "below" in condition.lower() or "sell" in condition.lower() else "🟢"
    tg_msg = (f"{arrow} <b>Alert: {sym}</b>\n"
              f"เงื่อนไข: {condition}\n"
              f"เป้า: ${target}  |  ราคาจริง: ${actual}\n"
              f"⏱ {ts}")
    threading.Thread(target=_send_telegram, args=(tg_msg,), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/alerts/clear-log", methods=["POST"])
@login_required
def alerts_clear_log():
    uname = session["username"]
    update_user_fields(uname, {"alert_history": []})
    return redirect("/alerts")


@app.route("/api/prices")
@login_required
def api_prices():
    """Live price JSON for frontend polling (every 60s). Includes RSI."""
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user  = get_user(session["username"])
    syms  = list(_get_active_portfolio(user).keys()) + user.get("watchlist", [])
    syms += ETFS + [GOLD, CRYPTO]
    data  = {"_thb": round(thb, 2)}
    for sym in set(syms):
        d = mkt.get(sym)
        if d and d.get("price"):
            closes = d.get("closes", [])
            rsi = dw._calc_rsi(closes) if len(closes) >= 15 else None
            data[sym] = {
                "price": d["price"],
                "chg":   round(d.get("change_pct") or d.get("chg") or 0, 2),
                "rsi":   round(rsi, 1) if rsi else None,
            }
    return jsonify(data)


@app.route("/api/ticker")
@login_required
def api_ticker():
    """JSON ticker data for live 30s auto-update."""
    mkt, _, _ = _get_mkt()
    order = ["QQQ", "IVV", "DIA", "GC=F", "BTC-USD", "NVDA", "MSFT",
             "GOOGL", "META", "AMZN", "TSLA", "AVGO", "AMD"]
    items = []
    for sym in order:
        d = mkt.get(sym)
        if not d or not d.get("price"):
            continue
        chg = d.get("change_pct") or d.get("chg") or 0
        label = {"GC=F": "GOLD", "BTC-USD": "BTC"}.get(sym, sym)
        items.append({"sym": sym, "label": label,
                      "price": round(d["price"], 2), "chg": round(chg, 2)})
    return jsonify(items)


@app.route("/api/news/<sym>")
@login_required
def api_news(sym):
    """News for a symbol via MarketAux."""
    sym = sym.upper()
    articles = []
    if MARKETAUX_KEY:
        try:
            import requests as req
            r = req.get(
                "https://api.marketaux.com/v1/news/all",
                params={"symbols": sym, "filter_entities": "true",
                        "language": "en", "limit": 5,
                        "api_token": MARKETAUX_KEY},
                timeout=8, verify=False
            )
            for a in r.json().get("data", [])[:5]:
                articles.append({
                    "title": a.get("title", ""),
                    "url":   a.get("url", ""),
                    "published": (a.get("published_at", "") or "")[:10],
                    "source": a.get("source", ""),
                    "sentiment": (a.get("entities") or [{}])[0].get("sentiment_score", 0),
                })
        except Exception as e:
            log.warning(f"[News] {sym}: {e}")
    return jsonify({"sym": sym, "articles": articles})


@app.route("/api/fundamentals/<sym>")
@login_required
def api_fundamentals(sym):
    """Fundamental data via yfinance (incl. analyst ratings + price target)."""
    sym = sym.upper()
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        info = yf.Ticker(sym).info or {}

        def _s(k, fmt=None):
            v = info.get(k)
            if v is None:
                return "—"
            try:
                return format(float(v), fmt) if fmt else v
            except Exception:
                return str(v)

        def _mill(k):
            v = info.get(k)
            if v is None:
                return "—"
            try:
                v = float(v)
                if v >= 1e12: return f"${v/1e12:.2f}T"
                if v >= 1e9:  return f"${v/1e9:.2f}B"
                if v >= 1e6:  return f"${v/1e6:.2f}M"
                return f"${v:,.0f}"
            except Exception:
                return "—"

        def _pct(k):
            v = info.get(k)
            try:
                return f"{float(v)*100:.1f}%" if v is not None else "—"
            except Exception:
                return "—"

        # Analyst consensus
        rec_key = info.get("recommendationKey", "")
        rec_map = {"strongBuy": "Strong Buy", "buy": "Buy", "hold": "Hold",
                   "sell": "Sell", "strongSell": "Strong Sell"}
        analyst_rec = rec_map.get(rec_key, rec_key.title() if rec_key else "—")
        n_analysts = info.get("numberOfAnalystOpinions", "—")
        target_mean = _s("targetMeanPrice", ",.2f")
        target_high = _s("targetHighPrice", ",.2f")
        target_low  = _s("targetLowPrice",  ",.2f")

        return jsonify({
            "sym": sym,
            "name": info.get("longName") or info.get("shortName", sym),
            "sector": info.get("sector", "—"),
            "industry": info.get("industry", "—"),
            "market_cap": _mill("marketCap"),
            "pe": _s("trailingPE", ".1f"),
            "forward_pe": _s("forwardPE", ".1f"),
            "eps": _s("trailingEps", ".2f"),
            "revenue": _mill("totalRevenue"),
            "revenue_growth": _pct("revenueGrowth"),
            "gross_margin": _pct("grossMargins"),
            "debt_equity": _s("debtToEquity", ".1f"),
            "roe": _pct("returnOnEquity"),
            "dividend_yield": _pct("dividendYield"),
            "beta": _s("beta", ".2f"),
            "avg_volume": _mill("averageVolume"),
            "description": (info.get("longBusinessSummary", "") or "")[:400],
            # Analyst
            "analyst_rec": analyst_rec,
            "n_analysts": str(n_analysts),
            "target_mean": target_mean,
            "target_high": target_high,
            "target_low":  target_low,
        })
    except Exception as e:
        return jsonify({"sym": sym, "error": str(e)})


@app.route("/api/earnings/<sym>")
@login_required
def api_earnings(sym):
    """Quarterly EPS history (beat/miss vs estimate) via yfinance."""
    sym = sym.upper()
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        t = yf.Ticker(sym)
        rows = []
        try:
            hist = t.earnings_history
            if hist is not None and not hist.empty:
                for _, row in hist.tail(8).iterrows():
                    eps_est = row.get("epsEstimate", None)
                    eps_act = row.get("epsActual", None)
                    if eps_act is None:
                        continue
                    surprise = None
                    if eps_est and eps_est != 0:
                        surprise = round((eps_act - eps_est) / abs(eps_est) * 100, 1)
                    rows.append({
                        "date": str(row.name)[:10] if hasattr(row, "name") else "",
                        "eps_est": round(float(eps_est), 2) if eps_est is not None else None,
                        "eps_act": round(float(eps_act), 2),
                        "surprise_pct": surprise,
                        "beat": surprise is not None and surprise > 0,
                    })
        except Exception:
            pass
        # Fallback: quarterly_earnings DataFrame
        if not rows:
            try:
                qe = t.quarterly_earnings
                if qe is not None and not qe.empty:
                    for idx, row in qe.tail(8).iterrows():
                        rows.append({
                            "date": str(idx)[:10],
                            "eps_act": round(float(row.get("Earnings", 0)), 2),
                            "revenue": round(float(row.get("Revenue", 0)) / 1e9, 2),
                        })
            except Exception:
                pass
        return jsonify({"sym": sym, "quarters": list(reversed(rows))})
    except Exception as e:
        return jsonify({"sym": sym, "quarters": [], "error": str(e)})


@app.route("/api/portfolio-history")
@login_required
def api_portfolio_history():
    """Return this user's daily portfolio value snapshots."""
    user = get_user(session["username"])
    snaps = (user or {}).get("portfolio_snapshots", [])
    return jsonify({"snapshots": snaps[-90:]})  # 90 days


# ─── Trade Journal ─────────────────────────────────────────────────────────────

@app.route("/journal")
@login_required
def journal():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.journal_page(user, mkt)


@app.route("/journal/add", methods=["POST"])
@login_required
def journal_add():
    uname  = session["username"]
    sym    = request.form.get("sym", "").upper().strip()
    action = request.form.get("action", "NOTE")
    price  = request.form.get("price", "").strip()
    reason = request.form.get("reason", "").strip()
    notes  = request.form.get("notes", "").strip()
    if sym or notes:
        entry = {
            "id": int(time.time()),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sym": sym, "action": action,
            "price": price, "reason": reason, "notes": notes,
        }
        with _users_lock:
            users = load_users()
            users[uname].setdefault("trade_journal", []).append(entry)
            save_users(users)
    return redirect("/journal")


@app.route("/journal/delete", methods=["POST"])
@login_required
def journal_delete():
    uname = session["username"]
    try:
        jid = int(request.form.get("jid", 0))
    except (ValueError, TypeError):
        jid = 0
    with _users_lock:
        users = load_users()
        jl = users[uname].get("trade_journal", [])
        users[uname]["trade_journal"] = [e for e in jl if e.get("id") != jid]
        save_users(users)
    return redirect("/journal")


# ─── Watchlist Group routes ────────────────────────────────────────────────────

@app.route("/watchlist/set-group", methods=["POST"])
@login_required
def watchlist_set_group():
    sym   = request.form.get("sym", "").upper().strip()
    group = request.form.get("group", "").strip()
    if sym:
        uname = session["username"]
        with _users_lock:
            users = load_users()
            meta = users[uname].setdefault("watchlist_meta", {})
            meta.setdefault(sym, {})["group"] = group
            save_users(users)
    return redirect("/watchlist")


@app.route("/watchlist")
@login_required
def watchlist_page():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.watchlist_page(user, mkt)


@app.route("/watchlist/add", methods=["POST"])
@login_required
def watchlist_add():
    sym   = request.form.get("sym", "").upper().strip()
    group = request.form.get("group", "").strip()
    if sym:
        uname = session["username"]
        with _users_lock:
            users = load_users()
            wl = users[uname].get("watchlist", [])
            if sym not in wl:
                wl.append(sym)
            users[uname]["watchlist"] = wl
            if group:
                meta = users[uname].setdefault("watchlist_meta", {})
                meta.setdefault(sym, {})["group"] = group
            save_users(users)
    return redirect("/watchlist")


@app.route("/watchlist/remove", methods=["POST"])
@login_required
def watchlist_remove():
    sym = request.form.get("sym", "").upper().strip()
    if sym:
        uname = session["username"]
        with _users_lock:
            users = load_users()
            wl = users[uname].get("watchlist", [])
            if sym in wl:
                wl.remove(sym)
            users[uname]["watchlist"] = wl
            save_users(users)
    return redirect("/watchlist")


@app.route("/api/compare")
@login_required
def api_compare():
    """Return normalized (base-100) price series for 2-5 symbols."""
    syms_raw = request.args.get("syms", "")
    period   = request.args.get("period", "1y")
    syms = [s.strip().upper() for s in syms_raw.split(",") if s.strip()][:5]
    if not syms:
        return jsonify({"error": "no symbols"})
    try:
        import yfinance as yf
        result = {}
        for sym in syms:
            try:
                h = yf.download(sym, period=period, interval="1d",
                                progress=False, auto_adjust=True)
                if not h.empty and "Close" in h.columns:
                    closes = h["Close"].squeeze()
                    base = float(closes.iloc[0])
                    result[sym] = [
                        {"date": str(d.date()), "val": round(float(v)/base*100, 2)}
                        for d, v in closes.items()
                    ]
            except Exception:
                continue
        if not result:
            return jsonify({"error": "ดึงข้อมูลไม่ได้"})
        return jsonify({"series": result, "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/heatmap")
@login_required
def heatmap():
    import dashboard_web as dw
    mkt, macro, _ = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.heatmap_page(user, mkt, macro)


@app.route("/analytics")
@login_required
def analytics():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.analytics_page(user, mkt, thb)


@app.route("/scanner")
@login_required
def scanner():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.scanner_page(user, mkt)

@app.route("/api/correlation")
@login_required
def api_correlation():
    """Return correlation matrix for requested symbols using 1Y daily returns."""
    raw = request.args.get("syms", "")
    syms = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if len(syms) < 2:
        return jsonify({"error": "ต้องการอย่างน้อย 2 symbols"})
    syms = syms[:15]  # cap at 15
    try:
        import yfinance as yf
        import pandas as pd
        closes = {}
        for sym in syms:
            try:
                hist = yf.download(sym, period="1y", interval="1d",
                                   progress=False, auto_adjust=True)
                if not hist.empty and "Close" in hist.columns:
                    closes[sym] = hist["Close"].squeeze()
            except Exception:
                pass
        if len(closes) < 2:
            return jsonify({"error": "ดึงข้อมูลไม่ได้ — ลองใหม่อีกครั้ง"})
        df = pd.DataFrame(closes).dropna()
        rets = df.pct_change().dropna()
        corr = rets.corr()
        valid = list(corr.columns)
        matrix = [[round(corr.loc[r, c], 4) for c in valid] for r in valid]
        return jsonify({
            "syms": valid,
            "matrix": matrix,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/correlation")
@login_required
def correlation():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.correlation_page(user, mkt)


@app.route("/report")
@login_required
def report():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.report_page(user, mkt or {}, thb or 34.0)


@app.route("/api/risk-metrics")
@login_required
def api_risk_metrics():
    """Compute Sharpe, Beta, MaxDrawdown, Volatility for the user's portfolio."""
    try:
        import yfinance as yf
        import pandas as pd
        import math as _m
        user = _inject_active_portfolio(get_user(session["username"]))
        port = user.get("portfolio", {})
        if not port:
            return jsonify({"error": "ไม่มีหุ้นใน portfolio"})
        # Build equal-weighted portfolio returns (weighted by current value)
        mkt, _, _ = _get_mkt()
        weights = {}
        total_val = 0.0
        for sym, info in port.items():
            qty  = float(info.get("qty", 0) or 0)
            price = float((mkt or {}).get(sym, {}).get("price") or 0)
            val  = qty * price
            weights[sym] = val
            total_val += val
        if total_val == 0:
            return jsonify({"error": "มูลค่า portfolio เป็น 0"})
        # Fetch 1Y closes
        all_syms = list(weights.keys()) + ["SPY"]
        closes = {}
        for sym in all_syms:
            try:
                h = yf.download(sym, period="1y", interval="1d",
                                progress=False, auto_adjust=True)
                if not h.empty and "Close" in h.columns:
                    closes[sym] = h["Close"].squeeze()
            except Exception:
                pass
        if not closes or "SPY" not in closes:
            return jsonify({"error": "ดึงข้อมูลไม่ได้"})
        df = pd.DataFrame({s: closes[s] for s in closes}).dropna()
        rets = df.pct_change().dropna()
        # Weighted portfolio return series
        valid_syms = [s for s in weights if s in rets.columns]
        if not valid_syms:
            return jsonify({"error": "ไม่มีข้อมูลพอ"})
        w = {s: weights[s] / total_val for s in valid_syms}
        port_ret = sum(rets[s] * w[s] for s in valid_syms)
        spy_ret  = rets["SPY"]
        # Metrics
        trading_days = 252
        ann_ret = float(port_ret.mean() * trading_days)
        ann_vol = float(port_ret.std() * _m.sqrt(trading_days))
        risk_free = 0.045  # ~4.5% risk-free rate
        sharpe = (ann_ret - risk_free) / ann_vol if ann_vol else 0
        # Beta
        cov = port_ret.cov(spy_ret)
        var_spy = spy_ret.var()
        beta = float(cov / var_spy) if var_spy else 1.0
        # Max Drawdown
        cumret = (1 + port_ret).cumprod()
        rolling_max = cumret.cummax()
        dd = (cumret - rolling_max) / rolling_max
        max_dd = float(dd.min())
        # Sortino
        neg = port_ret[port_ret < 0]
        downvol = float(neg.std() * _m.sqrt(trading_days)) if len(neg) > 0 else 0.0001
        sortino = (ann_ret - risk_free) / downvol if downvol else 0
        # Win rate
        win_rate = float((port_ret > 0).sum() / len(port_ret) * 100)
        return jsonify({
            "ann_return": round(ann_ret * 100, 2),
            "ann_vol": round(ann_vol * 100, 2),
            "sharpe": round(sharpe, 3),
            "sortino": round(sortino, 3),
            "beta": round(beta, 3),
            "max_drawdown": round(max_dd * 100, 2),
            "win_rate": round(win_rate, 1),
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/risk")
@login_required
def risk():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.risk_page(user, mkt, thb)


@app.route("/api/benchmark")
@login_required
def api_benchmark():
    """Portfolio value history + SPY/QQQ normalized to compare performance."""
    try:
        import yfinance as yf
        user = _inject_active_portfolio(get_user(session["username"]))
        snaps = user.get("portfolio_snapshots", [])
        if len(snaps) < 2:
            return jsonify({"error": "ยังไม่มี portfolio history — รอให้ระบบบันทึกข้อมูล 2 วันขึ้นไป"})
        # Fetch SPY + QQQ for the same date range
        start_date = snaps[0]["date"]
        bench_data = {}
        for sym in ["SPY", "QQQ"]:
            try:
                h = yf.download(sym, start=start_date, interval="1d",
                                progress=False, auto_adjust=True)
                if not h.empty and "Close" in h.columns:
                    closes = h["Close"].squeeze()
                    base = float(closes.iloc[0])
                    bench_data[sym] = [
                        {"date": str(d.date()), "pct": round((v/base - 1)*100, 2)}
                        for d, v in closes.items()
                    ]
            except Exception:
                pass
        # Normalize portfolio snaps to % change from first value
        base_port = snaps[0]["value"] or 1
        port_series = [
            {"date": s["date"], "pct": round((s["value"]/base_port - 1)*100, 2)}
            for s in snaps if s.get("value")
        ]
        return jsonify({"portfolio": port_series, "benchmarks": bench_data,
                        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/benchmark")
@login_required
def benchmark():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.benchmark_page(user, mkt, thb)


@app.route("/realized")
@login_required
def realized():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.realized_page(user, mkt or {}, thb or 34.0)


@app.route("/realized/add", methods=["POST"])
@login_required
def realized_add():
    uname = session["username"]
    f = request.form
    try:
        qty       = float(f.get("qty", 0) or 0)
        cost_per  = float(f.get("cost_per", 0) or 0)
        sell_per  = float(f.get("sell_price", 0) or 0)
    except ValueError:
        qty = cost_per = sell_per = 0
    pnl = (sell_per - cost_per) * qty
    entry = {
        "id": int(time.time() * 1000),
        "date": f.get("date", datetime.now().strftime("%Y-%m-%d")),
        "sym": f.get("sym", "").upper().strip(),
        "qty": qty,
        "cost_per": cost_per,
        "sell_price": sell_per,
        "pnl": round(pnl, 2),
        "notes": f.get("notes", ""),
    }
    with _users_lock:
        users = load_users()
        users[uname].setdefault("realized_trades", []).append(entry)
        save_users(users)
    return redirect("/realized")


@app.route("/realized/delete", methods=["POST"])
@login_required
def realized_delete():
    uname = session["username"]
    rid   = int(request.form.get("rid", 0))
    with _users_lock:
        users = load_users()
        trades = users[uname].get("realized_trades", [])
        users[uname]["realized_trades"] = [t for t in trades if t.get("id") != rid]
        save_users(users)
    return redirect("/realized")


@app.route("/compare")
@login_required
def compare():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.compare_page(user, mkt or {})


@app.route("/api/macro")
@login_required
def api_macro():
    """Macro data: VIX, 10Y/2Y yields, DXY, Oil, Gold."""
    try:
        import yfinance as yf
        macro_syms = {
            "VIX":   "^VIX",
            "10Y":   "^TNX",
            "2Y":    "^IRX",
            "DXY":   "DX-Y.NYB",
            "OIL":   "CL=F",
            "GOLD":  "GC=F",
            "SPY":   "SPY",
            "BTC":   "BTC-USD",
        }
        result = {}
        for label, sym in macro_syms.items():
            try:
                t = yf.Ticker(sym)
                info = t.fast_info
                price = float(getattr(info, "last_price", 0) or 0)
                prev  = float(getattr(info, "previous_close", price) or price)
                chg   = ((price - prev) / prev * 100) if prev else 0
                result[label] = {"price": round(price, 2), "chg": round(chg, 2), "sym": sym}
            except Exception:
                result[label] = {"price": 0, "chg": 0, "sym": sym}
        # Yield curve spread
        y10 = result.get("10Y", {}).get("price", 0)
        y2  = result.get("2Y", {}).get("price", 0)
        spread = round(y10 - y2, 3) if y10 and y2 else None
        return jsonify({"data": result, "yield_spread": spread,
                        "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/macro")
@login_required
def macro():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    if not _require_mkt():
        return dw.LOADING_PAGE
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.macro_page(user, mkt or {})


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
        portfolio=_get_active_portfolio(user),
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

    with _users_lock:
        users = load_users()
        u = users[uname]
        if "portfolios" in u:
            active = u.get("active_portfolio", "default")
            u.setdefault("portfolios", {})[active] = portfolio
        else:
            u["portfolio"] = portfolio
        u["dashboard_html"] = None
        save_users(users)
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
        raw_users = load_users()
    # Filter only real user entries (exclude special keys like _invite_codes)
    users = {k: v for k, v in raw_users.items()
             if isinstance(v, dict) and not k.startswith("_")}
    invite_codes = raw_users.get("_invite_codes", [])
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
        invite_codes=invite_codes,
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

@app.route("/chart/<sym>")
@login_required
def chart_sym(sym):
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user = get_user(session["username"])
    return dw.charts_page(user, mkt, thb, sym=sym.upper())

@app.route("/api/chart/<sym>")
@login_required
def api_chart(sym):
    sym = sym.upper()
    period = request.args.get("period", "1y")
    interval_map = {
        "5d": "1d", "1mo": "1d", "3mo": "1d", "6mo": "1d",
        "1y": "1d", "2y": "1wk", "5y": "1wk",
    }
    interval = interval_map.get(period, "1d")
    try:
        import yfinance as yf
        import warnings; warnings.filterwarnings("ignore")
        t = yf.Ticker(sym)
        hist = t.history(period=period, interval=interval)
        if hist.empty:
            return jsonify({"error": "no data", "candles": []})
        fi = t.fast_info
        candles = []
        for ts, row in hist.iterrows():
            try:
                date_str = ts.strftime("%Y-%m-%d")
                candles.append({
                    "time":   date_str,
                    "open":   round(float(row["Open"]),   4),
                    "high":   round(float(row["High"]),   4),
                    "low":    round(float(row["Low"]),    4),
                    "close":  round(float(row["Close"]),  4),
                    "volume": int(row["Volume"] or 0),
                })
            except Exception:
                pass
        last_price = 0.0
        try:
            last_price = round(float(fi.last_price or (candles[-1]["close"] if candles else 0)), 4)
        except Exception:
            last_price = candles[-1]["close"] if candles else 0.0
        return jsonify({
            "symbol":   sym,
            "name":     getattr(fi, "exchange", sym),
            "currency": "USD",
            "price":    last_price,
            "candles":  candles,
        })
    except Exception as e:
        log.warning(f"[api/chart/{sym}] {e}")
        return jsonify({"error": str(e), "candles": []})

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

@app.route("/portfolio/add-quick", methods=["POST"])
@login_required
def portfolio_add_quick():
    """Quick-add a symbol to portfolio from the screener page."""
    sym    = request.form.get("sym", "").upper().strip()
    shares = float(request.form.get("shares", 0) or 0)
    cost   = float(request.form.get("cost", 0) or 0)
    if not sym or shares <= 0 or cost <= 0:
        return redirect("/screener")
    uname = session["username"]
    with _users_lock:
        users = load_users()
        u = users[uname]
        port = _get_active_portfolio(u)
        if sym in port:
            # Weighted average cost on re-add
            old_shares = port[sym]["shares"]
            old_cost   = port[sym]["cost"]
            new_shares = old_shares + shares
            port[sym]["cost"]   = round((old_shares * old_cost + shares * cost) / new_shares, 4)
            port[sym]["shares"] = round(new_shares, 4)
        else:
            port[sym] = {"shares": round(shares, 4), "cost": round(cost, 4)}
        # Save back to correct location
        if "portfolios" in u:
            active = u.get("active_portfolio", "default")
            u.setdefault("portfolios", {})[active] = port
        else:
            u["portfolio"] = port
        save_users(users)
    return redirect("/stocks")


@app.route("/backtest")
@login_required
def backtest():
    import dashboard_web as dw
    mkt, _, _ = _get_mkt()
    user = get_user(session["username"])
    return dw.backtest_page(user, mkt)


@app.route("/api/backtest")
@login_required
def api_backtest():
    sym      = request.args.get("sym", "NVDA").upper()
    strategy = request.args.get("strategy", "rsi")
    period   = request.args.get("period", "1y")
    try:
        import yfinance as yf, warnings, math as _math
        warnings.filterwarnings("ignore")
        hist = yf.Ticker(sym).history(period=period, interval="1d")
        if hist.empty:
            return jsonify({"error": "no data"})

        closes  = [float(c) for c in hist["Close"].tolist()]
        dates   = [str(d.date()) for d in hist.index]
        n       = len(closes)

        def ma(data, w):
            return [sum(data[max(0, i - w + 1):i + 1]) / min(i + 1, w) for i in range(len(data))]

        def rsi14(data):
            result = [None] * 14
            gains, losses = [], []
            for i in range(1, 15):
                d = data[i] - data[i - 1]
                gains.append(max(d, 0)); losses.append(max(-d, 0))
            ag, al = sum(gains) / 14, sum(losses) / 14
            result[14] = 100 - 100 / (1 + ag / al) if al else 100
            for i in range(15, len(data)):
                d = data[i] - data[i - 1]
                ag = (ag * 13 + max(d, 0)) / 14
                al = (al * 13 + max(-d, 0)) / 14
                result.append(100 - 100 / (1 + ag / al) if al else 100)
            return result

        def ema(data, w):
            k = 2 / (w + 1); e = data[0]; out = [e]
            for v in data[1:]:
                e = v * k + e * (1 - k); out.append(e)
            return out

        def bb(data, w=20, mult=2):
            upper, lower = [], []
            for i in range(len(data)):
                sl = data[max(0, i - w + 1):i + 1]
                m = sum(sl) / len(sl)
                std = (_math.sqrt(sum((x - m) ** 2 for x in sl) / len(sl))) if len(sl) > 1 else 0
                upper.append(m + mult * std); lower.append(m - mult * std)
            return upper, lower

        # Generate signals
        signals = [None] * n
        if strategy == "rsi":
            rsi_vals = rsi14(closes)
            for i in range(1, n):
                if rsi_vals[i] and rsi_vals[i - 1]:
                    if rsi_vals[i - 1] >= 30 and rsi_vals[i] < 30: signals[i] = "BUY"
                    elif rsi_vals[i - 1] <= 70 and rsi_vals[i] > 70: signals[i] = "SELL"
        elif strategy == "ma":
            ma20, ma50 = ma(closes, 20), ma(closes, 50)
            for i in range(1, n):
                if ma20[i - 1] <= ma50[i - 1] and ma20[i] > ma50[i]: signals[i] = "BUY"
                elif ma20[i - 1] >= ma50[i - 1] and ma20[i] < ma50[i]: signals[i] = "SELL"
        elif strategy == "bb":
            upper, lower = bb(closes)
            for i in range(1, n):
                if closes[i] <= lower[i] and closes[i - 1] > lower[i - 1]: signals[i] = "BUY"
                elif closes[i] >= upper[i] and closes[i - 1] < upper[i - 1]: signals[i] = "SELL"
        elif strategy == "macd":
            macd_line = [e - s for e, s in zip(ema(closes, 12), ema(closes, 26))]
            sig_line  = ema(macd_line, 9)
            for i in range(1, n):
                if macd_line[i - 1] <= sig_line[i - 1] and macd_line[i] > sig_line[i]: signals[i] = "BUY"
                elif macd_line[i - 1] >= sig_line[i - 1] and macd_line[i] < sig_line[i]: signals[i] = "SELL"

        # Simulate trades (buy as many full shares as cash allows)
        trades = []
        position = None
        cash = 10000.0; shares_held = 0; equity = []

        for i in range(n):
            if signals[i] == "BUY" and position is None:
                shares_held = int(cash / closes[i])
                if shares_held > 0:
                    cash -= shares_held * closes[i]
                    position = {"date": dates[i], "price": closes[i], "shares": shares_held}
            elif signals[i] == "SELL" and position:
                proceeds = position["shares"] * closes[i]
                pl = proceeds - position["shares"] * position["price"]
                cash += proceeds
                trades.append({
                    "buy_date":   position["date"],
                    "sell_date":  dates[i],
                    "buy_price":  round(position["price"], 2),
                    "sell_price": round(closes[i], 2),
                    "shares":     position["shares"],
                    "pl":         round(pl, 2),
                })
                position = None; shares_held = 0
            equity.append(round(cash + shares_held * closes[i], 2))

        # Close any open position at last price
        if position:
            pl = position["shares"] * (closes[-1] - position["price"])
            cash += position["shares"] * closes[-1]
            trades.append({
                "buy_date":   position["date"],
                "sell_date":  dates[-1] + " (open)",
                "buy_price":  round(position["price"], 2),
                "sell_price": round(closes[-1], 2),
                "shares":     position["shares"],
                "pl":         round(pl, 2),
            })

        # Stats
        start_val = 10000.0
        end_val   = cash
        total_ret = (end_val - start_val) / start_val * 100
        wins      = [t for t in trades if t["pl"] > 0]
        win_rate  = len(wins) / len(trades) * 100 if trades else 0
        peak = start_val; max_dd = 0
        for v in equity:
            if v > peak: peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd: max_dd = dd

        equity_norm = [round(v / start_val * 100, 2) for v in equity]

        return jsonify({
            "sym": sym, "strategy": strategy, "period": period,
            "total_return": round(total_ret, 2), "win_rate": round(win_rate, 1),
            "max_drawdown": round(max_dd, 2), "num_trades": len(trades),
            "final_value": round(end_val, 2),
            "equity": equity_norm, "dates": dates, "trades": trades[-30:]
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)})


# ─── Self-Registration ───────────────────────────────────────────────────────

def _register_page(code="", error=""):
    err_html = (f'<div style="color:#ef5350;margin-bottom:12px;font-size:13px">⚠️ {error}</div>'
                if error else "")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>สมัครสมาชิก — ArtheeNoi</title>
    <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#131722;color:#d1d4dc;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}}
    .box{{background:#1e222d;border:1px solid #363a45;border-radius:12px;padding:32px;width:360px}}
    h2{{color:#2dd4bf;margin-bottom:4px;font-size:18px}} p{{color:#787b86;font-size:13px;margin-bottom:20px}}
    label{{font-size:12px;color:#787b86;display:block;margin-bottom:4px}}
    input{{width:100%;background:#2a2e39;border:1px solid #363a45;color:#d1d4dc;border-radius:6px;padding:9px 12px;font-size:14px;margin-bottom:14px;outline:none}}
    input:focus{{border-color:#2dd4bf}}
    button{{width:100%;background:#2dd4bf;color:#000;border:none;border-radius:6px;padding:10px;font-weight:700;cursor:pointer;font-size:14px}}
    button:hover{{filter:brightness(1.1)}}
    a{{color:#2dd4bf;font-size:13px;text-decoration:none}}
    </style></head>
    <body><div class="box">
    <h2>📊 ArtheeNoi</h2><p>สร้างบัญชีด้วยรหัสเชิญ</p>
    {err_html}
    <form method="POST">
    <input type="hidden" name="code" value="{code}">
    <label>รหัสเชิญ</label>
    <input value="{code}" readonly style="color:#787b86;cursor:default">
    <label>Username</label><input name="username" required placeholder="เช่น somchai">
    <label>ชื่อที่แสดง</label><input name="display_name" placeholder="เช่น สมชาย">
    <label>Password (อย่างน้อย 6 ตัว)</label>
    <input type="password" name="password" required>
    <button type="submit">สมัครสมาชิก</button>
    </form>
    <div style="margin-top:14px;text-align:center"><a href="/login">← กลับหน้า Login</a></div>
    </div></body></html>"""

@app.route("/register", methods=["GET", "POST"])
def register():
    code = request.args.get("code", "") or request.form.get("code", "")
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        display  = request.form.get("display_name", "").strip() or username
        if not use_invite_code(code):
            return _register_page(code, error="รหัสเชิญไม่ถูกต้องหรือถูกใช้แล้ว")
        if not username or len(password) < 6:
            use_invite_code_reverse = True  # need to restore code
            # Restore code since we consumed it
            with _users_lock:
                users = load_users()
                codes = users.get("_invite_codes", [])
                for c in codes:
                    if c["code"] == code and c["used"]:
                        c["used"] = False
                        break
                users["_invite_codes"] = codes
                _save_users_raw(users)
            return _register_page(code, error="username ต้องไม่ว่าง, password ต้องมีอย่างน้อย 6 ตัว")
        with _users_lock:
            users = load_users()
            real_users = {k: v for k, v in users.items()
                         if isinstance(v, dict) and not k.startswith("_")}
            if username in real_users:
                # Restore code
                codes = users.get("_invite_codes", [])
                for c in codes:
                    if c["code"] == code and c["used"]:
                        c["used"] = False; break
                users["_invite_codes"] = codes
                _save_users_raw(users)
                return _register_page(code, error=f"username '{username}' มีแล้ว")
            users[username] = {
                "password_hash": _hash(password),
                "display_name":  display,
                "role":          "user",
                "portfolio":     {},
                "watchlist":     ["NVDA", "MSFT", "GOOGL", "META", "AMZN"],
            }
            _save_users_raw(users)
        return redirect("/login?registered=1")
    return _register_page(code)

@app.route("/admin/invite", methods=["POST"])
@admin_required
def admin_invite():
    import secrets
    code = secrets.token_urlsafe(8)
    save_invite_code(code)
    return jsonify({"code": code, "url": f"/register?code={code}"})

# ─── Dividend Tracker ─────────────────────────────────────────────────────────

@app.route("/dividends")
@login_required
def dividends():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.dividends_page(user, mkt, thb)

@app.route("/dividends/add", methods=["POST"])
@login_required
def dividends_add():
    sym    = request.form.get("sym", "").upper().strip()
    date   = request.form.get("date", "")
    try:
        amount = float(request.form.get("amount", 0) or 0)
        shares = float(request.form.get("shares", 0) or 0)
    except (ValueError, TypeError):
        amount = shares = 0.0
    if sym and amount > 0 and shares > 0:
        entry = {"sym": sym, "date": date, "amount_usd": round(amount, 4),
                 "shares": round(shares, 4), "total": round(amount * shares, 4)}
        uname = session["username"]
        with _users_lock:
            users = load_users()
            users[uname].setdefault("dividends", []).append(entry)
            save_users(users)
    return redirect("/dividends")

@app.route("/dividends/delete", methods=["POST"])
@login_required
def dividends_delete():
    try:
        idx = int(request.form.get("idx", -1))
    except (ValueError, TypeError):
        idx = -1
    uname = session["username"]
    with _users_lock:
        users = load_users()
        divs = users[uname].get("dividends", [])
        if 0 <= idx < len(divs):
            divs.pop(idx)
        users[uname]["dividends"] = divs
        save_users(users)
    return redirect("/dividends")

# ─── Tools Page ───────────────────────────────────────────────────────────────

@app.route("/tools")
@login_required
def tools():
    import dashboard_web as dw
    mkt, _, thb = _get_mkt()
    user = _inject_active_portfolio(get_user(session["username"]))
    return dw.tools_page(user, mkt, thb)


@app.route("/tools/set-target", methods=["POST"])
@login_required
def tools_set_target():
    uname = session["username"]
    sym   = request.form.get("sym", "").upper().strip()
    try:
        pct = float(request.form.get("pct", 0) or 0)
    except (ValueError, TypeError):
        pct = 0.0
    if sym:
        with _users_lock:
            users = load_users()
            users[uname].setdefault("target_allocation", {})[sym] = round(pct, 1)
            save_users(users)
    return redirect("/stocks")

# ─── Multi-Portfolio Routes ───────────────────────────────────────────────────

@app.route("/portfolio/switch", methods=["POST"])
@login_required
def portfolio_switch():
    name = request.form.get("name", "default").strip()
    update_user_fields(session["username"], {"active_portfolio": name})
    return redirect("/stocks")

@app.route("/portfolio/new", methods=["POST"])
@login_required
def portfolio_new():
    name = request.form.get("name", "").strip()
    if name:
        uname = session["username"]
        with _users_lock:
            users = load_users()
            u = users[uname]
            # Migrate old format
            if "portfolios" not in u:
                u["portfolios"] = {"default": u.get("portfolio", {})}
            ports = u["portfolios"]
            if name not in ports:
                ports[name] = {}
            u["portfolios"] = ports
            u["active_portfolio"] = name
            save_users(users)
    return redirect("/stocks")

@app.route("/portfolio/delete-port", methods=["POST"])
@login_required
def portfolio_delete_port():
    name = request.form.get("name", "").strip()
    if name and name != "default":
        uname = session["username"]
        with _users_lock:
            users = load_users()
            u = users[uname]
            ports = u.get("portfolios", {})
            ports.pop(name, None)
            u["portfolios"] = ports
            if u.get("active_portfolio") == name:
                u["active_portfolio"] = "default"
            save_users(users)
    return redirect("/stocks")

# ─── PWA Manifest ────────────────────────────────────────────────────────────

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "ArtheeNoi Dashboard",
        "short_name": "ArtheeNoi",
        "description": "ระบบวิเคราะห์หุ้น AI",
        "start_url": "/stocks",
        "display": "standalone",
        "background_color": "#131722",
        "theme_color": "#131722",
        "orientation": "any",
        "icons": [
            {"src": "https://fav.farm/📊", "sizes": "192x192", "type": "image/png"},
            {"src": "https://fav.farm/📊", "sizes": "512x512", "type": "image/png"},
        ],
    })

# ─── CSV Import / Export ─────────────────────────────────────────────────────

@app.route("/settings/import-csv", methods=["POST"])
@login_required
def import_csv():
    f = request.files.get("csv_file")
    if not f:
        return redirect("/settings")
    try:
        import csv, io
        content = f.read().decode("utf-8-sig")
        reader  = csv.DictReader(io.StringIO(content))
        new_entries = {}
        for row in reader:
            sym    = (row.get("Symbol") or row.get("symbol", "")).upper().strip()
            try:
                shares = float(row.get("Shares") or row.get("shares") or 0)
                cost   = float(row.get("Cost")   or row.get("cost")   or 0)
            except (ValueError, TypeError):
                continue
            if sym and shares > 0 and cost > 0:
                new_entries[sym] = {"shares": round(shares, 4), "cost": round(cost, 4)}
        if new_entries:
            uname = session["username"]
            with _users_lock:
                users = load_users()
                u = users[uname]
                port = _get_active_portfolio(u)
                port.update(new_entries)
                if "portfolios" in u:
                    active = u.get("active_portfolio", "default")
                    u["portfolios"][active] = port
                else:
                    u["portfolio"] = port
                save_users(users)
    except Exception as e:
        log.warning(f"CSV import error: {e}")
    return redirect("/stocks")

@app.route("/settings/export-csv")
@login_required
def export_csv():
    user = _inject_active_portfolio(get_user(session["username"]))
    port = user.get("portfolio", {})
    active = (get_user(session["username"]) or {}).get("active_portfolio", "default")
    lines = ["Symbol,Shares,Cost\n"]
    for sym, d in port.items():
        lines.append(f"{sym},{d['shares']},{d['cost']}\n")
    return Response("".join(lines), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment;filename=portfolio_{active}.csv'})

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
