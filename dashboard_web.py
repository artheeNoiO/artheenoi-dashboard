"""
dashboard_web.py — ArtheeNoi Dashboard v2
New premium dark UI: black/gray theme + sidebar navigation
Pages: Stocks | Gold | Crypto | DCA | News | Signals | Paper Trading | AI
"""
import json
import math
import time
import logging
import requests
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent

# ─── Theme / CSS ──────────────────────────────────────────────────────────────

_CSS = """
:root {
  --bg:       #0a0a0c;
  --sb:       #0f0f12;
  --card:     #16161a;
  --card2:    #1c1c22;
  --border:   #252530;
  --bl:       #1e1e26;
  --text:     #f0f0f2;
  --mid:      #9999a8;
  --muted:    #5a5a68;
  --green:    #22c55e;
  --red:      #ef4444;
  --gold:     #f59e0b;
  --blue:     #3b82f6;
  --purple:   #8b5cf6;
  --teal:     #2dd4bf;
  --orange:   #f97316;
  --accent:   #4ade80;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;overflow:hidden}

/* ── Layout ── */
.layout{display:flex;height:100vh}

/* ── Sidebar ── */
.sb{width:64px;background:var(--sb);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:4px;flex-shrink:0;z-index:100}
.sb-logo{width:38px;height:38px;background:linear-gradient(135deg,#22c55e,#16a34a);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:12px;flex-shrink:0}
.sb-link{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer;transition:.15s;text-decoration:none;color:var(--muted);position:relative}
.sb-link:hover{background:var(--card);color:var(--mid)}
.sb-link.active{background:var(--card2);color:var(--text)}
.sb-link .tip{position:absolute;left:54px;background:#1e1e26;border:1px solid var(--border);padding:4px 10px;border-radius:6px;font-size:11px;white-space:nowrap;opacity:0;pointer-events:none;transition:.15s;color:var(--text)}
.sb-link:hover .tip{opacity:1}
.sb-spacer{flex:1}
.sb-bot{display:flex;flex-direction:column;align-items:center;gap:4px}

/* ── Main ── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}

/* ── Topbar ── */
.topbar{height:52px;background:var(--sb);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:16px;flex-shrink:0}
.topbar-title{font-size:15px;font-weight:700;color:var(--text)}
.topbar-sub{font-size:12px;color:var(--muted)}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:12px}
.top-pill{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;color:var(--mid)}
.top-user{font-size:12px;color:var(--muted);cursor:pointer}
.top-user:hover{color:var(--text)}

/* ── Tabs ── */
.tabs{display:flex;gap:2px;padding:0 20px;background:var(--sb);border-bottom:1px solid var(--border);flex-shrink:0}
.tab{padding:10px 16px;font-size:12px;font-weight:600;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;transition:.15s;white-space:nowrap}
.tab:hover{color:var(--mid)}
.tab.active{color:var(--text);border-bottom-color:var(--teal)}

/* ── Content ── */
.content{flex:1;overflow-y:auto;padding:20px}
.content::-webkit-scrollbar{width:6px}
.content::-webkit-scrollbar-track{background:transparent}
.content::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* ── Cards ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
.card-sm{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px}
.card-hdr{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-bottom:12px}

/* ── Grid ── */
.g2{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.g-auto{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
@media(max-width:900px){.g4{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.g4,.g3,.g2{grid-template-columns:1fr}.layout{flex-direction:column}.sb{width:100%;height:56px;flex-direction:row;padding:0 12px;overflow-x:auto}.sb-logo{margin-bottom:0;margin-right:8px}.sb-spacer,.sb-bot{display:none}}

/* ── Stat blocks ── */
.stat-val{font-size:22px;font-weight:800;line-height:1}
.stat-lbl{font-size:11px;color:var(--muted);margin-top:4px}
.pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--mid)}
.gold-c{color:var(--gold)}.blue-c{color:var(--blue)}.teal-c{color:var(--teal)}

/* ── Badges ── */
.badge{display:inline-flex;align-items:center;font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:.3px}
.badge-buy{background:#22c55e22;color:#22c55e;border:1px solid #22c55e44}
.badge-sell,.badge-avoid{background:#ef444422;color:#ef4444;border:1px solid #ef444444}
.badge-watch{background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b44}
.badge-wait,.badge-neutral{background:#6b6b7822;color:#9999a8;border:1px solid #6b6b7844}
.badge-dca{background:#2dd4bf22;color:#2dd4bf;border:1px solid #2dd4bf44}

/* ── Progress bar ── */
.pbar{height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:6px}
.pbar-fill{height:100%;border-radius:2px;transition:width .4s}

/* ── Table ── */
.tbl{width:100%;border-collapse:collapse}
.tbl th{text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding:0 8px 10px;white-space:nowrap}
.tbl td{padding:10px 8px;border-top:1px solid var(--bl);font-size:13px;vertical-align:middle}
.tbl tr:hover td{background:var(--card2)}
.tbl .sym{font-weight:700;font-size:14px}

/* ── Signal chip ── */
.sig{display:inline-flex;gap:4px;align-items:center;font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px}
.sig-BUY{background:#22c55e18;color:#22c55e}.sig-WATCH{background:#f59e0b18;color:#f59e0b}
.sig-WAIT,.sig-NEUTRAL{background:#6b6b7818;color:#9999a8}.sig-AVOID{background:#ef444418;color:#ef4444}

/* ── RSI bar ── */
.rsi-wrap{width:80px}
.rsi-bar{height:6px;background:var(--border);border-radius:3px;position:relative;overflow:hidden}
.rsi-fill{height:100%;border-radius:3px}

/* ── Sparkline ── */
canvas.spark{width:80px;height:32px;display:block}

/* ── Price ticker ── */
.ticker-wrap{overflow:hidden;background:var(--sb);border-bottom:1px solid var(--border);height:32px;flex-shrink:0}
.ticker-inner{display:flex;align-items:center;height:32px;animation:tick 40s linear infinite;width:max-content}
.ticker-inner:hover{animation-play-state:paused}
.ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 20px;font-size:11px;font-weight:600;white-space:nowrap;border-right:1px solid var(--bl)}
.ticker-sym{color:var(--mid)}.ticker-px{color:var(--text)}.ticker-chg.up{color:var(--green)}.ticker-chg.dn{color:var(--red)}
@keyframes tick{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}

/* ── Buttons ── */
.btn{padding:8px 18px;border:none;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;transition:.15s;letter-spacing:.3px}
.btn-primary{background:var(--teal);color:#000}.btn-primary:hover{filter:brightness(1.1)}
.btn-ghost{background:var(--card);border:1px solid var(--border);color:var(--mid)}.btn-ghost:hover{border-color:var(--mid);color:var(--text)}
.btn-sm{padding:5px 12px;font-size:11px;border-radius:6px}

/* ── Refresh indicator ── */
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Loading ── */
.spin{animation:spin 1s linear infinite;display:inline-block}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Chat ── */
.chat-wrap{display:flex;flex-direction:column;height:calc(100vh - 52px - 32px);overflow:hidden}
.chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.chat-messages::-webkit-scrollbar{width:5px}
.chat-messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.msg-row{display:flex;gap:10px;align-items:flex-end;max-width:85%}
.msg-row.user{align-self:flex-end;flex-direction:row-reverse}
.msg-row.ai{align-self:flex-start}
.msg-avatar{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.msg-avatar.user-av{background:var(--card2);border:1px solid var(--border)}
.msg-avatar.ai-av{background:linear-gradient(135deg,#22c55e,#16a34a)}
.bubble{padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.6;max-width:100%;word-wrap:break-word;white-space:pre-wrap}
.bubble.user{background:var(--teal);color:#000;border-bottom-right-radius:4px}
.bubble.ai{background:var(--card);border:1px solid var(--border);color:var(--text);border-bottom-left-radius:4px}
.bubble.typing{color:var(--muted)}
.chat-bar{padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0;background:var(--sb)}
.chat-input{flex:1;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;resize:none;outline:none;max-height:120px;min-height:42px;transition:border .15s}
.chat-input:focus{border-color:var(--teal)}
.chat-input::placeholder{color:var(--muted)}
.chat-send{width:42px;height:42px;border-radius:10px;background:var(--teal);border:none;cursor:pointer;font-size:18px;flex-shrink:0;transition:.15s;display:flex;align-items:center;justify-content:center}
.chat-send:hover{filter:brightness(1.1)}
.chat-send:disabled{opacity:.4;cursor:not-allowed}
.chat-toolbar{display:flex;gap:6px;padding:6px 16px;background:var(--sb);border-bottom:1px solid var(--border)}
.chip{font-size:11px;padding:4px 10px;border-radius:20px;background:var(--card);border:1px solid var(--border);color:var(--muted);cursor:pointer;transition:.1s;white-space:nowrap}
.chip:hover{border-color:var(--teal);color:var(--teal)}
"""

# ─── Base Layout ──────────────────────────────────────────────────────────────

def _base(page_id: str, title: str, content: str, user: dict,
          ticker_html: str = "", extra_js: str = "") -> str:
    display = user.get("display_name", "User")
    is_admin = user.get("role") == "admin"
    nav = [
        ("stocks",  "📊", "Stocks"),
        ("gold",    "🥇", "Gold"),
        ("crypto",  "₿",  "Crypto"),
        ("dca",     "📈", "DCA"),
        ("signals", "🎯", "Signals"),
        ("news",    "📰", "News"),
        ("paper",   "🧪", "Paper Trade"),
        ("ai",      "🤖", "AI Analysis"),
        ("screener","🔭", "Screener"),
        ("chat",    "💬", "Chat ArtheeNoi"),
    ]
    nav_html = ""
    for nid, icon, label in nav:
        act = "active" if nid == page_id else ""
        nav_html += (f'<a class="sb-link {act}" href="/{nid}">'
                     f'{icon}<span class="tip">{label}</span></a>')

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — ArtheeNoi</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{_CSS}</style>
</head>
<body>
<div class="layout">
  <!-- Sidebar -->
  <nav class="sb">
    <div class="sb-logo">A</div>
    {nav_html}
    <div class="sb-spacer"></div>
    <div class="sb-bot">
      <a class="sb-link" href="/settings">⚙️<span class="tip">Settings</span></a>
      {'<a class="sb-link" href="/admin">👑<span class="tip">Admin</span></a>' if is_admin else ''}
      <a class="sb-link" href="/logout">🚪<span class="tip">Logout</span></a>
    </div>
  </nav>
  <!-- Main -->
  <div class="main">
    <!-- Topbar -->
    <div class="topbar">
      <div>
        <div class="topbar-title">{title}</div>
      </div>
      <div class="topbar-right">
        <span class="live-dot" id="liveDot" title="Live"></span>
        <span class="top-pill" id="mktTime">--:--</span>
        <span class="top-user" onclick="location.href='/settings'">👤 {display}</span>
      </div>
    </div>
    <!-- Ticker -->
    {('<div class="ticker-wrap"><div class="ticker-inner" id="tickerInner">' + ticker_html*2 + '</div></div>') if ticker_html else ''}
    <!-- Content -->
    <div class="content" id="pageContent">
      {content}
    </div>
  </div>
</div>
<script>
// Clock
function updateClock(){{
  const now=new Date();
  document.getElementById('mktTime').textContent=now.toLocaleTimeString('th-TH',{{hour:'2-digit',minute:'2-digit'}});
}}
setInterval(updateClock,1000); updateClock();
{extra_js}
</script>
</body></html>"""

# ─── Live Price API helpers ────────────────────────────────────────────────────

def _fetch_live(symbols: list, period="2d") -> dict:
    try:
        import yfinance as yf
        data = {}
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if not t:
                    continue
                fi = t.fast_info
                hist = t.history(period=period, interval="1d")
                closes = hist["Close"].dropna().tolist()
                price  = fi.last_price or 0
                prev   = fi.previous_close or price
                chg    = (price - prev) / prev * 100 if prev else 0
                data[sym] = {
                    "price": round(price, 2),
                    "chg":   round(chg, 2),
                    "high":  round(fi.year_high or price, 2),
                    "low":   round(fi.year_low or price, 2),
                    "closes": [round(c, 2) for c in closes[-30:]],
                }
            except Exception:
                pass
        return data
    except ImportError:
        return {}

def _calc_rsi(closes: list, n=14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains[-n:]) / n; al = sum(losses[-n:]) / n
    return round(100 - 100 / (1 + ag / al), 1) if al else 100.0

def _ma(closes, n):
    return round(sum(closes[-n:]) / n, 2) if len(closes) >= n else None

def _ticker_html(market_data: dict) -> str:
    order = ["QQQ", "IVV", "DIA", "GC=F", "BTC-USD", "NVDA", "MSFT",
             "GOOGL", "META", "AMZN", "TSLA", "AVGO", "AMD"]
    items = ""
    for sym in order:
        d = market_data.get(sym)
        if not d or not d.get("price"):
            continue
        chg  = d.get("chg", 0)
        cls  = "up" if chg >= 0 else "dn"
        sign = "+" if chg >= 0 else ""
        label = {"GC=F": "GOLD", "BTC-USD": "BTC"}.get(sym, sym)
        items += (f'<div class="ticker-item">'
                  f'<span class="ticker-sym">{label}</span>'
                  f'<span class="ticker-px">${d["price"]:,.2f}</span>'
                  f'<span class="ticker-chg {cls}">{sign}{chg:.2f}%</span>'
                  f'</div>')
    return items

# ─── STOCKS PAGE ──────────────────────────────────────────────────────────────

def _signal_badge(action: str) -> str:
    icons = {"BUY": "▲", "WATCH": "◎", "WAIT": "◌", "NEUTRAL": "—", "AVOID": "▼"}
    return f'<span class="badge badge-{action.lower()}">{icons.get(action,"·")} {action}</span>'

def _rsi_bar(rsi) -> str:
    if rsi is None:
        return '<span style="color:var(--muted)">—</span>'
    w = min(rsi, 100)
    color = "#ef4444" if rsi >= 70 else "#22c55e" if rsi <= 30 else "#f59e0b" if rsi <= 45 else "#3b82f6"
    return (f'<div class="rsi-wrap" title="RSI {rsi}">'
            f'<div style="font-size:11px;color:var(--mid);margin-bottom:2px">{rsi}</div>'
            f'<div class="rsi-bar"><div class="rsi-fill" style="width:{w}%;background:{color}"></div></div>'
            f'</div>')

def stocks_page(user: dict, market_data: dict, macro: dict, thb: float) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])

    # Portfolio summary
    total_val = total_cost = total_pnl = 0
    port_rows = []
    for sym, info in port.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        sh = float(info.get("shares", 0))
        cost = float(info.get("cost", 0))
        val = d["price"] * sh
        ct  = cost * sh
        pnl = val - ct
        pnl_pct = pnl / ct * 100 if ct else 0
        total_val  += val
        total_cost += ct
        total_pnl  += pnl
        port_rows.append({"sym": sym, "price": d["price"], "shares": sh,
                          "cost": cost, "val": val, "pnl": pnl,
                          "pnl_pct": pnl_pct, "pnl_thb": pnl * thb,
                          "chg": d.get("chg", 0), "rsi": d.get("rsi"),
                          "closes": d.get("closes", [])})

    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    pnl_col = "pos" if total_pnl >= 0 else "neg"
    pnl_sign = "+" if total_pnl >= 0 else ""

    # Market mood
    qqq = market_data.get("QQQ", {})
    qqq_chg = qqq.get("chg", 0)
    mood = "🟢 Bullish" if qqq_chg > 0.5 else "🔴 Bearish" if qqq_chg < -0.5 else "⚪ Neutral"
    mood_col = "var(--green)" if qqq_chg > 0.5 else "var(--red)" if qqq_chg < -0.5 else "var(--muted)"

    # Macro strip
    vix  = macro.get("vix", "—")
    dxy  = macro.get("dxy", "—")
    rate = macro.get("fed_rate", "—")
    yc   = macro.get("yield_curve", "—")

    # ETF summary cards
    etf_cards = ""
    for sym, label, color in [("QQQ","NASDAQ","var(--blue)"),("IVV","S&P 500","var(--teal)"),("DIA","DOW","var(--purple)")]:
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        chg = d.get("chg", 0)
        cl  = "pos" if chg >= 0 else "neg"
        sg  = "+" if chg >= 0 else ""
        etf_cards += f"""
        <div class="card-sm" style="border-top:3px solid {color}">
          <div style="font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-bottom:6px">{label}</div>
          <div style="font-size:20px;font-weight:800">${d['price']:,.2f}</div>
          <div class="stat-lbl {cl}" style="margin-top:4px">{sg}{chg:.2f}% today</div>
        </div>"""

    # Portfolio table
    port_table = ""
    for r in sorted(port_rows, key=lambda x: -abs(x["pnl"])):
        pc = "pos" if r["pnl"] >= 0 else "neg"
        ps = "+" if r["pnl"] >= 0 else ""
        cc = "pos" if r["chg"] >= 0 else "neg"
        cs = "+" if r["chg"] >= 0 else ""
        sp_id = f"sp_{r['sym']}"
        port_table += f"""
        <tr>
          <td><span class="sym">{r['sym']}</span></td>
          <td>${r['price']:,.2f}</td>
          <td class="{cc}">{cs}{r['chg']:.2f}%</td>
          <td>{_rsi_bar(r.get('rsi'))}</td>
          <td>{r['shares']}×${r['cost']}</td>
          <td class="{pc}">{ps}${r['pnl']:,.0f} <span style="font-size:10px;color:var(--muted)">({ps}{r['pnl_pct']:.1f}%)</span></td>
          <td class="{pc}" style="font-weight:700">{ps}฿{abs(r['pnl_thb']):,.0f}</td>
          <td><canvas id="{sp_id}" class="spark"></canvas></td>
        </tr>"""

    spark_js = ""
    for r in port_rows:
        if r.get("closes"):
            col = "#22c55e" if (r["closes"][-1] >= r["closes"][0] if len(r["closes"])>1 else True) else "#ef4444"
            spark_js += f"drawSpark('{r['sym']}',{json.dumps(r['closes'])},'{col}');"

    # Watchlist cards
    wl_cards = ""
    for sym in watchlist:
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        closes = d.get("closes", [])
        rsi = _calc_rsi(closes) if closes else d.get("rsi")
        chg = d.get("chg", 0)
        chg_col = "var(--green)" if chg >= 0 else "var(--red)"
        chg_s = "+" if chg >= 0 else ""
        rsi_col = "#ef4444" if (rsi or 50) >= 70 else "#22c55e" if (rsi or 50) <= 30 else "#f59e0b"

        # Entry signal
        action = "BUY" if (rsi and rsi <= 35) else "WATCH" if (rsi and rsi <= 45) else "WAIT" if (rsi and rsi >= 65) else "AVOID" if (rsi and rsi >= 75) else "NEUTRAL"
        rng = d["high"] - d["low"] if d.get("high") and d.get("low") else 1
        pct_range = (d["price"] - d["low"]) / rng * 100 if rng else 50

        wl_cards += f"""
        <div class="card-sm" style="cursor:default">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <div>
              <div style="font-weight:800;font-size:15px">{sym}</div>
              <div style="color:var(--muted);font-size:11px;margin-top:1px">${d['price']:,.2f}</div>
            </div>
            {_signal_badge(action)}
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span style="font-size:12px;color:{chg_col};font-weight:700">{chg_s}{chg:.2f}%</span>
            <span style="font-size:11px;color:var(--muted)">RSI <b style="color:{rsi_col}">{rsi or '—'}</b></span>
          </div>
          <div class="pbar"><div class="pbar-fill" style="width:{pct_range:.0f}%;background:var(--teal)"></div></div>
          <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:10px;color:var(--muted)">
            <span>L ${d['low']:,.0f}</span><span>52W range</span><span>H ${d['high']:,.0f}</span>
          </div>
        </div>"""

    html = f"""
<!-- Summary bar -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm">
    <div class="card-hdr">Portfolio Value</div>
    <div class="stat-val">${total_val:,.0f}</div>
    <div class="stat-lbl">฿{total_val*thb:,.0f}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Total P&L</div>
    <div class="stat-val {pnl_col}">{pnl_sign}${total_pnl:,.0f}</div>
    <div class="stat-lbl {pnl_col}">{pnl_sign}{total_pnl_pct:.1f}% &nbsp; ฿{total_pnl*thb:,.0f}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Market Mood</div>
    <div style="font-size:18px;font-weight:800;color:{mood_col}">{mood}</div>
    <div class="stat-lbl">QQQ {'+' if qqq_chg>=0 else ''}{qqq_chg:.2f}% today</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Macro</div>
    <div style="font-size:12px;line-height:1.8;color:var(--mid)">
      Fed <b style="color:var(--text)">{rate}%</b> &nbsp;·&nbsp; VIX <b style="color:var(--text)">{vix}</b><br>
      DXY <b style="color:var(--text)">{dxy}</b> &nbsp;·&nbsp; YC <b style="color:var(--text)">{yc}</b>
    </div>
  </div>
</div>

<!-- ETF Cards -->
<div class="g3" style="margin-bottom:16px">{etf_cards}</div>

<!-- Portfolio -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">📊 My Portfolio</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr>
        <th>Symbol</th><th>Price</th><th>Today</th><th>RSI</th><th>Position</th><th>P&L (USD)</th><th>P&L (THB)</th><th>30D</th>
      </tr></thead>
      <tbody>{port_table or '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">ยังไม่มี portfolio — ไป Settings เพื่อเพิ่ม</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- Watchlist -->
<div class="card-hdr" style="margin-bottom:8px">👀 Watchlist</div>
<div class="g-auto">
  {wl_cards or '<div style="color:var(--muted)">ยังไม่มี watchlist</div>'}
</div>
"""

    js = f"""
function drawSpark(sym, closes, color) {{
  const c = document.getElementById('sp_' + sym);
  if (!c || !closes || closes.length < 2) return;
  new Chart(c, {{
    type: 'line',
    data: {{ labels: closes.map((_,i)=>i),
             datasets: [{{ data: closes, borderColor: color, borderWidth: 1.5,
               pointRadius: 0, fill: true,
               backgroundColor: ctx2 => {{
                 const g = ctx2.chart.ctx.createLinearGradient(0,0,0,32);
                 g.addColorStop(0, color+'33'); g.addColorStop(1, color+'00'); return g;
               }}
             }}] }},
    options: {{ animation:false, responsive:false, plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},
               scales:{{x:{{display:false}},y:{{display:false}}}} }}
  }});
}}
{spark_js}

// Auto-refresh prices every 90 sec
let _refreshTimer = setInterval(async ()=>{{
  try {{
    const r = await fetch('/api/prices');
    if(r.ok) {{ const d = await r.json(); applyPrices(d); }}
  }} catch(e) {{}}
}}, 90000);

function applyPrices(prices) {{
  // Update ticker
  for (const [sym, d] of Object.entries(prices)) {{
    const els = document.querySelectorAll('[data-sym="'+sym+'"]');
    els.forEach(el => {{
      if (el.dataset.field === 'price') el.textContent = '$' + d.price.toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}});
      if (el.dataset.field === 'chg') {{
        el.textContent = (d.chg >= 0 ? '+' : '') + d.chg.toFixed(2) + '%';
        el.className = d.chg >= 0 ? 'pos' : 'neg';
      }}
    }});
  }}
}}
"""

    return _base("stocks", "Stocks Dashboard", html, user, _ticker_html(market_data), js)

# ─── GOLD PAGE ────────────────────────────────────────────────────────────────

def gold_page(user: dict, market_data: dict) -> str:
    d = market_data.get("GC=F") or market_data.get("GOLD") or {}
    price  = d.get("price", 0)
    chg    = d.get("chg", 0)
    high   = d.get("high", price * 1.15)
    low    = d.get("low",  price * 0.85)
    closes = d.get("closes", [])
    rsi    = _calc_rsi(closes) if len(closes) >= 15 else 50
    ma50   = _ma(closes, 50)
    ma200  = _ma(closes, 200) if len(closes) >= 200 else None
    ma20   = _ma(closes, 20)

    # 52W position
    rng = high - low
    pct_pos = (price - low) / rng * 100 if rng else 50

    # Entry analysis
    if rsi and rsi <= 35:
        entry_signal = "STRONG BUY"
        entry_color  = "#22c55e"
        entry_note   = f"RSI oversold ({rsi}) — โซนซื้อดีมาก ราคาทองถูกเทขาย"
        dca_weight   = "Heavy (30-40%)"
    elif rsi and rsi <= 45:
        entry_signal = "BUY"
        entry_color  = "#4ade80"
        entry_note   = f"RSI low ({rsi}) — จังหวะเข้าซื้อสะสม"
        dca_weight   = "Normal (15-20%)"
    elif rsi and rsi >= 75:
        entry_signal = "AVOID"
        entry_color  = "#ef4444"
        entry_note   = f"RSI overbought ({rsi}) — รอ pullback ก่อน"
        dca_weight   = "Wait"
    elif rsi and rsi >= 65:
        entry_signal = "WAIT"
        entry_color  = "#f59e0b"
        entry_note   = f"RSI {rsi} — ราคาสูงพอควร รอจังหวะ"
        dca_weight   = "Small (5-10%)"
    else:
        entry_signal = "NEUTRAL"
        entry_color  = "#9999a8"
        entry_note   = f"RSI {rsi or '—'} — ไม่มีสัญญาณชัดเจน"
        dca_weight   = "Small (10%)"

    # Support / Resistance levels (simple: round numbers near price)
    r1 = round(price * 1.02 / 50) * 50
    r2 = round(price * 1.05 / 50) * 50
    s1 = round(price * 0.98 / 50) * 50
    s2 = round(price * 0.95 / 50) * 50
    entry_zone_lo = round(s1 * 0.995, 0)
    entry_zone_hi = round(s1 * 1.005, 0)
    tp = round(r2, 0)
    sl = round(s2, 0)

    chg_col = "var(--green)" if chg >= 0 else "var(--red)"
    chg_s   = "+" if chg >= 0 else ""

    html = f"""
<!-- Gold Header -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--gold)">
    <div class="card-hdr">Gold (XAU/USD)</div>
    <div class="stat-val gold-c">${price:,.2f}</div>
    <div class="stat-lbl" style="color:{chg_col}">{chg_s}{chg:.2f}% today</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">52W Range</div>
    <div style="font-size:13px;margin-bottom:8px">
      <span style="color:var(--green)">L ${low:,.0f}</span> &nbsp;—&nbsp;
      <span style="color:var(--red)">H ${high:,.0f}</span>
    </div>
    <div class="pbar"><div class="pbar-fill" style="width:{pct_pos:.0f}%;background:var(--gold)"></div></div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">{pct_pos:.0f}% of 52W range</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">RSI (14)</div>
    <div class="stat-val" style="color:{'#ef4444' if (rsi or 50)>=70 else '#22c55e' if (rsi or 50)<=30 else '#f59e0b'}">{rsi or '—'}</div>
    <div class="stat-lbl">{'Overbought' if (rsi or 50)>=70 else 'Oversold' if (rsi or 50)<=30 else 'Neutral zone'}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Moving Averages</div>
    <div style="font-size:12px;line-height:1.9;color:var(--mid)">
      MA20 <b style="color:{'var(--green)' if ma20 and price>ma20 else 'var(--red)'}">${ma20:,.0f}</b><br>
      MA50 <b style="color:{'var(--green)' if ma50 and price>ma50 else 'var(--red)'}">${ma50:,.0f}</b>
      {f'<br>MA200 <b style="color:{chr(34)}{"var(--green)" if ma200 and price>ma200 else "var(--red)"}{chr(34)}">${ma200:,.0f}</b>' if ma200 else ''}
    </div>
  </div>
</div>

<!-- Entry Signal -->
<div class="g2" style="margin-bottom:16px">
  <div class="card" style="border-left:4px solid {entry_color}">
    <div class="card-hdr">🎯 Entry Signal</div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
      <span style="font-size:20px;font-weight:800;color:{entry_color}">{entry_signal}</span>
      <span style="font-size:13px;color:var(--mid)">{entry_note}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Entry Zone</div>
        <div style="font-weight:700;color:var(--teal)">${entry_zone_lo:,.0f}–{entry_zone_hi:,.0f}</div>
      </div>
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Target (TP)</div>
        <div style="font-weight:700;color:var(--green)">${tp:,.0f}</div>
      </div>
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted);margin-bottom:4px">Stop Loss</div>
        <div style="font-weight:700;color:var(--red)">${sl:,.0f}</div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-hdr">📐 S/R Levels</div>
    <table class="tbl">
      <thead><tr><th>Level</th><th>Price</th><th>Type</th></tr></thead>
      <tbody>
        <tr><td>R2</td><td style="color:var(--red)">${r2:,.0f}</td><td style="color:var(--muted)">Resistance 2</td></tr>
        <tr><td>R1</td><td style="color:var(--red)">${r1:,.0f}</td><td style="color:var(--muted)">Resistance 1</td></tr>
        <tr><td style="font-weight:700">NOW</td><td style="font-weight:700;color:var(--gold)">${price:,.0f}</td><td style="color:var(--muted)">Current</td></tr>
        <tr><td>S1</td><td style="color:var(--green)">${s1:,.0f}</td><td style="color:var(--muted)">Support 1 / Entry</td></tr>
        <tr><td>S2</td><td style="color:var(--green)">${s2:,.0f}</td><td style="color:var(--muted)">Support 2 / SL</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- DCA for Gold -->
<div class="card">
  <div class="card-hdr">🪙 Gold DCA Guide</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px">
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">แนะนำลงทุน</div>
      <div style="font-size:18px;font-weight:800;color:{entry_color};margin-top:4px">{dca_weight}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">ราคาเฉลี่ย DCA ดี</div>
      <div style="font-size:18px;font-weight:800;color:var(--teal);margin-top:4px">${s1:,.0f}–{price:,.0f}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">ทอง 1 บาท ≈</div>
      <div style="font-size:18px;font-weight:800;color:var(--gold);margin-top:4px">฿{price*0.4802*34.5:,.0f}</div>
      <div style="font-size:10px;color:var(--muted);margin-top:2px">อิงราคา XAU/oz</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">Trend vs MA50</div>
      <div style="font-size:18px;font-weight:800;margin-top:4px;color:{'var(--green)' if ma50 and price>ma50 else 'var(--red)'}">{'📈 Above' if ma50 and price>ma50 else '📉 Below'} MA50</div>
    </div>
  </div>
</div>
"""
    return _base("gold", "Gold Analysis", html, user, "", "")

# ─── CRYPTO PAGE ──────────────────────────────────────────────────────────────

def crypto_page(user: dict, market_data: dict) -> str:
    btc = market_data.get("BTC-USD") or {}
    price  = btc.get("price", 0)
    chg    = btc.get("chg", 0)
    high   = btc.get("high", price * 1.4)
    low    = btc.get("low",  price * 0.6)
    closes = btc.get("closes", [])
    rsi    = _calc_rsi(closes) if len(closes) >= 15 else 50
    ma50   = _ma(closes, 50)
    ma20   = _ma(closes, 20)

    rng     = high - low
    pct_pos = (price - low) / rng * 100 if rng else 50
    chg_col = "var(--orange)" if chg >= 0 else "var(--red)"
    chg_s   = "+" if chg >= 0 else ""

    # BTC cycle position (rough halving-based)
    # BTC halving ~every 4 years, last Apr 2024
    days_since_halving = (datetime.now() - datetime(2024, 4, 19)).days
    cycle_pct = min(days_since_halving / (4*365) * 100, 100)
    phase = "Early Bull" if cycle_pct < 25 else "Mid Bull" if cycle_pct < 50 else "Late Bull / Distribution" if cycle_pct < 75 else "Bear"
    phase_col = "#22c55e" if cycle_pct < 50 else "#f59e0b" if cycle_pct < 75 else "#ef4444"

    if rsi and rsi <= 30:
        signal, sig_col, note = "STRONG BUY", "#22c55e", "Panic zone — RSI ต่ำมาก จังหวะสะสมระยะยาว"
    elif rsi and rsi <= 45:
        signal, sig_col, note = "BUY / DCA", "#4ade80", "โซนสะสม BTC ระยะยาวดี"
    elif rsi and rsi >= 75:
        signal, sig_col, note = "TAKE PROFIT", "#ef4444", "Overheated — พิจารณาขายบางส่วน"
    elif rsi and rsi >= 65:
        signal, sig_col, note = "WAIT", "#f59e0b", "ราคาสูง รอ pullback หรือลง DCA เล็กน้อย"
    else:
        signal, sig_col, note = "NEUTRAL", "#9999a8", "ยังไม่มีสัญญาณชัด"

    s1 = round(price * 0.95 / 1000) * 1000
    s2 = round(price * 0.88 / 1000) * 1000
    r1 = round(price * 1.05 / 1000) * 1000
    r2 = round(price * 1.12 / 1000) * 1000

    html = f"""
<!-- BTC Header -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--orange)">
    <div class="card-hdr">Bitcoin (BTC/USD)</div>
    <div class="stat-val" style="color:var(--orange)">${price:,.0f}</div>
    <div class="stat-lbl" style="color:{chg_col}">{chg_s}{chg:.2f}% today</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">52W Range</div>
    <div style="font-size:13px;margin-bottom:8px">
      <span style="color:var(--green)">L ${low:,.0f}</span> &nbsp;—&nbsp;
      <span style="color:var(--red)">H ${high:,.0f}</span>
    </div>
    <div class="pbar"><div class="pbar-fill" style="width:{pct_pos:.0f}%;background:var(--orange)"></div></div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">{pct_pos:.0f}% of 52W range</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">RSI (14)</div>
    <div class="stat-val" style="color:{'#ef4444' if (rsi or 50)>=70 else '#22c55e' if (rsi or 50)<=30 else '#f59e0b'}">{rsi or '—'}</div>
    <div class="stat-lbl">{'Overbought' if (rsi or 50)>=70 else 'Oversold' if (rsi or 50)<=30 else 'Neutral zone'}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Halving Cycle</div>
    <div style="font-weight:800;font-size:16px;color:{phase_col};margin-bottom:4px">{phase}</div>
    <div class="pbar"><div class="pbar-fill" style="width:{cycle_pct:.0f}%;background:{phase_col}"></div></div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">{cycle_pct:.0f}% through 4Y cycle</div>
  </div>
</div>

<!-- Signal + Levels -->
<div class="g2" style="margin-bottom:16px">
  <div class="card" style="border-left:4px solid {sig_col}">
    <div class="card-hdr">🎯 BTC Signal</div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
      <span style="font-size:20px;font-weight:800;color:{sig_col}">{signal}</span>
      <span style="font-size:13px;color:var(--mid)">{note}</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted)">Entry Zone</div>
        <div style="font-weight:700;color:var(--teal);font-size:13px">${s1:,.0f}–{price:,.0f}</div>
      </div>
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted)">Target (TP)</div>
        <div style="font-weight:700;color:var(--green);font-size:13px">${r2:,.0f}</div>
      </div>
      <div class="card-sm" style="text-align:center">
        <div style="font-size:10px;color:var(--muted)">Stop Loss</div>
        <div style="font-weight:700;color:var(--red);font-size:13px">${s2:,.0f}</div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-hdr">📐 Key Levels</div>
    <table class="tbl">
      <thead><tr><th>Level</th><th>Price</th><th>Note</th></tr></thead>
      <tbody>
        <tr><td>R2</td><td style="color:var(--red)">${r2:,.0f}</td><td style="color:var(--muted)">TP / Resistance</td></tr>
        <tr><td>R1</td><td style="color:var(--red)">${r1:,.0f}</td><td style="color:var(--muted)">Minor resistance</td></tr>
        <tr><td style="font-weight:700">NOW</td><td style="font-weight:700;color:var(--orange)">${price:,.0f}</td><td style="color:var(--muted)">Current</td></tr>
        <tr><td>S1</td><td style="color:var(--green)">${s1:,.0f}</td><td style="color:var(--muted)">Support / Entry</td></tr>
        <tr><td>S2</td><td style="color:var(--green)">${s2:,.0f}</td><td style="color:var(--muted)">Strong support / SL</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- MA Analysis -->
<div class="card">
  <div class="card-hdr">📊 Moving Average Signal</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px">
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">Price vs MA20</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:{'var(--green)' if ma20 and price>ma20 else 'var(--red)'}">{'Above ↑' if ma20 and price>ma20 else 'Below ↓'}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:2px">MA20 = ${ma20:,.0f}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">Price vs MA50</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:{'var(--green)' if ma50 and price>ma50 else 'var(--red)'}">{'Above ↑' if ma50 and price>ma50 else 'Below ↓'}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:2px">MA50 = ${ma50:,.0f}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">MA Cross</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:{'var(--green)' if ma20 and ma50 and ma20>ma50 else 'var(--red)'}">{'Golden ✨' if ma20 and ma50 and ma20>ma50 else 'Death ☠'}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:2px">{'Bullish crossover' if ma20 and ma50 and ma20>ma50 else 'Bearish crossover'}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">DCA Recommendation</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:{sig_col}">{'20-30%' if 'BUY' in signal else '5-10%' if signal=='NEUTRAL' else 'Wait'}</div>
    </div>
  </div>
</div>
"""
    return _base("crypto", "Crypto (BTC)", html, user, "", "")

# ─── DCA PAGE ─────────────────────────────────────────────────────────────────

def dca_page(user: dict, market_data: dict) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    all_syms = list(port.keys()) + watchlist

    rows = ""
    for sym in all_syms:
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        price  = d["price"]
        high   = d.get("high", price * 1.3)
        low    = d.get("low",  price * 0.7)
        closes = d.get("closes", [])
        rsi    = _calc_rsi(closes) if len(closes) >= 15 else None

        rng = high - low
        pct = (price - low) / rng * 100 if rng else 50

        # DCA score (0-100): lower RSI + lower 52W position = better
        rsi_score = max(0, 100 - (rsi or 50) * 1.5)
        pos_score = max(0, 100 - pct)
        dca_score = round((rsi_score * 0.6 + pos_score * 0.4))

        if dca_score >= 75:
            weight = "Heavy (25-30%)"; w_col = "#22c55e"
        elif dca_score >= 55:
            weight = "Normal (15-20%)"; w_col = "#4ade80"
        elif dca_score >= 35:
            weight = "Light (5-10%)"; w_col = "#f59e0b"
        else:
            weight = "Wait"; w_col = "#6b6b78"

        next_entry = round(price * 0.97, 2)
        next_entry2 = round(price * 0.94, 2)

        in_port = sym in port
        port_cost = port.get(sym, {}).get("cost", 0) if in_port else None
        vs_cost = ""
        if port_cost:
            diff = (price - port_cost) / port_cost * 100
            ds   = "+" if diff >= 0 else ""
            vc   = "var(--green)" if diff >= 0 else "var(--red)"
            vs_cost = f'<span style="font-size:11px;color:{vc}">{ds}{diff:.1f}% vs cost</span>'

        rows += f"""
        <tr>
          <td>
            <div style="font-weight:800">{sym}</div>
            {vs_cost}
          </td>
          <td>${price:,.2f}</td>
          <td>{_rsi_bar(rsi)}</td>
          <td>
            <div class="pbar" style="width:100px">
              <div class="pbar-fill" style="width:{pct:.0f}%;background:{'#22c55e' if pct<30 else '#f59e0b' if pct<60 else '#ef4444'}"></div>
            </div>
            <div style="font-size:10px;color:var(--muted);margin-top:2px">{pct:.0f}% of 52W</div>
          </td>
          <td>
            <div style="font-size:28px;font-weight:900;color:{w_col}">{dca_score}</div>
          </td>
          <td style="color:{w_col};font-weight:700">{weight}</td>
          <td>
            <div style="font-size:12px">Zone 1: <b style="color:var(--teal)">${next_entry:,.2f}</b></div>
            <div style="font-size:12px">Zone 2: <b style="color:var(--blue)">${next_entry2:,.2f}</b></div>
          </td>
        </tr>"""

    html = f"""
<div class="card" style="margin-bottom:16px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <div>
      <div class="card-hdr" style="margin-bottom:2px">📈 DCA Score & Entry Zones</div>
      <div style="font-size:12px;color:var(--muted)">Score 0-100 — ยิ่งสูง ยิ่งเหมาะสะสม | คำนวณจาก RSI + 52W position</div>
    </div>
  </div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr>
        <th>Symbol</th><th>ราคาปัจจุบัน</th><th>RSI</th><th>52W Position</th>
        <th>DCA Score</th><th>แนะนำลงทุน</th><th>Entry Zones</th>
      </tr></thead>
      <tbody>{rows or '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px">ไม่มีข้อมูล</td></tr>'}</tbody>
    </table>
  </div>
</div>

<div class="g2">
  <div class="card">
    <div class="card-hdr">💡 DCA หลักการ</div>
    <div style="font-size:13px;line-height:1.9;color:var(--mid)">
      <b style="color:var(--text)">Score ≥ 75</b> — เหมาะซื้อหนัก (RSI oversold + ใกล้ 52W Low)<br>
      <b style="color:var(--text)">Score 55-74</b> — ซื้อปกติทุกเดือน<br>
      <b style="color:var(--text)">Score 35-54</b> — ซื้อเบาๆ เล็กน้อย<br>
      <b style="color:var(--text)">Score &lt; 35</b> — รอ pullback ก่อน<br><br>
      <span style="color:var(--muted)">Zone 1 = -3% จากราคาปัจจุบัน<br>Zone 2 = -6% (สำหรับ limit order)</span>
    </div>
  </div>
  <div class="card">
    <div class="card-hdr">📅 DCA Strategy</div>
    <div style="font-size:13px;line-height:1.9;color:var(--mid)">
      <b style="color:var(--text)">Monthly DCA</b> — ซื้อวันที่ 1-5 ทุกเดือน ไม่ต้องดูราคา<br>
      <b style="color:var(--text)">Signal DCA</b> — รอ Score ≥ 60 แล้วซื้อเพิ่ม<br>
      <b style="color:var(--text)">Crash DCA</b> — ถ้าหุ้นลง &gt;20% ใส่ Extra 2x<br><br>
      <b style="color:var(--text)">กระจาย:</b> ไม่เกิน 30% ต่อตัว<br>
      <b style="color:var(--text)">เงินสำรอง:</b> เก็บ Cash ≥ 20% เสมอ
    </div>
  </div>
</div>
"""
    return _base("dca", "DCA System", html, user, "", "")

# ─── NEWS PAGE ────────────────────────────────────────────────────────────────

def _fetch_news(marketaux_key: str = None) -> list:
    news = []
    # Yahoo RSS feeds
    topics = [("^GSPC", "S&P 500"), ("GC=F", "Gold"), ("BTC-USD", "Bitcoin")]
    headers = {"User-Agent": "Mozilla/5.0"}
    import xml.etree.ElementTree as ET
    for sym, label in topics:
        try:
            r = requests.get(
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US",
                headers=headers, timeout=6, verify=False
            )
            root = ET.fromstring(r.text)
            for item in root.findall(".//item")[:3]:
                title = (item.findtext("title") or "").strip()
                link  = (item.findtext("link") or "").strip()
                pub   = (item.findtext("pubDate") or "")[:16]
                if title:
                    news.append({"title": title, "link": link, "date": pub,
                                 "source": label, "sentiment": _news_sentiment(title)})
        except Exception:
            pass
    # MarketAux (if key)
    if marketaux_key and marketaux_key != "ใส่_key":
        try:
            r = requests.get(
                f"https://api.marketaux.com/v1/news/all?symbols=AAPL,NVDA,MSFT&filter_entities=true&language=en&api_token={marketaux_key}",
                timeout=8, verify=False
            )
            for a in r.json().get("data", [])[:5]:
                sent = (a.get("entities") or [{}])[0].get("sentiment_score", 0) or 0
                news.append({"title": a["title"], "link": a["url"],
                             "date": a.get("published_at", "")[:16],
                             "source": "MarketAux", "sentiment": sent})
        except Exception:
            pass
    return news[:15]

def _news_sentiment(title: str) -> float:
    pos = ["surge", "rally", "gain", "rise", "bull", "record", "strong", "beat", "growth", "profit"]
    neg = ["fall", "drop", "crash", "loss", "bear", "weak", "miss", "debt", "risk", "cut"]
    t = title.lower()
    score = sum(1 for w in pos if w in t) - sum(1 for w in neg if w in t)
    return max(-1, min(1, score * 0.3))

def _risk_score(macro: dict, news: list) -> int:
    score = 50
    vix = macro.get("vix", 20) or 20
    if vix > 30: score += 20
    elif vix > 20: score += 10
    elif vix < 15: score -= 10
    yc = macro.get("yield_curve", 0) or 0
    if yc < 0: score += 15
    avg_sent = sum(n.get("sentiment", 0) for n in news) / len(news) if news else 0
    score -= int(avg_sent * 10)
    return max(0, min(100, score))

def news_page(user: dict, macro: dict, marketaux_key: str = "") -> str:
    news = _fetch_news(marketaux_key)
    risk = _risk_score(macro, news)
    risk_col = "#ef4444" if risk >= 70 else "#f59e0b" if risk >= 45 else "#22c55e"
    risk_label = "High Risk ⚠️" if risk >= 70 else "Medium Risk 🟡" if risk >= 45 else "Low Risk 🟢"

    news_html = ""
    for n in news:
        sent = n.get("sentiment", 0)
        s_col = "#22c55e" if sent > 0.1 else "#ef4444" if sent < -0.1 else "#9999a8"
        s_lbl = "Positive" if sent > 0.1 else "Negative" if sent < -0.1 else "Neutral"
        news_html += f"""
        <div class="card-sm" style="border-left:3px solid {s_col};margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
            <a href="{n['link']}" target="_blank" style="font-size:13px;font-weight:600;color:var(--text);text-decoration:none;line-height:1.4;flex:1">{n['title']}</a>
            <span style="font-size:10px;font-weight:700;color:{s_col};white-space:nowrap">{s_lbl}</span>
          </div>
          <div style="margin-top:5px;font-size:10px;color:var(--muted)">{n['source']} · {n['date']}</div>
        </div>"""

    vix  = macro.get("vix", "—")
    yc   = macro.get("yield_curve", "—")
    rate = macro.get("fed_rate", "—")
    dxy  = macro.get("dxy", "—")

    html = f"""
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid {risk_col};grid-column:span 1">
    <div class="card-hdr">Daily Risk Score</div>
    <div style="font-size:36px;font-weight:900;color:{risk_col}">{risk}</div>
    <div style="font-size:12px;font-weight:700;color:{risk_col};margin-top:4px">{risk_label}</div>
    <div class="pbar" style="margin-top:10px"><div class="pbar-fill" style="width:{risk}%;background:{risk_col}"></div></div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">VIX (Fear Index)</div>
    <div class="stat-val" style="color:{'#ef4444' if float(vix or 0)>25 else '#22c55e'}">{vix}</div>
    <div class="stat-lbl">{'High fear' if float(vix or 0)>25 else 'Low fear' if float(vix or 0)<15 else 'Moderate'}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Fed Rate</div>
    <div class="stat-val blue-c">{rate}%</div>
    <div class="stat-lbl">Yield Curve: {yc}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">DXY (USD Index)</div>
    <div class="stat-val" style="color:var(--purple)">{dxy}</div>
    <div class="stat-lbl">Dollar strength</div>
  </div>
</div>

<div class="g2">
  <div class="card">
    <div class="card-hdr" style="margin-bottom:12px">📰 Market News & Sentiment</div>
    {news_html or '<div style="color:var(--muted)">ดึงข่าวไม่ได้ (เช็ค internet)</div>'}
  </div>
  <div class="card">
    <div class="card-hdr">📊 Risk Factors</div>
    <div style="font-size:13px;line-height:2.1;color:var(--mid)">
      <div style="display:flex;justify-content:space-between">
        <span>VIX Level</span>
        <b style="color:{'#ef4444' if float(vix or 0)>25 else '#22c55e'}">{'+20 risk' if float(vix or 0)>30 else '+10 risk' if float(vix or 0)>20 else '−10 risk' if float(vix or 0)<15 else 'neutral'}</b>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span>Yield Curve</span>
        <b style="color:{'#ef4444' if float(yc or 0)<0 else '#22c55e'}">{'Inverted ⚠️ +15' if float(yc or 0)<0 else 'Normal −5'}</b>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span>News Sentiment</span>
        <b style="color:var(--mid)">Calculated from {len(news)} articles</b>
      </div>
    </div>
    <div style="margin-top:16px;padding:12px;background:var(--card2);border-radius:8px;font-size:12px;color:var(--mid);line-height:1.7">
      <b style="color:var(--text)">Risk Score guide:</b><br>
      🟢 0-44 = ปลอดภัย ตลาดสงบ<br>
      🟡 45-69 = ระวังปานกลาง<br>
      🔴 70+ = Risk สูง ลด position
    </div>
  </div>
</div>
"""
    return _base("news", "News & Risk", html, user, "", "")

# ─── Loading Page ─────────────────────────────────────────────────────────────

# ─── SIGNALS PAGE (Day / Weekly / Monthly) ───────────────────────────────────

def _compute_signals(sym: str, d: dict) -> dict:
    """Compute day/weekly/monthly trade signals from market data."""
    closes  = d.get("closes", [])
    price   = d.get("price", 0)
    chg_d   = d.get("change_pct") or d.get("chg") or 0

    rsi      = _calc_rsi(closes) if len(closes) >= 15 else 50
    ma20     = _ma(closes, 20)
    ma50     = _ma(closes, 50)
    ma200    = _ma(closes, 200) if len(closes) >= 200 else None

    # Day signal (intraday momentum)
    if abs(chg_d) < 0.3:
        day_sig = "NEUTRAL"; day_col = "#9999a8"
    elif chg_d > 1.5:
        day_sig = "DAY BUY" if (rsi or 50) < 65 else "OVERBOUGHT"; day_col = "#22c55e"
    elif chg_d > 0.3:
        day_sig = "BULLISH"; day_col = "#4ade80"
    elif chg_d < -1.5:
        day_sig = "DAY SELL" if (rsi or 50) > 35 else "OVERSOLD"; day_col = "#ef4444"
    else:
        day_sig = "BEARISH"; day_col = "#f87171"

    # Weekly signal (RSI + MA20)
    if rsi and ma20:
        if rsi < 35 and price < ma20:
            wk_sig = "STRONG BUY"; wk_col = "#22c55e"
        elif rsi < 45 and price > ma20:
            wk_sig = "BUY"; wk_col = "#4ade80"
        elif rsi > 70 and price > ma20:
            wk_sig = "SELL"; wk_col = "#ef4444"
        elif rsi > 60:
            wk_sig = "WATCH"; wk_col = "#f59e0b"
        else:
            wk_sig = "HOLD"; wk_col = "#9999a8"
    else:
        wk_sig = "—"; wk_col = "#5a5a68"

    # Monthly signal (MA50 + MA200 trend)
    if ma50 and price > ma50:
        if ma200 and ma50 > ma200:
            mo_sig = "UPTREND ↑"; mo_col = "#22c55e"
        elif ma200 and ma50 < ma200:
            mo_sig = "RECOVERING"; mo_col = "#f59e0b"
        else:
            mo_sig = "ABOVE MA50"; mo_col = "#4ade80"
    elif ma50 and price < ma50:
        if ma200 and ma50 < ma200:
            mo_sig = "DOWNTREND ↓"; mo_col = "#ef4444"
        else:
            mo_sig = "BELOW MA50"; mo_col = "#f87171"
    else:
        mo_sig = "—"; mo_col = "#5a5a68"

    # Risk/Reward
    support  = round(price * 0.96, 2)
    resist   = round(price * 1.05, 2) if ma20 and price > ma20 else round(price * 1.03, 2)
    rr       = round((resist - price) / (price - support), 1) if price > support else 0

    return {
        "day_sig": day_sig, "day_col": day_col,
        "wk_sig":  wk_sig,  "wk_col":  wk_col,
        "mo_sig":  mo_sig,  "mo_col":  mo_col,
        "rsi": rsi, "rr": rr,
        "support": support, "resist": resist,
        "ma20": ma20, "ma50": ma50,
    }

def signals_page(user: dict, market_data: dict, thb: float) -> str:
    port     = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    all_syms = list(port.keys()) + [s for s in watchlist if s not in port]

    rows = ""
    for sym in all_syms:
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        price = d["price"]
        chg   = d.get("change_pct") or d.get("chg") or 0
        sig   = _compute_signals(sym, d)
        in_port = sym in port

        rows += f"""
        <tr>
          <td>
            <div style="font-weight:800;font-size:14px">{sym}</div>
            {'<div style="font-size:10px;color:var(--teal)">Portfolio</div>' if in_port else '<div style="font-size:10px;color:var(--muted)">Watchlist</div>'}
          </td>
          <td>${price:,.2f} <span style="font-size:11px;color:{'var(--green)' if chg>=0 else 'var(--red)'}">{'+' if chg>=0 else ''}{chg:.2f}%</span></td>
          <td>{_rsi_bar(sig['rsi'])}</td>
          <td><span style="font-weight:700;color:{sig['day_col']}">{sig['day_sig']}</span></td>
          <td><span style="font-weight:700;color:{sig['wk_col']}">{sig['wk_sig']}</span></td>
          <td><span style="font-weight:700;color:{sig['mo_col']}">{sig['mo_sig']}</span></td>
          <td>
            <div style="font-size:11px">
              <span style="color:var(--green)">S ${sig['support']:,.2f}</span> /
              <span style="color:var(--red)">R ${sig['resist']:,.2f}</span>
            </div>
            <div style="font-size:10px;color:var(--muted)">R:R = {sig['rr']}x</div>
          </td>
          <td style="font-size:11px;color:var(--muted)">
            {'MA20 $'+str(f'{sig["ma20"]:,.0f}') if sig["ma20"] else '—'}<br>
            {'MA50 $'+str(f'{sig["ma50"]:,.0f}') if sig["ma50"] else '—'}
          </td>
        </tr>"""

    html = f"""
<div class="card" style="margin-bottom:16px">
  <div style="margin-bottom:14px">
    <div class="card-hdr" style="margin-bottom:2px">🎯 Trade Signals — Day / Weekly / Monthly</div>
    <div style="font-size:12px;color:var(--muted)">
      Day = momentum วันนี้ &nbsp;·&nbsp; Weekly = RSI+MA20 &nbsp;·&nbsp; Monthly = trend MA50/MA200
    </div>
  </div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr>
        <th>Symbol</th><th>ราคา</th><th>RSI</th>
        <th>Day Signal</th><th>Weekly Signal</th><th>Monthly Signal</th>
        <th>S/R Level</th><th>MAs</th>
      </tr></thead>
      <tbody>{rows or '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">ไม่มีข้อมูล</td></tr>'}</tbody>
    </table>
  </div>
</div>

<div class="g3">
  <div class="card-sm">
    <div class="card-hdr">📅 Day Trade</div>
    <div style="font-size:12px;line-height:1.9;color:var(--mid)">
      <b style="color:var(--text)">DAY BUY:</b> เปลี่ยน &gt;+1.5%, RSI &lt;65<br>
      <b style="color:var(--text)">DAY SELL:</b> เปลี่ยน &lt;−1.5%, RSI &gt;35<br>
      <b style="color:var(--text)">BULLISH/BEARISH:</b> momentum ปานกลาง<br>
      <span style="color:var(--muted)">ใช้ร่วมกับ Volume และ News</span>
    </div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">📆 Weekly Trade</div>
    <div style="font-size:12px;line-height:1.9;color:var(--mid)">
      <b style="color:var(--text)">STRONG BUY:</b> RSI &lt;35 + ต่ำกว่า MA20<br>
      <b style="color:var(--text)">BUY:</b> RSI &lt;45 + เหนือ MA20<br>
      <b style="color:var(--text)">SELL:</b> RSI &gt;70 + เหนือ MA20<br>
      <span style="color:var(--muted)">Time frame 5-15 วัน</span>
    </div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">📅 Monthly/Swing</div>
    <div style="font-size:12px;line-height:1.9;color:var(--mid)">
      <b style="color:var(--text)">UPTREND:</b> ราคา &gt; MA50 และ MA50 &gt; MA200<br>
      <b style="color:var(--text)">DOWNTREND:</b> ราคา &lt; MA50 และ MA50 &lt; MA200<br>
      <b style="color:var(--text)">RECOVERING:</b> เริ่มฟื้นตัว<br>
      <span style="color:var(--muted)">Time frame 1-3 เดือน</span>
    </div>
  </div>
</div>
"""
    return _base("signals", "Trade Signals", html, user, "", "")

# ─── PAPER TRADING PAGE ───────────────────────────────────────────────────────

def paper_page(user: dict, market_data: dict, thb: float,
               paper_trades: list = None) -> str:
    trades   = paper_trades or []
    cash_start = user.get("paper_cash_start", 10000)
    cash       = user.get("paper_cash", cash_start)

    # Calculate open positions P&L
    open_positions = [t for t in trades if t.get("status") == "open"]
    closed_trades  = [t for t in trades if t.get("status") == "closed"]

    total_unrealized = 0.0
    pos_rows = ""
    for t in open_positions:
        sym      = t["sym"]
        d        = market_data.get(sym, {})
        cur      = d.get("price", t["entry"])
        qty      = t["qty"]
        entry    = t["entry"]
        side     = t.get("side", "LONG")
        if side == "LONG":
            unreal = (cur - entry) * qty
        else:
            unreal = (entry - cur) * qty
        pct    = unreal / (entry * qty) * 100 if entry else 0
        total_unrealized += unreal
        pc = "pos" if unreal >= 0 else "neg"
        ps = "+" if unreal >= 0 else ""
        pos_rows += f"""
        <tr>
          <td><b>{sym}</b> <span style="font-size:10px;color:{'var(--teal)' if side=='LONG' else 'var(--orange)'}">{'▲ LONG' if side=='LONG' else '▼ SHORT'}</span></td>
          <td>${entry:,.2f}</td>
          <td>${cur:,.2f}</td>
          <td>{qty}</td>
          <td class="{pc}">{ps}${unreal:,.2f} ({ps}{pct:.1f}%)</td>
          <td>
            <form method="POST" action="/paper/close" style="display:inline">
              <input type="hidden" name="trade_id" value="{t['id']}">
              <input type="hidden" name="close_price" value="{cur}">
              <button class="btn btn-ghost btn-sm">Close</button>
            </form>
          </td>
        </tr>"""

    # Closed trade history
    total_realized = sum(t.get("pnl", 0) for t in closed_trades)
    hist_rows = ""
    for t in sorted(closed_trades, key=lambda x: x.get("close_date",""), reverse=True)[:10]:
        pnl = t.get("pnl", 0)
        pc  = "pos" if pnl >= 0 else "neg"
        ps  = "+" if pnl >= 0 else ""
        hist_rows += f"""
        <tr>
          <td>{t['sym']}</td>
          <td style="color:{'var(--teal)' if t.get('side')=='LONG' else 'var(--orange)'}">{'LONG' if t.get('side')=='LONG' else 'SHORT'}</td>
          <td>${t['entry']:,.2f} → ${t.get('close_price',0):,.2f}</td>
          <td>{t['qty']}</td>
          <td class="{pc}">{ps}${pnl:,.2f}</td>
          <td style="font-size:11px;color:var(--muted)">{t.get('close_date','')[:10]}</td>
        </tr>"""

    # Stock options for trade form
    port = user.get("portfolio", {})
    wl   = user.get("watchlist", [])
    all_syms = sorted(set(list(port.keys()) + wl + ["QQQ","IVV","DIA","GC=F","BTC-USD"]))
    sym_opts  = "".join(f'<option value="{s}">${market_data.get(s,{}).get("price",0):,.2f} — {s}</option>' for s in all_syms if market_data.get(s,{}).get("price"))

    total_equity = cash + total_unrealized
    roi = (total_equity - cash_start) / cash_start * 100 if cash_start else 0
    roi_col = "var(--green)" if roi >= 0 else "var(--red)"
    roi_s   = "+" if roi >= 0 else ""

    html = f"""
<!-- Summary -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--teal)">
    <div class="card-hdr">Cash Available</div>
    <div class="stat-val teal-c">${cash:,.2f}</div>
    <div class="stat-lbl">Starting: ${cash_start:,.2f}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Unrealized P&L</div>
    <div class="stat-val {'pos' if total_unrealized>=0 else 'neg'}">{'+' if total_unrealized>=0 else ''}${total_unrealized:,.2f}</div>
    <div class="stat-lbl">{len(open_positions)} open positions</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Realized P&L</div>
    <div class="stat-val {'pos' if total_realized>=0 else 'neg'}">{'+' if total_realized>=0 else ''}${total_realized:,.2f}</div>
    <div class="stat-lbl">{len(closed_trades)} trades closed</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Total Return</div>
    <div class="stat-val" style="color:{roi_col}">{roi_s}{roi:.1f}%</div>
    <div class="stat-lbl">Equity: ${total_equity:,.2f}</div>
  </div>
</div>

<!-- Open Positions -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">📌 Open Positions</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>Entry</th><th>Current</th><th>Qty</th><th>Unrealized P&L</th><th></th></tr></thead>
      <tbody>{pos_rows or '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">ยังไม่มี position เปิดอยู่</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- New Trade Form -->
<div class="g2" style="margin-bottom:16px">
  <div class="card">
    <div class="card-hdr">➕ เปิด Trade ใหม่</div>
    <form method="POST" action="/paper/open">
      <div style="display:grid;gap:10px">
        <div>
          <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">Symbol</label>
          <select name="sym" style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
            {sym_opts}
          </select>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">Side</label>
            <select name="side" style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
              <option value="LONG">▲ LONG (ซื้อ)</option>
              <option value="SHORT">▼ SHORT (ชอร์ต)</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">จำนวนหุ้น</label>
            <input type="number" name="qty" value="1" min="0.01" step="0.01"
              style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
          </div>
        </div>
        <div>
          <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">ราคาเข้า (0 = ราคาตลาด)</label>
          <input type="number" name="entry" value="0" step="0.01" min="0"
            style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
        </div>
        <div style="display:flex;gap:8px">
          <div style="flex:1">
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">Stop Loss ($)</label>
            <input type="number" name="sl" value="0" step="0.01"
              style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
          </div>
          <div style="flex:1">
            <label style="font-size:11px;color:var(--muted);display:block;margin-bottom:4px">Target (TP $)</label>
            <input type="number" name="tp" value="0" step="0.01"
              style="width:100%;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px;font-size:13px">
          </div>
        </div>
        <button type="submit" class="btn btn-primary">🚀 เปิด Trade</button>
      </div>
    </form>
  </div>

  <!-- Trade History -->
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div class="card-hdr" style="margin-bottom:0">📜 ประวัติ (10 ล่าสุด)</div>
      <form method="POST" action="/paper/reset" onsubmit="return confirm('Reset paper trading ทั้งหมด?')">
        <button class="btn btn-ghost btn-sm">🔄 Reset</button>
      </form>
    </div>
    <div style="overflow-x:auto">
      <table class="tbl">
        <thead><tr><th>Sym</th><th>Side</th><th>Entry→Close</th><th>Qty</th><th>P&L</th><th>Date</th></tr></thead>
        <tbody>{hist_rows or '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">ยังไม่มีประวัติ</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>
"""
    return _base("paper", "Paper Trading", html, user, "", "")

# ─── AI ANALYSIS PAGE ─────────────────────────────────────────────────────────

def _ai_analyze(market_data: dict, user: dict, openrouter_key: str = "") -> str:
    """Call OpenRouter → claude-haiku-4-5 for market analysis."""
    if not openrouter_key:
        return ""

    port = user.get("portfolio", {})
    lines = []
    for sym, info in port.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        closes  = d.get("closes", [])
        rsi     = _calc_rsi(closes) if len(closes) >= 15 else None
        chg     = d.get("change_pct") or d.get("chg") or 0
        cost    = info.get("cost", 0)
        shares  = info.get("shares", 0)
        pnl_pct = (d["price"] - cost) / cost * 100 if cost else 0
        lines.append(f"{sym}: price=${d['price']:.2f}, RSI={rsi}, change_today={chg:+.2f}%, P&L={pnl_pct:+.1f}%")

    qqq = market_data.get("QQQ", {})
    gold = market_data.get("GC=F", {})
    btc  = market_data.get("BTC-USD", {})
    ctx  = "\n".join(lines)
    prompt = f"""You are ArtheeNoi, a Thai-language AI stock analyst. Today is {datetime.now().strftime('%Y-%m-%d')}.

Market snapshot:
- QQQ: ${qqq.get('price',0):,.2f} ({qqq.get('chg',0):+.2f}% today)
- Gold: ${gold.get('price',0):,.2f} ({gold.get('chg',0):+.2f}%)
- BTC: ${btc.get('price',0):,.0f} ({btc.get('chg',0):+.2f}%)

User portfolio (Thai investor, ~20,000 THB capital, medium risk):
{ctx}

Write a concise Thai-language daily analysis (4-6 bullet points) covering:
1. Overall market mood today
2. Portfolio highlights — which stocks look good/risky
3. 1-2 specific action items (buy/hold/reduce)
4. One risk to watch this week

Format: use bullet points with emoji. Keep it practical and concise for a retail Thai investor. Response in Thai."""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {openrouter_key}",
                     "Content-Type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001",
                  "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30, verify=False
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning(f"[AI] OpenRouter error: {e}")
        return ""

def ai_page(user: dict, market_data: dict, macro: dict, thb: float,
            openrouter_key: str = "", cached_analysis: str = "") -> str:

    port = user.get("portfolio", {})
    total_val = total_cost = total_pnl = 0
    sym_summary = []
    for sym, info in port.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        sh = float(info.get("shares", 0))
        c  = float(info.get("cost", 0))
        v  = d["price"] * sh
        ct = c * sh
        total_val  += v
        total_cost += ct
        total_pnl  += v - ct
        closes = d.get("closes", [])
        rsi    = _calc_rsi(closes) if len(closes) >= 15 else None
        sym_summary.append({
            "sym": sym, "price": d["price"],
            "chg": d.get("change_pct") or d.get("chg") or 0,
            "rsi": rsi, "pnl_pct": (d["price"]-c)/c*100 if c else 0,
        })

    pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    pnl_col = "var(--green)" if total_pnl >= 0 else "var(--red)"

    # Sort by signal priority
    sym_summary.sort(key=lambda x: x.get("rsi") or 50)

    sym_rows = ""
    for s in sym_summary:
        rsi = s.get("rsi")
        if rsi and rsi <= 35:
            rec = "🟢 BUY เพิ่ม"; rc = "#22c55e"
        elif rsi and rsi <= 45:
            rec = "🟡 HOLD / DCA"; rc = "#f59e0b"
        elif rsi and rsi >= 70:
            rec = "🔴 ลด Position"; rc = "#ef4444"
        elif s["pnl_pct"] > 30:
            rec = "🟡 Take Profit?"; rc = "#f59e0b"
        else:
            rec = "⚪ HOLD"; rc = "#9999a8"
        sym_rows += f"""
        <tr>
          <td><b>{s['sym']}</b></td>
          <td>${s['price']:,.2f} <span style="color:{'var(--green)' if s['chg']>=0 else 'var(--red)'}">({'+' if s['chg']>=0 else ''}{s['chg']:.2f}%)</span></td>
          <td>{_rsi_bar(rsi)}</td>
          <td style="color:{'var(--green)' if s['pnl_pct']>=0 else 'var(--red)'};">{'+' if s['pnl_pct']>=0 else ''}{s['pnl_pct']:.1f}%</td>
          <td style="font-weight:700;color:{rc}">{rec}</td>
        </tr>"""

    # AI analysis section
    ai_html = ""
    if cached_analysis:
        lines = cached_analysis.strip().split("\n")
        formatted = "".join(f'<div style="padding:6px 0;border-bottom:1px solid var(--bl);font-size:13px;line-height:1.7;color:var(--mid)">{l}</div>' for l in lines if l.strip())
        ai_html = f"""
        <div class="card" style="margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
            <div class="card-hdr" style="margin-bottom:0">🤖 ArtheeNoi AI Analysis</div>
            <form method="POST" action="/ai/analyze">
              <button class="btn btn-ghost btn-sm">🔄 Refresh Analysis</button>
            </form>
          </div>
          <div style="background:var(--card2);border-radius:8px;padding:14px">{formatted}</div>
          <div style="font-size:10px;color:var(--muted);margin-top:8px">Powered by Claude Haiku · อัปเดตเมื่อกดปุ่ม Refresh</div>
        </div>"""
    elif openrouter_key:
        ai_html = f"""
        <div class="card" style="margin-bottom:16px;text-align:center">
          <div class="card-hdr">🤖 ArtheeNoi AI Analysis</div>
          <div style="color:var(--muted);font-size:13px;margin:16px 0">กดปุ่มด้านล่างเพื่อให้ AI วิเคราะห์ portfolio ของคุณ</div>
          <form method="POST" action="/ai/analyze">
            <button class="btn btn-primary">🚀 วิเคราะห์ AI ทันที</button>
          </form>
          <div style="font-size:11px;color:var(--muted);margin-top:8px">ใช้ Claude Haiku ผ่าน OpenRouter · ใช้เวลา ~5-10 วินาที</div>
        </div>"""
    else:
        ai_html = f"""
        <div class="card" style="margin-bottom:16px">
          <div class="card-hdr">🤖 ArtheeNoi AI Analysis</div>
          <div style="background:var(--card2);border-radius:8px;padding:14px;color:var(--muted);font-size:13px">
            ⚠️ ยังไม่ได้ตั้งค่า OPENROUTER_API_KEY<br>
            ไป Render Dashboard → Environment → เพิ่ม <code style="color:var(--teal)">OPENROUTER_API_KEY</code> แล้ว Redeploy
          </div>
        </div>"""

    html = f"""
<!-- Portfolio Overview -->
<div class="g3" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--teal)">
    <div class="card-hdr">Portfolio Value</div>
    <div class="stat-val teal-c">${total_val:,.0f}</div>
    <div class="stat-lbl">฿{total_val*thb:,.0f}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Total P&L</div>
    <div class="stat-val" style="color:{pnl_col}">{'+' if total_pnl>=0 else ''}${total_pnl:,.0f}</div>
    <div class="stat-lbl" style="color:{pnl_col}">{'+' if pnl_pct>=0 else ''}{pnl_pct:.1f}%</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Positions</div>
    <div class="stat-val">{len(port)}</div>
    <div class="stat-lbl">หุ้นที่ถืออยู่</div>
  </div>
</div>

{ai_html}

<!-- Recommendation Table -->
<div class="card">
  <div class="card-hdr">📋 AI Recommendations per Stock</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>ราคา</th><th>RSI</th><th>P&L</th><th>AI แนะนำ</th></tr></thead>
      <tbody>{sym_rows or '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px">ยังไม่มี portfolio</td></tr>'}</tbody>
    </table>
  </div>
  <div style="margin-top:12px;font-size:11px;color:var(--muted)">
    * คำแนะนำจาก rule-based RSI + P&L analysis ไม่ใช่คำแนะนำทางการเงิน
  </div>
</div>
"""
    return _base("ai", "AI Analysis", html, user, "", "")

# ─── CHAT PAGE ───────────────────────────────────────────────────────────────

def _artheenoi_system_prompt(user: dict, market_data: dict, thb: float) -> str:
    port  = user.get("portfolio", {})
    lines = []
    for sym, info in port.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        cost = float(info.get("cost", 0))
        sh   = float(info.get("shares", 0))
        pnl  = (d["price"] - cost) / cost * 100 if cost else 0
        closes = d.get("closes", [])
        rsi    = _calc_rsi(closes) if len(closes) >= 15 else None
        lines.append(f"  {sym}: price=${d['price']:,.2f}, RSI={rsi}, P&L={pnl:+.1f}%, shares={sh}@${cost}")

    qqq  = market_data.get("QQQ", {})
    gold = market_data.get("GC=F", {})
    btc  = market_data.get("BTC-USD", {})
    port_block = "\n".join(lines) or "  (ยังไม่มี portfolio)"

    return f"""คุณคือ ArtheeNoi — AI ผู้ช่วยด้านการเงินและหุ้นส่วนตัว พัฒนาโดย Olarn
ตอบภาษาไทยเสมอ สั้น กระชับ ตรงประเด็น ใช้ตัวเลขจริงจากข้อมูลที่มี

ข้อมูลตลาดปัจจุบัน ({datetime.now().strftime('%Y-%m-%d %H:%M')}):
  QQQ: ${qqq.get('price',0):,.2f} ({qqq.get('chg',0):+.2f}% today)
  Gold: ${gold.get('price',0):,.2f} ({gold.get('chg',0):+.2f}%)
  BTC: ${btc.get('price',0):,.0f} ({btc.get('chg',0):+.2f}%)
  USD/THB: {thb:.2f}

Portfolio ของ {user.get('display_name','User')}:
{port_block}

Watchlist: {', '.join(user.get('watchlist', []))}

กฎ:
- อ้างอิงตัวเลขจริงเสมอ ไม่เดาสุ่ม
- ถ้าถามนอกขอบเขตการเงิน ตอบสั้นๆ ว่าไม่ถนัด
- ไม่แนะนำให้ซื้อขายหุ้นใด 100% เสมอบอกว่า DYOR
- ตอบเป็น bullet point ถ้าตอบยาว"""

def chat_page(user: dict, market_data: dict, thb: float,
              history: list = None) -> str:
    history = history or []
    has_key_class = "has-key" if market_data else ""

    # Render existing messages
    msgs_html = ""
    for msg in history:
        role = msg["role"]
        text = msg["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if role == "user":
            msgs_html += f"""
            <div class="msg-row user">
              <div class="msg-avatar user-av">👤</div>
              <div class="bubble user">{text}</div>
            </div>"""
        else:
            msgs_html += f"""
            <div class="msg-row ai">
              <div class="msg-avatar ai-av">A</div>
              <div class="bubble ai">{text}</div>
            </div>"""

    # Quick chips
    chips = [
        "พอร์ตฉันเป็นยังไงบ้าง?",
        "วันนี้ตลาดเป็นยังไง?",
        "ทองควรซื้อไหม?",
        "BTC สัญญาณอะไร?",
        "หุ้นไหนน่าเพิ่ม?",
        "ควร DCA ตัวไหน?",
    ]
    chips_html = "".join(f'<div class="chip" onclick="setMsg(this)">{c}</div>' for c in chips)

    js = """
const msgs   = document.getElementById('chatMsgs');
const input  = document.getElementById('chatInput');
const btn    = document.getElementById('sendBtn');

function scrollBottom(){ msgs.scrollTop = msgs.scrollHeight; }
scrollBottom();

function setMsg(el){ input.value = el.textContent; input.focus(); }

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
});

async function sendMsg() {
  const txt = input.value.trim();
  if (!txt || btn.disabled) return;

  // Show user bubble
  addBubble('user', txt);
  input.value = '';
  btn.disabled = true;

  // Typing indicator
  const typingId = 'typing_' + Date.now();
  msgs.insertAdjacentHTML('beforeend', `
    <div class="msg-row ai" id="${typingId}">
      <div class="msg-avatar ai-av">A</div>
      <div class="bubble ai typing">กำลังคิด<span class="spin">⟳</span></div>
    </div>`);
  scrollBottom();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({message: txt})
    });
    const data = await res.json();
    document.getElementById(typingId)?.remove();
    addBubble('ai', data.reply || '⚠️ ไม่ได้รับคำตอบ');
  } catch(e) {
    document.getElementById(typingId)?.remove();
    addBubble('ai', '⚠️ เกิดข้อผิดพลาด กรุณาลองใหม่');
  }
  btn.disabled = false;
  input.focus();
}

function addBubble(role, text) {
  const escaped = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const isUser  = role === 'user';
  msgs.insertAdjacentHTML('beforeend', `
    <div class="msg-row ${isUser?'user':'ai'}">
      <div class="msg-avatar ${isUser?'user-av':'ai-av'}">${isUser?'👤':'A'}</div>
      <div class="bubble ${isUser?'user':'ai'}">${escaped}</div>
    </div>`);
  scrollBottom();
}
"""

    no_key_banner = "" if market_data else """
    <div style="background:#f59e0b18;border:1px solid #f59e0b44;border-radius:8px;padding:10px 14px;
                font-size:12px;color:#f59e0b;margin:12px 16px">
      ⚠️ ยังไม่ได้ตั้ง OPENROUTER_API_KEY — ArtheeNoi จะใช้ rule-based mode (ไม่ใช่ AI จริง)
    </div>"""

    content = f"""
<div class="chat-wrap">
  <div class="chat-toolbar">{chips_html}</div>
  {no_key_banner}
  <div class="chat-messages" id="chatMsgs">
    {'<div class="msg-row ai"><div class="msg-avatar ai-av">A</div><div class="bubble ai">สวัสดีครับ! ผม ArtheeNoi 👋<br>ถามเรื่องหุ้น ทอง คริปโต หรือพอร์ตของคุณได้เลยครับ</div></div>' if not msgs_html else ''}
    {msgs_html}
  </div>
  <div class="chat-bar">
    <textarea class="chat-input" id="chatInput" rows="1"
      placeholder="ถามอะไรก็ได้เกี่ยวกับหุ้น ทอง คริปโต..."></textarea>
    <button class="chat-send" id="sendBtn" onclick="sendMsg()">➤</button>
  </div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chat ArtheeNoi</title>
<style>{_CSS}
body{{overflow:hidden}}
.main{{overflow:hidden}}
.content{{padding:0;overflow:hidden}}
</style>
</head>
<body>
<div class="layout">
  {_sidebar_html(user, "chat")}
  <div class="main">
    <div class="topbar">
      <div>
        <div class="topbar-title">💬 Chat กับ ArtheeNoi</div>
      </div>
      <div class="topbar-right">
        <span class="live-dot"></span>
        <span class="top-pill" id="mktTime">--:--</span>
        <span class="top-user" onclick="location.href='/settings'">👤 {user.get('display_name','User')}</span>
      </div>
    </div>
    <div class="main" style="overflow:hidden">
      {content}
    </div>
  </div>
</div>
<script>
function updateClock(){{const n=new Date();document.getElementById('mktTime').textContent=n.toLocaleTimeString('th-TH',{{hour:'2-digit',minute:'2-digit'}});}}
setInterval(updateClock,1000);updateClock();
{js}
</script>
</body></html>"""
    return html

# ─── SCREENER PAGE ───────────────────────────────────────────────────────────

_TIER_LABEL = {1: "🔵 Blue-chip", 2: "🟡 Growth", 3: "🔴 Speculative"}
_TIER_COL   = {1: "var(--blue)", 2: "var(--gold)", 3: "var(--red)"}

def _action_badge(action: str) -> str:
    colors = {
        "BUY":        ("#22c55e", "#22c55e22"),
        "STRONG BUY": ("#4ade80", "#22c55e33"),
        "WATCH":      ("#f59e0b", "#f59e0b22"),
        "WAIT":       ("#9999a8", "#6b6b7822"),
        "NEUTRAL":    ("#9999a8", "#6b6b7822"),
        "AVOID":      ("#ef4444", "#ef444422"),
    }
    fg, bg = colors.get(action, ("#9999a8", "#6b6b7822"))
    return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}44;'
            f'font-size:10px;font-weight:800;padding:2px 8px;border-radius:20px;'
            f'text-transform:uppercase">{action}</span>')

def screener_page(user: dict, market_data: dict, macro: dict,
                  vault_picks: list = None) -> str:
    """
    3 tabs:
      1. Top Picks — ArtheeNoi daily filtered list (from vault_picks cache)
      2. Browse All — all 600+ stocks searchable/filterable
      3. Under Radar — tier 3 speculative stocks
    """
    try:
        import at_stock_vault as vault
        VAULT = vault.VAULT
        summary = vault.vault_summary()
    except ImportError:
        VAULT = []
        summary = {"total": 0, "tier1": 0, "tier2": 0, "tier3": 0, "sectors": {}}

    picks = vault_picks or []

    # ── Tab 1: Top Picks ────────────────────────────────────────────────────
    regime   = (macro or {}).get("regime", "mid_cycle")
    risk_lvl = (macro or {}).get("risk_level", "normal_risk")
    regime_display = {
        "expansion":     "🚀 Expansion",
        "mid_cycle":     "📈 Mid Cycle",
        "recession_risk":"⚠️ Recession Risk",
        "crisis":        "🔴 Crisis",
        "overheating":   "🌡 Overheating",
    }.get(regime, regime)

    picks_rows = ""
    for p in picks[:60]:
        sym    = p.get("sym") or p.get("t", "")
        d      = market_data.get(sym, {})
        price  = d.get("price", 0)
        chg    = d.get("change_pct") or d.get("chg") or 0
        rsi    = d.get("rsi")
        action = p.get("action", "NEUTRAL")
        sector = p.get("sector") or p.get("s", "")
        score  = p.get("ai_score", 0)
        note   = next((e.get("note","") for e in VAULT if e["t"]==sym), "")
        tier   = next((e.get("tier", 2) for e in VAULT if e["t"]==sym), 2)
        pct52  = ""
        if d.get("high") and d.get("low") and price:
            rng = d["high"] - d["low"]
            pos = (price - d["low"]) / rng * 100 if rng else 50
            pct52 = f'<div class="pbar" style="width:70px;margin-top:3px"><div class="pbar-fill" style="width:{pos:.0f}%;background:var(--teal)"></div></div>'

        picks_rows += f"""
        <tr>
          <td>
            <div style="font-weight:800;font-size:14px">{sym}</div>
            <div style="font-size:10px;color:var(--muted)">{note[:35]}</div>
          </td>
          <td><span style="font-size:11px;color:var(--mid)">{sector}</span></td>
          <td><span style="color:{_TIER_COL.get(tier,'var(--mid)')};font-size:11px;font-weight:700">{_TIER_LABEL.get(tier,'')}</span></td>
          <td>{'$'+f'{price:,.2f}' if price else '<span style="color:var(--muted)">—</span>'}</td>
          <td><span style="color:{'var(--green)' if chg>=0 else 'var(--red)'}">{'+'if chg>=0 else ''}{chg:.2f}%</span></td>
          <td>{_rsi_bar(rsi)}</td>
          <td>
            <div style="font-size:22px;font-weight:900;color:{'var(--teal)' if score>=70 else 'var(--gold)' if score>=50 else 'var(--muted)'}">{score or '—'}</div>
            {pct52}
          </td>
          <td>{_action_badge(action)}</td>
        </tr>"""

    # ── Tab 2: Browse All ────────────────────────────────────────────────────
    all_sectors = sorted({e["s"] for e in VAULT})
    sector_btns = "".join(
        f'<button class="chip" onclick="filterSector(this,\'{s}\')">{s}</button>'
        for s in all_sectors
    )

    all_rows = ""
    for e in VAULT:
        d     = market_data.get(e["t"], {})
        price = d.get("price", 0)
        chg   = d.get("change_pct") or d.get("chg") or 0
        rsi   = d.get("rsi")
        tier  = e.get("tier", 2)
        all_rows += f"""
        <tr class="vault-row" data-sector="{e['s']}" data-tier="{tier}"
            data-sym="{e['t']}" data-search="{e['t'].lower()} {e['c'].lower()} {e['s'].lower()} {e.get('note','').lower()}">
          <td><b style="font-size:13px">{e['t']}</b></td>
          <td style="font-size:12px;color:var(--mid)">{e['c']}</td>
          <td><span style="font-size:11px;color:var(--mid)">{e['s']}</span></td>
          <td><span style="color:{_TIER_COL.get(tier,'var(--mid)')};font-size:10px;font-weight:700">{_TIER_LABEL.get(tier,'')}</span></td>
          <td>{'$'+f'{price:,.2f}' if price else '<span style="color:var(--muted);font-size:11px">—</span>'}</td>
          <td><span style="color:{'var(--green)'if chg>=0 else 'var(--red)';font-size:12px}">{'+'if chg>=0 else ''}{chg:.2f if price else 0:.2f}%</span></td>
          <td>{_rsi_bar(rsi) if rsi else '<span style="color:var(--muted)">—</span>'}</td>
          <td style="font-size:11px;color:var(--muted)">{e.get('note','')[:40]}</td>
        </tr>"""

    # ── Tab 3: Under Radar (Tier 3) ──────────────────────────────────────────
    tier3 = [e for e in VAULT if e.get("tier") == 3]
    under_cards = ""
    for e in tier3:
        d     = market_data.get(e["t"], {})
        price = d.get("price", 0)
        chg   = d.get("change_pct") or d.get("chg") or 0
        rsi   = d.get("rsi")
        if price:
            closes = d.get("closes", [])
            hi = d.get("high", price * 1.3)
            lo = d.get("low",  price * 0.7)
            pos = (price - lo) / (hi - lo) * 100 if hi > lo else 50
            buy = rsi and rsi <= 40
        under_cards += f"""
        <div class="card-sm" style="border-left:3px solid var(--purple)">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div style="font-weight:800;font-size:14px">{e['t']}</div>
              <div style="font-size:11px;color:var(--muted)">{e['c']}</div>
            </div>
            {'<span style="font-size:10px;font-weight:800;color:var(--teal);border:1px solid var(--teal)44;padding:2px 7px;border-radius:10px">👀 WATCH</span>' if (price and rsi and rsi<=40) else ''}
          </div>
          <div style="margin-top:6px;font-size:11px;color:var(--muted)">{e['s']} · {e.get('note','')[:40]}</div>
          {f'<div style="margin-top:8px"><div style="font-size:16px;font-weight:800">${price:,.2f} <span style="font-size:11px;color:{chr(39)}var(--green){chr(39) if chg>=0 else chr(39)}var(--red){chr(39)}">{chr(43) if chg>=0 else chr(45)}{abs(chg):.2f}%</span></div><div class="pbar" style="margin-top:4px"><div class="pbar-fill" style="width:{pos:.0f}%;background:var(--purple)"></div></div></div>' if price else '<div style="color:var(--muted);font-size:11px;margin-top:6px">ยังไม่มีราคา</div>'}
        </div>"""

    # ── Sector summary cards ─────────────────────────────────────────────────
    top_sectors = sorted(summary.get("sectors", {}).items(), key=lambda x: -x[1])[:12]
    sector_cards = "".join(
        f'<div style="background:var(--card2);border-radius:8px;padding:8px 12px;font-size:12px">'
        f'<div style="color:var(--mid);font-size:10px">{s}</div>'
        f'<div style="font-weight:700;color:var(--text)">{n} หุ้น</div></div>'
        for s, n in top_sectors
    )

    html = f"""
<!-- Stats bar -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm">
    <div class="card-hdr">Vault ทั้งหมด</div>
    <div class="stat-val teal-c">{summary['total']}</div>
    <div class="stat-lbl">หุ้นใน database</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Top Picks วันนี้</div>
    <div class="stat-val" style="color:var(--gold)">{len(picks)}</div>
    <div class="stat-lbl">ArtheeNoi เลือก</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Macro Regime</div>
    <div style="font-size:15px;font-weight:800;margin-top:4px">{regime_display}</div>
    <div class="stat-lbl" style="color:{'var(--red)' if 'Risk' in risk_lvl or 'Crisis' in regime_display else 'var(--green)'}">{risk_lvl}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Tier</div>
    <div style="font-size:12px;line-height:2;color:var(--mid)">
      🔵 <b style="color:var(--text)">{summary['tier1']}</b> Blue-chip &nbsp;
      🟡 <b style="color:var(--text)">{summary['tier2']}</b> Growth<br>
      🔴 <b style="color:var(--text)">{summary['tier3']}</b> Under Radar
    </div>
  </div>
</div>

<!-- Tabs -->
<div style="display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:0">
  <button class="tab active" id="tabPicks" onclick="showTab('picks')">🎯 Top Picks ({len(picks)})</button>
  <button class="tab" id="tabAll"   onclick="showTab('all')">🔭 Browse All ({summary['total']})</button>
  <button class="tab" id="tabUnder" onclick="showTab('under')">👀 Under Radar ({len(tier3)})</button>
  <button class="tab" id="tabSect" onclick="showTab('sect')">📊 Sectors</button>
</div>

<!-- Tab: Top Picks -->
<div id="panePicks">
  <div class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div class="card-hdr" style="margin-bottom:0">ArtheeNoi Daily Picks — {regime_display}</div>
      <span style="font-size:11px;color:var(--muted)">อัปเดตตอน market refresh</span>
    </div>
    <div style="overflow-x:auto">
      <table class="tbl">
        <thead><tr>
          <th>Symbol</th><th>Sector</th><th>Tier</th><th>ราคา</th><th>วันนี้</th><th>RSI</th><th>AI Score</th><th>Action</th>
        </tr></thead>
        <tbody>{picks_rows or '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">กำลังโหลด Vault picks... (ใช้เวลา 2-3 นาทีหลัง refresh)</td></tr>'}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- Tab: Browse All -->
<div id="paneAll" style="display:none">
  <div class="card">
    <div style="display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
      <input id="vaultSearch" type="text" placeholder="ค้นหา symbol / ชื่อ / sector..."
        style="flex:1;min-width:180px;background:var(--card2);border:1px solid var(--border);border-radius:8px;
               padding:8px 12px;color:var(--text);font-size:13px;outline:none"
        oninput="filterVault()">
      <select id="tierFilter" onchange="filterVault()"
        style="background:var(--card2);border:1px solid var(--border);border-radius:8px;
               color:var(--text);padding:8px 12px;font-size:12px;cursor:pointer">
        <option value="">All Tiers</option>
        <option value="1">🔵 Blue-chip</option>
        <option value="2">🟡 Growth</option>
        <option value="3">🔴 Speculative</option>
      </select>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">
      <button class="chip" onclick="filterSector(this,'')">All</button>
      {sector_btns}
    </div>
    <div id="vaultCount" style="font-size:11px;color:var(--muted);margin-bottom:8px">{summary['total']} หุ้น</div>
    <div style="overflow-x:auto;max-height:60vh;overflow-y:auto">
      <table class="tbl" id="vaultTable">
        <thead style="position:sticky;top:0;background:var(--card)"><tr>
          <th>Symbol</th><th>Company</th><th>Sector</th><th>Tier</th><th>ราคา</th><th>วันนี้</th><th>RSI</th><th>Note</th>
        </tr></thead>
        <tbody id="vaultBody">{all_rows}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- Tab: Under Radar -->
<div id="paneUnder" style="display:none">
  <div class="card-hdr" style="margin-bottom:10px">👀 Under-Radar Stocks ({len(tier3)} ตัว) — Tier 3 Speculative</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">
    {under_cards or '<div style="color:var(--muted)">ไม่มีข้อมูล</div>'}
  </div>
</div>

<!-- Tab: Sectors -->
<div id="paneSect" style="display:none">
  <div class="card">
    <div class="card-hdr">📊 Sector Breakdown</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;margin-top:4px">
      {sector_cards}
    </div>
  </div>
</div>
"""

    js = """
// Tab switching
function showTab(name) {
  ['picks','all','under','sect'].forEach(t => {
    document.getElementById('pane'+t.charAt(0).toUpperCase()+t.slice(1)).style.display = t===name?'':'none';
    const btn = document.getElementById('tab'+t.charAt(0).toUpperCase()+t.slice(1));
    if(btn) btn.classList.toggle('active', t===name);
  });
}
// Vault search + filter
let _activeSector = '';
function filterVault() {
  const q    = document.getElementById('vaultSearch').value.toLowerCase().trim();
  const tier = document.getElementById('tierFilter').value;
  let shown  = 0;
  document.querySelectorAll('#vaultBody tr.vault-row').forEach(tr => {
    const search = tr.dataset.search || '';
    const sec    = tr.dataset.sector || '';
    const t      = tr.dataset.tier || '';
    const match  = (!q || search.includes(q)) &&
                   (!tier || t === tier) &&
                   (!_activeSector || sec === _activeSector);
    tr.style.display = match ? '' : 'none';
    if(match) shown++;
  });
  document.getElementById('vaultCount').textContent = shown + ' หุ้น';
}
function filterSector(el, sec) {
  _activeSector = sec;
  document.querySelectorAll('.chip').forEach(c => c.style.color='');
  if(el) el.style.color = 'var(--teal)';
  filterVault();
}
"""

    return _base("screener", "Stock Screener", html, user, "", js)

def _sidebar_html(user: dict, active: str) -> str:
    is_admin = user.get("role") == "admin"
    nav = [
        ("stocks",  "📊", "Stocks"),
        ("gold",    "🥇", "Gold"),
        ("crypto",  "₿",  "Crypto"),
        ("dca",     "📈", "DCA"),
        ("signals", "🎯", "Signals"),
        ("news",    "📰", "News"),
        ("paper",   "🧪", "Paper Trade"),
        ("ai",      "🤖", "AI Analysis"),
        ("screener","🔭", "Screener"),
        ("chat",    "💬", "Chat ArtheeNoi"),
    ]
    nav_html = ""
    for nid, icon, label in nav:
        a = "active" if nid == active else ""
        nav_html += (f'<a class="sb-link {a}" href="/{nid}">'
                     f'{icon}<span class="tip">{label}</span></a>')
    return f"""<nav class="sb">
    <div class="sb-logo">A</div>
    {nav_html}
    <div class="sb-spacer"></div>
    <div class="sb-bot">
      <a class="sb-link" href="/settings">⚙️<span class="tip">Settings</span></a>
      {'<a class="sb-link" href="/admin">👑<span class="tip">Admin</span></a>' if is_admin else ''}
      <a class="sb-link" href="/logout">🚪<span class="tip">Logout</span></a>
    </div>
  </nav>"""

LOADING_PAGE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="12">
<title>Loading — ArtheeNoi</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;background:#0a0a0c;display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif;color:#f0f0f2}
.box{text-align:center;max-width:420px;padding:0 20px}
.logo{width:64px;height:64px;background:linear-gradient(135deg,#22c55e,#16a34a);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 20px}
h2{font-size:22px;font-weight:800;margin-bottom:8px}
p{color:#5a5a68;font-size:14px;margin-bottom:4px}
.bar{width:200px;height:4px;background:#1c1c22;border-radius:2px;margin:20px auto;overflow:hidden}
.bar-fill{height:100%;background:#22c55e;border-radius:2px;animation:load 2s ease-in-out infinite}
@keyframes load{0%{width:0%}100%{width:100%}}
.note{margin-top:16px;font-size:11px;color:#3a3a48}
</style>
</head>
<body>
<div class="box">
  <div class="logo">A</div>
  <h2>กำลังโหลดข้อมูล</h2>
  <p>ดึงราคาหุ้น + คำนวณ AI Score</p>
  <p>ใช้เวลา 2-3 นาทีสำหรับครั้งแรก</p>
  <div class="bar"><div class="bar-fill"></div></div>
  <p class="note">หน้าจะ refresh อัตโนมัติทุก 12 วินาที</p>
</div>
</body></html>"""
