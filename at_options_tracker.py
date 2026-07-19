"""
at_options_tracker.py — Paper Trade Options Engine
ดึง option chain จริง (Yahoo Finance) + Black-Scholes Greeks
เปิดไม้ Call อัตโนมัติเมื่อ ArtheeNoi ให้ BUY signal
"""
import json, math, time
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR      = Path(__file__).parent
OPTIONS_FILE  = BASE_DIR / "wiki" / "options_tracker.json"

CAPITAL_THB   = 10_000.0   # ทุน options แยกจาก stock portfolio
MAX_POSITIONS = 6          # ถือสูงสุด 6 สัญญา
ALLOC_PCT     = 0.15       # ต่อสัญญา 15% ของทุน
STOP_LOSS_PCT = 0.50       # stop loss ถ้าขาดทุน 50% ของ premium
TAKE_PROFIT_PCT = 1.00     # take profit ถ้ากำไร 100% ของ premium


# ── Black-Scholes ─────────────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun approximation)"""
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
           + t * (-1.821255978 + t * 1.330274429))))
    cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x) * poly
    return cdf if x >= 0 else 1.0 - cdf

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def black_scholes(S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = "call") -> dict:
    """
    S     = ราคาหุ้นปัจจุบัน
    K     = strike price
    T     = เวลาถึง expiry (ปี เช่น 21 วัน = 21/365)
    r     = risk-free rate (เช่น 0.0363)
    sigma = implied volatility (เช่น 0.45 = 45%)
    """
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return {"price": round(intrinsic, 4), "delta": 1.0 if intrinsic > 0 else 0.0,
                "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = _norm_cdf(d1)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
        delta = _norm_cdf(d1) - 1.0

    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega  = S * _norm_pdf(d1) * math.sqrt(T) / 100          # per 1% IV move
    theta = (-(S * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
             - r * K * math.exp(-r * T) * _norm_cdf(d2 if option_type == "call" else -d2)) / 365

    return {
        "price": round(max(price, 0), 4),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),   # USD/วัน (negative = time decay)
        "vega":  round(vega, 4),    # USD per 1% IV
    }


# ── Fetch Option Chain ────────────────────────────────────────────────────────

def fetch_option_chain(ticker: str, min_days: int = 14, max_days: int = 45) -> dict | None:
    """
    ดึง option chain ใกล้ที่สุดที่อยู่ในช่วง min_days-max_days
    คืน dict ของ call ATM/OTM ที่น่าสนใจ
    """
    try:
        import yfinance as yf
        tk   = yf.Ticker(ticker)
        exps = tk.options
        if not exps:
            return None

        today   = datetime.now()
        best_exp = None
        for exp in exps:
            exp_dt = datetime.strptime(exp, "%Y-%m-%d")
            days   = (exp_dt - today).days
            if min_days <= days <= max_days:
                best_exp = exp
                break

        if not best_exp:
            # ใช้อันที่ใกล้ที่สุดที่ > min_days
            for exp in exps:
                exp_dt = datetime.strptime(exp, "%Y-%m-%d")
                if (exp_dt - today).days >= min_days:
                    best_exp = exp
                    break

        if not best_exp:
            return None

        chain = tk.option_chain(best_exp)
        calls = chain.calls
        if calls.empty:
            return None

        # ราคาปัจจุบัน
        info  = tk.fast_info
        spot  = float(info.last_price or 0)
        if spot <= 0:
            return None

        # เลือก strike ที่ใกล้ ATM ที่สุด (หรือ slightly OTM +5%)
        target_strike = spot * 1.03
        calls["dist"]  = (calls["strike"] - target_strike).abs()
        best_call      = calls.sort_values("dist").iloc[0]

        exp_dt  = datetime.strptime(best_exp, "%Y-%m-%d")
        T_years = max((exp_dt - today).days / 365.0, 0.001)
        iv      = float(best_call.get("impliedVolatility", 0.35) or 0.35)

        return {
            "ticker":       ticker,
            "expiry":       best_exp,
            "days_to_exp":  (exp_dt - today).days,
            "spot":         round(spot, 4),
            "strike":       float(best_call["strike"]),
            "ask":          float(best_call.get("ask", 0) or best_call.get("lastPrice", 0)),
            "bid":          float(best_call.get("bid", 0)),
            "iv":           round(iv, 4),
            "volume":       int(best_call.get("volume", 0) or 0),
            "open_interest": int(best_call.get("openInterest", 0) or 0),
            "T_years":      round(T_years, 6),
        }
    except Exception as e:
        print(f"    options fetch {ticker}: {e}")
        return None


# ── I/O ──────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if OPTIONS_FILE.exists():
        try:
            return json.loads(OPTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "version":   1,
        "positions": [],   # open option positions
        "history":   [],   # closed
        "equity_curve": [],
        "cash_thb":  CAPITAL_THB,
        "capital_thb": CAPITAL_THB,
    }

def _save(data: dict):
    OPTIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Open position ─────────────────────────────────────────────────────────────

def open_call(ticker: str, ai_score: int, stars: int,
              thb_rate: float = 36.0, r: float = 0.0363) -> bool:
    """
    เปิด Call option อัตโนมัติเมื่อ ArtheeNoi BUY
    คืน True ถ้าเปิดได้
    """
    data = _load()
    open_tickers = {p["ticker"] for p in data["positions"]}
    if ticker in open_tickers:
        return False
    if len(data["positions"]) >= MAX_POSITIONS:
        return False

    chain = fetch_option_chain(ticker)
    if not chain or chain["ask"] <= 0:
        return False

    # Paper trade: ใช้ mini contract = 1 หุ้น (ไม่ใช่ 100 หุ้นจริง)
    # เพื่อให้ทุน 10,000 THB สามารถเทรดได้
    premium_usd = chain["ask"]
    contracts   = 1                       # 1 mini unit = 1 หุ้น
    cost_usd    = premium_usd * contracts
    cost_thb    = cost_usd * thb_rate

    # ตรวจว่ามีเงินพอไหม
    alloc_thb = data["cash_thb"] * ALLOC_PCT
    if cost_thb > alloc_thb or cost_thb > data["cash_thb"]:
        print(f"    options {ticker}: insufficient cash (need {cost_thb:.0f} have {data['cash_thb']:.0f} THB)")
        return False

    # คำนวณ Greeks ณ วันเปิด
    greeks = black_scholes(chain["spot"], chain["strike"],
                           chain["T_years"], r, chain["iv"], "call")

    data["cash_thb"] -= cost_thb
    data["positions"].append({
        "ticker":       ticker,
        "type":         "call",
        "open_date":    datetime.now().strftime("%Y-%m-%d"),
        "expiry":       chain["expiry"],
        "days_to_exp":  chain["days_to_exp"],
        "strike":       chain["strike"],
        "spot_open":    chain["spot"],
        "premium_open": round(premium_usd, 4),
        "contracts":    contracts,
        "cost_usd":     round(cost_usd, 2),
        "cost_thb":     round(cost_thb, 2),
        "thb_rate":     round(thb_rate, 2),
        "iv_open":      chain["iv"],
        "ai_score":     ai_score,
        "stars":        stars,
        # Greeks ณ วันเปิด
        "delta_open":   greeks["delta"],
        "theta_open":   greeks["theta"],
        "vega_open":    greeks["vega"],
        # อัปเดตทุกวัน
        "premium_current": round(premium_usd, 4),
        "unreal_usd":   0.0,
        "unreal_thb":   0.0,
        "unreal_pct":   0.0,
        "delta":        greeks["delta"],
        "theta":        greeks["theta"],
        "vega":         greeks["vega"],
        "status":       "open",
    })

    _save(data)
    print(f"    options OPEN {ticker} Call ${chain['strike']} exp={chain['expiry']} "
          f"premium=${premium_usd:.2f} ({cost_thb:.0f} THB) delta={greeks['delta']:.2f}")
    return True


# ── Update positions ──────────────────────────────────────────────────────────

def update_positions(market_data: dict, thb_rate: float = 36.0, r: float = 0.0363):
    """
    อัปเดต Greeks + P&L ของทุก position ทุกวัน
    ปิดอัตโนมัติเมื่อ: expire / stop loss / take profit
    """
    data  = _load()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    remaining = []

    for pos in data["positions"]:
        ticker = pos["ticker"]
        spot   = float((market_data.get(ticker) or {}).get("price") or pos["spot_open"])

        try:
            exp_dt  = datetime.strptime(pos["expiry"], "%Y-%m-%d")
            T_years = max((exp_dt - today).days / 365.0, 0.0)
            days_left = (exp_dt - today).days
        except Exception:
            remaining.append(pos)
            continue

        # คำนวณ Greeks และ option price ปัจจุบัน
        greeks = black_scholes(spot, pos["strike"], T_years, r, pos["iv_open"], pos["type"])
        cur_premium = greeks["price"]

        unreal_usd = (cur_premium - pos["premium_open"]) * pos["contracts"]
        unreal_thb = unreal_usd * thb_rate
        unreal_pct = unreal_usd / (pos["premium_open"] * pos["contracts"]) * 100 if pos["premium_open"] > 0 else 0

        pos.update({
            "premium_current": round(cur_premium, 4),
            "unreal_usd":   round(unreal_usd, 2),
            "unreal_thb":   round(unreal_thb, 2),
            "unreal_pct":   round(unreal_pct, 2),
            "delta":        greeks["delta"],
            "theta":        greeks["theta"],
            "vega":         greeks["vega"],
            "spot_current": round(spot, 4),
            "days_left":    days_left,
        })

        # เงื่อนไขปิด
        close_reason = None
        if days_left <= 0:
            close_reason = "expired"
        elif unreal_pct <= -STOP_LOSS_PCT * 100:
            close_reason = "stop_loss"
        elif unreal_pct >= TAKE_PROFIT_PCT * 100:
            close_reason = "take_profit"

        if close_reason:
            close_val_thb = (pos["cost_thb"] + unreal_thb) if close_reason != "expired" else 0
            pnl_thb = close_val_thb - pos["cost_thb"]
            data["cash_thb"] += max(close_val_thb, 0)
            data["history"].append({
                **pos,
                "close_date":   today_str,
                "close_reason": close_reason,
                "pnl_thb":      round(pnl_thb, 2),
                "pnl_pct":      round(unreal_pct, 2),
                "status":       "closed",
            })
            print(f"    options CLOSE {ticker} [{close_reason}] P&L={pnl_thb:+.0f} THB ({unreal_pct:+.1f}%)")
        else:
            remaining.append(pos)

    data["positions"]  = remaining
    data["history"]    = data["history"][-100:]

    # equity curve
    open_val_thb = sum(max(p["cost_thb"] + p["unreal_thb"], 0) for p in remaining)
    total_val    = data["cash_thb"] + open_val_thb
    data["equity_curve"].append({"date": today_str, "value_thb": round(total_val, 2)})
    data["equity_curve"] = data["equity_curve"][-200:]

    _save(data)


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    data     = _load()
    history  = data["history"]
    equity   = data["equity_curve"]
    positions = data["positions"]

    pnls      = [t["pnl_thb"] for t in history]
    wins      = [p for p in pnls if p > 0]
    cur_val   = equity[-1]["value_thb"] if equity else CAPITAL_THB
    total_ret = (cur_val - CAPITAL_THB) / CAPITAL_THB * 100

    return {
        "capital_thb":      CAPITAL_THB,
        "cash_thb":         round(data["cash_thb"], 2),
        "current_val_thb":  round(cur_val, 2),
        "total_return_pct": round(total_ret, 2),
        "open_positions":   len(positions),
        "closed_trades":    len(history),
        "win_rate":         round(len(wins) / len(pnls) * 100, 1) if pnls else None,
        "avg_pnl_thb":      round(sum(pnls) / len(pnls), 2) if pnls else None,
        "best_trade_thb":   round(max(pnls), 2) if pnls else None,
        "worst_trade_thb":  round(min(pnls), 2) if pnls else None,
        "positions":        positions,
        "recent_trades":    list(reversed(history[-15:])),
        "equity_curve":     equity[-60:],
    }
