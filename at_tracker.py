"""
at_tracker.py — Paper Trade Accuracy Tracker + Paper Portfolio
บันทึก BUY/WATCH signal ทุกวัน ติดตามผล 5/10/20 วัน vs QQQ
Paper Portfolio: จำลองเงินทุน เปิด/ปิดไม้ตาม signal จริง
"""
import json
from pathlib import Path
from datetime import datetime

BASE_DIR     = Path(__file__).parent
TRACKER_FILE = BASE_DIR / "wiki" / "signal_tracker.json"
MAX_SIGNALS  = 300

PAPER_CAPITAL_THB  = 10_000.0   # เงินทุนเริ่มต้น บาท
MAX_POSITIONS      = 10          # ถือหุ้นพร้อมกันสูงสุด
HOLD_DAYS          = 10          # ถือ 10 วันแล้วขาย (ถ้าไม่มี AVOID)
POSITION_SIZE_PCT  = 0.10        # ต่อไม้ 10% ของพอร์ต


# ── I/O ──────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "version":   2,
        "signals":   [],
        "portfolio": {
            "capital_thb":   PAPER_CAPITAL_THB,
            "cash_thb":      PAPER_CAPITAL_THB,
            "positions":     [],   # open positions
            "history":       [],   # closed trades
            "equity_curve":  [],   # [{date, value_thb}]
            "qqq_curve":     [],   # [{date, qqq_price}]  for benchmark
        },
    }

def _save(data: dict):
    TRACKER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Record accuracy signals ───────────────────────────────────────────────────

def record_signals(scored_stocks: list, market_data: dict,
                   qqq_price: float = None, thb_rate: float = 36.0) -> int:
    """
    บันทึก BUY/WATCH signal และเปิดไม้ paper portfolio
    scored_stocks = list of dicts: ticker/t, action, ai_score, stars, sector
    market_data   = {ticker: {price, ...}}
    qqq_price     = ราคา QQQ วันนี้ (USD)
    thb_rate      = อัตราแลกเปลี่ยน THB/USD
    """
    data  = _load()
    today = datetime.now().strftime("%Y-%m-%d")
    existing_today = {s["ticker"] for s in data["signals"] if s["date"] == today}
    port  = data["portfolio"]

    added = 0
    for s in scored_stocks:
        ticker = s.get("ticker") or s.get("t", "")
        action = s.get("action", "")
        if action not in ("BUY", "WATCH"):
            continue
        if not ticker or ticker in existing_today:
            continue
        price_usd = (market_data.get(ticker) or {}).get("price")
        if not price_usd:
            continue

        # ── Accuracy tracker entry ──
        data["signals"].append({
            "ticker":      ticker,
            "date":        today,
            "action":      action,
            "ai_score":    s.get("ai_score"),
            "stars":       s.get("stars"),
            "sector":      s.get("sector", s.get("s", "")),
            "price_entry": round(float(price_usd), 4),
            "qqq_entry":   round(float(qqq_price), 4) if qqq_price else None,
            "outcomes":    {},
            "status":      "open",
        })
        existing_today.add(ticker)
        added += 1

        # ── Paper Portfolio: เปิดไม้ถ้า BUY และมีที่ว่าง ──
        if action == "BUY":
            open_tickers = {p["ticker"] for p in port["positions"]}
            if ticker not in open_tickers and len(port["positions"]) < MAX_POSITIONS:
                alloc_thb  = port["cash_thb"] * POSITION_SIZE_PCT
                alloc_usd  = alloc_thb / thb_rate
                shares     = alloc_usd / float(price_usd)
                cost_thb   = shares * float(price_usd) * thb_rate
                if cost_thb > 0 and port["cash_thb"] >= cost_thb:
                    port["cash_thb"] -= cost_thb
                    port["positions"].append({
                        "ticker":      ticker,
                        "open_date":   today,
                        "shares":      round(shares, 6),
                        "price_open":  round(float(price_usd), 4),
                        "cost_thb":    round(cost_thb, 2),
                        "thb_rate":    round(thb_rate, 2),
                        "ai_score":    s.get("ai_score"),
                        "sector":      s.get("sector", s.get("s", "")),
                    })

    # ── ตัด signal เก่าสุด ──
    if len(data["signals"]) > MAX_SIGNALS:
        data["signals"] = data["signals"][-MAX_SIGNALS:]

    _save(data)
    return added


# ── Update outcomes + close paper positions ───────────────────────────────────

def update_outcomes(market_data: dict, qqq_price: float = None, thb_rate: float = 36.0):
    """
    อัปเดตผล accuracy + ปิดไม้ paper portfolio ที่ครบ HOLD_DAYS
    """
    data     = _load()
    today    = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    port     = data["portfolio"]

    # ── Accuracy outcomes ──
    for sig in data["signals"]:
        if sig["status"] == "closed":
            continue
        try:
            entry_date   = datetime.strptime(sig["date"], "%Y-%m-%d")
            days_elapsed = (today - entry_date).days
        except Exception:
            continue

        ticker        = sig["ticker"]
        current_price = (market_data.get(ticker) or {}).get("price")
        if not current_price:
            continue

        entry_p = sig["price_entry"]
        for period in [5, 10, 20]:
            key = f"{period}d"
            if key not in sig["outcomes"] and days_elapsed >= period:
                ret   = (current_price - entry_p) / entry_p * 100
                alpha = None
                if qqq_price and sig.get("qqq_entry"):
                    qqq_ret = (qqq_price - sig["qqq_entry"]) / sig["qqq_entry"] * 100
                    alpha   = round(ret - qqq_ret, 2)
                sig["outcomes"][key] = {
                    "price":         round(float(current_price), 4),
                    "return_pct":    round(ret, 2),
                    "alpha_vs_qqq":  alpha,
                    "date_measured": today_str,
                }

        if "20d" in sig["outcomes"]:
            sig["status"] = "closed"

    # ── Paper Portfolio: ปิดไม้ที่ครบ HOLD_DAYS ──
    remaining = []
    for pos in port["positions"]:
        try:
            open_date    = datetime.strptime(pos["open_date"], "%Y-%m-%d")
            days_held    = (today - open_date).days
        except Exception:
            remaining.append(pos)
            continue

        ticker        = pos["ticker"]
        current_price = (market_data.get(ticker) or {}).get("price")

        if days_held >= HOLD_DAYS and current_price:
            # ปิดไม้
            close_val_thb = pos["shares"] * float(current_price) * thb_rate
            pnl_thb       = close_val_thb - pos["cost_thb"]
            pnl_pct       = pnl_thb / pos["cost_thb"] * 100
            port["cash_thb"] += close_val_thb
            port["history"].append({
                "ticker":      ticker,
                "open_date":   pos["open_date"],
                "close_date":  today_str,
                "days_held":   days_held,
                "price_open":  pos["price_open"],
                "price_close": round(float(current_price), 4),
                "shares":      pos["shares"],
                "cost_thb":    pos["cost_thb"],
                "close_thb":   round(close_val_thb, 2),
                "pnl_thb":     round(pnl_thb, 2),
                "pnl_pct":     round(pnl_pct, 2),
                "ai_score":    pos.get("ai_score"),
                "sector":      pos.get("sector", ""),
            })
        else:
            # อัปเดต unrealized P&L ใน position
            if current_price:
                cur_val_thb = pos["shares"] * float(current_price) * thb_rate
                pos["price_current"] = round(float(current_price), 4)
                pos["unreal_thb"]    = round(cur_val_thb - pos["cost_thb"], 2)
                pos["unreal_pct"]    = round((cur_val_thb - pos["cost_thb"]) / pos["cost_thb"] * 100, 2)
                pos["days_held"]     = days_held
            remaining.append(pos)

    port["positions"] = remaining

    # ── Equity curve snapshot ──
    open_val_thb = sum(
        pos["shares"] * float((market_data.get(pos["ticker"]) or {}).get("price", pos["price_open"])) * thb_rate
        for pos in port["positions"]
    )
    total_val = port["cash_thb"] + open_val_thb
    port["equity_curve"].append({"date": today_str, "value_thb": round(total_val, 2)})
    if qqq_price:
        port["qqq_curve"].append({"date": today_str, "qqq_price": round(float(qqq_price), 4)})

    # เก็บ curve สูงสุด 200 วัน
    port["equity_curve"] = port["equity_curve"][-200:]
    port["qqq_curve"]    = port["qqq_curve"][-200:]
    port["history"]      = port["history"][-200:]

    _save(data)


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    data    = _load()
    signals = data["signals"]
    port    = data["portfolio"]

    # Accuracy per period
    period_stats = {}
    for period in ["5d", "10d", "20d"]:
        measured = [s for s in signals if period in s.get("outcomes", {})]
        if not measured:
            period_stats[period] = None
            continue
        returns = [s["outcomes"][period]["return_pct"] for s in measured]
        alphas  = [s["outcomes"][period]["alpha_vs_qqq"] for s in measured
                   if s["outcomes"][period].get("alpha_vs_qqq") is not None]
        wins    = [r for r in returns if r > 0]
        period_stats[period] = {
            "count":      len(measured),
            "win_rate":   round(len(wins) / len(measured) * 100, 1),
            "avg_return": round(sum(returns) / len(returns), 2),
            "avg_alpha":  round(sum(alphas) / len(alphas), 2) if alphas else None,
            "best":       round(max(returns), 2),
            "worst":      round(min(returns), 2),
        }

    # BUY vs WATCH breakdown
    action_stats = {}
    for act in ("BUY", "WATCH"):
        subset = [s for s in signals if s["action"] == act and "5d" in s.get("outcomes", {})]
        if subset:
            rets = [s["outcomes"]["5d"]["return_pct"] for s in subset]
            wins = [r for r in rets if r > 0]
            action_stats[act] = {
                "count":    len(subset),
                "win_rate": round(len(wins) / len(subset) * 100, 1),
                "avg_5d":   round(sum(rets) / len(rets), 2),
            }

    # Paper portfolio summary
    history     = port.get("history", [])
    closed_pnls = [t["pnl_pct"] for t in history]
    port_wins   = [p for p in closed_pnls if p > 0]
    equity      = port.get("equity_curve", [])
    start_val   = PAPER_CAPITAL_THB
    current_val = equity[-1]["value_thb"] if equity else start_val
    total_return = (current_val - start_val) / start_val * 100

    # QQQ benchmark return
    qqq_curve = port.get("qqq_curve", [])
    qqq_return = None
    if len(qqq_curve) >= 2:
        q0 = qqq_curve[0]["qqq_price"]
        q1 = qqq_curve[-1]["qqq_price"]
        qqq_return = round((q1 - q0) / q0 * 100, 2)

    paper_stats = {
        "capital_thb":    PAPER_CAPITAL_THB,
        "current_val_thb": round(current_val, 2),
        "total_return_pct": round(total_return, 2),
        "cash_thb":       round(port["cash_thb"], 2),
        "open_positions": len(port.get("positions", [])),
        "closed_trades":  len(history),
        "win_rate_trades": round(len(port_wins) / len(closed_pnls) * 100, 1) if closed_pnls else None,
        "avg_trade_pct":  round(sum(closed_pnls) / len(closed_pnls), 2) if closed_pnls else None,
        "qqq_return_pct": qqq_return,
        "alpha":          round(total_return - qqq_return, 2) if qqq_return is not None else None,
        "equity_curve":   equity[-60:],   # 60 วันล่าสุด
        "open_pos":       port.get("positions", []),
        "recent_trades":  list(reversed(history[-20:])),
    }

    return {
        "period_stats":   period_stats,
        "action_stats":   action_stats,
        "total_signals":  len(signals),
        "open_signals":   sum(1 for s in signals if s["status"] == "open"),
        "recent_signals": list(reversed(signals[-30:])),
        "paper":          paper_stats,
    }
