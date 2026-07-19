"""
Daily Wiki Update
Fetches US stock prices, calculates RSI + signals, writes wiki/analysis/YYYY-MM-DD.md
Runs automatically every day after US market close.
"""

import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import requests, urllib3
    urllib3.disable_warnings()
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

HEADERS       = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}

# ===== Paths =====
BASE_DIR     = Path(__file__).parent
WIKI_DIR     = BASE_DIR.parent.parent / "wiki"
ANALYSIS_DIR = WIKI_DIR / "analysis"
STOCKS_DIR   = WIKI_DIR / "stocks"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
STOCKS_DIR.mkdir(parents=True, exist_ok=True)

# ===== Config =====
THB_RATE = 35.0  # overwritten by get_thb_rate() after functions are defined
TODAY    = datetime.now().strftime("%Y-%m-%d")

PORTFOLIO = {
    "NVDA":  {"shares": 2, "cost": 850},
    "MSFT":  {"shares": 3, "cost": 420},
    "GOOGL": {"shares": 2, "cost": 175},
    "META":  {"shares": 2, "cost": 550},
    "AMZN":  {"shares": 3, "cost": 200},
}

WATCHLIST = ["AVGO", "MRVL", "AMD", "INTC", "TSM", "TSLA", "NOW", "SOFI", "VST", "NOK"]
ETFS      = ["QQQ", "IVV", "DIA"]
GOLD      = "GC=F"
CRYPTO    = "BTC-USD"


# ===== Fundamentals Scraper =====
def _parse_abbr(text):
    if not text or text.strip() in ("N/A", "--", ""):
        return None
    text = text.strip().replace(",", "")
    mult = 1
    if   text.endswith("T"): mult = 1e12; text = text[:-1]
    elif text.endswith("B"): mult = 1e9;  text = text[:-1]
    elif text.endswith("M"): mult = 1e6;  text = text[:-1]
    elif text.endswith("K"): mult = 1e3;  text = text[:-1]
    try:    return float(text) * mult
    except: return None

import re as _re
import xml.etree.ElementTree as _ET

def get_thb_rate() -> float:
    """Fetch live USD/THB rate from Frankfurter (ECB), fallback to ExchangeRate-API."""
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest?from=USD&to=THB",
            timeout=6, verify=False
        )
        rate = r.json()["rates"]["THB"]
        print(f"  [FX] Live USD/THB = {rate:.4f} (Frankfurter)")
        return rate
    except Exception:
        pass
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=6, verify=False)
        rate = r.json()["rates"]["THB"]
        print(f"  [FX] Live USD/THB = {rate:.4f} (ExchangeRate-API)")
        return rate
    except Exception:
        print("  [FX] Using fallback THB rate = 35.0")
        return 35.0


def get_stock_news(ticker: str, count: int = 4) -> list:
    """Fetch recent news headlines from Yahoo Finance RSS feed."""
    try:
        r = requests.get(
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
            headers=SCRAPE_HEADERS, timeout=8, verify=False
        )
        if r.status_code != 200:
            return []
        root = _ET.fromstring(r.text)
        news = []
        for item in root.findall(".//item")[:count]:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            if pub:
                pub = pub[:16]
            if title and link:
                news.append({"title": title, "url": link, "date": pub})
        return news
    except Exception:
        return []


def scrape_fundamentals(ticker: str) -> dict:
    """Scrape Yahoo Finance quote page for fundamentals not in chart API."""
    out = {"market_cap": None, "pe_ratio": None, "forward_pe": None, "beta": None, "analyst_target": None}
    try:
        r = requests.get(
            f"https://finance.yahoo.com/quote/{ticker}/",
            headers=SCRAPE_HEADERS, verify=False, timeout=15
        )
        html = r.text

        def _field(name):
            m = _re.search(rf'data-field="{name}"[^>]*>([^<]+)</fin-streamer>', html)
            return _parse_abbr(m.group(1)) if m else None

        out["market_cap"] = _field("marketCap")
        out["pe_ratio"]   = _field("trailingPE")

        # Analyst mean target — fin-streamer field
        at_m = _re.search(r'data-field="targetMeanPrice"[^>]*>([^<]+)</fin-streamer>', html)
        out["analyst_target"] = _parse_abbr(at_m.group(1)) if at_m else None

        # Forward PE — <p class="value ...">value</p> after "Forward P/E" label
        fpe_m = _re.search(r'Forward P/E.{0,60}?class="value[^"]*"[^>]*>\s*([\d.,]+)', html, _re.DOTALL)
        out["forward_pe"] = float(fpe_m.group(1).replace(",", "")) if fpe_m else None

        # Beta — <span class="value ...">value</span> after "Beta (5Y Monthly)" label
        beta_m = _re.search(r'Beta \(5Y Monthly\)[^<]*</span>[^<]*<span[^>]*class="value[^"]*"[^>]*>([\d.]+)', html)
        out["beta"] = float(beta_m.group(1)) if beta_m else None
    except Exception:
        pass
    return out


def scrape_financials(ticker: str) -> dict:
    """Scrape Yahoo Finance key-statistics page for income statement metrics."""
    out = {}
    try:
        r = requests.get(
            f"https://finance.yahoo.com/quote/{ticker}/key-statistics/",
            headers=SCRAPE_HEADERS, verify=False, timeout=15
        )
        html = r.text

        rows = _re.findall(r'<tr[^>]*>(.*?)</tr>', html, _re.DOTALL)
        label_map = {
            "Revenue (ttm)":                    ("revenue_ttm",      False),
            "Net Income Avi to Common (ttm)":   ("net_income_ttm",   False),
            "Diluted EPS (ttm)":                ("eps_ttm",          False),
            "Profit Margin":                    ("profit_margin",    True),
            "Operating Margin (ttm)":           ("operating_margin", True),
            "Return on Equity (ttm)":           ("roe",              True),
            "Quarterly Revenue Growth (yoy)":   ("revenue_growth",   True),
            "Quarterly Earnings Growth (yoy)":  ("eps_growth",       True),
            "Levered Free Cash Flow (ttm)":     ("free_cash_flow",   False),
            "50-Day Moving Average":            ("ma50",             False),
            "200-Day Moving Average":           ("ma200",            False),
        }
        for row in rows:
            text = _re.sub(r'<[^>]+>', ' ', row)
            text = _re.sub(r'&amp;', '&', text)
            text = _re.sub(r'\s+', ' ', text).strip()
            for label, (key, is_pct) in label_map.items():
                if text.startswith(label):
                    rest = text[len(label):].strip()
                    if is_pct:
                        m = _re.match(r'(-?[\d.,]+)%', rest)
                        out[key] = float(m.group(1).replace(",", "")) if m else None
                    else:
                        m = _re.match(r'(-?[\d.,]+[TBM]?)', rest)
                        if m:
                            val = m.group(1)
                            # Skip single-digit footnote superscripts (e.g. "3 206.91" → 206.91)
                            if len(val) <= 2 and not any(c in val for c in "TBM."):
                                rest2 = rest[len(val):].strip()
                                m2 = _re.match(r'(-?[\d.,]+[TBM]?)', rest2)
                                val = m2.group(1) if m2 else val
                            out[key] = _parse_abbr(val)
                        else:
                            out[key] = None
                    break
    except Exception:
        pass
    return out


def scrape_analyst_reco(ticker: str) -> dict:
    """Scrape analyst recommendation counts from Yahoo Finance analysis page."""
    out = {"strong_buy": None, "buy": None, "hold": None, "sell": None, "strong_sell": None, "total_analysts": None}
    try:
        r = requests.get(
            f"https://finance.yahoo.com/quote/{ticker}/analysis/",
            headers=SCRAPE_HEADERS, verify=False, timeout=15
        )
        html = r.text
        # Recommendation trend is embedded as escaped JSON in a script tag (period "0m" = current month)
        m = _re.search(
            r'\\"period\\":\\"0m\\",\\"strongBuy\\":(\d+),\\"buy\\":(\d+),\\"hold\\":(\d+),\\"sell\\":(\d+),\\"strongSell\\":(\d+)',
            html
        )
        if m:
            sb, b, h, s, ss = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
            out.update({
                "strong_buy": sb, "buy": b, "hold": h, "sell": s, "strong_sell": ss,
                "total_analysts": sb + b + h + s + ss
            })
    except Exception:
        pass
    return out


# ===== Data Fetching =====
def get_quote(ticker: str) -> dict:
    """Fetch price history + extra fundamentals via Yahoo Finance APIs."""
    try:
        # --- History (chart API) ---
        url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=45d"
        r    = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        meta   = result["meta"]
        quote  = result["indicators"]["quote"][0]
        ts     = result.get("timestamp", [])

        closes  = [c for c in quote.get("close", []) if c is not None]
        price   = closes[-1] if closes else meta.get("regularMarketPrice", 0)
        prev    = closes[-2] if len(closes) > 1 else price
        chg_pct = round((price - prev) / prev * 100, 2) if prev else 0

        # 30-day slice with date labels
        if ts:
            paired   = [(t, c) for t, c in zip(ts, quote.get("close", [])) if c is not None][-30:]
            closes30 = [round(c, 2) for _, c in paired]
            dates30  = [datetime.fromtimestamp(t).strftime("%b %d") for t, _ in paired]
        else:
            closes30 = [round(c, 2) for c in closes[-30:]]
            dates30  = []

        base = {
            "ticker":     ticker,
            "name":       meta.get("shortName", ticker),
            "price":      round(price, 2),
            "change_pct": chg_pct,
            "high_52w":   meta.get("fiftyTwoWeekHigh"),
            "low_52w":    meta.get("fiftyTwoWeekLow"),
            "volume":     (quote.get("volume") or [None])[-1],
            "rsi":        calc_rsi(closes),
            "closes":     closes,
            "closes30":   closes30,
            "dates30":    dates30,
        }

        # --- Extra fundamentals (HTML scrape — quoteSummary API requires auth) ---
        fund = scrape_fundamentals(ticker)
        base.update(fund)

        # --- Financials from key-statistics page ---
        fin = scrape_financials(ticker)
        base.update(fin)

        # --- Analyst recommendation counts from analysis page ---
        reco = scrape_analyst_reco(ticker)
        base.update(reco)

        # --- Recent news headlines from Yahoo Finance RSS (skip special tickers like GC=F) ---
        if "=" not in ticker:
            base["news"] = get_stock_news(ticker)
        else:
            base["news"] = []

        return base

    except Exception as e:
        return {"ticker": ticker, "error": str(e), "price": 0, "change_pct": 0}


def fetch_all(tickers: list) -> dict:
    """Fetch all tickers one by one (requests-based, no rate limits)."""
    return {sym: get_quote(sym) for sym in tickers}


def calc_rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [max(d, 0) for d in deltas[-period:]]
    losses = [abs(min(d, 0)) for d in deltas[-period:]]
    avg_g  = sum(gains) / period
    avg_l  = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - 100 / (1 + rs), 1)


# ===== Signal Logic =====
def get_signal(rsi, change_pct, high_52w, low_52w, price) -> tuple:
    if rsi is None:
        if change_pct >  2: return "BULLISH",  "momentum +"
        if change_pct < -2: return "BEARISH",  "momentum -"
        return "NEUTRAL", "sideways"

    if rsi >= 70 and change_pct > 0:
        return "OVERBOUGHT", f"RSI {rsi} — watch for pullback"
    if rsi <= 30:
        return "OVERSOLD",   f"RSI {rsi} — potential entry"
    if rsi >= 55 and change_pct > 0:
        return "BULLISH",    f"RSI {rsi}, positive momentum"
    if rsi <= 45 and change_pct < 0:
        return "BEARISH",    f"RSI {rsi}, negative momentum"
    if change_pct >  1.5:
        return "BULLISH",    f"momentum +{change_pct}%"
    if change_pct < -1.5:
        return "BEARISH",    f"momentum {change_pct}%"
    return "NEUTRAL", f"RSI {rsi}"


# ===== Market Commentary (rule-based) =====
def market_commentary(market_data: dict) -> str:
    qqq  = market_data.get("QQQ", {})
    nvda = market_data.get("NVDA", {})
    q_pct = qqq.get("change_pct", 0)
    n_pct = nvda.get("change_pct", 0)

    if   q_pct >  1.5: tone = f"Tech market surged — QQQ +{q_pct}%. Broad risk-on across AI/Growth names."
    elif q_pct >  0.3: tone = f"Tech market nudged higher — QQQ +{q_pct}%. Selective buying, not broad rally."
    elif q_pct < -1.5: tone = f"Tech market sold off — QQQ {q_pct}%. Risk-off; monitor support levels."
    elif q_pct < -0.3: tone = f"Mild tech weakness — QQQ {q_pct}%. Profit-taking after recent run."
    else:               tone = f"Tech market sideways — QQQ {q_pct}%. No clear catalyst today."

    if abs(n_pct) > 2:
        nvda_line = f"NVDA moved {'+' if n_pct>0 else ''}{n_pct}% — significant for AI-Tech sentiment."
    else:
        nvda_line = f"NVDA held range ({'+' if n_pct>=0 else ''}{n_pct}%)."

    if   q_pct >  1: outlook = "Momentum positive. Watch for continuation above resistance."
    elif q_pct < -1: outlook = "Wait for support confirmation before adding positions."
    else:            outlook = "Hold current positions. No urgent action needed."

    return f"{tone}\n\n{nvda_line}\n\n**Outlook:** {outlook}"


# ===== Wiki Page Builder =====
def build_page(market_data: dict) -> str:
    # --- Portfolio P&L ---
    port_rows  = []
    total_val  = 0.0
    total_cost = 0.0

    for sym, info in PORTFOLIO.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        val      = d["price"] * info["shares"]
        cost_tot = info["cost"] * info["shares"]
        pnl_usd  = val - cost_tot
        pnl_pct  = pnl_usd / cost_tot * 100
        pnl_thb  = pnl_usd * THB_RATE
        total_val  += val
        total_cost += cost_tot
        sig, reason = get_signal(d.get("rsi"), d.get("change_pct", 0),
                                  d.get("high_52w"), d.get("low_52w"), d["price"])
        port_rows.append({
            "sym": sym, "shares": info["shares"], "cost": info["cost"],
            "price": d["price"], "pnl_usd": pnl_usd, "pnl_pct": pnl_pct,
            "pnl_thb": pnl_thb, "sig": sig, "rsi": d.get("rsi"),
            "chg": d.get("change_pct", 0), "reason": reason,
        })

    total_pnl     = total_val - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    total_pnl_thb = total_pnl * THB_RATE

    # --- Assemble markdown ---
    L = []
    L.append(f"---")
    L.append(f"title: Market Analysis {TODAY}")
    L.append(f"type: analysis")
    L.append(f"tags: [daily-update, stocks, portfolio]")
    L.append(f"sources: []")
    L.append(f"created: {TODAY}")
    L.append(f"updated: {TODAY}")
    L.append(f"---")
    L.append(f"")
    L.append(f"# Market Analysis -- {TODAY}")
    L.append(f"")
    L.append(f"Auto-generated daily update from Yahoo Finance.")
    L.append(f"")

    # Market Overview
    L.append(f"## Market Overview")
    L.append(f"")
    L.append(f"| Index | Price | Change | RSI |")
    L.append(f"|-------|-------|--------|-----|")
    for etf in ETFS:
        d = market_data.get(etf, {})
        if "error" not in d and d.get("price"):
            arr = "+" if d["change_pct"] >= 0 else ""
            rsi = str(d["rsi"]) if d.get("rsi") else "-"
            L.append(f"| {etf} | ${d['price']:,.2f} | {arr}{d['change_pct']}% | {rsi} |")
    gd = market_data.get(GOLD, {})
    if "error" not in gd and gd.get("price"):
        arr = "+" if gd["change_pct"] >= 0 else ""
        L.append(f"| XAU/USD | ${gd['price']:,.2f} | {arr}{gd['change_pct']}% | - |")
    L.append(f"")

    # Commentary
    L.append(f"## Market Commentary")
    L.append(f"")
    L.append(market_commentary(market_data))
    L.append(f"")

    # Portfolio P&L
    pnl_sign = "+" if total_pnl >= 0 else ""
    L.append(f"## Portfolio P&L")
    L.append(f"")
    L.append(f"**Total P&L: {pnl_sign}${total_pnl:,.2f} ({pnl_sign}{total_pnl_pct:.2f}%) = {pnl_sign}{total_pnl_thb:,.0f} THB**")
    L.append(f"")
    L.append(f"| Symbol | Shares | Cost | Price | P&L USD | P&L THB | Signal | RSI | Day% |")
    L.append(f"|--------|--------|------|-------|---------|---------|--------|-----|------|")
    for r in port_rows:
        s = "+" if r["pnl_usd"] >= 0 else ""
        c = "+" if r["chg"] >= 0 else ""
        rsi = str(r["rsi"]) if r["rsi"] else "-"
        L.append(f"| {r['sym']} | {r['shares']} | ${r['cost']} | ${r['price']:,.2f} | {s}${r['pnl_usd']:,.2f} | {s}{r['pnl_thb']:,.0f} | {r['sig']} | {rsi} | {c}{r['chg']}% |")
    L.append(f"")

    # Watchlist
    L.append(f"## Watchlist")
    L.append(f"")
    L.append(f"| Symbol | Price | Day% | RSI | Signal | Note |")
    L.append(f"|--------|-------|------|-----|--------|------|")
    for sym in WATCHLIST:
        d = market_data.get(sym, {})
        if "error" in d or not d.get("price"):
            L.append(f"| {sym} | - | - | - | - | fetch error |")
            continue
        arr = "+" if d["change_pct"] >= 0 else ""
        rsi = str(d["rsi"]) if d.get("rsi") else "-"
        sig, reason = get_signal(d.get("rsi"), d.get("change_pct", 0),
                                  d.get("high_52w"), d.get("low_52w"), d["price"])
        L.append(f"| {sym} | ${d['price']:,.2f} | {arr}{d['change_pct']}% | {rsi} | {sig} | {reason} |")
    L.append(f"")

    # Key Levels
    L.append(f"## Key Levels")
    L.append(f"")
    for sym, info in PORTFOLIO.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        p  = d["price"]
        sl = round(info["cost"] * 0.90, 2)
        tp = round(info["cost"] * 1.20, 2)
        sp = round(p * 0.95, 2)
        rs = round(p * 1.05, 2)
        L.append(f"- **{sym}** ${p:,.2f} -- Support: ${sp} | Resistance: ${rs} | Stop: ${sl} | Target: ${tp}")
    L.append(f"")

    # See also
    L.append(f"## See also")
    L.append(f"- [[concepts/n8n-portfolio-tracker-workflow]]")
    L.append(f"- [[stocks/NVDA]]")
    L.append(f"- [[stocks/MSFT]]")
    L.append(f"- [[synthesis/เปรียบเทียบหุ้น-AI-Tech-2026]]")

    return "\n".join(L)


# ===== Index + Log update =====
def update_index(date: str):
    path = WIKI_DIR / "index.md"
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    if date in content:
        return
    new_row = f"| [[analysis/{date}]] | Daily market update -- Portfolio P&L, Signals, Watchlist | {date} |"
    marker  = "## Analysis"
    idx     = content.find(marker)
    if idx == -1:
        return
    table_sep = content.find("\n|---", idx)
    if table_sep == -1:
        return
    insert = content.find("\n", table_sep + 1)
    content = content[:insert] + "\n" + new_row + content[insert:]
    path.write_text(content, encoding="utf-8")


def append_log(date: str):
    path = WIKI_DIR / "log.md"
    entry = (
        f"\n## [{date}] update | Daily Market Analysis -- Auto-generated\n"
        f"- Fetched portfolio + watchlist + ETF prices from Yahoo Finance\n"
        f"- Calculated RSI-14, signals, P&L\n"
        f"- Created wiki/analysis/{date}.md\n"
    )
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if date in existing:
            return
        path.write_text(existing + entry, encoding="utf-8")
    else:
        path.write_text(entry, encoding="utf-8")


def update_stock_pages(market_data: dict, date: str):
    """Updates individual stocks/*.md files with latest metrics."""
    for ticker, d in market_data.items():
        if "error" in d or d.get("price", 0) == 0:
            continue
        path = STOCKS_DIR / f"{ticker}.md"
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        # Update updated: field
        content = _re.sub(r"updated: .*", f"updated: {date}", content)
        # Update Price in # header if exists or in list
        price_str = f"${d['price']:,.2f} ({date})"
        content = _re.sub(r"- \*\*ราคาปัจจุบัน:\*\* .*", f"- **ราคาปัจจุบัน:** {price_str}", content)
        
        # Update valuation table if exists
        mc_b = f"${d['market_cap']/1e9:.1f}B" if d.get('market_cap') else "N/A"
        content = _re.sub(r"\| Market Cap \| .*", f"| Market Cap | {mc_b} |", content)
        content = _re.sub(r"\| P/E \(TTM\) \| .*", f"| P/E (TTM) | {d.get('pe_ratio','N/A')}x |", content)
        
        path.write_text(content, encoding="utf-8")
    print("  Updated individual stock pages.")


# ===== Entry Point =====
def main():
    global THB_RATE
    THB_RATE = get_thb_rate()

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] Daily Wiki Update -- {TODAY}")

    all_tickers = list(PORTFOLIO.keys()) + WATCHLIST + ETFS + [GOLD, CRYPTO]

    print("  Batch fetching all tickers via yfinance...")
    market_data = fetch_all(all_tickers)

    # Fill any missing symbols with single fetch
    for ticker in all_tickers:
        if ticker not in market_data or market_data[ticker].get("price", 0) == 0:
            market_data[ticker] = get_quote(ticker)

    for ticker in all_tickers:
        d = market_data[ticker]
        if "error" not in d and d.get("price"):
            sign = "+" if d["change_pct"] >= 0 else ""
            pe   = f"  PE:{d['pe_ratio']:.1f}" if d.get("pe_ratio") else ""
            mc   = f"  MC:${d['market_cap']/1e9:.0f}B" if d.get("market_cap") else ""
            print(f"  {ticker:8}  ${d['price']:>10,.2f}  {sign}{d['change_pct']}%  RSI:{d['rsi'] or '?'}{pe}{mc}")
        else:
            print(f"  {ticker:8}  ERROR: {str(d.get('error','unknown'))[:60]}")

    # Build portfolio rows (needed for both wiki page and dashboard)
    port_rows  = []
    total_val  = 0.0
    total_cost = 0.0
    for sym, info in PORTFOLIO.items():
        d = market_data.get(sym, {})
        if not d.get("price"):
            continue
        val      = d["price"] * info["shares"]
        cost_tot = info["cost"] * info["shares"]
        pnl_usd  = val - cost_tot
        pnl_pct  = pnl_usd / cost_tot * 100
        pnl_thb  = pnl_usd * THB_RATE
        total_val  += val
        total_cost += cost_tot
        sig, reason = get_signal(d.get("rsi"), d.get("change_pct", 0),
                                  d.get("high_52w"), d.get("low_52w"), d["price"])
        port_rows.append({
            "sym": sym, "shares": info["shares"], "cost": info["cost"],
            "price": d["price"], "pnl_usd": pnl_usd, "pnl_pct": pnl_pct,
            "pnl_thb": pnl_thb, "sig": sig, "rsi": d.get("rsi"),
            "chg": d.get("change_pct", 0), "reason": reason,
        })
    total_pnl     = total_val - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0
    total_pnl_thb = total_pnl * THB_RATE

    page = build_page(market_data)
    out  = ANALYSIS_DIR / f"{TODAY}.md"
    out.write_text(page, encoding="utf-8")
    print(f"\n  Wrote wiki: {out}")

    # ── Enrich with Finviz + Earnings Date (short interest, insider, D/E, div) ──
    try:
        from at_analysis import fetch_finviz, fetch_earnings_date, fetch_marketaux_news
        import time as _time
        enrich_syms = [t for t in all_tickers if "=" not in t and t != "BTC-USD"]
        print(f"\n  Enriching {len(enrich_syms)} stocks (Finviz + Earnings + MarketAux) ...")
        for ticker in enrich_syms:
            try:
                fv = fetch_finviz(ticker)
                if fv:
                    market_data.setdefault(ticker, {}).update(fv)
                ed = fetch_earnings_date(ticker)
                if ed.get("earnings_days_away") is not None:
                    market_data.setdefault(ticker, {}).update(ed)
                # MarketAux news (replaces Yahoo RSS if key available)
                mx_news = fetch_marketaux_news(ticker)
                if mx_news:
                    market_data.setdefault(ticker, {})["news"] = mx_news
                _time.sleep(0.35)   # Finviz rate limit (polite)
            except Exception:
                pass
        print(f"  Enrichment done.")
    except ImportError:
        pass

    # ── FRED Macro (fetch once, share everywhere) ──────────────────────────
    macro = {}
    try:
        from at_analysis import fetch_macro
        print("\n  Fetching FRED macro data ...")
        macro = fetch_macro()
        regime = macro.get("regime", "?")
        vix    = macro.get("vix", "?")
        rate   = macro.get("fed_rate", "?")
        yc     = macro.get("yield_curve", "?")
        dxy    = macro.get("dxy", "?")
        oil    = macro.get("oil", "?")
        print(f"  Macro: regime={regime} | FedRate={rate} | VIX={vix} | YC={yc} | DXY={dxy} | Oil={oil}")
    except Exception as e:
        print(f"  Macro fetch error: {e}")

    qqq_chg = market_data.get("QQQ", {}).get("change_pct", 0) or 0
    mood    = "BULL" if qqq_chg > 0.5 else "BEAR" if qqq_chg < -0.5 else "NEUTRAL"
    macro.setdefault("qqq_chg", qqq_chg)
    macro.setdefault("mood", mood)

    # ── ArtheeNoi Vault Picks ──────────────────────────────────────────────
    vault_tickers = []
    vault_all     = []
    try:
        import at_stock_vault as vault_mod
        vault_all = vault_mod.VAULT  # set immediately — even if picks fail, คลังหุ้นยังแสดง
        print(f"\n  Vault pick (regime={macro.get('regime','?')}, QQQ{qqq_chg:+.1f}%, mood={mood}) ...")
        vault_tickers = vault_mod.get_vault_picks(macro=macro, qqq_chg=qqq_chg,
                                                   market_mood=mood, n=50)
        new_tickers = [t for t in vault_tickers if t not in market_data]
        if new_tickers:
            print(f"  Fetching {len(new_tickers)} vault stocks (lite) ...")
            lite_data = vault_mod.fetch_picks_lite(new_tickers)
            market_data.update(lite_data)
        print(f"  Vault picks: {vault_tickers[:10]}... ({len(vault_tickers)} total)")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  Vault error: {e}")

    # ── Prefetch sector ETFs for watchlist stocks ─────────────────────────────
    try:
        from at_analysis import prefetch_sector_etfs
        # Watchlist + Portfolio sectors (approximate from name — ETF covers it)
        _ws = ["AI-SW", "Semis", "Fintech", "Utilities", "Telecom", "EV-Auto", "Mega-Tech"]
        print(f"  Prefetching sector ETFs for signals page ...")
        prefetch_sector_etfs(_ws, also_qqq=True)
    except Exception:
        pass

    # ── Paper Trade Tracker ────────────────────────────────────────────────────
    tracker_stats = {}
    try:
        import at_tracker as tracker
        qqq_price = (market_data.get("QQQ") or {}).get("price")

        # คำนวณ action ด้วย analyze() สำหรับแต่ละหุ้น
        import dashboard as _dash
        from at_analysis import ai_score_full as _ai_full
        _scored_all = []
        for sym in list(dict.fromkeys(WATCHLIST + vault_tickers)):  # unique, preserve order
            d = market_data.get(sym, {})
            if not d.get("price"):
                continue
            a = _dash.analyze(d)
            # ลอง ai_score_full ด้วย (ถ้ามีข้อมูลพอ)
            try:
                full = _ai_full(d, macro, "")
                a["action"]   = full.get("action", a["action"])
                a["ai_score"] = full.get("ai_score")
                a["stars"]    = full.get("stars", a["stars"])
            except Exception:
                pass
            if a.get("action") in ("BUY", "WATCH"):
                _scored_all.append({
                    "ticker":   sym,
                    "action":   a["action"],
                    "ai_score": a.get("ai_score"),
                    "stars":    a.get("stars"),
                    "sector":   d.get("sector", ""),
                })

        n_new = tracker.record_signals(_scored_all, market_data,
                                       qqq_price=qqq_price, thb_rate=THB_RATE)
        tracker.update_outcomes(market_data, qqq_price=qqq_price, thb_rate=THB_RATE)
        tracker_stats = tracker.get_stats()
        print(f"  Tracker: +{n_new} new signals | "
              f"paper portfolio {tracker_stats['paper']['current_val_thb']:.0f} THB "
              f"({tracker_stats['paper']['total_return_pct']:+.1f}%)")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  Tracker error: {e}")

    # ── Paper Options Tracker ──────────────────────────────────────────────────
    options_stats = {}
    try:
        import at_options_tracker as opt_tr
        fed_rate = macro.get("fed_rate", 3.63) / 100 if macro else 0.0363

        # อัปเดต position ที่มีอยู่
        opt_tr.update_positions(market_data, thb_rate=THB_RATE, r=fed_rate)

        # เปิดไม้ใหม่จาก BUY signals (เฉพาะ ai_score >= 65)
        buy_signals = [s for s in _scored_all if s.get("action") == "BUY"
                       and (s.get("ai_score") or 0) >= 65]
        n_opt = 0
        for sig in buy_signals[:3]:   # ลองแค่ 3 ตัวต่อวัน (ดึง option chain ช้า)
            opened = opt_tr.open_call(
                sig["ticker"], sig.get("ai_score", 50), sig.get("stars", 1),
                thb_rate=THB_RATE, r=fed_rate,
            )
            if opened:
                n_opt += 1
            time.sleep(0.5)

        options_stats = opt_tr.get_stats()
        print(f"  Options: +{n_opt} new | "
              f"portfolio {options_stats['current_val_thb']:.0f} THB "
              f"({options_stats['total_return_pct']:+.1f}%)")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  Options error: {e}")

    # Generate web dashboard
    try:
        import dashboard as dash
        dash_path = dash.generate(
            market_data, port_rows, WATCHLIST, ETFS, GOLD, CRYPTO,
            total_pnl, total_pnl_thb, total_pnl_pct, total_val, THB_RATE,
            vault_tickers=vault_tickers,
            vault_all=vault_all,
            macro=macro,
            tracker=tracker_stats,
            options_stats=options_stats,
        )
        print(f"  Wrote dashboard: {dash_path}")
    except Exception as e:
        print(f"  Dashboard error: {e}")

    update_index(TODAY)
    append_log(TODAY)
    update_stock_pages(market_data, TODAY)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done.")


if __name__ == "__main__":
    main()
