"""
artheenoi_agent.py — ArtheeNoi 24/7 Cloud Agent
รันเป็น background thread ใน dashboard_server.py

Tasks:
  - ทุก 1 ชั่วโมง: วิเคราะห์ตลาด + detect signal changes
  - เมื่อ signal เปลี่ยน: ส่ง Telegram alert ทันที
  - ตี 5:00 BKK: ส่ง daily summary
  - เก็บผลการวิเคราะห์ใน _agent_state (shared memory กับ web server)
"""
import os
import json
import time
import logging
import threading
import requests
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
log = logging.getLogger("ArtheeNoi.Agent")

# ─── Config ───────────────────────────────────────────────────────────────────

TG_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
OR_KEY        = os.environ.get("OPENROUTER_API_KEY", "")
OPENAI_MODEL  = "claude-haiku-4-5-20251001"
BKK           = timezone(timedelta(hours=7))
HOURLY_SEC    = 3600          # วิเคราะห์ทุก 1 ชั่วโมง
DAILY_HOUR    = 5             # Daily summary ตี 5 BKK
ALERT_COOLDOWN = 3600 * 2     # ห้าม alert ซ้ำใน 2 ชั่วโมง

BASE = Path(__file__).parent

# ─── Shared State (อ่านได้จาก dashboard_server.py) ───────────────────────────

_agent_state = {
    "running":        False,
    "last_analysis":  None,    # datetime ISO
    "last_summary":   None,    # ISO วันที่ส่ง daily
    "hourly_report":  "",      # ข้อความรายงานล่าสุด
    "signals":        {},      # {sym: {"rsi": 45, "bucket": "neutral", "alerted_at": ISO}}
    "alert_log":      [],      # [{ts, msg}] ล่าสุด 20 รายการ
    "error":          None,
}
_state_lock = threading.Lock()

def get_state() -> dict:
    with _state_lock:
        return dict(_agent_state)

def _set(key, val):
    with _state_lock:
        _agent_state[key] = val

# ─── Telegram ────────────────────────────────────────────────────────────────

def _tg_send(text: str) -> bool:
    """ส่งข้อความไปยัง Telegram. คืน True ถ้าสำเร็จ"""
    if not TG_TOKEN or not TG_CHAT_ID:
        log.warning("[Telegram] ยังไม่ตั้ง TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10, verify=False
        )
        ok = r.json().get("ok", False)
        if not ok:
            log.warning(f"[Telegram] API error: {r.text[:200]}")
        return ok
    except Exception as e:
        log.warning(f"[Telegram] send failed: {e}")
        return False

def _log_alert(msg: str):
    with _state_lock:
        _agent_state["alert_log"].append({
            "ts": _now_bkk().strftime("%H:%M"),
            "msg": msg[:120],
        })
        _agent_state["alert_log"] = _agent_state["alert_log"][-20:]

# ─── Time helpers ────────────────────────────────────────────────────────────

def _now_bkk() -> datetime:
    return datetime.now(BKK)

def _is_market_open() -> bool:
    """US market: อาทิตย์ 20:30 – ศุกร์ 03:00 BKK"""
    now  = _now_bkk()
    wd   = now.weekday()        # 0=Mon, 6=Sun
    hour = now.hour + now.minute / 60
    # ตลาดปิด: เสาร์ทั้งวัน + อาทิตย์ก่อน 20:30
    if wd == 5:
        return False
    if wd == 6 and hour < 20.5:
        return False
    return True

# ─── Market Data (ดึงด้วย yfinance) ─────────────────────────────────────────

def _fetch_snapshot(syms: list) -> dict:
    """ดึงราคา + RSI ทุก symbol ที่ต้องการ"""
    try:
        import yfinance as yf
        data = {}
        if not syms:
            return data
        tickers = yf.Tickers(" ".join(syms))
        for sym in syms:
            try:
                t = tickers.tickers.get(sym)
                if not t:
                    continue
                fi   = t.fast_info
                hist = t.history(period="30d", interval="1d")
                closes = hist["Close"].dropna().tolist()
                rsi  = _rsi(closes)
                data[sym] = {
                    "price": round(fi.last_price or 0, 4),
                    "chg":   round(((fi.last_price or 0) - (fi.previous_close or 1)) /
                                   (fi.previous_close or 1) * 100, 2),
                    "rsi":   rsi,
                    "high":  round(fi.year_high or 0, 2),
                    "low":   round(fi.year_low  or 0, 2),
                }
            except Exception:
                pass
        return data
    except ImportError:
        log.error("[Agent] yfinance ไม่มี — pip install yfinance")
        return {}

def _rsi(closes: list, n=14) -> float | None:
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag = sum(gains[-n:]) / n
    al = sum(losses[-n:]) / n
    return round(100 - 100 / (1 + ag / al), 1) if al else 100.0

def _rsi_bucket(rsi: float | None) -> str:
    if rsi is None: return "unknown"
    if rsi <= 30:   return "oversold"
    if rsi <= 45:   return "low"
    if rsi >= 75:   return "extreme_ob"
    if rsi >= 65:   return "overbought"
    return "neutral"

# ─── ArtheeNoi Intelligence (OpenRouter) ─────────────────────────────────────

_BRAIN = (BASE / "home" / "ArtheeNoiAI" / "arteenoi_system_prompt.txt")

def _get_system_prompt() -> str:
    if _BRAIN.exists():
        return _BRAIN.read_text(encoding="utf-8")
    return "You are ArtheeNoi, a professional stock/forex/crypto analyst. Answer in Thai."

def _ai_call(user_msg: str, max_tokens: int = 500) -> str:
    if not OR_KEY:
        return ""
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://artheenoi-dashboard.onrender.com"},
            json={"model": OPENAI_MODEL,
                  "max_tokens": max_tokens,
                  "system": _get_system_prompt(),
                  "messages": [{"role": "user", "content": user_msg}]},
            timeout=30, verify=False
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.warning(f"[AI] OpenRouter error: {e}")
        return ""

# ─── Signal Change Detection ──────────────────────────────────────────────────

def _check_signals(mkt: dict, users_fn) -> list:
    """
    ตรวจ signal เปลี่ยนแปลง คืน list ของ alert messages ที่ต้องส่ง
    users_fn = callable ที่คืน dict ของ user ทั้งหมด (ดึงจาก dashboard_server)
    """
    alerts = []
    now_iso = _now_bkk().isoformat()

    try:
        users = users_fn()
    except Exception:
        return alerts

    # รวม symbols ทุก user
    all_syms: set = set()
    for u in users.values():
        all_syms.update(u.get("portfolio", {}).keys())
        all_syms.update(u.get("watchlist", []))

    with _state_lock:
        prev_sigs = dict(_agent_state["signals"])

    new_sigs = dict(prev_sigs)

    for sym in all_syms:
        d = mkt.get(sym, {})
        if not d.get("price"):
            continue
        rsi    = d.get("rsi")
        bucket = _rsi_bucket(rsi)
        prev   = prev_sigs.get(sym, {})
        p_buck = prev.get("bucket", "unknown")
        alerted_at = prev.get("alerted_at")

        # cooldown check
        if alerted_at:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(alerted_at)).total_seconds()
                if elapsed < ALERT_COOLDOWN:
                    new_sigs[sym] = {**prev, "rsi": rsi, "bucket": bucket}
                    continue
            except Exception:
                pass

        # Signal transitions ที่น่าสนใจ
        alert_msg = None
        price = d["price"]
        chg   = d.get("chg", 0)

        if p_buck != "oversold" and bucket == "oversold":
            alert_msg = (f"🟢 <b>{sym}</b> เข้าโซน OVERSOLD\n"
                         f"RSI {rsi} | ราคา ${price:,.2f} ({chg:+.2f}%)\n"
                         f"💡 โซนซื้อสะสม — พิจารณา DCA")

        elif p_buck not in ("overbought","extreme_ob") and bucket in ("overbought","extreme_ob"):
            alert_msg = (f"🔴 <b>{sym}</b> เข้าโซน OVERBOUGHT\n"
                         f"RSI {rsi} | ราคา ${price:,.2f} ({chg:+.2f}%)\n"
                         f"⚠️ ระวัง pullback — พิจารณาลด position")

        elif p_buck in ("overbought","extreme_ob") and bucket == "neutral":
            alert_msg = (f"⚪ <b>{sym}</b> RSI ลงจาก overbought\n"
                         f"RSI {rsi} | ราคา ${price:,.2f}\n"
                         f"🔍 จับตาดูต่อ")

        elif p_buck == "oversold" and bucket == "low":
            alert_msg = (f"📈 <b>{sym}</b> RSI ฟื้นตัวจาก oversold\n"
                         f"RSI {rsi} | ราคา ${price:,.2f} ({chg:+.2f}%)\n"
                         f"✅ สัญญาณ buy ยืนยัน")

        # แจ้งเมื่อราคาลงแรง (>5% วันเดียว)
        if abs(chg) >= 5.0:
            icon = "📉" if chg < 0 else "📈"
            alert_msg = (f"{icon} <b>{sym}</b> ราคา {'ลด' if chg<0 else 'เพิ่ม'}แรง {chg:+.1f}%\n"
                         f"ราคา ${price:,.2f} | RSI {rsi or '—'}")

        new_sigs[sym] = {"rsi": rsi, "bucket": bucket,
                         "alerted_at": now_iso if alert_msg else alerted_at,
                         "price": price}

        if alert_msg:
            alerts.append(alert_msg)

    with _state_lock:
        _agent_state["signals"] = new_sigs

    return alerts

# ─── Hourly Analysis ──────────────────────────────────────────────────────────

def _hourly_analysis(mkt: dict) -> str:
    """สร้างรายงานรายชั่วโมงด้วย AI"""
    now    = _now_bkk()
    qqq    = mkt.get("QQQ",     {})
    gold   = mkt.get("GC=F",    {})
    btc    = mkt.get("BTC-USD", {})
    spy    = mkt.get("IVV",     {})

    prompt = f"""ตอนนี้ {now.strftime('%Y-%m-%d %H:%M')} BKK

ข้อมูลตลาดล่าสุด:
- QQQ (NASDAQ): ${qqq.get('price',0):,.2f} ({qqq.get('chg',0):+.2f}%) RSI={qqq.get('rsi','—')}
- IVV (S&P500): ${spy.get('price',0):,.2f} ({spy.get('chg',0):+.2f}%) RSI={spy.get('rsi','—')}
- Gold (XAU):   ${gold.get('price',0):,.2f} ({gold.get('chg',0):+.2f}%) RSI={gold.get('rsi','—')}
- BTC:          ${btc.get('price',0):,.0f} ({btc.get('chg',0):+.2f}%) RSI={btc.get('rsi','—')}

วิเคราะห์ตลาดสั้นๆ ภาษาไทย 3-4 bullet points:
1. อารมณ์ตลาดตอนนี้เป็นอย่างไร
2. asset ไหนน่าสนใจ/น่าระวัง
3. จุดระวังในชั่วโมงถัดไป
(ตอบกระชับ ใช้ emoji, เน้น actionable)"""

    text = _ai_call(prompt, 300)
    return text or _rule_analysis(mkt)

def _rule_analysis(mkt: dict) -> str:
    """fallback ถ้าไม่มี AI key"""
    qqq  = mkt.get("QQQ",     {})
    gold = mkt.get("GC=F",    {})
    btc  = mkt.get("BTC-USD", {})
    chg  = qqq.get("chg", 0)
    mood = "🟢 Bullish" if chg > 0.5 else "🔴 Bearish" if chg < -0.5 else "⚪ Neutral"
    return (f"{mood} — QQQ {chg:+.2f}%\n"
            f"• ทอง ${gold.get('price',0):,.0f} ({gold.get('chg',0):+.2f}%)\n"
            f"• BTC ${btc.get('price',0):,.0f} ({btc.get('chg',0):+.2f}%)")

# ─── Daily Summary (ตี 5 BKK) ─────────────────────────────────────────────────

def _daily_summary(mkt: dict, users_fn) -> str:
    """สร้าง daily summary รายงานสำหรับส่ง Telegram ตอนเช้า"""
    now = _now_bkk()
    try:
        users = users_fn()
    except Exception:
        users = {}

    # รวม portfolio ทุก user
    port_lines = []
    for uname, u in users.items():
        port = u.get("portfolio", {})
        for sym, info in port.items():
            d = mkt.get(sym, {})
            if not d.get("price"):
                continue
            cost = float(info.get("cost", 0))
            sh   = float(info.get("shares", 0))
            pnl  = (d["price"] - cost) / cost * 100 if cost else 0
            rsi  = d.get("rsi")
            port_lines.append(f"{sym}: ${d['price']:,.2f} | P&L {pnl:+.1f}% | RSI {rsi or '—'}")

    port_block = "\n".join(port_lines) if port_lines else "(ยังไม่มี portfolio)"

    qqq  = mkt.get("QQQ",     {})
    gold = mkt.get("GC=F",    {})
    btc  = mkt.get("BTC-USD", {})

    prompt = f"""เช้าวันใหม่ {now.strftime('%A %d %b %Y')} BKK

Portfolio สรุป:
{port_block}

ตลาดเมื่อวาน:
- QQQ: ${qqq.get('price',0):,.2f} ({qqq.get('chg',0):+.2f}%)
- Gold: ${gold.get('price',0):,.2f} ({gold.get('chg',0):+.2f}%)
- BTC: ${btc.get('price',0):,.0f} ({btc.get('chg',0):+.2f}%)

ทำ daily morning briefing ภาษาไทย สั้น กระชับ:
1. สรุป portfolio วานนี้
2. แผนวันนี้ 2-3 ข้อ (buy/hold/watch)
3. ปัจจัยเสี่ยงที่ต้องจับตา
4. Grand Master tip ประจำวัน
(ใช้ emoji, เน้น practical, ไม่เกิน 8 bullet points)"""

    text = _ai_call(prompt, 500)
    if not text:
        text = (f"☀️ Good Morning! {now.strftime('%d %b %Y')}\n"
                f"• QQQ: ${qqq.get('price',0):,.2f} ({qqq.get('chg',0):+.2f}%)\n"
                f"• Gold: ${gold.get('price',0):,.0f} | BTC: ${btc.get('price',0):,.0f}\n"
                f"• ตรวจ portfolio และ news ก่อนเทรดครับ")
    return text

# ─── Price Alerts (User-defined) ──────────────────────────────────────────────

def check_price_alerts(users_fn, mkt: dict):
    """
    ตรวจสอบ alert ที่ user ตั้งไว้กับราคาตลาดปัจจุบัน
    - เมื่อ alert triggered → ส่ง Telegram + mark triggered_at
    - คืน list of messages ที่ triggered
    """
    triggered_msgs = []
    try:
        from pathlib import Path
        import json as _json
        users_path = BASE / "dashboard_users.json"
        if not users_path.exists():
            return []
        with open(users_path, encoding="utf-8") as f:
            users = _json.load(f)
        changed = False
        for uname, user in users.items():
            alerts_list = user.get("alerts", [])
            for a in alerts_list:
                if not a.get("active") or a.get("triggered_at"):
                    continue
                sym = a.get("sym", "")
                d   = mkt.get(sym, {})
                if not d.get("price"):
                    continue
                cur_price = d["price"]
                chg       = d.get("chg", 0)
                target    = float(a.get("price", 0))
                cond      = a.get("condition", "above")
                hit = False
                if cond == "above" and cur_price >= target:
                    hit = True
                elif cond == "below" and cur_price <= target:
                    hit = True
                elif cond == "change_pct" and abs(chg) >= target:
                    hit = True
                if hit:
                    now_str = _now_bkk().strftime("%Y-%m-%d %H:%M")
                    a["triggered_at"] = now_str
                    a["active"] = False
                    changed = True
                    msg = (f"🔔 <b>Price Alert!</b> [{uname}]\n"
                           f"<b>{sym}</b> — {cond} ${target:,.2f}\n"
                           f"ราคาตอนนี้: ${cur_price:,.2f} ({chg:+.2f}%)\n"
                           f"Note: {a.get('note','') or '—'}\n"
                           f"⏰ {now_str} BKK")
                    triggered_msgs.append(msg)
                    log.info(f"[Alert] {uname}/{sym} triggered ({cond} {target})")
        if changed:
            with open(users_path, "w", encoding="utf-8") as f:
                _json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.warning(f"[PriceAlerts] error: {e}")
    return triggered_msgs


# ─── Main Agent Loop ──────────────────────────────────────────────────────────

def run_agent(users_fn, mkt_fn):
    """
    users_fn: callable() → dict of all users (จาก dashboard_server.load_users)
    mkt_fn:   callable() → market data dict (จาก _mkt_cache["data"])
    """
    _set("running", True)
    log.info("=" * 50)
    log.info("ArtheeNoi Agent เริ่มทำงาน 24/7")
    log.info(f"  Telegram: {'✅' if TG_TOKEN else '❌ (ไม่มี TOKEN)'}")
    log.info(f"  OpenRouter: {'✅' if OR_KEY else '❌ (rule-based mode)'}")
    log.info("=" * 50)

    # ส่ง startup notice
    if TG_TOKEN:
        _tg_send("🤖 <b>ArtheeNoi Agent เริ่มทำงานแล้ว</b>\n"
                 f"⏰ {_now_bkk().strftime('%Y-%m-%d %H:%M')} BKK\n"
                 f"📡 วิเคราะห์ตลาดทุก 1 ชั่วโมง\n"
                 f"🔔 Alert เมื่อ RSI/Signal เปลี่ยน\n"
                 f"☀️ Daily summary ตี 5:00 BKK")
        _log_alert("🤖 Agent started")

    last_hour_run  = 0.0
    last_daily_day = -1   # วันที่ส่ง daily summary ล่าสุด (day of month)

    while True:
        try:
            now      = _now_bkk()
            now_unix = time.time()

            mkt = mkt_fn() or {}

            # ── รายงานรายชั่วโมง ───────────────────────────────────────────
            if now_unix - last_hour_run >= HOURLY_SEC and mkt:
                log.info(f"[Agent] Hourly run at {now.strftime('%H:%M')}")

                # Signal change detection (RSI bucket changes)
                alerts = _check_signals(mkt, users_fn)
                for a in alerts:
                    if _tg_send(f"🔔 <b>ArtheeNoi Alert</b>\n{a}"):
                        log.info(f"[Telegram] Sent alert: {a[:50]}")
                    _log_alert(a[:80])

                # User-defined price alerts
                try:
                    price_alerts = check_price_alerts(users_fn, mkt)
                    for pa in price_alerts:
                        _tg_send(pa)
                        _log_alert(pa[:80])
                except Exception as _pe:
                    log.warning(f"[PriceAlerts] {_pe}")

                # AI analysis (เฉพาะช่วงตลาดเปิดหรือทุก 3 ชั่วโมง)
                if _is_market_open() or (int(now_unix / HOURLY_SEC) % 3 == 0):
                    report = _hourly_analysis(mkt)
                    _set("hourly_report", report)
                    _set("last_analysis", now.isoformat())
                    log.info(f"[Agent] Analysis done: {report[:60]}...")

                last_hour_run = now_unix

            # ── Daily summary ตี 5 BKK ─────────────────────────────────────
            if (now.hour == DAILY_HOUR and
                    now.minute < 10 and
                    now.day != last_daily_day and
                    mkt):
                log.info("[Agent] Sending daily summary...")
                summary = _daily_summary(mkt, users_fn)
                header  = (f"☀️ <b>ArtheeNoi Morning Brief</b>\n"
                           f"{now.strftime('%A %d %b %Y')} | ตี {DAILY_HOUR}:00 BKK\n"
                           f"{'─' * 30}\n")
                _tg_send(header + summary)
                _log_alert("☀️ Daily summary sent")
                _set("last_summary", now.isoformat())
                last_daily_day = now.day

            _set("error", None)

        except Exception as e:
            log.exception(f"[Agent] Loop error: {e}")
            _set("error", str(e))

        time.sleep(60)   # ตรวจทุก 1 นาที (ทำให้ daily check แม่นยำ ±10 นาที)

def start(users_fn, mkt_fn):
    """เริ่ม agent ใน daemon thread — เรียกจาก dashboard_server.py"""
    t = threading.Thread(
        target=run_agent,
        args=(users_fn, mkt_fn),
        daemon=True,
        name="ArtheeNoi-Agent",
    )
    t.start()
    log.info("[Agent] Thread started")
    return t
