"""
Daily Stock Analysis Dashboard with interactive price charts.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent


# ─── Signal Engine ────────────────────────────────────────────────────────────

def analyze(d: dict) -> dict:
    rsi   = d.get("rsi")
    chg   = d.get("change_pct", 0) or 0
    price = d.get("price", 0) or 0
    h52   = d.get("high_52w") or price * 1.30
    l52   = d.get("low_52w")  or price * 0.70

    rng       = h52 - l52
    pct_range = (price - l52) / rng * 100 if rng > 0 else 50
    pct_high  = (h52 - price) / h52 * 100

    entry = round(price, 2)
    sl    = round(price * 0.92, 2)
    tp    = round(price * 1.18, 2)
    rr    = round((tp - entry) / (entry - sl), 1) if entry > sl else 0

    action = "NEUTRAL"
    reason = ""
    stars  = 0

    if rsi is None:
        if chg >= 2.5:   action, reason, stars = "BUY",   "Strong momentum breakout today", 2
        elif chg >= 1.0: action, reason, stars = "WATCH", "Positive momentum, wait for confirmation", 0
        elif chg <= -2.5:action, reason        = "AVOID", "Heavy selling today, wait for bottom"
        else:            action, reason        = "NEUTRAL","No RSI data available"
    elif rsi <= 30:
        if chg >= -1.0:  action, reason, stars = "BUY",   f"RSI extremely oversold ({rsi}) — reversal likely", 3
        elif chg >= -3.0:action, reason, stars = "BUY",   f"RSI oversold ({rsi}), mild dip today", 2
        else:            action, reason        = "WAIT",  f"RSI oversold ({rsi}) but still falling — wait"
    elif rsi <= 40:
        if chg >= 1.0:   action, reason, stars = "BUY",   f"RSI low ({rsi}) bouncing up — good entry", 3
        elif chg >= 0:   action, reason, stars = "BUY",   f"RSI low ({rsi}), holding support", 2
        elif chg >= -2.0:action, reason, stars = "WATCH", f"RSI {rsi} — approaching entry zone", 0
        else:            action, reason        = "WAIT",  f"RSI {rsi} but selling pressure today"
    elif rsi <= 50:
        if chg >= 2.5:   action, reason, stars = "BUY",   f"RSI neutral ({rsi}) + strong breakout today", 2
        elif chg >= 0.5 and pct_range < 30:
                         action, reason, stars = "WATCH", f"RSI {rsi}, near support zone", 0
        elif chg <= -2.0:action, reason        = "WAIT",  f"RSI {rsi} dipping — wait for stability"
        else:            action, reason        = "NEUTRAL",f"RSI {rsi} — sideways, no clear signal"
    elif rsi <= 60:
        if chg >= 3.0:   action, reason, stars = "WATCH", f"RSI {rsi} + big move today — possible breakout", 0
        elif chg <= -2.0:action, reason        = "NEUTRAL",f"RSI {rsi} pulling back"
        else:            action, reason        = "NEUTRAL",f"RSI {rsi} — hold existing positions"
    elif rsi <= 70:
        if chg >= 2.0:   action, reason = "WAIT",  f"RSI {rsi} getting high — wait for pullback"
        else:            action, reason = "WAIT",  f"RSI {rsi} — overextended, wait for cooldown"
    else:
        action, reason = "AVOID", f"RSI overbought ({rsi}) — high reversal risk"

    if pct_high <= 3 and action in ("BUY", "WATCH"):
        reason += " (near 52W high, tight stop)"
    if pct_range <= 10 and action != "AVOID":
        reason += " (near 52W low support)"

    return {
        "action": action, "reason": reason, "stars": stars,
        "entry": entry, "sl": sl, "tp": tp, "rr": rr,
        "rsi": rsi, "chg": chg, "price": price,
        "high_52w": round(h52, 2), "low_52w": round(l52, 2),
        "pct_range": round(pct_range, 1),
    }


def market_summary(qqq_chg: float) -> dict:
    q = qqq_chg
    if   q >  2.0: mood, color, icon = "Strong Bullish",    "#10b981", "BULL"
    elif q >  0.5: mood, color, icon = "Mildly Bullish",    "#34d399", "BULL"
    elif q < -2.0: mood, color, icon = "Strong Bearish",    "#ef4444", "BEAR"
    elif q < -0.5: mood, color, icon = "Mildly Bearish",    "#f87171", "BEAR"
    else:          mood, color, icon = "Neutral / Sideways", "#94a3b8", "SIDE"

    if   q >  2.0: note = "Strong risk-on day. Good day to add to strong positions."
    elif q >  0.5: note = "Mild upside. Focus on oversold names that are bouncing."
    elif q < -2.0: note = "Risk-off. Avoid new entries. Wait for market to stabilize."
    elif q < -0.5: note = "Mild weakness. Not ideal for new buys. Watch your stops."
    else:          note = "No clear direction. Focus on individual stock setups."
    return {"mood": mood, "color": color, "icon": icon, "note": note}


# ─── Daily Entry Finder ───────────────────────────────────────────────────────

def find_daily_entries(stocks: list) -> list:
    """Score & rank BUY/WATCH stocks by entry quality. Returns sorted list."""
    candidates = []
    for s in stocks:
        if s.get('category'):
            continue
        action = s.get('action', '')
        if action not in ('BUY', 'WATCH'):
            continue

        rsi       = s.get('rsi') or 50
        chg       = s.get('chg', 0) or 0
        stars     = s.get('stars', 0) or 0
        pct_range = s.get('pct_range', 50) or 50
        rr        = s.get('rr', 0) or 0
        total_an  = s.get('total_analysts') or 0

        score = 15 if action == 'BUY' else 0
        score += stars * 10

        # RSI: lower oversold zone = better entry
        if   rsi <= 25: score += 40
        elif rsi <= 30: score += 35
        elif rsi <= 35: score += 30
        elif rsi <= 40: score += 25
        elif rsi <= 45: score += 15
        elif rsi <= 50: score += 8
        elif rsi <= 55: score += 3

        # 52W range position: near support = better
        if   pct_range <= 10: score += 20
        elif pct_range <= 20: score += 12
        elif pct_range <= 35: score += 6

        # Momentum today: mild positive preferred, penalise falling
        if   0.5 <= chg <= 2.0:  score += 8
        elif 2.0 < chg <= 4.0:   score += 5
        elif chg < 0:             score -= 5

        # Risk/reward quality
        if   rr >= 2.0: score += 10
        elif rr >= 1.5: score += 5

        # Analyst consensus bonus
        if total_an > 0:
            bull = ((s.get('strong_buy') or 0) + (s.get('buy') or 0)) / total_an
            if   bull >= 0.6: score += 12
            elif bull >= 0.4: score += 6

        candidates.append({**s, 'entry_score': score})

    candidates.sort(key=lambda x: -x['entry_score'])
    return candidates


# ─── HTML ─────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#090d16">
<title>Claude AI — Stock Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#090d16;--card:#0f1623;--card2:#111d2e;--border:#1c2a3a;--border2:#243040;
  --orange:#d97757;--green:#10b981;--red:#ef4444;
  --blue:#3b82f6;--yellow:#f59e0b;--purple:#a855f7;
  --text:#e2e8f0;--muted:#64748b;--muted2:#94a3b8;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}

/* ── Header ── */
.hdr{position:sticky;top:0;z-index:200;background:#0b111e;border-bottom:1px solid var(--border);padding:12px 16px;display:flex;align-items:center;justify-content:space-between}
.hdr-left{display:flex;align-items:center;gap:10px}
.logo{width:34px;height:34px;background:var(--orange);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:900;color:#fff}
.hdr-title{font-size:16px;font-weight:700}
.hdr-sub{font-size:11px;color:var(--muted)}
.date-pill{background:rgba(217,119,87,.15);border:1px solid rgba(217,119,87,.3);color:var(--orange);padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600}

/* ── Ticker ── */
.ticker{display:flex;overflow-x:auto;background:#0b111e;border-bottom:1px solid var(--border);scrollbar-width:none}
.ticker::-webkit-scrollbar{display:none}
.ti{flex:1;min-width:80px;padding:9px 14px;border-right:1px solid var(--border);display:flex;flex-direction:column;gap:2px}
.ti-sym{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.05em}
.ti-price{font-size:13px;font-weight:700}
.ti-chg{font-size:11px;font-weight:600}

/* ── Layout ── */
.main{padding:16px;max-width:1100px;margin:0 auto}
.sec-title{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:24px 0 12px;display:flex;align-items:center;gap:10px}
.sec-title::after{content:'';flex:1;height:1px;background:var(--border)}

/* ── Mood Card ── */
.mood-card{border-radius:14px;padding:16px 20px;margin-bottom:4px}
.mood-title{font-size:17px;font-weight:800}
.mood-note{font-size:13px;color:var(--muted2);margin-top:4px;line-height:1.5}

/* ── Index Row ── */
.index-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:10px;margin-bottom:4px}
.idx-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.idx-sym{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.05em}
.idx-price{font-size:15px;font-weight:800;margin-top:4px}
.idx-chg{font-size:12px;font-weight:600;margin-top:2px}

/* ── Stock Grid ── */
.stock-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}

/* ── Stock Card ── */
.sc{background:var(--card);border-radius:14px;padding:16px;border-left:4px solid var(--border);border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border);transition:.2s;cursor:pointer}
.sc:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,0,0,.45);border-top-color:var(--border2);border-right-color:var(--border2);border-bottom-color:var(--border2)}
.sc:active{transform:translateY(0)}
.sc.buy{border-left-color:var(--green)}
.sc.watch{border-left-color:var(--yellow)}
.sc.wait{border-left-color:var(--muted)}
.sc.avoid{border-left-color:var(--red)}
.sc.neutral{border-left-color:var(--border2)}
.sc-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.sc-sym{font-size:18px;font-weight:900}
.sc-name{font-size:10px;color:var(--muted);margin-top:2px;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc-price-wrap{text-align:right}
.sc-price{font-size:18px;font-weight:800}
.sc-chg{font-size:12px;font-weight:700;margin-top:2px}

/* ── Mini Sparkline ── */
.spark-wrap{height:40px;margin:8px 0;position:relative}
.spark-wrap canvas{width:100%!important;height:40px!important}

/* ── Badge ── */
.action-badge{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px}
.ab-BUY{background:rgba(16,185,129,.2);color:#10b981;border:1px solid rgba(16,185,129,.4)}
.ab-WATCH{background:rgba(245,158,11,.15);color:#f59e0b;border:1px solid rgba(245,158,11,.35)}
.ab-WAIT{background:rgba(100,116,139,.15);color:#94a3b8;border:1px solid rgba(100,116,139,.3)}
.ab-AVOID{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
.ab-NEUTRAL{background:rgba(100,116,139,.1);color:#64748b;border:1px solid rgba(100,116,139,.2)}
.stars{color:#f59e0b;font-size:12px;margin-left:4px}
.sc-reason{font-size:12px;color:var(--muted2);line-height:1.5;margin-bottom:10px;min-height:32px}
.rsi-row{display:flex;align-items:center;gap:8px}
.rsi-label{font-size:10px;color:var(--muted);width:30px;flex-shrink:0}
.rsi-track{flex:1;height:4px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden}
.rsi-fill{height:4px;border-radius:3px}
.rsi-val{font-size:11px;font-weight:700;width:26px;text-align:right;flex-shrink:0}
.sc-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.meta-chip{background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:6px;padding:3px 8px;font-size:10px;color:var(--muted2)}
.meta-chip b{color:var(--text);font-weight:700}
.tap-hint{font-size:10px;color:var(--muted);margin-top:8px;text-align:right}

/* ── Modal Overlay ── */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:500;display:none;align-items:flex-end;justify-content:center;backdrop-filter:blur(4px)}
.overlay.open{display:flex}
.modal{
  background:#0f1827;border:1px solid var(--border2);
  border-radius:20px 20px 0 0;width:100%;max-width:680px;
  max-height:92vh;overflow-y:auto;
  animation:slideUp .25s ease;
  scrollbar-width:thin;scrollbar-color:var(--border) transparent;
}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.modal-drag{width:40px;height:4px;background:var(--border2);border-radius:2px;margin:12px auto 0}
.modal-header{padding:16px 20px 12px;display:flex;justify-content:space-between;align-items:flex-start}
.modal-sym{font-size:24px;font-weight:900}
.modal-name{font-size:12px;color:var(--muted);margin-top:2px}
.modal-price-wrap{text-align:right}
.modal-price{font-size:24px;font-weight:900}
.modal-chg{font-size:13px;font-weight:700;margin-top:2px}
.modal-close{position:absolute;top:16px;right:16px;width:30px;height:30px;background:rgba(255,255,255,.08);border:none;border-radius:50%;color:var(--muted2);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.modal-close:hover{background:rgba(255,255,255,.15);color:var(--text)}

/* Chart area */
.chart-area{padding:0 20px 4px;position:relative}
.chart-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;height:220px;position:relative}
.chart-period{display:flex;gap:6px;margin-bottom:10px}
.period-btn{padding:4px 10px;border-radius:6px;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:11px;font-weight:600;cursor:pointer;transition:.15s}
.period-btn.active{background:var(--orange);border-color:var(--orange);color:#fff}

/* Stats grid */
.modal-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 20px}
@media(max-width:400px){.modal-stats{grid-template-columns:repeat(2,1fr)}}
.ms{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px}
.ms-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.ms-val{font-size:16px;font-weight:800;margin-top:4px}

/* Action section */
.modal-action{padding:12px 20px;background:var(--card2);margin:0 20px;border-radius:12px;border:1px solid var(--border)}
.action-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
.action-row:last-child{border-bottom:none}
.ar-label{color:var(--muted);font-size:12px}
.ar-val{font-weight:700}
.modal-reason{padding:12px 20px;font-size:13px;color:var(--muted2);line-height:1.6}
.modal-footer-pad{height:24px}

/* Colors */
.pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--muted2)}.yl{color:var(--yellow)}
/* Analyst Consensus bar */
.reco-bar{display:flex;height:8px;border-radius:6px;overflow:hidden;margin:10px 0 6px}
.reco-sb{background:#10b981}.reco-b{background:#34d399}.reco-h{background:#f59e0b}.reco-s{background:#f87171}.reco-ss{background:#ef4444}
.reco-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--muted)}
.reco-counts{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.reco-pill{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:20px;font-size:11px;font-weight:700}
.reco-pill.sb{background:rgba(16,185,129,.2);color:#10b981}
.reco-pill.b{background:rgba(52,211,153,.15);color:#34d399}
.reco-pill.h{background:rgba(245,158,11,.15);color:#f59e0b}
.reco-pill.s{background:rgba(248,113,113,.15);color:#f87171}
.reco-pill.ss{background:rgba(239,68,68,.2);color:#ef4444}

/* Financials table in modal */
.fin-section{padding:0 20px 8px}
.fin-title{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:8px;display:flex;align-items:center;gap:8px}
.fin-title::after{content:'';flex:1;height:1px;background:var(--border)}
.fin-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.fin-item{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 10px}
.fin-label{font-size:10px;color:var(--muted);font-weight:600}
.fin-val{font-size:14px;font-weight:800;margin-top:2px}
.fin-sub{font-size:10px;color:var(--muted2);margin-top:1px}
.ma-row{display:flex;gap:8px;padding:6px 0;font-size:12px}
.ma-item{flex:1;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:6px 10px;text-align:center}
.ma-label{font-size:10px;color:var(--muted)}
.ma-val{font-size:13px;font-weight:800;margin-top:2px}

/* Commodity / Crypto cards */
.comm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-bottom:20px}
.comm-card{background:var(--card);border-radius:16px;padding:16px 18px;cursor:pointer;transition:.2s;border:1px solid transparent}
.comm-card:hover{transform:translateY(-2px);background:var(--card2)}
.comm-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.comm-icon{font-size:24px;line-height:1}
.comm-sym{font-size:16px;font-weight:900}
.comm-name{font-size:11px;color:var(--muted);margin-top:2px}
.comm-price{font-size:24px;font-weight:900;margin-bottom:4px}
.comm-chg{font-size:13px;font-weight:700;margin-bottom:10px}
.comm-range{font-size:11px;color:var(--muted);margin-top:6px}

/* News section in modal */
.news-item{display:block;padding:10px 0;border-bottom:1px solid var(--border);text-decoration:none;color:inherit;cursor:pointer}
.news-item:last-child{border-bottom:none}
.news-title{font-size:13px;line-height:1.45;color:var(--text);transition:color .15s}
.news-item:hover .news-title{color:#60a5fa}
.news-date{font-size:11px;color:var(--muted);margin-top:3px}

/* ── Page Tabs ── */
.page-tabs{display:flex;gap:4px;padding:10px 16px;background:#0b111e;border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none;position:sticky;top:58px;z-index:100}
.page-tabs::-webkit-scrollbar{display:none}
.tab-btn{flex:none;padding:6px 18px;border-radius:20px;border:1px solid var(--border2);background:transparent;color:var(--muted);font-size:12px;font-weight:700;cursor:pointer;transition:.15s;letter-spacing:.03em;white-space:nowrap}
.tab-btn.active{background:var(--orange);border-color:var(--orange);color:#fff}
.tab-btn:hover:not(.active){border-color:var(--muted2);color:var(--text)}

/* ── Hidden Gems Page ── */
.gem-header{margin-bottom:16px}
.gem-title{font-size:20px;font-weight:900;margin-bottom:4px}
.gem-sub{font-size:12px;color:var(--muted)}
.gem-filters{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.gf{padding:5px 14px;border-radius:20px;border:1px solid var(--border2);background:transparent;color:var(--muted2);font-size:11px;font-weight:700;cursor:pointer;transition:.15s;white-space:nowrap}
.gf.on{border-color:var(--orange);color:var(--orange);background:rgba(217,119,87,.12)}
.gem-count{font-size:11px;color:var(--muted);margin-bottom:12px}
.gem-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.gem-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;transition:.15s;display:flex;flex-direction:column;gap:6px}
.gem-card:hover{border-color:var(--border2);background:var(--card2);transform:translateY(-1px)}
.gem-top{display:flex;justify-content:space-between;align-items:flex-start}
.gem-ticker{font-size:17px;font-weight:900}
.gem-badge{font-size:10px;padding:3px 9px;border-radius:10px;font-weight:700;white-space:nowrap}
.gem-company{font-size:11px;color:var(--muted2)}
.gem-thesis{font-size:12px;color:var(--muted2);line-height:1.5;flex:1}
.gem-footer{display:flex;align-items:center;justify-content:space-between;margin-top:4px}
.gem-upside{font-size:13px;font-weight:800;color:var(--green)}
.gem-risk{font-size:10px;padding:2px 8px;border-radius:8px;font-weight:700}
.rs{background:rgba(239,68,68,.15);color:#ef4444}
.rg{background:rgba(245,158,11,.15);color:#f59e0b}
.rv{background:rgba(16,185,129,.15);color:#10b981}

/* Top-10 pick button */
.top10-btn{display:inline-flex;align-items:center;gap:6px;margin-top:10px;padding:8px 20px;border-radius:24px;border:none;background:linear-gradient(135deg,#f59e0b,#f97316);color:#fff;font-size:13px;font-weight:800;cursor:pointer;letter-spacing:.03em;box-shadow:0 2px 12px rgba(245,158,11,.35);transition:.2s}
.top10-btn:hover{transform:translateY(-1px);box-shadow:0 4px 18px rgba(245,158,11,.5)}
/* Top-10 panel */
.top10-panel{display:none;margin:18px 0;background:linear-gradient(135deg,rgba(245,158,11,.06),rgba(249,115,22,.04));border:1px solid rgba(245,158,11,.25);border-radius:16px;padding:20px}
.top10-panel.open{display:block}
.top10-title{font-size:16px;font-weight:900;margin-bottom:4px;background:linear-gradient(90deg,#f59e0b,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.top10-sub{font-size:11px;color:var(--muted);margin-bottom:16px}
.top10-list{display:flex;flex-direction:column;gap:10px}
.t10-row{display:grid;grid-template-columns:28px 60px 1fr auto;gap:10px;align-items:start;background:var(--card);border-radius:10px;padding:12px 14px;border:1px solid var(--border)}
.t10-rank{font-size:18px;font-weight:900;color:var(--muted2)}
.t10-sym{font-size:16px;font-weight:900}
.t10-body{}
.t10-company{font-size:11px;color:var(--muted2);margin-bottom:3px}
.t10-reason{font-size:12px;color:var(--muted2);line-height:1.55}
.t10-meta{display:flex;flex-direction:column;align-items:flex-end;gap:4px;white-space:nowrap}
.t10-up{font-size:14px;font-weight:800;color:var(--green)}
.t10-risk{font-size:10px;padding:2px 8px;border-radius:8px;font-weight:700}
.t10-row{cursor:pointer}
.t10-row:hover{border-color:var(--border2);background:var(--card2)}

/* Gem Chart Modal */
#gcOverlay{display:none;position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,.8);backdrop-filter:blur(6px);align-items:flex-end;justify-content:center}
#gcOverlay.open{display:flex}
#gcModal{background:#0d1117;border-radius:20px 20px 0 0;width:100%;max-width:900px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden}
@media(min-width:600px){#gcModal{border-radius:16px;margin:auto;max-height:88vh}}
.gc-header{display:flex;align-items:center;gap:12px;padding:14px 18px;border-bottom:1px solid var(--border);flex-shrink:0}
.gc-info{flex:1;min-width:0}
.gc-ticker{font-size:22px;font-weight:900;letter-spacing:-.02em}
.gc-company{font-size:11px;color:var(--muted2);margin-top:1px}
.gc-links{display:flex;gap:6px;flex-shrink:0}
.gc-link{padding:5px 12px;border-radius:8px;font-size:11px;font-weight:700;text-decoration:none;border:1px solid var(--border2);color:var(--muted2);transition:.15s;white-space:nowrap}
.gc-link:hover{border-color:var(--orange);color:var(--orange)}
.gc-close{width:34px;height:34px;border-radius:50%;border:1px solid var(--border2);background:transparent;color:var(--muted2);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.15s}
.gc-close:hover{background:var(--border);color:var(--text)}
.gc-thesis-bar{padding:9px 18px;font-size:12px;color:var(--muted2);background:var(--card);border-bottom:1px solid var(--border);line-height:1.55;flex-shrink:0}
.gc-meta{display:flex;gap:8px;padding:8px 18px;border-bottom:1px solid var(--border);flex-shrink:0;align-items:center;flex-wrap:wrap}
.gc-up{font-size:13px;font-weight:800;color:var(--green)}
.gc-body{flex:1;overflow:hidden;min-height:0;position:relative}
#gcContainer{width:100%;height:100%;min-height:460px}
.gc-loading{display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);font-size:13px;gap:8px}

/* SP500 Signal badges */
.sig-buy{background:rgba(16,185,129,.15);color:#10b981;font-size:10px;padding:2px 9px;border-radius:8px;font-weight:800}
.sig-hold{background:rgba(245,158,11,.15);color:#f59e0b;font-size:10px;padding:2px 9px;border-radius:8px;font-weight:800}
.sig-watch{background:rgba(99,102,241,.15);color:#8b5cf6;font-size:10px;padding:2px 9px;border-radius:8px;font-weight:800}
/* SP500 card: same as gem-card but with mc field */
.sp-mc{font-size:11px;color:var(--muted);font-weight:600}

.footer{text-align:center;padding:32px 16px 24px;color:var(--muted);font-size:11px}

@media(min-width:600px){
  .overlay{align-items:center}
  .modal{border-radius:20px;max-height:85vh}
  .main{padding:24px}
  .stock-grid{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
}

/* ── Daily Entry Panel ── */
.entry-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;display:grid;grid-template-columns:36px 56px 1fr auto;gap:10px;align-items:start;transition:.15s;cursor:pointer}
.entry-card:hover{border-color:var(--border2);background:var(--card2);transform:translateY(-1px)}
.entry-rank{font-size:22px;font-weight:900;color:var(--muted2);text-align:center;padding-top:2px}
.entry-sym{font-size:18px;font-weight:900;line-height:1.1}
.entry-name{font-size:10px;color:var(--muted);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:160px}
.entry-body{min-width:0}
.entry-reason{font-size:12px;color:var(--muted2);line-height:1.5;margin:4px 0 8px}
.entry-chips{display:flex;gap:6px;flex-wrap:wrap}
.e-chip{background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:6px;padding:3px 8px;font-size:10px;color:var(--muted2);white-space:nowrap}
.e-chip b{color:var(--text)}
.entry-right{display:flex;flex-direction:column;align-items:flex-end;gap:5px;white-space:nowrap}
.entry-score{font-size:11px;font-weight:800;background:rgba(217,119,87,.15);color:var(--orange);border:1px solid rgba(217,119,87,.3);padding:3px 9px;border-radius:10px}
.entry-price{font-size:16px;font-weight:900}
.entry-chg{font-size:12px;font-weight:700}
.entry-list{display:flex;flex-direction:column;gap:10px}
.entry-bar{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:12px}
.eb-item{display:flex;flex-direction:column;gap:2px}
.eb-label{font-size:10px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.eb-val{font-size:15px;font-weight:800}
.entry-tp-row{display:flex;gap:8px;margin-top:4px}
.etp{font-size:11px;padding:2px 7px;border-radius:6px;font-weight:700}
.etp-entry{background:rgba(59,130,246,.15);color:#60a5fa}
.etp-sl{background:rgba(239,68,68,.12);color:#f87171}
.etp-tp{background:rgba(16,185,129,.12);color:#34d399}
.etp-rr{background:rgba(245,158,11,.12);color:#f59e0b}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-left">
    <div class="logo">C</div>
    <div><div class="hdr-title">Claude AI Agent</div><div class="hdr-sub">Daily Stock Analysis</div></div>
  </div>
  <div class="date-pill" id="datePill"></div>
</header>

<div class="ticker" id="ticker"></div>

<div class="page-tabs" id="pageTabs">
  <button class="tab-btn active" onclick="showPage('signals',this)">&#x1F4C8; Signals</button>
  <button class="tab-btn" onclick="showPage('entry',this)">&#x1F4C5; Daily Entry</button>
  <button class="tab-btn" onclick="showPage('vault',this)">&#x1F3DB; คลังหุ้น 500+</button>
  <button class="tab-btn" onclick="showPage('gems',this)">&#x1F48E; Hidden Gems 100</button>
  <button class="tab-btn" onclick="showPage('sp500',this)">&#x1F4CA; S&amp;P 500</button>
  <button class="tab-btn" onclick="showPage('tracker',this)">&#x1F3AF; Tracker</button>
  <button class="tab-btn" onclick="showPage('options',this)">&#x1F4C3; Options</button>
</div>

<div id="page-signals">
<div class="main">
  <div class="sec-title">Market Sentiment</div>
  <div class="mood-card" id="moodCard"></div>
  <div class="index-row" id="indexRow" style="margin-top:10px"></div>

  <div id="macroPanel" style="display:none;margin-top:16px">
    <div class="sec-title">&#x1F3DB; FRED Macro Environment</div>
    <div id="macroGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:8px"></div>
    <div id="macroRegime" style="font-size:12px;color:var(--muted2);padding:8px 12px;background:var(--card);border-radius:8px;border:1px solid var(--border)"></div>
  </div>

  <div id="commoditySection" style="display:none">
    <div class="sec-title">Commodities &amp; Crypto</div>
    <div class="comm-grid" id="commGrid"></div>
  </div>

  <div class="sec-title" id="buyTitle"></div>
  <div class="stock-grid" id="buyGrid"></div>

  <div class="sec-title" id="watchTitle"></div>
  <div class="stock-grid" id="watchGrid"></div>

  <div class="sec-title" id="waitTitle"></div>
  <div class="stock-grid" id="waitGrid"></div>

  <div class="sec-title" id="avoidTitle"></div>
  <div class="stock-grid" id="avoidGrid"></div>
</div>

</div><!-- /page-signals -->

<div id="page-gems" style="display:none">
<div class="main">
  <div class="gem-header">
    <div class="gem-title">&#x1F48E; Hidden Gems — 100 หุ้นนอกกระแส 2026</div>
    <div class="gem-sub">รวบรวมจาก Insider Monkey · Barchart · Tickeron · Morningstar · Yahoo Finance — อัพเดต Jun 2026</div>
    <button class="top10-btn" onclick="toggleTop10()">&#x1F3C6; เลือก 10 หุ้นน่าซื้อ</button>
  </div>
  <div class="top10-panel" id="top10Panel">
    <div class="top10-title">&#x1F3C6; Top 10 หุ้นน่าซื้อตอนนี้</div>
    <div class="top10-sub">คัดจาก 96 ตัว — สมดุลระหว่าง Upside, Risk, และ Diversification</div>
    <div class="top10-list" id="top10List"></div>
  </div>
  <div class="gem-filters" id="gemFilters"></div>
  <div class="gem-count" id="gemCount"></div>
  <div class="gem-grid" id="gemGrid"></div>
</div>
</div><!-- /page-gems -->

<div id="page-sp500" style="display:none">
<div class="main">
  <div class="gem-header">
    <div class="gem-title">&#x1F4CA; S&amp;P 500 — หุ้นเกรด A คัดสรร 120 ตัว</div>
    <div class="gem-sub">ครอบคลุม 11 Sectors · คลิกการ์ดเพื่อดูกราฟ · สัญญาณ: <span class="sig-buy">BUY</span> <span class="sig-hold">HOLD</span> <span class="sig-watch">WATCH</span></div>
  </div>
  <div class="gem-filters" id="spFilters"></div>
  <div class="gem-count" id="spCount"></div>
  <div class="gem-grid" id="spGrid"></div>
</div>
</div><!-- /page-sp500 -->

<div id="page-entry" style="display:none">
<div class="main">
  <div class="gem-header">
    <div class="gem-title">&#x1F4C5; Daily Entry Points</div>
    <div class="gem-sub">หุ้น BUY/WATCH ที่คะแนนสูงที่สุดวันนี้ — เรียงตาม RSI, Stars, Support, R:R, Analyst</div>
  </div>
  <div id="entrySummaryBar" class="entry-bar" style="display:none"></div>
  <div class="gem-count" id="entryCount"></div>
  <div class="entry-list" id="entryGrid"></div>
</div>
</div><!-- /page-entry -->

<div id="page-tracker" style="display:none">
<div class="main">
  <div class="gem-header">
    <div class="gem-title">&#x1F3AF; Paper Trade Tracker — วัดความแม่น ArtheeNoi</div>
    <div class="gem-sub">Paper Portfolio เงินทุน 10,000฿ · ถือ 10 วัน · BUY เท่านั้น · vs QQQ benchmark</div>
  </div>
  <div id="trackerBody"></div>
</div>
</div><!-- /page-tracker -->

<div id="page-options" style="display:none">
<div class="main">
  <div class="gem-header">
    <div class="gem-title">&#x1F4C3; Paper Trade Options — Call/Put Simulator</div>
    <div class="gem-sub">ทุน 10,000฿ แยกจาก Stock · Auto-buy Call เมื่อ ArtheeNoi BUY (AI Score ≥65) · Stop Loss 50% / Take Profit 100%</div>
  </div>
  <div id="optionsBody"></div>
</div>
</div><!-- /page-options -->

<div id="page-vault" style="display:none">
<div class="main">
  <div class="gem-header">
    <h2 style="margin:0">&#x1F3DB; คลังหุ้น — ArtheeNoi Picks</h2>
    <p id="vaultSubtitle" style="margin:4px 0 0;opacity:.7;font-size:.85em"></p>
  </div>
  <div id="vaultPicksGrid" style="margin-bottom:32px"></div>
  <hr style="border-color:#333;margin:16px 0">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap">
    <h3 style="margin:0;font-size:1em;opacity:.8">คลังทั้งหมด</h3>
    <input id="vaultSearch" placeholder="ค้นหา ticker / บริษัท / sector..." oninput="filterVault()" style="background:#222;border:1px solid #444;color:#eee;padding:6px 10px;border-radius:6px;font-size:.85em;width:220px">
    <select id="vaultSector" onchange="filterVault()" style="background:#222;border:1px solid #444;color:#eee;padding:6px 8px;border-radius:6px;font-size:.85em">
      <option value="">ทุก Sector</option>
    </select>
    <select id="vaultTier" onchange="filterVault()" style="background:#222;border:1px solid #444;color:#eee;padding:6px 8px;border-radius:6px;font-size:.85em">
      <option value="">ทุก Tier</option>
      <option value="1">Tier 1 — Blue Chip</option>
      <option value="2">Tier 2 — Growth</option>
      <option value="3">Tier 3 — Speculative</option>
    </select>
    <span id="vaultCount" style="opacity:.5;font-size:.8em"></span>
  </div>
  <div id="vaultAllTable"></div>
</div>
</div><!-- /page-vault -->

<footer class="footer" id="footerBar">Claude AI Agent &mdash; Daily analysis &mdash; Data: Yahoo Finance &mdash; Not financial advice</footer>

<!-- Gem Chart Modal -->
<div id="gcOverlay" onclick="gcBgClick(event)">
  <div id="gcModal">
    <div class="gc-header">
      <div class="gc-info">
        <div class="gc-ticker" id="gcTicker"></div>
        <div class="gc-company" id="gcCompany"></div>
      </div>
      <div class="gc-links">
        <a class="gc-link" id="gcYfLink" href="#" target="_blank" rel="noopener noreferrer">&#x1F4CA; Yahoo Finance</a>
        <a class="gc-link" id="gcTvLink" href="#" target="_blank" rel="noopener noreferrer">&#x1F4C8; TradingView</a>
      </div>
      <button class="gc-close" onclick="closeGemChart()">&#x2715;</button>
    </div>
    <div class="gc-meta">
      <span class="gc-up" id="gcUpside"></span>
      <span class="gem-risk" id="gcRisk"></span>
      <span class="gem-badge" id="gcTheme"></span>
    </div>
    <div class="gc-thesis-bar" id="gcThesis"></div>
    <div class="gc-body">
      <div id="gcContainer"><div class="gc-loading">&#x23F3; กำลังโหลดกราฟ...</div></div>
    </div>
  </div>
</div>

<!-- Modal -->
<div class="overlay" id="overlay" onclick="closeIfBg(event)">
  <div class="modal" id="modal">
    <div class="modal-drag"></div>
    <button class="modal-close" onclick="closeModal()">&#x2715;</button>
    <div class="modal-header">
      <div>
        <div class="modal-sym" id="mSym"></div>
        <div class="modal-name" id="mName"></div>
      </div>
      <div class="modal-price-wrap">
        <div class="modal-price" id="mPrice"></div>
        <div class="modal-chg" id="mChg"></div>
      </div>
    </div>

    <!-- Action badge -->
    <div style="padding:0 20px 10px" id="mBadgeWrap"></div>

    <!-- Chart -->
    <div class="chart-area">
      <div class="chart-period">
        <button class="period-btn active" onclick="setPeriod(30,this)">1M</button>
        <button class="period-btn" onclick="setPeriod(14,this)">2W</button>
        <button class="period-btn" onclick="setPeriod(7,this)">1W</button>
      </div>
      <div class="chart-box"><canvas id="priceChart"></canvas></div>
    </div>

    <!-- Stats -->
    <div class="modal-stats">
      <div class="ms"><div class="ms-label">RSI-14</div><div class="ms-val" id="mRsi"></div></div>
      <div class="ms"><div class="ms-label">P/E (TTM)</div><div class="ms-val" id="mPE"></div></div>
      <div class="ms"><div class="ms-label">Forward P/E</div><div class="ms-val" id="mFwdPE"></div></div>
      <div class="ms"><div class="ms-label">Market Cap</div><div class="ms-val" id="mMC"></div></div>
      <div class="ms"><div class="ms-label">Beta</div><div class="ms-val" id="mBeta"></div></div>
      <div class="ms"><div class="ms-label">Volume</div><div class="ms-val neu" id="mVol"></div></div>
      <div class="ms"><div class="ms-label">52W High</div><div class="ms-val neu" id="mH52"></div></div>
      <div class="ms"><div class="ms-label">52W Low</div><div class="ms-val neu" id="mL52"></div></div>
      <div class="ms ms-target" id="mTargetBox" style="display:none"><div class="ms-label">Analyst Target</div><div class="ms-val" id="mTarget"></div></div>
    </div>

    <!-- Entry/SL/TP -->
    <div style="padding:0 20px 10px"><div class="modal-action" id="mAction"></div></div>

    <!-- Reason -->
    <div class="modal-reason" id="mReason"></div>

    <!-- Analyst Consensus -->
    <div class="fin-section" id="recoSection" style="display:none">
      <div class="fin-title">Analyst Consensus</div>
      <div class="reco-bar" id="recoBar"></div>
      <div class="reco-labels"><span id="recoLeft"></span><span id="recoRight"></span></div>
      <div class="reco-counts" id="recoPills"></div>
    </div>

    <!-- Financials -->
    <div class="fin-section" id="finSection" style="display:none">
      <div class="fin-title">Financials (TTM)</div>
      <div class="fin-grid" id="finGrid"></div>
      <div class="ma-row" id="maRow" style="margin-top:6px"></div>
    </div>

    <!-- Recent News -->
    <div class="fin-section" id="newsSection" style="display:none">
      <div class="fin-title">Recent News</div>
      <div id="newsList"></div>
    </div>

    <div class="modal-footer-pad"></div>
  </div>
</div>

<script>
const D = __DATA__;

// helpers
const fUSD = n => n == null ? '-' : '$' + Math.abs(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const fPct = n => (n >= 0 ? '+' : '') + (n||0).toFixed(2) + '%';
const cls  = n => n > 0 ? 'pos' : n < 0 ? 'neg' : 'neu';
function rsiColor(r){ if(!r)return'#64748b'; if(r>=70)return'#ef4444'; if(r<=30)return'#3b82f6'; if(r>=55)return'#f59e0b'; if(r<=45)return'#10b981'; return'#94a3b8'; }

// ── Header + Live Countdown ──
(function() {
  const interval = (D.next_update || 0) * 60; // seconds, 0 = no auto-updater running
  const pill = document.getElementById('datePill');

  function setLabel(secsLeft) {
    const base = D.date + '  ' + D.updated_at;
    if (!interval) { pill.textContent = base; return; }
    const m = Math.floor(secsLeft / 60);
    const s = String(secsLeft % 60).padStart(2, '0');
    const color = secsLeft <= 30 ? '#4ade80' : '#facc15';
    pill.innerHTML = base
      + ` <span style="font-size:.75em;margin-left:10px;color:${color}">&#x25CF; LIVE อัปเดตใน ${m}:${s}</span>`;
  }

  if (interval > 0) {
    let remaining = interval;
    setLabel(remaining);
    const t = setInterval(() => {
      remaining--;
      if (remaining <= 0) {
        pill.innerHTML = D.date + '  ' + D.updated_at
          + ' <span style="font-size:.75em;margin-left:10px;color:#4ade80">&#x25CF; กำลังโหลด...</span>';
        clearInterval(t);
        location.reload();
      } else {
        setLabel(remaining);
      }
    }, 1000);
  } else {
    pill.textContent = D.date + '  ' + D.updated_at;
  }
})();
if (D.thb_rate) {
  document.getElementById('footerBar').textContent =
    'Claude AI Agent — Data: Yahoo Finance — USD/THB ' + D.thb_rate.toFixed(4) + ' (live) — Not financial advice';
}

// ── Ticker ──
const tk = document.getElementById('ticker');
D.tickers.forEach(t => {
  const c = (t.chg||0) >= 0 ? 'pos' : 'neg';
  tk.innerHTML += `<div class="ti"><span class="ti-sym">${t.sym}</span><span class="ti-price">${fUSD(t.price)}</span><span class="ti-chg ${c}">${fPct(t.chg)}</span></div>`;
});

// ── Mood ──
const m = D.market;
const mc = document.getElementById('moodCard');
mc.style.background = m.color + '18';
mc.style.border = '1px solid ' + m.color + '40';
mc.innerHTML = `<div class="mood-title" style="color:${m.color}">${m.icon=='BULL'?'BULLISH':m.icon=='BEAR'?'BEARISH':'SIDEWAYS'} — ${m.mood}</div><div class="mood-note">${m.note}</div>`;

// ── Index Row ──
const ir = document.getElementById('indexRow');
D.indices.forEach(i => {
  const c = (i.chg||0) >= 0 ? 'pos' : 'neg';
  ir.innerHTML += `<div class="idx-card"><div class="idx-sym">${i.sym}</div><div class="idx-price">${fUSD(i.price)}</div><div class="idx-chg ${c}">${fPct(i.chg)}</div></div>`;
});

// ── FRED Macro Panel ──
(function(){
  const mac = D.macro || {};
  if (!mac.regime) return;
  document.getElementById('macroPanel').style.display = '';
  const ITEMS = [
    { label:'Fed Rate',    val: mac.fed_rate    != null ? mac.fed_rate.toFixed(2)+'%' : '?' },
    { label:'Yield Curve', val: mac.yield_curve != null ? mac.yield_curve.toFixed(2)+'%' : '?',
      color: (mac.yield_curve||0) < 0 ? '#ef4444' : '#10b981' },
    { label:'CPI (YoY)',   val: mac.cpi         != null ? mac.cpi.toFixed(1)+'%' : '?' },
    { label:'Unemploymt',  val: mac.unrate      != null ? mac.unrate.toFixed(1)+'%' : '?' },
    { label:'VIX',         val: mac.vix         != null ? mac.vix.toFixed(1) : '?',
      color: (mac.vix||0) > 25 ? '#ef4444' : (mac.vix||0) > 18 ? '#f59e0b' : '#10b981' },
    { label:'DXY',         val: mac.dxy         != null ? mac.dxy.toFixed(1) : '?' },
    { label:'Oil (WTI)',   val: mac.oil         != null ? '$'+mac.oil.toFixed(1) : '?' },
    { label:'10Y Yield',   val: mac.tnx         != null ? mac.tnx.toFixed(2)+'%' : '?' },
  ];
  const grid = document.getElementById('macroGrid');
  ITEMS.forEach(it => {
    const col = it.color || '#94a3b8';
    grid.innerHTML += `<div style="background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px">
      <div style="font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.05em">${it.label}</div>
      <div style="font-size:16px;font-weight:800;margin-top:4px;color:${col}">${it.val}</div>
    </div>`;
  });
  const REGIME_LABELS = {
    expansion:      '📈 Expansion — risk-on, growth favored',
    mid_cycle:      '📊 Mid-cycle — balanced, sector rotation',
    recession_risk: '⚠️ Recession Risk — defensive positioning',
    crisis:         '🚨 Crisis — max defense, cash is king',
    overheating:    '🔥 Overheating — commodities, reduce growth',
  };
  const RATE_LABELS = {
    high_rate:   '🔺 High Rate env — banks ok, Biotech/REIT pressured',
    low_rate:    '🔻 Low Rate env — growth/tech/REIT favored',
    normal_rate: '⚖️ Normal Rate — neutral sector impact',
  };
  const rLabel = REGIME_LABELS[mac.regime] || mac.regime;
  const eLabel = RATE_LABELS[mac.rate_env] || mac.rate_env || '';
  const riskCl = mac.risk_level === 'high_risk' ? '#ef4444' : mac.risk_level === 'low_risk' ? '#10b981' : '#94a3b8';
  document.getElementById('macroRegime').innerHTML =
    `<b style="color:#d97757">Regime:</b> ${rLabel} &nbsp;|&nbsp; ${eLabel} &nbsp;|&nbsp; <span style="color:${riskCl}">Risk: ${mac.risk_level||'?'}</span>`;
})();

// ── Sparkline ──
const sparkCharts = {};
function drawSpark(canvasId, closes, positive) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || !closes || closes.length < 2) return;
  const color = positive ? '#10b981' : '#ef4444';
  sparkCharts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: closes.map((_,i) => i),
      datasets: [{ data: closes, borderColor: color, borderWidth: 2, pointRadius: 0,
        fill: true, backgroundColor: ctx2 => {
          const g = ctx2.chart.ctx.createLinearGradient(0,0,0,40);
          g.addColorStop(0, color+'40'); g.addColorStop(1, color+'00'); return g;
        }
      }]
    },
    options: { animation:false, responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{x:{display:false},y:{display:false}} }
  });
}

// ── Stock Card ──
let cardIdx = 0;
function stockCard(s) {
  const act  = s.action;
  const cls2 = act.toLowerCase();
  const dc   = (s.chg||0) >= 0 ? 'pos' : 'neg';
  const rsi  = s.rsi;
  const rsiW = Math.min(rsi||0,100);
  const sparkId = 'spark_' + (cardIdx++);
  const stars = act === 'BUY' ? '&#9733;'.repeat(s.stars||1) + '&#9734;'.repeat(3-(s.stars||1)) : '';
  const positive = (s.closes30 && s.closes30.length >= 2)
    ? s.closes30[s.closes30.length-1] >= s.closes30[0] : (s.chg||0) >= 0;

  setTimeout(() => drawSpark(sparkId, s.closes30 || [], positive), 50);

  const aiScore = s.ai_score != null ? Math.round(s.ai_score) : null;
  const aiCol   = aiScore == null ? '#64748b' : aiScore >= 70 ? '#10b981' : aiScore >= 50 ? '#f59e0b' : '#ef4444';
  const aiLabel = aiScore == null ? '' :
    `<span title="AI Score: Technical+Fundamental+Macro+Sentiment" style="margin-left:6px;font-size:10px;font-weight:800;color:${aiCol};background:${aiCol}18;border:1px solid ${aiCol}40;border-radius:10px;padding:2px 7px">AI ${aiScore}</span>`;

  return `<div class="sc ${cls2}" onclick="openModal('${s.sym}')">
    <div class="sc-top">
      <div><div class="sc-sym">${s.sym}</div><div class="sc-name">${s.name||''}</div></div>
      <div class="sc-price-wrap"><div class="sc-price">${fUSD(s.price)}</div><div class="sc-chg ${dc}">${fPct(s.chg)}</div></div>
    </div>
    <div class="spark-wrap"><canvas id="${sparkId}" height="40"></canvas></div>
    <div style="margin-bottom:6px">
      <span class="action-badge ab-${act}">${act==='BUY'?'BUY NOW':act==='WATCH'?'WATCH':act==='WAIT'?'WAIT':act==='AVOID'?'AVOID':'NEUTRAL'}</span>
      ${stars ? `<span class="stars">${stars}</span>` : ''}${aiLabel}
    </div>
    <div class="sc-reason">${s.reason}</div>
    <div class="rsi-row">
      <span class="rsi-label">RSI</span>
      <div class="rsi-track"><div class="rsi-fill" style="width:${rsiW}%;background:${rsiColor(rsi)}"></div></div>
      <span class="rsi-val" style="color:${rsiColor(rsi)}">${rsi||'?'}</span>
    </div>
    <div class="sc-meta">
      ${s.pe_ratio   ? `<span class="meta-chip">P/E <b>${s.pe_ratio.toFixed(1)}</b></span>` : ''}
      ${s.forward_pe ? `<span class="meta-chip">Fwd <b>${s.forward_pe.toFixed(1)}</b></span>` : ''}
      ${s.market_cap ? `<span class="meta-chip">MC <b>$${s.market_cap>=1e12?(s.market_cap/1e12).toFixed(2)+'T':s.market_cap>=1e9?(s.market_cap/1e9).toFixed(0)+'B':(s.market_cap/1e6).toFixed(0)+'M'}</b></span>` : ''}
      ${s.beta       ? `<span class="meta-chip">β <b>${s.beta.toFixed(2)}</b></span>` : ''}
      ${s.rs_sector != null ? (() => { const v=s.rs_sector; const c=v>=5?'#10b981':v>=0?'#94a3b8':'#ef4444'; const sign=v>=0?'+':''; return `<span class="meta-chip" title="Relative Strength vs ${s.rs_etf||'sector'} (20-day outperformance pp)">RS <b style="color:${c}">${sign}${v.toFixed(1)}</b></span>`; })() : ''}
      ${s.short_float != null ? `<span class="meta-chip" title="Short Float %">Short <b>${s.short_float.toFixed(1)}%</b></span>` : ''}
    </div>
    <div class="tap-hint">Tap for chart &rsaquo;</div>
  </div>`;
}

// ── Section Renderer ──
function renderSection(titleEl, gridEl, stocks, label, emptyMsg) {
  titleEl.textContent = label + (stocks.length ? ` (${stocks.length})` : '');
  gridEl.innerHTML = !stocks.length
    ? `<p style="color:var(--muted);font-size:13px;padding:4px 0">${emptyMsg}</p>`
    : stocks.map(stockCard).join('');
}

// ── Commodities & Crypto ──
const commStocks = D.stocks.filter(s => s.category);
const cSec = document.getElementById('commoditySection');
if (commStocks.length) {
  const cGrid = document.getElementById('commGrid');
  cGrid.innerHTML = commStocks.map(c => {
    const isGold = c.category === 'gold';
    const accent = isGold ? '#f59e0b' : '#f97316';
    const icon   = isGold ? '\u{1F947}' : '₿';
    const dc     = (c.chg||0) >= 0 ? 'pos' : 'neg';
    const rsiW   = Math.min(c.rsi||0, 100);
    const rsiC   = rsiColor(c.rsi);
    const priceStr = !isGold && c.price > 1000
      ? '$' + Math.round(c.price).toLocaleString('en-US')
      : fUSD(c.price);
    const rangeStr = (c.high_52w && c.low_52w)
      ? `52W  $${Math.round(c.low_52w).toLocaleString()} – $${Math.round(c.high_52w).toLocaleString()}`
      : '';
    return `<div class="comm-card" onclick="openModal('${c.sym}')" style="border-color:${accent}50">
      <div class="comm-top">
        <div>
          <div class="comm-sym" style="color:${accent}">${c.name}</div>
          <div class="comm-name">${isGold ? 'XAU/USD · COMEX' : 'BTC/USD · Crypto'}</div>
        </div>
        <div class="comm-icon">${icon}</div>
      </div>
      <div class="comm-price">${priceStr}</div>
      <div class="comm-chg ${dc}">${fPct(c.chg)} today</div>
      <div class="rsi-row" style="margin-top:8px">
        <span class="rsi-label">RSI</span>
        <div class="rsi-track"><div class="rsi-fill" style="width:${rsiW}%;background:${rsiC}"></div></div>
        <span class="rsi-val" style="color:${rsiC}">${c.rsi||'?'}</span>
      </div>
      ${rangeStr ? `<div class="comm-range">${rangeStr}</div>` : ''}
    </div>`;
  }).join('');
  cSec.style.display = '';
}

const regStocks = D.stocks.filter(s => !s.category);
const buy   = regStocks.filter(s => s.action==='BUY').sort((a,b)=>b.stars-a.stars);
const watch = regStocks.filter(s => s.action==='WATCH');
const wait  = regStocks.filter(s => s.action==='WAIT'||s.action==='NEUTRAL');
const avoid = regStocks.filter(s => s.action==='AVOID');

renderSection(document.getElementById('buyTitle'),   document.getElementById('buyGrid'),   buy,   'BUY NOW',        'No clear buy signals today. Be patient.');
renderSection(document.getElementById('watchTitle'), document.getElementById('watchGrid'), watch, 'WORTH WATCHING', 'Nothing approaching entry zone yet.');
renderSection(document.getElementById('waitTitle'),  document.getElementById('waitGrid'),  wait,  'WAIT / NEUTRAL', 'All stocks have signals.');
renderSection(document.getElementById('avoidTitle'), document.getElementById('avoidGrid'), avoid, 'AVOID TODAY',    'No overbought stocks right now.');

// ── Modal ──
let modalChart = null;
let currentStock = null;

function openModal(sym) {
  const s = D.stocks.find(x => x.sym === sym);
  if (!s) return;
  currentStock = s;

  document.getElementById('mSym').textContent   = s.sym;
  document.getElementById('mName').textContent  = s.name || '';
  document.getElementById('mPrice').textContent = fUSD(s.price);

  const dc = (s.chg||0) >= 0 ? 'pos' : 'neg';
  document.getElementById('mChg').className   = 'modal-chg ' + dc;
  document.getElementById('mChg').textContent = fPct(s.chg) + ' today';

  // Badge
  const act = s.action;
  const stars = act==='BUY' ? '&#9733;'.repeat(s.stars||1)+'&#9734;'.repeat(3-(s.stars||1)) : '';
  document.getElementById('mBadgeWrap').innerHTML =
    `<span class="action-badge ab-${act}">${act==='BUY'?'BUY NOW':act==='WATCH'?'WATCH':act==='WAIT'?'WAIT':act==='AVOID'?'AVOID':'NEUTRAL'}</span>${stars?`<span class="stars" style="margin-left:8px">${stars}</span>`:''}`;

  // Stats
  const fMC  = n => !n ? '-' : n >= 1e12 ? '$'+(n/1e12).toFixed(2)+'T' : n >= 1e9 ? '$'+(n/1e9).toFixed(0)+'B' : '$'+(n/1e6).toFixed(0)+'M';
  const fVol = n => !n ? '-' : n >= 1e6 ? (n/1e6).toFixed(1)+'M' : n >= 1e3 ? (n/1e3).toFixed(0)+'K' : n;
  document.getElementById('mRsi').innerHTML   = `<span style="color:${rsiColor(s.rsi)}">${s.rsi||'-'}</span>`;
  document.getElementById('mPE').innerHTML    = s.pe_ratio   ? `<span style="color:var(--yellow)">${s.pe_ratio.toFixed(1)}x</span>`  : '<span style="color:var(--muted)">N/A</span>';
  document.getElementById('mFwdPE').innerHTML = s.forward_pe ? `<span style="color:var(--green)">${s.forward_pe.toFixed(1)}x</span>` : '<span style="color:var(--muted)">N/A</span>';
  document.getElementById('mMC').textContent  = fMC(s.market_cap);
  document.getElementById('mBeta').innerHTML  = s.beta ? `<span style="color:${s.beta>1.5?'var(--red)':s.beta<0.8?'var(--green)':'var(--yellow)'}">&#x3B2; ${s.beta.toFixed(2)}</span>` : '<span style="color:var(--muted)">N/A</span>';
  document.getElementById('mVol').textContent = fVol(s.volume);
  document.getElementById('mH52').textContent = fUSD(s.high_52w);
  document.getElementById('mL52').textContent = fUSD(s.low_52w);

  // Analyst target box
  const tBox = document.getElementById('mTargetBox');
  if (s.analyst_target && s.price) {
    const upside = ((s.analyst_target - s.price) / s.price * 100).toFixed(1);
    const uColor = upside > 0 ? 'var(--green)' : 'var(--red)';
    document.getElementById('mTarget').innerHTML =
      `<span style="color:var(--text)">${fUSD(s.analyst_target)}</span> <span style="font-size:12px;color:${uColor}">${upside>0?'+':''}${upside}%</span>`;
    tBox.style.display = '';
  } else {
    tBox.style.display = 'none';
  }

  // Entry table
  const rrColor = s.rr >= 2 ? '#10b981' : s.rr >= 1.5 ? '#f59e0b' : '#94a3b8';
  if (act === 'BUY' || act === 'WATCH') {
    document.getElementById('mAction').innerHTML = `
      <div class="action-row"><span class="ar-label">Entry Price</span><span class="ar-val pos">${fUSD(s.entry)}</span></div>
      <div class="action-row"><span class="ar-label">Stop Loss</span><span class="ar-val neg">${fUSD(s.sl)} &nbsp;<span style="color:var(--muted);font-size:11px">(-8%)</span></span></div>
      <div class="action-row"><span class="ar-label">Target</span><span class="ar-val" style="color:#34d399">${fUSD(s.tp)} &nbsp;<span style="color:var(--muted);font-size:11px">(+18%)</span></span></div>
      <div class="action-row"><span class="ar-label">Risk/Reward</span><span class="ar-val" style="color:${rrColor}">${s.rr}:1 &nbsp;<span style="color:var(--muted);font-size:11px">${s.rr>=2?'Good':'Acceptable'}</span></span></div>`;
  } else {
    document.getElementById('mAction').innerHTML = `
      <div class="action-row"><span class="ar-label">Action</span><span class="ar-val neu">${act === 'AVOID' ? 'Do not buy — wait for RSI to cool' : act === 'WAIT' ? 'Not ideal entry — wait for better RSI' : 'Hold existing positions'}</span></div>`;
  }

  document.getElementById('mReason').textContent = s.reason;

  // ── Analyst Consensus ──
  const rSec = document.getElementById('recoSection');
  if (s.total_analysts && s.total_analysts > 0) {
    const tot = s.total_analysts;
    const sb = s.strong_buy||0, b = s.buy||0, h = s.hold||0, se = s.sell||0, ss = s.strong_sell||0;
    const pct = n => (n/tot*100).toFixed(1)+'%';
    document.getElementById('recoBar').innerHTML =
      `<div class="reco-sb" style="width:${pct(sb)}"></div>` +
      `<div class="reco-b"  style="width:${pct(b)}"></div>` +
      `<div class="reco-h"  style="width:${pct(h)}"></div>` +
      `<div class="reco-s"  style="width:${pct(se)}"></div>` +
      `<div class="reco-ss" style="width:${pct(ss)}"></div>`;
    const bull = sb+b, bear = se+ss;
    document.getElementById('recoLeft').textContent  = `${bull} Buy (${(bull/tot*100).toFixed(0)}%)`;
    document.getElementById('recoRight').textContent = `${bear} Sell · ${h} Hold · ${tot} analysts`;
    document.getElementById('recoPills').innerHTML =
      (sb ? `<span class="reco-pill sb">⬆ Strong Buy ${sb}</span>` : '') +
      (b  ? `<span class="reco-pill b">↑ Buy ${b}</span>` : '') +
      (h  ? `<span class="reco-pill h">— Hold ${h}</span>` : '') +
      (se ? `<span class="reco-pill s">↓ Sell ${se}</span>` : '') +
      (ss ? `<span class="reco-pill ss">⬇ Strong Sell ${ss}</span>` : '');
    rSec.style.display = '';
  } else { rSec.style.display = 'none'; }

  // ── Financials ──
  const fSec = document.getElementById('finSection');
  const fMC2 = n => !n ? null : n>=1e12 ? '$'+(n/1e12).toFixed(2)+'T' : n>=1e9 ? '$'+(n/1e9).toFixed(1)+'B' : '$'+(n/1e6).toFixed(0)+'M';
  const fPct2 = n => n==null ? null : (n>0?'+':'')+n.toFixed(1)+'%';
  const finItems = [
    { label:'Revenue TTM',   val: fMC2(s.revenue_ttm),   sub: s.revenue_growth!=null ? `YoY ${fPct2(s.revenue_growth)}` : null, color: s.revenue_growth>20?'var(--green)':null },
    { label:'Net Income TTM',val: fMC2(s.net_income_ttm), sub: null },
    { label:'EPS (Diluted)', val: s.eps_ttm ? '$'+s.eps_ttm.toFixed(2) : null, sub: s.eps_growth!=null ? `YoY ${fPct2(s.eps_growth)}` : null, color: s.eps_growth>20?'var(--green)':null },
    { label:'Free Cash Flow',val: fMC2(s.free_cash_flow), sub: null },
    { label:'Profit Margin', val: s.profit_margin!=null ? s.profit_margin.toFixed(1)+'%' : null, sub: s.operating_margin!=null ? 'Op '+s.operating_margin.toFixed(1)+'%' : null, color: s.profit_margin>30?'var(--green)':s.profit_margin<10?'var(--red)':null },
    { label:'ROE',           val: s.roe!=null ? s.roe.toFixed(1)+'%' : null, sub: null, color: s.roe>20?'var(--green)':null },
  ].filter(i => i.val);
  if (finItems.length) {
    document.getElementById('finGrid').innerHTML = finItems.map(i =>
      `<div class="fin-item"><div class="fin-label">${i.label}</div>` +
      `<div class="fin-val" style="${i.color?'color:'+i.color:''}">${i.val}</div>` +
      (i.sub ? `<div class="fin-sub">${i.sub}</div>` : '') + `</div>`
    ).join('');
    const maHtml = (s.ma50||s.ma200) ?
      `${s.ma50  ? `<div class="ma-item"><div class="ma-label">MA 50</div><div class="ma-val" style="color:${(s.price||0)>s.ma50?'var(--green)':'var(--red)'}">$${s.ma50.toFixed(2)}</div></div>` : ''}` +
      `${s.ma200 ? `<div class="ma-item"><div class="ma-label">MA 200</div><div class="ma-val" style="color:${(s.price||0)>s.ma200?'var(--green)':'var(--red)'}">$${s.ma200.toFixed(2)}</div></div>` : ''}` : '';
    document.getElementById('maRow').innerHTML = maHtml;
    fSec.style.display = '';
  } else { fSec.style.display = 'none'; }

  // ── Recent News ──
  const nSec = document.getElementById('newsSection');
  if (s.news && s.news.length) {
    document.getElementById('newsList').innerHTML = s.news.map(n =>
      `<a class="news-item" href="${n.url}" target="_blank" rel="noopener noreferrer">` +
      `<div class="news-title">${n.title}</div>` +
      `<div class="news-date">${n.date}</div></a>`
    ).join('');
    nSec.style.display = '';
  } else { nSec.style.display = 'none'; }

  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';

  // Draw chart
  setPeriod(30, document.querySelector('.period-btn.active'));
}

function setPeriod(days, btn) {
  document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  if (!currentStock) return;
  const s = currentStock;
  const closes = (s.closes30 || []).slice(-days);
  const dates  = (s.dates30  || []).slice(-days);

  if (modalChart) { modalChart.destroy(); modalChart = null; }

  const positive = closes.length >= 2 && closes[closes.length-1] >= closes[0];
  const color    = positive ? '#10b981' : '#ef4444';
  const ctx      = document.getElementById('priceChart').getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 200);
  grad.addColorStop(0, color + '50');
  grad.addColorStop(1, color + '00');

  modalChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates.length ? dates : closes.map((_,i)=>i),
      datasets: [{
        data: closes, borderColor: color, borderWidth: 2.5,
        pointRadius: 0, pointHoverRadius: 5,
        pointHoverBackgroundColor: color,
        fill: true, backgroundColor: grad, tension: 0.35
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a2536', borderColor: '#2a3a50', borderWidth: 1,
          titleColor: '#94a3b8', bodyColor: '#e2e8f0', padding: 10,
          callbacks: { label: ctx => ' $' + ctx.raw.toFixed(2) }
        }
      },
      scales: {
        x: { grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#64748b',font:{size:10}, maxTicksLimit:6} },
        y: { grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#64748b',font:{size:10},callback:v=>'$'+v.toFixed(0)}, position:'right' }
      }
    }
  });
}

// ── Page Navigation ──
function showPage(page, btn) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  document.getElementById('page-signals').style.display  = page === 'signals'  ? '' : 'none';
  document.getElementById('page-gems').style.display     = page === 'gems'     ? '' : 'none';
  document.getElementById('page-sp500').style.display    = page === 'sp500'    ? '' : 'none';
  document.getElementById('page-entry').style.display    = page === 'entry'    ? '' : 'none';
  document.getElementById('page-vault').style.display    = page === 'vault'    ? '' : 'none';
  document.getElementById('page-tracker').style.display  = page === 'tracker'  ? '' : 'none';
  document.getElementById('page-options').style.display  = page === 'options'  ? '' : 'none';
  if (page === 'gems'    && !document.getElementById('gemGrid').innerHTML)        renderGems('ALL');
  if (page === 'sp500'   && !document.getElementById('spGrid').innerHTML)         renderSP500('ALL');
  if (page === 'vault'   && !document.getElementById('vaultPicksGrid').innerHTML) renderVault();
  if (page === 'entry'   && !document.getElementById('entryGrid').innerHTML)      renderDailyEntry();
  if (page === 'tracker' && !document.getElementById('trackerBody').innerHTML)    renderTracker();
  if (page === 'options' && !document.getElementById('optionsBody').innerHTML)    renderOptions();
}

// ── Daily Entry Renderer ──
function renderDailyEntry() {
  const entries = D.daily_entries || [];
  const buyCount   = entries.filter(e => e.action === 'BUY').length;
  const watchCount = entries.filter(e => e.action === 'WATCH').length;

  // Summary bar
  const sb = document.getElementById('entrySummaryBar');
  if (entries.length) {
    const top = entries[0];
    const avgRsi = entries.length
      ? Math.round(entries.slice(0,5).reduce((s,e) => s + (e.rsi||50), 0) / Math.min(entries.length,5))
      : 0;
    sb.innerHTML =
      `<div class="eb-item"><div class="eb-label">จำนวนวันนี้</div><div class="eb-val pos">${entries.length} ตัว</div></div>` +
      `<div class="eb-item"><div class="eb-label">BUY NOW</div><div class="eb-val pos">${buyCount}</div></div>` +
      `<div class="eb-item"><div class="eb-label">WATCH</div><div class="eb-val yl">${watchCount}</div></div>` +
      `<div class="eb-item"><div class="eb-label">Top Pick</div><div class="eb-val">${top.sym}</div></div>` +
      `<div class="eb-item"><div class="eb-label">Avg RSI (Top 5)</div><div class="eb-val" style="color:${rsiColor(avgRsi)}">${avgRsi}</div></div>`;
    sb.style.display = 'flex';
  }

  document.getElementById('entryCount').textContent = entries.length
    ? entries.length + ' หุ้น — เรียงจากคะแนนสูงสุด'
    : 'ไม่มีหุ้น BUY/WATCH วันนี้';

  const rankEmojis = ['🥇','🥈','🥉'];
  document.getElementById('entryGrid').innerHTML = entries.map((e, i) => {
    const act  = e.action;
    const dc   = (e.chg||0) >= 0 ? 'pos' : 'neg';
    const rank = i < 3 ? rankEmojis[i] : (i+1);
    const symColor = act === 'BUY' ? 'var(--green)' : 'var(--yellow)';
    const stars = act === 'BUY' ? '&#9733;'.repeat(e.stars||1)+'&#9734;'.repeat(3-(e.stars||1)) : '';

    const chips = [
      e.rsi  != null ? `<span class="e-chip">RSI <b style="color:${rsiColor(e.rsi)}">${e.rsi}</b></span>` : '',
      `<span class="e-chip">52W-pos <b>${(e.pct_range||0).toFixed(0)}%</b></span>`,
      e.pe_ratio   ? `<span class="e-chip">P/E <b>${e.pe_ratio.toFixed(1)}</b></span>` : '',
      e.beta       ? `<span class="e-chip">&#x3B2; <b>${e.beta.toFixed(2)}</b></span>` : '',
      e.total_analysts ? `<span class="e-chip">Analysts <b>${e.total_analysts}</b></span>` : '',
    ].filter(Boolean).join('');

    return `<div class="entry-card" onclick="openModal('${e.sym}')">
      <div class="entry-rank">${rank}</div>
      <div>
        <div class="entry-sym" style="color:${symColor}">${e.sym}</div>
        <div class="entry-name">${e.name||''}</div>
        <span class="action-badge ab-${act}" style="margin-top:6px;display:inline-flex">${act==='BUY'?'BUY NOW':'WATCH'}${stars?` <span class="stars" style="margin-left:4px">${stars}</span>`:''}</span>
      </div>
      <div class="entry-body">
        <div class="entry-reason">${e.reason||''}</div>
        <div class="entry-tp-row">
          <span class="etp etp-entry">Entry ${fUSD(e.entry)}</span>
          <span class="etp etp-sl">SL ${fUSD(e.sl)}</span>
          <span class="etp etp-tp">TP ${fUSD(e.tp)}</span>
          <span class="etp etp-rr">R:R ${e.rr}:1</span>
        </div>
        <div class="entry-chips" style="margin-top:6px">${chips}</div>
      </div>
      <div class="entry-right">
        <span class="entry-score">Score ${e.entry_score}</span>
        <span class="entry-price">${fUSD(e.price)}</span>
        <span class="entry-chg ${dc}">${fPct(e.chg)}</span>
      </div>
    </div>`;
  }).join('');
}

// ── Hidden Gems Data ──
const GEMS = [
  // AI / Data Infrastructure
  {t:'INOD',c:'Innodata',th:'AI',thesis:'AI data labeling & engineering สำหรับ LLM training — เบื้องหลัง AI revolution',up:63,risk:'g'},
  {t:'ZETA',c:'Zeta Global',th:'AI',thesis:'220M-person identity graph + Athena AI agent สำหรับ digital marketing',up:35,risk:'g'},
  {t:'PGY',c:'Pagaya Technologies',th:'AI',thesis:'AI credit decisioning ใน 30+ ธนาคาร — ensemble ML models ประเมินความเสี่ยงสินเชื่อ',up:40,risk:'g'},
  {t:'EVER',c:'EverQuote',th:'AI',thesis:'AI marketplace เชื่อม insurance carrier กับ consumer. EPS forecast +19% YoY 2026',up:25,risk:'g'},
  {t:'SOUN',c:'SoundHound AI',th:'AI',thesis:'Voice AI สำหรับ restaurant/retail/healthcare. Drive-thru ordering AI',up:30,risk:'s'},
  {t:'SERV',c:'Serve Robotics',th:'AI',thesis:'Physical AI delivery robots. ตลาด AI robot $7.4B→$60.6B ในปี 2034',up:50,risk:'s'},
  {t:'KRNT',c:'Kornit Digital',th:'AI',thesis:'Digital textile printing on-demand fashion manufacturing. Upside 58%',up:58,risk:'g'},
  {t:'SKYT',c:'SkyWater Technology',th:'AI',thesis:'US-based semiconductor foundry (ไม่ใช่ TSMC Taiwan) — national security play',up:16,risk:'s'},
  {t:'ONTO',c:'Onto Innovation',th:'AI',thesis:'Semiconductor inspection & process control — ลูกค้า chipmaker ทุกเจ้า',up:17,risk:'g'},
  {t:'CCB',c:'Coastal Financial Corp',th:'AI',thesis:'BaaS (Banking-as-a-Service) ให้ fintech — rare business model ใน community bank',up:15,risk:'g'},
  // Defense / Counter-Drone
  {t:'ONDS',c:'Ondas Holdings',th:'Defense',thesis:'Counter-drone ป้องกัน FIFA 2026 (16 เมือง) + $68M military order. Palantir AIP integrated',up:80,risk:'s'},
  {t:'DRO',c:'DroneShield',th:'Defense',thesis:'AI-powered counter-UAS — ML trained on drone RF signatures. US DoD deployed',up:60,risk:'s'},
  {t:'KRKNF',c:'Kraken Robotics',th:'Defense',thesis:'Underwater defense robotics — NATO submarine detection & mine countermeasures',up:45,risk:'s'},
  {t:'TDY',c:'Teledyne Technologies',th:'Defense',thesis:'Defense electronics/aerospace. Aerospace segment +40.4% Q4 2025. FCF $1B+/yr',up:20,risk:'v'},
  {t:'BAH',c:'Booz Allen Hamilton',th:'Defense',thesis:'IT consulting สำหรับ US government. Q3 backlog $38B record. PE 11x ถูกผิดปกติ',up:25,risk:'v'},
  {t:'ATRO',c:'Astronics',th:'Defense',thesis:'Aerospace lighting/power/avionics components. Recovery play หลัง Boeing delays',up:15,risk:'g'},
  {t:'KRMN',c:'Karman Holdings',th:'Defense',thesis:'Space/defense components supplier. Analyst upside 66.9% — highest in peer group',up:67,risk:'g'},
  {t:'HON',c:'Honeywell International',th:'Defense',thesis:'Defense & Space backlog $37B+. Corporate separation catalyst Q3 2026 = unlock value',up:20,risk:'v'},
  {t:'HLI',c:'Houlihan Lokey',th:'Defense',thesis:'Investment bank M&A advisory. Goldman highest-conviction — $237 target, 36% upside',up:36,risk:'g'},
  {t:'GNSS',c:'Genasys',th:'Defense',thesis:'Emergency warning & mass communications systems — government contracts',up:40,risk:'s'},
  // Space
  {t:'LUNR',c:'Intuitive Machines',th:'Space',thesis:'Commercial lunar lander. L3Harris SDA missile tracking contract. $943M backlog',up:50,risk:'s'},
  {t:'RDW',c:'Redwire Space',th:'Space',thesis:'In-space 3D printing manufacturing. NASA Gateway deployable solar arrays',up:60,risk:'s'},
  {t:'MDA',c:'MDA Space',th:'Space',thesis:'Canadarm3 robotic systems สำหรับ NASA Gateway — multi-decade recurring revenue',up:30,risk:'g'},
  {t:'RKLB',c:'Rocket Lab USA',th:'Space',thesis:'Launch vehicle (Electron) + space systems. Neutron rocket mid-size development',up:40,risk:'s'},
  {t:'SPIR',c:'Spire Global',th:'Space',thesis:'Space-based data subscriptions (weather/maritime/aviation) — B2B SaaS model',up:55,risk:'s'},
  {t:'ASTS',c:'AST SpaceMobile',th:'Space',thesis:'Space-based cellular — ดาวเทียมทำให้ทุก smartphone เชื่อม internet ได้โดยตรง',up:70,risk:'s'},
  // Clean Energy
  {t:'EOSE',c:'Eos Energy Enterprises',th:'Energy',thesis:'Zinc-based grid-scale batteries — ไม่ใช้ lithium จีน. Q1 2026 revenue $56-57M',up:80,risk:'s'},
  {t:'SMR',c:'NuScale Power',th:'Energy',thesis:'เพียง NRC-approved SMR design. DoE funding + space nuclear applications',up:90,risk:'s'},
  {t:'SHLS',c:'Shoals Technologies',th:'Energy',thesis:'Solar electrical EBOS components. Capital-light, renewable energy tailwind',up:25,risk:'g'},
  {t:'STEM',c:'Stem Inc',th:'Energy',thesis:'AI-driven battery storage optimization software สำหรับ grid/commercial',up:40,risk:'s'},
  {t:'AMRC',c:'Ameresco',th:'Energy',thesis:'Renewable energy solutions สำหรับ government/commercial. Long-term contracts',up:30,risk:'g'},
  {t:'ARRY',c:'Array Technologies',th:'Energy',thesis:'Solar tracking systems for utility-scale solar. US manufacturing advantage',up:35,risk:'g'},
  {t:'FF',c:'FutureFuel Corp',th:'Energy',thesis:'Specialty chemicals + biofuels. Dividend yield 7.5% + strong balance sheet',up:20,risk:'v'},
  // Biotech
  {t:'INO',c:'Inovio Pharma',th:'Biotech',thesis:'INO-3107 BLA submission — FDA approval expected 2026. Analyst upside 200%',up:200,risk:'s'},
  {t:'TERN',c:'Terns Pharmaceuticals',th:'Biotech',thesis:'TERN-701 Phase 1 CML results expected. Analyst consensus upside 101%',up:101,risk:'s'},
  {t:'CRDL',c:'Cardiol Therapeutics',th:'Biotech',thesis:'CardiolRx Phase 2 ARCHER trial positive. Analyst upside 602% (very speculative)',up:602,risk:'s'},
  {t:'SLN',c:'Silence Therapeutics',th:'Biotech',thesis:'RNAi platform — zerlasiran Phase 3 hemoglobin reduction. Upside 324%',up:324,risk:'s'},
  {t:'ATRA',c:'Atara Biotherapeutics',th:'Biotech',thesis:'Tabelecleucel BLA submission — FDA decision 2026. Analyst upside 96%',up:96,risk:'s'},
  {t:'CRSP',c:'CRISPR Therapeutics',th:'Biotech',thesis:'Gene editing leader. CEO: "defining year 2026". 14/26 analysts bullish, upside 52%',up:52,risk:'s'},
  {t:'HALO',c:'Halozyme Therapeutics',th:'Biotech',thesis:'Drug-delivery ENHANZE platform — royalty model. Revenue + EPS double-digit growth',up:25,risk:'g'},
  {t:'CPRX',c:'Catalyst Pharmaceuticals',th:'Biotech',thesis:'Rare disease FIRDAPSE. High margins, low analyst coverage = hidden opportunity',up:30,risk:'g'},
  {t:'NUVL',c:'Nuvalent',th:'Biotech',thesis:'Next-gen ROS1/ALK oncology inhibitors. Clinical stage entering commercialization',up:45,risk:'s'},
  {t:'RXRX',c:'Recursion Pharmaceuticals',th:'Biotech',thesis:'AI drug discovery + Nvidia partnership. เป็น AI-biotech ที่ institutional สนใจ',up:60,risk:'s'},
  {t:'PRVA',c:'Privia Health Group',th:'Biotech',thesis:'Physician enablement for value-based care. Consistent revenue growth, scalable',up:30,risk:'g'},
  {t:'TOI',c:'The Oncology Institute',th:'Biotech',thesis:'Community cancer care. Q1 2026 revenue $147M (+41% YoY). Insider buying',up:35,risk:'g'},
  // Cybersecurity
  {t:'TENB',c:'Tenable Holdings',th:'Cyber',thesis:'Cloud exposure management (Tenable One). 500 new enterprise/Q. Upside ~70%',up:70,risk:'g'},
  {t:'QLYS',c:'Qualys Inc',th:'Cyber',thesis:'10,000+ enterprise customers. FCF margin 43%, EBITDA 47%. Analyst upside 80%',up:80,risk:'v'},
  {t:'CVLT',c:'Commvault Systems',th:'Cyber',thesis:'Ransomware recovery leader. SaaS ARR +40% YoY. Price target +50% upside',up:50,risk:'g'},
  {t:'IDN',c:'Intellicheck',th:'Cyber',thesis:'Real-time identity validation banking/automotive. Record SaaS revenue growth',up:60,risk:'g'},
  {t:'CWAN',c:'Clearwater Analytics',th:'Cyber',thesis:'Cloud risk analytics สำหรับ insurance/asset management. Sticky enterprise SaaS',up:25,risk:'g'},
  // Industrial / Small Cap Value
  {t:'ORN',c:'Orion Group Holdings',th:'Industrial',thesis:'Marine & concrete construction. Data center + manufacturing plant contracts surge',up:30,risk:'g'},
  {t:'SMP',c:'Standard Motor Products',th:'Industrial',thesis:'Automotive aftermarket parts — defensive demand. Dividend + consistent revenue',up:15,risk:'v'},
  {t:'TRS',c:'TriMas',th:'Industrial',thesis:'Diversified manufacturer. Share buyback 22.81% completed. Insider confidence',up:20,risk:'v'},
  {t:'RBC',c:'RBC Bearings',th:'Industrial',thesis:'Precision bearings สำหรับ aerospace/industrial. Stable high margins',up:12,risk:'v'},
  {t:'HLIO',c:'Helios Technologies',th:'Industrial',thesis:'Hydraulic/electronic control systems. Niche industrial compounder',up:20,risk:'g'},
  {t:'KAI',c:'Kadant',th:'Industrial',thesis:'Industrial processing equipment (pulp/paper/metals). Consistent compounder',up:18,risk:'v'},
  {t:'NDSN',c:'Nordson Corp',th:'Industrial',thesis:'Precision dispensing systems สำหรับ electronics manufacturing. High margin niche',up:15,risk:'v'},
  {t:'LQDT',c:'Liquidity Services',th:'Industrial',thesis:'Digital marketplace surplus inventory. E-commerce returns boom benefits. Upside 56%',up:56,risk:'g'},
  {t:'AXT',c:'AXT Inc',th:'Industrial',thesis:'Compound semiconductor substrates (GaAs/InP/Ge). Revenue forecast +30% 2026',up:30,risk:'g'},
  {t:'REZI',c:'Resideo Technologies',th:'Industrial',thesis:'Smart home security/HVAC products. ADT installation network',up:20,risk:'g'},
  // Consumer Staples (Oversold Recovery)
  {t:'HRL',c:'Hormel Foods',th:'Staples',thesis:'ราคาตก 25% ใน 2025 — brand แข็งแกร่ง. EPS forecast +11.5%. Dividend yield 5.12%',up:28,risk:'v'},
  {t:'CAG',c:'Conagra Brands',th:'Staples',thesis:'ราคาตก 37% ใน 2025 — portfolio rationalization. Dividend yield 8.4% = income play',up:25,risk:'v'},
  {t:'LW',c:'Lamb Weston',th:'Staples',thesis:'ราคาตก 34% ใน 2025 — frozen food, stable demand, foodservice recovery',up:30,risk:'v'},
  {t:'SJM',c:'J.M. Smucker',th:'Staples',thesis:'Pressured by coffee แต่ brand equity แข็ง. Dividend yield 4.59%. Mix management',up:20,risk:'v'},
  {t:'POST',c:'Post Holdings',th:'Staples',thesis:'Cereal brand tiering play. Sticky category + pricing power',up:15,risk:'g'},
  // Healthcare REIT / Services
  {t:'AHR',c:'American Healthcare REIT',th:'REIT',thesis:'Senior housing occupancy surge — baby boomer demand + frozen supply. RIDEA structure',up:35,risk:'g'},
  {t:'DOC',c:'Healthpeak Properties',th:'REIT',thesis:'40% discount to fair value (Morningstar). Medical office + lab space portfolio',up:40,risk:'v'},
  {t:'O',c:'Realty Income',th:'REIT',thesis:'5-star Morningstar, 20% discount. 15,000+ locations. Dividend yield 5.5%',up:20,risk:'v'},
  {t:'PEB',c:'Pebblebrook Hotel Trust',th:'REIT',thesis:'Upscale hotels recovery. Insider buying June 2026 — smart money signal',up:30,risk:'g'},
  {t:'PINE',c:'Alpine Income Property',th:'REIT',thesis:'Small net-lease REIT. Dividend yield 6%+ undercovered by Wall Street',up:20,risk:'v'},
  {t:'ILPT',c:'Industrial Logistics Prop',th:'REIT',thesis:'Warehouse REIT ราคาถูกมาก — asset value สูงกว่า market cap ปัจจุบัน',up:40,risk:'s'},
  // Fintech / Finance
  {t:'ABR',c:'Arbor Realty Trust',th:'Fintech',thesis:'Commercial real estate lending REIT. PE 14.1x, insider buying. High yield',up:25,risk:'g'},
  {t:'MCB',c:'Metropolitan Bank Holding',th:'Fintech',thesis:'NY community bank. PE 12.7x — undervalued ชัดเจน. Consistent earnings',up:20,risk:'v'},
  {t:'CTBI',c:'Community Trust Bancorp',th:'Fintech',thesis:'Kentucky community bank. Insider buying June 2026. Dividend payer',up:15,risk:'v'},
  {t:'PKBK',c:'Parke Bancorp',th:'Fintech',thesis:'NJ community bank. Net income margin 50% ผิดปกติสูง. Insider activity',up:20,risk:'v'},
  {t:'IDT',c:'IDT Corporation',th:'Fintech',thesis:'Telecom + BOSS Money remittance fintech. Underfollowed, growing international',up:30,risk:'g'},
  {t:'RELY',c:'Remitly Global',th:'Fintech',thesis:'Digital remittances. Revenue +30%+ YoY. กำลัง scale ถึง profitability',up:40,risk:'g'},
  {t:'PAYO',c:'Payoneer Global',th:'Fintech',thesis:'Cross-border payments สำหรับ SME/freelancers globally. Asset-light model',up:30,risk:'g'},
  // Autonomous / Sensing
  {t:'OUST',c:'Ouster',th:'Auto',thesis:'Digital CMOS lidar ราคาถูกลงมาก. Merger กับ Velodyne = largest US lidar company',up:40,risk:'s'},
  {t:'HSAI',c:'Hesai Technology',th:'Auto',thesis:'4M+ unit lidar orders. 24 OEM wins (BYD/Li Auto/Xiaomi). NVIDIA DRIVE qualified',up:50,risk:'s'},
  {t:'AUR',c:'Aurora Innovation',th:'Auto',thesis:'Autonomous trucks — 200+ trucks end 2026. Revenue $14-16M/yr growing fast',up:60,risk:'s'},
  {t:'LAZR',c:'Luminar Technologies',th:'Auto',thesis:'Lidar สำหรับ automotive OEM. Volvo partnership. Long runway แต่ burning cash',up:50,risk:'s'},
  // Specialty
  {t:'FMC',c:'FMC Corporation',th:'Chemical',thesis:'Agricultural chemicals. Director insider buy $250K Feb 2026. Recovery play',up:25,risk:'g'},
  {t:'TROX',c:'Tronox Holdings',th:'Chemical',thesis:'Titanium dioxide สำหรับ paints/coatings. Cyclical recovery cycle beginning',up:30,risk:'g'},
  {t:'ASIX',c:'AdvanSix',th:'Chemical',thesis:'Nylon + specialty chemicals. Compounding earnings growth, attractive PE',up:25,risk:'g'},
  {t:'MERC',c:'Mercer International',th:'Chemical',thesis:'Pulp & paper products. High yield, cyclical recovery underway',up:20,risk:'g'},
  // Healthcare / Consumer
  {t:'OWLT',c:'Owlet Inc',th:'Health',thesis:'FDA-cleared infant monitoring (SmartSock vital signs). EPS growth ~80% 2026 forecast',up:80,risk:'s'},
  {t:'MONRO',c:'Monro Inc',th:'Health',thesis:'Auto service centers chain. EPS forecast +64% 2026. Insider buying. Recovery',up:40,risk:'g'},
  {t:'MBC',c:'MasterBrand',th:'Health',thesis:'Kitchen cabinet manufacturer. Insider activity June 2026. Consumer recovery play',up:25,risk:'g'},
  {t:'ADSS',c:'Advantage Solutions',th:'Health',thesis:'Sales & marketing outsourcing. Insider D.Peacock bought 8,000 shares Mar 2026',up:20,risk:'g'},
  // Value / Wide Moat (Morningstar)
  {t:'NKE',c:'Nike Inc',th:'Value',thesis:'Morningstar: 57% below fair value. Global brand turnaround + new CEO',up:57,risk:'v'},
  {t:'MSFT',c:'Microsoft',th:'Value',thesis:'Morningstar: 38% below fair value. Azure AI + Copilot revenue acceleration',up:38,risk:'v'},
  {t:'HRL2',c:'Hormel (duplicate see above)',th:'Value',thesis:'Consumer staples oversold',up:28,risk:'v'},
  {t:'QLYS2',c:'Qualys (see above)',th:'Value',thesis:'Cybersecurity profitability',up:80,risk:'v'},
];
const GEMS_CLEAN = GEMS.filter(g => !g.t.includes('2'));
const GEMS_BY_TICKER = {};
GEMS_CLEAN.forEach(g => GEMS_BY_TICKER[g.t] = g);

const THEME_COLORS = {
  AI:'#a855f7',Defense:'#3b82f6',Space:'#6366f1',Energy:'#10b981',
  Biotech:'#ec4899',Cyber:'#f59e0b',Industrial:'#64748b',
  Staples:'#84cc16',REIT:'#14b8a6',Fintech:'#f97316',
  Auto:'#06b6d4',Chemical:'#8b5cf6',Health:'#e11d48',Value:'#10b981'
};
const RISK_LABEL = {s:'Speculative',g:'Growth',v:'Value'};
const RISK_CLS   = {s:'rs',g:'rg',v:'rv'};

let activeTheme = 'ALL';
function renderGems(theme) {
  activeTheme = theme;
  document.querySelectorAll('.gf').forEach(b => b.classList.toggle('on', b.dataset.th === theme));
  const list = theme === 'ALL' ? GEMS_CLEAN : GEMS_CLEAN.filter(g => g.th === theme);
  document.getElementById('gemCount').textContent = list.length + ' หุ้น';
  document.getElementById('gemGrid').innerHTML = list.map(g => {
    const col = THEME_COLORS[g.th] || '#64748b';
    const upStr = g.up >= 100 ? '+'+g.up+'%' : '+'+g.up+'%';
    return `<div class="gem-card" style="border-left:3px solid ${col};cursor:pointer" onclick="openGemChart('${g.t}')">
      <div class="gem-top">
        <span class="gem-ticker" style="color:${col}">${g.t}</span>
        <span class="gem-badge" style="background:${col}20;color:${col}">${g.th}</span>
      </div>
      <div class="gem-company">${g.c}</div>
      <div class="gem-thesis">${g.thesis}</div>
      <div class="gem-footer">
        <span class="gem-upside">${upStr} upside</span>
        <span class="gem-risk ${RISK_CLS[g.risk]}">${RISK_LABEL[g.risk]}</span>
      </div>
      <div style="font-size:10px;color:var(--muted);margin-top:2px">&#x1F4C8; คลิกดูกราฟ</div>
    </div>`;
  }).join('');
}

// ── Top-10 Picks ──
const TOP10 = [
  {rank:1,  t:'QLYS', c:'Qualys Inc',            th:'Cyber',    up:80,  risk:'v',
   reason:'FCF margin 43% — หายากมากในกลุ่ม cybersecurity. 10,000+ enterprise customers ยึดไว้นาน. PE ถูกกว่า peer อย่าง CrowdStrike 40%. หุ้น profitable + growing = risk ต่ำที่สุดใน list'},
  {rank:2,  t:'TENB', c:'Tenable Holdings',       th:'Cyber',    up:70,  risk:'g',
   reason:'Tenable One platform กลายเป็น standard สำหรับ cloud exposure management. 500 new enterprise customers/Q, net revenue retention 110%+. Upside 70% แต่ business model ระดับ Value quality'},
  {rank:3,  t:'CVLT', c:'Commvault Systems',       th:'Cyber',    up:50,  risk:'g',
   reason:'Ransomware recovery คือ megatrend — ทุกองค์กรต้องมี backup. SaaS ARR +40% YoY แปลว่ากำลัง transition สำเร็จ. FCF แข็งแกร่ง + ไม่มีคู่แข่งในกลุ่ม enterprise data protection'},
  {rank:4,  t:'DOC',  c:'Healthpeak Properties',   th:'REIT',     up:40,  risk:'v',
   reason:'Morningstar 5-star: ราคา 40% ต่ำกว่า fair value. Medical office + life science lab — sector ที่ทน recession. Dividend yield 5%+ บวก upside re-rating เมื่อ rate ลด'},
  {rank:5,  t:'INOD', c:'Innodata Inc',             th:'AI',       up:63,  risk:'g',
   reason:'ธุรกิจ data labeling สำหรับ LLM training — AI boom ยิ่งโต demand ยิ่งสูง. ลูกค้าหลักคือ hyperscaler. Market cap เล็ก (~$800M) เทียบกับ revenue traction = asymmetric upside'},
  {rank:6,  t:'HRL',  c:'Hormel Foods',             th:'Staples',  up:28,  risk:'v',
   reason:'ราคาร่วง 25% ใน 2025 จาก sector rotation ไม่ใช่ business deterioration. Dividend yield 5.12% = ได้เงินรอระหว่างถือ. Brand Spam/SKIPPY/Hormel แข็งแกร่ง 100+ ปี. EPS คาด +11.5% YoY 2026'},
  {rank:7,  t:'LUNR', c:'Intuitive Machines',       th:'Space',    up:50,  risk:'g',
   reason:'$943M backlog = revenue visibility 3+ ปี. SDA missile tracking contract + NASA CLPS lunar ทำให้ไม่ใช่ speculative อีกต่อไป. Space economy กำลังเข้า commercial phase จริง'},
  {rank:8,  t:'EOSE', c:'Eos Energy Enterprises',   th:'Energy',   up:80,  risk:'s',
   reason:'Zinc battery ไม่พึ่งพา lithium จากจีน = geopolitical advantage ชัดเจน. DoE loan $315M pending. Q1 2026 revenue $56-57M แสดงว่า product ขายได้แล้ว ไม่ใช่แค่ R&D'},
  {rank:9,  t:'CRSP', c:'CRISPR Therapeutics',      th:'Biotech',  up:52,  risk:'s',
   reason:'Gene editing leader ที่มี product commercial จริง (Casgevy สำหรับ sickle cell disease อนุมัติแล้ว). 14/26 analysts bullish. CEO: "defining year 2026" = catalyst ชัดเจน. ดีกว่า speculative biotech เพราะมี revenue แล้ว'},
  {rank:10, t:'ONDS', c:'Ondas Holdings',            th:'Defense',  up:80,  risk:'s',
   reason:'FIFA World Cup 2026 (16 เมือง) = near-term revenue catalyst ที่มี deadline ชัด. $68M military order + Palantir AIP integration. Counter-drone คือ theme ที่รัฐบาล US ผลักดันหนักมาก — political tailwind'}
];

function toggleTop10() {
  const panel = document.getElementById('top10Panel');
  const isOpen = panel.classList.contains('open');
  if (!isOpen) {
    if (!document.getElementById('top10List').innerHTML) {
      document.getElementById('top10List').innerHTML = TOP10.map(p => {
        const col = THEME_COLORS[p.th] || '#64748b';
        const rankEmoji = ['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟'][p.rank-1];
        return `<div class="t10-row" onclick="openGemChart('${p.t}')">
          <div class="t10-rank">${rankEmoji}</div>
          <div class="t10-sym" style="color:${col}">${p.t}</div>
          <div class="t10-body">
            <div class="t10-company">${p.c} · <span style="color:${col}">${p.th}</span></div>
            <div class="t10-reason">${p.reason}</div>
          </div>
          <div class="t10-meta">
            <span class="t10-up">+${p.up}%</span>
            <span class="t10-risk ${RISK_CLS[p.risk]}">${RISK_LABEL[p.risk]}</span>
          </div>
        </div>`;
      }).join('');
    }
    panel.classList.add('open');
    panel.scrollIntoView({behavior:'smooth',block:'nearest'});
  } else {
    panel.classList.remove('open');
  }
}

// ── S&P 500 Sector Colors (extend THEME_COLORS) ──
Object.assign(THEME_COLORS, {
  Tech:'#a855f7', Healthcare:'#ec4899', Financials:'#3b82f6',
  Consumer:'#f59e0b', Staples:'#84cc16', Industrials:'#64748b',
  Communication:'#6366f1', Materials:'#d97706', Utilities:'#06b6d4',
  // REIT / Energy already exist in THEME_COLORS
});

// ── SP500 Data (~120 stocks) ──
const SP500 = [
  // Technology
  {t:'NVDA', c:'NVIDIA Corp',              sec:'Tech',          mc:'$5T',    sig:'buy',   thesis:'AI chip king — 90%+ data center GPU market share. Blackwell demand ไม่หยุด'},
  {t:'AAPL', c:'Apple Inc',                sec:'Tech',          mc:'$3.3T',  sig:'hold',  thesis:'Services $100B+/yr — ecosystem lock-in. iPhone installed base 1.2B users ทั่วโลก'},
  {t:'MSFT', c:'Microsoft Corp',           sec:'Tech',          mc:'$2.9T',  sig:'buy',   thesis:'Azure AI + Copilot = revenue layer ใหม่. GitHub Copilot 1.8M paid users'},
  {t:'GOOGL',c:'Alphabet Inc',             sec:'Tech',          mc:'$4.4T',  sig:'buy',   thesis:'Google Cloud +63% YoY. Search moat + Gemini AI. PE 17x ถูกที่สุดใน Big Tech'},
  {t:'META', c:'Meta Platforms',           sec:'Tech',          mc:'$1.4T',  sig:'buy',   thesis:'Reels + AI Ads = margin expansion. Op margin 41%. Llama open-source moat'},
  {t:'AVGO', c:'Broadcom Inc',             sec:'Tech',          mc:'$1.8T',  sig:'buy',   thesis:'Custom AI ASICs สำหรับ Google/Meta. VMware acquisition เพิ่ม recurring revenue'},
  {t:'AMD',  c:'Advanced Micro Devices',   sec:'Tech',          mc:'$835B',  sig:'buy',   thesis:'MI300X GPU ชิง NVDA market share. Data center revenue +80% YoY'},
  {t:'ORCL', c:'Oracle Corp',              sec:'Tech',          mc:'$500B',  sig:'buy',   thesis:'OCI cloud on fire — Ellison "fastest growing cloud". Database ERP sticky moat'},
  {t:'CRM',  c:'Salesforce Inc',           sec:'Tech',          mc:'$280B',  sig:'hold',  thesis:'Agentforce AI agent platform. CRM king แต่ growth decelerating. FCF yield 4%+'},
  {t:'ADBE', c:'Adobe Inc',                sec:'Tech',          mc:'$185B',  sig:'hold',  thesis:'Firefly AI ใน Creative Cloud. เจอ competition จาก Canva AI + generative newcomers'},
  {t:'QCOM', c:'Qualcomm Inc',             sec:'Tech',          mc:'$180B',  sig:'buy',   thesis:'Snapdragon X Elite PC chip — diversify จาก smartphone. AI edge computing play'},
  {t:'TXN',  c:'Texas Instruments',        sec:'Tech',          mc:'$165B',  sig:'hold',  thesis:'Analog chip king 80K+ products — moat ที่ชัดเจน. Capex cycle = 2027 FCF boom'},
  {t:'NOW',  c:'ServiceNow Inc',           sec:'Tech',          mc:'$105B',  sig:'buy',   thesis:'AI workflow automation สำหรับ enterprise. Net retention 125%+ = sticky'},
  {t:'AMAT', c:'Applied Materials',        sec:'Tech',          mc:'$165B',  sig:'buy',   thesis:'Chip fab equipment — ทุก wafer ที่ผลิตในโลกผ่าน AMAT tools. Duopoly กับ LRCX'},
  {t:'MU',   c:'Micron Technology',        sec:'Tech',          mc:'$115B',  sig:'buy',   thesis:'HBM (High Bandwidth Memory) สำหรับ AI GPU = revenue tier ใหม่ที่ margin สูง'},
  {t:'INTC', c:'Intel Corp',               sec:'Tech',          mc:'$530B',  sig:'watch', thesis:'Turnaround play — Intel Foundry 18A. TSMC competitor ถ้า execute ได้ปี 2027'},
  {t:'LRCX', c:'Lam Research',             sec:'Tech',          mc:'$95B',   sig:'buy',   thesis:'Etch/deposition tools สำหรับ chip fabs. Duopoly pricing power กับ AMAT'},
  {t:'KLAC', c:'KLA Corp',                 sec:'Tech',          mc:'$75B',   sig:'buy',   thesis:'Process control inspection equipment — 50%+ global market share'},
  {t:'SNPS', c:'Synopsys Inc',             sec:'Tech',          mc:'$80B',   sig:'buy',   thesis:'EDA software — chip designers ทุกรายต้องใช้. Ansys merger เพิ่ม simulation moat'},
  {t:'ACN',  c:'Accenture PLC',            sec:'Tech',          mc:'$200B',  sig:'hold',  thesis:'IT consulting + AI transformation. Beneficiary enterprise AI adoption ทุก industry'},
  {t:'IBM',  c:'IBM Corp',                 sec:'Tech',          mc:'$225B',  sig:'hold',  thesis:'Hybrid cloud (Red Hat) + watsonx AI. Dividend 3.5% + slow-growth value play'},
  {t:'CSCO', c:'Cisco Systems',            sec:'Tech',          mc:'$200B',  sig:'hold',  thesis:'Network infrastructure + Splunk. AI-era network upgrade cycle coming 2026-27'},
  {t:'INTU', c:'Intuit Inc',               sec:'Tech',          mc:'$165B',  sig:'hold',  thesis:'TurboTax + QuickBooks AI Assist. SMB financial software monopoly USA'},
  {t:'PANW', c:'Palo Alto Networks',        sec:'Tech',          mc:'$130B',  sig:'buy',   thesis:'Cybersecurity platform consolidation — SASE + XDR + SOC. Billings beat consistently'},
  // Healthcare
  {t:'LLY',  c:'Eli Lilly & Co',           sec:'Healthcare',    mc:'$680B',  sig:'buy',   thesis:'GLP-1 Mounjaro/Zepbound — weight loss revolution. Revenue คาด $60B ในปี 2027'},
  {t:'UNH',  c:'UnitedHealth Group',        sec:'Healthcare',    mc:'$475B',  sig:'hold',  thesis:'Largest health insurer US. Medicare Advantage growth. PE 17x reasonable'},
  {t:'JNJ',  c:'Johnson & Johnson',         sec:'Healthcare',    mc:'$380B',  sig:'hold',  thesis:'Pharma + MedTech conglomerate. Dividend 62 consecutive increase years. Defensive'},
  {t:'ABBV', c:'AbbVie Inc',                sec:'Healthcare',    mc:'$310B',  sig:'buy',   thesis:'Skyrizi + Rinvoq แทน Humira ได้ผลดี. Revenue คาด $60B+ ปี 2026. Dividend 3.5%'},
  {t:'MRK',  c:'Merck & Co',               sec:'Healthcare',    mc:'$255B',  sig:'buy',   thesis:'Keytruda oncology $25B+/yr — ยาที่ขายดีที่สุดในโลก. 30+ pipeline candidates'},
  {t:'TMO',  c:'Thermo Fisher Scientific',  sec:'Healthcare',    mc:'$200B',  sig:'buy',   thesis:'Life science tools — ทุก lab ในโลกใช้ ThermoFisher. Sticky recurring revenue'},
  {t:'ABT',  c:'Abbott Laboratories',       sec:'Healthcare',    mc:'$200B',  sig:'buy',   thesis:'FreeStyle Libre CGM 5M+ users. Diagnostics + devices diversified portfolio'},
  {t:'AMGN', c:'Amgen Inc',                 sec:'Healthcare',    mc:'$165B',  sig:'hold',  thesis:'MariTide GLP-1 challenge Lilly. Enbrel patent cliff แต่ pipeline ชดเชยได้บางส่วน'},
  {t:'GILD', c:'Gilead Sciences',           sec:'Healthcare',    mc:'$125B',  sig:'buy',   thesis:'HIV Biktarvy $13B/yr monopoly. Trodelvy oncology = next growth platform'},
  {t:'ISRG', c:'Intuitive Surgical',        sec:'Healthcare',    mc:'$185B',  sig:'buy',   thesis:'Da Vinci robotic surgery — 9,000+ installed systems. Razor/blade recurring revenue'},
  {t:'PFE',  c:'Pfizer Inc',               sec:'Healthcare',    mc:'$145B',  sig:'watch', thesis:'Post-COVID restructuring. Seagen cancer acquisition. Dividend 6.5% แต่ growth ไม่ชัด'},
  {t:'VRTX', c:'Vertex Pharmaceuticals',    sec:'Healthcare',    mc:'$115B',  sig:'buy',   thesis:'CF Trikafta $8B+/yr monopoly. Pain drug suzetrigine FDA-approved = new market'},
  {t:'REGN', c:'Regeneron Pharma',          sec:'Healthcare',    mc:'$90B',   sig:'buy',   thesis:'Eylea + Dupixent $15B+/yr. Inflammation & rare disease franchise leader'},
  {t:'MDT',  c:'Medtronic PLC',             sec:'Healthcare',    mc:'$110B',  sig:'hold',  thesis:'Medical devices — pacemaker, insulin pump, Hugo surgical robot. Dividend 3.5%'},
  // Financials
  {t:'BRK-B',c:'Berkshire Hathaway B',      sec:'Financials',    mc:'$1.1T',  sig:'buy',   thesis:'$330B+ cash pile รอจังหวะ. Buffett legacy portfolio — BNSF + GEICO + equities'},
  {t:'JPM',  c:'JPMorgan Chase',            sec:'Financials',    mc:'$750B',  sig:'buy',   thesis:'Best-managed US bank. Jamie Dimon era. NII record + IB fees revival. ROE 17%+'},
  {t:'V',    c:'Visa Inc',                  sec:'Financials',    mc:'$620B',  sig:'buy',   thesis:'Payments duopoly — 60%+ market share. ทุก swipe ทั่วโลก Visa ได้ส่วนแบ่ง. Asset-light'},
  {t:'MA',   c:'Mastercard Inc',            sec:'Financials',    mc:'$530B',  sig:'buy',   thesis:'Payments duopoly. International markets growth สูงกว่า US. Network effect moat'},
  {t:'GS',   c:'Goldman Sachs',             sec:'Financials',    mc:'$220B',  sig:'buy',   thesis:'IB + trading revival 2025-26. M&A cycle กลับมา = fee windfall. Return to roots'},
  {t:'BAC',  c:'Bank of America',           sec:'Financials',    mc:'$340B',  sig:'hold',  thesis:'Consumer + commercial banking. NII sensitive กับ rate. Merrill Lynch wealth mgmt'},
  {t:'MS',   c:'Morgan Stanley',            sec:'Financials',    mc:'$215B',  sig:'buy',   thesis:'Wealth management $7T AUM = fee-based recurring. E*TRADE integration complete'},
  {t:'BLK',  c:'BlackRock Inc',             sec:'Financials',    mc:'$155B',  sig:'buy',   thesis:'$10T+ AUM — largest asset manager globally. iShares ETF + alternatives growth'},
  {t:'SPGI', c:'S&P Global Inc',            sec:'Financials',    mc:'$155B',  sig:'buy',   thesis:'Credit ratings + data — ทุก bond issue ต้องจ่าย SPGI. Pricing power สูงสุด'},
  {t:'AXP',  c:'American Express',          sec:'Financials',    mc:'$210B',  sig:'buy',   thesis:'Affluent cardholders — higher spend, lower default. Closed-loop network advantage'},
  {t:'SCHW', c:'Charles Schwab',            sec:'Financials',    mc:'$135B',  sig:'buy',   thesis:'Post-TD Ameritrade: largest retail brokerage. Net new assets $100B+/Q'},
  {t:'MCO',  c:"Moody's Corp",              sec:'Financials',    mc:'$85B',   sig:'buy',   thesis:'Credit ratings duopoly กับ SPGI. Bond market revival = transaction revenue ขึ้น'},
  {t:'ICE',  c:'Intercontinental Exchange', sec:'Financials',    mc:'$90B',   sig:'buy',   thesis:'NYSE owner + mortgage tech (Black Knight). Financial infrastructure moat'},
  {t:'C',    c:'Citigroup',                 sec:'Financials',    mc:'$140B',  sig:'hold',  thesis:'Jane Fraser turnaround simplification. Book value play แต่ execution risk สูง'},
  // Consumer Discretionary
  {t:'HD',   c:'Home Depot Inc',            sec:'Consumer',      mc:'$390B',  sig:'hold',  thesis:'Home improvement king. SRS Distribution acquisition. Rate-sensitive housing cycle'},
  {t:'COST', c:'Costco Wholesale',          sec:'Consumer',      mc:'$440B',  sig:'hold',  thesis:'Membership model 93% renewal. Treasure hunt = premium PE ที่ justify ได้'},
  {t:'MCD',  c:"McDonald's Corp",           sec:'Consumer',      mc:'$195B',  sig:'hold',  thesis:'Franchise 40,000+ locations. $3B+/yr royalty. Recession-resistant food moat'},
  {t:'NKE',  c:'Nike Inc',                  sec:'Consumer',      mc:'$100B',  sig:'buy',   thesis:'Morningstar 5-star: 57% below fair value. New CEO turnaround. Global brand moat'},
  {t:'SBUX', c:'Starbucks Corp',            sec:'Consumer',      mc:'$100B',  sig:'hold',  thesis:'Brian Niccol (Chipotle CEO) turnaround. Traffic recovery + menu simplification'},
  {t:'CMG',  c:'Chipotle Mexican Grill',    sec:'Consumer',      mc:'$75B',   sig:'buy',   thesis:'Digital ordering 35%+ revenue. International expansion เพิ่งเริ่ม. Unit economics ดี'},
  {t:'LOW',  c:"Lowe's Companies",          sec:'Consumer',      mc:'$145B',  sig:'hold',  thesis:'Home improvement duopoly. Pro customer focus = higher ticket + loyalty'},
  {t:'BKNG', c:'Booking Holdings',          sec:'Consumer',      mc:'$180B',  sig:'buy',   thesis:'Online travel duopoly. GenAI trip planner. FCF $7B+/yr. Capital-light model'},
  {t:'ABNB', c:'Airbnb Inc',                sec:'Consumer',      mc:'$80B',   sig:'buy',   thesis:'Long-term stays growth. FCF margin 35%+. Experiences platform เพิ่งเริ่ม scale'},
  {t:'GM',   c:'General Motors',            sec:'Consumer',      mc:'$55B',   sig:'hold',  thesis:'Buyback aggressive — 30% float reduced. ICE profitable + EV pivot more disciplined'},
  {t:'F',    c:'Ford Motor Co',             sec:'Consumer',      mc:'$45B',   sig:'watch', thesis:'EV division ขาดทุน $5B+/yr. Hybrid pivot ถูกต้องแต่ช้า. PE 6x แต่ risk สูง'},
  // Consumer Staples
  {t:'WMT',  c:'Walmart Inc',               sec:'Staples',       mc:'$800B',  sig:'buy',   thesis:'Grocery king + ads business $4B+. Flipkart India. Supply chain defensible moat'},
  {t:'PG',   c:'Procter & Gamble',          sec:'Staples',       mc:'$370B',  sig:'hold',  thesis:'67 consecutive dividend increase years. Global pricing power ใน inflationary env.'},
  {t:'KO',   c:'Coca-Cola Co',              sec:'Staples',       mc:'$285B',  sig:'hold',  thesis:'Warren Buffett core holding. 62 dividend increase years. Global brand distribution'},
  {t:'PEP',  c:'PepsiCo Inc',               sec:'Staples',       mc:'$195B',  sig:'hold',  thesis:'Beverages + Frito-Lay snacks = diversified portfolio. Emerging markets growing'},
  {t:'PM',   c:'Philip Morris International',sec:'Staples',      mc:'$210B',  sig:'buy',   thesis:'IQOS heated tobacco smoke-free transformation. Int\'l markets only. Dividend 4.5%'},
  {t:'MDLZ', c:'Mondelez International',     sec:'Staples',      mc:'$80B',   sig:'hold',  thesis:'Oreo + Cadbury + Toblerone. Snacks brand portfolio + emerging market penetration'},
  {t:'CL',   c:'Colgate-Palmolive',          sec:'Staples',      mc:'$67B',   sig:'hold',  thesis:'Oral care 40%+ global market share. Premium pricing power. Dividend 2.5%'},
  {t:'KMB',  c:'Kimberly-Clark',             sec:'Staples',      mc:'$43B',   sig:'hold',  thesis:'Kleenex + Huggies — household staples. Defensive dividend 3.6%'},
  // Energy
  {t:'XOM',  c:'Exxon Mobil',               sec:'Energy',        mc:'$520B',  sig:'buy',   thesis:'Pioneer acquisition เพิ่ม Permian. Low-cost operator. Dividend 3.4% + buyback $20B/yr'},
  {t:'CVX',  c:'Chevron Corp',              sec:'Energy',        mc:'$285B',  sig:'buy',   thesis:'Hess acquisition (Guyana oil). FCF $15B+/yr. Dividend 4.5% ต่อเนื่อง 37 ปี'},
  {t:'COP',  c:'ConocoPhillips',            sec:'Energy',        mc:'$155B',  sig:'buy',   thesis:'Marathon Oil acquisition. Permian + Bakken + LNG. Break-even $40/bbl ต่ำมาก'},
  {t:'OXY',  c:'Occidental Petroleum',      sec:'Energy',        mc:'$50B',   sig:'hold',  thesis:'Buffett backing 28% stake. Carbon capture DAC tech = ESG + energy play'},
  {t:'EOG',  c:'EOG Resources',             sec:'Energy',        mc:'$70B',   sig:'buy',   thesis:'Premium Permian + Eagle Ford. Break-even $30/bbl. Dividend + buyback program'},
  {t:'WMB',  c:'Williams Companies',        sec:'Energy',        mc:'$60B',   sig:'buy',   thesis:'Natural gas pipeline — AI data center power demand spike = gas demand secular bull'},
  {t:'LNG',  c:'Cheniere Energy',           sec:'Energy',        mc:'$45B',   sig:'buy',   thesis:'US LNG export leader. Long-term contracts กับ Europe/Asia post-Russia crisis'},
  {t:'SLB',  c:'SLB (Schlumberger)',        sec:'Energy',        mc:'$65B',   sig:'hold',  thesis:'Oil service leader. International drilling acceleration = earnings lever 2026'},
  // Industrials
  {t:'GE',   c:'GE Aerospace',              sec:'Industrials',   mc:'$230B',  sig:'buy',   thesis:'LEAP jet engine — 44,000 backlog units. Aerospace recovery + defense pure-play now'},
  {t:'RTX',  c:'RTX Corp (Raytheon)',        sec:'Industrials',   mc:'$175B',  sig:'buy',   thesis:'Pratt & Whitney + Raytheon missiles. Ukraine war demand. Backlog $220B record'},
  {t:'LMT',  c:'Lockheed Martin',           sec:'Industrials',   mc:'$120B',  sig:'buy',   thesis:'F-35 program 3,000+ jets backlog. Missile defense = critical NATO spend. Div 2.5%'},
  {t:'CAT',  c:'Caterpillar Inc',           sec:'Industrials',   mc:'$180B',  sig:'hold',  thesis:'Construction + mining equipment. Global infrastructure + AI data center building'},
  {t:'DE',   c:'Deere & Company',           sec:'Industrials',   mc:'$130B',  sig:'hold',  thesis:'Precision ag — John Deere autonomous tractor. JDLink connectivity platform moat'},
  {t:'HON',  c:'Honeywell International',   sec:'Industrials',   mc:'$135B',  sig:'buy',   thesis:'Defense + Space backlog $37B+. Corporate separation catalyst Q3 2026 = unlock'},
  {t:'ETN',  c:'Eaton Corp',                sec:'Industrials',   mc:'$130B',  sig:'buy',   thesis:'Electrical infrastructure — AI data center power distribution. Record backlog'},
  {t:'UPS',  c:'United Parcel Service',     sec:'Industrials',   mc:'$100B',  sig:'hold',  thesis:'Logistics king. Dividend 5% แต่ volume declining ใน US. Amazon disruption risk'},
  {t:'BA',   c:'Boeing Co',                 sec:'Industrials',   mc:'$140B',  sig:'watch', thesis:'Turnaround — 737 MAX + 787 rate recovery. Backlog $500B+ แต่ execution risk สูง'},
  {t:'CARR', c:'Carrier Global',            sec:'Industrials',   mc:'$65B',   sig:'hold',  thesis:'HVAC + fire safety. Viessmann acquisition เพิ่ม Europe heat pump exposure'},
  // Communication Services
  {t:'NFLX', c:'Netflix Inc',               sec:'Communication', mc:'$490B',  sig:'buy',   thesis:'Ad-supported tier 70M users. Password crackdown = revenue surge. Global content moat'},
  {t:'DIS',  c:'Walt Disney Co',            sec:'Communication', mc:'$200B',  sig:'buy',   thesis:'Streaming profitable. Parks + Experiences cash cow. IP moat = incomparable brand'},
  {t:'CMCSA',c:'Comcast Corp',              sec:'Communication', mc:'$145B',  sig:'hold',  thesis:'SpinCo cable separation coming. Broadband monopoly in service areas. PE 8x cheap'},
  {t:'VZ',   c:'Verizon Communications',    sec:'Communication', mc:'$165B',  sig:'hold',  thesis:'Frontier acquisition. Dividend 6.5% income play. Wireless ARPU growth slow'},
  {t:'T',    c:'AT&T Inc',                  sec:'Communication', mc:'$165B',  sig:'hold',  thesis:'Debt reduction ongoing. Fiber broadband growth. Dividend 5% post-WarnerMedia cut'},
  {t:'TMUS', c:'T-Mobile US',               sec:'Communication', mc:'$300B',  sig:'buy',   thesis:'5G market share gaining. US Cellular merger + Starlink partnership. Subscriber growth'},
  // Materials
  {t:'LIN',  c:'Linde PLC',                 sec:'Materials',     mc:'$210B',  sig:'buy',   thesis:'Industrial gas duopoly กับ Air Products. Clean hydrogen infrastructure investment'},
  {t:'APD',  c:'Air Products & Chemicals',  sec:'Materials',     mc:'$55B',   sig:'hold',  thesis:'Hydrogen economy bet ใหญ่. CEO changes ทำ capital allocation ชัดขึ้น'},
  {t:'NEM',  c:'Newmont Corp',              sec:'Materials',     mc:'$55B',   sig:'hold',  thesis:'Largest gold miner. ราคาทอง $4,000+ = earnings leverage. Newcrest acquisition cost'},
  {t:'FCX',  c:'Freeport-McMoRan',          sec:'Materials',     mc:'$55B',   sig:'buy',   thesis:'Copper king — EV + grid + AI data center = copper demand secular bull thesis'},
  {t:'SHW',  c:'Sherwin-Williams',          sec:'Materials',     mc:'$90B',   sig:'hold',  thesis:'Paint market leader. Proven pricing power. Housing remodel recovery beneficiary'},
  // REIT
  {t:'AMT',  c:'American Tower Corp',       sec:'REIT',          mc:'$90B',   sig:'buy',   thesis:'Cell tower landlord — 5G buildout = more equipment per tower. 100K+ towers global'},
  {t:'PLD',  c:'Prologis Inc',              sec:'REIT',          mc:'$100B',  sig:'buy',   thesis:'Logistics warehouse king. E-commerce + nearshoring = occupancy near 100%'},
  {t:'EQIX', c:'Equinix Inc',               sec:'REIT',          mc:'$75B',   sig:'buy',   thesis:'Data center REIT — AI workloads = capacity constraint. 250+ IBX data centers global'},
  {t:'O',    c:'Realty Income Corp',        sec:'REIT',          mc:'$50B',   sig:'buy',   thesis:'Monthly dividend 62 consecutive years. 15,400+ properties. Yield 5.5%'},
  {t:'SPG',  c:'Simon Property Group',      sec:'REIT',          mc:'$65B',   sig:'hold',  thesis:'Premium mall operator — outlet centers resilient. Saks-Neiman merger landlord'},
  // Utilities
  {t:'NEE',  c:'NextEra Energy',            sec:'Utilities',     mc:'$145B',  sig:'buy',   thesis:'Largest US utility + largest renewable. Florida Power & Light monopoly + wind/solar'},
  {t:'DUK',  c:'Duke Energy',               sec:'Utilities',     mc:'$90B',   sig:'hold',  thesis:'Southeast/Midwest utility monopoly. Grid modernization $75B capex plan'},
  {t:'SO',   c:'Southern Company',          sec:'Utilities',     mc:'$90B',   sig:'hold',  thesis:'Vogtle nuclear complete. Rate base expansion + AI power demand Southeast US'},
  {t:'D',    c:'Dominion Energy',           sec:'Utilities',     mc:'$44B',   sig:'hold',  thesis:'Virginia utility — data center corridor. Amazon/Google hyperscaler power demand'},
  {t:'XEL',  c:'Xcel Energy',               sec:'Utilities',     mc:'$37B',   sig:'hold',  thesis:'Renewables leader among utilities. Colorado/Minnesota solar + wind build-out'},
];

// Normalize SP500 for chart modal reuse
const SP500_MAP = {};
const SIG_CLS   = {buy:'sig-buy', hold:'sig-hold', watch:'sig-watch'};
const SIG_LABEL = {buy:'BUY', hold:'HOLD', watch:'WATCH'};
SP500.forEach(s => {
  s.th   = s.sec;   // chart modal uses .th for badge
  s.up   = null;    // no upside %, show mc instead
  s.risk = null;
  SP500_MAP[s.t] = s;
  GEMS_BY_TICKER[s.t] = s;  // unified lookup
});

let activeSec = 'ALL';
function renderSP500(sec) {
  activeSec = sec;
  document.querySelectorAll('#spFilters .gf').forEach(b => b.classList.toggle('on', b.dataset.th === sec));
  const list = sec === 'ALL' ? SP500 : SP500.filter(s => s.sec === sec);
  document.getElementById('spCount').textContent = list.length + ' หุ้น';
  document.getElementById('spGrid').innerHTML = list.map(s => {
    const col = THEME_COLORS[s.sec] || '#64748b';
    return `<div class="gem-card" style="border-left:3px solid ${col};cursor:pointer" onclick="openGemChart('${s.t}')">
      <div class="gem-top">
        <span class="gem-ticker" style="color:${col}">${s.t}</span>
        <span class="gem-badge" style="background:${col}20;color:${col}">${s.sec}</span>
      </div>
      <div style="display:flex;align-items:center;gap:6px;margin-top:1px">
        <span class="gem-company">${s.c}</span>
        <span class="sp-mc">${s.mc}</span>
      </div>
      <div class="gem-thesis">${s.thesis}</div>
      <div class="gem-footer">
        <span class="${SIG_CLS[s.sig]}">${SIG_LABEL[s.sig]}</span>
        <span style="font-size:10px;color:var(--muted)">&#x1F4C8; ดูกราฟ</span>
      </div>
    </div>`;
  }).join('');
}

// Build SP500 filter buttons
(function(){
  const secs = ['ALL','Tech','Healthcare','Financials','Consumer','Staples','Energy','Industrials','Communication','Materials','REIT','Utilities'];
  const icons = {ALL:'✦',Tech:'💻',Healthcare:'🏥',Financials:'🏦',Consumer:'🛍️',Staples:'🌾',Energy:'⚡',Industrials:'🏭',Communication:'📡',Materials:'⚗️',REIT:'🏗️',Utilities:'💡'};
  const el = document.getElementById('spFilters');
  secs.forEach(sec => {
    const b = document.createElement('button');
    b.className = 'gf' + (sec === 'ALL' ? ' on' : '');
    b.dataset.th = sec;
    b.textContent = (icons[sec] || '') + ' ' + (sec === 'ALL' ? 'ทั้งหมด' : sec);
    b.onclick = () => renderSP500(sec);
    el.appendChild(b);
  });
})();

// Build filter buttons
(function(){
  const themes = ['ALL','AI','Defense','Space','Energy','Biotech','Cyber','Industrial','Staples','REIT','Fintech','Auto','Chemical','Health','Value'];
  const icons  = {ALL:'✦',AI:'🤖',Defense:'🛡️',Space:'🚀',Energy:'⚡',Biotech:'🧬',Cyber:'🔐',Industrial:'🏭',Staples:'🌾',REIT:'🏗️',Fintech:'💳',Auto:'🚗',Chemical:'⚗️',Health:'❤️',Value:'💎'};
  const el = document.getElementById('gemFilters');
  themes.forEach(th => {
    const b = document.createElement('button');
    b.className = 'gf' + (th==='ALL'?' on':'');
    b.dataset.th = th;
    b.textContent = (icons[th]||'') + ' ' + (th==='ALL'?'ทั้งหมด':th);
    b.onclick = () => renderGems(th);
    el.appendChild(b);
  });
})();

// ── Gem Chart (TradingView) ──
let _tvReady = false;
function _loadTV(cb) {
  if (window.TradingView) { cb(); return; }
  if (_tvReady) { const t = setInterval(() => { if (window.TradingView) { clearInterval(t); cb(); } }, 120); return; }
  _tvReady = true;
  const s = document.createElement('script');
  s.src = 'https://s3.tradingview.com/tv.js';
  s.onload = cb;
  document.head.appendChild(s);
}

function openGemChart(ticker) {
  const g = GEMS_BY_TICKER[ticker] || TOP10.find(p => p.t === ticker);
  if (!g) return;
  const col = THEME_COLORS[g.th] || '#64748b';
  document.getElementById('gcTicker').textContent   = g.t;
  document.getElementById('gcTicker').style.color   = col;
  document.getElementById('gcCompany').textContent  = g.c;
  const upEl = document.getElementById('gcUpside');
  upEl.textContent = g.up != null ? '+' + g.up + '% upside' : (g.mc ? 'Market Cap: ' + g.mc : '');
  const rEl = document.getElementById('gcRisk');
  if (g.sig) { rEl.textContent = SIG_LABEL[g.sig]; rEl.className = SIG_CLS[g.sig]; }
  else if (g.risk) { rEl.textContent = RISK_LABEL[g.risk]; rEl.className = 'gem-risk ' + RISK_CLS[g.risk]; }
  else { rEl.textContent = ''; rEl.className = ''; }
  const thEl = document.getElementById('gcTheme');
  thEl.textContent = g.th; thEl.style.background = col+'20'; thEl.style.color = col;
  document.getElementById('gcThesis').textContent   = g.thesis;
  document.getElementById('gcYfLink').href = 'https://finance.yahoo.com/chart/' + g.t;
  document.getElementById('gcTvLink').href = 'https://www.tradingview.com/chart/?symbol=' + g.t;
  document.getElementById('gcContainer').innerHTML  = '<div class="gc-loading">&#x23F3; กำลังโหลดกราฟ...</div>';
  const ov = document.getElementById('gcOverlay');
  ov.classList.add('open');
  document.body.style.overflow = 'hidden';
  _loadTV(() => {
    const cid = 'tv_gc_' + Date.now();
    document.getElementById('gcContainer').innerHTML = '<div id="' + cid + '"></div>';
    new TradingView.widget({
      container_id: cid,
      symbol: g.t,
      interval: 'D',
      timezone: 'America/New_York',
      theme: 'dark',
      style: '1',
      locale: 'en',
      toolbar_bg: '#0d1117',
      width: '100%',
      height: 460,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      enable_publishing: false,
      studies: ['RSI@tv-basicstudies', 'MASimple@tv-basicstudies'],
      overrides: { 'paneProperties.background': '#0d1117', 'paneProperties.backgroundType': 'solid' },
    });
  });
}

function closeGemChart() {
  document.getElementById('gcOverlay').classList.remove('open');
  document.body.style.overflow = '';
}
function gcBgClick(e) { if (e.target === document.getElementById('gcOverlay')) closeGemChart(); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeGemChart(); closeModal(); } });

function closeModal() {
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
  if (modalChart) { modalChart.destroy(); modalChart = null; }
  currentStock = null;
}
function closeIfBg(e) { if (e.target === document.getElementById('overlay')) closeModal(); }

// ── Vault Renderer ──────────────────────────────────────────────────────────
function renderVault() {
  const picks  = D.vault_picks || [];
  const all    = D.vault_all   || [];
  const today  = D.date || '';

  // Subtitle
  document.getElementById('vaultSubtitle').textContent =
    `ArtheeNoi เลือกวันนี้ (${today}): ${picks.length} ตัว | คลังทั้งหมด: ${all.length} ตัว`;

  // ── Picks grid ──
  const actionColor = {BUY:'#4ade80',WATCH:'#facc15',NEUTRAL:'#94a3b8',WAIT:'#f97316',AVOID:'#f87171'};
  const pg = document.getElementById('vaultPicksGrid');
  if (!picks.length) {
    pg.innerHTML = '<p style="opacity:.5;padding:16px">ยังไม่มีข้อมูล vault picks วันนี้ (รัน bat ใหม่)</p>';
  } else {
    pg.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px">'
      + picks.map(s => {
        const col   = actionColor[s.action] || '#94a3b8';
        const stars = '★'.repeat(s.stars||0) + '☆'.repeat(3-(s.stars||0));
        const rsi   = s.rsi != null ? s.rsi.toFixed(1) : '—';
        const chgSign = (s.chg||0) >= 0 ? '+' : '';
        return `<div onclick="openModal('${s.sym}')" style="background:#1a1a2e;border:1px solid #333;border-left:3px solid ${col};border-radius:8px;padding:10px;cursor:pointer">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:700;font-size:.95em">${s.sym}</span>
            <span style="font-size:.7em;color:${col};font-weight:600">${s.action}</span>
          </div>
          <div style="font-size:.7em;opacity:.6;margin:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.name||''}</div>
          <div style="font-size:.9em;font-weight:600">$${(s.price||0).toFixed(2)}</div>
          <div style="font-size:.75em;color:${(s.chg||0)>=0?'#4ade80':'#f87171'}">${chgSign}${(s.chg||0).toFixed(2)}%</div>
          <div style="font-size:.72em;opacity:.7;margin-top:4px">RSI ${rsi} &nbsp;${stars}</div>
        </div>`;
      }).join('') + '</div>';
  }

  // ── Populate sector filter ──
  const sectors = [...new Set(all.map(e => e.s))].sort();
  const sel = document.getElementById('vaultSector');
  sel.innerHTML = '<option value="">ทุก Sector</option>'
    + sectors.map(s => `<option value="${s}">${s}</option>`).join('');

  filterVault();
}

function filterVault() {
  const all    = D.vault_all || [];
  const q      = (document.getElementById('vaultSearch')?.value || '').toUpperCase();
  const sector = document.getElementById('vaultSector')?.value || '';
  const tier   = document.getElementById('vaultTier')?.value   || '';

  const filtered = all.filter(e => {
    if (sector && e.s !== sector) return false;
    if (tier   && String(e.tier) !== tier) return false;
    if (q && !e.t.includes(q) && !e.c.toUpperCase().includes(q) && !e.note.toUpperCase().includes(q) && !e.s.toUpperCase().includes(q)) return false;
    return true;
  });

  document.getElementById('vaultCount').textContent = `แสดง ${filtered.length} ตัว`;

  const tierLabel  = {1:'T1',2:'T2',3:'T3'};
  const tierColor  = {1:'#4ade80',2:'#facc15',3:'#f97316'};
  const html = `<table style="width:100%;border-collapse:collapse;font-size:.8em">
    <thead><tr style="background:#111;text-align:left">
      <th style="padding:6px 8px">Ticker</th>
      <th style="padding:6px 8px">บริษัท</th>
      <th style="padding:6px 8px">Sector</th>
      <th style="padding:6px 8px">Tier</th>
      <th style="padding:6px 8px">Theme</th>
    </tr></thead>
    <tbody>${filtered.map((e,i) => `
      <tr style="background:${i%2?'#0d0d0d':'#161616'};cursor:pointer" onclick="openModal('${e.t}')">
        <td style="padding:5px 8px;font-weight:700;color:#7dd3fc">${e.t}</td>
        <td style="padding:5px 8px;opacity:.85">${e.c}</td>
        <td style="padding:5px 8px;opacity:.65">${e.s}</td>
        <td style="padding:5px 8px"><span style="color:${tierColor[e.tier]||'#94a3b8'};font-weight:600">${tierLabel[e.tier]||'—'}</span></td>
        <td style="padding:5px 8px;opacity:.55;font-size:.85em">${e.note}</td>
      </tr>`).join('')}
    </tbody></table>`;
  document.getElementById('vaultAllTable').innerHTML = html;
}

// ── Tracker Renderer ─────────────────────────────────────────────────────────
function renderTracker() {
  var el = document.getElementById('trackerBody');
  if (!el) return;

  var T  = D.tracker || {};
  var ps = T.period_stats || {};
  var pp = T.paper || {};

  function fmtPct(v) {
    if (v == null) return '—';
    var s = v >= 0 ? '+' : '';
    var c = v >= 0 ? '#10b981' : '#ef4444';
    return '<span style="color:' + c + '">' + s + v.toFixed(1) + '%</span>';
  }
  function fmtThb(v) {
    if (v == null) return '—';
    return Math.round(v).toLocaleString() + ' THB';
  }

  var out = '';

  // ── Portfolio Summary cards ──
  var totalRet = pp.total_return_pct || 0;
  var retColor = totalRet >= 0 ? '#10b981' : '#ef4444';
  var cards = [
    ['เงินทุนเริ่มต้น', fmtThb(pp.capital_thb)],
    ['มูลค่าปัจจุบัน', '<b style="color:' + retColor + '">' + fmtThb(pp.current_val_thb) + '</b>'],
    ['ผลตอบแทนรวม',   '<b style="color:' + retColor + '">' + fmtPct(pp.total_return_pct) + '</b>'],
    ['Alpha vs QQQ',  pp.alpha != null ? fmtPct(pp.alpha) + ' vs QQQ' : '—'],
    ['เงินสด',        fmtThb(pp.cash_thb)],
    ['ไม้เปิดอยู่',  (pp.open_positions || 0) + ' ไม้'],
    ['เทรดปิดแล้ว',  (pp.closed_trades || 0) + ' ครั้ง'],
    ['Win Rate',      pp.win_rate_trades != null ? pp.win_rate_trades + '%' : '—'],
    ['เฉลี่ย/เทรด',  fmtPct(pp.avg_trade_pct)],
  ];
  out += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:24px">';
  for (var i = 0; i < cards.length; i++) {
    out += '<div style="background:#0f1623;border:1px solid #1c2a3a;border-radius:10px;padding:12px">';
    out += '<div style="font-size:11px;color:#64748b;margin-bottom:4px">' + cards[i][0] + '</div>';
    out += '<div style="font-size:14px;font-weight:700">' + cards[i][1] + '</div>';
    out += '</div>';
  }
  out += '</div>';

  // ── Accuracy table ──
  out += '<div class="sec-title" style="margin-bottom:10px">&#x1F4CA; ความแม่น Signal</div>';
  out += '<div style="overflow-x:auto;margin-bottom:24px"><table style="width:100%;border-collapse:collapse;font-size:13px">';
  out += '<thead><tr style="color:#64748b;border-bottom:1px solid #1c2a3a">';
  out += '<th style="text-align:left;padding:8px">Period</th><th>Count</th><th>Win Rate</th><th>Avg Return</th><th>Alpha QQQ</th><th>Best</th><th>Worst</th>';
  out += '</tr></thead><tbody>';
  var periods = ['5d','10d','20d'];
  for (var pi = 0; pi < periods.length; pi++) {
    var p = periods[pi];
    var s = ps[p];
    if (!s) {
      out += '<tr><td style="padding:8px;color:#d97757;font-weight:700">' + p + '</td>';
      out += '<td colspan="6" style="color:#64748b;text-align:center;padding:8px">ยังไม่มีข้อมูล — ต้องรอให้ครบ ' + p + '</td></tr>';
    } else {
      var wc = s.win_rate >= 60 ? '#10b981' : s.win_rate >= 50 ? '#f59e0b' : '#ef4444';
      out += '<tr style="border-bottom:1px solid #1c2a3a">';
      out += '<td style="padding:8px;font-weight:700;color:#d97757">' + p + '</td>';
      out += '<td style="text-align:center">' + s.count + '</td>';
      out += '<td style="text-align:center;color:' + wc + ';font-weight:700">' + s.win_rate + '%</td>';
      out += '<td style="text-align:center">' + fmtPct(s.avg_return) + '</td>';
      out += '<td style="text-align:center">' + (s.avg_alpha != null ? fmtPct(s.avg_alpha) : '—') + '</td>';
      out += '<td style="text-align:center;color:#10b981">+' + s.best + '%</td>';
      out += '<td style="text-align:center;color:#ef4444">' + s.worst + '%</td>';
      out += '</tr>';
    }
  }
  out += '</tbody></table></div>';

  // ── Open Positions ──
  var openPos = pp.open_pos || [];
  if (openPos.length > 0) {
    out += '<div class="sec-title" style="margin-bottom:10px">&#x1F4BC; ไม้ที่ถือปัจจุบัน (' + openPos.length + ' ไม้)</div>';
    out += '<div style="overflow-x:auto;margin-bottom:24px"><table style="width:100%;border-collapse:collapse;font-size:13px">';
    out += '<thead><tr style="color:#64748b;border-bottom:1px solid #1c2a3a">';
    out += '<th style="text-align:left;padding:8px">Ticker</th>';
    out += '<th>วันที่เปิด</th><th>ราคาเปิด</th><th>ราคาปัจจุบัน</th>';
    out += '<th>กำไร/ขาดทุน (THB)</th><th>Return %</th><th>ถือมา</th><th>AI</th>';
    out += '</tr></thead><tbody>';
    for (var oi = 0; oi < openPos.length; oi++) {
      var pos = openPos[oi];
      var hasUnreal = pos.unreal_pct != null;
      var uc = hasUnreal ? (pos.unreal_pct >= 0 ? '#10b981' : '#ef4444') : '#64748b';
      var uSign = hasUnreal ? (pos.unreal_pct >= 0 ? '+' : '') : '';
      var uThb  = hasUnreal ? (pos.unreal_thb >= 0 ? '+' : '') + Math.round(pos.unreal_thb) + ' THB' : '—';
      var uPct  = hasUnreal ? uSign + pos.unreal_pct.toFixed(1) + '%' : '—';
      var curP  = pos.price_current ? '$' + pos.price_current : '—';
      var daysH = pos.days_held != null ? pos.days_held + 'd' : '—';
      out += '<tr style="border-bottom:1px solid #1c2a3a">';
      out += '<td style="padding:8px;font-weight:700;color:#d97757">' + pos.ticker + '</td>';
      out += '<td style="text-align:center">' + pos.open_date + '</td>';
      out += '<td style="text-align:center">$' + pos.price_open + '</td>';
      out += '<td style="text-align:center">' + curP + '</td>';
      out += '<td style="text-align:center;font-weight:700;color:' + uc + '">' + uThb + '</td>';
      out += '<td style="text-align:center;font-weight:700;color:' + uc + '">' + uPct + '</td>';
      out += '<td style="text-align:center;color:#64748b">' + daysH + '</td>';
      out += '<td style="text-align:center">' + (pos.ai_score || '—') + '</td>';
      out += '</tr>';
    }
    out += '</tbody></table></div>';
  }

  // ── Closed Trades ──
  var trades = pp.recent_trades || [];
  if (trades.length > 0) {
    out += '<div class="sec-title" style="margin-bottom:10px">&#x1F4CB; เทรดที่ปิดแล้ว</div>';
    out += '<div style="overflow-x:auto;margin-bottom:24px"><table style="width:100%;border-collapse:collapse;font-size:13px">';
    out += '<thead><tr style="color:#64748b;border-bottom:1px solid #1c2a3a">';
    out += '<th style="text-align:left;padding:8px">Ticker</th><th>เปิด</th><th>ปิด</th><th>ราคาเปิด</th><th>ราคาปิด</th><th>P&L</th><th>Return</th></tr></thead><tbody>';
    for (var ti = 0; ti < trades.length; ti++) {
      var t = trades[ti];
      var tc = t.pnl_pct >= 0 ? '#10b981' : '#ef4444';
      out += '<tr style="border-bottom:1px solid #1c2a3a">';
      out += '<td style="padding:8px;font-weight:700;color:#d97757">' + t.ticker + '</td>';
      out += '<td style="text-align:center">' + t.open_date + '</td>';
      out += '<td style="text-align:center">' + t.close_date + '</td>';
      out += '<td style="text-align:center">$' + t.price_open + '</td>';
      out += '<td style="text-align:center">$' + t.price_close + '</td>';
      out += '<td style="text-align:center;color:' + tc + ';font-weight:700">' + (t.pnl_thb >= 0 ? '+' : '') + Math.round(t.pnl_thb) + ' THB</td>';
      out += '<td style="text-align:center;color:' + tc + ';font-weight:700">' + (t.pnl_pct >= 0 ? '+' : '') + t.pnl_pct.toFixed(1) + '%</td>';
      out += '</tr>';
    }
    out += '</tbody></table></div>';
  }

  if (!T.total_signals) {
    out = '<p style="opacity:.5;padding:32px;text-align:center">ยังไม่มีข้อมูล — รัน Update Dashboard ก่อนครับ</p>';
  }

  el.innerHTML = out;
}

// ── Options Renderer ──────────────────────────────────────────────────────────
function renderOptions() {
  var el = document.getElementById('optionsBody');
  if (!el) return;

  var O   = D.options_stats || {};
  var pos = O.positions     || [];
  var trd = O.recent_trades || [];

  function fmtPct(v) {
    if (v == null) return '—';
    var c = v >= 0 ? '#10b981' : '#ef4444';
    var s = v >= 0 ? '+' : '';
    return '<span style="color:' + c + ';font-weight:700">' + s + v.toFixed(1) + '%</span>';
  }
  function fmtThb(v, bold) {
    if (v == null) return '—';
    var c = v >= 0 ? '#10b981' : '#ef4444';
    var s = v >= 0 ? '+' : '';
    var r = s + Math.round(v) + ' THB';
    return bold ? '<span style="color:' + c + ';font-weight:700">' + r + '</span>' : r;
  }
  function fmtUsd(v) { return v == null ? '—' : '$' + v.toFixed(2); }

  var out = '';

  // ── Summary cards ──
  var totalRet = O.total_return_pct || 0;
  var retColor = totalRet >= 0 ? '#10b981' : '#ef4444';
  var cards = [
    ['ทุน Options',      Math.round(O.capital_thb || 10000) + ' THB'],
    ['มูลค่าปัจจุบัน',  '<b style="color:' + retColor + '">' + Math.round(O.current_val_thb || 10000) + ' THB</b>'],
    ['ผลตอบแทนรวม',    '<b style="color:' + retColor + '">' + fmtPct(O.total_return_pct) + '</b>'],
    ['เงินสด',          Math.round(O.cash_thb || 0) + ' THB'],
    ['ไม้เปิดอยู่',     (O.open_positions || 0) + ' สัญญา'],
    ['เทรดปิดแล้ว',    (O.closed_trades || 0) + ' ครั้ง'],
    ['Win Rate',        O.win_rate != null ? O.win_rate + '%' : '—'],
    ['เฉลี่ย/เทรด',    O.avg_pnl_thb != null ? fmtThb(O.avg_pnl_thb, true) : '—'],
  ];
  out += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:24px">';
  for (var i = 0; i < cards.length; i++) {
    out += '<div style="background:#0f1623;border:1px solid #1c2a3a;border-radius:10px;padding:12px">';
    out += '<div style="font-size:11px;color:#64748b;margin-bottom:4px">' + cards[i][0] + '</div>';
    out += '<div style="font-size:14px;font-weight:700">' + cards[i][1] + '</div></div>';
  }
  out += '</div>';

  // ── Open positions ──
  if (pos.length > 0) {
    out += '<div class="sec-title" style="margin-bottom:10px">&#x1F4BC; สัญญาที่เปิดอยู่ (' + pos.length + ')</div>';
    out += '<div style="overflow-x:auto;margin-bottom:24px"><table style="width:100%;border-collapse:collapse;font-size:12px">';
    out += '<thead><tr style="color:#64748b;border-bottom:1px solid #1c2a3a">';
    out += '<th style="text-align:left;padding:8px">Ticker</th>';
    out += '<th>Type</th><th>Strike</th><th>Expiry</th><th>เหลือ</th>';
    out += '<th>Premium เปิด</th><th>Premium ตอนนี้</th>';
    out += '<th>P&L (THB)</th><th>Return</th>';
    out += '<th>Delta</th><th>Theta/วัน</th><th>AI</th>';
    out += '</tr></thead><tbody>';
    for (var oi = 0; oi < pos.length; oi++) {
      var p   = pos[oi];
      var uc  = (p.unreal_pct || 0) >= 0 ? '#10b981' : '#ef4444';
      var daysLeft = p.days_left != null ? p.days_left + 'd' : '—';
      out += '<tr style="border-bottom:1px solid #1c2a3a">';
      out += '<td style="padding:8px;font-weight:700;color:#d97757">' + p.ticker + '</td>';
      out += '<td style="text-align:center;color:#3b82f6;font-weight:700">' + (p.type || 'call').toUpperCase() + '</td>';
      out += '<td style="text-align:center">$' + (p.strike || '—') + '</td>';
      out += '<td style="text-align:center">' + (p.expiry || '—') + '</td>';
      out += '<td style="text-align:center;color:' + (p.days_left <= 5 ? '#ef4444' : '#64748b') + '">' + daysLeft + '</td>';
      out += '<td style="text-align:center">' + fmtUsd(p.premium_open) + '</td>';
      out += '<td style="text-align:center">' + fmtUsd(p.premium_current) + '</td>';
      out += '<td style="text-align:center;color:' + uc + ';font-weight:700">' + (p.unreal_thb >= 0 ? '+' : '') + Math.round(p.unreal_thb || 0) + ' THB</td>';
      out += '<td style="text-align:center">' + fmtPct(p.unreal_pct) + '</td>';
      out += '<td style="text-align:center;color:#a855f7">' + (p.delta != null ? p.delta.toFixed(2) : '—') + '</td>';
      out += '<td style="text-align:center;color:#ef4444">' + (p.theta != null ? p.theta.toFixed(2) : '—') + '</td>';
      out += '<td style="text-align:center">' + (p.ai_score || '—') + '</td>';
      out += '</tr>';
    }
    out += '</tbody></table></div>';
  }

  // ── Closed trades ──
  if (trd.length > 0) {
    out += '<div class="sec-title" style="margin-bottom:10px">&#x1F4CB; เทรดที่ปิดแล้ว</div>';
    out += '<div style="overflow-x:auto;margin-bottom:24px"><table style="width:100%;border-collapse:collapse;font-size:12px">';
    out += '<thead><tr style="color:#64748b;border-bottom:1px solid #1c2a3a">';
    out += '<th style="text-align:left;padding:8px">Ticker</th><th>Type</th><th>Strike</th>';
    out += '<th>เปิด</th><th>ปิด</th><th>เหตุผลปิด</th><th>P&L (THB)</th><th>Return</th>';
    out += '</tr></thead><tbody>';
    var reasonTh = {expired:'หมดอายุ', stop_loss:'Stop Loss', take_profit:'Take Profit'};
    for (var ti = 0; ti < trd.length; ti++) {
      var t  = trd[ti];
      var tc = (t.pnl_thb || 0) >= 0 ? '#10b981' : '#ef4444';
      var rLabel = reasonTh[t.close_reason] || t.close_reason || '—';
      out += '<tr style="border-bottom:1px solid #1c2a3a">';
      out += '<td style="padding:8px;font-weight:700;color:#d97757">' + t.ticker + '</td>';
      out += '<td style="text-align:center;color:#3b82f6">' + (t.type || 'CALL').toUpperCase() + '</td>';
      out += '<td style="text-align:center">$' + (t.strike || '—') + '</td>';
      out += '<td style="text-align:center">' + (t.open_date || '—') + '</td>';
      out += '<td style="text-align:center">' + (t.close_date || '—') + '</td>';
      out += '<td style="text-align:center;color:#f59e0b">' + rLabel + '</td>';
      out += '<td style="text-align:center;color:' + tc + ';font-weight:700">' + (t.pnl_thb >= 0 ? '+' : '') + Math.round(t.pnl_thb || 0) + ' THB</td>';
      out += '<td style="text-align:center">' + fmtPct(t.pnl_pct) + '</td>';
      out += '</tr>';
    }
    out += '</tbody></table></div>';
  }

  if (!O.capital_thb) {
    out = '<p style="opacity:.5;padding:32px;text-align:center">ยังไม่มีข้อมูล — รัน Update Dashboard ก่อนครับ</p>';
  }

  el.innerHTML = out;
}
</script>
</body>
</html>"""


# ─── Data Builder ─────────────────────────────────────────────────────────────

def _build_commodity_entry(d: dict, sym: str, name: str, category: str) -> dict:
    a = analyze(d)
    a["sym"]      = sym
    a["name"]     = name
    a["category"] = category
    a["closes30"] = d.get("closes30", [])
    a["dates30"]  = d.get("dates30", [])
    a["volume"]   = d.get("volume")
    a["news"]     = d.get("news", [])
    return a


def build_data(market_data: dict, all_syms: list, etf_syms: list,
               gold_sym: str, crypto_sym: str = None, *,
               vault_tickers: list = None, vault_all: list = None,
               macro: dict = None) -> dict:
    def q(sym):
        d = market_data.get(sym, {})
        return d if "error" not in d and d.get("price") else None

    tickers = []
    for s in etf_syms:
        d = q(s)
        if d: tickers.append({"sym": s, "price": d["price"], "chg": d.get("change_pct", 0)})
    gd = q(gold_sym)
    if gd: tickers.append({"sym": "GOLD", "price": gd["price"], "chg": gd.get("change_pct", 0)})
    bd = q(crypto_sym) if crypto_sym else None
    if bd: tickers.append({"sym": "BTC", "price": bd["price"], "chg": bd.get("change_pct", 0)})

    indices = []
    for s in etf_syms:
        d = q(s)
        if d: indices.append({"sym": s, "price": d["price"], "chg": d.get("change_pct", 0)})
    if gd: indices.append({"sym": "XAU", "price": gd["price"], "chg": gd.get("change_pct", 0)})
    if bd: indices.append({"sym": "BTC", "price": bd["price"], "chg": bd.get("change_pct", 0)})

    qqq_chg = (q("QQQ") or {}).get("change_pct", 0)
    mood    = market_summary(qqq_chg)

    # Try loading at_analysis for comprehensive scoring
    try:
        from at_analysis import ai_score_full as _ai_full
        _macro = macro or {}
    except ImportError:
        _ai_full = None
        _macro   = {}

    def _enrich(a: dict, d: dict, sector: str = "") -> dict:
        """Overlay ai_score_full() fields on top of simple analyze() result."""
        if not _ai_full:
            return a
        try:
            full = _ai_full(d, _macro, sector)
            a["ai_score"]   = full.get("ai_score", 50)
            a["ai_action"]  = full.get("action", a.get("action", "NEUTRAL"))
            a["ai_stars"]   = full.get("stars", a.get("stars", 0))
            a["ai_reason"]  = full.get("reason", "")
            # sub-scores
            tech  = full.get("technical", {})
            fund  = full.get("fundamental", {})
            mac_s = full.get("macro", {})
            sent  = full.get("sentiment", {})
            a["tech_score"]      = tech.get("score", 0)
            a["fund_score"]      = fund.get("score", 0)
            a["macro_score"]     = mac_s.get("score", 0)
            a["sentiment_score"] = sent.get("score", 0)
            # detailed indicators from technical
            sigs = tech.get("signals", {})
            a["macd_trend"]  = sigs.get("macd_trend", "")
            a["bb_squeeze"]  = sigs.get("bb_squeeze", False)
            a["ma_cross"]    = sigs.get("ma_cross", "")
            a["obv_signal"]  = sigs.get("obv_signal", "")
            a["momentum"]    = sigs.get("momentum")
            a["stoch_rsi"]   = sigs.get("stoch_rsi")
            # override action/stars only if ai_score is meaningful
            if full.get("ai_score", 0) > 0:
                a["action"] = full.get("action", a["action"])
                a["stars"]  = full.get("stars",  a["stars"])
                a["reason"] = full.get("reason", a["reason"]) or a["reason"]
        except Exception:
            pass
        return a

    stocks = []
    for sym in all_syms:
        d = q(sym)
        if not d: continue
        a = analyze(d)
        a["sym"]             = sym
        a["name"]            = d.get("name", sym)
        a["closes30"]        = d.get("closes30", [])
        a["dates30"]         = d.get("dates30", [])
        a["pe_ratio"]        = d.get("pe_ratio")
        a["forward_pe"]      = d.get("forward_pe")
        a["market_cap"]      = d.get("market_cap")
        a["volume"]          = d.get("volume")
        a["beta"]            = d.get("beta")
        a["analyst_target"]  = d.get("analyst_target")
        # Financials
        a["revenue_ttm"]     = d.get("revenue_ttm")
        a["net_income_ttm"]  = d.get("net_income_ttm")
        a["eps_ttm"]         = d.get("eps_ttm")
        a["profit_margin"]   = d.get("profit_margin")
        a["operating_margin"]= d.get("operating_margin")
        a["roe"]             = d.get("roe")
        a["revenue_growth"]  = d.get("revenue_growth")
        a["eps_growth"]      = d.get("eps_growth")
        a["free_cash_flow"]  = d.get("free_cash_flow")
        a["ma50"]            = d.get("ma50")
        a["ma200"]           = d.get("ma200")
        # Analyst recommendation counts
        a["strong_buy"]      = d.get("strong_buy")
        a["buy"]             = d.get("buy")
        a["hold"]            = d.get("hold")
        a["sell"]            = d.get("sell")
        a["strong_sell"]     = d.get("strong_sell")
        a["total_analysts"]  = d.get("total_analysts")
        # News headlines
        a["news"]            = d.get("news", [])
        # Short interest + earnings from Finviz enrichment
        a["short_float"]        = d.get("short_float")
        a["insider_own"]        = d.get("insider_own")
        a["debt_eq"]            = d.get("debt_eq")
        a["curr_ratio"]         = d.get("curr_ratio")
        a["div_yield"]          = d.get("div_yield")
        a["eps_q_q"]            = d.get("eps_q_q")
        a["earnings_days_away"] = d.get("earnings_days_away")
        a["earnings_date_str"]  = d.get("earnings_date_str")
        # Comprehensive AI score (Technical+Fundamental+Macro+Sentiment+Extra+RS)
        _enrich(a, d)
        # RS fields set by extra_score (written into d dict during ai_score_full)
        a["rs_sector"] = d.get("rs_sector")
        a["rs_qqq"]    = d.get("rs_qqq")
        a["rs_etf"]    = d.get("rs_etf")
        stocks.append(a)

    stocks.sort(key=lambda s: (
        {"BUY":0,"WATCH":1,"NEUTRAL":2,"WAIT":3,"AVOID":4}.get(s["action"],5),
        -s.get("stars",0), s.get("rsi") or 50
    ))

    daily_picks = find_daily_entries(stocks)

    # Commodity entries (gold + BTC) — added to stocks for modal access
    if gd:
        stocks.append(_build_commodity_entry(gd, gold_sym, "Gold", "gold"))
    if bd:
        stocks.append(_build_commodity_entry(bd, crypto_sym, "Bitcoin", "crypto"))

    # ── Vault picks (live data for today's ArtheeNoi picks) ──────────────────
    # build sector lookup from vault_all for enrich
    _vault_sector = {e["t"]: e.get("s", "") for e in (vault_all or [])}

    vault_picks_live = []
    if vault_tickers:
        for sym in vault_tickers:
            d = q(sym)
            if not d:
                continue
            a = analyze(d)
            a["sym"]      = sym
            a["name"]     = d.get("name", sym)
            a["closes30"] = d.get("closes30", [])
            a["dates30"]  = d.get("dates30", [])
            _enrich(a, d, _vault_sector.get(sym, ""))
            a["rs_sector"]          = d.get("rs_sector")
            a["rs_qqq"]             = d.get("rs_qqq")
            a["rs_etf"]             = d.get("rs_etf")
            a["short_float"]        = d.get("short_float")
            a["earnings_days_away"] = d.get("earnings_days_away")
            vault_picks_live.append(a)
        vault_picks_live.sort(key=lambda s: (
            {"BUY": 0, "WATCH": 1, "NEUTRAL": 2, "WAIT": 3, "AVOID": 4}.get(s["action"], 5),
            -(s.get("stars") or 0), -(s.get("ai_score") or 0)
        ))

    # Macro snapshot for dashboard display
    macro_snap = {}
    if _macro:
        macro_snap = {
            "fed_rate":    _macro.get("fed_rate"),
            "yield_curve": _macro.get("yield_curve"),
            "cpi":         _macro.get("cpi"),
            "unrate":      _macro.get("unrate"),
            "vix":         _macro.get("vix"),
            "dxy":         _macro.get("dxy"),
            "oil":         _macro.get("oil"),
            "gold_price":  _macro.get("gold_price"),
            "tnx":         _macro.get("tnx"),
            "regime":      _macro.get("regime"),
            "rate_env":    _macro.get("rate_env"),
            "risk_level":  _macro.get("risk_level"),
        }

    return {
        "date":          datetime.now().strftime("%Y-%m-%d"),
        "updated_at":    datetime.now().strftime("%H:%M:%S"),
        "tickers":       tickers,
        "indices":       indices,
        "market":        mood,
        "macro":         macro_snap,
        "stocks":        stocks,
        "daily_entries": daily_picks,
        "vault_picks":   vault_picks_live,
        "vault_all":     vault_all or [],
    }


def generate(market_data: dict, portfolio_rows: list, watchlist_syms: list,
             etf_syms: list, gold_sym: str, crypto_sym: str = None, *args, **kwargs):
    port_keys = [r['sym'] for r in (portfolio_rows or [])]
    all_syms  = port_keys + list(watchlist_syms or [])
    vault_tickers = kwargs.get("vault_tickers", [])
    vault_all     = kwargs.get("vault_all", [])
    macro         = kwargs.get("macro", None)
    tracker       = kwargs.get("tracker", {})
    options_stats = kwargs.get("options_stats", {})
    data = build_data(market_data, all_syms, etf_syms, gold_sym, crypto_sym,
                      vault_tickers=vault_tickers, vault_all=vault_all, macro=macro)
    data["tracker"]       = tracker
    data["options_stats"] = options_stats
    # args: total_pnl, total_pnl_thb, total_pnl_pct, total_val, THB_RATE
    if len(args) >= 5:
        data["thb_rate"] = round(args[4], 4)
    html = HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    out  = BASE_DIR / "wiki" / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    # mirror to root wiki/ (user opens from desktop shortcut)
    mirror = BASE_DIR.parent.parent / "wiki" / "dashboard.html"
    if mirror.parent.exists():
        mirror.write_text(html, encoding="utf-8")
    return out
