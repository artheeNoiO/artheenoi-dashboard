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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root {
  --bg:       #080808;
  --bg2:      #111111;
  --bg3:      #1a1a1a;
  --border:   #2a2a2a;
  --text:     #f0f0f0;
  --mid:      #888888;
  --muted:    #555555;
  --teal:     #e0e0e0;
  --blue:     #a0a0a0;
  --green:    #4caf50;
  --red:      #ef5350;
  --gold:     #c8b87a;
  --purple:   #b0b0b0;
  --card:     #111111;
  /* legacy aliases */
  --sb:       #111111;
  --card2:    #1a1a1a;
  --bl:       #1a1a1a;
  --orange:   #d4a96a;
  --accent:   #e0e0e0;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:'Inter','Segoe UI',system-ui,sans-serif;font-size:14px}

/* ── Layout ── */
.layout{display:flex;height:100vh;overflow:hidden}

/* ── Sidebar ── */
.sb{width:220px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;z-index:50;overflow-y:auto}
.sb-logo{display:flex;align-items:center;padding:20px 16px 16px;border-bottom:1px solid var(--border);flex-shrink:0}
.sb-logo-icon{display:none}
.sb-logo-text{font-size:14px;font-weight:900;color:var(--text);letter-spacing:2px;text-transform:uppercase}
.sb-link{display:flex;align-items:center;padding:9px 16px;color:var(--muted);text-decoration:none;font-size:11px;font-weight:600;transition:.12s;border-left:2px solid transparent;letter-spacing:1.5px;text-transform:uppercase}
.sb-link:hover{color:var(--text);background:rgba(255,255,255,0.03)}
.sb-link.active{color:var(--text);border-left-color:var(--text);background:rgba(255,255,255,0.04)}
.sb-icon{display:none}
.sb-label{font-size:11px;letter-spacing:1.5px;font-weight:600}
.tip{display:none}
.sb-spacer{flex:1}
.sb-bot{border-top:1px solid var(--border);padding:8px 0}
@media(max-width:700px){.sb{width:52px}.sb-label{display:none}.sb-logo-text{display:none}}

/* ── Main ── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* ── Topbar ── */
.topbar{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;gap:12px;flex-shrink:0}
.topbar-title{font-size:13px;font-weight:800;color:var(--text);letter-spacing:.3px;text-transform:uppercase}
.topbar-sub{font-size:11px;color:var(--muted)}
.topbar-search{flex:1;max-width:280px;position:relative}
.topbar-search input{background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 12px 6px 32px;font-size:13px;width:100%;outline:none;transition:.15s}
.topbar-search input:focus{border-color:var(--teal)}
.topbar-search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;pointer-events:none}
.topbar-right{margin-left:auto;display:flex;align-items:center;gap:10px;flex-shrink:0}
.mkt-dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:2px;vertical-align:middle}
.mkt-open{background:#26a69a}.mkt-closed{background:#ef5350}
.top-pill{background:var(--bg3);border:1px solid var(--border);border-radius:16px;padding:4px 10px;font-size:11px;font-weight:600;color:var(--mid)}
.top-user{font-size:12px;color:var(--mid);cursor:pointer}
.top-user:hover{color:var(--text)}

/* ── Tabs ── */
.tabs{display:flex;gap:2px;padding:0 16px;background:var(--bg2);border-bottom:1px solid var(--border);flex-shrink:0}
.tab{padding:10px 14px;font-size:12px;font-weight:600;color:var(--mid);cursor:pointer;border-bottom:2px solid transparent;transition:.15s;white-space:nowrap;text-decoration:none;display:inline-block}
.tab:hover{color:var(--text)}
.tab.active{color:var(--text);border-bottom-color:var(--teal)}

/* ── Scrollbar global ── */
*::-webkit-scrollbar{width:5px;height:5px}
*::-webkit-scrollbar-track{background:#0d0d0d}
*::-webkit-scrollbar-thumb{background:#2e2e2e;border-radius:2px}
*::-webkit-scrollbar-thumb:hover{background:#444444}
*{scrollbar-width:thin;scrollbar-color:#2e2e2e #0d0d0d}

/* ── Content ── */
.content{flex:1;overflow-y:auto;padding:20px}

/* ── Cards ── */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:18px}
.card-sm{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:18px 20px}
.card-hdr{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:14px}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:18px 20px;display:flex;flex-direction:column}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:6px}
.stat-value{font-size:26px;font-weight:800;color:var(--text)}
.stat-sub{font-size:11px;color:var(--mid);margin-top:4px}

/* ── Grid ── */
.g2{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.g-auto{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
@media(max-width:900px){.g4{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.g4,.g3,.g2{grid-template-columns:1fr}}

/* ── Stat blocks ── */
.stat-val{font-size:26px;font-weight:900;line-height:1;letter-spacing:-.5px}
.stat-lbl{font-size:10px;color:var(--muted);margin-top:5px;letter-spacing:.3px}
.pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--mid)}
.gold-c{color:var(--gold)}.blue-c{color:var(--blue)}.teal-c{color:var(--teal)}

/* ── Badges ── */
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.badge-buy{background:rgba(38,166,154,0.2);color:var(--green);border:1px solid rgba(38,166,154,0.4)}
.badge-sell,.badge-avoid{background:rgba(239,83,80,0.2);color:var(--red);border:1px solid rgba(239,83,80,0.4)}
.badge-watch{background:rgba(240,180,41,0.2);color:var(--gold);border:1px solid rgba(240,180,41,0.4)}
.badge-wait,.badge-neutral{background:rgba(120,123,134,0.2);color:var(--mid);border:1px solid rgba(120,123,134,0.4)}
.badge-dca{background:rgba(45,212,191,0.2);color:var(--teal);border:1px solid rgba(45,212,191,0.4)}

/* ── Progress bar ── */
.pbar{height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:6px}
.pbar-fill{height:100%;border-radius:2px;transition:width .4s}

/* ── Table ── */
.tbl{width:100%;border-collapse:collapse}
.tbl th{background:var(--bg3);color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.8px;padding:10px 12px;text-align:left;white-space:nowrap;font-weight:700;border-bottom:1px solid var(--border)}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--bg3);font-size:13px;vertical-align:middle}
.tbl tr:hover td{background:rgba(255,255,255,0.02)}
.tbl .sym{font-weight:800;font-size:14px;letter-spacing:.2px}

/* ── Signal chip ── */
.sig{display:inline-flex;gap:4px;align-items:center;font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px}
.sig-BUY{background:rgba(38,166,154,0.15);color:var(--green)}
.sig-WATCH{background:rgba(240,180,41,0.15);color:var(--gold)}
.sig-WAIT,.sig-NEUTRAL{background:rgba(120,123,134,0.15);color:var(--mid)}
.sig-AVOID{background:rgba(239,83,80,0.15);color:var(--red)}

/* ── RSI bar ── */
.rsi-wrap{width:80px}
.rsi-bar{height:6px;background:var(--border);border-radius:3px;position:relative;overflow:hidden}
.rsi-fill{height:100%;border-radius:3px}

/* ── Sparkline ── */
canvas.spark{width:80px;height:32px;display:block}

/* ── Ticker ── */
.ticker-wrap{overflow:hidden;background:var(--bg2);border-bottom:1px solid var(--border);height:32px;flex-shrink:0}
.ticker-inner{display:flex;align-items:center;height:32px;animation:tick 40s linear infinite;width:max-content}
.ticker-inner:hover{animation-play-state:paused}
.ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 20px;font-size:11px;font-weight:600;white-space:nowrap;border-right:1px solid var(--border)}
.ticker-sym{color:var(--mid)}.ticker-px{color:var(--text)}.ticker-chg.up{color:var(--green)}.ticker-chg.dn{color:var(--red)}
@keyframes tick{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}

/* ── Buttons ── */
.btn{padding:7px 16px;border-radius:6px;border:none;cursor:pointer;font-size:13px;font-weight:500;transition:.15s;font-family:inherit}
.btn-primary{background:#f0f0f0;color:#080808;font-weight:700;letter-spacing:.2px}.btn-primary:hover{background:#ffffff}
.btn-secondary{background:var(--bg3);color:var(--text);border:1px solid var(--border)}
.btn-danger{background:rgba(239,83,80,0.12);color:var(--red);border:1px solid rgba(239,83,80,0.25)}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--mid)}.btn-ghost:hover{border-color:var(--text);color:var(--text)}
.btn-sm{padding:4px 10px;font-size:11px;border-radius:4px}

/* ── Input / Select ── */
input,select,textarea{background:var(--bg3);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:7px 11px;font-size:13px;font-family:inherit}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}

/* ── Live dot ── */
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Loading ── */
.spin{animation:spin 1s linear infinite;display:inline-block}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Chat ── */
.chat-wrap{display:flex;flex-direction:column;height:100%;overflow:hidden}
.chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.chat-messages::-webkit-scrollbar{width:5px}
.chat-messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.msg-row{display:flex;gap:10px;align-items:flex-end;max-width:85%}
.msg-row.user{align-self:flex-end;flex-direction:row-reverse}
.msg-row.ai{align-self:flex-start}
.msg-avatar{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.msg-avatar.user-av{background:var(--bg3);border:1px solid var(--border)}
.msg-avatar.ai-av{background:linear-gradient(135deg,var(--teal),#16a34a)}
.bubble{padding:10px 14px;border-radius:12px;font-size:13px;line-height:1.6;max-width:100%;word-wrap:break-word;white-space:pre-wrap}
.bubble.user{background:var(--teal);color:#000;border-bottom-right-radius:4px}
.bubble.ai{background:var(--bg3);border:1px solid var(--border);color:var(--text);border-bottom-left-radius:4px}
.bubble.typing{color:var(--muted)}
.chat-bar{padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px;flex-shrink:0;background:var(--bg2)}
.chat-input{flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:13px;font-family:inherit;resize:none;outline:none;max-height:120px;min-height:42px;transition:border .15s}
.chat-input:focus{border-color:var(--teal)}
.chat-input::placeholder{color:var(--muted)}
.chat-send{width:42px;height:42px;border-radius:10px;background:var(--teal);border:none;cursor:pointer;font-size:18px;flex-shrink:0;transition:.15s;display:flex;align-items:center;justify-content:center}
.chat-send:hover{filter:brightness(1.1)}
.chat-send:disabled{opacity:.4;cursor:not-allowed}
.chat-toolbar{display:flex;gap:6px;padding:6px 16px;background:var(--bg2);border-bottom:1px solid var(--border)}
.chip{font-size:11px;padding:4px 10px;border-radius:20px;background:var(--bg3);border:1px solid var(--border);color:var(--mid);cursor:pointer;transition:.1s;white-space:nowrap}
.chip:hover{border-color:var(--teal);color:var(--teal)}

/* ── Chart toolbar (TV-style) ── */
.chart-toolbar{display:flex;align-items:center;gap:6px;padding:10px 0;flex-wrap:wrap}
.tf-btn,.ind-btn{background:var(--bg3);color:var(--mid);border:1px solid var(--border);padding:4px 10px;border-radius:4px;cursor:pointer;font-size:12px;transition:.15s;font-family:inherit}
.tf-btn.active,.ind-btn.active{background:var(--teal);color:#000;border-color:var(--teal)}
.tf-btn:hover,.ind-btn:hover{border-color:var(--teal);color:var(--teal)}
.tf-btn.active:hover,.ind-btn.active:hover{color:#000}
.tf-sep{width:1px;height:20px;background:var(--border);margin:0 4px;display:inline-block}
.ohlcv-bar{display:flex;align-items:center;gap:14px;padding:6px 0;font-size:13px;flex-wrap:wrap;min-height:36px}
.sym-label{font-size:16px;font-weight:700;color:var(--text)}
.chart-panel{background:var(--bg2);border:1px solid var(--border);border-radius:8px;margin-bottom:8px;overflow:hidden}
.chart-panel-label{font-size:10px;color:var(--mid);text-transform:uppercase;letter-spacing:.5px;padding:6px 12px;border-bottom:1px solid var(--border);background:var(--bg3)}

/* ── Hamburger button ── */
.hamburger{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px;z-index:301}
.hamburger span{display:block;width:22px;height:2px;background:var(--mid);border-radius:2px;transition:.3s}
.hamburger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.hamburger.open span:nth-child(2){opacity:0}
.hamburger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
/* ── Sidebar overlay ── */
.sb-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:299}
.sb-overlay.open{display:block}
/* ── Search dropdown ── */
.search-dropdown{position:absolute;top:calc(100% + 4px);left:0;right:0;background:var(--bg2);border:1px solid var(--border);border-radius:8px;z-index:500;max-height:240px;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.5)}
.search-item{padding:8px 14px;cursor:pointer;font-size:13px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--bg3)}
.search-item:last-child{border-bottom:none}
.search-item:hover{background:var(--bg3)}
.search-item .s-sym{font-weight:700;color:var(--teal);min-width:56px}
.search-item .s-name{color:var(--muted);font-size:11px}
/* ── Bottom nav (mobile) ── */
.bottom-nav{display:none;position:fixed;bottom:0;left:0;right:0;z-index:200;background:var(--bg2);border-top:1px solid var(--border);height:58px;justify-content:space-around;align-items:center}
.bottom-nav a{display:flex;flex-direction:column;align-items:center;color:var(--mid);text-decoration:none;font-size:9px;gap:2px;padding:6px 4px;border-radius:8px;transition:.15s;flex:1;min-width:0}
.bottom-nav a.active{color:var(--teal)}
.bottom-nav a .bn-icon{font-size:19px;line-height:1}
.bottom-nav a .bn-lbl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:48px;text-align:center}
/* ── Mobile Responsive ── */
@media (max-width: 768px) {
  .hamburger{display:flex}
  .sb{position:fixed;left:-240px;top:0;height:100vh;z-index:300;transition:left .3s;width:220px}
  .sb.open{left:0}
  .topbar-search{max-width:none;flex:1}
  .top-pill{display:none}
  .content{padding:14px 12px 70px}
  .bottom-nav{display:flex}
  .g2,.g3,.g4{grid-template-columns:1fr!important}
  .tbl td,.tbl th{padding:6px 8px;font-size:12px}
  .stat-value{font-size:18px}
}
@media (min-width:769px){
  .bottom-nav{display:none!important}
  .sb-overlay{display:none!important}
}

/* ── Toast Notifications ── */
.toast-container { position:fixed; top:60px; right:16px; z-index:9999; display:flex; flex-direction:column; gap:8px; pointer-events:none; }
.toast { background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:12px 16px; min-width:260px; max-width:320px; box-shadow:0 4px 20px rgba(0,0,0,.4); pointer-events:all; animation:toastIn .3s ease; display:flex; align-items:flex-start; gap:10px; }
.toast-icon { font-size:20px; flex-shrink:0; }
.toast-body { flex:1; }
.toast-title { font-weight:700; font-size:13px; color:var(--text); }
.toast-msg { font-size:12px; color:var(--mid); margin-top:2px; }
.toast-close { cursor:pointer; color:var(--muted); font-size:16px; line-height:1; padding:0 4px; }
.toast.toast-buy { border-left:3px solid var(--green); }
.toast.toast-sell { border-left:3px solid var(--red); }
.toast.toast-info { border-left:3px solid var(--teal); }
@keyframes toastIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:none} }

/* ── Quick-Add Button ── */
.btn-qadd { background:rgba(45,212,191,.15); color:var(--teal); border:1px solid rgba(45,212,191,.3); padding:3px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:600; white-space:nowrap; }
.btn-qadd:hover { background:rgba(45,212,191,.3); }
"""

# ─── Toast / Alert JS (always loaded) ────────────────────────────────────────

_TOAST_JS = """
// ── Toast notification system ──────────────────────────────────────
window._ArtheeToast = {
  container: null,
  init() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  },
  show(title, msg, type='info', duration=6000) {
    this.init();
    const icons = {buy:'🟢', sell:'🔴', info:'🔔'};
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.innerHTML = `<span class="toast-icon">${icons[type]||'🔔'}</span><div class="toast-body"><div class="toast-title">${title}</div><div class="toast-msg">${msg}</div></div><span class="toast-close" onclick="this.parentElement.remove()">✕</span>`;
    this.container.appendChild(t);
    if (duration > 0) setTimeout(() => t.remove(), duration);
  }
};
// ── Price alert polling (check every 60s against user's alerts) ────
let _lastAlertCheck = {};
async function _checkBrowserAlerts() {
  try {
    const [priceRes, alertRes] = await Promise.all([
      fetch('/api/prices'),
      fetch('/api/alerts')
    ]);
    const prices = await priceRes.json();
    const alerts = await alertRes.json();
    (alerts.active || []).forEach(a => {
      const d = prices[a.sym];
      if (!d || !d.price) return;
      const key = `${a.id}`;
      const price = d.price;
      let triggered = false;
      if (a.condition === 'above' && price >= a.price) triggered = true;
      if (a.condition === 'below' && price <= a.price) triggered = true;
      if (a.condition === 'change_pct' && Math.abs(d.chg || 0) >= a.price) triggered = true;
      if (triggered && _lastAlertCheck[key] !== true) {
        _lastAlertCheck[key] = true;
        const dir = a.condition === 'above' ? 'buy' : 'sell';
        window._ArtheeToast.show(
          `🚨 Alert: ${a.sym}`,
          `Price $${price.toFixed(2)} — ${a.condition} $${a.price} triggered!`,
          dir
        );
        // Log triggered alert to server
        fetch('/api/alert-log', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({alert_id: a.id, sym: a.sym,
            condition: a.condition, target: a.price, actual: price})
        }).catch(()=>{});
      } else if (!triggered) {
        _lastAlertCheck[key] = false;
      }
    });
  } catch(e) {}
}
setInterval(_checkBrowserAlerts, 60000);
document.addEventListener('DOMContentLoaded', () => setTimeout(_checkBrowserAlerts, 3000));
"""

# ─── Base Layout ──────────────────────────────────────────────────────────────

def _base(page_id: str, title: str, content: str, user: dict,
          ticker_html: str = "", extra_js: str = "") -> str:
    display = user.get("display_name", "User")
    is_admin = user.get("role") == "admin"
    nav = [
        ("stocks",    "📊", "Stocks"),
        ("watchlist", "👁",  "Watchlist"),
        ("journal",   "📓", "Journal"),
        ("charts",    "📉", "Charts"),
        ("gold",      "🥇", "Gold"),
        ("crypto",    "₿",  "Crypto"),
        ("dca",       "📈", "DCA"),
        ("signals",   "🎯", "Signals"),
        ("dividends", "💰", "Dividends"),
        ("tools",     "🧮", "Tools"),
        ("news",      "📰", "News"),
        ("map",       "🗺️", "Map"),
        ("paper",     "🧪", "Paper"),
        ("ai",        "🤖", "AI"),
        ("screener",  "🔭", "Screener"),
        ("heatmap",   "🟩", "Heatmap"),
        ("analytics", "📐", "Analytics"),
        ("scanner",   "🔍", "Scanner"),
        ("chat",      "💬", "Chat"),
        ("alerts",    "🔔", "Alerts"),
        ("calendar",  "📅", "Calendar"),
        ("options",   "⚙",  "Options"),
        ("backtest",    "⏪", "Backtest"),
        ("correlation", "🔗", "Correlation"),
        ("report",      "📄", "Report"),
        ("risk",        "⚠️", "Risk"),
        ("benchmark",   "📏", "Benchmark"),
        ("realized",    "💵", "Realized P&L"),
        ("compare",     "⚖️", "Compare"),
        ("macro",       "🌐", "Macro"),
        ("earnings",    "📆", "Earnings"),
        ("sentiment",   "🧠", "Sentiment"),
        ("targets",     "🎯", "Targets"),
        ("portfolios",  "💼", "Portfolios"),
        ("settings",    "⚙️", "Settings"),
        ("insider",     "🏦", "Insider"),
    ]
    _TH = {
        "stocks":"หุ้น","watchlist":"ติดตาม","journal":"บันทึก","charts":"กราฟ",
        "gold":"ทอง","crypto":"คริปโต","dca":"DCA","signals":"สัญญาณ",
        "dividends":"ปันผล","tools":"เครื่องมือ","news":"ข่าว","map":"แผนที่","paper":"ทดลอง",
        "ai":"AI","screener":"คัดกรอง","heatmap":"ฮีตแมป","analytics":"วิเคราะห์",
        "scanner":"สแกน","chat":"แชท","alerts":"แจ้งเตือน","calendar":"ปฏิทิน",
        "options":"ออปชัน","backtest":"ทดสอบ","correlation":"สหสัมพันธ์",
        "report":"รายงาน","risk":"ความเสี่ยง","benchmark":"เปรียบ","realized":"กำไรจริง",
        "compare":"เปรียบเทียบ","macro":"มาโคร","earnings":"กำไร","sentiment":"ความรู้สึก",
        "targets":"เป้าหมาย","portfolios":"พอร์ต","insider":"อินไซเดอร์",
        "settings":"ตั้งค่า","admin":"แอดมิน","logout":"ออกจากระบบ","home":"หน้าหลัก",
    }
    nav = [(nid, ic, lb) for nid, ic, lb in nav if nid not in ("settings", "home")]
    bn_stocks  = "active" if page_id == "stocks"   else ""
    bn_charts  = "active" if page_id == "charts"   else ""
    bn_screen  = "active" if page_id == "screener" else ""
    bn_scanner = "active" if page_id == "scanner"  else ""
    bn_chat    = "active" if page_id == "chat"     else ""
    nav_html = ""
    for nid, icon, label in nav:
        act = "active" if nid == page_id else ""
        th = _TH.get(nid, label)
        nav_html += f'<a class="sb-link {act}" href="/{nid}"><span class="sb-label" data-en="{label}" data-th="{th}">{label}</span></a>\n'

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — ArtheeNoi</title>
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#131722">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="ArtheeNoi">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{_CSS}
#pwa-install-btn{{display:none;align-items:center;gap:4px;background:var(--bg3);border:1px solid var(--border);color:var(--mid);border-radius:16px;padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer}}
#pwa-install-btn:hover{{border-color:var(--teal);color:var(--teal)}}
</style>
</head>
<body>
<!-- Sidebar overlay for mobile -->
<div class="sb-overlay" id="sbOverlay" onclick="closeSidebar()"></div>
<div class="layout">
  <!-- Sidebar -->
  <nav class="sb" id="sidebar">
    <a href="/home" class="sb-logo" style="text-decoration:none">
      <span class="sb-logo-text">ArtheeNoi</span>
    </a>
    {nav_html}
    <div class="sb-spacer"></div>
    <div class="sb-bot">
      <a class="sb-link" href="/settings"><span class="sb-label" data-en="Settings" data-th="ตั้งค่า">Settings</span></a>
      {'<a class="sb-link" href="/admin"><span class="sb-label" data-en="Admin" data-th="แอดมิน">Admin</span></a>' if is_admin else ''}
      <a class="sb-link" href="/logout"><span class="sb-label" data-en="Logout" data-th="ออกจากระบบ">Logout</span></a>
    </div>
  </nav>
  <!-- Main -->
  <div class="main">
    <!-- Topbar -->
    <div class="topbar">
      <button class="hamburger" id="hamburger" onclick="toggleSidebar()" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
      <div class="topbar-search" style="position:relative">
        <span class="topbar-search-icon">🔍</span>
        <input type="text" placeholder="ค้นหา symbol... (Enter)" id="symSearch"
          autocomplete="off"
          oninput="onSearchInput(this.value)"
          onkeydown="onSearchKey(event)"
          onfocus="onSearchInput(this.value)"
          onblur="setTimeout(()=>document.getElementById('searchDrop').style.display='none',200)">
        <div id="searchDrop" class="search-dropdown" style="display:none"></div>
      </div>
      <div class="topbar-right">
        <span id="mktDot" class="mkt-dot mkt-closed"></span>
        <span id="mktLabel" style="font-size:11px;color:var(--mid)">Market</span>
        <span class="top-pill" id="thbRate">🇹🇭 ฿—</span>
        <span class="top-pill" id="mktTime">--:--</span>
        <button id="langBtn" onclick="toggleLang()" title="เปลี่ยนภาษา"
          style="background:transparent;border:1px solid var(--border);color:var(--mid);font-size:10px;font-weight:700;letter-spacing:1px;padding:4px 8px;border-radius:3px;cursor:pointer;font-family:inherit;transition:.12s"
          onmouseover="this.style.color='var(--text)';this.style.borderColor='#666'"
          onmouseout="this.style.color='var(--mid)';this.style.borderColor='var(--border)'">EN</button>
        <button id="pwa-install-btn" onclick="installPWA()" title="Install as App">📲 Install</button>
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
<!-- Bottom nav (mobile only) -->
<nav class="bottom-nav">
  <a href="/stocks" class="{'active' if page_id=='stocks' else ''}"><span class="bn-lbl">STOCKS</span></a>
  <a href="/charts" class="{'active' if page_id=='charts' else ''}"><span class="bn-lbl">CHARTS</span></a>
  <a href="/screener" class="{'active' if page_id=='screener' else ''}"><span class="bn-lbl">SCREEN</span></a>
  <a href="/alerts" class="{'active' if page_id=='alerts' else ''}"><span class="bn-lbl">ALERTS</span></a>
  <a href="/macro" class="{'active' if page_id=='macro' else ''}"><span class="bn-lbl">MACRO</span></a>
</nav>
<script>
// ── Sidebar toggle (mobile) ──────────────────────────────────────────
function toggleSidebar(){{
  const sb=document.getElementById('sidebar');
  const hb=document.getElementById('hamburger');
  const ov=document.getElementById('sbOverlay');
  const open=sb.classList.toggle('open');
  hb.classList.toggle('open',open);
  ov.classList.toggle('open',open);
}}
function closeSidebar(){{
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('hamburger').classList.remove('open');
  document.getElementById('sbOverlay').classList.remove('open');
}}
// Close sidebar when nav link clicked on mobile
document.addEventListener('DOMContentLoaded',()=>{{
  document.querySelectorAll('.sb-link').forEach(a=>a.addEventListener('click',()=>{{
    if(window.innerWidth<=768)closeSidebar();
  }}));
}});
// ── Global symbol search ─────────────────────────────────────────────
const _SEARCH_SYMS=[
  ['NVDA','NVIDIA'],['MSFT','Microsoft'],['AAPL','Apple'],['GOOGL','Alphabet'],
  ['META','Meta'],['AMZN','Amazon'],['TSLA','Tesla'],['AMD','AMD'],
  ['AVGO','Broadcom'],['MRVL','Marvell'],['INTC','Intel'],['TSM','TSMC'],
  ['NOW','ServiceNow'],['CRWD','CrowdStrike'],['SOFI','SoFi'],['VST','Vistra'],
  ['QQQ','Nasdaq ETF'],['IVV','S&P500 ETF'],['DIA','Dow ETF'],['SPY','S&P500 ETF'],
  ['BTC-USD','Bitcoin'],['ETH-USD','Ethereum'],['GC=F','Gold Futures'],['CL=F','Oil WTI'],
  ['CRWV','CoreWeave'],['SPCX','Space ETF'],['NOK','Nokia'],['ASTS','AST SpaceMobile'],
];
function onSearchInput(val){{
  const q=val.trim().toUpperCase();
  const drop=document.getElementById('searchDrop');
  if(!q){{drop.style.display='none';return;}}
  const matches=_SEARCH_SYMS.filter(([s,n])=>s.includes(q)||n.toUpperCase().includes(q)).slice(0,8);
  if(!matches.length){{drop.style.display='none';return;}}
  drop.innerHTML=matches.map(([s,n])=>`<div class="search-item" onmousedown="goSearch('${{s}}')"><span class="s-sym">${{s}}</span><span class="s-name">${{n}}</span></div>`).join('');
  drop.style.display='block';
}}
function onSearchKey(e){{
  if(e.key==='Enter'){{
    const q=document.getElementById('symSearch').value.trim().toUpperCase();
    if(q)goSearch(q);
  }}
  if(e.key==='Escape')document.getElementById('searchDrop').style.display='none';
}}
function goSearch(sym){{
  document.getElementById('symSearch').value=sym;
  document.getElementById('searchDrop').style.display='none';
  location.href='/charts?sym='+sym;
}}
// ── Clock ────────────────────────────────────────────────────────────
function updateClock(){{
  const now=new Date();
  document.getElementById('mktTime').textContent=now.toLocaleTimeString('th-TH',{{hour:'2-digit',minute:'2-digit'}});
}}
setInterval(updateClock,1000); updateClock();
// Market status
(function(){{
  const now=new Date();
  const est=new Date(now.toLocaleString('en-US',{{timeZone:'America/New_York'}}));
  const h=est.getHours(),m=est.getMinutes(),d=est.getDay();
  const open=d>=1&&d<=5&&(h>9||(h===9&&m>=30))&&h<16;
  document.getElementById('mktDot').className='mkt-dot '+(open?'mkt-open':'mkt-closed');
  document.getElementById('mktLabel').textContent=open?'Open':'Closed';
}})();
// Fetch THB rate
(function(){{
  fetch('/api/prices').then(r=>r.json()).then(d=>{{
    const thb=d._thb||35.0;
    document.getElementById('thbRate').textContent='🇹🇭 ฿'+thb.toFixed(1);
  }}).catch(()=>{{}});
}})();
// Live ticker auto-update every 30s
(function(){{
  function buildTickerItem(t){{
    const cls=t.chg>=0?'up':'dn', sign=t.chg>=0?'+':'';
    return `<div class="ticker-item"><span class="ticker-sym">${{t.label}}</span><span class="ticker-px">$${{t.price.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}</span><span class="ticker-chg ${{cls}}">${{sign}}${{t.chg.toFixed(2)}}%</span></div>`;
  }}
  function refreshTicker(){{
    fetch('/api/ticker').then(r=>r.json()).then(items=>{{
      if(!items||!items.length)return;
      const html=items.map(buildTickerItem).join('');
      const el=document.getElementById('tickerInner');
      if(el)el.innerHTML=html+html;
    }}).catch(()=>{{}});
  }}
  setInterval(refreshTicker, 30000);
}})();
{extra_js}
{_TOAST_JS}
// PWA install
let _installPrompt = null;
window.addEventListener('beforeinstallprompt', e => {{
  e.preventDefault(); _installPrompt = e;
  const btn = document.getElementById('pwa-install-btn');
  if (btn) btn.style.display = 'flex';
}});
function installPWA() {{
  if (_installPrompt) {{ _installPrompt.prompt(); _installPrompt = null; }}
}}

// ── Language switcher ──────────────────────────────────────────────
function applyLang(lang) {{
  document.querySelectorAll('[data-en][data-th]').forEach(el => {{
    el.textContent = lang === 'th' ? el.dataset.th : el.dataset.en;
  }});
  const btn = document.getElementById('langBtn');
  if (btn) btn.textContent = lang === 'th' ? 'EN' : 'TH';
  document.documentElement.lang = lang;
  localStorage.setItem('lang', lang);
}}
function toggleLang() {{
  const cur = localStorage.getItem('lang') || 'en';
  applyLang(cur === 'th' ? 'en' : 'th');
}}
(function(){{
  const saved = localStorage.getItem('lang') || 'en';
  if (saved === 'th') applyLang('th');
}})();
</script>
<nav class="bottom-nav" style="display:none">
  <a href="/stocks" class="{bn_stocks}">STOCKS</a>
  <a href="/charts" class="{bn_charts}">CHARTS</a>
  <a href="/screener" class="{bn_screen}">SCREEN</a>
  <a href="/scanner" class="{bn_scanner}">SCAN</a>
  <a href="/chat" class="{bn_chat}">CHAT</a>
</nav>
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

def _get_vault_sector(sym: str) -> str:
    """Look up sector from VAULT for a symbol."""
    try:
        import at_stock_vault as v
        for item in v.VAULT:
            if item.get("t", "").upper() == sym.upper():
                return item.get("s", "Other")
    except Exception:
        pass
    return "Other"

def _sector_allocation_html(port_rows: list, total_val: float) -> str:
    """Build sector allocation horizontal bars."""
    if not port_rows or total_val <= 0:
        return ""
    sectors: dict = {}
    for r in port_rows:
        sec = _get_vault_sector(r["sym"])
        sectors[sec] = sectors.get(sec, 0) + r["val"]
    sorted_sec = sorted(sectors.items(), key=lambda x: -x[1])
    colors = ["var(--teal)","var(--blue)","var(--purple)","var(--gold)","var(--green)","var(--orange)","var(--red)"]
    rows = ""
    for i, (sec, val) in enumerate(sorted_sec):
        pct = val / total_val * 100
        col = colors[i % len(colors)]
        rows += f"""<div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px">
            <span style="color:var(--mid)">{sec}</span>
            <span style="color:var(--text);font-weight:700">${val:,.0f} <span style="color:var(--muted)">({pct:.0f}%)</span></span>
          </div>
          <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden">
            <div style="height:100%;width:{pct:.1f}%;background:{col};border-radius:3px;transition:width .4s"></div>
          </div>
        </div>"""
    return f'<div class="card" style="margin-bottom:16px"><div class="card-hdr">🏭 Sector Allocation</div>{rows}</div>'

def _portfolio_health_html(port_rows: list, total_val: float, total_cost: float) -> str:
    """Compute and display portfolio health score 0-100."""
    if not port_rows:
        return ""
    # --- Diversification (0-30) ---
    sectors = set(_get_vault_sector(r["sym"]) for r in port_rows)
    n_sec = len(sectors)
    max_alloc = max((r["val"] / total_val * 100 for r in port_rows), default=0) if total_val else 0
    div_score = min(n_sec * 5, 20)
    if max_alloc > 40:
        div_score -= 10
    elif max_alloc > 60:
        div_score -= 20
    div_score = max(0, min(30, div_score))

    # --- RSI health (0-25) ---
    rsis = [r["rsi"] for r in port_rows if r.get("rsi") is not None]
    avg_rsi = sum(rsis) / len(rsis) if rsis else 50
    if 35 <= avg_rsi <= 65:
        rsi_score = 25
    elif 30 <= avg_rsi < 35 or 65 < avg_rsi <= 70:
        rsi_score = 15
    else:
        rsi_score = 5
    rsi_score = max(0, min(25, rsi_score))

    # --- Momentum: % above MA20 (0-25) ---
    above_ma20 = 0
    for r in port_rows:
        cl = r.get("closes", [])
        ma20 = sum(cl[-20:]) / 20 if len(cl) >= 20 else None
        if ma20 and r["price"] > ma20:
            above_ma20 += 1
    mom_pct = above_ma20 / len(port_rows) * 100 if port_rows else 50
    mom_score = int(mom_pct / 100 * 25)

    # --- P&L trend (0-20) ---
    total_pnl = sum(r["pnl"] for r in port_rows)
    pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    if pnl_pct > 5:
        pnl_score = 20
    elif pnl_pct > 0:
        pnl_score = 14
    elif pnl_pct > -5:
        pnl_score = 8
    else:
        pnl_score = 2

    total_score = div_score + rsi_score + mom_score + pnl_score
    if total_score >= 80:
        emoji = "🟢"; grade = "Excellent"; col = "var(--green)"
    elif total_score >= 60:
        emoji = "🟡"; grade = "Good"; col = "var(--gold)"
    elif total_score >= 40:
        emoji = "🟠"; grade = "Fair"; col = "var(--orange)"
    else:
        emoji = "🔴"; grade = "Weak"; col = "var(--red)"

    return f"""<div class="card" style="margin-bottom:16px;border-top:3px solid {col}">
  <div class="card-hdr">💪 Portfolio Health</div>
  <div style="display:flex;align-items:center;gap:20px">
    <div style="text-align:center">
      <div style="font-size:40px;font-weight:900;color:{col};line-height:1">{total_score}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:2px">/100</div>
      <div style="font-size:13px;font-weight:700;color:{col};margin-top:4px">{emoji} {grade}</div>
    </div>
    <div style="flex:1;font-size:12px;line-height:2;color:var(--mid)">
      🏭 Diversification &nbsp;<b style="color:var(--text)">{div_score}/30</b> — {n_sec} sectors, max {max_alloc:.0f}% in one stock<br>
      📊 RSI Health &nbsp;<b style="color:var(--text)">{rsi_score}/25</b> — avg RSI {avg_rsi:.0f}<br>
      🚀 Momentum &nbsp;<b style="color:var(--text)">{mom_score}/25</b> — {above_ma20}/{len(port_rows)} stocks above MA20<br>
      💰 P&L Trend &nbsp;<b style="color:var(--text)">{pnl_score}/20</b> — {'+' if pnl_pct>=0 else ''}{pnl_pct:.1f}% overall
    </div>
  </div>
</div>"""

def home_page(user: dict, market_data: dict, macro: dict) -> str:
    """Dashboard home — top movers + market pulse + quick links."""
    display = user.get("display_name", "User")
    mkt = market_data or {}

    # ── Top movers from market cache ──────────────────────────────────
    INDEX_SYMS = {"QQQ", "SPY", "DIA", "IVV", "VTI", "^GSPC", "^DJI", "^IXIC"}
    movers = []
    for sym, d in mkt.items():
        if sym in INDEX_SYMS:
            continue
        chg = d.get("chg") or 0
        price = d.get("price") or 0
        if price > 0:
            movers.append((sym, chg, price, d.get("name", sym)))

    gainers = sorted(movers, key=lambda x: x[1], reverse=True)[:5]
    losers  = sorted(movers, key=lambda x: x[1])[:5]

    def mover_row(sym, chg, price, name):
        col = "var(--green)" if chg >= 0 else "var(--red)"
        sign = "+" if chg >= 0 else ""
        short = name[:18] + "…" if len(name) > 18 else name
        return f"""<div style="display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--border)">
          <div>
            <span style="font-size:12px;font-weight:700;color:var(--text);letter-spacing:.5px">{sym}</span>
            <span style="font-size:10px;color:var(--muted);margin-left:6px">{short}</span>
          </div>
          <div style="text-align:right">
            <span style="font-size:13px;font-weight:700;color:{col}">{sign}{chg:.2f}%</span>
            <span style="font-size:10px;color:var(--muted);display:block">${price:,.2f}</span>
          </div>
        </div>"""

    gainers_html = "".join(mover_row(*g) for g in gainers) or "<p style='color:var(--muted);font-size:12px'>— No data —</p>"
    losers_html  = "".join(mover_row(*g) for g in losers)  or "<p style='color:var(--muted);font-size:12px'>— No data —</p>"

    # ── Index pulse ────────────────────────────────────────────────────
    index_cards = ""
    for sym, label in [("SPY","S&P 500"), ("QQQ","NASDAQ"), ("DIA","DOW"), ("GC=F","Gold")]:
        d = mkt.get(sym, {})
        chg = d.get("chg") or 0
        price = d.get("price") or 0
        col = "var(--green)" if chg >= 0 else "var(--red)"
        sign = "+" if chg >= 0 else ""
        index_cards += f"""<div class="card-sm" style="text-align:center;padding:16px 12px">
          <div style="font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px">{label}</div>
          <div style="font-size:20px;font-weight:900;color:var(--text)">${price:,.2f}</div>
          <div style="font-size:13px;font-weight:700;color:{col};margin-top:4px">{sign}{chg:.2f}%</div>
        </div>"""

    # ── Quick nav tiles ────────────────────────────────────────────────
    quick = [
        ("/stocks",    "STOCKS",    "Portfolio & watchlist"),
        ("/charts",    "CHARTS",    "Technical analysis"),
        ("/gold",      "GOLD",      "XAU/USD · Thai price"),
        ("/news",      "NEWS",      "Market headlines"),
        ("/screener",  "SCREENER",  "Filter stocks"),
        ("/signals",   "SIGNALS",   "Buy/sell signals"),
        ("/crypto",    "CRYPTO",    "BTC ETH & more"),
        ("/macro",     "MACRO",     "Fed · VIX · DXY"),
    ]
    tiles_html = ""
    for href, title, sub in quick:
        tiles_html += f"""<a href="{href}" style="display:block;text-decoration:none">
          <div class="card-sm" style="padding:16px;transition:.12s" onmouseover="this.style.borderColor='var(--text)'" onmouseout="this.style.borderColor='var(--border)'">
            <div style="font-size:11px;font-weight:700;color:var(--text);letter-spacing:1.5px">{title}</div>
            <div style="font-size:10px;color:var(--muted);margin-top:4px">{sub}</div>
          </div>
        </a>"""

    content = f"""
<div style="max-width:1100px;margin:0 auto;padding:24px 0">

  <!-- Header -->
  <div style="margin-bottom:28px">
    <div style="font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase">Dashboard</div>
    <div style="font-size:28px;font-weight:900;color:var(--text);letter-spacing:-1px;margin-top:4px">Welcome, {display}</div>
  </div>

  <!-- Index pulse -->
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:28px">
    {index_cards}
  </div>

  <!-- Movers -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px">
    <div class="card">
      <div class="card-hdr" style="margin-bottom:4px">TOP GAINERS</div>
      {gainers_html}
    </div>
    <div class="card">
      <div class="card-hdr" style="margin-bottom:4px">TOP LOSERS</div>
      {losers_html}
    </div>
  </div>

  <!-- Quick nav -->
  <div style="font-size:10px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">Quick Access</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">
    {tiles_html}
  </div>

</div>"""

    return _base("home", "Home", content, user)


def stocks_page(user: dict, market_data: dict, macro: dict, thb: float) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    # Multi-portfolio selector HTML
    portfolios = user.get("portfolios")
    active_port_name = user.get("active_portfolio", "default")
    port_selector_html = ""
    if portfolios and isinstance(portfolios, dict):
        opts = "".join(
            f'<option value="{n}" {"selected" if n == active_port_name else ""}>{n}</option>'
            for n in portfolios
        )
        port_selector_html = f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">
  <span style="font-size:12px;color:var(--mid)">📁 Portfolio:</span>
  <form method="POST" action="/portfolio/switch" style="display:flex;gap:6px;align-items:center">
    <select name="name" onchange="this.form.submit()" style="font-size:12px;padding:4px 8px;border-radius:4px;background:var(--bg3);border:1px solid var(--border);color:var(--text)">
      {opts}
    </select>
  </form>
  <button onclick="document.getElementById('new-port-modal').style.display='flex'" class="btn btn-ghost btn-sm">＋ New</button>
  {'<form method="POST" action="/portfolio/delete-port" style="display:inline" onsubmit="return confirm(\'ลบ portfolio นี้?\')">'
   + f'<input type="hidden" name="name" value="{active_port_name}">'
   + '<button class="btn btn-danger btn-sm" type="submit">🗑</button></form>' if active_port_name != "default" else ""}
</div>
<div id="new-port-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:999;align-items:center;justify-content:center" onclick="if(event.target===this)this.style.display='none'">
  <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:28px;width:320px">
    <div style="font-weight:700;margin-bottom:14px">📁 สร้าง Portfolio ใหม่</div>
    <form method="POST" action="/portfolio/new" style="display:flex;flex-direction:column;gap:10px">
      <input name="name" placeholder="ชื่อ portfolio เช่น trading" autofocus>
      <div style="display:flex;gap:8px">
        <button type="submit" class="btn btn-primary" style="flex:1">สร้าง</button>
        <button type="button" class="btn btn-ghost" onclick="document.getElementById('new-port-modal').style.display='none'">ยกเลิก</button>
      </div>
    </form>
  </div>
</div>"""

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
          <td id="price-{r['sym']}" data-price="{r['price']}">${r['price']:,.2f}</td>
          <td id="chg-{r['sym']}" class="{cc}">{cs}{r['chg']:.2f}%</td>
          <td id="rsi-{r['sym']}">{_rsi_bar(r.get('rsi'))}</td>
          <td>{r['shares']}×${r['cost']}</td>
          <td class="{pc}">{ps}${r['pnl']:,.0f} <span style="font-size:10px;color:var(--muted)">({ps}{r['pnl_pct']:.1f}%)</span></td>
          <td class="{pc}" style="font-weight:700">{ps}฿{abs(r['pnl_thb']):,.0f}</td>
          <td><canvas id="{sp_id}" class="spark"></canvas></td>
          <td><a href="/chart/{r['sym']}" class="btn btn-ghost btn-sm" title="View Chart">📉</a></td>
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
        rng = (d.get("high", 0) - d.get("low", 0)) if d.get("high") and d.get("low") else 1
        pct_range = (d["price"] - d.get("low", 0)) / rng * 100 if rng else 50

        wl_cards += f"""
        <div class="card-sm" style="cursor:default">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
            <div>
              <div style="font-weight:800;font-size:15px">{sym}</div>
              <div id="price-{sym}" data-price="{d['price']}" style="color:var(--muted);font-size:11px;margin-top:1px">${d['price']:,.2f}</div>
            </div>
            {_signal_badge(action)}
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:8px">
            <span id="chg-{sym}" style="font-size:12px;color:{chg_col};font-weight:700">{chg_s}{chg:.2f}%</span>
            <span style="font-size:11px;color:var(--muted)">RSI <b id="rsi-{sym}" style="color:{rsi_col}">{rsi or '—'}</b></span>
          </div>
          <div class="pbar"><div class="pbar-fill" style="width:{pct_range:.0f}%;background:var(--teal)"></div></div>
          <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:10px;color:var(--muted)">
            <span>L ${d.get('low') or 0:,.0f}</span><span>52W range</span><span>H ${d.get('high') or 0:,.0f}</span>
          </div>
          <div style="margin-top:10px;text-align:right">
            <a href="/chart/{sym}" class="btn btn-ghost btn-sm">📉 Chart</a>
          </div>
        </div>"""

    html = f"""
{port_selector_html}
<!-- Live indicator -->
<div style="display:flex;align-items:center;margin-bottom:12px">
  <span style="font-size:13px;font-weight:700;color:var(--text)">📊 Stocks Dashboard {'— ' + active_port_name if portfolios else ''}</span>
  <span id="live-timer" style="font-size:11px;color:var(--mid);background:var(--bg3);padding:3px 8px;border-radius:4px;margin-left:8px">🟢 Live · Updates in 60s</span>
</div>

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

<!-- Portfolio Value History Chart -->
<div class="card" style="margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div class="card-hdr" style="margin-bottom:0">📈 Portfolio Value History</div>
    <span style="font-size:11px;color:var(--muted)" id="hist-status">กำลังโหลด...</span>
  </div>
  <div style="position:relative;height:160px;width:100%;overflow:hidden">
    <canvas id="portHistChart" style="display:block"></canvas>
  </div>
</div>

<!-- ETF Cards -->
<div class="g3" style="margin-bottom:16px">{etf_cards}</div>

<!-- Portfolio Health + Sector Allocation -->
<div class="g2" style="margin-bottom:16px">
  <div>{_portfolio_health_html(port_rows, total_val, total_cost)}</div>
  <div>{_sector_allocation_html(port_rows, total_val)}</div>
</div>

<!-- Attribution + Economic Calendar -->
<div class="g2" style="margin-bottom:16px">
  <div>{_portfolio_attribution_html(port_rows)}</div>
  <div>{_econ_calendar_widget()}</div>
</div>

<!-- Rebalancing Advisor -->
{_rebalancing_html(port_rows, total_val, user)}

<!-- Portfolio -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">📊 My Portfolio</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr>
        <th>Symbol</th><th>Price</th><th>Today</th><th>RSI</th><th>Position</th><th>P&L (USD)</th><th>P&L (THB)</th><th>30D</th><th></th>
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

// Auto-refresh prices every 60 sec with countdown
let _countdown = 60;
function _startCountdown() {{
  const el = document.getElementById('live-timer');
  clearInterval(window._cdTimer);
  _countdown = 60;
  window._cdTimer = setInterval(() => {{
    _countdown--;
    if (el) el.textContent = `Updates in ${{_countdown}}s`;
    if (_countdown <= 0) {{ clearInterval(window._cdTimer); _refreshPrices(); }}
  }}, 1000);
}}
function _flash(id, up) {{
  const el = document.getElementById(id);
  if (!el) return;
  el.style.transition = 'background 0.2s';
  el.style.background = up ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)';
  setTimeout(() => el.style.background = '', 1500);
}}
async function _refreshPrices() {{
  try {{
    const r = await fetch('/api/prices');
    const data = await r.json();
    for (const [sym, d] of Object.entries(data)) {{
      if (sym.startsWith('_')) continue;
      const priceEl = document.getElementById(`price-${{sym}}`);
      const chgEl   = document.getElementById(`chg-${{sym}}`);
      const rsiEl   = document.getElementById(`rsi-${{sym}}`);
      if (priceEl && d.price) {{
        const oldPrice = parseFloat(priceEl.dataset.price || '0');
        const up = d.price >= oldPrice;
        priceEl.textContent = `$${{d.price.toFixed(2)}}`;
        priceEl.dataset.price = d.price;
        if (oldPrice && Math.abs(d.price - oldPrice) > 0.001) _flash(`price-${{sym}}`, up);
      }}
      if (chgEl && d.chg !== undefined) {{
        const sign = d.chg >= 0 ? '+' : '';
        chgEl.textContent = `${{sign}}${{d.chg.toFixed(2)}}%`;
        chgEl.style.color = d.chg >= 0 ? 'var(--green)' : 'var(--red)';
      }}
      if (rsiEl && d.rsi) rsiEl.textContent = d.rsi.toFixed(1);
    }}
  }} catch(e) {{ console.warn('Price refresh error', e); }}
  _startCountdown();
}}
document.addEventListener('DOMContentLoaded', () => {{
  _startCountdown();
  // Load portfolio history chart
  fetch('/api/portfolio-history').then(r=>r.json()).then(d=>{{
    const snaps = d.snapshots || [];
    const el = document.getElementById('hist-status');
    if (!snaps.length) {{
      if (el) el.textContent = 'ยังไม่มีข้อมูล (จะเริ่มเก็บหลัง market refresh ครั้งแรก)';
      return;
    }}
    if (el) el.textContent = snaps.length + ' วัน';
    const labels = snaps.map(s=>s.date);
    const vals   = snaps.map(s=>s.value);
    const first  = vals[0] || 1;
    const last   = vals[vals.length-1] || 1;
    const up     = last >= first;
    const color  = up ? '#26a69a' : '#ef5350';
    const ctx    = document.getElementById('portHistChart').getContext('2d');
    new Chart(ctx, {{
      type: 'line',
      data: {{
        labels,
        datasets: [{{
          data: vals,
          borderColor: color,
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
          backgroundColor: ctx2 => {{
            const g = ctx2.chart.ctx.createLinearGradient(0,0,0,160);
            g.addColorStop(0, color+'44'); g.addColorStop(1, color+'00'); return g;
          }}
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: {{ legend: {{display:false}}, tooltip: {{
          mode:'index', intersect:false,
          callbacks: {{ label: ctx2 => `$${{ctx2.raw.toLocaleString()}}` }}
        }} }},
        scales: {{
          x: {{ ticks: {{ color:'#787b86', maxTicksLimit:8, font:{{size:10}} }}, grid:{{color:'#363a45'}} }},
          y: {{ ticks: {{ color:'#787b86', callback: v=>'$'+v.toLocaleString(), font:{{size:10}} }}, grid:{{color:'#363a45'}} }}
        }}
      }}
    }});
  }}).catch(()=>{{}});
}});
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

    src_lbl   = d.get("source", "metals.live")
    src_date  = d.get("date", "")

    # Thai gold (pre-loaded from cache — may be 0 if not yet fetched)
    thai_bar_buy  = d.get("thai_bar_buy",  0)
    thai_bar_sell = d.get("thai_bar_sell", 0)
    thai_orna_buy = d.get("thai_orna_buy", 0)
    thai_orna_sell= d.get("thai_orna_sell",0)

    thai_section = ""
    if thai_bar_sell:
        thai_section = f"""
<!-- Thai Gold Prices -->
<div class="card" style="margin-bottom:16px;border-top:3px solid #FFD700">
  <div class="card-hdr" style="display:flex;align-items:center;gap:8px">
    🇹🇭 ราคาทองคำไทย
    <span style="font-size:10px;background:rgba(255,215,0,.1);color:#FFD700;border:1px solid rgba(255,215,0,.3);border-radius:8px;padding:1px 7px" id="thaiGoldSrc">goldtraders.or.th</span>
    <span style="font-size:10px;color:var(--muted)" id="thaiGoldDate">{d.get("thai_date","")}</span>
  </div>
  <div class="g4" style="margin-top:12px">
    <div class="card-sm" style="text-align:center">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ทองแท่ง ซื้อ</div>
      <div style="font-size:20px;font-weight:800;color:var(--green)" id="thaiBarBuy">฿{thai_bar_buy:,.2f}</div>
      <div style="font-size:10px;color:var(--muted)">บาทน้ำหนัก</div>
    </div>
    <div class="card-sm" style="text-align:center">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ทองแท่ง ขาย</div>
      <div style="font-size:20px;font-weight:800;color:var(--red)" id="thaiBarSell">฿{thai_bar_sell:,.2f}</div>
      <div style="font-size:10px;color:var(--muted)">บาทน้ำหนัก</div>
    </div>
    <div class="card-sm" style="text-align:center">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ทองรูปพรรณ ซื้อ</div>
      <div style="font-size:20px;font-weight:800;color:var(--green)" id="thaiOrnasBuy">฿{thai_orna_buy:,.2f}</div>
      <div style="font-size:10px;color:var(--muted)">บาทน้ำหนัก</div>
    </div>
    <div class="card-sm" style="text-align:center">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ทองรูปพรรณ ขาย</div>
      <div style="font-size:20px;font-weight:800;color:var(--red)" id="thaiOrnasSell">฿{thai_orna_sell:,.2f}</div>
      <div style="font-size:10px;color:var(--muted)">บาทน้ำหนัก</div>
    </div>
  </div>
</div>"""

    html = f"""
<!-- Gold live refresh bar -->
<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap">
  <span style="font-size:12px;color:var(--muted)">แหล่งข้อมูล: <b style="color:var(--teal)">{src_lbl}</b> · <span id="goldSrcDate">{src_date}</span></span>
  <button class="btn btn-primary btn-sm" onclick="refreshGold(this)">🔄 ดึงราคาล่าสุด</button>
  <span id="goldRefreshStatus" style="font-size:11px;color:var(--muted)"></span>
</div>

{thai_section}

<!-- Gold Header -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--gold)">
    <div class="card-hdr">Gold (XAU/USD)</div>
    <div class="stat-val gold-c" id="goldPrice">${price:,.2f}</div>
    <div class="stat-lbl" id="goldChg" style="color:{chg_col}">{chg_s}{chg:.2f}% today</div>
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
      MA20 <b style="color:{'var(--green)' if ma20 and price>ma20 else 'var(--red)'}">{'$'+f'{ma20:,.0f}' if ma20 else '—'}</b><br>
      MA50 <b style="color:{'var(--green)' if ma50 and price>ma50 else 'var(--red)'}">{'$'+f'{ma50:,.0f}' if ma50 else '—'}</b>
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
    gold_js = """
const _gfmt=(n,dec=2)=>n.toLocaleString('th-TH',{minimumFractionDigits:dec,maximumFractionDigits:dec});

function refreshGold(){
  fetch('/api/gold-xau').then(r=>r.json()).then(d=>{
    if(!d.ok) return;
    const el=document.getElementById('goldPrice');
    if(el && d.price) el.textContent='$'+_gfmt(d.price);
    const sd=document.getElementById('goldSrcDate');
    if(sd) sd.textContent=d.date||'';
    document.getElementById('goldRefreshStatus').textContent=
      '🟢 '+d.date+' · $'+_gfmt(d.price)+'/oz (฿'+_gfmt(d.price_thb,0)+'/oz) ['+d.source+']';
  }).catch(()=>{});
}

function refreshThai(){
  fetch('/api/gold-thai').then(r=>r.json()).then(d=>{
    if(!d.ok||!d.thai_bar_sell) return;
    const upd=(id,v)=>{const e=document.getElementById(id);if(e&&v)e.textContent='฿'+_gfmt(v,2);};
    upd('thaiBarBuy',    d.thai_bar_buy);
    upd('thaiBarSell',   d.thai_bar_sell);
    upd('thaiOrnasBuy',  d.thai_orna_buy);
    upd('thaiOrnasSell', d.thai_orna_sell);
    const td=document.getElementById('thaiGoldDate');
    if(td) td.textContent=d.thai_date||'';
  }).catch(()=>{});
}

// XAU/USD refresh ทุก 5 วิ, Thai gold ทุก 30 วิ
refreshGold(); refreshThai();
setInterval(refreshGold, 5000);
setInterval(refreshThai, 30000);
"""
    return _base("gold", "Gold Analysis", html, user, "", gold_js)

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
      <div style="font-size:11px;color:var(--muted);margin-top:2px">MA20 = {'$'+f'{ma20:,.0f}' if ma20 else '—'}</div>
    </div>
    <div class="card-sm">
      <div style="font-size:11px;color:var(--muted)">Price vs MA50</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:{'var(--green)' if ma50 and price>ma50 else 'var(--red)'}">{'Above ↑' if ma50 and price>ma50 else 'Below ↓'}</div>
      <div style="font-size:11px;color:var(--muted);margin-top:2px">MA50 = {'$'+f'{ma50:,.0f}' if ma50 else '—'}</div>
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
    risk_col = "var(--red)" if risk >= 70 else "var(--gold)" if risk >= 45 else "var(--green)"

    def _f(v):
        try: return float(v)
        except: return 0.0
    def _fmt(v, dec=2):
        try: return f"{float(v):.{dec}f}"
        except: return "—"

    vix  = _fmt(macro.get("vix"),  2)
    yc   = _fmt(macro.get("yield_curve"), 2)
    rate = _fmt(macro.get("fed_rate"), 2)
    dxy  = _fmt(macro.get("dxy"),  2)

    html = f"""
<!-- ── AI News Brief ──────────────────────────────────────────── -->
<div class="card" style="margin-bottom:20px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <div>
      <div style="font-size:10px;color:var(--muted);letter-spacing:2px;text-transform:uppercase" data-en="AI Analysis" data-th="AI วิเคราะห์">AI Analysis</div>
      <div style="font-size:16px;font-weight:900;color:var(--text);margin-top:2px" data-en="Today's World News Analysis" data-th="วิเคราะห์ข่าวโลกวันนี้">Today's World News Analysis</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px">
      <span id="briefTs" style="font-size:10px;color:var(--muted)"></span>
      <button onclick="loadBrief(true)" class="btn btn-ghost btn-sm" id="briefBtn" data-en="Refresh" data-th="รีเฟรช">Refresh</button>
    </div>
  </div>
  <div id="briefLoading" style="color:var(--muted);font-size:13px;padding:20px 0;text-align:center;display:none"
       data-en="Analyzing news... may take 10-20 seconds" data-th="กำลังวิเคราะห์ข่าว... อาจใช้เวลา 10-20 วินาที">
    Analyzing news... may take 10-20 seconds
  </div>
  <div id="briefError" style="color:var(--red);font-size:12px;display:none"></div>
  <div id="briefContent" style="font-size:13px;line-height:1.85;color:var(--mid)">
    <div style="color:var(--muted);text-align:center;padding:16px 0" data-en="Click <b>Refresh</b> to analyze today's news with AI" data-th="คลิก รีเฟรช เพื่อให้ AI วิเคราะห์ข่าววันนี้">Click <b style="color:var(--text)">Refresh</b> to analyze today's news with AI</div>
  </div>
</div>

<!-- ── Market Pulse ───────────────────────────────────────────── -->
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:20px">
  <div class="card-sm" style="text-align:center">
    <div class="card-hdr">Risk Score</div>
    <div style="font-size:30px;font-weight:900;color:{risk_col}">{risk}</div>
    <div class="pbar" style="margin-top:8px"><div class="pbar-fill" style="width:{risk}%;background:{risk_col}"></div></div>
  </div>
  <div class="card-sm" style="text-align:center">
    <div class="card-hdr">VIX</div>
    <div style="font-size:24px;font-weight:900;color:{'var(--red)' if _f(vix)>25 else 'var(--green)'}">{vix}</div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">{'สูง — กลัว' if _f(vix)>25 else 'ต่ำ — สงบ' if _f(vix)<15 else 'ปานกลาง'}</div>
  </div>
  <div class="card-sm" style="text-align:center">
    <div class="card-hdr">Fed Rate</div>
    <div style="font-size:24px;font-weight:900;color:var(--text)">{rate}%</div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">Yield Curve {yc}</div>
  </div>
  <div class="card-sm" style="text-align:center">
    <div class="card-hdr">DXY</div>
    <div style="font-size:24px;font-weight:900;color:var(--text)">{dxy}</div>
    <div style="font-size:10px;color:var(--muted);margin-top:4px">Dollar Index</div>
  </div>
</div>

<!-- ── Raw Headlines ─────────────────────────────────────────── -->
<div class="card">
  <div class="card-hdr" style="margin-bottom:12px">Headlines วันนี้</div>
  {''.join(f"""<div style="padding:9px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
    <span style="font-size:12px;color:var(--mid);line-height:1.5">{n['title']}</span>
    <span style="font-size:10px;color:var(--muted);white-space:nowrap;flex-shrink:0">{n['source']}</span>
  </div>""" for n in news) or '<div style="color:var(--muted);font-size:12px">ดึงข่าวไม่ได้</div>'}
</div>

<script>
function parseBrief(text){{
  // Convert ## headers and plain text to styled HTML
  const lines = text.split('\\n');
  let html = '';
  for(const line of lines){{
    const trimmed = line.trim();
    if(!trimmed) {{ html += '<div style="height:8px"></div>'; continue; }}
    if(trimmed.startsWith('## ')){{
      html += `<div style="font-size:11px;font-weight:700;color:var(--text);letter-spacing:1.5px;text-transform:uppercase;margin:18px 0 6px;border-bottom:1px solid var(--border);padding-bottom:6px">${{trimmed.slice(3)}}</div>`;
    }} else {{
      html += `<div style="color:var(--mid);font-size:13px;line-height:1.8;margin-bottom:2px">${{trimmed}}</div>`;
    }}
  }}
  return html;
}}

function loadBrief(force=false){{
  const content = document.getElementById('briefContent');
  const loading = document.getElementById('briefLoading');
  const errDiv  = document.getElementById('briefError');
  const btn     = document.getElementById('briefBtn');
  const ts      = document.getElementById('briefTs');

  const lang = localStorage.getItem('lang') || 'en';
  loading.style.display = 'block';
  errDiv.style.display  = 'none';
  btn.disabled = true;
  btn.textContent = lang === 'th' ? 'กำลังโหลด...' : 'Loading...';

  let url = '/api/news-ai-brief?lang=' + lang;
  if (force) url += '&force=1';
  fetch(url)
    .then(r=>r.json())
    .then(d=>{{
      loading.style.display = 'none';
      btn.disabled = false;
      btn.dataset.en = 'Refresh'; btn.dataset.th = 'รีเฟรช';
      btn.textContent = lang === 'th' ? 'รีเฟรช' : 'Refresh';
      if(d.brief){{
        content.innerHTML = parseBrief(d.brief);
        ts.textContent = (lang==='th'?'อัปเดต ':'Updated ') + (d.updated||'') + (d.from_cache ? (lang==='th' ? ' (แคช)' : ' (cached)') : '');
        if(d.warn) errDiv.style.display='block', errDiv.textContent=d.warn;
      }} else {{
        errDiv.style.display = 'block';
        errDiv.textContent = d.error || 'เกิดข้อผิดพลาด';
        content.innerHTML = '<div style="color:var(--muted);font-size:12px;padding:12px 0">' + (lang==='th'?'ไม่สามารถโหลดการวิเคราะห์ได้':'Unable to load analysis') + '</div>';
      }}
    }})
    .catch(e=>{{
      loading.style.display = 'none';
      btn.disabled = false;
      btn.textContent = lang === 'th' ? 'รีเฟรช' : 'Refresh';
      errDiv.style.display = 'block';
      errDiv.textContent = lang === 'th' ? 'เครือข่ายขัดข้อง' : 'Network error';
    }});
}}

// Auto-load on page open
loadBrief();
</script>
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

# ─── DIVIDEND TRACKER PAGE ────────────────────────────────────────────────────

def dividends_page(user: dict, market_data: dict, thb: float) -> str:
    divs = user.get("dividends", [])
    port = user.get("portfolio", {})

    # Summary calculations
    total_usd = sum(d.get("total", 0) for d in divs)
    total_thb = total_usd * thb

    # Yield on cost
    total_cost = sum(
        float(port.get(sym, {}).get("cost", 0)) * float(port.get(sym, {}).get("shares", 0))
        for sym in port
    )
    yoc = (total_usd / total_cost * 100) if total_cost else 0

    # Annual run rate — last 12 months
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    annual_divs = [d for d in divs if d.get("date", "") >= cutoff]
    annual_rate = sum(d.get("total", 0) for d in annual_divs)

    # Dividend history table
    hist_rows = ""
    for i, d in enumerate(sorted(divs, key=lambda x: x.get("date", ""), reverse=True)):
        hist_rows += f"""
        <tr>
          <td>{d.get('date','—')}</td>
          <td><b>{d.get('sym','')}</b></td>
          <td>${d.get('amount_usd',0):.4f}</td>
          <td>{d.get('shares',0)}</td>
          <td><b>${d.get('total',0):.2f}</b></td>
          <td>฿{d.get('total',0)*thb:,.0f}</td>
          <td>
            <form method="POST" action="/dividends/delete" style="display:inline">
              <input type="hidden" name="idx" value="{divs.index(d) if d in divs else i}">
              <button class="btn btn-danger btn-sm">✕</button>
            </form>
          </td>
        </tr>"""

    # Monthly chart data
    monthly: dict = {}
    for d in divs:
        m = d.get("date", "")[:7]  # YYYY-MM
        if m:
            monthly[m] = monthly.get(m, 0) + d.get("total", 0)
    sorted_months = sorted(monthly.keys())[-12:]
    chart_labels = json.dumps(sorted_months)
    chart_data   = json.dumps([round(monthly.get(m, 0), 2) for m in sorted_months])

    # Per-stock estimated dividends from yfinance
    stock_yield_rows = ""
    for sym in list(port.keys())[:10]:  # limit to avoid slow loads
        try:
            import yfinance as yf
            t = yf.Ticker(sym)
            price = (market_data.get(sym) or {}).get("price", 0)
            info = t.fast_info
            annual_div = getattr(info, "last_annual_dividend_value", None) or 0
            div_yield = (annual_div / price * 100) if price and annual_div else 0
            shares = float(port.get(sym, {}).get("shares", 0))
            est_annual = annual_div * shares
            stock_yield_rows += f"""
            <tr>
              <td><b>{sym}</b></td>
              <td>${price:,.2f}</td>
              <td>${annual_div:.3f}</td>
              <td>{div_yield:.2f}%</td>
              <td>${est_annual:.2f} / yr</td>
            </tr>"""
        except Exception:
            pass

    # Add dividend form - preselect portfolio symbols
    port_opts = "".join(f'<option value="{s}">{s}</option>' for s in sorted(port.keys()))
    today = datetime.now().strftime("%Y-%m-%d")

    html = f"""
<!-- Summary Cards -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-top:3px solid var(--gold)">
    <div class="card-hdr">Total Dividends</div>
    <div class="stat-val gold-c">${total_usd:,.2f}</div>
    <div class="stat-lbl">฿{total_thb:,.0f}</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Yield on Cost</div>
    <div class="stat-val teal-c">{yoc:.2f}%</div>
    <div class="stat-lbl">Based on total cost</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Annual Run Rate</div>
    <div class="stat-val" style="color:var(--green)">${annual_rate:,.2f}</div>
    <div class="stat-lbl">Last 12 months</div>
  </div>
  <div class="card-sm">
    <div class="card-hdr">Records</div>
    <div class="stat-val">{len(divs)}</div>
    <div class="stat-lbl">Dividend entries</div>
  </div>
</div>

<!-- Add Dividend Form -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">➕ บันทึกเงินปันผลที่ได้รับ</div>
  <form method="POST" action="/dividends/add" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
    <div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">Symbol</div>
      <select name="sym" style="width:120px">
        {port_opts}
        <option value="">— พิมพ์เอง —</option>
      </select>
    </div>
    <div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">หรือพิมพ์ Symbol</div>
      <input name="sym_custom" placeholder="เช่น NVDA" style="width:100px" oninput="document.querySelector('[name=sym]').value=this.value.toUpperCase()">
    </div>
    <div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">วันที่</div>
      <input type="date" name="date" value="{today}" style="width:140px">
    </div>
    <div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">ปันผล/หุ้น (USD)</div>
      <input type="number" name="amount" step="0.0001" min="0" placeholder="0.04" style="width:120px">
    </div>
    <div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">จำนวนหุ้น</div>
      <input type="number" name="shares" step="0.01" min="0" placeholder="10" style="width:100px">
    </div>
    <button type="submit" class="btn btn-primary">บันทึก</button>
  </form>
</div>

<!-- Monthly Chart + History -->
<div class="g2" style="margin-bottom:16px">
  <div class="card">
    <div class="card-hdr">📊 Dividends รายเดือน (12M)</div>
    <canvas id="divChart" style="max-height:220px"></canvas>
  </div>
  <div class="card">
    <div class="card-hdr">📈 Estimated Annual Dividend (yfinance)</div>
    {'<div style="overflow-x:auto"><table class="tbl"><thead><tr><th>Symbol</th><th>Price</th><th>Div/Share</th><th>Yield</th><th>Est/yr</th></tr></thead><tbody>' + stock_yield_rows + '</tbody></table></div>' if stock_yield_rows else '<div style="color:var(--muted);font-size:13px">ไม่มีข้อมูล portfolio หรือหุ้นไม่จ่ายปันผล</div>'}
  </div>
</div>

<!-- History Table -->
<div class="card">
  <div class="card-hdr">📋 ประวัติเงินปันผลทั้งหมด</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>วันที่</th><th>Symbol</th><th>ต่อหุ้น</th><th>หุ้น</th><th>รวม USD</th><th>รวม THB</th><th></th></tr></thead>
      <tbody>{hist_rows or '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px">ยังไม่มีข้อมูลปันผล — กรอกด้านบนได้เลย</td></tr>'}</tbody>
    </table>
  </div>
</div>
"""
    js = f"""
const divCtx = document.getElementById('divChart');
if (divCtx) {{
  new Chart(divCtx, {{
    type: 'bar',
    data: {{
      labels: {chart_labels},
      datasets: [{{
        label: 'Dividends (USD)',
        data: {chart_data},
        backgroundColor: 'rgba(45,212,191,0.6)',
        borderColor: 'rgba(45,212,191,1)',
        borderWidth: 1,
        borderRadius: 4,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: ctx => '$'+ctx.raw.toFixed(2) }} }} }},
      scales: {{
        x: {{ ticks: {{ color: '#787b86', font: {{ size: 10 }} }}, grid: {{ color: '#363a45' }} }},
        y: {{ ticks: {{ color: '#787b86', callback: v => '$'+v }} , grid: {{ color: '#363a45' }} }}
      }}
    }}
  }});
}}
"""
    return _base("dividends", "Dividend Tracker", html, user, "", js)

# ─── TOOLS PAGE (Position Sizing + Calculators) ───────────────────────────────

def tools_page(user: dict, market_data: dict, thb: float) -> str:
    html = f"""
<!-- Position Sizing Calculator -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">🧮 Position Sizing Calculator</div>
  <div style="font-size:12px;color:var(--muted);margin-bottom:16px">คำนวณขนาด position จากความเสี่ยงที่รับได้ — ใส่ตัวเลขแล้วผลจะคำนวณทันที</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:16px">
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Account Size (USD)</label>
      <input type="number" id="ps_account" value="10000" oninput="calcPS()" style="width:100%">
    </div>
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Risk per Trade (%)</label>
      <input type="number" id="ps_risk" value="2" step="0.1" min="0.1" max="100" oninput="calcPS()" style="width:100%">
    </div>
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Entry Price (USD)</label>
      <input type="number" id="ps_entry" value="0" step="0.01" oninput="calcPS()" style="width:100%">
    </div>
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Stop Loss Price (USD)</label>
      <input type="number" id="ps_stop" value="0" step="0.01" oninput="calcPS()" style="width:100%">
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px" id="ps_results">
    <div class="card-sm" style="border-top:3px solid var(--red)">
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">Max Loss (USD)</div>
      <div id="ps_loss" style="font-size:22px;font-weight:800;color:var(--red)">—</div>
    </div>
    <div class="card-sm" style="border-top:3px solid var(--teal)">
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">Shares to Buy</div>
      <div id="ps_shares" style="font-size:22px;font-weight:800;color:var(--teal)">—</div>
    </div>
    <div class="card-sm" style="border-top:3px solid var(--blue)">
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">Position Value</div>
      <div id="ps_value" style="font-size:22px;font-weight:800;color:var(--blue)">—</div>
    </div>
    <div class="card-sm" style="border-top:3px solid var(--purple)">
      <div style="font-size:11px;color:var(--mid);margin-bottom:4px">% of Account</div>
      <div id="ps_pct" style="font-size:22px;font-weight:800;color:var(--purple)">—</div>
    </div>
  </div>
</div>

<!-- THB / USD Calculator -->
<div class="g2" style="margin-bottom:16px">
  <div class="card">
    <div class="card-hdr">💱 THB / USD Converter</div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:12px">อัตราปัจจุบัน: 1 USD = <b id="thb_rate" style="color:var(--teal)">฿{thb:.2f}</b></div>
    <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
      <input type="number" id="usd_in" placeholder="USD" oninput="document.getElementById('thb_out').value=(+this.value*{thb}).toFixed(2)" style="flex:1">
      <span style="color:var(--mid)">→</span>
      <input type="number" id="thb_out" placeholder="THB" oninput="document.getElementById('usd_in').value=(+this.value/{thb}).toFixed(4)" style="flex:1">
    </div>
    <div style="font-size:11px;color:var(--muted)">USD → THB ทันที</div>
  </div>

  <!-- Compound Return Calculator -->
  <div class="card">
    <div class="card-hdr">📈 Compound Return Calculator</div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
      <div>
        <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:3px">Principal (USD)</label>
        <input type="number" id="cp_principal" value="10000" oninput="calcCompound()" style="width:100%">
      </div>
      <div>
        <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:3px">Return/yr (%)</label>
        <input type="number" id="cp_rate" value="15" step="0.5" oninput="calcCompound()" style="width:100%">
      </div>
      <div>
        <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:3px">Years</label>
        <input type="number" id="cp_years" value="10" min="1" max="50" oninput="calcCompound()" style="width:100%">
      </div>
    </div>
    <canvas id="compoundChart" style="max-height:160px"></canvas>
    <div id="cp_result" style="margin-top:10px;font-size:13px;color:var(--mid)"></div>
  </div>
</div>

<!-- Quick Reference -->
<div class="card">
  <div class="card-hdr">📚 Position Sizing Rules of Thumb</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;font-size:13px">
    <div class="card-sm">
      <div style="font-weight:700;color:var(--teal);margin-bottom:6px">Conservative (1-2% risk)</div>
      <div style="color:var(--mid);line-height:1.8">เหมาะ: สวิง/ลงทุนระยะกลาง<br>Max drawdown: ~10-20%<br>ยอมรับขาดทุนต่อไม้ได้ดี</div>
    </div>
    <div class="card-sm">
      <div style="font-weight:700;color:var(--gold);margin-bottom:6px">Moderate (2-3% risk)</div>
      <div style="color:var(--mid);line-height:1.8">เหมาะ: นักเทรดมีประสบการณ์<br>Max drawdown: ~20-30%<br>ต้องระวัง drawdown ช่วง loss streak</div>
    </div>
    <div class="card-sm">
      <div style="font-weight:700;color:var(--red);margin-bottom:6px">Aggressive (&gt;3% risk)</div>
      <div style="color:var(--mid);line-height:1.8">ความเสี่ยงสูงมาก<br>ไม่แนะนำสำหรับมือใหม่<br>เสี่ยง blow up account</div>
    </div>
  </div>
</div>
"""
    js = """
function calcPS() {
  const account = +document.getElementById('ps_account').value || 0;
  const riskPct = +document.getElementById('ps_risk').value || 0;
  const entry   = +document.getElementById('ps_entry').value || 0;
  const stop    = +document.getElementById('ps_stop').value || 0;
  if (!account || !riskPct || !entry || !stop || entry <= stop) {
    ['ps_loss','ps_shares','ps_value','ps_pct'].forEach(id => document.getElementById(id).textContent = '—');
    return;
  }
  const riskAmt = account * riskPct / 100;
  const riskPerShare = Math.abs(entry - stop);
  const shares = riskAmt / riskPerShare;
  const posValue = shares * entry;
  const pctAccount = posValue / account * 100;
  document.getElementById('ps_loss').textContent = '$' + riskAmt.toFixed(2);
  document.getElementById('ps_shares').textContent = shares.toFixed(2) + ' shares';
  document.getElementById('ps_value').textContent = '$' + posValue.toFixed(2);
  document.getElementById('ps_pct').textContent = pctAccount.toFixed(1) + '%';
}

let _compoundChart = null;
function calcCompound() {
  const p = +document.getElementById('cp_principal').value || 0;
  const r = +document.getElementById('cp_rate').value || 0;
  const y = Math.min(+document.getElementById('cp_years').value || 0, 50);
  const labels = [], data = [];
  for (let i = 0; i <= y; i++) {
    labels.push('Y' + i);
    data.push(+(p * Math.pow(1 + r/100, i)).toFixed(2));
  }
  const final = data[data.length - 1];
  const gain = final - p;
  document.getElementById('cp_result').innerHTML =
    `เงิน <b style="color:var(--teal)">$${p.toLocaleString()}</b> หลัง <b>${y} ปี</b> @ <b>${r}%/yr</b> = <b style="color:var(--green);font-size:15px">$${final.toLocaleString()}</b> (กำไร $${gain.toLocaleString()})`;
  const ctx = document.getElementById('compoundChart');
  if (_compoundChart) _compoundChart.destroy();
  _compoundChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: '#2dd4bf',
        backgroundColor: 'rgba(45,212,191,0.15)',
        fill: true,
        tension: 0.4,
        pointRadius: 2,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => '$'+ctx.raw.toLocaleString() } } },
      scales: {
        x: { ticks: { color: '#787b86', font: { size: 10 } }, grid: { color: '#363a45' } },
        y: { ticks: { color: '#787b86', callback: v => '$'+v.toLocaleString() }, grid: { color: '#363a45' } }
      }
    }
  });
}
document.addEventListener('DOMContentLoaded', () => { calcPS(); calcCompound(); });
"""
    return _base("tools", "Trading Tools", html, user, "", js)

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
        if isinstance(p, str):
            sym = p; action = "WATCH"; sector = ""; score = 0
        else:
            sym    = p.get("sym") or p.get("t", "")
            action = p.get("action", "NEUTRAL")
            sector = p.get("sector") or p.get("s", "")
            score  = p.get("ai_score") or 0
        d      = market_data.get(sym, {})
        price  = d.get("price", 0)
        chg    = d.get("change_pct") or d.get("chg") or 0
        rsi    = d.get("rsi")
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
            <div style="font-size:22px;font-weight:900;color:{'var(--teal)' if (score or 0)>=70 else 'var(--gold)' if (score or 0)>=50 else 'var(--muted)'}">{score or '—'}</div>
            {pct52}
          </td>
          <td>{_action_badge(action)}</td>
          <td><button class="btn-qadd" onclick="quickAdd('{sym}',{price:.2f})">+ Add</button></td>
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
          <td><span style="color:{'var(--green)' if chg>=0 else 'var(--red)'};font-size:12px">{'+' if chg>=0 else ''}{(chg if price else 0.0):.2f}%</span></td>
          <td>{_rsi_bar(rsi) if rsi else '<span style="color:var(--muted)">—</span>'}</td>
          <td style="font-size:11px;color:var(--muted)">{e.get('note','')[:40]}</td>
          <td><button class="btn-qadd" onclick="quickAdd('{e['t']}',{price:.2f})">+ Add</button></td>
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
<div style="display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:0;flex-wrap:wrap">
  <button class="tab active" id="tabPicks"  onclick="showTab('picks')">🎯 Top Picks ({len(picks)})</button>
  <button class="tab" id="tabAll"           onclick="showTab('all')">🔭 Browse All ({summary['total']})</button>
  <button class="tab" id="tabUnder"         onclick="showTab('under')">👀 Under Radar ({len(tier3)})</button>
  <button class="tab" id="tabSect"          onclick="showTab('sect')">📊 Sectors</button>
  <button class="tab" id="tabCustom"        onclick="showTab('custom')">⚙️ Custom Filter</button>
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
          <th>Symbol</th><th>Sector</th><th>Tier</th><th>ราคา</th><th>วันนี้</th><th>RSI</th><th>AI Score</th><th>Action</th><th>Add</th>
        </tr></thead>
        <tbody>{picks_rows or '<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:24px">กำลังโหลด Vault picks... (ใช้เวลา 2-3 นาทีหลัง refresh)</td></tr>'}</tbody>
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
          <th>Symbol</th><th>Company</th><th>Sector</th><th>Tier</th><th>ราคา</th><th>วันนี้</th><th>RSI</th><th>Note</th><th>Add</th>
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

<!-- Tab: Custom Filter -->
<div id="paneCustom" style="display:none">
  <div class="card" style="margin-bottom:12px">
    <div class="card-hdr">⚙️ Custom Screener — ตั้ง filter เอง</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:14px">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">RSI min</div>
        <input type="number" id="cf-rsi-min" placeholder="0" min="0" max="100" style="width:100%">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">RSI max</div>
        <input type="number" id="cf-rsi-max" placeholder="100" min="0" max="100" style="width:100%">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Change % min</div>
        <input type="number" id="cf-chg-min" placeholder="-99" step="0.1" style="width:100%">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Change % max</div>
        <input type="number" id="cf-chg-max" placeholder="99" step="0.1" style="width:100%">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Sector</div>
        <select id="cf-sector" style="width:100%">
          <option value="">All Sectors</option>
          {''.join(f'<option value="{s}">{s}</option>' for s in sorted({e['s'] for e in VAULT}))}
        </select>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Tier</div>
        <select id="cf-tier" style="width:100%">
          <option value="">All Tiers</option>
          <option value="1">🔵 Blue-chip</option>
          <option value="2">🟡 Growth</option>
          <option value="3">🔴 Under Radar</option>
        </select>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Signal</div>
        <select id="cf-signal" style="width:100%">
          <option value="">All Signals</option>
          <option value="BUY">BUY</option>
          <option value="WATCH">WATCH</option>
          <option value="WAIT">WAIT</option>
          <option value="NEUTRAL">NEUTRAL</option>
          <option value="AVOID">AVOID</option>
        </select>
      </div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <button class="btn btn-primary" onclick="runCustomFilter()">🔍 Filter</button>
      <button class="btn btn-ghost" onclick="clearCustomFilter()">✕ Clear</button>
      <span id="cf-count" style="font-size:12px;color:var(--muted)"></span>
    </div>
  </div>
  <div class="card">
    <div style="overflow-x:auto">
    <table class="tbl" id="cf-results-table">
      <thead><tr>
        <th>Symbol</th><th>Sector</th><th>Tier</th><th>ราคา</th><th>วันนี้</th><th>RSI</th><th>Signal</th><th>Add</th>
      </tr></thead>
      <tbody id="cf-results"><tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">กด Filter เพื่อค้นหา</td></tr></tbody>
    </table>
    </div>
  </div>
</div>

<!-- Quick-Add Modal -->
<div id="qadd-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:500;align-items:center;justify-content:center">
  <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:24px;width:320px;max-width:90vw">
    <div style="font-size:16px;font-weight:700;margin-bottom:16px">➕ Add to Portfolio</div>
    <form method="POST" action="/portfolio/add-quick">
      <input type="hidden" name="sym" id="qadd-sym">
      <div style="margin-bottom:12px">
        <label style="font-size:12px;color:var(--mid)">Symbol</label>
        <div id="qadd-sym-display" style="font-size:20px;font-weight:800;color:var(--teal);margin-top:4px"></div>
      </div>
      <div style="margin-bottom:12px">
        <label style="font-size:12px;color:var(--mid)">Shares</label>
        <input type="number" name="shares" min="0.001" step="0.001" required placeholder="e.g. 10" style="margin-top:4px;width:100%">
      </div>
      <div style="margin-bottom:16px">
        <label style="font-size:12px;color:var(--mid)">Cost per share (USD)</label>
        <input type="number" name="cost" id="qadd-cost" min="0.01" step="0.01" required placeholder="e.g. 202.81" style="margin-top:4px;width:100%">
      </div>
      <div style="display:flex;gap:8px">
        <button type="submit" class="btn btn-primary" style="flex:1">Add to Portfolio</button>
        <button type="button" class="btn btn-secondary" onclick="document.getElementById('qadd-modal').style.display='none'">Cancel</button>
      </div>
    </form>
  </div>
</div>
"""

    js = """
// Quick-Add to portfolio
function quickAdd(sym, price) {
  document.getElementById('qadd-sym').value = sym;
  document.getElementById('qadd-sym-display').textContent = sym;
  document.getElementById('qadd-cost').value = price || '';
  document.getElementById('qadd-modal').style.display = 'flex';
}
// Tab switching
function showTab(name) {
  ['picks','all','under','sect','custom'].forEach(t => {
    document.getElementById('pane'+t.charAt(0).toUpperCase()+t.slice(1)).style.display = t===name?'':'none';
    const btn = document.getElementById('tab'+t.charAt(0).toUpperCase()+t.slice(1));
    if(btn) btn.classList.toggle('active', t===name);
  });
}

// Custom screener filter
const _VAULT_DATA = {vault_data_json};
function runCustomFilter() {{
  const rsiMin  = parseFloat(document.getElementById('cf-rsi-min').value)  || 0;
  const rsiMax  = parseFloat(document.getElementById('cf-rsi-max').value)  || 100;
  const chgMin  = parseFloat(document.getElementById('cf-chg-min').value);
  const chgMax  = parseFloat(document.getElementById('cf-chg-max').value);
  const sector  = document.getElementById('cf-sector').value;
  const tier    = document.getElementById('cf-tier').value;
  const signal  = document.getElementById('cf-signal').value;
  const results = _VAULT_DATA.filter(s => {{
    if (s.rsi === null) return false;
    if (s.rsi < rsiMin || s.rsi > rsiMax) return false;
    if (!isNaN(chgMin) && s.chg < chgMin) return false;
    if (!isNaN(chgMax) && s.chg > chgMax) return false;
    if (sector && s.sector !== sector) return false;
    if (tier && String(s.tier) !== tier) return false;
    if (signal && s.signal !== signal) return false;
    return true;
  }});
  document.getElementById('cf-count').textContent = results.length + ' หุ้นที่ตรงเงื่อนไข';
  const tierCols = {{'1':'var(--blue)','2':'var(--gold)','3':'var(--red)'}};
  const tierLabels = {{'1':'🔵 Blue-chip','2':'🟡 Growth','3':'🔴 Under Radar'}};
  document.getElementById('cf-results').innerHTML = results.slice(0,100).map(s => {{
    const pc = s.chg >= 0 ? 'var(--green)' : 'var(--red)';
    const rsic = s.rsi >= 70 ? '#ef4444' : s.rsi <= 30 ? '#22c55e' : '#f59e0b';
    const sigcls = s.signal==='BUY'?'badge-buy':s.signal==='AVOID'?'badge-avoid':s.signal==='WATCH'?'badge-watch':'badge-neutral';
    return `<tr>
      <td><b>${{s.sym}}</b></td>
      <td style="font-size:11px;color:var(--muted)">${{s.sector}}</td>
      <td style="font-size:11px;color:${{tierCols[s.tier]||'var(--mid)'}}"><b>${{tierLabels[s.tier]||''}}</b></td>
      <td>${{s.price?'$'+s.price.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}}):'—'}}</td>
      <td style="color:${{pc}}">${{s.chg>=0?'+':''}}${{s.chg.toFixed(2)}}%</td>
      <td style="color:${{rsic}};font-weight:700">${{s.rsi||'—'}}</td>
      <td><span class="badge ${{sigcls}}">${{s.signal}}</span></td>
      <td><button class="btn-qadd" onclick="quickAdd('${{s.sym}}',${{s.price||0}})">+ Add</button></td>
    </tr>`;
  }}).join('') || '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">ไม่พบหุ้นที่ตรงเงื่อนไข</td></tr>';
}}
function clearCustomFilter() {{
  ['cf-rsi-min','cf-rsi-max','cf-chg-min','cf-chg-max'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('cf-sector').value='';
  document.getElementById('cf-tier').value='';
  document.getElementById('cf-signal').value='';
  document.getElementById('cf-count').textContent='';
  document.getElementById('cf-results').innerHTML='<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">กด Filter เพื่อค้นหา</td></tr>';
}}
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

    # Build vault data JSON for custom screener
    vault_data = []
    for e in VAULT:
        d = market_data.get(e["t"], {})
        price = d.get("price", 0)
        chg   = d.get("change_pct") or d.get("chg") or 0
        closes = d.get("closes", [])
        rsi = _calc_rsi(closes) if len(closes) >= 15 else d.get("rsi")
        # simple signal from RSI
        sig = "BUY" if (rsi and rsi <= 35) else "WATCH" if (rsi and rsi <= 45) else "AVOID" if (rsi and rsi >= 75) else "WAIT" if (rsi and rsi >= 65) else "NEUTRAL"
        vault_data.append({
            "sym": e["t"], "sector": e.get("s",""), "tier": e.get("tier", 2),
            "price": round(price, 2), "chg": round(chg, 2),
            "rsi": round(rsi, 1) if rsi else None, "signal": sig,
        })
    js = js.replace("{vault_data_json}", json.dumps(vault_data))

    return _base("screener", "Stock Screener", html, user, "", js)

def _sidebar_html(user: dict, active: str) -> str:
    is_admin = user.get("role") == "admin"
    nav = [
        ("stocks",    "📊", "Stocks"),
        ("watchlist", "👁",  "Watchlist"),
        ("journal",   "📓", "Journal"),
        ("charts",    "📉", "Charts"),
        ("gold",      "🥇", "Gold"),
        ("crypto",    "₿",  "Crypto"),
        ("dca",       "📈", "DCA"),
        ("signals",   "🎯", "Signals"),
        ("dividends", "💰", "Dividends"),
        ("tools",     "🧮", "Tools"),
        ("news",      "📰", "News"),
        ("map",       "🗺️", "Map"),
        ("paper",     "🧪", "Paper"),
        ("ai",        "🤖", "AI"),
        ("screener",  "🔭", "Screener"),
        ("heatmap",   "🟩", "Heatmap"),
        ("analytics", "📐", "Analytics"),
        ("scanner",   "🔍", "Scanner"),
        ("chat",      "💬", "Chat"),
        ("alerts",    "🔔", "Alerts"),
        ("calendar",  "📅", "Calendar"),
        ("options",   "⚙",  "Options"),
        ("backtest",    "⏪", "Backtest"),
        ("correlation", "🔗", "Correlation"),
        ("report",      "📄", "Report"),
        ("risk",        "⚠️", "Risk"),
        ("benchmark",   "📏", "Benchmark"),
        ("realized",    "💵", "Realized P&L"),
        ("compare",     "⚖️", "Compare"),
        ("macro",       "🌐", "Macro"),
        ("earnings",    "📆", "Earnings"),
        ("sentiment",   "🧠", "Sentiment"),
        ("targets",     "🎯", "Targets"),
        ("portfolios",  "💼", "Portfolios"),
        ("settings",    "⚙️", "Settings"),
        ("insider",     "🏦", "Insider"),
    ]
    _TH2 = {
        "stocks":"หุ้น","watchlist":"ติดตาม","journal":"บันทึก","charts":"กราฟ",
        "gold":"ทอง","crypto":"คริปโต","dca":"DCA","signals":"สัญญาณ",
        "dividends":"ปันผล","tools":"เครื่องมือ","news":"ข่าว","map":"แผนที่","paper":"ทดลอง",
        "ai":"AI","screener":"คัดกรอง","heatmap":"ฮีตแมป","analytics":"วิเคราะห์",
        "scanner":"สแกน","chat":"แชท","alerts":"แจ้งเตือน","calendar":"ปฏิทิน",
        "options":"ออปชัน","backtest":"ทดสอบ","correlation":"สหสัมพันธ์",
        "report":"รายงาน","risk":"ความเสี่ยง","benchmark":"เปรียบ","realized":"กำไรจริง",
        "compare":"เปรียบเทียบ","macro":"มาโคร","earnings":"กำไร","sentiment":"ความรู้สึก",
        "targets":"เป้าหมาย","portfolios":"พอร์ต","insider":"อินไซเดอร์",
    }
    nav = [(nid, ic, lb) for nid, ic, lb in nav if nid not in ("settings", "home")]
    nav_html = ""
    for nid, icon, label in nav:
        a = "active" if nid == active else ""
        th = _TH2.get(nid, label)
        nav_html += f'<a class="sb-link {a}" href="/{nid}"><span class="sb-label" data-en="{label}" data-th="{th}">{label}</span></a>\n'
    return f"""<nav class="sb">
    <a href="/home" class="sb-logo" style="text-decoration:none">
      <span class="sb-logo-text">ArtheeNoi</span>
    </a>
    {nav_html}
    <div class="sb-spacer"></div>
    <div class="sb-bot">
      <a class="sb-link" href="/settings"><span class="sb-label" data-en="Settings" data-th="ตั้งค่า">Settings</span></a>
      {'<a class="sb-link" href="/admin"><span class="sb-label" data-en="Admin" data-th="แอดมิน">Admin</span></a>' if is_admin else ''}
      <a class="sb-link" href="/logout"><span class="sb-label" data-en="Logout" data-th="ออกจากระบบ">Logout</span></a>
    </div>
  </nav>"""

# ─── CHARTS PAGE ──────────────────────────────────────────────────────────────

def _pearson(xs: list, ys: list) -> float | None:
    """Pearson correlation between two equal-length lists."""
    n = len(xs)
    if n < 5:
        return None
    mx = sum(xs) / n; my = sum(ys) / n
    num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    dx  = sum((xs[i]-mx)**2 for i in range(n)) ** 0.5
    dy  = sum((ys[i]-my)**2 for i in range(n)) ** 0.5
    return round(num/(dx*dy), 2) if dx*dy else None

def _daily_returns(closes: list) -> list:
    if len(closes) < 2:
        return []
    return [round((closes[i]-closes[i-1])/closes[i-1]*100, 4)
            for i in range(1, len(closes))]

def charts_page(user: dict, market_data: dict, thb: float, sym: str | None = None) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    all_syms  = list(port.keys()) + [s for s in watchlist if s not in port]
    if not all_syms:
        all_syms = ["NVDA", "MSFT", "GOOGL"]

    default_sym = sym if sym else (all_syms[0] if all_syms else "NVDA")
    sym_opts = "".join(
        f'<option value="{s}" {"selected" if s == default_sym else ""}>{s}</option>'
        for s in all_syms
    )
    # Add default sym to list if not already there
    if default_sym not in all_syms:
        sym_opts = f'<option value="{default_sym}" selected>{default_sym}</option>' + sym_opts

    html = f"""
<!-- Chart Toolbar -->
<div class="card" style="margin-bottom:8px;padding:12px 16px">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
    <a href="/stocks" class="btn btn-ghost btn-sm">← Back</a>
    <select id="symSelect" onchange="loadSymbol(this.value)"
      style="background:var(--bg3);border:1px solid var(--border);color:var(--text);
             border-radius:6px;padding:6px 10px;font-size:13px;font-weight:700;cursor:pointer">
      {sym_opts}
    </select>
    <div class="tf-sep"></div>
    <div class="chart-toolbar" style="padding:0">
      <button class="tf-btn" onclick="setTF('5d')">5D</button>
      <button class="tf-btn" onclick="setTF('1mo')">1M</button>
      <button class="tf-btn" onclick="setTF('3mo')">3M</button>
      <button class="tf-btn" onclick="setTF('6mo')">6M</button>
      <button class="tf-btn active" id="tf-1y" onclick="setTF('1y')">1Y</button>
      <button class="tf-btn" onclick="setTF('2y')">2Y</button>
      <button class="tf-btn" onclick="setTF('5y')">5Y</button>
    </div>
    <div class="tf-sep"></div>
    <div class="chart-toolbar" style="padding:0">
      <button class="ind-btn active" id="btn-ma" onclick="toggleInd('ma')">MA</button>
      <button class="ind-btn" id="btn-ema" onclick="toggleInd('ema')">EMA</button>
      <button class="ind-btn" id="btn-bb" onclick="toggleInd('bb')">BB</button>
      <button class="ind-btn active" id="btn-vol" onclick="toggleInd('vol')">VOL</button>
      <button class="ind-btn active" id="btn-rsi" onclick="toggleInd('rsi')">RSI</button>
      <button class="ind-btn" id="btn-macd" onclick="toggleInd('macd')">MACD</button>
    </div>
    <div class="tf-sep"></div>
    <button class="ind-btn" id="compareBtn" onclick="toggleCompare()">➕ Compare</button>
    <span id="chartLoading" style="color:var(--mid);font-size:12px;margin-left:8px"></span>
  </div>
</div>

<!-- Compare Panel (hidden initially) -->
<div id="comparePanel" class="card" style="display:none;margin-bottom:8px;padding:10px 16px">
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
    <span style="font-size:12px;color:var(--mid);font-weight:600">Compare with (max 4):</span>
    <input id="cmpInput1" type="text" placeholder="AAPL" style="width:80px;padding:5px 8px;font-size:12px;border-radius:4px">
    <input id="cmpInput2" type="text" placeholder="MSFT" style="width:80px;padding:5px 8px;font-size:12px;border-radius:4px">
    <input id="cmpInput3" type="text" placeholder="GOOGL" style="width:80px;padding:5px 8px;font-size:12px;border-radius:4px">
    <input id="cmpInput4" type="text" placeholder="" style="width:80px;padding:5px 8px;font-size:12px;border-radius:4px">
    <button class="btn btn-primary btn-sm" onclick="runCompare()">🔍 Compare</button>
    <button class="btn btn-ghost btn-sm" onclick="exitCompare()">✕ Cancel</button>
  </div>
</div>

<!-- Compare Chart Panel (hidden initially) -->
<div id="compareChartPanel" class="chart-panel" style="display:none;margin-bottom:8px">
  <div class="chart-panel-label" id="compareTitle">Comparison (normalized 100)</div>
  <div id="chart-compare" style="width:100%;height:50vh;min-height:300px"></div>
  <div id="compareLegend" style="padding:8px 12px;display:flex;gap:16px;flex-wrap:wrap;background:var(--bg3)"></div>
</div>

<!-- OHLCV Info Bar -->
<div class="ohlcv-bar" id="ohlcv-bar" style="padding:6px 4px;margin-bottom:4px">
  <span class="sym-label" id="ohlcv-sym">{default_sym}</span>
  <span id="ohlcv-price" style="font-size:18px;font-weight:600;color:var(--text)">—</span>
  <span id="ohlcv-ohlc" style="color:var(--mid);font-size:12px"></span>
  <span id="ohlcv-chg" style="font-size:12px"></span>
  <span id="ohlcv-vol" style="font-size:12px;color:var(--mid)"></span>
</div>

<!-- Main Candlestick Chart -->
<div class="chart-panel">
  <div class="chart-panel-label">Price</div>
  <div id="chart-main" style="width:100%;height:50vh;min-height:300px"></div>
</div>

<!-- Volume Chart -->
<div class="chart-panel" id="panel-vol">
  <div class="chart-panel-label">Volume</div>
  <div id="chart-volume" style="width:100%;height:100px"></div>
</div>

<!-- RSI Chart -->
<div class="chart-panel" id="panel-rsi">
  <div class="chart-panel-label">RSI (14)</div>
  <div id="chart-rsi" style="width:100%;height:110px"></div>
</div>

<!-- MACD Chart -->
<div class="chart-panel" id="panel-macd" style="display:none">
  <div class="chart-panel-label">MACD (12,26,9)</div>
  <div id="chart-macd" style="width:100%;height:110px"></div>
</div>
"""

    js = f"""
// ── Load LightweightCharts ──────────────────────────────────────────────────
const _lcScript = document.createElement('script');
_lcScript.src = 'https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js';
_lcScript.onload = () => initCharts();
document.head.appendChild(_lcScript);

// ── State ───────────────────────────────────────────────────────────────────
let currentSym = '{default_sym}';
let currentPeriod = '1y';
let _chart, _volChart, _rsiChart, _macdChart;
let _candleSeries, _volSeries, _rsiSeries, _macdLineSeries, _macdSignalSeries, _macdHistSeries;
let _ma20Series, _ma50Series, _ma200Series, _ema20Series;
let _bbUpperSeries, _bbMidSeries, _bbLowerSeries;
let _indState = {{ma:true, ema:false, bb:false, vol:true, rsi:true, macd:false}};
let _currentCandles = [];

// ── Indicator calculations ──────────────────────────────────────────────────
function calcMA(data, n) {{
  return data.map((d,i) => {{
    if (i < n-1) return null;
    const sum = data.slice(i-n+1,i+1).reduce((a,b)=>a+b.close,0);
    return {{time:d.time,value:sum/n}};
  }}).filter(Boolean);
}}
function calcEMA(data, n) {{
  const k=2/(n+1); let ema=data[0].close;
  return data.map((d,i)=>{{
    if(i===0){{ema=d.close;return{{time:d.time,value:ema}};}}
    ema=d.close*k+ema*(1-k); return{{time:d.time,value:ema}};
  }});
}}
function calcBB(data,n=20,mult=2) {{
  return data.map((d,i)=>{{
    if(i<n-1)return null;
    const sl=data.slice(i-n+1,i+1).map(x=>x.close);
    const mean=sl.reduce((a,b)=>a+b,0)/n;
    const std=Math.sqrt(sl.map(x=>(x-mean)**2).reduce((a,b)=>a+b,0)/n);
    return{{time:d.time,upper:mean+mult*std,middle:mean,lower:mean-mult*std}};
  }}).filter(Boolean);
}}
function calcRSI(data,n=14) {{
  const result=[]; let gains=0,losses=0;
  for(let i=1;i<data.length;i++){{
    const diff=data[i].close-data[i-1].close;
    if(i<=n){{gains+=Math.max(diff,0);losses+=Math.max(-diff,0);
      if(i===n){{gains/=n;losses/=n;result.push({{time:data[i].time,value:losses===0?100:100-100/(1+gains/losses)}});}}
      continue;
    }}
    gains=(gains*(n-1)+Math.max(diff,0))/n; losses=(losses*(n-1)+Math.max(-diff,0))/n;
    result.push({{time:data[i].time,value:losses===0?100:100-100/(1+gains/losses)}});
  }}
  return result;
}}
function calcMACD(data,fast=12,slow=26,sig=9) {{
  const ef=calcEMA(data,fast),es=calcEMA(data,slow);
  const macdLine=es.map((d,i)=>{{return{{time:d.time,value:ef[i].value-d.value}}}});
  const k=2/(sig+1); let ema=macdLine[0].value;
  const signal=macdLine.map(d=>{{ema=d.value*k+ema*(1-k);return{{time:d.time,value:ema}}}});
  const hist=macdLine.map((d,i)=>{{
    const v=d.value-signal[i].value;
    return{{time:d.time,value:v,color:v>=0?'#26a69a':'#ef5350'}};
  }});
  return{{macd:macdLine,signal,hist}};
}}

// ── Chart init ──────────────────────────────────────────────────────────────
function initCharts() {{
  const LC = LightweightCharts;
  const chartOpts = (h) => ({{
    layout:{{background:{{color:'#131722'}},textColor:'#d1d4dc'}},
    grid:{{vertLines:{{color:'#2a2e39'}},horzLines:{{color:'#2a2e39'}}}},
    rightPriceScale:{{borderColor:'#363a45'}},
    timeScale:{{borderColor:'#363a45',timeVisible:true,secondsVisible:false}},
    crosshair:{{mode:LC.CrosshairMode.Normal}},
    width:document.getElementById('chart-main').offsetWidth,
    height:h,
  }});

  _chart = LC.createChart(document.getElementById('chart-main'), {{
    ...chartOpts(document.getElementById('chart-main').offsetHeight||Math.floor(window.innerHeight*0.50)),
    crosshair:{{mode:LC.CrosshairMode.Normal}},
  }});
  _candleSeries = _chart.addCandlestickSeries({{
    upColor:'#26a69a',downColor:'#ef5350',
    borderUpColor:'#26a69a',borderDownColor:'#ef5350',
    wickUpColor:'#26a69a',wickDownColor:'#ef5350',
  }});
  _ma20Series  = _chart.addLineSeries({{color:'#f0b429',lineWidth:1,title:'MA20',lastValueVisible:false,priceLineVisible:false}});
  _ma50Series  = _chart.addLineSeries({{color:'#2dd4bf',lineWidth:1,title:'MA50',lastValueVisible:false,priceLineVisible:false}});
  _ma200Series = _chart.addLineSeries({{color:'#ff6b35',lineWidth:1,title:'MA200',lastValueVisible:false,priceLineVisible:false}});
  _ema20Series = _chart.addLineSeries({{color:'#ab47bc',lineWidth:1,lineStyle:1,title:'EMA20',lastValueVisible:false,priceLineVisible:false}});
  _bbUpperSeries = _chart.addLineSeries({{color:'rgba(41,98,255,0.7)',lineWidth:1,lineStyle:2,title:'BB+',lastValueVisible:false,priceLineVisible:false}});
  _bbMidSeries   = _chart.addLineSeries({{color:'rgba(41,98,255,0.4)',lineWidth:1,lineStyle:2,title:'BB~',lastValueVisible:false,priceLineVisible:false}});
  _bbLowerSeries = _chart.addLineSeries({{color:'rgba(41,98,255,0.7)',lineWidth:1,lineStyle:2,title:'BB-',lastValueVisible:false,priceLineVisible:false}});

  _volChart = LC.createChart(document.getElementById('chart-volume'), {{
    ...chartOpts(document.getElementById('chart-volume').offsetHeight||100),
    rightPriceScale:{{borderColor:'#363a45',scaleMargins:{{top:0.1,bottom:0}}}},
    timeScale:{{visible:false}},
  }});
  _volSeries = _volChart.addHistogramSeries({{priceFormat:{{type:'volume'}},priceScaleId:''}});

  _rsiChart = LC.createChart(document.getElementById('chart-rsi'), {{
    ...chartOpts(document.getElementById('chart-rsi').offsetHeight||110),
    rightPriceScale:{{borderColor:'#363a45',scaleMargins:{{top:0.1,bottom:0.1}}}},
    timeScale:{{visible:false}},
  }});
  _rsiSeries = _rsiChart.addLineSeries({{color:'#9c27b0',lineWidth:1,title:'RSI'}});
  // RSI reference lines
  _rsiChart.addLineSeries({{color:'rgba(239,83,80,0.4)',lineWidth:1,lineStyle:2,lastValueVisible:false,priceLineVisible:false}})
    .setData([{{time:'2000-01-01',value:70}}]); // placeholder — we'll set properly after data load

  _macdChart = LC.createChart(document.getElementById('chart-macd'), {{
    ...chartOpts(document.getElementById('chart-macd').offsetHeight||110),
    rightPriceScale:{{borderColor:'#363a45',scaleMargins:{{top:0.1,bottom:0.1}}}},
    timeScale:{{visible:false}},
  }});
  _macdLineSeries   = _macdChart.addLineSeries({{color:'#2962ff',lineWidth:1,title:'MACD'}});
  _macdSignalSeries = _macdChart.addLineSeries({{color:'#ff6b35',lineWidth:1,title:'Signal'}});
  _macdHistSeries   = _macdChart.addHistogramSeries({{priceScaleId:'',title:'Hist'}});

  // Sync crosshair
  function syncCH(src, targets, param) {{
    if(!param||!param.time) {{ targets.forEach(t=>t.clearCrosshairPosition&&t.clearCrosshairPosition()); return; }}
    targets.forEach(t=>{{
      if(t._series) try{{t.setCrosshairPosition(0,param.time,t._series);}}catch(e){{}}
    }});
  }}
  _volChart._series  = _volSeries;
  _rsiChart._series  = _rsiSeries;
  _macdChart._series = _macdLineSeries;
  _chart.subscribeCrosshairMove(p=>syncCH(_chart,[_volChart,_rsiChart,_macdChart],p));

  // OHLCV bar on crosshair move
  _chart.subscribeCrosshairMove(param=>{{
    if(!param||!param.time||!param.seriesData)return;
    const c=param.seriesData.get(_candleSeries);
    if(!c)return;
    const chg=((c.close-c.open)/c.open*100).toFixed(2);
    const col=c.close>=c.open?'#26a69a':'#ef5350';
    const sign=chg>=0?'+':'';
    document.getElementById('ohlcv-price').style.color=col;
    document.getElementById('ohlcv-price').textContent=c.close.toFixed(2);
    document.getElementById('ohlcv-ohlc').innerHTML=
      `O:<b>${{c.open.toFixed(2)}}</b> H:<b>${{c.high.toFixed(2)}}</b> L:<b>${{c.low.toFixed(2)}}</b> C:<b>${{c.close.toFixed(2)}}</b>`;
    document.getElementById('ohlcv-chg').style.color=col;
    document.getElementById('ohlcv-chg').textContent=sign+chg+'%';
  }});

  // Resize
  const ro=new ResizeObserver(()=>{{
    [['chart-main',_chart],['chart-volume',_volChart],['chart-rsi',_rsiChart],['chart-macd',_macdChart]]
      .forEach(([id,ch])=>{{const el=document.getElementById(id);if(el&&ch)ch.resize(el.offsetWidth,el.offsetHeight);}});
  }});
  ro.observe(document.getElementById('pageContent'));

  loadChart(currentSym, currentPeriod);
}}

// ── Load chart data ──────────────────────────────────────────────────────────
function loadChart(sym, period) {{
  document.getElementById('chartLoading').textContent='Loading...';
  document.getElementById('ohlcv-sym').textContent=sym;
  fetch('/api/chart/'+sym+'?period='+period)
    .then(r=>r.json()).then(data=>{{
      document.getElementById('chartLoading').textContent='';
      const candles=data.candles||[];
      if(!candles.length){{document.getElementById('chartLoading').textContent='No data';return;}}
      _currentCandles=candles;
      updateData(candles);
      // Initial OHLCV from last candle
      const last=candles[candles.length-1];
      const first=candles[0];
      const chg=((last.close-first.close)/first.close*100).toFixed(2);
      const col=last.close>=last.open?'#26a69a':'#ef5350';
      document.getElementById('ohlcv-price').textContent=last.close.toFixed(2);
      document.getElementById('ohlcv-price').style.color=col;
      document.getElementById('ohlcv-chg').textContent=(chg>=0?'+':'')+chg+'%';
      document.getElementById('ohlcv-chg').style.color=col;
      const v=last.volume;
      document.getElementById('ohlcv-vol').textContent='Vol: '+(v>1e6?(v/1e6).toFixed(1)+'M':v>1e3?(v/1e3).toFixed(0)+'K':v);
    }})
    .catch(()=>{{document.getElementById('chartLoading').textContent='Error';}});
}}

function updateData(candles) {{
  if(!_candleSeries)return;
  _candleSeries.setData(candles);

  // MA overlays
  if(_indState.ma){{
    _ma20Series.setData(calcMA(candles,20));
    _ma50Series.setData(calcMA(candles,50));
    _ma200Series.setData(calcMA(candles,200));
  }} else {{_ma20Series.setData([]);_ma50Series.setData([]);_ma200Series.setData([]);}}

  // EMA
  if(_indState.ema) _ema20Series.setData(calcEMA(candles,20));
  else _ema20Series.setData([]);

  // BB
  if(_indState.bb){{
    const bb=calcBB(candles,20,2);
    _bbUpperSeries.setData(bb.map(b=>{{return{{time:b.time,value:b.upper}}}}));
    _bbMidSeries.setData(bb.map(b=>{{return{{time:b.time,value:b.middle}}}}));
    _bbLowerSeries.setData(bb.map(b=>{{return{{time:b.time,value:b.lower}}}}));
  }} else {{_bbUpperSeries.setData([]);_bbMidSeries.setData([]);_bbLowerSeries.setData([]);}}

  // Volume
  if(_indState.vol) {{
    _volSeries.setData(candles.map(c=>{{
      return{{time:c.time,value:c.volume,color:c.close>=c.open?'rgba(38,166,154,0.6)':'rgba(239,83,80,0.6)'}};
    }}));
  }} else _volSeries.setData([]);

  // RSI
  if(_indState.rsi) {{
    const rsiData=calcRSI(candles,14);
    _rsiSeries.setData(rsiData);
    // Sync time scale for RSI 70/30 lines using price scale
    if(rsiData.length){{
      const t0=rsiData[0].time, t1=rsiData[rsiData.length-1].time;
    }}
  }} else _rsiSeries.setData([]);

  // MACD
  if(_indState.macd){{
    const m=calcMACD(candles);
    _macdLineSeries.setData(m.macd);
    _macdSignalSeries.setData(m.signal);
    _macdHistSeries.setData(m.hist);
  }} else {{_macdLineSeries.setData([]);_macdSignalSeries.setData([]);_macdHistSeries.setData([]);}}

  _chart.timeScale().fitContent();
}}

// ── Controls ────────────────────────────────────────────────────────────────
function setTF(period) {{
  document.querySelectorAll('.tf-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  currentPeriod=period;
  loadChart(currentSym, period);
}}

function loadSymbol(sym) {{
  currentSym=sym;
  document.getElementById('ohlcv-sym').textContent=sym;
  loadChart(sym, currentPeriod);
}}

function toggleInd(name) {{
  _indState[name]=!_indState[name];
  const btn=document.getElementById('btn-'+name);
  btn.classList.toggle('active',_indState[name]);
  if(['vol','rsi','macd'].includes(name)){{
    const panel=document.getElementById('panel-'+name);
    if(panel) panel.style.display=_indState[name]?'':'none';
  }}
  if(_currentCandles.length) updateData(_currentCandles);
}}

// ── Compare Mode ─────────────────────────────────────────────────────────────
const COMPARE_COLORS = ['#2dd4bf','#f0b429','#ff6b35','#9c27b0','#ef5350'];
let _compareMode = false;
let _compareChart = null;

function toggleCompare() {{
  const panel = document.getElementById('comparePanel');
  panel.style.display = panel.style.display === 'none' ? '' : 'none';
  if (panel.style.display !== 'none') document.getElementById('cmpInput1').focus();
}}

async function runCompare() {{
  const inputs = ['cmpInput1','cmpInput2','cmpInput3','cmpInput4'];
  const extras = inputs.map(id => document.getElementById(id).value.trim().toUpperCase()).filter(s => s);
  const syms = [currentSym, ...extras];
  if (syms.length < 2) {{ alert('เพิ่มอย่างน้อย 1 symbol เพื่อเปรียบเทียบ'); return; }}

  document.getElementById('chartLoading').textContent = 'Loading compare...';
  try {{
    const r = await fetch('/api/compare?syms=' + syms.join(',') + '&period=' + currentPeriod);
    const data = await r.json();
    if (data.error) {{ document.getElementById('chartLoading').textContent = data.error; return; }}

    _compareMode = true;
    // Hide single-stock panels
    document.getElementById('chart-main').closest('.chart-panel').style.display = 'none';
    document.getElementById('panel-vol').style.display = 'none';
    document.getElementById('panel-rsi').style.display = 'none';
    document.getElementById('panel-macd').style.display = 'none';
    document.getElementById('compareChartPanel').style.display = '';
    document.getElementById('comparePanel').style.display = '';

    const LC = LightweightCharts;
    if (_compareChart) {{ _compareChart.remove(); _compareChart = null; }}
    const cmpEl = document.getElementById('chart-compare');
    _compareChart = LC.createChart(cmpEl, {{
      layout:{{background:{{color:'#131722'}},textColor:'#d1d4dc'}},
      grid:{{vertLines:{{color:'#2a2e39'}},horzLines:{{color:'#2a2e39'}}}},
      rightPriceScale:{{borderColor:'#363a45'}},
      timeScale:{{borderColor:'#363a45',timeVisible:true}},
      crosshair:{{mode:LC.CrosshairMode.Normal}},
      width: cmpEl.offsetWidth,
      height: cmpEl.offsetHeight || 400,
    }});

    const legend = document.getElementById('compareLegend');
    legend.innerHTML = '';
    let colorIdx = 0;
    for (const [sym, closes] of Object.entries(data)) {{
      if (!closes || !closes.length) continue;
      const base = closes[0].value;
      if (!base) continue;
      const normalized = closes.map(d => ({{time: d.time, value: parseFloat((d.value / base * 100).toFixed(2))}}));
      const color = COMPARE_COLORS[colorIdx % COMPARE_COLORS.length];
      const series = _compareChart.addLineSeries({{color, lineWidth:2, title:sym, lastValueVisible:true, priceLineVisible:false}});
      series.setData(normalized);
      const lastNorm = normalized[normalized.length-1].value;
      const chgCmp = (lastNorm - 100).toFixed(2);
      const signCmp = chgCmp >= 0 ? '+' : '';
      legend.innerHTML += `<span style="color:${{color}};font-size:13px;font-weight:700">${{sym}} ${{signCmp}}${{chgCmp}}%</span>`;
      colorIdx++;
    }}
    _compareChart.timeScale().fitContent();
    document.getElementById('compareTitle').textContent = 'Comparison (normalized 100): ' + Object.keys(data).join(' vs ');
    document.getElementById('chartLoading').textContent = '';
  }} catch(e) {{ document.getElementById('chartLoading').textContent = 'Compare error'; console.error(e); }}
}}

function exitCompare() {{
  _compareMode = false;
  document.getElementById('comparePanel').style.display = 'none';
  document.getElementById('compareChartPanel').style.display = 'none';
  document.getElementById('chart-main').closest('.chart-panel').style.display = '';
  if (_indState.vol) document.getElementById('panel-vol').style.display = '';
  if (_indState.rsi) document.getElementById('panel-rsi').style.display = '';
  if (_indState.macd) document.getElementById('panel-macd').style.display = '';
  if (_compareChart) {{ _compareChart.remove(); _compareChart = null; }}
}}
"""
    return _base("charts", f"Chart — {default_sym}", html, user, "", js)


# ─── ALERTS PAGE ──────────────────────────────────────────────────────────────

def alerts_page(user: dict, market_data: dict) -> str:
    alerts = user.get("alerts", [])
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    all_syms = list(port.keys()) + [s for s in watchlist if s not in port]

    active_alerts   = [a for a in alerts if a.get("active") and not a.get("triggered_at")]
    triggered_alerts= [a for a in reversed(alerts) if a.get("triggered_at")][:10]
    # Full alert history from separate log
    alert_history = list(reversed(user.get("alert_history", [])))[:50]

    # Active alerts table
    act_rows = ""
    for a in active_alerts:
        d = market_data.get(a["sym"], {})
        cur = d.get("price", 0)
        cond_map = {"above": "ราคา >", "below": "ราคา <", "change_pct": "Chg% >"}
        cond_lbl = cond_map.get(a.get("condition","above"), a.get("condition",""))
        hit = False
        if a.get("condition") == "above" and cur >= a.get("price",0): hit = True
        elif a.get("condition") == "below" and cur <= a.get("price",0): hit = True
        elif a.get("condition") == "change_pct":
            chg = abs(d.get("chg",0))
            if chg >= a.get("price",0): hit = True
        status_html = ('<span style="color:var(--gold);font-weight:700">⚡ Close!</span>'
                       if hit else '<span style="color:var(--muted)">⏳ Watching</span>')
        act_rows += f"""
        <tr>
          <td class="sym">{a['sym']}</td>
          <td style="color:var(--mid)">{cond_lbl}</td>
          <td style="font-weight:700">${a.get('price',0):,.2f}</td>
          <td class="{'pos' if cur>0 else ''}">${cur:,.2f}</td>
          <td>{a.get('note','—') or '—'}</td>
          <td>{status_html}</td>
          <td>
            <form method="POST" action="/alerts/toggle" style="display:inline">
              <input type="hidden" name="alert_id" value="{a['id']}">
              <button class="btn btn-ghost btn-sm" type="submit">⏸ Pause</button>
            </form>
            <form method="POST" action="/alerts/delete" style="display:inline;margin-left:4px">
              <input type="hidden" name="alert_id" value="{a['id']}">
              <button class="btn btn-sm" style="background:#ef444422;color:#ef4444;border:1px solid #ef444444" type="submit">✕</button>
            </form>
          </td>
        </tr>"""

    # Triggered history
    trig_rows = ""
    for a in triggered_alerts:
        trig_rows += f"""
        <tr>
          <td class="sym">{a['sym']}</td>
          <td style="color:var(--mid)">{a.get('condition','')}</td>
          <td>${a.get('price',0):,.2f}</td>
          <td style="color:var(--muted);font-size:11px">{a.get('triggered_at','')}</td>
          <td style="color:var(--muted)">{a.get('note','') or '—'}</td>
        </tr>"""

    sym_opts = "".join(f'<option value="{s}">{s}</option>' for s in all_syms)

    # Paused alerts
    paused = [a for a in alerts if not a.get("active") and not a.get("triggered_at")]
    paused_html = ""
    for a in paused:
        paused_html += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--bl)">
          <span class="sym">{a['sym']}</span>
          <span style="color:var(--muted);font-size:12px">{a.get('condition','')} ${a.get('price',0):.2f}</span>
          <span style="flex:1"></span>
          <form method="POST" action="/alerts/toggle" style="display:inline">
            <input type="hidden" name="alert_id" value="{a['id']}">
            <button class="btn btn-ghost btn-sm" type="submit">▶ Resume</button>
          </form>
          <form method="POST" action="/alerts/delete" style="display:inline">
            <input type="hidden" name="alert_id" value="{a['id']}">
            <button class="btn btn-sm" style="background:#ef444422;color:#ef4444;border:1px solid #ef444444" type="submit">✕</button>
          </form>
        </div>"""

    html = f"""
<!-- Add Alert -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">➕ ตั้ง Alert ใหม่</div>
  <form method="POST" action="/alerts/add" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbol</div>
      <select name="sym" style="background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px 12px;font-size:12px">{sym_opts}</select>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">เงื่อนไข</div>
      <select name="condition" style="background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px 12px;font-size:12px">
        <option value="above">ราคา > (Price above)</option>
        <option value="below">ราคา &lt; (Price below)</option>
        <option value="change_pct">Daily change &gt;%</option>
      </select>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ราคาเป้าหมาย</div>
      <input type="number" name="price" step="0.01" min="0" placeholder="0.00"
        style="width:110px;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px 12px;font-size:12px">
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Note (ไม่บังคับ)</div>
      <input type="text" name="note" placeholder="หมายเหตุ..."
        style="width:160px;background:var(--card2);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:8px 12px;font-size:12px">
    </div>
    <button type="submit" class="btn btn-primary">🔔 เพิ่ม Alert</button>
  </form>
</div>

<!-- Active Alerts -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">🔔 Active Alerts ({len(active_alerts)})</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>เงื่อนไข</th><th>Target</th><th>ราคาปัจจุบัน</th><th>Note</th><th>Status</th><th></th></tr></thead>
      <tbody>{act_rows or '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:24px">ยังไม่มี alert — เพิ่มด้านบน</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- Paused -->
{f'<div class="card" style="margin-bottom:16px"><div class="card-hdr">⏸ Paused ({len(paused)})</div>{paused_html}</div>' if paused else ''}

<!-- Triggered History -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">⚡ Triggered History (ล่าสุด 10)</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>เงื่อนไข</th><th>Target</th><th>เวลา</th><th>Note</th></tr></thead>
      <tbody>{trig_rows or '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:24px">ยังไม่มี triggered alerts</td></tr>'}</tbody>
    </table>
  </div>
</div>

<!-- Full Alert Log -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <div class="card-hdr" style="margin-bottom:0">📋 Alert Log (browser-triggered, ล่าสุด 50)</div>
    <form method="POST" action="/alerts/clear-log" style="margin:0">
      <button class="btn btn-danger btn-sm" type="submit" onclick="return confirm('ลบ log ทั้งหมด?')">🗑 Clear Log</button>
    </form>
  </div>
  {f'''<div style="overflow-x:auto">
  <table class="tbl">
    <thead><tr><th>Symbol</th><th>เงื่อนไข</th><th>Target</th><th>Actual Price</th><th>เวลา</th></tr></thead>
    <tbody>{''.join(
      f"""<tr>
        <td class="sym">{h['sym']}</td>
        <td style="color:var(--mid)">{h.get('condition','')}</td>
        <td style="font-weight:700">${h.get('target',0):,.2f}</td>
        <td style="color:{'var(--green)' if h.get('condition')=='above' else 'var(--red)'}">${h.get('actual',0):,.2f}</td>
        <td style="color:var(--muted);font-size:11px">{h.get('ts','')}</td>
      </tr>"""
      for h in alert_history
    )}</tbody>
  </table>
  </div>''' if alert_history else '<div style="text-align:center;color:var(--muted);padding:24px">ยังไม่มี log — alert จะถูกบันทึกอัตโนมัติเมื่อ trigger</div>'}
</div>
"""
    return _base("alerts", "Price Alerts", html, user)


# ─── CALENDAR PAGE ────────────────────────────────────────────────────────────

# Hardcoded US economic events (next 3 months from mid-2026)
_ECON_EVENTS = [
    {"date": "2026-07-29", "event": "FOMC Meeting", "type": "fed"},
    {"date": "2026-07-10", "event": "CPI Report (June)", "type": "cpi"},
    {"date": "2026-08-12", "event": "CPI Report (July)", "type": "cpi"},
    {"date": "2026-09-16", "event": "FOMC Meeting", "type": "fed"},
    {"date": "2026-09-10", "event": "CPI Report (August)", "type": "cpi"},
    {"date": "2026-10-07", "event": "CPI Report (September)", "type": "cpi"},
    {"date": "2026-11-04", "event": "FOMC Meeting", "type": "fed"},
]

def _fetch_earnings(syms: list) -> list:
    """Fetch earnings dates via yfinance .calendar attribute."""
    results = []
    try:
        import yfinance as yf
        for sym in syms:
            try:
                t = yf.Ticker(sym)
                cal = t.calendar
                # cal can be a dict or DataFrame
                if cal is None:
                    continue
                if hasattr(cal, "get"):
                    ed = cal.get("Earnings Date")
                    if isinstance(ed, list) and ed:
                        ed = ed[0]
                    eps = cal.get("EPS Estimate")
                    rev = cal.get("Revenue Estimate")
                else:
                    try:
                        ed  = cal.loc["Earnings Date"].iloc[0] if "Earnings Date" in cal.index else None
                        eps = cal.loc["EPS Estimate"].iloc[0]  if "EPS Estimate" in cal.index else None
                        rev = cal.loc["Revenue Estimate"].iloc[0] if "Revenue Estimate" in cal.index else None
                    except Exception:
                        ed = eps = rev = None
                if ed:
                    if hasattr(ed, "date"):
                        ed = ed.date()
                    results.append({
                        "sym": sym, "date": str(ed)[:10],
                        "eps": f"${eps:.2f}" if eps and not (hasattr(eps,"__float__") and math.isnan(float(eps))) else "—",
                        "rev": f"${rev/1e9:.1f}B" if rev and not (hasattr(rev,"__float__") and math.isnan(float(rev))) else "—",
                    })
            except Exception:
                pass
    except ImportError:
        pass
    return results

def calendar_page(user: dict, market_data: dict) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    syms = list(port.keys()) + [s for s in watchlist if s not in port]
    syms = [s for s in syms if "=" not in s and "BTC" not in s]

    earnings = _fetch_earnings(syms[:20])  # limit to 20 to avoid timeout
    today = datetime.now().date()

    # Add days_away
    rows = []
    for e in earnings:
        try:
            ed = datetime.strptime(e["date"], "%Y-%m-%d").date()
            days_away = (ed - today).days
            e["days_away"] = days_away
            rows.append(e)
        except Exception:
            pass
    rows.sort(key=lambda x: x.get("days_away", 9999))

    earn_html = ""
    for e in rows:
        da = e.get("days_away", 0)
        if da < 0:
            col = "var(--muted)"; badge = "ผ่านแล้ว"
        elif da <= 7:
            col = "var(--red)"; badge = f"⚠️ {da} วัน!"
        elif da <= 30:
            col = "var(--gold)"; badge = f"🟡 {da} วัน"
        else:
            col = "var(--green)"; badge = f"🟢 {da} วัน"
        earn_html += f"""
        <tr>
          <td class="sym">{e['sym']}</td>
          <td style="color:var(--mid)">{e['date']}</td>
          <td style="color:var(--text)">{e['eps']}</td>
          <td style="color:var(--text)">{e['rev']}</td>
          <td><span style="color:{col};font-weight:700;font-size:12px">{badge}</span></td>
        </tr>"""

    econ_html = ""
    for ev in _ECON_EVENTS:
        try:
            ed = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            da = (ed - today).days
        except Exception:
            da = 999
        if da < 0:
            col = "var(--muted)"; badge = "ผ่านแล้ว"
        elif da <= 7:
            col = "var(--red)"; badge = f"⚠️ {da} วัน"
        elif da <= 30:
            col = "var(--gold)"; badge = f"🟡 {da} วัน"
        else:
            col = "var(--green)"; badge = f"🟢 {da} วัน"
        icon = "🏛️" if ev["type"] == "fed" else "📊"
        econ_html += f"""
        <tr>
          <td><span style="font-size:16px">{icon}</span></td>
          <td style="font-weight:700;color:var(--text)">{ev['event']}</td>
          <td style="color:var(--mid)">{ev['date']}</td>
          <td><span style="color:{col};font-weight:700;font-size:12px">{badge}</span></td>
        </tr>"""

    html = f"""
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">📅 Earnings Calendar — Portfolio + Watchlist</div>
  <div style="overflow-x:auto">
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>Earnings Date</th><th>EPS Estimate</th><th>Revenue</th><th>Days Away</th></tr></thead>
      <tbody>{earn_html or '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:24px">กำลังโหลดข้อมูล earnings...</td></tr>'}</tbody>
    </table>
  </div>
</div>

<div class="card">
  <div class="card-hdr">🏛️ Economic Events (3 เดือนข้างหน้า)</div>
  <table class="tbl">
    <thead><tr><th></th><th>Event</th><th>Date</th><th>Days Away</th></tr></thead>
    <tbody>{econ_html}</tbody>
  </table>
</div>
"""
    return _base("calendar", "Earnings Calendar", html, user)


# ─── OPTIONS PAGE ─────────────────────────────────────────────────────────────

def options_page(user: dict, market_data: dict, sym: str | None = None) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    all_syms = [s for s in list(port.keys()) + watchlist
                if "=" not in s and "BTC" not in s]
    if not sym:
        sym = all_syms[0] if all_syms else "AAPL"

    cur_price = (market_data.get(sym) or {}).get("price", 0)
    sym_opts  = "".join(
        f'<option value="{s}" {"selected" if s==sym else ""}>{s}</option>'
        for s in all_syms
    )
    expiry_tabs = '<div id="expiryTabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px"></div>'

    html = f"""
<div class="card-hdr" style="margin-bottom:8px">Select Stock</div>
<form method="GET" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">
  <select name="sym" onchange="this.form.submit()"
    style="background:var(--card2);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:8px 14px;font-size:13px;cursor:pointer">
    {sym_opts}
  </select>
  <span style="color:var(--mid);font-size:13px">ราคาปัจจุบัน: <b style="color:var(--text)">${cur_price:,.2f}</b></span>
</form>

<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">⚙ Options Chain — <span id="chainSym">{sym}</span></div>
  {expiry_tabs}
  <div id="chainLoading" style="color:var(--muted);padding:16px">กำลังโหลด options chain...</div>
  <div id="chainContent" style="display:none">
    <div class="g2" style="gap:16px">
      <div>
        <div style="font-size:11px;font-weight:700;color:var(--green);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">📞 Calls</div>
        <div style="overflow-x:auto"><table class="tbl" id="callsTable">
          <thead><tr><th>Strike</th><th>Last</th><th>Bid</th><th>Ask</th><th>Vol</th><th>OI</th><th>IV</th><th>ITM</th></tr></thead>
          <tbody id="callsBody"></tbody>
        </table></div>
      </div>
      <div>
        <div style="font-size:11px;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">📤 Puts</div>
        <div style="overflow-x:auto"><table class="tbl" id="putsTable">
          <thead><tr><th>Strike</th><th>Last</th><th>Bid</th><th>Ask</th><th>Vol</th><th>OI</th><th>IV</th><th>ITM</th></tr></thead>
          <tbody id="putsBody"></tbody>
        </table></div>
      </div>
    </div>
  </div>
</div>
"""

    js = f"""
const CUR = {cur_price};
const SYM = '{sym}';
let expiries = [];

function loadExpiries() {{
  fetch('/api/options/' + SYM).then(r=>r.json()).then(d => {{
    expiries = d.expiries || [];
    const tabs = document.getElementById('expiryTabs');
    tabs.innerHTML = '';
    expiries.slice(0,8).forEach((exp,i) => {{
      const b = document.createElement('button');
      b.className = 'chip' + (i===0?' active':'');
      b.textContent = exp;
      b.onclick = () => {{ document.querySelectorAll('#expiryTabs .chip').forEach(x=>x.classList.remove('active'));
                           b.classList.add('active'); loadChain(exp); }};
      tabs.appendChild(b);
    }});
    if (expiries.length) loadChain(expiries[0]);
  }}).catch(() => {{
    document.getElementById('chainLoading').textContent = 'ไม่สามารถโหลด options ได้';
  }});
}}

function loadChain(exp) {{
  document.getElementById('chainLoading').style.display='block';
  document.getElementById('chainContent').style.display='none';
  fetch('/api/options/' + SYM + '?exp=' + exp).then(r=>r.json()).then(d => {{
    document.getElementById('chainLoading').style.display='none';
    document.getElementById('chainContent').style.display='block';
    renderTable('callsBody', d.calls||[], 'call');
    renderTable('putsBody', d.puts||[], 'put');
  }}).catch(() => {{ document.getElementById('chainLoading').textContent='Error loading chain'; }});
}}

function renderTable(tbodyId, rows, side) {{
  const tb = document.getElementById(tbodyId);
  tb.innerHTML = '';
  rows.forEach(r => {{
    const itm = side==='call' ? r.strike < CUR : r.strike > CUR;
    const bg  = itm ? 'background:#2dd4bf10;' : '';
    const itm_badge = itm ? '<span style="color:var(--teal);font-weight:700;font-size:10px">ITM</span>' : '<span style="color:var(--muted);font-size:10px">OTM</span>';
    tb.innerHTML += '<tr style="' + bg + '">'
      + '<td style="font-weight:700">$' + (r.strike||0).toFixed(2) + '</td>'
      + '<td>$' + (r.lastPrice||0).toFixed(2) + '</td>'
      + '<td style="color:var(--green)">$' + (r.bid||0).toFixed(2) + '</td>'
      + '<td style="color:var(--red)">$' + (r.ask||0).toFixed(2) + '</td>'
      + '<td style="color:var(--mid)">' + (r.volume||0).toLocaleString() + '</td>'
      + '<td style="color:var(--mid)">' + (r.openInterest||0).toLocaleString() + '</td>'
      + '<td>' + ((r.impliedVolatility||0)*100).toFixed(0) + '%</td>'
      + '<td>' + itm_badge + '</td>'
      + '</tr>';
  }});
}}

loadExpiries();
"""
    return _base("options", f"Options Chain — {sym}", html, user, "", js)


# ─── HEATMAP PAGE ─────────────────────────────────────────────────────────────

def heatmap_page(user: dict, market_data: dict, macro: dict) -> str:
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])

    vault_list = []
    try:
        import at_stock_vault as v
        vault_list = v.VAULT
    except Exception:
        pass

    # Build symbol → {price, chg, sector, company}
    all_stocks: dict = {}
    for item in vault_list:
        sym = item.get("t", "")
        d = market_data.get(sym, {})
        chg = d.get("chg") or d.get("change_pct") or 0
        if d.get("price") and sym:
            all_stocks[sym] = {"price": d["price"], "chg": chg,
                               "sector": item.get("s", "Other"), "company": item.get("c", sym)}
    # Ensure portfolio & watchlist included
    for sym in list(port.keys()) + watchlist:
        if sym not in all_stocks:
            d = market_data.get(sym, {})
            if d.get("price"):
                all_stocks[sym] = {"price": d["price"],
                                   "chg": d.get("chg") or d.get("change_pct") or 0,
                                   "sector": _get_vault_sector(sym), "company": sym}

    # Group by sector
    sectors: dict = {}
    for sym, info in all_stocks.items():
        sec = info["sector"]
        sectors.setdefault(sec, []).append((sym, info))

    def _chg_color(chg: float) -> str:
        if chg >= 3:   return "#1a6644"
        if chg >= 1:   return "#26a69a"
        if chg >= 0:   return "#2d8a6a"
        if chg >= -1:  return "#8a2d2d"
        if chg >= -3:  return "#ef5350"
        return "#b71c1c"

    # Sector summary pills
    sector_pills = ""
    for sec, stocks in sorted(sectors.items()):
        if not stocks:
            continue
        avg_chg = sum(s[1]["chg"] for s in stocks) / len(stocks)
        col = _chg_color(avg_chg)
        sign = "+" if avg_chg >= 0 else ""
        sector_pills += (f'<span style="background:{col};color:#fff;padding:3px 10px;'
                         f'border-radius:12px;font-size:11px;font-weight:700;white-space:nowrap">'
                         f'{sec} {sign}{avg_chg:.2f}%</span> ')

    # Build heatmap groups
    heatmap_html = ""
    for sec, stocks in sorted(sectors.items(), key=lambda x: -len(x[1])):
        if not stocks:
            continue
        blocks = ""
        for sym, info in sorted(stocks, key=lambda x: -abs(x[1]["chg"])):
            chg = info["chg"]
            col = _chg_color(chg)
            sign = "+" if chg >= 0 else ""
            blocks += (f'<a href="/chart/{sym}" style="text-decoration:none;display:block;background:{col};'
                       f'border-radius:6px;padding:8px;min-width:60px;min-height:50px;text-align:center;'
                       f'color:#fff;border:1px solid rgba(255,255,255,0.1);transition:filter .15s" '
                       f'title="{info["company"]}: {sign}{chg:.2f}%" '
                       f'onmouseover="this.style.filter=\'brightness(1.3)\'" '
                       f'onmouseout="this.style.filter=\'\'">'
                       f'<div style="font-size:12px;font-weight:800;line-height:1.2">{sym}</div>'
                       f'<div style="font-size:10px;margin-top:2px">{sign}{chg:.2f}%</div></a>')
        heatmap_html += (f'<div style="margin-bottom:16px">'
                         f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
                         f'color:var(--mid);letter-spacing:.5px;margin-bottom:6px">{sec}</div>'
                         f'<div style="display:flex;flex-wrap:wrap;gap:4px">{blocks}</div></div>')

    html = f"""
<div style="margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
    <span class="card-hdr" style="margin-bottom:0">🟩 Market Heatmap</span>
  </div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">{sector_pills}</div>
  <div style="font-size:11px;color:var(--muted)">คลิกที่หุ้นเพื่อดู chart · สีเขียว = บวก · สีแดง = ลบ</div>
</div>
<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px">
  <div class="card-sm" style="padding:6px 10px"><span style="background:#1a6644;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">+3%+</span> Strong</div>
  <div class="card-sm" style="padding:6px 10px"><span style="background:#26a69a;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">+1–3%</span> Bullish</div>
  <div class="card-sm" style="padding:6px 10px"><span style="background:#2d8a6a;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">0–1%</span> Mild+</div>
  <div class="card-sm" style="padding:6px 10px"><span style="background:#8a2d2d;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">0–1%↓</span> Mild-</div>
  <div class="card-sm" style="padding:6px 10px"><span style="background:#ef5350;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">1–3%↓</span> Bearish</div>
  <div class="card-sm" style="padding:6px 10px"><span style="background:#b71c1c;color:#fff;padding:2px 6px;border-radius:4px;font-size:10px">3%+↓</span> Strong-</div>
</div>
<div class="card">
  {heatmap_html or '<div style="color:var(--muted);padding:24px;text-align:center">ยังไม่มีข้อมูล — รอ market data refresh</div>'}
</div>
"""
    return _base("heatmap", "Market Heatmap", html, user, _ticker_html(market_data), "")


# ─── ANALYTICS PAGE ───────────────────────────────────────────────────────────

def analytics_page(user: dict, market_data: dict, thb: float) -> str:
    port = user.get("portfolio", {})

    def _daily_rets(values: list) -> list:
        if len(values) < 2:
            return []
        return [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]

    # Gather portfolio stock data
    port_data = []
    for sym, info in port.items():
        d = market_data.get(sym, {})
        closes = d.get("closes", [])
        if not closes or not d.get("price"):
            continue
        port_data.append({
            "sym": sym,
            "shares": float(info.get("shares", 0)),
            "cost": float(info.get("cost", 0)),
            "price": d["price"],
            "closes": closes,
            "sector": _get_vault_sector(sym),
        })

    if not port_data:
        msg = '<div class="card" style="text-align:center;padding:40px"><div style="font-size:16px;color:var(--muted)">ยังไม่มี Portfolio — ไปตั้งค่าที่ Settings ก่อนนะ</div></div>'
        return _base("analytics", "Portfolio Analytics", msg, user, "", "")

    qqq_closes  = (market_data.get("QQQ")  or {}).get("closes", [])
    sp500_closes = (market_data.get("IVV") or {}).get("closes", [])

    min_days = min(len(pd["closes"]) for pd in port_data)
    if qqq_closes:
        min_days = min(min_days, len(qqq_closes))
    min_days = min(min_days, 252)

    if min_days < 20:
        msg = '<div class="card" style="text-align:center;padding:40px"><div style="font-size:16px;color:var(--muted)">ข้อมูลไม่เพียงพอ (ต้องการ &gt; 20 วัน)</div></div>'
        return _base("analytics", "Portfolio Analytics", msg, user, "", "")

    # Portfolio daily values
    port_daily = []
    for i in range(min_days):
        idx = -(min_days - i)
        val = sum(pd["shares"] * pd["closes"][idx] for pd in port_data if len(pd["closes"]) >= min_days)
        port_daily.append(val)

    port_rets   = _daily_rets(port_daily)
    qqq_rets    = _daily_rets(qqq_closes[-min_days:]) if len(qqq_closes) >= min_days else []

    total_cost = sum(pd["shares"] * pd["cost"] for pd in port_data)
    total_val  = sum(pd["shares"] * pd["price"] for pd in port_data)
    total_return = (total_val - total_cost) / total_cost * 100 if total_cost else 0

    trading_days = len(port_daily)
    ann_return = ((1 + total_return / 100) ** (252 / trading_days) - 1) * 100 if trading_days > 0 else 0

    if len(port_rets) >= 5:
        mean_r   = sum(port_rets) / len(port_rets)
        variance = sum((r - mean_r) ** 2 for r in port_rets) / len(port_rets)
        volatility = (variance ** 0.5) * (252 ** 0.5) * 100
    else:
        volatility = None

    risk_free = 5.0
    sharpe = (ann_return - risk_free) / volatility if volatility and volatility > 0 else None

    # Max drawdown
    peak = port_daily[0]; max_dd = 0.0
    for v in port_daily:
        if v > peak: peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd: max_dd = dd

    # Beta vs QQQ
    beta = None
    if len(port_rets) >= 5 and len(qqq_rets) >= 5:
        min_l = min(len(port_rets), len(qqq_rets))
        pr, qr = port_rets[-min_l:], qqq_rets[-min_l:]
        mpr = sum(pr)/len(pr); mqr = sum(qr)/len(qr)
        cov   = sum((pr[i]-mpr)*(qr[i]-mqr) for i in range(min_l)) / min_l
        var_q = sum((r-mqr)**2 for r in qr) / len(qr)
        beta = round(cov / var_q, 2) if var_q else None

    win_rate = sum(1 for r in port_rets if r > 0) / len(port_rets) * 100 if port_rets else None

    def fmt_stat(val, suffix="", decimals=1, show_sign=False):
        if val is None: return "N/A"
        s = "+" if (show_sign and val >= 0) else ""
        return f"{s}{val:.{decimals}f}{suffix}"

    # Chart data (last 180 days, normalized to 100)
    chart_days = min(min_days, 180)
    port_chart  = port_daily[-chart_days:]
    qqq_chart   = qqq_closes[-chart_days:]  if len(qqq_closes)  >= chart_days else qqq_closes
    sp500_chart = sp500_closes[-chart_days:] if len(sp500_closes) >= chart_days else sp500_closes

    def normalize(values):
        if not values or values[0] == 0: return [100.0] * len(values)
        b = values[0]
        return [round(v / b * 100, 2) for v in values]

    port_norm  = normalize(port_chart)
    qqq_norm   = normalize(qqq_chart)
    sp500_norm = normalize(sp500_chart)
    labels = [f"D{i+1}" for i in range(max(len(port_norm), len(qqq_norm)))]

    # Monthly returns (~21 trading days per month)
    monthly_labels, monthly_vals = [], []
    if len(port_daily) >= 22:
        for i in range(0, len(port_daily)-1, 21):
            s = port_daily[i]; e = port_daily[min(i+21, len(port_daily)-1)]
            monthly_vals.append(round((e-s)/s*100, 2) if s else 0)
            monthly_labels.append(f"M{i//21+1}")
    monthly_colors = ["rgba(38,166,154,0.7)" if v >= 0 else "rgba(239,83,80,0.7)" for v in monthly_vals]

    # Per-stock tables
    contrib_rows = ""
    for pd_item in sorted(port_data, key=lambda x: -x["shares"]*x["price"]):
        sym  = pd_item["sym"]
        val  = pd_item["shares"] * pd_item["price"]
        wt   = val / total_val * 100 if total_val else 0
        sr   = (pd_item["price"] - pd_item["cost"]) / pd_item["cost"] * 100 if pd_item["cost"] else 0
        spnl = (pd_item["price"] - pd_item["cost"]) * pd_item["shares"]
        sc   = spnl / total_cost * 100 if total_cost else 0
        rc   = "var(--green)" if sr >= 0 else "var(--red)"
        cc2  = "var(--green)" if sc >= 0 else "var(--red)"
        contrib_rows += f"""
        <tr>
          <td><b>{sym}</b></td>
          <td>{wt:.1f}%</td>
          <td style="color:{cc2}">{'+' if sc>=0 else ''}{sc:.2f}%</td>
          <td style="color:{rc}">{'+' if sr>=0 else ''}{sr:.1f}%</td>
        </tr>"""

    risk_rows = ""
    for pd_item in port_data:
        sym    = pd_item["sym"]
        cl     = pd_item["closes"]
        if len(cl) < 20: continue
        dr     = _daily_rets(cl[-252:] if len(cl) >= 252 else cl)
        if not dr: continue
        mdr    = sum(dr)/len(dr)
        vol_s  = (sum((r-mdr)**2 for r in dr)/len(dr))**0.5 * (252**0.5) * 100
        pk_s   = cl[0]; md_s = 0.0
        for c in cl:
            if c > pk_s: pk_s = c
            dd_s = (pk_s-c)/pk_s*100 if pk_s else 0
            if dd_s > md_s: md_s = dd_s
        beta_s = None
        if len(qqq_closes) >= len(dr):
            qr_s  = _daily_rets(qqq_closes[-len(dr):])
            if len(qr_s) == len(dr):
                mn_dr = sum(dr)/len(dr); mn_qr = sum(qr_s)/len(qr_s)
                cov_s = sum((dr[i]-mn_dr)*(qr_s[i]-mn_qr) for i in range(len(dr)))/len(dr)
                vq_s  = sum((r-mn_qr)**2 for r in qr_s)/len(qr_s)
                beta_s = round(cov_s/vq_s, 2) if vq_s else None
        vc = "var(--red)" if vol_s > 30 else "var(--gold)" if vol_s > 20 else "var(--green)"
        risk_rows += f"""
        <tr>
          <td><b>{sym}</b></td>
          <td style="color:{vc}">{vol_s:.1f}%</td>
          <td>{beta_s if beta_s is not None else 'N/A'}</td>
          <td style="color:var(--red)">{md_s:.1f}%</td>
        </tr>"""

    # Sector exposure
    sec_vals: dict = {}
    for pd_item in port_data:
        sec_vals[pd_item["sector"]] = sec_vals.get(pd_item["sector"], 0) + pd_item["shares"] * pd_item["price"]
    sector_labels = list(sec_vals.keys())
    sector_pcts   = [round(v / total_val * 100, 1) for v in sec_vals.values()]
    PALETTE = ["rgba(45,212,191,.7)","rgba(41,98,255,.7)","rgba(156,39,176,.7)",
               "rgba(240,180,41,.7)","rgba(38,166,154,.7)","rgba(255,107,53,.7)",
               "rgba(239,83,80,.7)","rgba(33,150,243,.7)","rgba(76,175,80,.7)"]
    sector_colors_js = [PALETTE[i % len(PALETTE)] for i in range(len(sector_labels))]

    tr_col = "var(--green)" if total_return >= 0 else "var(--red)"
    an_col = "var(--green)" if ann_return  >= 0 else "var(--red)"
    sh_col = "var(--green)" if (sharpe or 0) >= 0 else "var(--red)"
    vol_c  = "var(--red)" if (volatility or 0) > 30 else "var(--gold)" if (volatility or 0) > 20 else "var(--green)"
    beta_d = ("Conservative" if beta is not None and beta < 0.8
              else "Market-like" if beta is not None and beta < 1.2 else "Aggressive")

    html = f"""
<div class="g3" style="margin-bottom:16px">
  <div class="stat-card" style="border-top:3px solid {tr_col}">
    <div class="stat-label">Total Return</div>
    <div class="stat-value" style="color:{tr_col}">{fmt_stat(total_return,'%',1,True)}</div>
    <div class="stat-sub">Cost basis ${total_cost:,.0f}</div>
  </div>
  <div class="stat-card" style="border-top:3px solid {an_col}">
    <div class="stat-label">Annualized Return</div>
    <div class="stat-value" style="color:{an_col}">{fmt_stat(ann_return,'%',1,True)}</div>
    <div class="stat-sub">{trading_days} trading days</div>
  </div>
  <div class="stat-card" style="border-top:3px solid {vol_c}">
    <div class="stat-label">Volatility (Ann.)</div>
    <div class="stat-value" style="color:{vol_c}">{fmt_stat(volatility,'%')}</div>
    <div class="stat-sub">σ daily returns × √252</div>
  </div>
  <div class="stat-card" style="border-top:3px solid {sh_col}">
    <div class="stat-label">Sharpe Ratio</div>
    <div class="stat-value" style="color:{sh_col}">{fmt_stat(sharpe,'',2)}</div>
    <div class="stat-sub">Rf=5% · {'Good' if (sharpe or 0)>1 else 'Fair' if (sharpe or 0)>0 else 'Poor'}</div>
  </div>
  <div class="stat-card" style="border-top:3px solid var(--red)">
    <div class="stat-label">Max Drawdown</div>
    <div class="stat-value" style="color:var(--red)">-{max_dd:.1f}%</div>
    <div class="stat-sub">Peak-to-trough decline</div>
  </div>
  <div class="stat-card" style="border-top:3px solid var(--gold)">
    <div class="stat-label">Beta vs QQQ</div>
    <div class="stat-value">{fmt_stat(beta,'',2)}</div>
    <div class="stat-sub">{beta_d}</div>
  </div>
</div>

<div class="g2" style="margin-bottom:16px">
  <div class="card">
    <div class="card-hdr">📈 Portfolio vs QQQ vs S&amp;P500 (normalized 100)</div>
    <canvas id="perfChart" style="max-height:220px"></canvas>
  </div>
  <div class="card">
    <div class="card-hdr">📅 Monthly Returns</div>
    <canvas id="monthlyChart" style="max-height:220px"></canvas>
  </div>
</div>

<div class="g2" style="margin-bottom:16px">
  <div class="card">
    <div class="card-hdr">💰 Stock Contribution to P&amp;L</div>
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>Weight</th><th>Contrib</th><th>Return</th></tr></thead>
      <tbody>{contrib_rows or '<tr><td colspan="4" style="text-align:center;color:var(--muted)">—</td></tr>'}</tbody>
    </table>
  </div>
  <div class="card">
    <div class="card-hdr">⚠️ Risk per Stock</div>
    <table class="tbl">
      <thead><tr><th>Symbol</th><th>Volatility</th><th>Beta</th><th>Max DD</th></tr></thead>
      <tbody>{risk_rows or '<tr><td colspan="4" style="text-align:center;color:var(--muted)">ข้อมูลไม่เพียงพอ</td></tr>'}</tbody>
    </table>
  </div>
</div>

<div class="card">
  <div class="card-hdr">🏭 Sector Exposure</div>
  <canvas id="sectorChart" style="max-height:180px"></canvas>
</div>
"""

    js = f"""
const perfCtx = document.getElementById('perfChart').getContext('2d');
new Chart(perfCtx, {{
  type: 'line',
  data: {{
    labels: {json.dumps(labels[:max(len(port_norm),len(qqq_norm))])},
    datasets: [
      {{label:'Portfolio',data:{json.dumps(port_norm)},borderColor:'#2dd4bf',borderWidth:2,pointRadius:0,fill:false,tension:.2}},
      {{label:'QQQ',data:{json.dumps(qqq_norm)},borderColor:'#f0b429',borderWidth:1.5,pointRadius:0,fill:false,tension:.2,borderDash:[4,2]}},
      {{label:'S&P500',data:{json.dumps(sp500_norm)},borderColor:'#2962ff',borderWidth:1.5,pointRadius:0,fill:false,tension:.2,borderDash:[2,4]}}
    ]
  }},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{labels:{{color:'#d1d4dc',font:{{size:11}}}}}},tooltip:{{mode:'index',intersect:false}}}},
    scales:{{x:{{ticks:{{color:'#787b86',maxTicksLimit:8,font:{{size:10}}}},grid:{{color:'#2a2e39'}}}},
             y:{{ticks:{{color:'#787b86',font:{{size:10}}}},grid:{{color:'#2a2e39'}},
                title:{{display:true,text:'Normalized (100=start)',color:'#787b86',font:{{size:10}}}}}}}}
  }}
}});

const moCtx = document.getElementById('monthlyChart').getContext('2d');
new Chart(moCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(monthly_labels)},
    datasets: [{{label:'Monthly %',data:{json.dumps(monthly_vals)},backgroundColor:{json.dumps(monthly_colors)},borderRadius:4}}]
  }},
  options:{{responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.raw.toFixed(2)+'%'}}}}}},
    scales:{{x:{{ticks:{{color:'#787b86',font:{{size:10}}}},grid:{{color:'#2a2e39'}}}},
             y:{{ticks:{{color:'#787b86',font:{{size:10}},callback:v=>v+'%'}},grid:{{color:'#2a2e39'}}}}}}
  }}
}});

const secCtx = document.getElementById('sectorChart').getContext('2d');
new Chart(secCtx, {{
  type: 'bar',
  data: {{
    labels: {json.dumps(sector_labels)},
    datasets: [{{label:'Weight %',data:{json.dumps(sector_pcts)},backgroundColor:{json.dumps(sector_colors_js)},borderRadius:4}}]
  }},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:true,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>ctx.raw.toFixed(1)+'%'}}}}}},
    scales:{{x:{{ticks:{{color:'#787b86',font:{{size:10}},callback:v=>v+'%'}},grid:{{color:'#2a2e39'}},max:100}},
             y:{{ticks:{{color:'#787b86',font:{{size:10}}}},grid:{{color:'#2a2e39'}}}}}}
  }}
}});
"""
    return _base("analytics", "Portfolio Analytics", html, user, "", js)


# ─── SCANNER PAGE ─────────────────────────────────────────────────────────────

def _scan_stock(sym: str, d: dict) -> list:
    """Run all technical scans on a stock. Returns list of signal dicts."""
    signals = []
    closes  = d.get("closes", [])
    price   = d.get("price", 0)
    high_52 = d.get("high", 0)
    low_52  = d.get("low", 0)
    if not closes or len(closes) < 15 or not price:
        return signals

    rsi   = _calc_rsi(closes)
    ma20  = _ma(closes, 20)
    ma50  = _ma(closes, 50)  if len(closes) >= 50  else None
    ma200 = _ma(closes, 200) if len(closes) >= 200 else None

    if rsi and rsi < 30:
        signals.append({"type":"RSI","signal":"RSI Oversold","direction":"BUY","detail":f"RSI={rsi}"})
    if rsi and rsi > 70:
        signals.append({"type":"RSI","signal":"RSI Overbought","direction":"SELL","detail":f"RSI={rsi}"})

    # MACD cross (last 3 days)
    if len(closes) >= 40:
        def _ema(data, n):
            k = 2/(n+1); e = data[0]; r = [e]
            for v in data[1:]: e = v*k + e*(1-k); r.append(e)
            return r
        fast_e = _ema(closes, 12); slow_e = _ema(closes, 26)
        macd_l = [f-s for f,s in zip(fast_e, slow_e)]
        sig_l  = _ema(macd_l, 9)
        for i in range(-3, -1):
            if abs(i) >= len(macd_l): continue
            if macd_l[i-1] < sig_l[i-1] and macd_l[i] > sig_l[i]:
                signals.append({"type":"MACD","signal":"MACD Bullish Cross","direction":"BUY","detail":f"MACD={macd_l[i]:.3f}"})
                break
            if macd_l[i-1] > sig_l[i-1] and macd_l[i] < sig_l[i]:
                signals.append({"type":"MACD","signal":"MACD Bearish Cross","direction":"SELL","detail":f"MACD={macd_l[i]:.3f}"})
                break

    # BB Squeeze
    if len(closes) >= 20 and price > 0:
        sl   = closes[-20:]
        mean = sum(sl)/20
        std  = (sum((x-mean)**2 for x in sl)/20)**0.5
        bw   = 4 * std
        if bw / price < 0.05:
            signals.append({"type":"Volatility","signal":"BB Squeeze","direction":"NEUTRAL","detail":f"Width {bw/price*100:.1f}% of price"})

    if ma200 and price > ma200:
        signals.append({"type":"MA","signal":"Price > MA200","direction":"BUY","detail":f"MA200=${ma200:,.0f}"})

    # Golden / Death Cross (MA50 vs MA200 changed in last 30 days)
    if ma50 and ma200 and len(closes) >= 230:
        old_ma50  = _ma(closes[:-30], 50)  if len(closes)-30 >= 50  else None
        old_ma200 = _ma(closes[:-30], 200) if len(closes)-30 >= 200 else None
        if old_ma50 and old_ma200:
            if old_ma50 < old_ma200 and ma50 > ma200:
                signals.append({"type":"MA","signal":"Golden Cross","direction":"BUY","detail":"MA50 crossed above MA200"})
            elif old_ma50 > old_ma200 and ma50 < ma200:
                signals.append({"type":"MA","signal":"Death Cross","direction":"SELL","detail":"MA50 crossed below MA200"})

    if high_52 and price > 0 and (high_52 - price) / high_52 < 0.05:
        signals.append({"type":"MA","signal":"Near 52W High","direction":"NEUTRAL","detail":f"${price:,.2f} vs H${high_52:,.0f}"})
    if low_52 and price > 0 and (price - low_52) / price < 0.05:
        signals.append({"type":"RSI","signal":"Near 52W Low","direction":"BUY","detail":f"${price:,.2f} vs L${low_52:,.0f}"})

    return signals


def scanner_page(user: dict, market_data: dict) -> str:
    port = user.get("portfolio", {})
    scan_results = []
    for sym, d in market_data.items():
        if sym.startswith("_") or "=" in sym or "BTC" in sym:
            continue
        if not d.get("closes") or not d.get("price"):
            continue
        signals = _scan_stock(sym, d)
        closes  = d.get("closes", [])
        rsi     = _calc_rsi(closes) if len(closes) >= 15 else None
        for sig in signals:
            scan_results.append({
                "sym": sym, "price": d["price"],
                "chg": d.get("chg") or d.get("change_pct") or 0,
                "rsi": rsi, "signal_type": sig["type"],
                "signal": sig["signal"], "direction": sig["direction"],
                "detail": sig["detail"], "in_port": sym in port,
            })

    dir_order = {"BUY": 0, "SELL": 1, "NEUTRAL": 2}
    scan_results.sort(key=lambda x: (dir_order.get(x["direction"], 3), x["sym"]))

    def row_html(r):
        dc   = "var(--green)" if r["direction"]=="BUY" else "var(--red)" if r["direction"]=="SELL" else "var(--mid)"
        chg  = r["chg"]
        cc3  = "var(--green)" if chg >= 0 else "var(--red)"
        sign = "+" if chg >= 0 else ""
        pb   = ' <span style="font-size:9px;color:var(--teal);font-weight:700">PORT</span>' if r["in_port"] else ""
        return (f'<tr class="scan-row" data-type="{r["signal_type"]}" data-dir="{r["direction"]}">'
                f'<td><a href="/chart/{r["sym"]}" style="font-weight:800;color:var(--text);text-decoration:none">{r["sym"]}</a>{pb}</td>'
                f'<td>${r["price"]:,.2f}</td>'
                f'<td style="color:{cc3}">{sign}{chg:.2f}%</td>'
                f'<td>{_rsi_bar(r["rsi"])}</td>'
                f'<td style="color:{dc};font-weight:700">{r["signal"]}</td>'
                f'<td style="color:{dc};font-weight:700;font-size:11px">{r["direction"]}</td>'
                f'<td style="font-size:11px;color:var(--muted)">{r["detail"]}</td>'
                f'<td><a href="/chart/{r["sym"]}" class="btn btn-ghost btn-sm">📉</a></td></tr>')

    buy_count     = sum(1 for r in scan_results if r["direction"]=="BUY")
    sell_count    = sum(1 for r in scan_results if r["direction"]=="SELL")
    neutral_count = sum(1 for r in scan_results if r["direction"]=="NEUTRAL")
    scanned_syms  = len(set(r["sym"] for r in scan_results))
    all_rows      = "".join(row_html(r) for r in scan_results)

    html = f"""
<div class="g3" style="margin-bottom:16px">
  <div class="stat-card" style="border-top:3px solid var(--green)">
    <div class="stat-label">BUY Signals</div>
    <div class="stat-value" style="color:var(--green)">{buy_count}</div>
    <div class="stat-sub">Bullish conditions</div>
  </div>
  <div class="stat-card" style="border-top:3px solid var(--red)">
    <div class="stat-label">SELL Signals</div>
    <div class="stat-value" style="color:var(--red)">{sell_count}</div>
    <div class="stat-sub">Bearish conditions</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">NEUTRAL / Watch</div>
    <div class="stat-value" style="color:var(--mid)">{neutral_count}</div>
    <div class="stat-sub">Monitor conditions</div>
  </div>
</div>

<div style="display:flex;gap:4px;margin-bottom:12px;flex-wrap:wrap;border-bottom:1px solid var(--border);padding-bottom:8px">
  <button class="tab active" onclick="filterScanner('all',this)">All ({len(scan_results)})</button>
  <button class="tab" onclick="filterScanner('RSI',this)">RSI</button>
  <button class="tab" onclick="filterScanner('MACD',this)">MACD</button>
  <button class="tab" onclick="filterScanner('MA',this)">MA / Cross</button>
  <button class="tab" onclick="filterScanner('Volatility',this)">Volatility</button>
  <button class="tab" onclick="filterScanner('BUY',this)" style="margin-left:12px;color:var(--green)">BUY only</button>
  <button class="tab" onclick="filterScanner('SELL',this)" style="color:var(--red)">SELL only</button>
</div>

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <div class="card-hdr" style="margin-bottom:0">🔍 Scanner — {scanned_syms} หุ้นที่สแกน</div>
    <a href="/refresh" class="btn btn-ghost btn-sm">🔄 Refresh Data</a>
  </div>
  <div style="overflow-x:auto">
    <table class="tbl" id="scannerTable">
      <thead><tr>
        <th>Symbol</th><th>Price</th><th>Today</th><th>RSI</th><th>Signal</th><th>Direction</th><th>Detail</th><th></th>
      </tr></thead>
      <tbody id="scannerBody">{all_rows or '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">ยังไม่มีข้อมูล — รอ market data หรือกด Refresh</td></tr>'}</tbody>
    </table>
  </div>
</div>
"""

    js = """
function filterScanner(type, btn) {
  document.querySelectorAll('[onclick^="filterScanner"]').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const TYPE_FILTERS = ['RSI','MACD','MA','Volatility'];
  const DIR_FILTERS  = ['BUY','SELL','NEUTRAL'];
  document.querySelectorAll('#scannerBody .scan-row').forEach(tr => {
    const t = tr.dataset.type, d = tr.dataset.dir;
    let show = type === 'all';
    if (!show && TYPE_FILTERS.includes(type)) show = t === type;
    if (!show && DIR_FILTERS.includes(type))  show = d === type;
    tr.style.display = show ? '' : 'none';
  });
}
"""
    return _base("scanner", "Technical Scanner", html, user, "", js)


def backtest_page(user: dict, market_data: dict) -> str:
    """Backtest page — run strategy simulations against historical data."""
    port      = list(user.get("portfolio", {}).keys())
    watchlist = user.get("watchlist", [])
    all_syms  = list(dict.fromkeys(port + watchlist)) or ["NVDA", "MSFT", "GOOGL", "AMZN", "TSLA"]

    sym_opts = "".join(
        f'<option value="{s}">{s}</option>' for s in all_syms
    )
    # Add extra popular symbols
    extra_syms = ["NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "AVGO", "META", "AMD", "AAPL"]
    for s in extra_syms:
        if s not in all_syms:
            sym_opts += f'<option value="{s}">{s}</option>'

    html = f"""
<div class="card" style="margin-bottom:16px;padding:16px 20px">
  <div class="card-hdr" style="margin-bottom:12px">⏪ Backtest Strategy</div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Symbol</label>
      <select id="bt-sym" style="min-width:100px">
        {sym_opts}
      </select>
    </div>
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Strategy</label>
      <select id="bt-strategy">
        <option value="rsi">RSI Mean Reversion</option>
        <option value="ma">MA Crossover</option>
        <option value="bb">Bollinger Bands</option>
        <option value="macd">MACD Signal</option>
      </select>
    </div>
    <div>
      <label style="font-size:11px;color:var(--mid);display:block;margin-bottom:4px">Period</label>
      <select id="bt-period">
        <option value="6mo">6 Months</option>
        <option value="1y" selected>1 Year</option>
        <option value="2y">2 Years</option>
        <option value="5y">5 Years</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="runBacktest()" id="bt-run-btn">▶ Run Backtest</button>
  </div>
</div>

<!-- Strategy info cards -->
<div class="g4" style="margin-bottom:16px">
  <div class="card-sm" style="border-left:3px solid var(--teal)">
    <div class="card-hdr">RSI Mean Reversion</div>
    <div style="font-size:11px;color:var(--mid);line-height:1.6">Buy RSI &lt; 30<br>Sell RSI &gt; 70</div>
  </div>
  <div class="card-sm" style="border-left:3px solid var(--blue)">
    <div class="card-hdr">MA Crossover</div>
    <div style="font-size:11px;color:var(--mid);line-height:1.6">Buy MA20 crosses above MA50<br>Sell MA20 crosses below MA50</div>
  </div>
  <div class="card-sm" style="border-left:3px solid var(--gold)">
    <div class="card-hdr">Bollinger Bands</div>
    <div style="font-size:11px;color:var(--mid);line-height:1.6">Buy at lower band<br>Sell at upper band</div>
  </div>
  <div class="card-sm" style="border-left:3px solid var(--purple)">
    <div class="card-hdr">MACD Signal</div>
    <div style="font-size:11px;color:var(--mid);line-height:1.6">Buy MACD crosses above signal<br>Sell MACD crosses below signal</div>
  </div>
</div>

<!-- Results (hidden until run) -->
<div id="bt-results" style="display:none">
  <div class="g4" style="margin-bottom:16px" id="bt-stats"></div>
  <div class="card" style="margin-bottom:16px">
    <div class="card-hdr">Equity Curve (Normalized to 100)</div>
    <canvas id="bt-chart" height="280"></canvas>
  </div>
  <div class="card">
    <div class="card-hdr">Trades (last 30)</div>
    <div style="overflow-x:auto">
      <table class="tbl" id="bt-trades-tbl">
        <thead><tr>
          <th>Buy Date</th><th>Sell Date</th><th>Buy Price</th><th>Sell Price</th><th>Shares</th><th>P&L</th>
        </tr></thead>
        <tbody id="bt-trades"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Loading spinner -->
<div id="bt-loading" style="display:none;text-align:center;padding:40px">
  <span class="spin" style="font-size:30px">⟳</span>
  <div style="margin-top:12px;color:var(--mid)">Running backtest...</div>
</div>
"""

    js = """
let _btChart = null;

async function runBacktest() {
  const sym      = document.getElementById('bt-sym').value;
  const strategy = document.getElementById('bt-strategy').value;
  const period   = document.getElementById('bt-period').value;

  document.getElementById('bt-results').style.display  = 'none';
  document.getElementById('bt-loading').style.display  = 'block';
  document.getElementById('bt-run-btn').disabled = true;

  try {
    const res  = await fetch(`/api/backtest?sym=${sym}&strategy=${strategy}&period=${period}`);
    const data = await res.json();

    document.getElementById('bt-loading').style.display = 'none';
    document.getElementById('bt-run-btn').disabled = false;

    if (data.error) {
      alert('Backtest error: ' + data.error);
      return;
    }

    // Stat cards
    const retColor  = data.total_return >= 0 ? 'var(--green)' : 'var(--red)';
    const ddColor   = 'var(--red)';
    document.getElementById('bt-stats').innerHTML = `
      <div class="card-sm">
        <div class="stat-label">Total Return</div>
        <div class="stat-val" style="color:${retColor}">${data.total_return >= 0 ? '+' : ''}${data.total_return.toFixed(2)}%</div>
        <div class="stat-sub">Start $10,000 → $${data.final_value.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}</div>
      </div>
      <div class="card-sm">
        <div class="stat-label">Win Rate</div>
        <div class="stat-val" style="color:${data.win_rate >= 50 ? 'var(--green)' : 'var(--red)'}">${data.win_rate.toFixed(1)}%</div>
        <div class="stat-sub">${data.num_trades} total trades</div>
      </div>
      <div class="card-sm">
        <div class="stat-label">Max Drawdown</div>
        <div class="stat-val" style="color:${ddColor}">-${data.max_drawdown.toFixed(2)}%</div>
        <div class="stat-sub">Peak-to-trough</div>
      </div>
      <div class="card-sm">
        <div class="stat-label"># Trades</div>
        <div class="stat-val">${data.num_trades}</div>
        <div class="stat-sub">${data.sym} · ${data.period}</div>
      </div>
    `;

    // Equity curve chart
    const ctx = document.getElementById('bt-chart').getContext('2d');
    if (_btChart) _btChart.destroy();
    _btChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.dates,
        datasets: [
          {
            label: 'Strategy',
            data: data.equity,
            borderColor: '#2dd4bf',
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.1,
            fill: false,
          },
          {
            label: 'Breakeven (100)',
            data: data.dates.map(() => 100),
            borderColor: '#787b86',
            borderWidth: 1,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { labels: { color: '#d1d4dc', font: { size: 11 } } },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: {
            ticks: { color: '#787b86', maxTicksLimit: 12, font: { size: 10 } },
            grid:  { color: '#363a45' }
          },
          y: {
            ticks: { color: '#787b86', callback: v => v.toFixed(0), font: { size: 10 } },
            grid:  { color: '#363a45' }
          }
        }
      }
    });

    // Trades table
    const tbody = document.getElementById('bt-trades');
    tbody.innerHTML = (data.trades || []).map(t => {
      const plColor = t.pl >= 0 ? 'var(--green)' : 'var(--red)';
      const plSign  = t.pl >= 0 ? '+' : '';
      return `<tr>
        <td>${t.buy_date}</td>
        <td>${t.sell_date}</td>
        <td>$${t.buy_price.toFixed(2)}</td>
        <td>$${t.sell_price.toFixed(2)}</td>
        <td>${t.shares}</td>
        <td style="color:${plColor};font-weight:700">${plSign}$${t.pl.toFixed(2)}</td>
      </tr>`;
    }).join('');

    document.getElementById('bt-results').style.display = 'block';
  } catch(e) {
    document.getElementById('bt-loading').style.display = 'none';
    document.getElementById('bt-run-btn').disabled = false;
    alert('Error: ' + e.message);
  }
}
"""

    return _base("backtest", "Backtest", html, user, "", js)


# ─── Portfolio Attribution ────────────────────────────────────────────────────

def _portfolio_attribution_html(port_rows: list) -> str:
    """Show P&L contribution bar chart (top winners + losers)."""
    if not port_rows:
        return ""
    total_abs = sum(abs(r["pnl"]) for r in port_rows) or 1
    sorted_rows = sorted(port_rows, key=lambda r: r["pnl"], reverse=True)
    bars = ""
    for r in sorted_rows:
        pct = r["pnl"] / total_abs * 100
        col = "var(--green)" if r["pnl"] >= 0 else "var(--red)"
        sign = "+" if r["pnl"] >= 0 else ""
        width = abs(pct)
        bars += f"""<div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
            <span style="font-weight:700">{r['sym']}</span>
            <span style="color:{col};font-weight:700">{sign}${r['pnl']:,.0f} <span style="font-size:10px;color:var(--muted)">({sign}{r['pnl_pct']:.1f}%)</span></span>
          </div>
          <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden">
            <div style="height:100%;width:{min(width,100):.1f}%;background:{col};border-radius:3px"></div>
          </div>
        </div>"""
    return f'<div class="card" style="margin-bottom:16px"><div class="card-hdr">📈 P&L Attribution</div>{bars}</div>'


# ─── Economic Calendar Widget ─────────────────────────────────────────────────

def _econ_calendar_widget() -> str:
    """Hardcoded upcoming macro events (2026)."""
    from datetime import date
    today = date.today()
    events = [
        ("2026-07-29", "FOMC Rate Decision", "🏛️", "red"),
        ("2026-07-30", "GDP Q2 Advance",     "📊", "blue"),
        ("2026-08-12", "CPI July",           "💰", "gold"),
        ("2026-08-14", "PPI July",           "🏭", "mid"),
        ("2026-08-27", "Jackson Hole",       "🏔️", "purple"),
        ("2026-09-10", "CPI August",         "💰", "gold"),
        ("2026-09-16", "FOMC Rate Decision", "🏛️", "red"),
        ("2026-10-13", "CPI September",      "💰", "gold"),
        ("2026-10-29", "FOMC Rate Decision", "🏛️", "red"),
        ("2026-11-05", "Nonfarm Payrolls",   "👷", "teal"),
        ("2026-11-12", "CPI October",        "💰", "gold"),
        ("2026-12-16", "FOMC Rate Decision", "🏛️", "red"),
    ]
    col_map = {"red":"var(--red)","blue":"var(--blue)","gold":"var(--gold)",
               "mid":"var(--mid)","purple":"var(--purple)","teal":"var(--teal)"}
    rows = ""
    for ev_date_str, label, icon, col_key in events:
        try:
            ev_date = date.fromisoformat(ev_date_str)
        except Exception:
            continue
        if ev_date < today:
            continue
        days = (ev_date - today).days
        col = col_map.get(col_key, "var(--mid)")
        urgency = "font-weight:700" if days <= 7 else ""
        rows += f"""<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--bg3)">
          <span style="font-size:16px">{icon}</span>
          <div style="flex:1">
            <div style="font-size:12px;{urgency}">{label}</div>
            <div style="font-size:11px;color:var(--muted)">{ev_date_str}</div>
          </div>
          <span style="font-size:11px;color:{col};font-weight:700;white-space:nowrap">{'TODAY' if days==0 else f'in {days}d'}</span>
        </div>"""
        if len(rows) > 3000:
            break
    if not rows:
        rows = '<div style="color:var(--muted);font-size:13px">ไม่มีอีเวนต์ใกล้นี้</div>'
    return f'<div class="card" style="margin-bottom:16px"><div class="card-hdr">📅 Economic Calendar</div>{rows}</div>'


# ─── Watchlist Page ──────────────────────────────────────────────────────────

def watchlist_page(user: dict, market_data: dict) -> str:
    watchlist = user.get("watchlist", [])
    wl_meta   = user.get("watchlist_meta", {})
    ticker_html = _ticker_html(market_data)

    # Build groups
    groups: dict = {}
    for sym in watchlist:
        g = (wl_meta.get(sym) or {}).get("group", "") or "All"
        groups.setdefault(g, []).append(sym)
    all_groups = sorted(groups.keys(), key=lambda x: (x == "All", x))

    cards = ""
    for sym in watchlist:
        d = market_data.get(sym, {})
        price = d.get("price", 0)
        closes = d.get("closes", [])
        rsi = _calc_rsi(closes) if closes else d.get("rsi")
        chg = d.get("chg", 0) or d.get("change_pct", 0)
        ma20 = _ma(closes, 20)
        ma50 = _ma(closes, 50)
        high52 = d.get("high", 0)
        low52  = d.get("low", 0)

        chg_col = "var(--green)" if chg >= 0 else "var(--red)"
        chg_s = "+" if chg >= 0 else ""
        rsi_col = "#ef4444" if (rsi or 50) >= 70 else "#22c55e" if (rsi or 50) <= 30 else "#f59e0b"
        action = "BUY" if (rsi and rsi <= 35) else "WATCH" if (rsi and rsi <= 45) else "AVOID" if (rsi and rsi >= 75) else "WAIT" if (rsi and rsi >= 65) else "NEUTRAL"
        rng = (high52 - low52) if high52 and low52 else 1
        pct_range = (price - low52) / rng * 100 if rng and price else 50

        vs_ma20 = f'+{(price/ma20-1)*100:.1f}%' if ma20 else '—'
        vs_ma50 = f'+{(price/ma50-1)*100:.1f}%' if ma50 else '—'
        if ma20 and price < ma20:
            vs_ma20 = f'{(price/ma20-1)*100:.1f}%'
        if ma50 and price < ma50:
            vs_ma50 = f'{(price/ma50-1)*100:.1f}%'

        sym_group = (wl_meta.get(sym) or {}).get("group", "All")
        cards += f"""
<div class="card" style="margin-bottom:12px" data-wl-group="{sym_group}">
  <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:10px">
    <div style="flex:1">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-weight:800;font-size:18px">{sym}</span>
        {f'<span style="font-size:10px;background:var(--bg3);padding:2px 6px;border-radius:4px;color:var(--mid)">{sym_group}</span>' if sym_group != "All" else ""}
        {_signal_badge(action)}
      </div>
      <div style="font-size:22px;font-weight:800;margin-top:4px">${f'{price:,.2f}' if price else '—'}</div>
      <div style="font-size:13px;color:{chg_col};font-weight:700">{chg_s}{chg:.2f}% today</div>
    </div>
    <div style="text-align:right">
      <canvas id="sp_{sym}" class="spark" style="width:100px;height:40px"></canvas>
    </div>
    <div style="display:flex;flex-direction:column;gap:4px">
      <a href="/chart/{sym}" class="btn btn-ghost btn-sm">📉 Chart</a>
      <form method="POST" action="/watchlist/remove" style="margin:0">
        <input type="hidden" name="sym" value="{sym}">
        <button class="btn btn-danger btn-sm" type="submit">✕ Remove</button>
      </form>
    </div>
  </div>

  <!-- Metrics row -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px">
    <div style="background:var(--bg3);border-radius:6px;padding:8px">
      <div style="font-size:10px;color:var(--muted);margin-bottom:2px">RSI(14)</div>
      <div style="font-size:14px;font-weight:700;color:{rsi_col}">{rsi or '—'}</div>
    </div>
    <div style="background:var(--bg3);border-radius:6px;padding:8px">
      <div style="font-size:10px;color:var(--muted);margin-bottom:2px">vs MA20</div>
      <div style="font-size:14px;font-weight:700;color:{'var(--green)' if ma20 and price>=ma20 else 'var(--red)'}">{vs_ma20}</div>
    </div>
    <div style="background:var(--bg3);border-radius:6px;padding:8px">
      <div style="font-size:10px;color:var(--muted);margin-bottom:2px">vs MA50</div>
      <div style="font-size:14px;font-weight:700;color:{'var(--green)' if ma50 and price>=ma50 else 'var(--red)'}">{vs_ma50}</div>
    </div>
    <div style="background:var(--bg3);border-radius:6px;padding:8px">
      <div style="font-size:10px;color:var(--muted);margin-bottom:2px">52W Range</div>
      <div style="font-size:11px;font-weight:700">{pct_range:.0f}%</div>
    </div>
  </div>

  <!-- 52W range bar -->
  <div style="margin-bottom:10px">
    <div class="pbar"><div class="pbar-fill" style="width:{pct_range:.0f}%;background:var(--teal)"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:3px">
      <span>L ${f'{low52:,.0f}' if low52 else '—'}</span><span>52W</span><span>H ${f'{high52:,.0f}' if high52 else '—'}</span>
    </div>
  </div>

  <!-- Group tag + actions -->
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px">
    <form method="POST" action="/watchlist/set-group" style="display:flex;gap:4px;align-items:center">
      <input type="hidden" name="sym" value="{sym}">
      <input name="group" placeholder="Group tag..." value="{(wl_meta.get(sym) or {}).get('group','')}" style="width:120px;font-size:11px;padding:3px 7px">
      <button class="btn btn-ghost btn-sm" type="submit">Tag</button>
    </form>
  </div>
  <!-- Expandable panels -->
  <div style="display:flex;gap:6px;flex-wrap:wrap">
    <button class="btn btn-ghost btn-sm" onclick="loadNews('{sym}',this)">📰 News</button>
    <button class="btn btn-ghost btn-sm" onclick="loadFundamentals('{sym}',this)">📊 Fundamentals</button>
    <button class="btn btn-ghost btn-sm" onclick="loadEarnings('{sym}',this)">📈 Earnings</button>
  </div>
  <div id="news-{sym}" style="display:none;margin-top:10px"></div>
  <div id="fund-{sym}" style="display:none;margin-top:10px"></div>
  <div id="earn-{sym}" style="display:none;margin-top:10px"></div>
</div>"""

    spark_js = ""
    for sym in watchlist:
        d = market_data.get(sym, {})
        closes = d.get("closes", [])
        if closes:
            chg = d.get("chg", 0)
            col = "#22c55e" if chg >= 0 else "#ef4444"
            spark_js += f"drawSpark('{sym}',{json.dumps(closes[-60:])},'{col}');"

    # Group tabs HTML
    group_tabs = ""
    if len(all_groups) > 1:
        group_tabs = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px">'
        group_tabs += '<button class="tf-btn active" id="gtab-__all__" onclick="filterGroup(\'__all__\',this)">All</button>'
        for g in all_groups:
            if g != "All":
                group_tabs += f'<button class="tf-btn" id="gtab-{g}" onclick="filterGroup(\'{g}\',this)">{g} <span style="color:var(--muted)">({len(groups[g])})</span></button>'
        group_tabs += "</div>"

    html = f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
  <div style="font-size:16px;font-weight:700">👁 Watchlist <span style="font-size:13px;color:var(--muted);font-weight:400">({len(watchlist)} stocks)</span></div>
  <form method="POST" action="/watchlist/add" style="display:flex;gap:6px">
    <input name="sym" placeholder="Symbol เช่น NVDA" style="width:140px;text-transform:uppercase" maxlength="10">
    <input name="group" placeholder="Group (opt)" style="width:120px">
    <button class="btn btn-primary btn-sm" type="submit">+ Add</button>
  </form>
</div>
{group_tabs}
<div id="wl-cards">
{cards or '<div class="card" style="text-align:center;color:var(--muted);padding:32px">ยังไม่มี watchlist — เพิ่ม symbol ด้านบน</div>'}
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
                 const g = ctx2.chart.ctx.createLinearGradient(0,0,0,40);
                 g.addColorStop(0, color+'33'); g.addColorStop(1, color+'00'); return g;
               }}
             }}] }},
    options: {{ animation:false, responsive:false, plugins:{{legend:{{display:false}},tooltip:{{enabled:false}}}},
               scales:{{x:{{display:false}},y:{{display:false}}}} }}
  }});
}}
{spark_js}

async function loadNews(sym, btn) {{
  const box = document.getElementById('news-' + sym);
  if (box.style.display !== 'none') {{ box.style.display = 'none'; return; }}
  box.style.display = 'block';
  box.innerHTML = '<span style="color:var(--muted);font-size:12px">⏳ กำลังโหลดข่าว...</span>';
  try {{
    const r = await fetch('/api/news/' + sym);
    const d = await r.json();
    if (!d.articles || !d.articles.length) {{
      box.innerHTML = '<span style="color:var(--muted);font-size:12px">ไม่พบข่าวล่าสุด</span>';
      return;
    }}
    box.innerHTML = d.articles.map(a => {{
      const sent = a.sentiment > 0.1 ? '🟢' : a.sentiment < -0.1 ? '🔴' : '⚪';
      return `<div style="padding:8px 0;border-bottom:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;margin-bottom:2px">${{sent}} <a href="${{a.url}}" target="_blank" style="color:var(--text);text-decoration:none">${{a.title}}</a></div>
        <div style="font-size:11px;color:var(--muted)">${{a.source}} · ${{a.published}}</div>
      </div>`;
    }}).join('');
  }} catch(e) {{
    box.innerHTML = '<span style="color:var(--red);font-size:12px">โหลดข่าวไม่ได้</span>';
  }}
}}

async function loadFundamentals(sym, btn) {{
  const box = document.getElementById('fund-' + sym);
  if (box.style.display !== 'none') {{ box.style.display = 'none'; return; }}
  box.style.display = 'block';
  box.innerHTML = '<span style="color:var(--muted);font-size:12px">⏳ กำลังโหลด fundamentals...</span>';
  try {{
    const r = await fetch('/api/fundamentals/' + sym);
    const d = await r.json();
    if (d.error) {{ box.innerHTML = `<span style="color:var(--red);font-size:12px">Error: ${{d.error}}</span>`; return; }}
    const row = (label, val) => `<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bg3);font-size:12px"><span style="color:var(--mid)">${{label}}</span><span style="font-weight:600">${{val}}</span></div>`;
    const recCol = d.analyst_rec.includes('Buy') ? 'var(--green)' : d.analyst_rec.includes('Sell') ? 'var(--red)' : 'var(--gold)';
    box.innerHTML = `
      <div style="font-size:13px;font-weight:700;margin-bottom:4px">${{d.name}}</div>
      <div style="font-size:11px;color:var(--mid);margin-bottom:10px">${{d.sector}} · ${{d.industry}}</div>
      <div style="background:var(--bg3);border-radius:6px;padding:10px;margin-bottom:10px;display:flex;gap:16px;flex-wrap:wrap">
        <div><div style="font-size:10px;color:var(--muted)">Analyst Consensus</div><div style="font-weight:800;color:${{recCol}}">${{d.analyst_rec}}</div><div style="font-size:10px;color:var(--muted)">${{d.n_analysts}} analysts</div></div>
        <div><div style="font-size:10px;color:var(--muted)">Price Target</div><div style="font-weight:800">$${{d.target_mean}}</div><div style="font-size:10px;color:var(--muted)">L:$${{d.target_low}} H:$${{d.target_high}}</div></div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        <div>${{row('Market Cap', d.market_cap)}}${{row('P/E (TTM)', d.pe)}}${{row('Forward P/E', d.forward_pe)}}${{row('EPS (TTM)', '$'+d.eps)}}${{row('Revenue', d.revenue)}}${{row('Rev Growth', d.revenue_growth)}}</div>
        <div>${{row('Gross Margin', d.gross_margin)}}${{row('ROE', d.roe)}}${{row('Debt/Equity', d.debt_equity)}}${{row('Dividend', d.dividend_yield)}}${{row('Beta', d.beta)}}${{row('Avg Volume', d.avg_volume)}}</div>
      </div>
      ${{d.description ? `<div style="margin-top:8px;font-size:11px;color:var(--mid);line-height:1.5">${{d.description}}...</div>` : ''}}
    `;
  }} catch(e) {{
    box.innerHTML = '<span style="color:var(--red);font-size:12px">โหลด fundamentals ไม่ได้</span>';
  }}
}}

async function loadEarnings(sym, btn) {{
  const box = document.getElementById('earn-' + sym);
  if (box.style.display !== 'none') {{ box.style.display = 'none'; return; }}
  box.style.display = 'block';
  box.innerHTML = '<span style="color:var(--muted);font-size:12px">⏳ กำลังโหลด earnings...</span>';
  try {{
    const r = await fetch('/api/earnings/' + sym);
    const d = await r.json();
    if (!d.quarters || !d.quarters.length) {{
      box.innerHTML = '<span style="color:var(--muted);font-size:12px">ไม่พบข้อมูล EPS</span>';
      return;
    }}
    const rows = d.quarters.map(q => {{
      const beat = q.beat;
      const col  = beat ? 'var(--green)' : 'var(--red)';
      const icon = beat ? '✅' : '❌';
      const surp = q.surprise_pct != null ? `(${{q.surprise_pct > 0 ? '+' : ''}}${{q.surprise_pct}}%)` : '';
      return `<tr>
        <td style="color:var(--mid);font-size:11px">${{q.date}}</td>
        <td style="font-size:12px">${{q.eps_est != null ? '$'+q.eps_est : '—'}}</td>
        <td style="font-weight:700;color:${{col}};font-size:12px">$${{q.eps_act}} ${{icon}}</td>
        <td style="color:${{col}};font-size:11px">${{surp}}</td>
      </tr>`;
    }}).join('');
    box.innerHTML = `
      <table style="width:100%;border-collapse:collapse">
        <thead><tr style="font-size:10px;color:var(--muted)"><th style="text-align:left;padding:4px 6px">Quarter</th><th style="text-align:left;padding:4px 6px">Est EPS</th><th style="text-align:left;padding:4px 6px">Actual EPS</th><th style="text-align:left;padding:4px 6px">Surprise</th></tr></thead>
        <tbody>${{rows}}</tbody>
      </table>`;
  }} catch(e) {{
    box.innerHTML = '<span style="color:var(--red);font-size:12px">โหลด earnings ไม่ได้</span>';
  }}
}}

function filterGroup(group, btn) {{
  document.querySelectorAll('[data-wl-group]').forEach(el => {{
    el.style.display = (group === '__all__' || el.dataset.wlGroup === group) ? '' : 'none';
  }});
  document.querySelectorAll('.tf-btn[id^="gtab-"]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}}
"""

    return _base("watchlist", "Watchlist", html, user, ticker_html, js)


# ─── Trade Journal Page ──────────────────────────────────────────────────────

def journal_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    entries = list(reversed(user.get("trade_journal", [])))

    action_opts = "".join(
        f'<option value="{a}">{a}</option>'
        for a in ["BUY", "SELL", "WATCH", "NOTE", "EXIT", "DCA"]
    )

    table_rows = ""
    for e in entries:
        act = e.get("action", "NOTE")
        col_map = {"BUY": "var(--green)", "SELL": "var(--red)", "WATCH": "var(--gold)",
                   "EXIT": "var(--red)", "DCA": "var(--teal)", "NOTE": "var(--mid)"}
        col = col_map.get(act, "var(--mid)")
        table_rows += f"""<tr>
          <td style="color:var(--muted);font-size:11px">{e.get('date','')}</td>
          <td><span style="font-weight:700">{e.get('sym','—')}</span></td>
          <td><span style="color:{col};font-weight:700;font-size:11px">{act}</span></td>
          <td style="font-size:12px">{e.get('price','—')}</td>
          <td style="font-size:12px;color:var(--teal)">{e.get('reason','')}</td>
          <td style="font-size:12px;color:var(--mid)">{e.get('notes','')}</td>
          <td>
            <form method="POST" action="/journal/delete" style="margin:0">
              <input type="hidden" name="jid" value="{e.get('id',0)}">
              <button class="btn btn-danger btn-sm" type="submit">✕</button>
            </form>
          </td>
        </tr>"""

    html = f"""
<!-- Add Entry Form -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">📓 บันทึก Trade ใหม่</div>
  <form method="POST" action="/journal/add">
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:12px">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbol</div>
        <input name="sym" placeholder="เช่น NVDA" style="width:100%;text-transform:uppercase" maxlength="10">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Action</div>
        <select name="action" style="width:100%">{action_opts}</select>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Price</div>
        <input name="price" placeholder="ราคา (opt)" style="width:100%">
      </div>
      <div style="grid-column:span 2">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">เหตุผล / Thesis</div>
        <input name="reason" placeholder="ทำไมถึงเปิด/ปิด position นี้..." style="width:100%">
      </div>
      <div style="grid-column:span 2">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">โน้ตเพิ่มเติม</div>
        <input name="notes" placeholder="บันทึกเพิ่มเติม..." style="width:100%">
      </div>
    </div>
    <button class="btn btn-primary" type="submit">💾 บันทึก</button>
  </form>
</div>

<!-- Journal Table -->
<div class="card">
  <div class="card-hdr">📋 Journal ({len(entries)} entries)</div>
  {f'''<div style="overflow-x:auto">
  <table class="tbl">
    <thead><tr>
      <th>Date</th><th>Symbol</th><th>Action</th><th>Price</th><th>เหตุผล</th><th>โน้ต</th><th></th>
    </tr></thead>
    <tbody>{table_rows}</tbody>
  </table>
  </div>''' if entries else '<div style="text-align:center;color:var(--muted);padding:24px">ยังไม่มีบันทึก — เพิ่ม entry ด้านบน</div>'}
</div>
"""

    return _base("journal", "Trade Journal", html, user, ticker_html, "")


# ─── Rebalancing Advisor (as a helper for tools page) ────────────────────────

def _rebalancing_html(port_rows: list, total_val: float, user: dict) -> str:
    """Show current vs target allocation, suggest buy/sell."""
    if not port_rows or total_val <= 0:
        return ""
    target_alloc = user.get("target_allocation", {})
    rows = ""
    for r in sorted(port_rows, key=lambda x: -x["val"]):
        sym = r["sym"]
        cur_pct = r["val"] / total_val * 100
        tgt_pct = float(target_alloc.get(sym, 0))
        diff_pct = tgt_pct - cur_pct
        diff_val = diff_pct / 100 * total_val
        if tgt_pct == 0:
            action_html = '<span style="color:var(--muted);font-size:11px">ไม่ได้ตั้ง target</span>'
        elif abs(diff_pct) < 1:
            action_html = '<span style="color:var(--teal);font-size:11px">✅ On target</span>'
        elif diff_val > 0:
            shares_to_buy = diff_val / r["price"] if r["price"] else 0
            action_html = f'<span style="color:var(--green);font-weight:700;font-size:11px">BUY ~{shares_to_buy:.2f} sh (${diff_val:,.0f})</span>'
        else:
            shares_to_sell = abs(diff_val) / r["price"] if r["price"] else 0
            action_html = f'<span style="color:var(--red);font-weight:700;font-size:11px">SELL ~{shares_to_sell:.2f} sh (${abs(diff_val):,.0f})</span>'

        rows += f"""<tr>
          <td><span style="font-weight:700">{sym}</span></td>
          <td>${r['val']:,.0f}</td>
          <td style="color:var(--teal)">{cur_pct:.1f}%</td>
          <td>
            <form method="POST" action="/tools/set-target" style="display:inline-flex;gap:4px">
              <input type="hidden" name="sym" value="{sym}">
              <input type="number" name="pct" value="{tgt_pct:.0f}" min="0" max="100" step="1" style="width:56px;font-size:11px;padding:2px 5px">
              <button class="btn btn-ghost btn-sm" type="submit">%</button>
            </form>
          </td>
          <td>{action_html}</td>
        </tr>"""

    total_target = sum(float(v) for v in target_alloc.values())
    target_sum_warning = f'<div style="color:var(--red);font-size:12px;margin-bottom:8px">⚠️ Target รวมกัน {total_target:.0f}% (ควรเป็น 100%)</div>' if target_alloc and abs(total_target - 100) > 2 else ""

    return f"""<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">⚖️ Rebalancing Advisor</div>
  <div style="font-size:12px;color:var(--muted);margin-bottom:8px">ตั้ง Target % ต่อหุ้น แล้วระบบจะคำนวณว่าต้องซื้อ/ขายเท่าไหร่</div>
  {target_sum_warning}
  <div style="overflow-x:auto">
  <table class="tbl">
    <thead><tr><th>Symbol</th><th>Value</th><th>Current %</th><th>Target %</th><th>แนะนำ</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>"""


def correlation_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    port = user.get("portfolio", {})
    watchlist = user.get("watchlist", [])
    # Build candidate symbols: portfolio + watchlist (max 20)
    syms = list(dict.fromkeys(list(port.keys()) + watchlist))[:20]
    # Filter to those with data
    syms = [s for s in syms if market_data.get(s, {}).get("price")]

    # Chips to toggle symbols
    chips_html = "".join(
        f'<span class="corr-chip active" data-sym="{s}" onclick="toggleSym(this)">{s}</span>'
        for s in syms
    )

    html = f"""
<div style="margin-bottom:16px">
  <div style="font-size:13px;color:var(--muted);margin-bottom:8px">
    เลือก symbol ที่ต้องการเปรียบเทียบ (ข้อมูล 1 ปีจาก yfinance · คลิก chip เพื่อ toggle)
  </div>
  <div id="symChips" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">
    {chips_html if chips_html else '<span style="color:var(--muted)">ยังไม่มีหุ้นใน Portfolio / Watchlist</span>'}
  </div>
  <button class="btn btn-primary" onclick="loadCorr()">🔗 คำนวณ Correlation</button>
</div>

<div id="corrStatus" style="color:var(--muted);font-size:12px;margin-bottom:8px"></div>

<!-- Matrix Table -->
<div class="card" id="corrCard" style="display:none;overflow-x:auto">
  <div class="card-hdr">📊 Correlation Matrix (Daily Return 1Y)</div>
  <div id="corrMatrix"></div>
</div>

<!-- Legend -->
<div id="corrLegend" style="display:none;margin-top:12px">
  <div style="font-size:11px;color:var(--muted);margin-bottom:6px">Legend</div>
  <div style="display:flex;gap:4px;align-items:center;font-size:11px">
    <span style="background:#c0392b;width:28px;height:14px;display:inline-block;border-radius:2px"></span>
    <span style="color:var(--mid)">0.8+ สูงมาก (เคลื่อนไหวเหมือนกัน)</span>
    <span style="background:#e67e22;width:28px;height:14px;display:inline-block;border-radius:2px;margin-left:10px"></span>
    <span style="color:var(--mid)">0.5-0.8 ปานกลาง</span>
    <span style="background:#27ae60;width:28px;height:14px;display:inline-block;border-radius:2px;margin-left:10px"></span>
    <span style="color:var(--mid)">0-0.5 ต่ำ (diversified)</span>
    <span style="background:#2980b9;width:28px;height:14px;display:inline-block;border-radius:2px;margin-left:10px"></span>
    <span style="color:var(--mid)">&lt;0 Negative (hedge)</span>
  </div>
</div>
"""

    js = """
function toggleSym(el){
  el.classList.toggle('active');
}
function loadCorr(){
  const chips = document.querySelectorAll('.corr-chip.active');
  const syms = Array.from(chips).map(c=>c.dataset.sym);
  if(syms.length < 2){
    document.getElementById('corrStatus').textContent='⚠️ เลือกอย่างน้อย 2 symbols';
    return;
  }
  document.getElementById('corrStatus').textContent='⏳ กำลังดึงข้อมูลและคำนวณ…';
  document.getElementById('corrCard').style.display='none';
  document.getElementById('corrLegend').style.display='none';
  fetch('/api/correlation?syms='+syms.join(','))
    .then(r=>r.json())
    .then(data=>{
      if(data.error){
        document.getElementById('corrStatus').textContent='❌ '+data.error;
        return;
      }
      renderMatrix(data.syms, data.matrix);
      document.getElementById('corrStatus').textContent='✅ อัปเดต '+data.updated;
      document.getElementById('corrCard').style.display='';
      document.getElementById('corrLegend').style.display='';
    })
    .catch(e=>{
      document.getElementById('corrStatus').textContent='❌ Error: '+e;
    });
}
function corrColor(v){
  if(v >= 0.8) return '#c0392b';
  if(v >= 0.6) return '#e67e22';
  if(v >= 0.4) return '#d4ac0d';
  if(v >= 0.2) return '#27ae60';
  if(v >= 0)   return '#1abc9c';
  return '#2980b9';
}
function renderMatrix(syms, matrix){
  let html = '<table style="border-collapse:collapse;font-size:12px">';
  html += '<tr><th style="padding:6px;color:var(--muted);background:var(--bg2)"></th>';
  for(const s of syms)
    html += `<th style="padding:6px 10px;color:var(--teal);background:var(--bg2)">${s}</th>`;
  html += '</tr>';
  for(let i=0;i<syms.length;i++){
    html += `<tr><td style="padding:6px 10px;font-weight:700;color:var(--teal);background:var(--bg2);white-space:nowrap">${syms[i]}</td>`;
    for(let j=0;j<syms.length;j++){
      const v = matrix[i][j];
      const bg = i===j ? 'var(--bg3)' : corrColor(v);
      const txt = i===j ? '—' : v.toFixed(2);
      const alpha = i===j ? 1 : Math.min(1, Math.abs(v)*1.2+0.2);
      const style = i===j
        ? `background:var(--bg3);color:var(--muted)`
        : `background:${bg};color:#fff;opacity:${alpha.toFixed(2)}`;
      html += `<td style="padding:6px 10px;text-align:center;${style}">${txt}</td>`;
    }
    html += '</tr>';
  }
  html += '</table>';
  document.getElementById('corrMatrix').innerHTML = html;
}
"""

    extra_css = """<style>
.corr-chip{
  display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:700;
  background:var(--bg3);color:var(--muted);cursor:pointer;border:1px solid var(--bg3);
  transition:all .2s;
}
.corr-chip.active{background:var(--teal);color:#131722;border-color:var(--teal);}
</style>"""

    return _base("correlation", "Correlation Matrix", extra_css + html, user, ticker_html, js)


# ─── Export Portfolio Report ─────────────────────────────────────────────────

def report_page(user: dict, market_data: dict, thb: float) -> str:
    """Printable portfolio report — full summary, positions, attribution."""
    from datetime import datetime as _dt
    port = user.get("portfolio", {})
    display = user.get("display_name", "User")
    today = _dt.now().strftime("%Y-%m-%d %H:%M")

    # Build position rows
    positions = []
    total_val = 0.0
    total_cost = 0.0
    for sym, info in port.items():
        qty = float(info.get("qty", 0) or 0)
        cost_per = float(info.get("cost", 0) or 0)
        d = market_data.get(sym, {})
        price = float(d.get("price") or 0)
        val = qty * price
        cost_tot = qty * cost_per
        pnl = val - cost_tot
        pnl_pct = (pnl / cost_tot * 100) if cost_tot else 0
        total_val += val
        total_cost += cost_tot
        positions.append({
            "sym": sym, "qty": qty, "cost_per": cost_per,
            "price": price, "val": val, "pnl": pnl, "pnl_pct": pnl_pct,
        })
    positions.sort(key=lambda x: -x["val"])
    total_pnl = total_val - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    pos_rows = ""
    for p in positions:
        color = "#27ae60" if p["pnl"] >= 0 else "#e74c3c"
        arrow = "▲" if p["pnl"] >= 0 else "▼"
        pos_rows += f"""<tr>
          <td><b>{p['sym']}</b></td>
          <td style="text-align:right">{p['qty']:,.2f}</td>
          <td style="text-align:right">${p['cost_per']:,.2f}</td>
          <td style="text-align:right">${p['price']:,.2f}</td>
          <td style="text-align:right">${p['val']:,.2f}</td>
          <td style="text-align:right;color:{color}">{arrow} ${abs(p['pnl']):,.2f}</td>
          <td style="text-align:right;color:{color}">{arrow} {p['pnl_pct']:+.2f}%</td>
          <td style="text-align:right">{(p['val']/total_val*100) if total_val else 0:.1f}%</td>
        </tr>"""

    # Watchlist section
    wl = user.get("watchlist", [])
    wl_rows = ""
    for sym in wl[:30]:
        d = market_data.get(sym, {})
        price = d.get("price", "—")
        chg   = d.get("chg") or d.get("change_pct") or 0
        color = "#27ae60" if float(chg or 0) >= 0 else "#e74c3c"
        wl_rows += f'<tr><td><b>{sym}</b></td><td style="text-align:right">${price}</td><td style="text-align:right;color:{color}">{float(chg or 0):+.2f}%</td></tr>'

    # Snapshot summary
    snaps = user.get("portfolio_snapshots", [])
    snap_note = ""
    if len(snaps) >= 2:
        first_val = snaps[0].get("value", 0)
        last_val = snaps[-1].get("value", 0)
        period_pnl = last_val - first_val
        period_pct = (period_pnl / first_val * 100) if first_val else 0
        snap_note = f"<p>📈 ช่วง {snaps[0].get('date','')} → {snaps[-1].get('date','')}: มูลค่าเปลี่ยนแปลง <b style='color:{'#27ae60' if period_pnl>=0 else '#e74c3c'}'>${period_pnl:+,.2f} ({period_pct:+.2f}%)</b></p>"

    pnl_color = "#27ae60" if total_pnl >= 0 else "#e74c3c"

    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<title>Portfolio Report — {display} — {today}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#fff;color:#1a1a2e;padding:32px;max-width:1000px;margin:0 auto}}
h1{{font-size:26px;font-weight:800;color:#1a1a2e;margin-bottom:4px}}
h2{{font-size:16px;font-weight:700;color:#2d3748;margin:24px 0 10px;border-bottom:2px solid #e2e8f0;padding-bottom:4px}}
.summary{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin:16px 0}}
.kpi{{background:#f8fafc;border-radius:8px;padding:14px;border-left:4px solid #2dd4bf}}
.kpi-lbl{{font-size:11px;color:#718096;text-transform:uppercase;letter-spacing:.5px}}
.kpi-val{{font-size:22px;font-weight:800;margin-top:2px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}}
th{{background:#f1f5f9;padding:8px 10px;text-align:left;font-weight:600;color:#475569;font-size:11px;text-transform:uppercase}}
td{{padding:7px 10px;border-bottom:1px solid #f1f5f9}}
tr:last-child td{{border-bottom:none}}
.footer{{margin-top:32px;font-size:11px;color:#718096;text-align:center}}
@media print{{.no-print{{display:none}}}}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:16px;display:flex;gap:10px">
  <button onclick="window.print()" style="padding:8px 18px;background:#2dd4bf;border:none;border-radius:6px;font-weight:700;cursor:pointer">🖨️ Print / Save PDF</button>
  <button onclick="window.close()" style="padding:8px 18px;background:#e2e8f0;border:none;border-radius:6px;cursor:pointer">✕ Close</button>
</div>

<h1>📄 Portfolio Report</h1>
<p style="color:#718096;margin-bottom:4px">ArtheeNoi Dashboard · {display} · สร้าง {today}</p>
{snap_note}

<h2>สรุปภาพรวม</h2>
<div class="summary">
  <div class="kpi"><div class="kpi-lbl">มูลค่ารวม (USD)</div><div class="kpi-val">${total_val:,.2f}</div></div>
  <div class="kpi"><div class="kpi-lbl">มูลค่ารวม (THB)</div><div class="kpi-val">฿{total_val*thb:,.0f}</div></div>
  <div class="kpi"><div class="kpi-lbl">ต้นทุนรวม</div><div class="kpi-val">${total_cost:,.2f}</div></div>
  <div class="kpi"><div class="kpi-lbl">P&L รวม</div><div class="kpi-val" style="color:{pnl_color}">${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)</div></div>
  <div class="kpi"><div class="kpi-lbl">จำนวนหุ้น</div><div class="kpi-val">{len(positions)}</div></div>
  <div class="kpi"><div class="kpi-lbl">อัตราแลกเปลี่ยน</div><div class="kpi-val">฿{thb:.2f}/USD</div></div>
</div>

<h2>รายการ Portfolio</h2>
{f'''<table>
  <thead><tr>
    <th>Symbol</th><th>Qty</th><th>ต้นทุน/หุ้น</th><th>ราคาปัจจุบัน</th>
    <th>มูลค่า</th><th>P&L $</th><th>P&L %</th><th>Weight</th>
  </tr></thead>
  <tbody>{pos_rows}</tbody>
</table>''' if positions else '<p style="color:#718096">ไม่มีหุ้นใน portfolio</p>'}

{f'''<h2>Watchlist ({len(wl)} symbols)</h2>
<table style="max-width:360px">
  <thead><tr><th>Symbol</th><th>ราคา</th><th>เปลี่ยนแปลง</th></tr></thead>
  <tbody>{wl_rows}</tbody>
</table>''' if wl else ''}

<div class="footer">สร้างโดย ArtheeNoi Dashboard · {today} · ข้อมูลอาจมีความล่าช้า ไม่ใช่คำแนะนำการลงทุน</div>
</body></html>"""

    # Return full HTML (not wrapped in _base — this is a standalone printable page)
    return html


def risk_page(user: dict, market_data: dict, thb: float) -> str:
    ticker_html = _ticker_html(market_data)
    port = user.get("portfolio", {})
    syms_list = ", ".join(port.keys()) if port else "—"

    html = f"""
<div style="margin-bottom:16px">
  <div style="font-size:13px;color:var(--muted);margin-bottom:10px">
    คำนวณ Risk Metrics จาก 1 ปีย้อนหลัง (252 วันทำการ) · เทียบ Beta กับ SPY
    <br>Portfolio: <span style="color:var(--teal)">{syms_list}</span>
  </div>
  <button class="btn btn-primary" onclick="loadRisk()">⚠️ คำนวณ Risk Metrics</button>
</div>

<div id="riskStatus" style="color:var(--muted);font-size:12px;margin-bottom:10px"></div>

<div id="riskCards" style="display:none">
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px" id="kpiGrid"></div>
  <div class="card">
    <div class="card-hdr">📖 ความหมายตัวชี้วัด</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;padding:8px 0">
      <div><span style="color:var(--teal);font-weight:700">Sharpe Ratio</span> — ผลตอบแทนต่อความเสี่ยง (>1 = ดี, >2 = ดีมาก)</div>
      <div><span style="color:var(--teal);font-weight:700">Sortino Ratio</span> — เหมือน Sharpe แต่นับแค่ downside risk</div>
      <div><span style="color:var(--teal);font-weight:700">Beta</span> — ความผันผวนเทียบ SPY (&lt;1 = เสี่ยงน้อยกว่าตลาด, >1 = มากกว่า)</div>
      <div><span style="color:var(--teal);font-weight:700">Max Drawdown</span> — ขาดทุนสูงสุดจากจุดสูงสุด (น้อยยิ่งดี)</div>
      <div><span style="color:var(--teal);font-weight:700">Ann. Return</span> — ผลตอบแทนรายปีจากช่วง 1 ปีที่ผ่านมา</div>
      <div><span style="color:var(--teal);font-weight:700">Win Rate</span> — วันที่ portfolio เป็นบวก ÷ วันทั้งหมด</div>
    </div>
  </div>
</div>
"""

    js = """
function loadRisk(){
  document.getElementById('riskStatus').textContent='⏳ กำลังคำนวณ…';
  document.getElementById('riskCards').style.display='none';
  fetch('/api/risk-metrics').then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('riskStatus').textContent='❌ '+d.error;return;}
    const metrics=[
      {lbl:'Ann. Return',val:(d.ann_return>=0?'+':'')+d.ann_return+'%',color:d.ann_return>=0?'var(--green)':'var(--red)'},
      {lbl:'Ann. Volatility',val:d.ann_vol+'%',color:'var(--gold)'},
      {lbl:'Sharpe Ratio',val:d.sharpe,color:d.sharpe>=1?'var(--green)':d.sharpe>=0?'var(--gold)':'var(--red)'},
      {lbl:'Sortino Ratio',val:d.sortino,color:d.sortino>=1?'var(--green)':d.sortino>=0?'var(--gold)':'var(--red)'},
      {lbl:'Beta (vs SPY)',val:d.beta,color:d.beta<=1.2?'var(--green)':'var(--red)'},
      {lbl:'Max Drawdown',val:d.max_drawdown+'%',color:'var(--red)'},
      {lbl:'Win Rate',val:d.win_rate+'%',color:d.win_rate>=50?'var(--green)':'var(--red)'},
    ];
    let html='';
    for(const m of metrics){
      html+=`<div class="card" style="text-align:center;padding:14px">
        <div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:4px">${m.lbl}</div>
        <div style="font-size:26px;font-weight:800;color:${m.color}">${m.val}</div>
      </div>`;
    }
    document.getElementById('kpiGrid').innerHTML=html;
    document.getElementById('riskStatus').textContent='✅ อัปเดต '+d.updated;
    document.getElementById('riskCards').style.display='';
  }).catch(e=>{document.getElementById('riskStatus').textContent='❌ '+e;});
}
"""
    return _base("risk", "Portfolio Risk Metrics", html, user, ticker_html, js)


def benchmark_page(user: dict, market_data: dict, thb: float) -> str:
    ticker_html = _ticker_html(market_data)
    snaps = user.get("portfolio_snapshots", [])
    snap_note = ""
    if len(snaps) < 2:
        snap_note = '<div class="card" style="color:var(--muted);padding:20px;text-align:center">ยังไม่มี portfolio history — ระบบจะบันทึกทุกวันหลัง market refresh ครั้งแรก</div>'

    html = f"""
<div style="display:flex;gap:10px;margin-bottom:12px;align-items:center;flex-wrap:wrap">
  <div style="font-size:13px;color:var(--muted)">เทียบผลตอบแทน Portfolio กับ SPY/QQQ (normalize เป็น % จากจุดเริ่ม)</div>
  <button class="btn btn-primary btn-sm" onclick="loadBench()">📏 โหลด Benchmark</button>
</div>
<div id="benchStatus" style="color:var(--muted);font-size:12px;margin-bottom:8px"></div>
{snap_note}
<div class="card" id="benchCard" style="{'display:none' if len(snaps)<2 else ''}">
  <div class="card-hdr">📏 Portfolio vs SPY vs QQQ</div>
  <div style="position:relative;height:320px">
    <canvas id="benchChart"></canvas>
  </div>
  <div id="benchLegend" style="display:flex;gap:16px;margin-top:10px;flex-wrap:wrap;font-size:12px"></div>
</div>
"""

    js = """
let benchChartInst = null;
function loadBench(){
  document.getElementById('benchStatus').textContent='⏳ กำลังโหลด…';
  fetch('/api/benchmark').then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('benchStatus').textContent='❌ '+d.error;return;}
    document.getElementById('benchCard').style.display='';
    renderBench(d);
    document.getElementById('benchStatus').textContent='✅ อัปเดต '+d.updated;
  }).catch(e=>{document.getElementById('benchStatus').textContent='❌ '+e;});
}
function renderBench(d){
  const colors={'Portfolio':'#2dd4bf','SPY':'#f59e0b','QQQ':'#a78bfa'};
  const datasets=[];
  // Portfolio
  datasets.push({
    label:'Portfolio',
    data: d.portfolio.map(p=>({x:p.date,y:p.pct})),
    borderColor:'#2dd4bf',borderWidth:2,pointRadius:0,tension:.3,fill:false
  });
  for(const [sym,series] of Object.entries(d.benchmarks)){
    datasets.push({
      label:sym,
      data:series.map(p=>({x:p.date,y:p.pct})),
      borderColor:colors[sym]||'#999',borderWidth:1.5,pointRadius:0,tension:.3,
      borderDash:sym==='SPY'?[4,3]:[2,2],fill:false
    });
  }
  if(benchChartInst){benchChartInst.destroy();}
  const ctx=document.getElementById('benchChart').getContext('2d');
  benchChartInst=new Chart(ctx,{
    type:'line',
    data:{datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      scales:{
        x:{type:'time',time:{unit:'month'},ticks:{color:'#787b86'},grid:{color:'#2a2e39'}},
        y:{ticks:{color:'#787b86',callback:v=>v+'%'},grid:{color:'#2a2e39'},
           title:{display:true,text:'% Return from Start',color:'#787b86'}}
      },
      plugins:{legend:{labels:{color:'#d1d4dc',boxWidth:12}},
               tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': '+(ctx.parsed.y>=0?'+':'')+ctx.parsed.y.toFixed(2)+'%'}}}
    }
  });
  // Legend with latest %
  let leg='';
  for(const ds of datasets){
    const last=ds.data[ds.data.length-1];
    const pct=last?last.y:0;
    const col=pct>=0?'var(--green)':'var(--red)';
    leg+=`<div style="display:flex;align-items:center;gap:5px">
      <span style="width:12px;height:3px;background:${ds.borderColor};display:inline-block;border-radius:2px"></span>
      <span>${ds.label}</span>
      <span style="color:${col};font-weight:700">${pct>=0?'+':''}${pct.toFixed(2)}%</span>
    </div>`;
  }
  document.getElementById('benchLegend').innerHTML=leg;
}
document.addEventListener('DOMContentLoaded',loadBench);
"""
    return _base("benchmark", "Benchmark Comparison", html, user, ticker_html, js)


def realized_page(user: dict, market_data: dict, thb: float) -> str:
    ticker_html = _ticker_html(market_data)
    trades = list(reversed(user.get("realized_trades", [])))
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    win_trades = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = (len(win_trades) / len(trades) * 100) if trades else 0

    rows_html = ""
    for t in trades:
        pnl = t.get("pnl", 0)
        color = "var(--green)" if pnl >= 0 else "var(--red)"
        arrow = "▲" if pnl >= 0 else "▼"
        pnl_pct = ((t.get("sell_price",0) - t.get("cost_per",0)) / t.get("cost_per",1) * 100) if t.get("cost_per") else 0
        rows_html += f"""<tr>
          <td style="color:var(--muted);font-size:11px">{t.get('date','')}</td>
          <td><b>{t.get('sym','—')}</b></td>
          <td style="text-align:right">{t.get('qty',0):,.2f}</td>
          <td style="text-align:right">${t.get('cost_per',0):,.2f}</td>
          <td style="text-align:right">${t.get('sell_price',0):,.2f}</td>
          <td style="text-align:right;color:{color};font-weight:700">{arrow} ${abs(pnl):,.2f}</td>
          <td style="text-align:right;color:{color}">{pnl_pct:+.2f}%</td>
          <td style="color:var(--muted);font-size:11px">{t.get('notes','')}</td>
          <td><form method="POST" action="/realized/delete" style="margin:0">
            <input type="hidden" name="rid" value="{t.get('id',0)}">
            <button class="btn btn-danger btn-sm" type="submit">✕</button>
          </form></td>
        </tr>"""

    pnl_color = "var(--green)" if total_pnl >= 0 else "var(--red)"

    html = f"""
<!-- Summary KPIs -->
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:16px">
  <div class="card" style="text-align:center;padding:14px">
    <div style="font-size:11px;color:var(--muted);text-transform:uppercase">Realized P&L รวม</div>
    <div style="font-size:24px;font-weight:800;color:{pnl_color}">${total_pnl:+,.2f}</div>
  </div>
  <div class="card" style="text-align:center;padding:14px">
    <div style="font-size:11px;color:var(--muted);text-transform:uppercase">฿ (THB)</div>
    <div style="font-size:24px;font-weight:800;color:{pnl_color}">฿{total_pnl*thb:+,.0f}</div>
  </div>
  <div class="card" style="text-align:center;padding:14px">
    <div style="font-size:11px;color:var(--muted);text-transform:uppercase">จำนวน Trade</div>
    <div style="font-size:24px;font-weight:800">{len(trades)}</div>
  </div>
  <div class="card" style="text-align:center;padding:14px">
    <div style="font-size:11px;color:var(--muted);text-transform:uppercase">Win Rate</div>
    <div style="font-size:24px;font-weight:800;color:{'var(--green)' if win_rate>=50 else 'var(--red)'}">{win_rate:.1f}%</div>
  </div>
</div>

<!-- Add Trade Form -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">💵 บันทึก Trade ที่ปิดแล้ว</div>
  <form method="POST" action="/realized/add">
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-bottom:12px">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbol</div>
        <input name="sym" placeholder="NVDA" style="width:100%;text-transform:uppercase" maxlength="10" required>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">วันที่ขาย</div>
        <input name="date" type="date" style="width:100%" value="{datetime.now().strftime('%Y-%m-%d')}">
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">จำนวน Qty</div>
        <input name="qty" placeholder="จำนวนหุ้น" style="width:100%" type="number" step="0.01" required>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ต้นทุน/หุ้น ($)</div>
        <input name="cost_per" placeholder="ราคาที่ซื้อ" style="width:100%" type="number" step="0.01" required>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ราคาขาย/หุ้น ($)</div>
        <input name="sell_price" placeholder="ราคาที่ขาย" style="width:100%" type="number" step="0.01" required>
      </div>
      <div style="grid-column:span 2">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">โน้ต</div>
        <input name="notes" placeholder="เหตุผลที่ขาย..." style="width:100%">
      </div>
    </div>
    <button class="btn btn-primary" type="submit">💾 บันทึก</button>
  </form>
</div>

<!-- Trades Table -->
<div class="card">
  <div class="card-hdr">📋 ประวัติ Realized Trade ({len(trades)} รายการ)</div>
  {f'''<div style="overflow-x:auto">
  <table class="tbl">
    <thead><tr>
      <th>วันที่</th><th>Symbol</th><th>Qty</th><th>ต้นทุน/หุ้น</th>
      <th>ราคาขาย</th><th>P&L $</th><th>P&L %</th><th>โน้ต</th><th></th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>''' if trades else '<div style="text-align:center;color:var(--muted);padding:24px">ยังไม่มีรายการ — เพิ่ม trade ที่ขายแล้วด้านบน</div>'}
</div>
"""
    return _base("realized", "Realized P&L", html, user, ticker_html, "")


def compare_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    port_syms = list(user.get("portfolio", {}).keys())
    wl_syms   = user.get("watchlist", [])
    suggest   = list(dict.fromkeys(port_syms + wl_syms))[:5]
    default   = ",".join(suggest[:3]) if suggest else "NVDA,MSFT,GOOGL"

    html = f"""
<div class="card" style="margin-bottom:14px">
  <div class="card-hdr">⚖️ เปรียบเทียบหุ้น (max 5 symbols)</div>
  <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;padding-top:4px">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbols (คั่นด้วย ,)</div>
      <input id="cmpSyms" value="{default}" placeholder="NVDA,MSFT,GOOGL"
             style="width:240px;text-transform:uppercase">
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ช่วงเวลา</div>
      <select id="cmpPeriod" style="width:100px">
        <option value="3mo">3 เดือน</option>
        <option value="6mo">6 เดือน</option>
        <option value="1y" selected>1 ปี</option>
        <option value="2y">2 ปี</option>
        <option value="5y">5 ปี</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="loadCompare()">⚖️ เปรียบเทียบ</button>
  </div>
</div>

<div id="cmpStatus" style="color:var(--muted);font-size:12px;margin-bottom:8px"></div>

<div class="card" id="cmpCard" style="display:none">
  <div class="card-hdr">📈 Normalized Return (เริ่มต้น = 100)</div>
  <div style="position:relative;height:340px">
    <canvas id="cmpChart"></canvas>
  </div>
  <div id="cmpSummary" style="margin-top:12px;overflow-x:auto"></div>
</div>
"""

    js = """
const CMP_COLORS=['#2dd4bf','#f59e0b','#a78bfa','#f87171','#34d399'];
let cmpChartInst=null;
function loadCompare(){
  const syms=document.getElementById('cmpSyms').value.toUpperCase().split(',').map(s=>s.trim()).filter(Boolean);
  const period=document.getElementById('cmpPeriod').value;
  if(syms.length<2){document.getElementById('cmpStatus').textContent='⚠️ ใส่อย่างน้อย 2 symbols';return;}
  document.getElementById('cmpStatus').textContent='⏳ กำลังโหลด…';
  document.getElementById('cmpCard').style.display='none';
  fetch('/api/compare?syms='+syms.join(',')+'&period='+period)
    .then(r=>r.json())
    .then(d=>{
      if(d.error){document.getElementById('cmpStatus').textContent='❌ '+d.error;return;}
      renderCompare(d);
      document.getElementById('cmpStatus').textContent='✅ '+d.updated;
      document.getElementById('cmpCard').style.display='';
    }).catch(e=>{document.getElementById('cmpStatus').textContent='❌ '+e;});
}
function renderCompare(d){
  const datasets=Object.entries(d.series).map(([sym,series],i)=>({
    label:sym,
    data:series.map(p=>({x:p.date,y:p.val})),
    borderColor:CMP_COLORS[i%CMP_COLORS.length],
    borderWidth:2,pointRadius:0,tension:.3,fill:false,
  }));
  if(cmpChartInst)cmpChartInst.destroy();
  cmpChartInst=new Chart(document.getElementById('cmpChart').getContext('2d'),{
    type:'line',data:{datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      scales:{
        x:{type:'time',time:{unit:'month'},ticks:{color:'#787b86'},grid:{color:'#2a2e39'}},
        y:{ticks:{color:'#787b86',callback:v=>(v-100).toFixed(1)+'%'},grid:{color:'#2a2e39'},
           title:{display:true,text:'% Return (base 100)',color:'#787b86'}}
      },
      plugins:{legend:{labels:{color:'#d1d4dc',boxWidth:12}}}
    }
  });
  // Summary table
  let tbl='<table class="tbl"><thead><tr><th>Symbol</th><th style="text-align:right">ราคาเริ่ม</th><th style="text-align:right">ราคาปัจจุบัน</th><th style="text-align:right">ผลตอบแทน</th></tr></thead><tbody>';
  for(const [sym,series] of Object.entries(d.series)){
    const first=series[0]?.val||100;
    const last=series[series.length-1]?.val||100;
    const pct=last-100;
    const col=pct>=0?'var(--green)':'var(--red)';
    tbl+=`<tr><td><b>${sym}</b></td><td style="text-align:right">100.00</td><td style="text-align:right">${last.toFixed(2)}</td><td style="text-align:right;color:${col};font-weight:700">${pct>=0?'+':''}${pct.toFixed(2)}%</td></tr>`;
  }
  tbl+='</tbody></table>';
  document.getElementById('cmpSummary').innerHTML=tbl;
}
document.addEventListener('DOMContentLoaded',loadCompare);
"""
    return _base("compare", "Stock Comparison", html, user, ticker_html, js)


def macro_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)

    html = """
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
  <div style="font-size:13px;color:var(--muted)">ตัวชี้วัด Macro เศรษฐกิจสหรัฐ — อัปเดต real-time จาก yfinance</div>
  <button class="btn btn-primary btn-sm" onclick="loadMacro()">🔄 Refresh</button>
</div>
<div id="macroStatus" style="color:var(--muted);font-size:12px;margin-bottom:12px"></div>

<!-- KPI Cards -->
<div id="macroGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-bottom:20px"></div>

<!-- Yield Curve Panel -->
<div class="card" id="yieldPanel" style="display:none;margin-bottom:16px">
  <div class="card-hdr">📉 Yield Curve Spread (10Y − 2Y)</div>
  <div id="yieldMsg" style="padding:12px;font-size:14px"></div>
</div>

<!-- Context Guide -->
<div class="card">
  <div class="card-hdr">📖 อ่านตัวชี้วัด Macro</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px;padding:8px 0">
    <div><span style="color:var(--teal);font-weight:700">VIX (Fear Index)</span><br>
      &lt;15 = ตลาดสงบ · 15-25 = ปกติ · &gt;30 = panic/โอกาสซื้อ</div>
    <div><span style="color:var(--teal);font-weight:700">10Y Yield</span><br>
      ขึ้น = ดอกเบี้ยแพง (กดหุ้นเทค) · ลง = เงินไหลเข้าหุ้น</div>
    <div><span style="color:var(--teal);font-weight:700">DXY (Dollar Index)</span><br>
      แข็ง = กดทอง/Emerging Market · อ่อน = เอื้อสินค้าโภคภัณฑ์</div>
    <div><span style="color:var(--teal);font-weight:700">Yield Spread (10Y-2Y)</span><br>
      &lt;0 = Inverted (ส่งสัญญาณ recession) · &gt;0 = ปกติ</div>
    <div><span style="color:var(--teal);font-weight:700">Oil (CL=F)</span><br>
      ขึ้น = เงินเฟ้อ/กดดัน Fed · ลง = บรรเทาแรงกดดัน</div>
    <div><span style="color:var(--teal);font-weight:700">BTC</span><br>
      Risk-on indicator: ขึ้นพร้อม Nasdaq = risk appetite สูง</div>
  </div>
</div>
"""

    js = """
const MACRO_CFG={
  VIX:  {label:'VIX (Fear Index)', unit:'', icon:'😨',
         badge:v=>v>30?['PANIC','var(--red)']:v>20?['ELEVATED','var(--gold)']:['CALM','var(--green)']},
  '10Y':{label:'US 10Y Yield',   unit:'%', icon:'📊',
         badge:v=>v>4.5?['HIGH','var(--red)']:v>3?['NORMAL','var(--gold)']:['LOW','var(--green)']},
  '2Y': {label:'US 2Y Yield',    unit:'%', icon:'📊',
         badge:v=>v>4.5?['HIGH','var(--red)']:['OK','var(--teal)']},
  DXY:  {label:'US Dollar (DXY)',unit:'',  icon:'💵',
         badge:v=>v>105?['STRONG','var(--red)']:v>100?['FIRM','var(--gold)']:['WEAK','var(--green)']},
  OIL:  {label:'Crude Oil (WTI)',unit:'$', icon:'🛢️',
         badge:v=>v>90?['HIGH','var(--red)']:v>70?['NORMAL','var(--gold)']:['LOW','var(--green)']},
  GOLD: {label:'Gold (XAU/USD)', unit:'$', icon:'🥇',
         badge:v=>['','var(--gold)']},
  SPY:  {label:'S&P 500 ETF',   unit:'$', icon:'📈',
         badge:v=>['','var(--teal)']},
  BTC:  {label:'Bitcoin',        unit:'$', icon:'₿',
         badge:v=>['','#f7931a']},
};
function loadMacro(){
  document.getElementById('macroStatus').textContent='⏳ กำลังดึงข้อมูล…';
  document.getElementById('macroGrid').innerHTML='';
  fetch('/api/macro').then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('macroStatus').textContent='❌ '+d.error;return;}
    let grid='';
    for(const [key,cfg] of Object.entries(MACRO_CFG)){
      const item=d.data[key]||{price:0,chg:0};
      const [badgeTxt,badgeCol]=cfg.badge(item.price);
      const chgCol=item.chg>=0?'var(--green)':'var(--red)';
      const arrow=item.chg>=0?'▲':'▼';
      grid+=`<div class="card" style="padding:14px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:13px;color:var(--muted)">${cfg.icon} ${cfg.label}</span>
          ${badgeTxt?`<span style="font-size:10px;font-weight:700;color:${badgeCol};border:1px solid ${badgeCol};border-radius:10px;padding:1px 7px">${badgeTxt}</span>`:''}
        </div>
        <div style="font-size:26px;font-weight:800">${cfg.unit}${item.price.toLocaleString('en-US',{maximumFractionDigits:2})}</div>
        <div style="font-size:12px;color:${chgCol};margin-top:2px">${arrow} ${Math.abs(item.chg).toFixed(2)}%</div>
      </div>`;
    }
    document.getElementById('macroGrid').innerHTML=grid;
    // Yield curve
    const spread=d.yield_spread;
    if(spread!==null){
      const col=spread<0?'var(--red)':spread<0.5?'var(--gold)':'var(--green)';
      const msg=spread<0
        ?`⚠️ Inverted Yield Curve: Spread = <b style="color:var(--red)">${spread.toFixed(3)}%</b> — สัญญาณเตือน Recession`
        :`✅ Normal Yield Curve: Spread = <b style="color:var(--green)">${spread.toFixed(3)}%</b>`;
      document.getElementById('yieldMsg').innerHTML=msg;
      document.getElementById('yieldPanel').style.display='';
    }
    document.getElementById('macroStatus').textContent='✅ อัปเดต '+d.updated;
  }).catch(e=>{document.getElementById('macroStatus').textContent='❌ '+e;});
}
document.addEventListener('DOMContentLoaded',loadMacro);
"""
    return _base("macro", "Macro Overview", html, user, ticker_html, js)


def earnings_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    port  = user.get("portfolio", {})
    wl    = user.get("watchlist", [])
    syms  = list(dict.fromkeys(list(port.keys()) + wl))

    chips = "".join(
        f'<span class="corr-chip active" data-sym="{s}" onclick="this.classList.toggle(\'active\')">{s}</span>'
        for s in syms
    )

    html = f"""
<div class="card" style="margin-bottom:14px">
  <div class="card-hdr">📆 Earnings Countdown — Portfolio + Watchlist</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0" id="earnChips">{chips if chips else '<span style="color:var(--muted)">ไม่มีหุ้นใน Portfolio/Watchlist</span>'}</div>
  <div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap">
    <button class="btn btn-primary" onclick="loadEarnings()">📆 โหลด Earnings Calendar</button>
    <span style="color:var(--muted);font-size:12px;align-self:center">ดึงข้อมูลจาก yfinance · อาจใช้เวลา 10-30 วินาที</span>
  </div>
</div>

<div id="earnStatus" style="color:var(--muted);font-size:12px;margin-bottom:10px"></div>
<div id="earnGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px"></div>
"""

    js = """
function loadEarnings(){
  const syms=Array.from(document.querySelectorAll('#earnChips .corr-chip.active')).map(c=>c.dataset.sym);
  if(!syms.length){document.getElementById('earnStatus').textContent='⚠️ เลือก symbol ก่อน';return;}
  document.getElementById('earnStatus').textContent='⏳ กำลังดึง Earnings date…';
  document.getElementById('earnGrid').innerHTML='';
  fetch('/api/earnings-calendar?syms='+syms.join(','))
    .then(r=>r.json()).then(d=>{
      if(d.error){document.getElementById('earnStatus').textContent='❌ '+d.error;return;}
      let html='';
      for(const item of d.earnings){
        const days=item.days_left;
        const col=days<0?'var(--muted)':days<=7?'var(--red)':days<=30?'var(--gold)':'var(--green)';
        const badge=days<0?'ผ่านแล้ว':days===0?'วันนี้!':days<=7?`${days}d ⚠️`:`${days}d`;
        html+=`<div class="card" style="padding:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <span style="font-weight:800;font-size:16px">${item.sym}</span>
            <span style="font-size:12px;font-weight:700;color:${col};border:1px solid ${col};border-radius:10px;padding:2px 8px">${badge}</span>
          </div>
          <div style="font-size:12px;color:var(--muted)">Earnings Date</div>
          <div style="font-size:14px;font-weight:700;margin-bottom:6px">${item.date||'ไม่ทราบ'}</div>
          ${item.eps_est?`<div style="font-size:11px;color:var(--muted)">EPS Estimate: <b style="color:var(--teal)">$${item.eps_est}</b></div>`:''}
          ${item.rev_est?`<div style="font-size:11px;color:var(--muted)">Revenue Est: <b style="color:var(--teal)">${item.rev_est}</b></div>`:''}
          ${item.last_eps!=null?`<div style="font-size:11px;color:var(--muted)">Last EPS: <b style="color:var(--gold)">$${item.last_eps}</b></div>`:''}
        </div>`;
      }
      document.getElementById('earnGrid').innerHTML=html||'<div style="color:var(--muted)">ไม่มีข้อมูล</div>';
      document.getElementById('earnStatus').textContent='✅ อัปเดต '+d.updated;
    }).catch(e=>{document.getElementById('earnStatus').textContent='❌ '+e;});
}
"""
    extra_css = """<style>
.corr-chip{display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:700;
  background:var(--bg3);color:var(--muted);cursor:pointer;border:1px solid var(--bg3);transition:all .2s;}
.corr-chip.active{background:var(--teal);color:#131722;border-color:var(--teal);}
</style>"""
    return _base("earnings", "Earnings Countdown", extra_css + html, user, ticker_html, js)


def sentiment_page(user: dict, market_data: dict, marketaux_key: str = "") -> str:
    ticker_html = _ticker_html(market_data)
    port = user.get("portfolio", {})
    wl   = user.get("watchlist", [])
    syms = list(dict.fromkeys(list(port.keys()) + wl))[:20]

    chips = "".join(
        f'<span class="corr-chip active" data-sym="{s}" onclick="this.classList.toggle(\'active\')">{s}</span>'
        for s in syms
    )

    html = f"""
<div class="card" style="margin-bottom:14px">
  <div class="card-hdr">🧠 News Sentiment — Bullish/Bearish Score ต่อหุ้น</div>
  <div style="font-size:12px;color:var(--muted);margin-bottom:8px">ดึงข่าวล่าสุดจาก MarketAux · วิเคราะห์ sentiment score ทุกบทความ · เฉลี่ยเป็น gauge ต่อ symbol</div>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px">{chips if chips else '<span style="color:var(--muted)">ไม่มีหุ้นใน Portfolio/Watchlist</span>'}</div>
  <button class="btn btn-primary" onclick="loadSentiment()">🧠 วิเคราะห์ Sentiment</button>
</div>

<div id="sentStatus" style="color:var(--muted);font-size:12px;margin-bottom:10px"></div>
<div id="sentGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px"></div>
"""

    js = """
function loadSentiment(){
  const syms=Array.from(document.querySelectorAll('.corr-chip.active')).map(c=>c.dataset.sym);
  if(!syms.length){document.getElementById('sentStatus').textContent='⚠️ เลือก symbol ก่อน';return;}
  document.getElementById('sentStatus').textContent='⏳ กำลังวิเคราะห์ sentiment… (อาจใช้เวลา ~30s)';
  document.getElementById('sentGrid').innerHTML='';
  Promise.all(syms.map(sym=>
    fetch('/api/sentiment/'+sym).then(r=>r.json()).catch(()=>({sym,error:'fail'}))
  )).then(results=>{
    let html='';
    for(const d of results){
      if(d.error&&!d.score&&d.score!==0){
        html+=`<div class="card" style="padding:14px"><b>${d.sym}</b><br><span style="color:var(--muted);font-size:12px">ไม่มีข้อมูล</span></div>`;
        continue;
      }
      const score=d.score||0; // -1 to 1
      const pct=Math.round((score+1)/2*100); // 0-100
      const col=score>0.2?'var(--green)':score<-0.2?'var(--red)':'var(--gold)';
      const label=score>0.4?'VERY BULLISH':score>0.1?'BULLISH':score<-0.4?'VERY BEARISH':score<-0.1?'BEARISH':'NEUTRAL';
      html+=`<div class="card" style="padding:14px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <span style="font-weight:800;font-size:16px">${d.sym}</span>
          <span style="font-size:11px;font-weight:700;color:${col};border:1px solid ${col};border-radius:10px;padding:2px 8px">${label}</span>
        </div>
        <div style="background:var(--bg3);border-radius:4px;height:8px;margin-bottom:6px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:${col};border-radius:4px;transition:width 1s"></div>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-bottom:8px">
          <span>Bearish</span><span style="color:${col};font-weight:700">${score>=0?'+':''}${score.toFixed(3)}</span><span>Bullish</span>
        </div>
        <div style="font-size:11px;color:var(--muted)">จาก ${d.count||0} บทความ · อัปเดต ${d.updated||''}</div>
        ${(d.headlines||[]).slice(0,2).map(h=>`<div style="font-size:11px;color:var(--mid);margin-top:4px;border-left:2px solid var(--bg3);padding-left:6px">${h}</div>`).join('')}
      </div>`;
    }
    document.getElementById('sentGrid').innerHTML=html||'<div style="color:var(--muted)">ไม่มีข้อมูล</div>';
    document.getElementById('sentStatus').textContent='✅ วิเคราะห์เสร็จ';
  });
}
"""
    extra_css = """<style>
.corr-chip{display:inline-block;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:700;
  background:var(--bg3);color:var(--muted);cursor:pointer;border:1px solid var(--bg3);transition:all .2s;}
.corr-chip.active{background:var(--teal);color:#131722;border-color:var(--teal);}
</style>"""
    return _base("sentiment", "News Sentiment", extra_css + html, user, ticker_html, js)


def targets_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    targets = user.get("price_targets", {})
    port_syms = list(user.get("portfolio", {}).keys())
    wl_syms   = user.get("watchlist", [])
    all_syms  = list(dict.fromkeys(port_syms + wl_syms))

    rows_html = ""
    for sym, tgt in targets.items():
        d = market_data.get(sym, {})
        price = float(d.get("price") or 0)
        target_p = float(tgt.get("target") or 0)
        stop_p   = float(tgt.get("stop") or 0)
        notes    = tgt.get("notes", "")

        upside = ((target_p - price) / price * 100) if price and target_p else 0
        downside = ((stop_p - price) / price * 100) if price and stop_p else 0
        # Progress bar: 0% = stop, 100% = target
        if target_p and stop_p and target_p != stop_p:
            prog = max(0, min(100, (price - stop_p) / (target_p - stop_p) * 100))
        else:
            prog = 50
        prog_col = "var(--green)" if prog > 65 else "var(--gold)" if prog > 35 else "var(--red)"

        rows_html += f"""
<div class="card" style="padding:14px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <div>
      <div style="font-size:18px;font-weight:800">{sym}</div>
      {f'<div style="font-size:11px;color:var(--muted)">{notes}</div>' if notes else ''}
    </div>
    <form method="POST" action="/targets/delete" style="margin:0">
      <input type="hidden" name="sym" value="{sym}">
      <button class="btn btn-danger btn-sm" type="submit">✕</button>
    </form>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;font-size:12px">
    <div style="text-align:center">
      <div style="color:var(--muted);font-size:10px;text-transform:uppercase">ราคาปัจจุบัน</div>
      <div style="font-weight:700;font-size:14px">${price:,.2f}</div>
    </div>
    <div style="text-align:center">
      <div style="color:var(--muted);font-size:10px;text-transform:uppercase">Target</div>
      <div style="font-weight:700;font-size:14px;color:var(--green)">${target_p:,.2f}</div>
      <div style="font-size:10px;color:var(--green)">{upside:+.1f}%</div>
    </div>
    <div style="text-align:center">
      <div style="color:var(--muted);font-size:10px;text-transform:uppercase">Stop Loss</div>
      <div style="font-weight:700;font-size:14px;color:var(--red)">${stop_p:,.2f}</div>
      <div style="font-size:10px;color:var(--red)">{downside:+.1f}%</div>
    </div>
  </div>
  <div style="background:var(--bg3);border-radius:4px;height:8px;overflow:hidden;position:relative">
    <div style="position:absolute;left:0;top:0;height:100%;width:{prog:.1f}%;background:{prog_col};border-radius:4px;transition:width 1s"></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:3px">
    <span>Stop ${stop_p:,.0f}</span>
    <span style="color:{prog_col};font-weight:700">{prog:.0f}% ถึง target</span>
    <span>Target ${target_p:,.0f}</span>
  </div>
</div>"""

    sym_opts = "".join(f'<option value="{s}">{s}</option>' for s in all_syms)

    html = f"""
<!-- Add Target Form -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">🎯 ตั้ง Price Target ใหม่</div>
  <form method="POST" action="/targets/set">
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:12px">
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbol</div>
        <input name="sym" list="symList" placeholder="หรือพิมพ์เอง" style="width:100%;text-transform:uppercase" maxlength="12">
        <datalist id="symList">{sym_opts}</datalist>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Target Price ($)</div>
        <input name="target" type="number" step="0.01" placeholder="เป้าขึ้น" style="width:100%" required>
      </div>
      <div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Stop Loss ($)</div>
        <input name="stop" type="number" step="0.01" placeholder="จุดตัดขาดทุน" style="width:100%">
      </div>
      <div style="grid-column:span 2">
        <div style="font-size:11px;color:var(--muted);margin-bottom:4px">โน้ต / Thesis</div>
        <input name="notes" placeholder="ทำไมถึงตั้ง target นี้..." style="width:100%">
      </div>
    </div>
    <button class="btn btn-primary" type="submit">💾 บันทึก Target</button>
  </form>
</div>

<!-- Targets Grid -->
{f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">{rows_html}</div>' if targets else '<div class="card" style="text-align:center;color:var(--muted);padding:32px">ยังไม่มี Price Target — เพิ่มด้านบน</div>'}
"""
    return _base("targets", "Price Targets", html, user, ticker_html, "")


def portfolios_page(user: dict, market_data: dict, thb: float) -> str:
    ticker_html = _ticker_html(market_data)
    raw_user    = user  # already has 'portfolio' injected
    ports       = user.get("portfolios", {})
    active_key  = user.get("active_portfolio", "default")

    # If old-style (no portfolios dict), show migration note
    if not ports:
        ports = {"default": {"label": "Default Portfolio", "holdings": user.get("portfolio", {})}}

    port_cards = ""
    for key, pdata in ports.items():
        label    = pdata.get("label", key)
        holdings = pdata.get("holdings", {})
        # Calculate value
        total = 0.0
        for sym, info in holdings.items():
            qty   = float(info.get("qty", 0) or info.get("shares", 0) or 0)
            price = float((market_data.get(sym) or {}).get("price") or 0)
            total += qty * price
        is_active = key == active_key
        border    = "border:2px solid var(--teal)" if is_active else "border:1px solid var(--border)"
        badge     = '<span style="font-size:10px;background:var(--teal);color:#131722;border-radius:8px;padding:1px 8px;font-weight:700">ACTIVE</span>' if is_active else ""

        port_cards += f"""
<div class="card" style="{border};padding:14px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
    <div>
      <div style="font-size:16px;font-weight:800">{label} {badge}</div>
      <div style="font-size:11px;color:var(--muted)">{len(holdings)} holdings · ${total:,.2f} USD</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      {f'''<form method="POST" action="/portfolios/switch" style="margin:0">
        <input type="hidden" name="key" value="{key}">
        <button class="btn btn-primary btn-sm" type="submit">Switch</button>
      </form>''' if not is_active else ''}
      {f'''<form method="POST" action="/portfolios/delete" style="margin:0" onsubmit="return confirm('ลบพอร์ต {label}?')">
        <input type="hidden" name="key" value="{key}">
        <button class="btn btn-danger btn-sm" type="submit">ลบ</button>
      </form>''' if key != active_key else ''}
    </div>
  </div>
  <!-- Holdings mini-list -->
  <div style="font-size:11px;color:var(--muted)">{' · '.join(list(holdings.keys())[:8]) or '(ว่าง)'}{' …' if len(holdings)>8 else ''}</div>
</div>"""

    html = f"""
<!-- Active Portfolio Banner -->
<div style="background:var(--bg2);border-left:4px solid var(--teal);padding:10px 14px;border-radius:4px;margin-bottom:16px;font-size:13px">
  💼 Portfolio ที่ใช้งานอยู่: <b style="color:var(--teal)">{ports.get(active_key,{}).get('label', active_key)}</b>
  — การดู Stocks/Charts/Signals ทุกหน้าจะใช้พอร์ตนี้
</div>

<!-- Create New Portfolio -->
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">➕ สร้าง Portfolio ใหม่</div>
  <form method="POST" action="/portfolios/create" style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ชื่อ (key, ไม่มีช่องว่าง)</div>
      <input name="key" placeholder="เช่น paper, us_tech" style="width:160px"
             pattern="[a-zA-Z0-9_]+" title="ตัวอักษร/ตัวเลข/_เท่านั้น" required>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ชื่อแสดง</div>
      <input name="label" placeholder="เช่น US Tech Portfolio" style="width:200px" required>
    </div>
    <button class="btn btn-primary" type="submit">➕ สร้าง</button>
  </form>
</div>

<!-- Portfolio List -->
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">
  {port_cards}
</div>

<!-- Import/Export CSV -->
<div class="card" style="margin-top:16px">
  <div class="card-hdr">📥 Import / 📤 Export Portfolio (CSV)</div>
  <div style="display:flex;gap:12px;flex-wrap:wrap;padding-top:4px">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">Import CSV (คอลัมน์: sym,qty,cost)</div>
      <form method="POST" action="/portfolio/import" enctype="multipart/form-data">
        <input type="file" name="csv_file" accept=".csv" style="margin-bottom:6px;width:100%">
        <button class="btn btn-primary btn-sm" type="submit">📥 Import</button>
      </form>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">Export พอร์ตปัจจุบันเป็น CSV</div>
      <a href="/portfolio/export" class="btn btn-primary btn-sm">📤 Download CSV</a>
    </div>
  </div>
  <div style="font-size:11px;color:var(--muted);margin-top:8px">
    รูปแบบ CSV: <code style="background:var(--bg3);padding:1px 5px;border-radius:3px">sym,qty,cost</code>
    เช่น <code style="background:var(--bg3);padding:1px 5px;border-radius:3px">NVDA,2,850</code>
  </div>
</div>
"""
    return _base("portfolios", "Portfolios", html, user, ticker_html, "")


def settings_page(user: dict, flash_msg: str = "") -> str:
    display    = user.get("display_name", "")
    uname      = user.get("_username", "")
    or_key     = user.get("openrouter_key", "")
    tg_notify  = user.get("telegram_notify", True)
    tg_checked = "checked" if tg_notify else ""
    flash_html = f'<div style="background:#1a3a2a;border-left:3px solid var(--green);padding:10px 14px;border-radius:4px;margin-bottom:14px;font-size:13px;color:var(--green)">{flash_msg}</div>' if flash_msg else ""

    html = f"""
{flash_html}
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">

<!-- Profile Settings -->
<div class="card">
  <div class="card-hdr">👤 Profile</div>
  <form method="POST" action="/settings/save">
    <input type="hidden" name="section" value="profile">
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Username (แก้ไขไม่ได้)</div>
      <input value="{uname}" disabled style="width:100%;opacity:.5">
    </div>
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Display Name</div>
      <input name="display_name" value="{display}" style="width:100%" required>
    </div>
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">เปลี่ยน Password (เว้นว่างถ้าไม่เปลี่ยน)</div>
      <input name="new_password" type="password" placeholder="รหัสผ่านใหม่" style="width:100%">
    </div>
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">ยืนยัน Password ใหม่</div>
      <input name="confirm_password" type="password" placeholder="พิมพ์อีกครั้ง" style="width:100%">
    </div>
    <button class="btn btn-primary" type="submit">💾 บันทึก Profile</button>
  </form>
</div>

<!-- API & Notifications -->
<div class="card">
  <div class="card-hdr">🔑 API Keys & Notifications</div>
  <form method="POST" action="/settings/save">
    <input type="hidden" name="section" value="api">
    <div style="margin-bottom:12px">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">OpenRouter API Key (สำหรับ AI features)</div>
      <input name="openrouter_key" value="{or_key}" placeholder="sk-or-..." style="width:100%;font-family:monospace;font-size:12px">
      <div style="font-size:10px;color:var(--muted);margin-top:3px">เว้นว่าง = ใช้ system key · มี key ส่วนตัว = เร็วกว่า</div>
    </div>
    <div style="margin-bottom:16px">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" name="telegram_notify" value="1" {tg_checked}
               style="width:16px;height:16px;accent-color:var(--teal)">
        <div>
          <div style="font-size:13px">Telegram Notification</div>
          <div style="font-size:11px;color:var(--muted)">ส่ง Telegram เมื่อ price alert trigger (ต้องตั้ง BOT_TOKEN ใน env)</div>
        </div>
      </label>
    </div>
    <button class="btn btn-primary" type="submit">💾 บันทึก API Settings</button>
  </form>
</div>

<!-- Danger Zone -->
<div class="card" style="border-color:var(--red);grid-column:span 2">
  <div class="card-hdr" style="color:var(--red)">⚠️ Danger Zone</div>
  <div style="display:flex;gap:12px;flex-wrap:wrap">
    <form method="POST" action="/portfolio/clear" onsubmit="return confirm('ลบหุ้นทั้งหมดใน Portfolio?')">
      <button class="btn btn-danger btn-sm" type="submit">🗑️ ล้าง Portfolio</button>
    </form>
    <form method="POST" action="/watchlist/clear" onsubmit="return confirm('ล้าง Watchlist?')">
      <button class="btn btn-danger btn-sm" type="submit">🗑️ ล้าง Watchlist</button>
    </form>
    <form method="POST" action="/journal/clear" onsubmit="return confirm('ลบ Trade Journal ทั้งหมด?')">
      <button class="btn btn-danger btn-sm" type="submit">🗑️ ล้าง Journal</button>
    </form>
  </div>
</div>

</div>
"""
    return _base("settings", "Settings", html, user, "", "")


def admin_page(users: dict, flash: str = "") -> str:
    flash_html = f'<div style="background:#1a3a2a;border-left:3px solid var(--green);padding:10px 14px;border-radius:4px;margin-bottom:14px;font-size:13px;color:var(--green)">{flash}</div>' if flash else ""
    rows = ""
    for uname, u in users.items():
        if uname.startswith("_") or not isinstance(u, dict):
            continue
        port_count = len(u.get("portfolio", {}))
        wl_count   = len(u.get("watchlist", []))
        role       = u.get("role", "user")
        display    = u.get("display_name", uname)
        last_upd   = u.get("last_updated", "—") or "—"
        badge_col  = "var(--gold)" if role == "admin" else "var(--teal)"
        rows += f"""<tr>
          <td><b>{display}</b><div style="font-size:11px;color:var(--muted)">{uname}</div></td>
          <td><span style="color:{badge_col};font-weight:700;font-size:11px">{role.upper()}</span></td>
          <td style="text-align:right">{port_count}</td>
          <td style="text-align:right">{wl_count}</td>
          <td style="font-size:11px;color:var(--muted)">{str(last_upd)[:16]}</td>
          <td>
            <div style="display:flex;gap:6px;flex-wrap:wrap">
              <form method="POST" action="/admin/reset-password" style="margin:0;display:flex;gap:4px">
                <input type="hidden" name="uname" value="{uname}">
                <input name="new_pwd" placeholder="รหัสใหม่" style="width:100px;font-size:11px;padding:4px 8px">
                <button class="btn btn-secondary btn-sm" type="submit">🔑 Reset</button>
              </form>
              {f'''<form method="POST" action="/admin/delete-user" style="margin:0" onsubmit="return confirm('ลบ user {uname}?')">
                <input type="hidden" name="uname" value="{uname}">
                <button class="btn btn-danger btn-sm" type="submit">🗑️</button>
              </form>''' if role != "admin" else ''}
            </div>
          </td>
        </tr>"""

    dummy_user = {"display_name": "Admin", "role": "admin"}
    html = f"""
{flash_html}
<div class="card" style="margin-bottom:16px">
  <div class="card-hdr">👑 User Management ({len([u for k,u in users.items() if not k.startswith('_') and isinstance(u,dict)])} users)</div>
  <div style="overflow-x:auto">
  <table class="tbl">
    <thead><tr>
      <th>User</th><th>Role</th><th>Portfolio</th><th>Watchlist</th><th>Last Update</th><th>Actions</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
</div>

<div class="card">
  <div class="card-hdr">➕ เพิ่ม User ใหม่</div>
  <form method="POST" action="/admin/create-user" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Username</div>
      <input name="uname" placeholder="username" style="width:130px" required>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Display Name</div>
      <input name="display" placeholder="ชื่อแสดง" style="width:150px" required>
    </div>
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Password</div>
      <input name="pwd" type="password" placeholder="รหัสผ่าน" style="width:130px" required>
    </div>
    <button class="btn btn-primary" type="submit">➕ สร้าง User</button>
  </form>
</div>
"""
    return _base("admin", "Admin Panel", html, dummy_user, "", "")


def insider_page(user: dict, market_data: dict) -> str:
    ticker_html = _ticker_html(market_data)
    port_syms = list(user.get("portfolio", {}).keys())
    wl_syms   = user.get("watchlist", [])
    suggest   = list(dict.fromkeys(port_syms + wl_syms))[:5]
    default   = suggest[0] if suggest else "NVDA"

    html = f"""
<div class="card" style="margin-bottom:14px">
  <div class="card-hdr">🏦 Insider Trading — SEC Form 4</div>
  <div style="font-size:12px;color:var(--muted);margin-bottom:10px">ดู insider ซื้อ/ขายหุ้นบริษัทตัวเอง · ข้อมูลจาก yfinance (SEC filings)</div>
  <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
    <div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px">Symbol</div>
      <input id="insiderSym" value="{default}" placeholder="NVDA" style="width:120px;text-transform:uppercase"
             list="insiderSuggest" oninput="this.value=this.value.toUpperCase()">
      <datalist id="insiderSuggest">{"".join(f'<option value="{s}">' for s in suggest)}</datalist>
    </div>
    <button class="btn btn-primary" onclick="loadInsider()">🔍 ดู Insider</button>
  </div>
</div>

<div id="insiderStatus" style="color:var(--muted);font-size:12px;margin-bottom:10px"></div>

<div class="card" id="insiderCard" style="display:none">
  <div class="card-hdr" id="insiderHdr">Insider Transactions</div>
  <div style="overflow-x:auto">
    <table class="tbl" id="insiderTable"></table>
  </div>
  <div id="insiderSummary" style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap;font-size:12px"></div>
</div>
"""

    js = """
function loadInsider(){
  const sym=document.getElementById('insiderSym').value.trim().toUpperCase();
  if(!sym){document.getElementById('insiderStatus').textContent='⚠️ ใส่ symbol ก่อน';return;}
  document.getElementById('insiderStatus').textContent='⏳ กำลังดึงข้อมูล SEC filings…';
  document.getElementById('insiderCard').style.display='none';
  fetch('/api/insider/'+sym).then(r=>r.json()).then(d=>{
    if(d.error){document.getElementById('insiderStatus').textContent='❌ '+d.error;return;}
    document.getElementById('insiderHdr').textContent='🏦 Insider Transactions — '+sym+' ('+d.transactions.length+' รายการ)';
    let html='<thead><tr><th>วันที่</th><th>Insider</th><th>ตำแหน่ง</th><th>Action</th><th style="text-align:right">จำนวนหุ้น</th><th style="text-align:right">ราคา</th><th style="text-align:right">มูลค่า</th></tr></thead><tbody>';
    for(const t of d.transactions){
      const isBuy=t.type&&t.type.toLowerCase().includes('buy');
      const col=isBuy?'var(--green)':'var(--red)';
      const label=isBuy?'BUY':'SELL';
      html+=`<tr>
        <td style="color:var(--muted);font-size:11px">${t.date||'—'}</td>
        <td style="font-size:12px;font-weight:600">${t.name||'—'}</td>
        <td style="font-size:11px;color:var(--muted)">${t.title||'—'}</td>
        <td><span style="color:${col};font-weight:700;font-size:11px;border:1px solid ${col};padding:1px 6px;border-radius:4px">${label}</span></td>
        <td style="text-align:right;font-weight:600">${(t.shares||0).toLocaleString()}</td>
        <td style="text-align:right">$${(t.price||0).toFixed(2)}</td>
        <td style="text-align:right;color:${col}">${t.value?'$'+(t.value/1e6).toFixed(2)+'M':'—'}</td>
      </tr>`;
    }
    html+='</tbody>';
    document.getElementById('insiderTable').innerHTML=html;
    // Summary
    const buys=d.transactions.filter(t=>t.type&&t.type.toLowerCase().includes('buy'));
    const sells=d.transactions.filter(t=>!t.type||!t.type.toLowerCase().includes('buy'));
    const buyVal=buys.reduce((a,t)=>a+(t.value||0),0);
    const sellVal=sells.reduce((a,t)=>a+(t.value||0),0);
    const net=buyVal-sellVal;
    const netCol=net>=0?'var(--green)':'var(--red)';
    document.getElementById('insiderSummary').innerHTML=`
      <div class="card" style="padding:10px 14px;flex:1;min-width:130px">
        <div style="font-size:10px;color:var(--muted)">Buy Value</div>
        <div style="font-size:16px;font-weight:800;color:var(--green)">$${(buyVal/1e6).toFixed(2)}M</div>
        <div style="font-size:11px;color:var(--muted)">${buys.length} transactions</div>
      </div>
      <div class="card" style="padding:10px 14px;flex:1;min-width:130px">
        <div style="font-size:10px;color:var(--muted)">Sell Value</div>
        <div style="font-size:16px;font-weight:800;color:var(--red)">$${(sellVal/1e6).toFixed(2)}M</div>
        <div style="font-size:11px;color:var(--muted)">${sells.length} transactions</div>
      </div>
      <div class="card" style="padding:10px 14px;flex:1;min-width:130px">
        <div style="font-size:10px;color:var(--muted)">Net Insider Flow</div>
        <div style="font-size:16px;font-weight:800;color:${netCol}">${net>=0?'+':''}$${(net/1e6).toFixed(2)}M</div>
        <div style="font-size:11px;color:var(--muted)">${net>=0?'Bullish signal':'Bearish signal'}</div>
      </div>`;
    document.getElementById('insiderCard').style.display='';
    document.getElementById('insiderStatus').textContent='✅ อัปเดต '+d.updated;
  }).catch(e=>{document.getElementById('insiderStatus').textContent='❌ '+e;});
}
"""
    return _base("insider", "Insider Trading", html, user, ticker_html, js)


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


# ─── GEO MONITOR PAGE ────────────────────────────────────────────────────────

# ─── GEO MONITOR PAGE v2 ─────────────────────────────────────────────────────

def geo_page(user: dict) -> str:
    content = (
        '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
        '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet-src.min.js"></script>'
        """
<style>
.main{overflow:hidden!important}
.content{padding:0!important;overflow:hidden!important}
#geo-wrap{position:relative;width:100%;height:100%;border-radius:0;overflow:hidden;border:none}
#geo-map{width:100%;height:100%}
.geo-layers{position:absolute;top:12px;left:12px;z-index:900;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 300px)}
.layer-btn{background:#111;border:1px solid #333;color:#aaa;padding:5px 10px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;letter-spacing:.5px;transition:.15s;font-family:inherit}
.layer-btn.on{border-color:#e0e0e0;color:#f0f0f0;background:#1a1a1a}
.layer-btn:hover{border-color:#666;color:#ccc}
.geo-panel{position:absolute;top:12px;right:12px;z-index:900;width:270px;background:rgba(10,10,10,.92);border:1px solid #2a2a2a;border-radius:10px;padding:14px;backdrop-filter:blur(6px);max-height:calc(100% - 24px);overflow-y:auto}
.geo-panel h3{font-size:11px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#888;margin-bottom:10px}
.impact-item{padding:8px 0;border-bottom:1px solid #1e1e1e;cursor:pointer}
.impact-item:last-child{border:none}
.impact-title{font-size:12px;font-weight:600;color:#e0e0e0;line-height:1.4;margin-bottom:4px}
.impact-tags{display:flex;gap:4px;flex-wrap:wrap}
.tag-up{background:rgba(76,175,80,.15);color:#4caf50;border:1px solid rgba(76,175,80,.3);padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.tag-dn{background:rgba(239,83,80,.15);color:#ef5350;border:1px solid rgba(239,83,80,.3);padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.tag-neu{background:rgba(100,100,100,.15);color:#888;border:1px solid #333;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
.geo-legend{position:absolute;bottom:20px;left:12px;z-index:900;background:rgba(10,10,10,.88);border:1px solid #2a2a2a;border-radius:8px;padding:10px 14px;font-size:10px;color:#888;max-height:300px;overflow-y:auto}
.leg-row{display:flex;align-items:center;gap:7px;margin-bottom:5px;white-space:nowrap}
.leg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.leg-box{width:14px;height:10px;border-radius:2px;flex-shrink:0;opacity:.75}
.geo-status{position:absolute;bottom:20px;right:12px;z-index:900;background:rgba(10,10,10,.88);border:1px solid #2a2a2a;border-radius:6px;padding:5px 10px;font-size:10px;color:#555}
.leaflet-popup-content-wrapper{background:#111;border:1px solid #2a2a2a;color:#e0e0e0;border-radius:8px;font-family:Inter,sans-serif;font-size:12px}
.leaflet-popup-tip{background:#111}
.leaflet-popup-content{margin:10px 14px;line-height:1.6}
.pop-title{font-weight:700;font-size:13px;margin-bottom:6px;color:#f0f0f0}
.pop-sub{font-size:11px;color:#777;margin-bottom:4px}
.pop-impact{margin-top:8px;padding-top:8px;border-top:1px solid #2a2a2a}
.hub-mk{display:flex;align-items:center;gap:3px;padding:3px 7px;border-radius:4px;font-size:10px;font-weight:800;white-space:nowrap;border:1px solid rgba(255,255,255,.15)}
</style>
<div id="geo-wrap">
  <div id="geo-map"></div>
  <div class="geo-layers">
    <button class="layer-btn on"  id="btn-zones"    onclick="toggleZoneLayer(this)">&#127757; Power Zones</button>
    <button class="layer-btn on"  id="btn-conflict" onclick="toggleLayer('conflict',this)">&#9876; Conflict</button>
    <button class="layer-btn on"  id="btn-quake"    onclick="toggleLayer('quake',this)">&#127755; Quake</button>
    <button class="layer-btn on"  id="btn-choke"    onclick="toggleLayer('choke',this)">&#128722; Chokepoints</button>
    <button class="layer-btn on"  id="btn-supply"   onclick="toggleLayer('supply',this)">&#127981; Supply Chain</button>
    <button class="layer-btn on"  id="btn-hubs"     onclick="toggleLayer('hubs',this)">&#128202; Markets</button>
    <button class="layer-btn on"  id="btn-lines"    onclick="toggleLayer('lines',this)">&#128279; Impact Lines</button>
    <button class="layer-btn"     id="btn-refresh"  onclick="loadEvents()" style="border-color:#555;color:#aaa">&#8635; Refresh</button>
  </div>
  <div class="geo-panel">
    <h3>&#127760; Market Impact</h3>
    <div id="impactList"><div style="color:#555;font-size:12px">Loading events...</div></div>
  </div>
  <div class="geo-legend" id="geoLegend">
    <div style="font-size:10px;font-weight:800;letter-spacing:1px;color:#666;margin-bottom:7px">POWER ZONES</div>
    <div class="leg-row"><div class="leg-box" style="background:#2563eb"></div>Western Alliance</div>
    <div class="leg-row"><div class="leg-box" style="background:#ef4444"></div>China &amp; Allies</div>
    <div class="leg-row"><div class="leg-box" style="background:#7f1d1d"></div>Russia &amp; CIS</div>
    <div class="leg-row"><div class="leg-box" style="background:#0d9488"></div>ASEAN</div>
    <div class="leg-row"><div class="leg-box" style="background:#d97706"></div>Middle East / OPEC</div>
    <div class="leg-row"><div class="leg-box" style="background:#7c3aed"></div>South Asia</div>
    <div class="leg-row"><div class="leg-box" style="background:#ea580c"></div>Latin America</div>
    <div class="leg-row"><div class="leg-box" style="background:#16a34a"></div>Africa</div>
    <div class="leg-row"><div class="leg-box" style="background:#374151"></div>Neutral / Other</div>
    <div style="border-top:1px solid #222;margin:8px 0"></div>
    <div style="font-size:10px;font-weight:800;letter-spacing:1px;color:#666;margin-bottom:7px">SUPPLY CHAIN</div>
    <div class="leg-row"><div class="leg-dot" style="background:#818cf8"></div>Semiconductor Fab</div>
    <div class="leg-row"><div class="leg-dot" style="background:#fcd34d"></div>Gold Mine (Top 10)</div>
    <div class="leg-row"><div class="leg-dot" style="background:#78350f"></div>Major Oil Field</div>
    <div style="border-top:1px solid #222;margin:8px 0"></div>
    <div style="font-size:10px;font-weight:800;letter-spacing:1px;color:#666;margin-bottom:7px">EVENTS</div>
    <div class="leg-row"><div class="leg-dot" style="background:#ef5350"></div>Conflict / War</div>
    <div class="leg-row"><div class="leg-dot" style="background:#f59e0b"></div>Earthquake</div>
    <div class="leg-row"><div class="leg-dot" style="background:#c8b87a"></div>Oil Chokepoint</div>
  </div>
  <div class="geo-status" id="geoStatus">&#8212;</div>
</div>
<script>
// ── Power Zones ──────────────────────────────────────────────────────────────
const ZONES = [
  {id:"west",    label:"Western Alliance",   color:"#2563eb",
   iso2:["US","CA","GB","IE","FR","DE","IT","ES","PT","NL","BE","LU","AT","CH","DK","NO","SE","FI","IS","PL","CZ","SK","HU","RO","BG","EE","LV","LT","HR","SI","GR","MT","CY","AL","ME","MK","BA","RS","AU","NZ","JP","KR","IL","LI","AD","MC","SM"]},
  {id:"china",   label:"China & Allies",     color:"#ef4444",
   iso2:["CN","KP","MM"]},
  {id:"russia",  label:"Russia & CIS",       color:"#991b1b",
   iso2:["RU","BY","KZ","KG","TJ","UZ","TM","AM","AZ"]},
  {id:"asean",   label:"ASEAN",              color:"#0d9488",
   iso2:["TH","VN","ID","MY","PH","SG","KH","LA","BN","TL"]},
  {id:"mideast", label:"Middle East / OPEC", color:"#d97706",
   iso2:["SA","AE","QA","KW","BH","OM","IR","IQ","SY","YE","JO","LB","TR","EG","LY","DZ","TN","MA","PS"]},
  {id:"sasia",   label:"South Asia",         color:"#7c3aed",
   iso2:["IN","PK","BD","LK","NP","BT","MV","AF"]},
  {id:"latam",   label:"Latin America",      color:"#ea580c",
   iso2:["BR","MX","AR","CO","CL","PE","VE","EC","BO","PY","UY","GY","SR","CR","PA","CU","DO","HN","GT","SV","NI","HT","JM","TT","BB","BS","BZ","GD","LC","VC","KN","AG","DM","GF"]},
  {id:"africa",  label:"Africa",             color:"#16a34a",
   iso2:["ZA","KE","TZ","UG","ET","SD","SS","SO","MZ","ZM","ZW","MW","MG","BW","NA","SZ","LS","RW","BI","DJ","ER","CD","CF","CM","TG","BJ","CI","GN","GW","SL","LR","GH","NG","NE","ML","BF","MR","SN","GM","CV","ST","GQ","GA","CG","AO","TD","KM","SC","MU"]},
  {id:"other",   label:"Neutral / Other",    color:"#374151", iso2:[]},
];
const ZONE_BY_ISO = {};
ZONES.forEach(z=>z.iso2.forEach(c=>ZONE_BY_ISO[c]=z));

// ── Supply Chain ─────────────────────────────────────────────────────────────
const SUPPLY = [
  // Semiconductor Fabs
  {type:"semi", lat:24.80,  lng:120.97, name:"TSMC (Hsinchu)",     note:"2nm / 3nm / 5nm · N.America+Japan customer",       stocks:["TSM","NVDA","AMD","AAPL","AVGO"]},
  {type:"semi", lat:23.00,  lng:120.22, name:"TSMC (Tainan N3/N2)",note:"N3E mass prod · Taiwan geopolitical risk",          stocks:["TSM","NVDA","QCOM"]},
  {type:"semi", lat:37.20,  lng:127.05, name:"Samsung (Hwaseong)", note:"3nm GAA · DRAM · HBM for AI GPU",                  stocks:["005930.KS","NVDA"]},
  {type:"semi", lat:30.26,  lng:-97.74, name:"Samsung (Austin TX)", note:"14nm mature node · US onshore",                   stocks:["005930.KS"]},
  {type:"semi", lat:45.52,  lng:-122.93,name:"Intel (Hillsboro OR)",note:"Intel 18A / 3nm · IFS foundry push",              stocks:["INTC"]},
  {type:"semi", lat:53.35,  lng:-6.49,  name:"Intel (Leixlip IE)",  note:"Fab 34 · Intel 4 / EU Chips Act",                 stocks:["INTC"]},
  {type:"semi", lat:51.42,  lng:5.41,   name:"ASML (Veldhoven NL)", note:"Only EUV/High-NA supplier · Zero substitute",     stocks:["ASML"]},
  {type:"semi", lat:31.23,  lng:121.47, name:"SMIC (Shanghai CN)",  note:"7nm domestic · US sanction block on EUV",         stocks:["981.HK"]},
  {type:"semi", lat:1.35,   lng:103.82, name:"GlobalFoundries (SG)",note:"22nm mature · automotive/RF",                     stocks:["GFS"]},
  {type:"semi", lat:43.60,  lng:-116.20,name:"Micron (Boise ID)",   note:"DRAM / NAND · HBM4 in dev",                      stocks:["MU"]},
  // Gold Mines
  {type:"gold", lat:41.51,  lng:64.57,  name:"Muruntau (UZ)",      note:"~70t/yr · worlds largest open-pit gold mine",      stocks:["GLD","GOLD"]},
  {type:"gold", lat:-4.05,  lng:137.12, name:"Grasberg (ID)",       note:"~45t/yr · Freeport · copper+gold giant",          stocks:["FCX","GLD"]},
  {type:"gold", lat:40.35,  lng:-116.65,name:"Cortez (NV US)",      note:"~30t/yr · Barrick Gold",                          stocks:["GOLD","GLD"]},
  {type:"gold", lat:-32.70, lng:116.47, name:"Boddington (AU)",     note:"~28t/yr · Newmont · open pit",                   stocks:["NEM","GLD"]},
  {type:"gold", lat:18.99,  lng:-70.02, name:"Pueblo Viejo (DO)",   note:"~27t/yr · Barrick+Newmont JV",                   stocks:["GOLD","NEM"]},
  {type:"gold", lat:3.66,   lng:29.58,  name:"Kibali (CD)",         note:"~25t/yr · AngloGold · DRC conflict zone",         stocks:["AU","GLD"]},
  {type:"gold", lat:-3.12,  lng:152.63, name:"Lihir (PG)",          note:"~24t/yr · Newcrest/Newmont · Pacific",            stocks:["NEM","GLD"]},
  {type:"gold", lat:-26.48, lng:27.34,  name:"Mponeng (ZA)",        note:"~12t/yr · deepest mine on Earth 4km",             stocks:["AU","GLD"]},
  {type:"gold", lat:59.00,  lng:93.00,  name:"Olimpiada (RU)",      note:"~50t/yr · Polyus · sanctioned supply risk",       stocks:["GLD"]},
  {type:"gold", lat:40.71,  lng:-116.10,name:"Carlin Trend (NV US)",note:"~28t/yr · Nevada Gold Mines · Barrick",           stocks:["GOLD","GLD"]},
  // Oil Fields
  {type:"oil",  lat:25.00,  lng:49.50,  name:"Ghawar (SA)",         note:"~3.8Mb/d · worlds largest oil field · Aramco",   stocks:["2222.SR","USO"]},
  {type:"oil",  lat:28.00,  lng:48.50,  name:"Safaniya (SA)",       note:"~1.5Mb/d · worlds largest offshore field",        stocks:["2222.SR","USO"]},
  {type:"oil",  lat:29.00,  lng:48.00,  name:"Burgan (KW)",         note:"~1.7Mb/d · Kuwait · 2nd largest ever found",      stocks:["USO","XOM"]},
  {type:"oil",  lat:30.80,  lng:47.40,  name:"Rumaila (IQ)",        note:"~1.4Mb/d · Iraq · BP operator",                  stocks:["BP","USO"]},
  {type:"oil",  lat:31.50,  lng:-102.50,name:"Permian Basin (TX)",  note:"~5.8Mb/d · US shale king · XOM/CVX/Pioneer",     stocks:["XOM","CVX","PXD","USO"]},
  {type:"oil",  lat:61.00,  lng:76.00,  name:"Samotlor (RU)",       note:"~0.5Mb/d · W.Siberia · sanction overhang",       stocks:["USO"]},
  {type:"oil",  lat:45.50,  lng:53.30,  name:"Tengiz (KZ)",         note:"~0.65Mb/d · Chevron op · Caspian route risk",    stocks:["CVX","USO"]},
  {type:"oil",  lat:-22.00, lng:-40.00, name:"Tupi / Lula (BR)",    note:"~1Mb/d · Petrobras · deepwater pre-salt",        stocks:["PBR","USO"]},
  {type:"oil",  lat:20.00,  lng:-91.00, name:"Cantarell (MX)",      note:"~0.35Mb/d · declining · Pemex",                  stocks:["USO"]},
  {type:"oil",  lat:46.00,  lng:52.00,  name:"Kashagan (KZ)",       note:"~0.4Mb/d · Caspian · Shell/Total JV",            stocks:["SHEL","TTE","USO"]},
];

// ── Market hubs ──────────────────────────────────────────────────────────────
const HUBS = {
  gold:   {lat:47.37,  lng:8.54,    label:"Gold",    color:"#c8b87a", bg:"rgba(200,184,122,.18)"},
  oil:    {lat:29.76,  lng:-95.37,  label:"Oil WTI", color:"#CD853F", bg:"rgba(205,133,63,.18)"},
  sp500:  {lat:40.71,  lng:-74.01,  label:"S&P500",  color:"#4caf50", bg:"rgba(76,175,80,.18)"},
  nikkei: {lat:35.68,  lng:139.69,  label:"Nikkei",  color:"#FF6347", bg:"rgba(255,99,71,.18)"},
  set:    {lat:13.75,  lng:100.52,  label:"SET",     color:"#60a5fa", bg:"rgba(96,165,250,.18)"},
  crypto: {lat:37.77,  lng:-122.42, label:"Crypto",  color:"#a78bfa", bg:"rgba(167,139,250,.18)"},
};

// ── Chokepoints ───────────────────────────────────────────────────────────────
const CHOKES = [
  {lat:26.56,lng:56.26, name:"Strait of Hormuz",   note:"20% world oil supply"},
  {lat:30.58,lng:32.35, name:"Suez Canal",           note:"~12% world trade"},
  {lat:1.14, lng:103.58,name:"Strait of Malacca",   note:"25% world trade"},
  {lat:41.12,lng:29.08, name:"Bosporus Strait",      note:"Russian oil route"},
  {lat:35.97,lng:-5.36, name:"Strait of Gibraltar",  note:"Atlantic-Med gateway"},
  {lat:12.5, lng:43.5,  name:"Bab el-Mandeb",        note:"Red Sea choke"},
  {lat:28.5, lng:-80.0, name:"Panama Canal",         note:"Atlantic-Pacific route"},
];

// ── Map init ──────────────────────────────────────────────────────────────────
const map = L.map("geo-map",{center:[20,10],zoom:2,preferCanvas:true});
L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",{
  attribution:"© CARTO",subdomains:"abcd",maxZoom:19
}).addTo(map);
setTimeout(()=>map.invalidateSize(),250);
window.addEventListener("resize",()=>map.invalidateSize());

const layers={conflict:[],quake:[],choke:[],hubs:[],lines:[],supply:[]};
const visible={conflict:true,quake:true,choke:true,hubs:true,lines:true,supply:true,zones:true};
let activeLines=[];
let zoneGeoLayer=null;
let zoneLoaded=false;

// ── Power Zone layer ──────────────────────────────────────────────────────────
function getZoneStyle(iso2){
  const zone = ZONE_BY_ISO[iso2] || ZONES[ZONES.length-1];
  return {
    fillColor: zone.color,
    fillOpacity: 0.22,
    color: zone.color,
    weight: 0.6,
    opacity: 0.5,
  };
}
async function loadZones(){
  if(zoneLoaded && zoneGeoLayer){zoneGeoLayer.addTo(map);return;}
  try{
    const r = await fetch("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson");
    const gj = await r.json();
    zoneGeoLayer = L.geoJSON(gj,{
      style: feat=>{
        const iso2 = (feat.properties||{}).ISO_A2 || "";
        return getZoneStyle(iso2);
      },
      onEachFeature:(feat,layer)=>{
        const iso2 = (feat.properties||{}).ISO_A2||"";
        const zone = ZONE_BY_ISO[iso2]||ZONES[ZONES.length-1];
        const name = (feat.properties||{}).ADMIN||(feat.properties||{}).NAME||iso2;
        layer.bindTooltip("<b>"+name+"</b><br><span style=\\"color:"+zone.color+";font-weight:700\\">"+zone.label+"</span>",{sticky:true});
      }
    });
    zoneGeoLayer.addTo(map);
    zoneGeoLayer.bringToBack();
    zoneLoaded=true;
  }catch(e){console.error("Zone GeoJSON load failed",e);}
}
function toggleZoneLayer(btn){
  visible.zones=!visible.zones;
  btn.classList.toggle("on",visible.zones);
  if(visible.zones){
    if(zoneLoaded&&zoneGeoLayer){zoneGeoLayer.addTo(map);zoneGeoLayer.bringToBack();}
    else loadZones();
  } else {
    if(zoneGeoLayer) map.removeLayer(zoneGeoLayer);
  }
}

// ── Supply Chain markers ──────────────────────────────────────────────────────
const SC_STYLE={
  semi:{color:"#818cf8",size:9,shape:"circle",label:"SEMI"},
  gold:{color:"#fcd34d",size:8,shape:"diamond",label:"GOLD"},
  oil: {color:"#92400e",size:9,shape:"square", label:"OIL"},
};
function addSupplyChain(){
  SUPPLY.forEach(sc=>{
    const st=SC_STYLE[sc.type];
    let shapeHtml;
    if(sc.type==="gold")
      shapeHtml="<div style=\\"width:10px;height:10px;background:"+st.color+";border:1.5px solid #a07800;transform:rotate(45deg);\\"></div>";
    else if(sc.type==="semi")
      shapeHtml="<div style=\\"width:10px;height:10px;background:"+st.color+";border:1.5px solid #6366f1;border-radius:50%;\\"></div>";
    else
      shapeHtml="<div style=\\"width:10px;height:10px;background:"+st.color+";border:1.5px solid #5c2d00;border-radius:2px;\\"></div>";
    const icon=L.divIcon({className:"",html:shapeHtml,iconSize:[10,10],iconAnchor:[5,5]});
    const m=L.marker([sc.lat,sc.lng],{icon,zIndexOffset:200}).addTo(map);
    const stockTags=(sc.stocks||[]).map(s=>"<code style=\\"background:#1a1a1a;padding:1px 4px;border-radius:3px;font-size:10px;color:#ccc\\">"+s+"</code>").join(" ");
    m.bindPopup(
      "<div class=\\"pop-title\\">"+
        (sc.type==="semi"?"&#128187; ":sc.type==="gold"?"&#9651; ":"&#128722; ")+
        sc.name+"</div>"+
      "<div class=\\"pop-sub\\">"+sc.note+"</div>"+
      (stockTags?"<div class=\\"pop-impact\\"><div style=\\"font-size:10px;color:#666;margin-bottom:4px\\">Related stocks:</div>"+stockTags+"</div>":"")
    );
    layers.supply.push(m);
  });
}

// ── Hub markers ───────────────────────────────────────────────────────────────
function addHubs(){
  Object.entries(HUBS).forEach(([key,h])=>{
    const icon=L.divIcon({className:"",
      html:"<div class=\\"hub-mk\\" style=\\"background:"+h.bg+";border-color:"+h.color+";color:"+h.color+"\\">"+h.label+"</div>",
      iconSize:[80,22],iconAnchor:[40,11]});
    const m=L.marker([h.lat,h.lng],{icon,zIndexOffset:500}).addTo(map);
    m.bindTooltip("<b>"+h.label+"</b>");
    layers.hubs.push(m);
  });
}

// ── Chokepoint markers ────────────────────────────────────────────────────────
function addChokes(){
  CHOKES.forEach(c=>{
    const icon=L.divIcon({className:"",
      html:"<div style=\\"width:12px;height:12px;background:#c8b87a;border:2px solid #a07848;border-radius:3px;\\"></div>",
      iconSize:[12,12],iconAnchor:[6,6]});
    const m=L.marker([c.lat,c.lng],{icon}).addTo(map);
    m.bindPopup("<div class=\\"pop-title\\">"+c.name+"</div><div class=\\"pop-sub\\">"+c.note+"</div>");
    layers.choke.push(m);
  });
}

// ── Impact lines ──────────────────────────────────────────────────────────────
function clearLines(){
  activeLines.forEach(l=>{try{map.removeLayer(l)}catch(e){}});
  activeLines=[];layers.lines=[];
}
function showLines(ev,latlng){
  clearLines();if(!visible.lines)return;
  (ev.impacts||[]).forEach(imp=>{
    const hub=HUBS[imp.market];if(!hub)return;
    const clr=imp.direction==="up"?"#4caf50":"#ef5350";
    const ln=L.polyline([[latlng.lat,latlng.lng],[hub.lat,hub.lng]],
      {color:clr,weight:1.5,opacity:.8,dashArray:"8 6"}).addTo(map);
    ln.bindTooltip("<b>"+hub.label+"</b> "+imp.label,{sticky:true});
    activeLines.push(ln);layers.lines.push(ln);
  });
}

// ── Event rendering ───────────────────────────────────────────────────────────
function renderEvents(data){
  ["conflict","quake"].forEach(k=>{layers[k].forEach(m=>{try{map.removeLayer(m)}catch(e){}});layers[k]=[];});
  clearLines();
  (data.conflicts||[]).forEach(ev=>{
    const r=Math.max(5,Math.min(14,5+(ev.tone||0)*-0.3));
    const m=L.circleMarker([ev.lat,ev.lng],{radius:r,color:"#ef5350",fillColor:"#ef5350",fillOpacity:.65,weight:1.5}).addTo(map);
    const impHtml=(ev.impacts||[]).map(i=>"<span class=\\""+( i.direction==="up"?"tag-up":"tag-dn")+"\\">" +i.label+"</span>").join(" ");
    m.bindPopup("<div class=\\"pop-title\\">&#9876; "+(ev.title||"Conflict")+"</div><div class=\\"pop-sub\\">"+(ev.source||"")+"</div><div class=\\"pop-impact\\"><div style=\\"font-size:11px;color:#888;margin-bottom:5px\\">Market Impact:</div><div style=\\"display:flex;flex-wrap:wrap;gap:4px\\">"+(impHtml||"<span class=\\"tag-neu\\">Monitoring</span>")+"</div></div>");
    m.on("click",()=>showLines(ev,m.getLatLng()));
    layers.conflict.push(m);
  });
  (data.earthquakes||[]).forEach(eq=>{
    const m=L.circleMarker([eq.lat,eq.lng],{radius:Math.max(4,eq.mag*2.5),color:"#f59e0b",fillColor:"#f59e0b",fillOpacity:.55,weight:1.5}).addTo(map);
    const impHtml=(eq.impacts||[]).map(i=>"<span class=\\""+( i.direction==="up"?"tag-up":"tag-dn")+"\\">" +i.label+"</span>").join(" ");
    m.bindPopup("<div class=\\"pop-title\\">&#127755; M"+eq.mag+" — "+(eq.place||"Unknown")+"</div><div class=\\"pop-impact\\"><div style=\\"font-size:11px;color:#888;margin-bottom:5px\\">Market Impact:</div><div style=\\"display:flex;flex-wrap:wrap;gap:4px\\">"+(impHtml||"<span class=\\"tag-neu\\">Minor / No impact</span>")+"</div></div>");
    m.on("click",()=>showLines(eq,m.getLatLng()));
    layers.quake.push(m);
  });
  updatePanel(data);
  document.getElementById("geoStatus").textContent="Updated "+new Date().toLocaleTimeString("th-TH")+" | "+(data.conflicts||[]).length+" conflicts | "+(data.earthquakes||[]).length+" quakes";
}

// ── Impact panel ──────────────────────────────────────────────────────────────
function updatePanel(data){
  const all=[...(data.conflicts||[]).map(e=>({...e,_t:"conflict"})),
             ...(data.earthquakes||[]).filter(e=>(e.impacts||[]).length>0).map(e=>({...e,_t:"quake"}))];
  all.sort((a,b)=>(b.impacts||[]).length-(a.impacts||[]).length);
  if(!all.length){document.getElementById("impactList").innerHTML="<div style=\\"color:#555;font-size:12px\\">No impact events</div>";return;}
  document.getElementById("impactList").innerHTML=all.slice(0,15).map(ev=>{
    const icon=ev._t==="conflict"?"&#9876;":"&#127755;";
    const impHtml=(ev.impacts||[]).map(i=>"<span class=\\""+( i.direction==="up"?"tag-up":"tag-dn")+"\\">" +i.label+"</span>").join(" ");
    return "<div class=\\"impact-item\\" onclick=\\"map.flyTo(["+ev.lat+","+ev.lng+"],5)\\"><div class=\\"impact-title\\">"+icon+" "+(ev.title||ev.place||"").substring(0,60)+"</div><div class=\\"impact-tags\\">"+(impHtml||"<span class=\\"tag-neu\\">Monitoring</span>")+"</div></div>";
  }).join("");
}

// ── Toggle ────────────────────────────────────────────────────────────────────
function toggleLayer(key,btn){
  visible[key]=!visible[key];
  btn.classList.toggle("on",visible[key]);
  if(key==="lines"){if(!visible.lines)clearLines();return;}
  layers[key].forEach(m=>{if(visible[key])m.addTo(map);else map.removeLayer(m);});
}

// ── Fetch events ──────────────────────────────────────────────────────────────
async function loadEvents(){
  document.getElementById("geoStatus").textContent="Loading...";
  try{
    const r=await fetch("/api/geo-events");
    const data=await r.json();
    renderEvents(data);
  }catch(e){
    document.getElementById("geoStatus").textContent="Error fetching data";
    console.error(e);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadZones();
addSupplyChain();
addHubs();
addChokes();
loadEvents();
setInterval(loadEvents,300000);
</script>"""
    )
    return _base("map", "Geo Monitor", content, user)
