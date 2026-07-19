"""
at_analysis.py — Comprehensive Stock Analysis Engine for ArtheeNoi
ทุกปัจจัยที่มีผลต่อราคาหุ้น: Technical + Fundamental + Macro + Sentiment
"""

import math
import requests
import warnings
warnings.filterwarnings("ignore")

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Sector → Benchmark ETF mapping ───────────────────────────────────────────
SECTOR_ETF: dict[str, str] = {
    "Semis":       "SOXX",  "AI-SW":       "XLK",   "AI-Infra":   "XLK",
    "Mega-Tech":   "XLK",   "EDA":         "XLK",   "Cyber":      "HACK",
    "Fintech":     "XLF",   "Bank":        "XLF",   "Reg-Bank":   "KRE",
    "Insurance":   "KIE",   "Biotech":     "XBI",   "Pharma":     "XPH",
    "Med-Tech":    "IHI",   "Health-Ins":  "XLV",   "REIT":       "VNQ",
    "BDC":         "BIZD",  "Utilities":   "XLU",   "Clean-NRG":  "ICLN",
    "Nuclear":     "NLR",   "Oil-Gas":     "XLE",   "Midstream":  "AMLP",
    "Refining":    "XLE",   "Oil-Svc":     "OIH",   "Mining":     "GDX",
    "Industrial":  "XLI",   "Defense":     "ITA",   "Aerospace":  "ITA",
    "Logistics":   "XLI",   "Rail":        "XTN",   "EV-Auto":    "LIT",
    "Auto":        "CARZ",  "Space":       "UFO",   "Satellite":  "UFO",
    "Telecom":     "IYZ",   "Staples":     "XLP",   "Retail":     "XRT",
    "Gaming":      "ESPO",  "Crypto":      "BITO",  "Water":      "PHO",
    "Gold-Mining": "GDX",   "Satellite":   "UFO",
}

# ── Sector ETF closes cache (TTL: 1 hour, shared across session) ──────────────
_etf_cache:    dict[str, list] = {}  # sym → closes list
_etf_cache_ts: dict[str, float] = {}
_ETF_TTL = 3600

# ══════════════════════════════════════════════════════════════════════════════
# 1. TECHNICAL INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

def calc_rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    return round(100 - 100 / (1 + ag / al), 1) if al > 0 else 100.0


def _ema_series(closes: list, period: int) -> list:
    if len(closes) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]
    for p in closes[period:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: list) -> dict:
    """MACD(12,26,9). Returns trend, crossover, histogram direction."""
    e12 = _ema_series(closes, 12)
    e26 = _ema_series(closes, 26)
    if not e12 or not e26:
        return {"trend": "neutral", "crossover": None, "hist": 0, "macd": 0, "signal": 0}
    offset = len(e12) - len(e26)
    macd_line = [e12[i + offset] - e26[i] for i in range(len(e26))]
    sig_line  = _ema_series(macd_line, 9)
    if not sig_line:
        return {"trend": "neutral", "crossover": None, "hist": 0, "macd": 0, "signal": 0}
    hist_now  = macd_line[-1] - sig_line[-1]
    hist_prev = macd_line[-2] - sig_line[-2] if len(macd_line) > 1 and len(sig_line) > 1 else hist_now
    trend     = "bullish" if macd_line[-1] > 0 else "bearish"
    crossover = None
    if hist_prev < 0 and hist_now >= 0:
        crossover = "bullish_cross"   # MACD crossed above signal
    elif hist_prev > 0 and hist_now <= 0:
        crossover = "bearish_cross"
    return {
        "trend":     trend,
        "crossover": crossover,
        "hist":      round(hist_now, 4),
        "macd":      round(macd_line[-1], 4),
        "signal":    round(sig_line[-1], 4),
    }


def calc_bollinger(closes: list, period: int = 20, std_mult: float = 2.0) -> dict:
    """Bollinger Bands. %B: 0=at lower band, 1=at upper band."""
    if len(closes) < period:
        return {"pct_b": 0.5, "bandwidth": 0, "squeeze": False, "position": "mid"}
    window = closes[-period:]
    mid    = sum(window) / period
    std    = math.sqrt(sum((x - mid) ** 2 for x in window) / period)
    upper  = mid + std_mult * std
    lower  = mid - std_mult * std
    price  = closes[-1]
    pct_b  = (price - lower) / (upper - lower) if upper > lower else 0.5
    bw     = (upper - lower) / mid * 100 if mid else 0
    squeeze = bw < 5.0  # volatility compression → breakout incoming
    if pct_b <= 0.05:   pos = "at_lower"    # oversold extreme
    elif pct_b <= 0.25: pos = "lower_zone"  # below mid, buy zone
    elif pct_b <= 0.75: pos = "mid_zone"
    elif pct_b <= 0.95: pos = "upper_zone"
    else:               pos = "at_upper"    # overbought extreme
    return {"pct_b": round(pct_b, 3), "bandwidth": round(bw, 2),
            "squeeze": squeeze, "position": pos,
            "upper": round(upper, 2), "mid": round(mid, 2), "lower": round(lower, 2)}


def calc_ema(closes: list, period: int) -> float | None:
    s = _ema_series(closes, period)
    return round(s[-1], 4) if s else None


def calc_atr(closes: list, period: int = 14) -> float | None:
    """Average True Range as % of price (normalized ATR)."""
    if len(closes) < period + 1:
        return None
    trs = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    atr = sum(trs[-period:]) / period
    return round(atr / closes[-1] * 100, 2) if closes[-1] else None


def calc_momentum(closes: list, period: int = 10) -> float | None:
    """Rate of Change (ROC): price change over N periods in %."""
    if len(closes) < period + 1:
        return None
    return round((closes[-1] - closes[-period-1]) / closes[-period-1] * 100, 2)


def calc_stoch_rsi(closes: list, rsi_period: int = 14, stoch_period: int = 14) -> float | None:
    """Stochastic RSI: 0=oversold, 1=overbought."""
    if len(closes) < rsi_period + stoch_period + 1:
        return None
    rsi_vals = []
    for i in range(stoch_period):
        sub = closes[i: i + rsi_period + 1]
        rsi_vals.append(calc_rsi(sub) or 50.0)
    low_r  = min(rsi_vals)
    high_r = max(rsi_vals)
    cur_r  = calc_rsi(closes[-rsi_period-1:]) or 50.0
    return round((cur_r - low_r) / (high_r - low_r), 3) if high_r > low_r else 0.5


def calc_obv_signal(closes: list, volumes: list) -> str:
    """On-Balance Volume trend: 'accumulating' / 'distributing' / 'neutral'."""
    if len(closes) < 2 or len(volumes) < 2:
        return "neutral"
    obv = 0
    obv_series = [0]
    for i in range(1, min(len(closes), len(volumes))):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        obv_series.append(obv)
    recent = obv_series[-10:]
    trend  = (recent[-1] - recent[0]) / (abs(recent[0]) + 1)
    if trend > 0.05:   return "accumulating"
    elif trend < -0.05: return "distributing"
    return "neutral"


def calc_ma_cross(closes: list) -> dict:
    """Golden/Death cross status and trend."""
    ema20  = calc_ema(closes, 20)
    ma50   = calc_ema(closes, 50)
    ma200  = calc_ema(closes, 200)
    price  = closes[-1] if closes else 0
    cross  = "neutral"
    if ma50 and ma200:
        if ma50 > ma200:   cross = "golden"   # bullish
        else:              cross = "death"     # bearish
    above_ma50  = price > ma50  if ma50  else None
    above_ma200 = price > ma200 if ma200 else None
    return {"cross": cross, "ema20": ema20, "ma50": ma50, "ma200": ma200,
            "above_ma50": above_ma50, "above_ma200": above_ma200}


def calc_volume_surge(volumes: list, period: int = 20) -> float | None:
    """Current volume vs N-day average (ratio). >1.5 = surge."""
    if len(volumes) < period + 1:
        return None
    avg = sum(volumes[-period-1:-1]) / period
    return round(volumes[-1] / avg, 2) if avg else None


# ══════════════════════════════════════════════════════════════════════════════
# 2. FUNDAMENTAL SCORING
# ══════════════════════════════════════════════════════════════════════════════

def fundamental_score(d: dict) -> dict:
    """
    Score fundamentals 0-100. Higher = better investment quality.
    Components: Analyst, Valuation, Growth, Quality, Upside
    """
    score  = 50  # neutral start
    notes  = []

    # ── Analyst Consensus (0-25 pts) ──────────────────────────────────────────
    total  = d.get("total_analysts") or 0
    sb     = d.get("strong_buy") or 0
    b      = d.get("buy") or 0
    h      = d.get("hold") or 0
    s      = d.get("sell") or 0
    ss     = d.get("strong_sell") or 0
    analyst_pts = 0
    if total > 0:
        bull_ratio = (sb + b) / total
        bear_ratio = (s + ss) / total
        if   bull_ratio >= 0.75: analyst_pts = 25; notes.append(f"Analyst consensus strong BUY ({bull_ratio:.0%})")
        elif bull_ratio >= 0.60: analyst_pts = 18; notes.append(f"Analyst consensus BUY ({bull_ratio:.0%})")
        elif bull_ratio >= 0.40: analyst_pts = 10; notes.append(f"Analyst mixed ({bull_ratio:.0%} buy)")
        elif bear_ratio >= 0.40: analyst_pts = -5; notes.append(f"Analyst bearish ({bear_ratio:.0%} sell)")
    score += analyst_pts - 12  # center around 0

    # ── Price Target Upside (0-20 pts) ────────────────────────────────────────
    target   = d.get("analyst_target")
    price    = d.get("price") or 0
    upside   = 0
    upside_pts = 0
    if target and price > 0:
        upside = (target - price) / price * 100
        if   upside >= 30: upside_pts = 20; notes.append(f"Target upside +{upside:.0f}% (strong)")
        elif upside >= 15: upside_pts = 12; notes.append(f"Target upside +{upside:.0f}%")
        elif upside >= 5:  upside_pts = 6
        elif upside < -5:  upside_pts = -8; notes.append(f"Below target (downside {upside:.0f}%)")
    score += upside_pts - 6

    # ── Revenue & EPS Growth (0-20 pts) ───────────────────────────────────────
    rev_g  = d.get("revenue_growth")   # decimal, e.g. 0.15 = 15%
    eps_g  = d.get("eps_growth")
    growth_pts = 0
    if rev_g is not None:
        if   rev_g >= 0.30: growth_pts += 10; notes.append(f"Revenue growth {rev_g:.0%} (high)")
        elif rev_g >= 0.15: growth_pts += 6;  notes.append(f"Revenue growth {rev_g:.0%}")
        elif rev_g >= 0.05: growth_pts += 3
        elif rev_g < 0:     growth_pts -= 5;  notes.append(f"Revenue declining {rev_g:.0%}")
    if eps_g is not None:
        if   eps_g >= 0.25: growth_pts += 10; notes.append(f"EPS growth {eps_g:.0%} (strong)")
        elif eps_g >= 0.10: growth_pts += 5
        elif eps_g < 0:     growth_pts -= 5;  notes.append(f"EPS declining {eps_g:.0%}")
    score += growth_pts - 8

    # ── Quality: Margin + ROE + FCF (0-20 pts) ────────────────────────────────
    margin = d.get("profit_margin")
    roe    = d.get("roe")
    fcf    = d.get("free_cash_flow")
    quality_pts = 0
    if margin is not None:
        if   margin >= 0.20: quality_pts += 8; notes.append(f"Profit margin {margin:.0%} (excellent)")
        elif margin >= 0.10: quality_pts += 4; notes.append(f"Profit margin {margin:.0%}")
        elif margin < 0:     quality_pts -= 6; notes.append(f"Losing money (margin {margin:.0%})")
    if roe is not None:
        if   roe >= 0.20: quality_pts += 6; notes.append(f"ROE {roe:.0%} (strong)")
        elif roe >= 0.10: quality_pts += 3
        elif roe < 0:     quality_pts -= 4
    if fcf is not None and fcf > 0:
        quality_pts += 6; notes.append("Positive FCF")
    elif fcf is not None and fcf < 0:
        quality_pts -= 4; notes.append("Negative FCF (cash burn)")
    score += quality_pts - 7

    # ── Valuation: PE vs Growth (PEG-like) (0-15 pts) ────────────────────────
    pe     = d.get("pe_ratio")
    fwd_pe = d.get("forward_pe")
    val_pts = 0
    if fwd_pe is not None and fwd_pe > 0:
        if   fwd_pe < 15:  val_pts = 10; notes.append(f"Fwd PE {fwd_pe:.1f} (cheap)")
        elif fwd_pe < 25:  val_pts = 5
        elif fwd_pe < 40:  val_pts = 0
        elif fwd_pe >= 60: val_pts = -5; notes.append(f"Fwd PE {fwd_pe:.1f} (expensive)")
        # PEG check: if growth > 20%, high PE is ok
        if rev_g and rev_g > 0.20 and fwd_pe < 50:
            val_pts += 5; notes.append("High growth justifies valuation")
    score += val_pts - 2

    score = max(0, min(100, score))
    return {
        "score":      round(score),
        "notes":      notes[:5],
        "analyst_pct": round((sb + b) / total * 100) if total > 0 else None,
        "upside_pct":  round(upside, 1) if target and price else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3. TECHNICAL SCORING
# ══════════════════════════════════════════════════════════════════════════════

def technical_score(closes: list, volumes: list = None) -> dict:
    """Combined technical score 0-100. Higher = better buy setup."""
    if len(closes) < 14:
        return {"score": 50, "signals": [], "trend": "unknown"}

    score   = 50
    signals = []
    vols    = volumes or []

    # RSI (−20 to +20)
    rsi = calc_rsi(closes)
    if rsi is not None:
        if   rsi <= 20: score += 20; signals.append(f"RSI {rsi} ← extreme oversold 🟢")
        elif rsi <= 30: score += 15; signals.append(f"RSI {rsi} ← oversold 🟢")
        elif rsi <= 40: score += 8;  signals.append(f"RSI {rsi} ← low")
        elif rsi <= 50: score += 2
        elif rsi <= 60: score -= 2
        elif rsi <= 70: score -= 8;  signals.append(f"RSI {rsi} ← elevated")
        else:           score -= 15; signals.append(f"RSI {rsi} ← overbought 🔴")

    # MACD (−15 to +15)
    macd = calc_macd(closes)
    if macd["crossover"] == "bullish_cross":
        score += 15; signals.append("MACD bullish crossover 🟢")
    elif macd["crossover"] == "bearish_cross":
        score -= 15; signals.append("MACD bearish crossover 🔴")
    elif macd["trend"] == "bullish":
        score += 5; signals.append("MACD above zero (bullish)")
    else:
        score -= 5; signals.append("MACD below zero (bearish)")

    # Bollinger Bands (−12 to +12)
    bb = calc_bollinger(closes)
    if bb["position"] == "at_lower":
        score += 12; signals.append("At lower Bollinger Band 🟢")
    elif bb["position"] == "lower_zone":
        score += 6;  signals.append("In lower BB zone (buy zone)")
    elif bb["position"] == "at_upper":
        score -= 12; signals.append("At upper Bollinger Band 🔴")
    elif bb["position"] == "upper_zone":
        score -= 5
    if bb["squeeze"]:
        signals.append("BB Squeeze → breakout coming ⚡")

    # MA Cross (−10 to +10)
    ma = calc_ma_cross(closes)
    if ma["cross"] == "golden":
        score += 10; signals.append("Golden Cross (MA50 > MA200) 🟡")
    elif ma["cross"] == "death":
        score -= 10; signals.append("Death Cross (MA50 < MA200) 💀")
    if ma["above_ma200"] is True:
        score += 4;  signals.append("Above MA200 (long-term uptrend)")
    elif ma["above_ma200"] is False:
        score -= 4;  signals.append("Below MA200 (long-term downtrend)")

    # Momentum ROC10 (−8 to +8)
    mom = calc_momentum(closes, 10)
    if mom is not None:
        if   mom >= 10: score += 8;  signals.append(f"Momentum +{mom:.1f}% (10d)")
        elif mom >= 3:  score += 4
        elif mom >= 0:  score += 1
        elif mom >= -3: score -= 2
        elif mom >= -10:score -= 5;  signals.append(f"Momentum {mom:.1f}% (weak)")
        else:           score -= 8;  signals.append(f"Momentum {mom:.1f}% (falling 🔴)")

    # Stochastic RSI (−5 to +5)
    srsi = calc_stoch_rsi(closes)
    if srsi is not None:
        if   srsi <= 0.20: score += 5; signals.append(f"StochRSI {srsi:.2f} oversold")
        elif srsi >= 0.80: score -= 5; signals.append(f"StochRSI {srsi:.2f} overbought")

    # Volume surge (−5 to +5)
    if vols:
        vsurge = calc_volume_surge(vols)
        if vsurge is not None:
            if vsurge >= 2.0:
                if closes[-1] >= closes[-2]:
                    score += 5; signals.append(f"Volume surge ×{vsurge} (buying 🟢)")
                else:
                    score -= 5; signals.append(f"Volume surge ×{vsurge} (selling 🔴)")

    # OBV (−5 to +5)
    if vols:
        obv = calc_obv_signal(closes, vols)
        if obv == "accumulating":
            score += 5; signals.append("OBV Accumulating (smart money buying)")
        elif obv == "distributing":
            score -= 5; signals.append("OBV Distributing (selling pressure)")

    # 52W position (additional from closes)
    h52 = max(closes) if closes else 0
    l52 = min(closes) if closes else 0
    rng = h52 - l52
    if rng > 0:
        pct = (closes[-1] - l52) / rng
        if pct <= 0.10:
            score += 8; signals.append("Near 52W low (major support) 🟢")
        elif pct >= 0.90:
            score -= 6; signals.append("Near 52W high (resistance)")

    score = max(0, min(100, score))
    trend = "strong_bull" if score >= 75 else "bull" if score >= 60 else \
            "bear" if score <= 30 else "strong_bear" if score <= 20 else "neutral"

    return {
        "score":   round(score),
        "signals": signals[:8],
        "trend":   trend,
        "rsi":     rsi,
        "macd":    macd,
        "bb":      bb,
        "ma":      ma,
        "mom":     mom,
        "srsi":    srsi,
        "atr":     calc_atr(closes),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. MACRO DATA (FRED + Market)
# ══════════════════════════════════════════════════════════════════════════════

_macro_cache: dict = {}
_macro_ts: float   = 0.0
_MACRO_TTL = 3600  # 1 hour cache

def fetch_fred_series(series_id: str) -> float | None:
    """Fetch latest value of a FRED series (no API key needed for public)."""
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        r = requests.get(url, headers=_HEADERS, timeout=10, verify=False)
        r.raise_for_status()
        lines = [l for l in r.text.strip().split("\n") if l and not l.startswith("DATE")]
        if not lines:
            return None
        # last non-empty value
        for line in reversed(lines):
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in (".", ""):
                try:
                    return float(parts[1].strip())
                except ValueError:
                    continue
    except Exception:
        pass
    return None


def fetch_yahoo_price(sym: str) -> float | None:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"
        r = requests.get(url, headers=_HEADERS, timeout=8, verify=False)
        closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        return [c for c in closes if c][-1]
    except Exception:
        return None


def fetch_macro() -> dict:
    """Fetch all macro indicators. Cached 1 hour."""
    import time
    global _macro_cache, _macro_ts
    if _macro_cache and (time.time() - _macro_ts) < _MACRO_TTL:
        return _macro_cache

    print("  Fetching macro data (FRED + market)...")
    m = {}

    # FRED series
    m["fed_rate"]    = fetch_fred_series("DFF")       # Fed Funds Rate
    m["yield_curve"] = fetch_fred_series("T10Y2Y")    # 10Y-2Y spread (negative = inverted)
    m["cpi"]         = fetch_fred_series("CPIAUCSL")  # CPI level
    m["unemployment"]= fetch_fred_series("UNRATE")    # Unemployment %
    m["m2"]          = fetch_fred_series("M2SL")      # Money supply

    # Market-based
    m["vix"]   = fetch_yahoo_price("^VIX")       # Fear gauge
    m["dxy"]   = fetch_yahoo_price("DX-Y.NYB")   # Dollar index
    m["oil"]   = fetch_yahoo_price("CL=F")        # Crude oil
    m["gold"]  = fetch_yahoo_price("GC=F")        # Gold
    m["tnx"]   = fetch_yahoo_price("^TNX")        # 10Y Treasury yield

    # Interpret
    m["rate_env"]   = _rate_environment(m)
    m["risk_level"] = _risk_level(m)
    m["regime"]     = _market_regime(m)

    _macro_cache = m
    _macro_ts    = time.time()
    print(f"  Macro: Fed={m.get('fed_rate')}% YieldCurve={m.get('yield_curve')} VIX={m.get('vix')} DXY={m.get('dxy')}")
    return m


def _rate_environment(m: dict) -> str:
    fr = m.get("fed_rate") or 0
    if fr >= 5.0:   return "high_rate"     # punishes growth/unprofitable
    elif fr >= 3.0: return "elevated_rate"
    elif fr >= 1.0: return "normal_rate"
    else:           return "low_rate"      # risk-on, growth favored


def _risk_level(m: dict) -> str:
    vix = m.get("vix") or 18
    yc  = m.get("yield_curve") or 0
    if vix >= 30 or yc < -0.5:  return "high_risk"
    elif vix >= 20:              return "elevated_risk"
    elif vix <= 13:              return "low_risk_complacent"
    return "normal_risk"


def _market_regime(m: dict) -> str:
    """Bull/Bear/Stagflation/Recession regime."""
    yc  = m.get("yield_curve") or 0
    vix = m.get("vix") or 18
    cpi = m.get("cpi") or 0
    une = m.get("unemployment") or 4
    # Simplified: real-world regimes need more data but this is directional
    if yc < -0.3 and vix > 20:   return "recession_risk"
    if vix > 30:                  return "crisis"
    if yc > 0.5 and vix < 20:    return "expansion"
    if cpi > 300 and une < 4.5:  return "overheating"
    return "mid_cycle"


def macro_score(macro: dict, sector: str = "") -> dict:
    """Score how macro environment favors this sector. 0-100."""
    regime    = macro.get("regime", "mid_cycle")
    rate_env  = macro.get("rate_env", "normal_rate")
    risk_lvl  = macro.get("risk_level", "normal_risk")
    vix       = macro.get("vix") or 18
    dxy       = macro.get("dxy") or 100

    score = 50
    notes = []

    # Rate environment impact by sector
    rate_sector_adj = {
        "high_rate": {
            "Semis": -5, "AI-SW": -8, "Biotech": -10, "Crypto": -15, "EV-Auto": -10,
            "REIT": -12, "Utilities": -5, "Bank": +8, "Reg-Bank": +8, "Insurance": +5,
            "Fintech": -5, "Staples": +3, "Defense": +3, "Oil-Gas": +3,
        },
        "low_rate": {
            "Semis": +8, "AI-SW": +10, "Biotech": +8, "Crypto": +12, "EV-Auto": +8,
            "REIT": +10, "Utilities": +5, "Bank": -5, "Reg-Bank": -5,
            "Staples": -3, "Mega-Tech": +8,
        },
    }.get(rate_env, {})
    adj = rate_sector_adj.get(sector, 0)
    score += adj
    if adj != 0:
        notes.append(f"{rate_env}: {sector} sector {'+' if adj>0 else ''}{adj}pts")

    # VIX impact
    if vix >= 30:
        score -= 10; notes.append(f"VIX {vix:.0f} HIGH (extreme fear → hold cash)")
    elif vix >= 20:
        score -= 4;  notes.append(f"VIX {vix:.0f} elevated")
    elif vix <= 13:
        score -= 3;  notes.append(f"VIX {vix:.0f} very low (complacency risk)")
    else:
        score += 3

    # Yield curve
    yc = macro.get("yield_curve") or 0
    if yc < -0.5:
        score -= 8; notes.append(f"Yield curve inverted ({yc:.2f}) — recession signal")
    elif yc < 0:
        score -= 3; notes.append(f"Yield curve negative ({yc:.2f})")
    elif yc > 0.5:
        score += 5; notes.append(f"Yield curve normal ({yc:.2f})")

    # Dollar (DXY) impact
    if dxy > 106:
        # Strong dollar hurts: international earners, commodities, EM
        if sector in ("Mining", "Oil-Gas", "REIT", "Pharma"):
            score -= 5; notes.append(f"Strong DXY {dxy:.0f} hurts {sector}")
    elif dxy < 98:
        # Weak dollar helps commodities, international
        if sector in ("Mining", "Oil-Gas", "Semis", "Mega-Tech"):
            score += 4; notes.append(f"Weak DXY {dxy:.0f} helps {sector}")

    # Regime bonus
    regime_bonus = {
        "expansion":     {"Semis": +5, "AI-SW": +5, "Fintech": +5, "EV-Auto": +3},
        "recession_risk":{"Utilities": +8, "Staples": +8, "Defense": +5, "REIT": +3},
        "crisis":        {"Defense": +10, "Utilities": +8, "Staples": +6, "Mining": +5},
        "overheating":   {"Mining": +8, "Oil-Gas": +8, "Utilities": +3},
    }.get(regime, {})
    rb = regime_bonus.get(sector, 0)
    score += rb
    if rb > 0:
        notes.append(f"Regime '{regime}' favors {sector} +{rb}pts")

    score = max(0, min(100, score))
    return {"score": round(score), "notes": notes, "regime": regime}


# ══════════════════════════════════════════════════════════════════════════════
# 5. EXTRA MARKET DATA: Short Interest, Insider, Balance Sheet, Earnings, RS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_finviz(ticker: str) -> dict:
    """
    Scrape Finviz stats snapshot table.
    Returns: short_float, short_ratio, insider_own, inst_own,
             debt_eq, curr_ratio, div_yield, payout_ratio,
             eps_q_q, sales_q_q, eps_next_y, rsi_finviz
    """
    import re as _re
    out = {}
    try:
        r = requests.get(
            f"https://finviz.com/quote.ashx?t={ticker}",
            headers={**_HEADERS,
                     "Referer":        "https://finviz.com/",
                     "Accept-Language": "en-US,en;q=0.9"},
            verify=False, timeout=14,
        )
        html = r.text
        # Extract (label, raw_value_html) pairs using adjacent snapshot-td-label/content divs
        raw_pairs = _re.findall(
            r'class="snapshot-td-label"[^>]*>'
            r'(?:<a[^>]*>)?([^<]+)(?:</a>)?</div>'
            r'</td>\s*<td[^>]*>\s*'
            r'<div class="snapshot-td-content"[^>]*>(.*?)</div>',
            html, _re.DOTALL
        )
        # Strip inner tags from value, keep text only
        data = {}
        for label, val_html in raw_pairs:
            val_clean = _re.sub(r'<[^>]+>', '', val_html).strip()
            data[label.strip()] = val_clean

        def _f(key):
            v = data.get(key, "").replace(",", "").replace("%", "").strip()
            try:   return float(v)
            except: return None

        out["short_float"]  = _f("Short Float")
        out["short_ratio"]  = _f("Short Ratio")
        out["insider_own"]  = _f("Insider Own")
        out["inst_own"]     = _f("Inst Own")
        out["debt_eq"]      = _f("Debt/Eq")
        out["curr_ratio"]   = _f("Current Ratio")
        out["div_yield"]    = _f("Dividend %")
        out["payout_ratio"] = _f("Payout")
        out["eps_q_q"]      = _f("EPS Q/Q")
        out["sales_q_q"]    = _f("Sales Q/Q")
        out["eps_next_y"]   = _f("EPS next Y")
        out["rsi_finviz"]   = _f("RSI (14)")
        out["beta_finviz"]  = _f("Beta")
        out["quick_ratio"]  = _f("Quick Ratio")

        # Earnings date: "May 20 AMC" or "Aug 27 AMC" format
        earn_str = data.get("Earnings", "")
        if earn_str and earn_str not in ("-", "N/A", ""):
            from datetime import datetime as _dt
            out["earnings_date_str"] = earn_str
            try:
                # Remove timing suffix (AMC/BMO) and parse
                parts = earn_str.split()
                date_part = " ".join(p for p in parts if p not in ("AMC","BMO","AHM","BHM"))
                # Try current year first, then next year
                year_now = _dt.now().year
                for yr in (year_now, year_now + 1):
                    try:
                        earn_dt = _dt.strptime(f"{date_part} {yr}", "%b %d %Y")
                        delta   = (earn_dt - _dt.now()).days
                        out["earnings_days_away"] = delta
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
    except Exception:
        pass
    return {k: v for k, v in out.items() if v is not None}


def fetch_earnings_date(ticker: str) -> dict:
    """Fetch next earnings date from Yahoo Finance v7 quote API."""
    out = {"earnings_days_away": None, "earnings_date_str": None}
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={ticker}"
        r = requests.get(url, headers=_HEADERS, verify=False, timeout=8)
        result = r.json().get("quoteResponse", {}).get("result", [{}])[0]
        ts = result.get("earningsTimestamp") or result.get("earningsTimestampStart")
        if ts:
            from datetime import datetime
            earn_dt = datetime.fromtimestamp(ts)
            delta   = (earn_dt - datetime.now()).days
            out["earnings_days_away"] = delta
            out["earnings_date_str"]  = earn_dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return out


def relative_strength(stock_closes: list, bench_closes: list, period: int = 20) -> float | None:
    """
    RS = stock N-day return MINUS benchmark N-day return (percentage points).
    Positive = outperforming. e.g. +5.2 means stock beat benchmark by 5.2pp.
    Using difference (not ratio) avoids blow-ups when benchmark return is near zero.
    """
    if len(stock_closes) < period + 1 or len(bench_closes) < period + 1:
        return None
    def pct(closes):
        p = closes[-period - 1]
        return (closes[-1] - p) / p * 100 if p else None
    sr, br = pct(stock_closes), pct(bench_closes)
    if sr is None or br is None:
        return None
    return round(sr - br, 2)


def _fetch_closes_quick(sym: str) -> list:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=35d"
    r = requests.get(url, headers=_HEADERS, verify=False, timeout=8)
    closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return [c for c in closes if c is not None]


def get_sector_etf_closes(sector: str) -> list:
    """Get cached closes for the sector benchmark ETF. Fetches if stale."""
    import time
    etf = SECTOR_ETF.get(sector, "QQQ")
    now = time.time()
    if etf in _etf_cache and (now - _etf_cache_ts.get(etf, 0)) < _ETF_TTL:
        return _etf_cache[etf]
    try:
        closes = _fetch_closes_quick(etf)
        _etf_cache[etf]    = closes
        _etf_cache_ts[etf] = now
        return closes
    except Exception:
        return []


def prefetch_sector_etfs(sectors: list, also_qqq: bool = True) -> dict:
    """
    Batch-fetch closes for all unique sector ETFs + QQQ.
    Returns {etf_sym: [closes]} dict.
    Call once before ai_score_full() loops to avoid repeated per-stock fetches.
    """
    import time
    etf_syms = {SECTOR_ETF.get(s, "QQQ") for s in sectors}
    if also_qqq:
        etf_syms.add("QQQ")
    result = {}
    now = time.time()
    for etf in etf_syms:
        if etf in _etf_cache and (now - _etf_cache_ts.get(etf, 0)) < _ETF_TTL:
            result[etf] = _etf_cache[etf]
            continue
        try:
            closes = _fetch_closes_quick(etf)
            _etf_cache[etf]    = closes
            _etf_cache_ts[etf] = now
            result[etf]        = closes
        except Exception:
            pass
    return result


def extra_score(d: dict, sector: str = "", stock_closes: list = None) -> dict:
    """
    Extra signal score 0-100:
    Short Interest + Insider Ownership + Balance Sheet +
    Dividend + Earnings Calendar + EPS/Sales acceleration +
    Relative Strength vs Sector ETF + vs QQQ
    """
    score = 50
    notes = []

    # ── Short Interest ────────────────────────────────────────────────────────
    sf = d.get("short_float")
    sr = d.get("short_ratio")
    if sf is not None:
        if sf >= 30:    score += 3;  notes.append(f"Short {sf:.0f}% (squeeze setup, high risk)")
        elif sf >= 20:  score -= 6;  notes.append(f"Short {sf:.0f}% (heavily shorted)")
        elif sf >= 12:  score -= 3;  notes.append(f"Short {sf:.0f}% (moderate short)")
        elif sf <= 3:   score += 6;  notes.append(f"Short {sf:.0f}% (not crowded ✓)")
        elif sf <= 6:   score += 3
    if sr is not None and sr > 8:
        score -= 4; notes.append(f"Short ratio {sr:.1f}d (crowded)")

    # ── Insider Ownership ─────────────────────────────────────────────────────
    io = d.get("insider_own")
    if io is not None:
        if io >= 20:   score += 10; notes.append(f"Insider {io:.0f}% (mgmt aligned ✓)")
        elif io >= 10: score += 6;  notes.append(f"Insider {io:.0f}% owned")
        elif io >= 5:  score += 3
        elif io <= 1:  score -= 4;  notes.append(f"Insider {io:.0f}% (no skin in game)")

    # ── Institutional Ownership ────────────────────────────────────────────────
    inst = d.get("inst_own")
    if inst is not None:
        if inst >= 80:   score += 5; notes.append(f"Inst {inst:.0f}% (high conviction)")
        elif inst <= 25: score -= 4; notes.append(f"Inst {inst:.0f}% (under-owned)")

    # ── Balance Sheet ─────────────────────────────────────────────────────────
    de = d.get("debt_eq")
    cr = d.get("curr_ratio")
    if de is not None:
        if de <= 0.2:   score += 8; notes.append(f"D/E {de:.1f} (fortress balance sheet ✓)")
        elif de <= 0.5: score += 4
        elif de <= 1.0: score += 1
        elif de >= 3.0: score -= 8; notes.append(f"D/E {de:.1f} (high leverage ⚠️)")
        elif de >= 2.0: score -= 4; notes.append(f"D/E {de:.1f} (leveraged)")
    if cr is not None:
        if cr >= 2.5:   score += 6; notes.append(f"Current ratio {cr:.1f} (very liquid ✓)")
        elif cr >= 1.5: score += 3
        elif cr < 1.0:  score -= 6; notes.append(f"Current ratio {cr:.1f} (liquidity risk ⚠️)")

    # ── Dividend ──────────────────────────────────────────────────────────────
    dy  = d.get("div_yield")
    pay = d.get("payout_ratio")
    if dy is not None and dy > 0:
        if dy >= 5:    score += 6; notes.append(f"Div {dy:.1f}% (income ✓)")
        elif dy >= 2:  score += 3
        if pay is not None and pay >= 90:
            score -= 5; notes.append(f"Payout {pay:.0f}% (cut risk)")

    # ── Earnings Calendar ─────────────────────────────────────────────────────
    ed = d.get("earnings_days_away")
    if ed is not None:
        if 0 <= ed <= 3:
            score -= 10; notes.append(f"Earnings in {ed}d ⚠️ (avoid new entry)")
        elif 4 <= ed <= 7:
            score -= 6;  notes.append(f"Earnings in {ed}d (caution)")
        elif 8 <= ed <= 14:
            score -= 2;  notes.append(f"Earnings in {ed}d")
        elif -7 <= ed < 0:
            score += 4;  notes.append(f"Earnings {abs(ed)}d ago (fresh report)")

    # ── EPS + Sales Acceleration ──────────────────────────────────────────────
    eps_qq  = d.get("eps_q_q")
    sale_qq = d.get("sales_q_q")
    if eps_qq is not None:
        if eps_qq >= 30:    score += 8; notes.append(f"EPS Q/Q {eps_qq:.0f}% (accelerating 🚀)")
        elif eps_qq >= 15:  score += 5; notes.append(f"EPS Q/Q {eps_qq:.0f}%")
        elif eps_qq >= 5:   score += 2
        elif eps_qq < -15:  score -= 6; notes.append(f"EPS Q/Q {eps_qq:.0f}% (deteriorating)")
        elif eps_qq < -5:   score -= 3
    if sale_qq is not None:
        if sale_qq >= 25:   score += 5; notes.append(f"Sales Q/Q {sale_qq:.0f}% ✓")
        elif sale_qq >= 10: score += 2
        elif sale_qq < -5:  score -= 4; notes.append(f"Sales Q/Q {sale_qq:.0f}% (slowing)")

    # ── Relative Strength vs Sector ETF & QQQ ────────────────────────────────
    sc = stock_closes or d.get("closes") or d.get("closes30") or []
    if sc and len(sc) >= 22:
        etf_sym  = SECTOR_ETF.get(sector, "QQQ")
        etf_cl   = _etf_cache.get(etf_sym) or get_sector_etf_closes(sector)
        qqq_cl   = _etf_cache.get("QQQ")   or get_sector_etf_closes("")

        # RS vs Sector ETF (20-day, percentage point outperformance)
        rs_sector = relative_strength(sc, etf_cl, period=20) if etf_cl else None
        if rs_sector is not None:
            if   rs_sector >= 15:
                score += 10; notes.append(f"RS vs {etf_sym} +{rs_sector:.1f}pp (sector leader ★)")
            elif rs_sector >= 5:
                score += 6;  notes.append(f"RS vs {etf_sym} +{rs_sector:.1f}pp (outperforming)")
            elif rs_sector >= 0:
                score += 2
            elif rs_sector >= -5:
                score -= 3;  notes.append(f"RS vs {etf_sym} {rs_sector:.1f}pp (lagging sector)")
            elif rs_sector >= -15:
                score -= 6;  notes.append(f"RS vs {etf_sym} {rs_sector:.1f}pp (weak vs sector)")
            else:
                score -= 9;  notes.append(f"RS vs {etf_sym} {rs_sector:.1f}pp (sector laggard ⚠️)")
            d["rs_sector"] = rs_sector
            d["rs_etf"]    = etf_sym

        # RS vs QQQ broad market
        rs_qqq = relative_strength(sc, qqq_cl, period=20) if qqq_cl and etf_sym != "QQQ" else None
        if rs_qqq is not None:
            if   rs_qqq >= 10: score += 4; notes.append(f"RS vs QQQ +{rs_qqq:.1f}pp (mkt leader)")
            elif rs_qqq >= 3:  score += 2
            elif rs_qqq <= -10:score -= 4; notes.append(f"RS vs QQQ {rs_qqq:.1f}pp (underperforming)")
            elif rs_qqq <= -3: score -= 2
            d["rs_qqq"] = rs_qqq

    score = max(0, min(100, score))
    return {"score": round(score), "notes": notes[:6], "rs_sector": d.get("rs_sector"), "rs_qqq": d.get("rs_qqq"), "rs_etf": d.get("rs_etf")}


# ══════════════════════════════════════════════════════════════════════════════
# 6. NEWS SENTIMENT SCORING
# ══════════════════════════════════════════════════════════════════════════════

def fetch_marketaux_news(ticker: str) -> list:
    """
    Fetch news + pre-computed sentiment scores from MarketAux API.
    Free tier: 100 req/day. Key loaded from .env MARKETAUX_KEY=...
    Falls back to empty list if no key.
    """
    api_key = None
    try:
        from pathlib import Path
        for env_path in [
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent.parent / ".env",
        ]:
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("MARKETAUX_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if api_key:
                break
    except Exception:
        pass
    if not api_key:
        return []
    try:
        url = (f"https://api.marketaux.com/v1/news/all"
               f"?symbols={ticker}&api_token={api_key}&language=en&limit=5")
        r = requests.get(url, headers=_HEADERS, timeout=10, verify=False)
        items = r.json().get("data", [])
        results = []
        for a in items:
            ents = a.get("entities", [])
            sent = next((e.get("sentiment_score", 0) for e in ents
                         if e.get("symbol") == ticker), 0)
            results.append({
                "title":     a.get("title", "")[:100],
                "sentiment": sent,   # -1 to +1
                "summary":   a.get("description", "")[:120],
            })
        return results
    except Exception:
        return []


def news_sentiment(headlines: list) -> dict:
    """
    Sentiment scoring from news headlines.
    Supports both Yahoo RSS format (keyword-based) and
    MarketAux format (pre-computed 'sentiment' -1 to +1 field).
    Returns score 0-100 (50=neutral, >60=positive, <40=negative).
    """
    BULLISH = [
        "beat", "beats", "record", "surge", "rally", "upgrade", "raise", "raised",
        "growth", "profit", "exceed", "strong", "bullish", "buy", "outperform",
        "partnership", "deal", "contract", "win", "launch", "breakthrough",
        "ai", "datacenter", "cloud", "expansion", "dividend", "buyback",
        "positive", "gain", "jump", "soar", "top", "high", "approval", "approved",
        "acquisition", "revenue beat", "eps beat", "guidance raised",
    ]
    BEARISH = [
        "miss", "misses", "cut", "cuts", "downgrade", "lower", "weak", "loss",
        "decline", "fall", "drop", "warning", "risk", "concern", "sell",
        "lawsuit", "fine", "penalty", "recall", "delay", "disappoint",
        "layoff", "restructure", "debt", "bearish", "negative", "fear",
        "crash", "plunge", "slump", "shrink", "subpoena", "investigation",
        "guidance cut", "guidance lowered", "below expectations",
    ]
    POLITICAL_BOOST = [
        "tariff", "sanction", "war", "conflict", "geopolitic", "election",
        "fed rate", "interest rate", "inflation", "gdp", "recession",
        "trade war", "ban", "regulation", "antitrust",
    ]
    if not headlines:
        return {"score": 50, "label": "no_news", "bull": 0, "bear": 0}

    # Check if MarketAux format (has 'sentiment' key with -1..+1 float)
    has_marketaux_score = any("sentiment" in h and isinstance(h.get("sentiment"), (int, float))
                               for h in headlines)
    if has_marketaux_score:
        scores = [h.get("sentiment", 0) for h in headlines
                  if isinstance(h.get("sentiment"), (int, float))]
        if scores:
            avg = sum(scores) / len(scores)
            score = round(50 + avg * 50)   # -1..+1 → 0..100
            score = max(0, min(100, score))
            label = "very_bullish" if score >= 80 else "bullish" if score >= 65 else \
                    "very_bearish" if score <= 20 else "bearish" if score <= 35 else "neutral"
            return {"score": score, "label": label, "bull": sum(1 for s in scores if s > 0.2),
                    "bear": sum(1 for s in scores if s < -0.2), "source": "marketaux"}

    # Keyword-based (Yahoo RSS)
    bull = bear = political = 0
    for h in headlines:
        text = (h.get("title", "") + " " + h.get("summary", "")).lower()
        bull += sum(1 for w in BULLISH if w in text)
        bear += sum(1 for w in BEARISH if w in text)
        political += sum(1 for w in POLITICAL_BOOST if w in text)

    total = bull + bear
    if total == 0:
        return {"score": 50, "label": "neutral", "bull": 0, "bear": 0}

    ratio = bull / total
    score = round(40 + ratio * 60)
    # Political/macro news dampens extremes (uncertainty)
    if political > 2:
        score = round(score * 0.85 + 50 * 0.15)

    label = "very_bullish" if score >= 80 else "bullish" if score >= 65 else \
            "very_bearish" if score <= 20 else "bearish" if score <= 35 else "neutral"
    return {"score": score, "label": label, "bull": bull, "bear": bear,
            "political": political, "source": "keyword"}


# ══════════════════════════════════════════════════════════════════════════════
# 6. COMBINED AI SCORE
# ══════════════════════════════════════════════════════════════════════════════

WEIGHTS = {
    "technical":    0.28,
    "fundamental":  0.28,
    "macro":        0.14,
    "sentiment":    0.14,
    "extra":        0.16,  # Short Interest + Insider + Balance Sheet + Earnings + EPS Q/Q
}

def ai_score_full(d: dict, macro: dict = None, sector: str = "") -> dict:
    """
    Master scoring function. Returns comprehensive AI score 0-100.
    d = stock data dict from get_quote() / fetch_picks_lite()
    Fields used:
      Technical:    closes, volumes
      Fundamental:  pe_ratio, forward_pe, revenue_growth, eps_growth, profit_margin, roe, fcf,
                    analyst recs, analyst_target
      Macro:        from macro dict (FRED + VIX + DXY)
      Sentiment:    news (Yahoo RSS or MarketAux)
      Extra:        short_float, short_ratio, insider_own, inst_own,
                    debt_eq, curr_ratio, div_yield, payout_ratio,
                    eps_q_q, sales_q_q, earnings_days_away
    """
    closes  = d.get("closes") or d.get("closes30") or []
    volumes = d.get("volumes") or []
    news    = d.get("news") or []

    t_res = technical_score(closes, volumes)
    f_res = fundamental_score(d)
    m_res = macro_score(macro or {}, sector)
    s_res = news_sentiment(news)
    e_res = extra_score(d, sector=sector, stock_closes=closes)

    combined = round(
        t_res["score"] * WEIGHTS["technical"] +
        f_res["score"] * WEIGHTS["fundamental"] +
        m_res["score"] * WEIGHTS["macro"] +
        s_res["score"] * WEIGHTS["sentiment"] +
        e_res["score"] * WEIGHTS["extra"]
    )
    combined = max(0, min(100, combined))

    # Derive action from combined score
    rsi = t_res.get("rsi")
    if combined >= 75:
        action = "BUY";     stars = 3
    elif combined >= 62:
        action = "BUY";     stars = 2
    elif combined >= 52:
        action = "WATCH";   stars = 1
    elif combined >= 42:
        action = "NEUTRAL"; stars = 0
    elif combined >= 30:
        action = "WAIT";    stars = 0
    else:
        action = "AVOID";   stars = 0

    # Hard override: earnings imminent → no new entry
    earn_days = d.get("earnings_days_away")
    if earn_days is not None and 0 <= earn_days <= 3 and action in ("BUY",):
        action = "WATCH"; stars = max(0, stars - 1)

    # Override if RSI extremely oversold → at least WATCH
    if rsi and rsi <= 25 and action in ("NEUTRAL", "WAIT"):
        action = "WATCH"; stars = 1

    # Build summary reason (best signals from each layer)
    top_signals = (
        t_res["signals"][:2] +
        f_res["notes"][:1] +
        m_res["notes"][:1] +
        e_res["notes"][:1] +
        ([f"News {s_res['label']}"] if s_res.get("label") not in ("neutral", "no_news") else [])
    )
    reason = " | ".join(top_signals[:4]) if top_signals else "Composite analysis"

    return {
        "ai_score":   combined,
        "action":     action,
        "stars":      stars,
        "reason":     reason,
        "technical":  t_res,
        "fundamental":f_res,
        "macro":      m_res,
        "sentiment":  s_res,
        "extra":      e_res,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. ARTHEE NOI CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_arthee_context(macro: dict, top_stocks: list, news_headlines: list = None) -> str:
    """
    Build rich context string for ArtheeNoi prompt.
    top_stocks: list of {sym, ai_score, action, sector, ...}
    """
    lines = ["=== สถานการณ์ตลาดวันนี้ ==="]

    # Macro
    lines.append(f"Fed Rate: {macro.get('fed_rate', '?')}%  |  "
                 f"Yield Curve (10Y-2Y): {macro.get('yield_curve', '?')}  |  "
                 f"VIX: {macro.get('vix', '?'):.1f}  |  "
                 f"DXY: {macro.get('dxy', '?'):.1f}  |  "
                 f"Oil: ${macro.get('oil', '?'):.0f}  |  "
                 f"Gold: ${macro.get('gold', '?'):.0f}")
    lines.append(f"Regime: {macro.get('regime','?')}  |  "
                 f"Rate Env: {macro.get('rate_env','?')}  |  "
                 f"Risk: {macro.get('risk_level','?')}")

    if news_headlines:
        lines.append("\n=== ข่าวสำคัญตลาด ===")
        for h in news_headlines[:5]:
            lines.append(f"• {h.get('title','')[:80]}")

    lines.append("\n=== AI Score ของหุ้นแต่ละตัว (T=Tech F=Fund M=Macro E=Extra RS=RelStrength) ===")
    lines.append(f"{'Sym':<7} {'Score':>5} {'Action':<7} {'Sector':<12} {'T':>4} {'F':>4} {'M':>4} {'E':>4} {'RS_S':>5} {'RS_Q':>5}")
    lines.append("-" * 72)
    for s in top_stocks[:80]:
        t   = s.get("technical",   {}).get("score", "?")
        f   = s.get("fundamental", {}).get("score", "?")
        m   = s.get("macro",       {}).get("score", "?")
        ex  = s.get("extra",       {}).get("score", "?")
        rss = s.get("rs_sector")
        rsq = s.get("rs_qqq")
        rss_str = f"{rss:.2f}" if rss is not None else "?"
        rsq_str = f"{rsq:.2f}" if rsq is not None else "?"
        lines.append(f"{s['sym']:<7} {s.get('ai_score', 50):>5} {s.get('action','?'):<7} "
                     f"{s.get('sector','')[:12]:<12} {str(t):>4} {str(f):>4} {str(m):>4} "
                     f"{str(ex):>4} {rss_str:>5} {rsq_str:>5}")

    lines.append(f"\n=== คำสั่ง ===")
    lines.append(f"จากข้อมูลข้างต้นทั้งหมด เลือก 50 หุ้นที่ดีที่สุดสำหรับวันนี้")
    lines.append(f"พิจารณา: AI Score สูง, macro เอื้อต่อ sector, ข่าวดี, technical แข็งแกร่ง")
    lines.append(f"ตอบเฉพาะ ticker คั่นด้วย comma เช่น NVDA, AAPL, MSFT")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing at_analysis.py...")
    test_closes = [100, 98, 95, 97, 102, 105, 103, 108, 110, 107,
                   104, 106, 109, 112, 115, 111, 108, 113, 116, 118,
                   120, 117, 114, 116, 119, 122, 125, 121, 118, 120, 123]
    t = technical_score(test_closes)
    print(f"Technical: {t['score']}/100 | Trend: {t['trend']}")
    for s in t["signals"]:
        print(f"  {s}")

    macro = fetch_macro()
    print(f"\nMacro regime: {macro.get('regime')} | Risk: {macro.get('risk_level')}")

    print("\nai_score_full (no fundamentals):")
    r = ai_score_full({"closes": test_closes, "price": 123}, macro, "AI-SW")
    print(f"  AI Score: {r['ai_score']} | Action: {r['action']} ({r['stars']}★)")
    print(f"  Reason: {r['reason']}")
