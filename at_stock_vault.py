"""
at_stock_vault.py — ArtheeNoi Stock Vault (Option A)
~600+ curated stocks. ArtheeNoi filters to top 75 picks/day.
Only picks get live yfinance data fetched.
"""

import json
import requests
import warnings
warnings.filterwarnings("ignore")

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "arthee-noi"
_HEADERS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _calc_rsi(closes: list, period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return round(100 - 100 / (1 + rs), 1)


def fetch_picks_lite(tickers: list) -> dict:
    """Fast fetch price + RSI only — no fundamentals scraping (< 3s/stock)."""
    results = {}
    for ticker in tickers:
        try:
            url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                   f"?interval=1d&range=35d")
            r = requests.get(url, headers=_HEADERS, verify=False, timeout=12)
            r.raise_for_status()
            result = r.json()["chart"]["result"][0]
            meta   = result["meta"]
            quote  = result["indicators"]["quote"][0]
            closes = [c for c in quote.get("close", []) if c is not None]
            price  = closes[-1] if closes else 0
            prev   = closes[-2] if len(closes) > 1 else price
            chg    = round((price - prev) / prev * 100, 2) if prev else 0
            results[ticker] = {
                "ticker":     ticker,
                "name":       meta.get("shortName", ticker),
                "price":      round(price, 2),
                "change_pct": chg,
                "high_52w":   meta.get("fiftyTwoWeekHigh"),
                "low_52w":    meta.get("fiftyTwoWeekLow"),
                "rsi":        _calc_rsi(closes),
                "closes":     closes,
                "closes30":   [round(c, 2) for c in closes[-30:]],
                "dates30":    [],
                "news":       [],
            }
        except Exception as e:
            results[ticker] = {"ticker": ticker, "error": str(e), "price": 0, "change_pct": 0}
    return results

# ── VAULT ─────────────────────────────────────────────────────────────────────
# {t: ticker, c: company, s: sector, tier: 1-3, note: keywords}
# tier 1=blue-chip  tier 2=growth/quality  tier 3=speculative
VAULT = [
    # AI / Semiconductors
    {"t":"NVDA","c":"NVIDIA","s":"Semis","tier":1,"note":"AI GPU datacenter"},
    {"t":"AMD","c":"Advanced Micro Devices","s":"Semis","tier":1,"note":"AI CPU GPU"},
    {"t":"AVGO","c":"Broadcom","s":"Semis","tier":1,"note":"AI networking chips"},
    {"t":"INTC","c":"Intel","s":"Semis","tier":2,"note":"turnaround fab"},
    {"t":"QCOM","c":"Qualcomm","s":"Semis","tier":1,"note":"mobile AI chips 5G"},
    {"t":"MRVL","c":"Marvell Tech","s":"Semis","tier":2,"note":"AI networking custom chip"},
    {"t":"TSM","c":"TSMC","s":"Semis","tier":1,"note":"foundry fab largest"},
    {"t":"ARM","c":"Arm Holdings","s":"Semis","tier":2,"note":"AI chip design architecture"},
    {"t":"SMCI","c":"Super Micro Computer","s":"Semis","tier":2,"note":"AI server rack"},
    {"t":"ANET","c":"Arista Networks","s":"Semis","tier":1,"note":"AI datacenter networking"},
    {"t":"ASML","c":"ASML Holding","s":"Semis","tier":1,"note":"EUV lithography monopoly"},
    {"t":"LRCX","c":"Lam Research","s":"Semis","tier":1,"note":"wafer fab equipment"},
    {"t":"AMAT","c":"Applied Materials","s":"Semis","tier":1,"note":"semiconductor equipment"},
    {"t":"KLAC","c":"KLA Corp","s":"Semis","tier":1,"note":"process control inspection"},
    {"t":"MU","c":"Micron Technology","s":"Semis","tier":1,"note":"HBM memory AI DRAM"},
    {"t":"ON","c":"ON Semiconductor","s":"Semis","tier":2,"note":"EV power SiC chips"},
    {"t":"ADI","c":"Analog Devices","s":"Semis","tier":1,"note":"analog mixed signal"},
    {"t":"MCHP","c":"Microchip Technology","s":"Semis","tier":1,"note":"embedded control MCU"},
    {"t":"TER","c":"Teradyne","s":"Semis","tier":2,"note":"chip testing automation"},
    {"t":"MPWR","c":"Monolithic Power","s":"Semis","tier":2,"note":"AI power management"},
    {"t":"SWKS","c":"Skyworks Solutions","s":"Semis","tier":2,"note":"RF chips 5G mobile"},
    {"t":"QRVO","c":"Qorvo","s":"Semis","tier":3,"note":"RF chips 5G"},
    {"t":"NXPI","c":"NXP Semiconductors","s":"Semis","tier":1,"note":"automotive IoT chips"},
    {"t":"STM","c":"STMicroelectronics","s":"Semis","tier":2,"note":"automotive IoT chips"},
    {"t":"ENTG","c":"Entegris","s":"Semis","tier":2,"note":"chip materials CMP"},
    {"t":"SNPS","c":"Synopsys","s":"EDA","tier":1,"note":"chip design EDA software"},
    {"t":"CDNS","c":"Cadence Design","s":"EDA","tier":1,"note":"chip design EDA software"},
    {"t":"ANSS","c":"ANSYS","s":"EDA","tier":1,"note":"simulation software engineering"},
    {"t":"CRUS","c":"Cirrus Logic","s":"Semis","tier":2,"note":"audio chips Apple supplier"},
    {"t":"ALGM","c":"Allegro MicroSystems","s":"Semis","tier":2,"note":"power sensing EV"},
    {"t":"ONTO","c":"Onto Innovation","s":"Semis","tier":2,"note":"metrology equipment"},
    {"t":"ACLS","c":"Axcelis Technologies","s":"Semis","tier":3,"note":"ion implant equipment"},
    {"t":"MKSI","c":"MKS Instruments","s":"Semis","tier":2,"note":"gas power semis equipment"},
    {"t":"LFUS","c":"Littelfuse","s":"Semis","tier":2,"note":"circuit protection fuse"},
    {"t":"DIOD","c":"Diodes Inc","s":"Semis","tier":3,"note":"discrete semiconductors"},
    {"t":"SITM","c":"SiTime","s":"Semis","tier":3,"note":"precision timing silicon"},
    {"t":"WOLF","c":"Wolfspeed","s":"Semis","tier":3,"note":"SiC EV power turnaround"},
    {"t":"SLAB","c":"Silicon Labs","s":"Semis","tier":2,"note":"IoT wireless chips"},
    {"t":"HIMX","c":"Himax Technologies","s":"Semis","tier":3,"note":"display driver AI AR"},
    {"t":"FORM","c":"FormFactor","s":"Semis","tier":3,"note":"probe cards testing"},
    {"t":"PLAB","c":"Photronics","s":"Semis","tier":3,"note":"photomasks semis"},
    {"t":"COHU","c":"Cohu","s":"Semis","tier":3,"note":"test equipment semis"},
    {"t":"ACMR","c":"ACM Research","s":"Semis","tier":3,"note":"wafer cleaning equipment"},
    {"t":"LSCC","c":"Lattice Semiconductor","s":"Semis","tier":2,"note":"low-power FPGA AI edge"},
    {"t":"AMKR","c":"Amkor Technology","s":"Semis","tier":2,"note":"advanced chip packaging"},
    {"t":"GFS","c":"GlobalFoundries","s":"Semis","tier":2,"note":"US foundry fab defense"},
    {"t":"TOWR","c":"Tower Semiconductor","s":"Semis","tier":2,"note":"analog specialty fab"},
    {"t":"UMC","c":"United Micro","s":"Semis","tier":2,"note":"foundry mature node"},
    {"t":"INDI","c":"indie Semiconductor","s":"Semis","tier":3,"note":"automotive AI sensing chips"},

    # AI Software / Cloud
    {"t":"NOW","c":"ServiceNow","s":"AI-SW","tier":1,"note":"enterprise AI platform workflows"},
    {"t":"PLTR","c":"Palantir","s":"AI-SW","tier":2,"note":"AI analytics defense gov AIP"},
    {"t":"SNOW","c":"Snowflake","s":"AI-SW","tier":2,"note":"AI data cloud"},
    {"t":"MDB","c":"MongoDB","s":"AI-SW","tier":2,"note":"AI developer data database"},
    {"t":"DDOG","c":"Datadog","s":"AI-SW","tier":2,"note":"AI observability monitoring"},
    {"t":"NET","c":"Cloudflare","s":"AI-SW","tier":2,"note":"edge AI network security CDN"},
    {"t":"CFLT","c":"Confluent","s":"AI-SW","tier":3,"note":"data streaming real-time"},
    {"t":"BILL","c":"Bill.com","s":"Fintech","tier":2,"note":"SMB finance AP AR AI"},
    {"t":"HUBS","c":"HubSpot","s":"AI-SW","tier":2,"note":"AI CRM marketing sales"},
    {"t":"VEEV","c":"Veeva Systems","s":"AI-SW","tier":1,"note":"pharma cloud CRM"},
    {"t":"WDAY","c":"Workday","s":"AI-SW","tier":1,"note":"HR ERP AI enterprise"},
    {"t":"CRM","c":"Salesforce","s":"AI-SW","tier":1,"note":"AI CRM Agentforce enterprise"},
    {"t":"ADBE","c":"Adobe","s":"AI-SW","tier":1,"note":"AI creative cloud Firefly"},
    {"t":"ORCL","c":"Oracle","s":"AI-SW","tier":1,"note":"cloud AI database GPU"},
    {"t":"IBM","c":"IBM","s":"AI-SW","tier":2,"note":"enterprise AI hybrid cloud WatsonX"},
    {"t":"ACN","c":"Accenture","s":"IT-Svc","tier":1,"note":"AI consulting digital services"},
    {"t":"INTU","c":"Intuit","s":"AI-SW","tier":1,"note":"AI fintech SMB TurboTax"},
    {"t":"DOCU","c":"DocuSign","s":"AI-SW","tier":2,"note":"AI agreements IAM IAI"},
    {"t":"TEAM","c":"Atlassian","s":"AI-SW","tier":2,"note":"AI developer tools Jira"},
    {"t":"GTLB","c":"GitLab","s":"AI-SW","tier":2,"note":"AI DevSecOps platform"},
    {"t":"MNDY","c":"monday.com","s":"AI-SW","tier":2,"note":"AI work management OS"},
    {"t":"ASAN","c":"Asana","s":"AI-SW","tier":3,"note":"AI project management"},
    {"t":"RNG","c":"RingCentral","s":"AI-SW","tier":2,"note":"AI UCaaS cloud comms"},
    {"t":"ZOOM","c":"Zoom Video","s":"AI-SW","tier":2,"note":"AI video platform"},
    {"t":"DBX","c":"Dropbox","s":"AI-SW","tier":2,"note":"AI cloud storage content"},
    {"t":"BOX","c":"Box","s":"AI-SW","tier":2,"note":"AI cloud content enterprise"},
    {"t":"AI","c":"C3.ai","s":"AI-SW","tier":3,"note":"enterprise AI apps"},
    {"t":"PATH","c":"UiPath","s":"AI-SW","tier":2,"note":"AI RPA automation"},
    {"t":"BBAI","c":"BigBear.ai","s":"AI-SW","tier":3,"note":"AI defense analytics"},
    {"t":"SOUN","c":"SoundHound AI","s":"AI-SW","tier":3,"note":"voice AI automotive"},
    {"t":"PEGA","c":"Pegasystems","s":"AI-SW","tier":2,"note":"AI workflow automation"},
    {"t":"NICE","c":"NICE Systems","s":"AI-SW","tier":2,"note":"AI cloud CX analytics"},
    {"t":"CDAY","c":"Ceridian HCM","s":"AI-SW","tier":2,"note":"AI HR payroll cloud"},
    {"t":"PAYC","c":"Paycom Software","s":"AI-SW","tier":2,"note":"AI HR payroll SaaS"},
    {"t":"PAYX","c":"Paychex","s":"IT-Svc","tier":1,"note":"HR payroll SMB"},
    {"t":"ADP","c":"ADP","s":"IT-Svc","tier":1,"note":"HR payroll enterprise largest"},
    {"t":"GWRE","c":"Guidewire","s":"AI-SW","tier":2,"note":"AI insurance software"},
    {"t":"PCTY","c":"Paylocity","s":"AI-SW","tier":2,"note":"AI HR cloud SMB"},
    {"t":"SPSC","c":"SPS Commerce","s":"AI-SW","tier":2,"note":"supply chain AI EDI"},
    {"t":"BRZE","c":"Braze","s":"AI-SW","tier":2,"note":"customer engagement AI"},
    {"t":"ZETA","c":"Zeta Global","s":"AI-SW","tier":3,"note":"AI marketing data cloud"},
    {"t":"INOD","c":"Innodata","s":"AI-Svc","tier":3,"note":"AI data annotation training"},
    {"t":"ALTR","c":"Altair Engineering","s":"AI-SW","tier":2,"note":"AI simulation HPC"},
    {"t":"EPAM","c":"EPAM Systems","s":"IT-Svc","tier":2,"note":"AI engineering software"},
    {"t":"GLOB","c":"Globant","s":"IT-Svc","tier":2,"note":"AI digital tech services LatAm"},
    {"t":"CIEN","c":"Ciena","s":"Network","tier":2,"note":"optical networking AI"},
    {"t":"JNPR","c":"Juniper Networks","s":"Network","tier":2,"note":"AI-driven networking HPE"},
    {"t":"CSCO","c":"Cisco Systems","s":"Network","tier":1,"note":"AI networking security enterprise"},
    {"t":"NTAP","c":"NetApp","s":"IT-Stor","tier":2,"note":"AI data infrastructure cloud"},
    {"t":"PSTG","c":"Pure Storage","s":"IT-Stor","tier":2,"note":"AI flash storage"},
    {"t":"WDC","c":"Western Digital","s":"IT-Stor","tier":2,"note":"storage HDD SSD cloud"},
    {"t":"STX","c":"Seagate Tech","s":"IT-Stor","tier":2,"note":"storage HDD AI nearline"},
    {"t":"VRNS","c":"Varonis","s":"Cyber","tier":2,"note":"data security AI insider"},
    {"t":"TENB","c":"Tenable","s":"Cyber","tier":2,"note":"vulnerability management"},
    {"t":"QLYS","c":"Qualys","s":"Cyber","tier":2,"note":"cloud security compliance"},
    {"t":"CVLT","c":"Commvault","s":"Cyber","tier":2,"note":"data protection backup"},
    {"t":"CHKP","c":"Check Point","s":"Cyber","tier":1,"note":"network security firewall"},
    {"t":"FTNT","c":"Fortinet","s":"Cyber","tier":1,"note":"AI network security platform"},
    {"t":"RPD","c":"Rapid7","s":"Cyber","tier":2,"note":"threat detection SIEM"},
    {"t":"CRWD","c":"CrowdStrike","s":"Cyber","tier":1,"note":"AI endpoint security Falcon"},
    {"t":"ZS","c":"Zscaler","s":"Cyber","tier":2,"note":"zero trust cloud security"},
    {"t":"OKTA","c":"Okta","s":"Cyber","tier":2,"note":"identity security SSO"},
    {"t":"PANW","c":"Palo Alto Networks","s":"Cyber","tier":1,"note":"AI security platform SASE"},
    {"t":"S","c":"SentinelOne","s":"Cyber","tier":2,"note":"AI autonomous cybersecurity"},

    # Quantum Computing
    {"t":"IONQ","c":"IonQ","s":"Quantum","tier":3,"note":"trapped ion quantum computing"},
    {"t":"QUBT","c":"Quantum Computing","s":"Quantum","tier":3,"note":"quantum optimization"},
    {"t":"RGTI","c":"Rigetti Computing","s":"Quantum","tier":3,"note":"superconducting quantum"},
    {"t":"QBTS","c":"D-Wave Quantum","s":"Quantum","tier":3,"note":"quantum annealing"},
    {"t":"ARQQ","c":"Arqit Quantum","s":"Quantum","tier":3,"note":"quantum encryption"},

    # Mega Cap / FAANG+
    {"t":"AAPL","c":"Apple","s":"Mega-Tech","tier":1,"note":"AI iPhone ecosystem services"},
    {"t":"MSFT","c":"Microsoft","s":"Mega-Tech","tier":1,"note":"AI cloud Copilot Azure"},
    {"t":"GOOGL","c":"Alphabet A","s":"Mega-Tech","tier":1,"note":"AI search Gemini Cloud YouTube"},
    {"t":"META","c":"Meta Platforms","s":"Mega-Tech","tier":1,"note":"AI social Llama Threads"},
    {"t":"AMZN","c":"Amazon","s":"Mega-Tech","tier":1,"note":"AI AWS ecommerce Alexa"},
    {"t":"TSLA","c":"Tesla","s":"EV-Auto","tier":1,"note":"FSD AI EV robotaxi Optimus"},
    {"t":"NFLX","c":"Netflix","s":"Streaming","tier":1,"note":"AI streaming content ads"},
    {"t":"SPOT","c":"Spotify","s":"Streaming","tier":2,"note":"AI music podcast"},
    {"t":"UBER","c":"Uber Tech","s":"Mobility","tier":1,"note":"AI rideshare delivery"},
    {"t":"LYFT","c":"Lyft","s":"Mobility","tier":3,"note":"AI rideshare"},
    {"t":"ABNB","c":"Airbnb","s":"Travel-Tech","tier":1,"note":"AI travel STR platform"},
    {"t":"BKNG","c":"Booking Holdings","s":"Travel-Tech","tier":1,"note":"AI travel OTA Priceline"},
    {"t":"DASH","c":"DoorDash","s":"Delivery","tier":2,"note":"AI food delivery"},
    {"t":"SNAP","c":"Snap","s":"Social","tier":3,"note":"AR AI social camera"},
    {"t":"PINS","c":"Pinterest","s":"Social","tier":2,"note":"AI visual discovery ads"},
    {"t":"RDDT","c":"Reddit","s":"Social","tier":2,"note":"AI community data search"},
    {"t":"RBLX","c":"Roblox","s":"Gaming","tier":2,"note":"AI metaverse UGC gaming"},

    # Finance / Banking
    {"t":"JPM","c":"JPMorgan Chase","s":"Bank","tier":1,"note":"biggest US bank AI Jamie Dimon"},
    {"t":"BAC","c":"Bank of America","s":"Bank","tier":1,"note":"retail bank AI Merrill"},
    {"t":"GS","c":"Goldman Sachs","s":"Bank","tier":1,"note":"investment bank trading AI"},
    {"t":"MS","c":"Morgan Stanley","s":"Bank","tier":1,"note":"wealth investment bank AI"},
    {"t":"WFC","c":"Wells Fargo","s":"Bank","tier":1,"note":"retail bank cap lift"},
    {"t":"C","c":"Citigroup","s":"Bank","tier":1,"note":"global bank restructure"},
    {"t":"USB","c":"US Bancorp","s":"Bank","tier":1,"note":"regional bank trust"},
    {"t":"PNC","c":"PNC Financial","s":"Bank","tier":1,"note":"regional bank tech"},
    {"t":"TFC","c":"Truist Financial","s":"Bank","tier":2,"note":"regional bank SE US"},
    {"t":"KEY","c":"KeyCorp","s":"Bank","tier":2,"note":"regional bank Midwest"},
    {"t":"MCB","c":"Metropolitan Bank","s":"Bank","tier":3,"note":"crypto-friendly NY bank"},
    {"t":"LPLA","c":"LPL Financial","s":"Fintech","tier":2,"note":"independent broker dealer"},
    {"t":"RJF","c":"Raymond James","s":"Bank","tier":2,"note":"wealth management investment"},
    {"t":"SCHW","c":"Schwab","s":"Brokerage","tier":1,"note":"retail brokerage AI"},
    {"t":"IBKR","c":"Interactive Brokers","s":"Brokerage","tier":2,"note":"algo trading platform"},
    {"t":"CBOE","c":"Cboe Global","s":"Exchange","tier":1,"note":"options exchange VIX"},
    {"t":"CME","c":"CME Group","s":"Exchange","tier":1,"note":"futures derivatives exchange"},
    {"t":"ICE","c":"Intercontinental Exchange","s":"Exchange","tier":1,"note":"NYSE exchange data"},
    {"t":"NDAQ","c":"Nasdaq Inc","s":"Exchange","tier":1,"note":"exchange tech index listings"},
    {"t":"MSCI","c":"MSCI Inc","s":"Fintech","tier":1,"note":"index analytics ESG"},
    {"t":"SPGI","c":"S&P Global","s":"Fintech","tier":1,"note":"ratings analytics data"},
    {"t":"MCO","c":"Moody's Corp","s":"Fintech","tier":1,"note":"credit ratings analytics"},
    {"t":"FDS","c":"FactSet","s":"Fintech","tier":2,"note":"financial data analytics"},
    {"t":"VRSK","c":"Verisk Analytics","s":"Fintech","tier":1,"note":"analytics insurance data"},
    {"t":"BX","c":"Blackstone","s":"Alt-Asset","tier":1,"note":"alternative investments PE REIT"},
    {"t":"KKR","c":"KKR & Co","s":"Alt-Asset","tier":1,"note":"PE infrastructure credit"},
    {"t":"APO","c":"Apollo Global","s":"Alt-Asset","tier":1,"note":"private credit PE"},
    {"t":"ARES","c":"Ares Management","s":"Alt-Asset","tier":1,"note":"private credit PE direct"},
    {"t":"CG","c":"Carlyle Group","s":"Alt-Asset","tier":2,"note":"PE alternative asset"},
    {"t":"TPG","c":"TPG Inc","s":"Alt-Asset","tier":2,"note":"PE growth equity"},
    {"t":"BLK","c":"BlackRock","s":"Asset-Mgmt","tier":1,"note":"largest asset manager ETF AI"},
    {"t":"STT","c":"State Street","s":"Asset-Mgmt","tier":1,"note":"institutional custodian SPDR"},
    {"t":"BK","c":"BNY Mellon","s":"Asset-Mgmt","tier":1,"note":"custody bank AI"},
    {"t":"BR","c":"Broadridge","s":"Fintech","tier":1,"note":"financial investor comms AI"},
    {"t":"FI","c":"Fiserv","s":"Fintech","tier":1,"note":"banking fintech Clover POS"},
    {"t":"FIS","c":"FIS","s":"Fintech","tier":2,"note":"financial technology banking"},
    {"t":"GPN","c":"Global Payments","s":"Fintech","tier":2,"note":"payment processing AI"},
    {"t":"JKHY","c":"Jack Henry","s":"Fintech","tier":2,"note":"community bank tech"},
    {"t":"WEX","c":"WEX Inc","s":"Fintech","tier":2,"note":"fleet payments health benefits"},
    {"t":"V","c":"Visa","s":"Payments","tier":1,"note":"payment network AI tokenization"},
    {"t":"MA","c":"Mastercard","s":"Payments","tier":1,"note":"payment network AI analytics"},
    {"t":"AXP","c":"American Express","s":"Payments","tier":1,"note":"premium payments rewards AI"},
    {"t":"COF","c":"Capital One","s":"Fintech","tier":1,"note":"AI credit card data bank"},
    {"t":"DFS","c":"Discover Financial","s":"Fintech","tier":1,"note":"credit card network Capital One"},
    {"t":"SYF","c":"Synchrony Financial","s":"Fintech","tier":2,"note":"retail credit partnership"},
    {"t":"ALLY","c":"Ally Financial","s":"Fintech","tier":2,"note":"online auto bank digital"},
    {"t":"SOFI","c":"SoFi Tech","s":"Fintech","tier":2,"note":"neobank AI student loan"},
    {"t":"NU","c":"Nu Holdings","s":"Fintech","tier":2,"note":"Brazil LatAm neobank AI"},
    {"t":"PYPL","c":"PayPal","s":"Fintech","tier":1,"note":"payments AI Venmo Braintree"},
    {"t":"SQ","c":"Block (Square)","s":"Fintech","tier":2,"note":"SMB payments Bitcoin Cash App"},
    {"t":"UPST","c":"Upstart","s":"Fintech","tier":3,"note":"AI credit lending model"},
    {"t":"AFRM","c":"Affirm","s":"Fintech","tier":3,"note":"BNPL AI Apple Pay"},
    {"t":"HOOD","c":"Robinhood","s":"Fintech","tier":2,"note":"retail trading crypto AI"},
    {"t":"COIN","c":"Coinbase","s":"Crypto","tier":2,"note":"crypto exchange regulated US"},
    {"t":"MSTR","c":"MicroStrategy","s":"Crypto","tier":3,"note":"Bitcoin treasury leverage"},
    {"t":"RIOT","c":"Riot Platforms","s":"Crypto","tier":3,"note":"Bitcoin mining datacenter"},
    {"t":"MARA","c":"Marathon Digital","s":"Crypto","tier":3,"note":"Bitcoin mining largest"},
    {"t":"CLSK","c":"CleanSpark","s":"Crypto","tier":3,"note":"Bitcoin mining clean energy"},
    {"t":"TOST","c":"Toast","s":"Fintech","tier":2,"note":"AI restaurant POS platform"},
    {"t":"NCNO","c":"nCino","s":"Fintech","tier":3,"note":"banking cloud AI origination"},
    {"t":"PGY","c":"Pagaya Tech","s":"Fintech","tier":3,"note":"AI credit lending network"},
    {"t":"MKTX","c":"MarketAxess","s":"Fintech","tier":2,"note":"bond trading AI electronic"},
    {"t":"EVTC","c":"Evertec","s":"Fintech","tier":2,"note":"LatAm payments fintech"},
    {"t":"DLO","c":"dLocal","s":"Fintech","tier":3,"note":"EM frontier market payments"},
    {"t":"ACIW","c":"ACI Worldwide","s":"Fintech","tier":2,"note":"real-time payment systems"},

    # Insurance
    {"t":"PGR","c":"Progressive","s":"Insurance","tier":1,"note":"AI auto insurance usage-based"},
    {"t":"CB","c":"Chubb","s":"Insurance","tier":1,"note":"commercial property specialty"},
    {"t":"TRV","c":"Travelers","s":"Insurance","tier":1,"note":"P&C insurance dividend"},
    {"t":"ALL","c":"Allstate","s":"Insurance","tier":1,"note":"auto home insurance AI"},
    {"t":"AFL","c":"Aflac","s":"Insurance","tier":1,"note":"supplemental cancer Japan"},
    {"t":"MET","c":"MetLife","s":"Insurance","tier":1,"note":"life insurance retirement"},
    {"t":"PRU","c":"Prudential","s":"Insurance","tier":1,"note":"life insurance asset mgmt"},
    {"t":"AON","c":"Aon","s":"Insurance","tier":1,"note":"reinsurance risk consulting"},
    {"t":"MMC","c":"Marsh McLennan","s":"Insurance","tier":1,"note":"risk insurance consulting"},
    {"t":"ACGL","c":"Arch Capital","s":"Insurance","tier":2,"note":"specialty reinsurance cat"},

    # Telecom
    {"t":"T","c":"AT&T","s":"Telecom","tier":2,"note":"telecom 5G fiber dividend"},
    {"t":"VZ","c":"Verizon","s":"Telecom","tier":2,"note":"telecom 5G dividend"},
    {"t":"TMUS","c":"T-Mobile US","s":"Telecom","tier":1,"note":"5G growth subscriber leader"},
    {"t":"CMCSA","c":"Comcast","s":"Telecom","tier":1,"note":"cable broadband NBCUniversal"},
    {"t":"CHTR","c":"Charter Comms","s":"Telecom","tier":2,"note":"cable internet broadband"},
    {"t":"LUMN","c":"Lumen Tech","s":"Telecom","tier":3,"note":"fiber network restructure"},
    {"t":"AMX","c":"America Movil","s":"Telecom","tier":2,"note":"LatAm telecom giant"},
    {"t":"IRDM","c":"Iridium Comms","s":"Satellite","tier":2,"note":"LEO satellite IoT"},
    {"t":"NOK","c":"Nokia","s":"Telecom","tier":2,"note":"5G network equipment AI"},
    {"t":"ASTS","c":"AST SpaceMobile","s":"Space","tier":2,"note":"satellite broadband direct-to-cell"},

    # Energy / Oil & Gas
    {"t":"XOM","c":"ExxonMobil","s":"Oil-Gas","tier":1,"note":"oil major dividend Permian CCS"},
    {"t":"CVX","c":"Chevron","s":"Oil-Gas","tier":1,"note":"oil major dividend Hess"},
    {"t":"COP","c":"ConocoPhillips","s":"Oil-Gas","tier":1,"note":"E&P efficient low-cost"},
    {"t":"OXY","c":"Occidental","s":"Oil-Gas","tier":2,"note":"Buffett play shale CCS"},
    {"t":"DVN","c":"Devon Energy","s":"Oil-Gas","tier":2,"note":"shale variable dividend"},
    {"t":"MPC","c":"Marathon Petroleum","s":"Refining","tier":1,"note":"refining margins"},
    {"t":"PSX","c":"Phillips 66","s":"Refining","tier":1,"note":"refining chemicals midstream"},
    {"t":"VLO","c":"Valero Energy","s":"Refining","tier":1,"note":"refining renewable diesel"},
    {"t":"HAL","c":"Halliburton","s":"Oil-Svc","tier":2,"note":"oilfield services AI digital"},
    {"t":"SLB","c":"Schlumberger","s":"Oil-Svc","tier":1,"note":"oilfield services digital"},
    {"t":"BKR","c":"Baker Hughes","s":"Oil-Svc","tier":2,"note":"oilfield tech LNG AI"},
    {"t":"CIVI","c":"Civitas Resources","s":"Oil-Gas","tier":3,"note":"DJ Permian E&P"},
    {"t":"SM","c":"SM Energy","s":"Oil-Gas","tier":3,"note":"E&P Permian Midland"},
    {"t":"MTDR","c":"Matador Resources","s":"Oil-Gas","tier":3,"note":"Permian E&P midstream"},

    # Utilities / Clean Energy
    {"t":"VST","c":"Vistra","s":"Utilities","tier":1,"note":"AI power nuclear Texas data center"},
    {"t":"CEG","c":"Constellation Energy","s":"Utilities","tier":1,"note":"AI nuclear clean power"},
    {"t":"NRG","c":"NRG Energy","s":"Utilities","tier":2,"note":"AI power retail Texas"},
    {"t":"NEE","c":"NextEra Energy","s":"Utilities","tier":1,"note":"clean wind solar largest"},
    {"t":"SO","c":"Southern Company","s":"Utilities","tier":1,"note":"nuclear AI data center"},
    {"t":"DUK","c":"Duke Energy","s":"Utilities","tier":1,"note":"nuclear clean energy grid"},
    {"t":"AEP","c":"AEP","s":"Utilities","tier":1,"note":"power AI data center grid"},
    {"t":"XEL","c":"Xcel Energy","s":"Utilities","tier":2,"note":"clean wind energy Midwest"},
    {"t":"PCG","c":"PG&E","s":"Utilities","tier":2,"note":"California utility EV grid"},
    {"t":"ED","c":"Con Edison","s":"Utilities","tier":1,"note":"NYC utility dividend stable"},
    {"t":"EXC","c":"Exelon","s":"Utilities","tier":1,"note":"nuclear grid utility regulated"},
    {"t":"ETR","c":"Entergy","s":"Utilities","tier":2,"note":"nuclear utility South AI"},
    {"t":"WEC","c":"WEC Energy","s":"Utilities","tier":1,"note":"clean energy Midwest dividend"},
    {"t":"FSLR","c":"First Solar","s":"Clean-NRG","tier":2,"note":"solar panels US made IRA"},
    {"t":"ENPH","c":"Enphase Energy","s":"Clean-NRG","tier":2,"note":"solar microinverter battery"},
    {"t":"SEDG","c":"SolarEdge","s":"Clean-NRG","tier":3,"note":"solar inverter turnaround"},
    {"t":"BE","c":"Bloom Energy","s":"Clean-NRG","tier":3,"note":"fuel cell hydrogen AI power"},
    {"t":"PLUG","c":"Plug Power","s":"Clean-NRG","tier":3,"note":"hydrogen fuel cell"},
    {"t":"CCJ","c":"Cameco","s":"Nuclear","tier":2,"note":"uranium largest miner"},
    {"t":"UEC","c":"Uranium Energy","s":"Nuclear","tier":3,"note":"uranium US domestic"},
    {"t":"SMR","c":"NuScale Power","s":"Nuclear","tier":3,"note":"SMR small modular reactor"},
    {"t":"OKLO","c":"Oklo","s":"Nuclear","tier":3,"note":"fast fission reactor AI data"},
    {"t":"BWXT","c":"BWX Technologies","s":"Nuclear","tier":2,"note":"nuclear components defense"},

    # Healthcare / Biotech
    {"t":"LLY","c":"Eli Lilly","s":"Pharma","tier":1,"note":"GLP-1 obesity Mounjaro AI drug"},
    {"t":"NVO","c":"Novo Nordisk","s":"Pharma","tier":1,"note":"GLP-1 Ozempic obesity largest"},
    {"t":"ABBV","c":"AbbVie","s":"Pharma","tier":1,"note":"immunology oncology Skyrizi"},
    {"t":"JNJ","c":"Johnson & Johnson","s":"Pharma","tier":1,"note":"medtech pharma diversified"},
    {"t":"MRK","c":"Merck","s":"Pharma","tier":1,"note":"Keytruda oncology blockbuster"},
    {"t":"PFE","c":"Pfizer","s":"Pharma","tier":2,"note":"pipeline rebuild post-COVID"},
    {"t":"AMGN","c":"Amgen","s":"Biotech","tier":1,"note":"obesity rare disease biosimilar"},
    {"t":"GILD","c":"Gilead Sciences","s":"Biotech","tier":1,"note":"HIV oncology cell therapy"},
    {"t":"BIIB","c":"Biogen","s":"Biotech","tier":2,"note":"Alzheimer Leqembi neuro"},
    {"t":"REGN","c":"Regeneron","s":"Biotech","tier":1,"note":"antibody oncology Dupixent"},
    {"t":"VRTX","c":"Vertex Pharma","s":"Biotech","tier":1,"note":"CF rare genetic CRISPR pain"},
    {"t":"MRNA","c":"Moderna","s":"Biotech","tier":2,"note":"mRNA cancer vaccine pipeline"},
    {"t":"BNTX","c":"BioNTech","s":"Biotech","tier":2,"note":"mRNA cancer AI drug"},
    {"t":"ALNY","c":"Alnylam Pharma","s":"Biotech","tier":2,"note":"RNAi rare disease silencer"},
    {"t":"IONS","c":"Ionis Pharma","s":"Biotech","tier":2,"note":"antisense RNA neuro ALS"},
    {"t":"SRPT","c":"Sarepta Therapy","s":"Biotech","tier":2,"note":"gene therapy Duchenne"},
    {"t":"CRSP","c":"CRISPR Therapeutics","s":"Biotech","tier":2,"note":"CRISPR gene editing cure"},
    {"t":"NTLA","c":"Intellia Therapeutics","s":"Biotech","tier":3,"note":"CRISPR in-vivo editing"},
    {"t":"BEAM","c":"Beam Therapeutics","s":"Biotech","tier":3,"note":"base editing gene therapy"},
    {"t":"HOLX","c":"Hologic","s":"Med-Tech","tier":2,"note":"women's health diagnostic imaging"},
    {"t":"DXCM","c":"Dexcom","s":"Med-Tech","tier":2,"note":"CGM continuous glucose AI"},
    {"t":"PODD","c":"Insulet","s":"Med-Tech","tier":2,"note":"OmniPod insulin tubeless"},
    {"t":"INSP","c":"Inspire Medical","s":"Med-Tech","tier":2,"note":"sleep apnea neurostim"},
    {"t":"ALGN","c":"Align Technology","s":"Med-Tech","tier":2,"note":"AI clear aligners Invisalign"},
    {"t":"IDXX","c":"IDEXX Labs","s":"Med-Tech","tier":1,"note":"veterinary diagnostics premium"},
    {"t":"ZTS","c":"Zoetis","s":"Animal","tier":1,"note":"animal medicine vaccines"},
    {"t":"TMO","c":"Thermo Fisher","s":"Life-Sci","tier":1,"note":"lab instruments genomics AI"},
    {"t":"DHR","c":"Danaher","s":"Life-Sci","tier":1,"note":"life science instruments AI"},
    {"t":"WAT","c":"Waters Corp","s":"Life-Sci","tier":2,"note":"analytical instruments HPLC"},
    {"t":"ILMN","c":"Illumina","s":"Genomics","tier":2,"note":"DNA sequencing genomics"},
    {"t":"PACB","c":"Pacific Biosciences","s":"Genomics","tier":3,"note":"long-read DNA HiFi"},
    {"t":"GH","c":"Guardant Health","s":"Biotech","tier":2,"note":"AI liquid biopsy cancer"},
    {"t":"EXAS","c":"Exact Sciences","s":"Biotech","tier":2,"note":"AI cancer detection Cologuard"},
    {"t":"NTRA","c":"Natera","s":"Genomics","tier":2,"note":"cfDNA prenatal cancer kidney"},
    {"t":"RXRX","c":"Recursion Pharma","s":"AI-Bio","tier":3,"note":"AI drug discovery biology"},
    {"t":"CERT","c":"Certara","s":"Biotech","tier":2,"note":"biosimulation drug AI FDA"},
    {"t":"HALO","c":"Halozyme","s":"Biotech","tier":2,"note":"drug delivery ENHANZE platform"},
    {"t":"EXEL","c":"Exelixis","s":"Biotech","tier":2,"note":"oncology cabozantinib XL"},
    {"t":"ARVN","c":"Arvinas","s":"Biotech","tier":3,"note":"PROTAC protein degrader cancer"},
    {"t":"TGTX","c":"TG Therapeutics","s":"Biotech","tier":3,"note":"MS immunology ublituximab"},
    {"t":"KYMR","c":"Kymera Therapeutics","s":"Biotech","tier":3,"note":"protein degradation TPD"},
    {"t":"MDT","c":"Medtronic","s":"Med-Tech","tier":1,"note":"medical devices cardiac robotic"},
    {"t":"BSX","c":"Boston Scientific","s":"Med-Tech","tier":1,"note":"cardiac rhythm interventional"},
    {"t":"EW","c":"Edwards Lifesciences","s":"Med-Tech","tier":1,"note":"heart valve TAVR critical"},
    {"t":"SYK","c":"Stryker","s":"Med-Tech","tier":1,"note":"orthopedic robotic surgery Mako"},
    {"t":"TDOC","c":"Teladoc Health","s":"Dig-Health","tier":3,"note":"AI telehealth virtual care"},
    {"t":"HIMS","c":"Hims & Hers","s":"Dig-Health","tier":3,"note":"telehealth compounding GLP"},
    {"t":"OSCR","c":"Oscar Health","s":"Fintech","tier":3,"note":"AI health insurance tech"},
    {"t":"HCA","c":"HCA Healthcare","s":"Hospital","tier":1,"note":"hospital AI largest US"},
    {"t":"THC","c":"Tenet Healthcare","s":"Hospital","tier":2,"note":"hospital ASC ambulatory"},
    {"t":"UNH","c":"UnitedHealth","s":"Health-Ins","tier":1,"note":"health insurance AI Optum"},
    {"t":"HUM","c":"Humana","s":"Health-Ins","tier":2,"note":"Medicare Advantage AI"},
    {"t":"ELV","c":"Elevance Health","s":"Health-Ins","tier":1,"note":"Blue Cross insurance AI"},
    {"t":"CNC","c":"Centene","s":"Health-Ins","tier":2,"note":"Medicaid managed care"},
    {"t":"CVS","c":"CVS Health","s":"Health-Ins","tier":2,"note":"pharmacy benefits Aetna"},
    {"t":"CI","c":"Cigna","s":"Health-Ins","tier":1,"note":"health insurance PBM Evernorth"},
    {"t":"MOH","c":"Molina Healthcare","s":"Health-Ins","tier":2,"note":"Medicaid Medicare"},

    # Consumer / Retail
    {"t":"COST","c":"Costco","s":"Retail","tier":1,"note":"warehouse retail AI premium"},
    {"t":"WMT","c":"Walmart","s":"Retail","tier":1,"note":"AI retail ecommerce pickup"},
    {"t":"TGT","c":"Target","s":"Retail","tier":2,"note":"omnichannel retail AI"},
    {"t":"HD","c":"Home Depot","s":"Retail","tier":1,"note":"home improvement AI pro"},
    {"t":"LOW","c":"Lowe's","s":"Retail","tier":1,"note":"home improvement AI"},
    {"t":"NKE","c":"Nike","s":"Consumer","tier":2,"note":"athletic brand DTC AI"},
    {"t":"LULU","c":"Lululemon","s":"Consumer","tier":1,"note":"premium athleisure AI"},
    {"t":"TJX","c":"TJX Companies","s":"Retail","tier":1,"note":"off-price retail TJ Maxx"},
    {"t":"ROST","c":"Ross Stores","s":"Retail","tier":1,"note":"off-price discount"},
    {"t":"ANF","c":"Abercrombie","s":"Retail","tier":2,"note":"teen apparel brand turnaround"},
    {"t":"AEO","c":"American Eagle","s":"Retail","tier":2,"note":"denim teen fashion Aerie"},
    {"t":"YETI","c":"YETI Holdings","s":"Consumer","tier":2,"note":"premium outdoor drinkware"},
    {"t":"ELF","c":"e.l.f. Beauty","s":"Consumer","tier":2,"note":"affordable beauty AI DTC"},
    {"t":"CELH","c":"Celsius Holdings","s":"Consumer","tier":2,"note":"energy drinks fitness AI"},
    {"t":"PG","c":"Procter & Gamble","s":"Staples","tier":1,"note":"consumer staples dividend"},
    {"t":"KO","c":"Coca-Cola","s":"Staples","tier":1,"note":"beverage dividend defensive"},
    {"t":"PEP","c":"PepsiCo","s":"Staples","tier":1,"note":"beverage snacks dividend"},
    {"t":"CL","c":"Colgate-Palmolive","s":"Staples","tier":1,"note":"oral care global defensive"},
    {"t":"CLX","c":"Clorox","s":"Staples","tier":2,"note":"cleaning home care"},
    {"t":"CHD","c":"Church & Dwight","s":"Staples","tier":2,"note":"consumer brands Arm Hammer"},
    {"t":"HRL","c":"Hormel Foods","s":"Staples","tier":2,"note":"food brands SPAM dividend"},
    {"t":"CAG","c":"Conagra Brands","s":"Staples","tier":2,"note":"packaged food value"},
    {"t":"GIS","c":"General Mills","s":"Staples","tier":2,"note":"cereal food pet Blue Buffalo"},
    {"t":"SJM","c":"J.M. Smucker","s":"Staples","tier":2,"note":"food brands Jif Folgers"},
    {"t":"CPB","c":"Campbell Soup","s":"Staples","tier":2,"note":"soup snacks Rao's premium"},
    {"t":"MKC","c":"McCormick","s":"Staples","tier":2,"note":"spices flavors global"},
    {"t":"MCD","c":"McDonald's","s":"Restaurant","tier":1,"note":"fast food AI global loyalty"},
    {"t":"SBUX","c":"Starbucks","s":"Restaurant","tier":1,"note":"coffee AI turnaround app"},
    {"t":"CMG","c":"Chipotle","s":"Restaurant","tier":1,"note":"fast casual AI digital"},
    {"t":"YUM","c":"Yum! Brands","s":"Restaurant","tier":1,"note":"KFC Pizza Hut Taco Bell"},
    {"t":"QSR","c":"Restaurant Brands","s":"Restaurant","tier":1,"note":"BK Popeyes Tim Hortons"},
    {"t":"TXRH","c":"Texas Roadhouse","s":"Restaurant","tier":1,"note":"casual steakhouse loyal"},
    {"t":"DRI","c":"Darden Restaurants","s":"Restaurant","tier":2,"note":"Olive Garden LongHorn"},
    {"t":"DPZ","c":"Domino's Pizza","s":"Restaurant","tier":2,"note":"pizza AI delivery loyalty"},
    {"t":"WING","c":"Wingstop","s":"Restaurant","tier":2,"note":"wings AI franchise digital"},
    {"t":"SHAK","c":"Shake Shack","s":"Restaurant","tier":3,"note":"premium burger expansion"},
    {"t":"FIVE","c":"Five Below","s":"Retail","tier":2,"note":"value teen retail expansion"},
    {"t":"DLTR","c":"Dollar Tree","s":"Retail","tier":2,"note":"dollar store value Family"},
    {"t":"DG","c":"Dollar General","s":"Retail","tier":2,"note":"dollar store rural US"},
    {"t":"ETSY","c":"Etsy","s":"E-Com","tier":2,"note":"craft marketplace AI"},
    {"t":"EBAY","c":"eBay","s":"E-Com","tier":2,"note":"marketplace recommerce AI"},
    {"t":"BJ","c":"BJ's Wholesale","s":"Retail","tier":2,"note":"warehouse club east US"},
    {"t":"BBWI","c":"Bath & Body Works","s":"Retail","tier":2,"note":"personal care retail"},

    # EV / Autonomous
    {"t":"RIVN","c":"Rivian Automotive","s":"EV-Auto","tier":2,"note":"EV truck van Amazon"},
    {"t":"LCID","c":"Lucid Group","s":"EV-Auto","tier":3,"note":"luxury EV Saudi sovereign"},
    {"t":"NIO","c":"NIO","s":"EV-Auto","tier":3,"note":"China EV smart premium"},
    {"t":"LI","c":"Li Auto","s":"EV-Auto","tier":3,"note":"China EV EREV profitable"},
    {"t":"XPEV","c":"XPeng","s":"EV-Auto","tier":3,"note":"China EV AI autonomous"},
    {"t":"GM","c":"General Motors","s":"Auto","tier":2,"note":"EV Cruise AI DOGE EV"},
    {"t":"F","c":"Ford","s":"Auto","tier":2,"note":"EV F-150 Lightning Pro"},
    {"t":"STLA","c":"Stellantis","s":"Auto","tier":2,"note":"Jeep Ram EV restructure"},
    {"t":"ACHR","c":"Archer Aviation","s":"eVTOL","tier":3,"note":"air taxi eVTOL FAA cert"},
    {"t":"JOBY","c":"Joby Aviation","s":"eVTOL","tier":3,"note":"air taxi eVTOL Toyota"},
    {"t":"BLNK","c":"Blink Charging","s":"EV-Infra","tier":3,"note":"EV charging stations"},
    {"t":"CHPT","c":"ChargePoint","s":"EV-Infra","tier":3,"note":"EV charging network"},
    {"t":"EVGO","c":"EVgo","s":"EV-Infra","tier":3,"note":"DC fast charging DCFC"},
    {"t":"LAZR","c":"Luminar Tech","s":"Auto-Tech","tier":3,"note":"LiDAR autonomous vehicle"},

    # Space / Defense
    {"t":"RTX","c":"Raytheon Tech","s":"Defense","tier":1,"note":"missile defense aerospace Pratt"},
    {"t":"LMT","c":"Lockheed Martin","s":"Defense","tier":1,"note":"F-35 missile THAAD"},
    {"t":"NOC","c":"Northrop Grumman","s":"Defense","tier":1,"note":"B-21 stealth space drone"},
    {"t":"GD","c":"General Dynamics","s":"Defense","tier":1,"note":"submarines Virginia Gulfstream"},
    {"t":"L3H","c":"L3Harris Tech","s":"Defense","tier":1,"note":"communications EW AI"},
    {"t":"KTOS","c":"Kratos Defense","s":"Defense","tier":2,"note":"drones AI defense UAV"},
    {"t":"HWM","c":"Howmet Aerospace","s":"Defense","tier":2,"note":"aerospace structures engines"},
    {"t":"TXT","c":"Textron","s":"Defense","tier":2,"note":"Bell helicopter Cessna drone"},
    {"t":"RKLB","c":"Rocket Lab","s":"Space","tier":2,"note":"small sat launch Neutron"},
    {"t":"LUNR","c":"Intuitive Machines","s":"Space","tier":3,"note":"lunar lander NASA CLPS"},
    {"t":"RDW","c":"Redwire Space","s":"Space","tier":3,"note":"space manufacturing solar"},
    {"t":"ONDS","c":"Ondas Holdings","s":"Defense","tier":3,"note":"industrial drones railroad AI"},
    {"t":"KRMN","c":"Karman Space","s":"Space","tier":3,"note":"space defense structures"},
    {"t":"GE","c":"GE Aerospace","s":"Defense","tier":1,"note":"jet engines AI defense LEAP"},

    # Industrial / Infrastructure
    {"t":"CAT","c":"Caterpillar","s":"Industrial","tier":1,"note":"AI construction mining equipment"},
    {"t":"DE","c":"Deere & Co","s":"Industrial","tier":1,"note":"AI precision ag equipment"},
    {"t":"HON","c":"Honeywell","s":"Industrial","tier":1,"note":"AI industrial automation software"},
    {"t":"MMM","c":"3M","s":"Industrial","tier":2,"note":"industrial materials consumer"},
    {"t":"BA","c":"Boeing","s":"Aerospace","tier":2,"note":"commercial jets defense turnaround"},
    {"t":"ITW","c":"Illinois Tool Works","s":"Industrial","tier":1,"note":"industrial segments dividend"},
    {"t":"ROK","c":"Rockwell Auto","s":"Industrial","tier":1,"note":"industrial AI automation PLC"},
    {"t":"EMR","c":"Emerson Electric","s":"Industrial","tier":1,"note":"automation software process"},
    {"t":"ETN","c":"Eaton","s":"Industrial","tier":1,"note":"electrical AI power management"},
    {"t":"AME","c":"AMETEK","s":"Industrial","tier":1,"note":"electronic instruments test"},
    {"t":"PH","c":"Parker Hannifin","s":"Industrial","tier":1,"note":"motion control hydraulics"},
    {"t":"DOV","c":"Dover Corp","s":"Industrial","tier":2,"note":"diversified industrial pumps"},
    {"t":"XYL","c":"Xylem","s":"Water","tier":2,"note":"water tech AI smart meter"},
    {"t":"AWK","c":"American Water Works","s":"Water","tier":1,"note":"water utility regulated"},
    {"t":"ECL","c":"Ecolab","s":"Chemicals","tier":1,"note":"water hygiene food safety AI"},
    {"t":"SHW","c":"Sherwin-Williams","s":"Chemicals","tier":1,"note":"paint coatings premium"},
    {"t":"PPG","c":"PPG Industries","s":"Chemicals","tier":2,"note":"coatings paint aerospace"},
    {"t":"DOW","c":"Dow Inc","s":"Chemicals","tier":2,"note":"materials chemicals packaging"},
    {"t":"DD","c":"DuPont","s":"Chemicals","tier":2,"note":"advanced materials AI safety"},
    {"t":"LYB","c":"LyondellBasell","s":"Chemicals","tier":2,"note":"plastic chemicals recycling"},
    {"t":"CTVA","c":"Corteva","s":"Ag-Chem","tier":2,"note":"seeds pesticides precision ag"},
    {"t":"FMC","c":"FMC Corp","s":"Ag-Chem","tier":2,"note":"crop protection biological"},
    {"t":"ADM","c":"Archer-Daniels-Midland","s":"Ag","tier":2,"note":"grain processing food"},
    {"t":"BG","c":"Bunge Global","s":"Ag","tier":2,"note":"grain oilseed processing"},
    {"t":"MOS","c":"The Mosaic Co","s":"Ag-Chem","tier":2,"note":"potash phosphate fertilizer"},
    {"t":"CF","c":"CF Industries","s":"Ag-Chem","tier":2,"note":"nitrogen fertilizer ammonia"},
    {"t":"ODFL","c":"Old Dominion","s":"Logistics","tier":1,"note":"LTL trucking premium service"},
    {"t":"FDX","c":"FedEx","s":"Logistics","tier":1,"note":"global logistics AI efficiency"},
    {"t":"UPS","c":"UPS","s":"Logistics","tier":1,"note":"global parcel logistics AI"},
    {"t":"CHRW","c":"CH Robinson","s":"Logistics","tier":2,"note":"freight broker AI platform"},
    {"t":"XPO","c":"XPO Inc","s":"Logistics","tier":2,"note":"LTL trucking AI platform"},
    {"t":"GXO","c":"GXO Logistics","s":"Logistics","tier":2,"note":"AI contract logistics warehouse"},
    {"t":"UNP","c":"Union Pacific","s":"Rail","tier":1,"note":"US freight railroad Western"},
    {"t":"CSX","c":"CSX Corp","s":"Rail","tier":1,"note":"US freight railroad Eastern"},
    {"t":"NSC","c":"Norfolk Southern","s":"Rail","tier":1,"note":"US freight railroad SE"},
    {"t":"WAB","c":"Wabtec","s":"Rail","tier":2,"note":"AI rail tech equipment loco"},

    # Materials / Mining
    {"t":"FCX","c":"Freeport-McMoRan","s":"Mining","tier":1,"note":"copper AI data center EV"},
    {"t":"NEM","c":"Newmont","s":"Mining","tier":1,"note":"gold miner largest global"},
    {"t":"GOLD","c":"Barrick Gold","s":"Mining","tier":2,"note":"gold miner Tier 1 mines"},
    {"t":"WPM","c":"Wheaton Precious","s":"Mining","tier":2,"note":"gold silver streaming royalty"},
    {"t":"AEM","c":"Agnico Eagle","s":"Mining","tier":1,"note":"gold miner Canada quality"},
    {"t":"FNV","c":"Franco-Nevada","s":"Mining","tier":1,"note":"royalty gold premium no-ops"},
    {"t":"RGLD","c":"Royal Gold","s":"Mining","tier":2,"note":"gold streaming royalty"},
    {"t":"PAAS","c":"Pan American Silver","s":"Mining","tier":2,"note":"silver gold miner"},
    {"t":"ALB","c":"Albemarle","s":"Mining","tier":2,"note":"lithium EV battery largest"},
    {"t":"LAC","c":"Lithium Americas","s":"Mining","tier":3,"note":"lithium Nevada Thacker Pass"},
    {"t":"MP","c":"MP Materials","s":"Mining","tier":2,"note":"rare earth magnets US supply"},
    {"t":"AA","c":"Alcoa","s":"Mining","tier":2,"note":"aluminum EV lightweighting"},
    {"t":"STLD","c":"Steel Dynamics","s":"Steel","tier":2,"note":"US steel mini-mill EV"},
    {"t":"NUE","c":"Nucor","s":"Steel","tier":1,"note":"US steel largest EV green"},
    {"t":"CLF","c":"Cleveland-Cliffs","s":"Steel","tier":2,"note":"US steel iron ore auto"},
    {"t":"SCCO","c":"Southern Copper","s":"Mining","tier":2,"note":"copper Mexico Peru largest"},

    # REIT
    {"t":"AMT","c":"American Tower","s":"REIT","tier":1,"note":"cell tower 5G AI dividend"},
    {"t":"CCI","c":"Crown Castle","s":"REIT","tier":1,"note":"cell tower 5G fiber small"},
    {"t":"PLD","c":"Prologis","s":"REIT","tier":1,"note":"logistics warehouse AI largest"},
    {"t":"EQIX","c":"Equinix","s":"REIT","tier":1,"note":"data center AI colocation global"},
    {"t":"DLR","c":"Digital Realty","s":"REIT","tier":1,"note":"data center AI cloud global"},
    {"t":"O","c":"Realty Income","s":"REIT","tier":1,"note":"net lease monthly dividend"},
    {"t":"WPC","c":"W.P. Carey","s":"REIT","tier":2,"note":"net lease industrial Europe"},
    {"t":"NNN","c":"NNN REIT","s":"REIT","tier":2,"note":"triple net lease retail"},
    {"t":"SPG","c":"Simon Property","s":"REIT","tier":1,"note":"premium mall outlet AI"},
    {"t":"EQR","c":"Equity Residential","s":"REIT","tier":1,"note":"apartment premium coast"},
    {"t":"AVB","c":"AvalonBay","s":"REIT","tier":1,"note":"apartment premium coastal"},
    {"t":"INVH","c":"Invitation Homes","s":"REIT","tier":2,"note":"single family rental"},
    {"t":"AMH","c":"American Homes 4 Rent","s":"REIT","tier":2,"note":"single family rental"},
    {"t":"SUI","c":"Sun Communities","s":"REIT","tier":2,"note":"mobile home community RV"},
    {"t":"WELL","c":"Welltower","s":"REIT","tier":1,"note":"senior care AI healthcare"},
    {"t":"VTR","c":"Ventas","s":"REIT","tier":2,"note":"senior care outpatient MOB"},
    {"t":"IRM","c":"Iron Mountain","s":"REIT","tier":1,"note":"data center storage AI records"},
    {"t":"STWD","c":"Starwood Property","s":"mREIT","tier":2,"note":"commercial real estate loans"},
    {"t":"BXMT","c":"Blackstone Mortgage","s":"mREIT","tier":2,"note":"commercial mortgage loans"},
    {"t":"ARCC","c":"Ares Capital","s":"BDC","tier":2,"note":"BDC largest direct lending"},
    {"t":"MAIN","c":"Main Street Capital","s":"BDC","tier":2,"note":"BDC SMB monthly dividend"},
    {"t":"HTGC","c":"Hercules Capital","s":"BDC","tier":2,"note":"BDC venture tech lending"},

    # Entertainment / Gaming / Media
    {"t":"EA","c":"Electronic Arts","s":"Gaming","tier":2,"note":"FIFA Madden AI gaming"},
    {"t":"TTWO","c":"Take-Two Interactive","s":"Gaming","tier":2,"note":"GTA6 2K NBA2K AI"},
    {"t":"U","c":"Unity Technologies","s":"Gaming","tier":2,"note":"game engine AI 3D"},
    {"t":"NTES","c":"NetEase","s":"Gaming","tier":2,"note":"China gaming AI premium"},
    {"t":"DIS","c":"Walt Disney","s":"Media","tier":2,"note":"streaming parks ESPN AI"},
    {"t":"PARA","c":"Paramount Global","s":"Media","tier":3,"note":"streaming CBS Skydance deal"},
    {"t":"WBD","c":"Warner Bros Discovery","s":"Media","tier":3,"note":"HBO Max CNN streaming"},
    {"t":"LYV","c":"Live Nation","s":"Entertain","tier":2,"note":"concerts ticketing venues"},
    {"t":"FOX","c":"Fox Corp","s":"Media","tier":2,"note":"news sports broadcasting"},
    {"t":"IMAX","c":"IMAX Corp","s":"Entertain","tier":3,"note":"premium film experience"},

    # AI Infrastructure / Niche
    {"t":"CRWV","c":"CoreWeave","s":"AI-Infra","tier":2,"note":"AI cloud GPU rental NVIDIA"},
    {"t":"SMTC","c":"Semtech","s":"Semis","tier":3,"note":"IoT LoRa silicon AI edge"},
    {"t":"BWA","c":"BorgWarner","s":"Auto-Tech","tier":2,"note":"EV powertrain components"},
    {"t":"SPCX","c":"SPAC/Space ETF","s":"Space","tier":3,"note":"space SpaceX proxy Starlink"},
    {"t":"EXPO","c":"Exponent Inc","s":"IT-Svc","tier":2,"note":"engineering consulting premium"},
    {"t":"SEIC","c":"SEI Investments","s":"Asset-Mgmt","tier":2,"note":"investment platform fintech"},
    {"t":"LPLA","c":"LPL Financial","s":"Fintech","tier":2,"note":"independent broker dealer"},

    # ── Airlines / Travel / Hospitality ──────────────────────────────────────
    {"t":"DAL","c":"Delta Air Lines","s":"Airline","tier":2,"note":"premium airline loyalty SkyMiles"},
    {"t":"UAL","c":"United Airlines","s":"Airline","tier":2,"note":"global network MileagePlus"},
    {"t":"AAL","c":"American Airlines","s":"Airline","tier":3,"note":"largest airline debt turnaround"},
    {"t":"LUV","c":"Southwest Airlines","s":"Airline","tier":2,"note":"low-cost domestic point-to-point"},
    {"t":"ALK","c":"Alaska Air","s":"Airline","tier":2,"note":"West Coast Hawaiian premium"},
    {"t":"JBLU","c":"JetBlue Airways","s":"Airline","tier":3,"note":"leisure airline turnaround"},
    {"t":"ALGT","c":"Allegiant Travel","s":"Airline","tier":3,"note":"ultra-low-cost leisure"},
    {"t":"SKYW","c":"SkyWest Airlines","s":"Airline","tier":3,"note":"regional airline feeder"},
    {"t":"MAR","c":"Marriott International","s":"Hotel","tier":1,"note":"largest hotel loyalty Bonvoy"},
    {"t":"HLT","c":"Hilton Worldwide","s":"Hotel","tier":1,"note":"hotel franchise Honors"},
    {"t":"H","c":"Hyatt Hotels","s":"Hotel","tier":2,"note":"luxury hotel World of Hyatt"},
    {"t":"WH","c":"Wyndham Hotels","s":"Hotel","tier":2,"note":"franchise economy select"},
    {"t":"CHH","c":"Choice Hotels","s":"Hotel","tier":2,"note":"economy mid-scale franchise"},
    {"t":"RCL","c":"Royal Caribbean","s":"Cruise","tier":2,"note":"cruise luxury Icon fleet"},
    {"t":"CCL","c":"Carnival Corp","s":"Cruise","tier":3,"note":"largest cruise group"},
    {"t":"NCLH","c":"Norwegian Cruise","s":"Cruise","tier":3,"note":"premium freestyle cruise"},
    {"t":"EXPE","c":"Expedia Group","s":"Travel-Tech","tier":2,"note":"OTA Vrbo Hotels.com AI"},
    {"t":"TRIP","c":"TripAdvisor","s":"Travel-Tech","tier":3,"note":"travel review booking AI"},
    {"t":"PCLN","c":"Priceline (BKNG)","s":"Travel-Tech","tier":1,"note":"see BKNG"},
    {"t":"TNL","c":"Travel + Leisure","s":"Travel-Tech","tier":3,"note":"vacation ownership timeshare"},

    # ── Homebuilders / Construction ───────────────────────────────────────────
    {"t":"DHI","c":"D.R. Horton","s":"Homebuilder","tier":1,"note":"largest homebuilder US"},
    {"t":"LEN","c":"Lennar Corp","s":"Homebuilder","tier":1,"note":"homebuilder AI modular"},
    {"t":"PHM","c":"PulteGroup","s":"Homebuilder","tier":1,"note":"homebuilder diverse buyer"},
    {"t":"TOL","c":"Toll Brothers","s":"Homebuilder","tier":2,"note":"luxury homebuilder premium"},
    {"t":"NVR","c":"NVR Inc","s":"Homebuilder","tier":1,"note":"Ryan Homes conservative capital"},
    {"t":"MDC","c":"M.D.C. Holdings","s":"Homebuilder","tier":2,"note":"homebuilder Traton"},
    {"t":"KBH","c":"KB Home","s":"Homebuilder","tier":2,"note":"built-to-order entry homebuilder"},
    {"t":"MTH","c":"Meritage Homes","s":"Homebuilder","tier":2,"note":"energy efficient homebuilder"},
    {"t":"LGIH","c":"LGI Homes","s":"Homebuilder","tier":2,"note":"entry-level homebuilder"},
    {"t":"TMHC","c":"Taylor Morrison","s":"Homebuilder","tier":2,"note":"attainable luxury homebuilder"},
    {"t":"GRBK","c":"Green Brick Partners","s":"Homebuilder","tier":3,"note":"Texas homebuilder infill"},
    {"t":"CVCO","c":"Cavco Industries","s":"Homebuilder","tier":2,"note":"manufactured housing affordable"},
    {"t":"SKY","c":"Skyline Champion","s":"Homebuilder","tier":2,"note":"manufactured homes affordable"},
    {"t":"ACM","c":"AECOM","s":"Construct","tier":2,"note":"infrastructure engineering design"},
    {"t":"PWR","c":"Quanta Services","s":"Construct","tier":1,"note":"power grid infrastructure AI"},
    {"t":"MTZ","c":"MasTec","s":"Construct","tier":2,"note":"5G utility pipeline construction"},
    {"t":"PRIM","c":"Primoris Services","s":"Construct","tier":3,"note":"utility infrastructure pipeline"},
    {"t":"J","c":"Jacobs Solutions","s":"Construct","tier":2,"note":"engineering consulting government"},
    {"t":"FLR","c":"Fluor Corp","s":"Construct","tier":2,"note":"engineering EPC nuclear"},
    {"t":"EME","c":"EMCOR Group","s":"Construct","tier":2,"note":"mechanical electrical contractor"},
    {"t":"STRL","c":"Sterling Infrastructure","s":"Construct","tier":2,"note":"data center construction"},

    # ── Oil & Gas Midstream / MLP ─────────────────────────────────────────────
    {"t":"ET","c":"Energy Transfer","s":"Midstream","tier":2,"note":"MLP pipeline large yield"},
    {"t":"EPD","c":"Enterprise Prod Partners","s":"Midstream","tier":1,"note":"MLP midstream NGL premium"},
    {"t":"MPLX","c":"MPLX LP","s":"Midstream","tier":2,"note":"MLP Marathon midstream"},
    {"t":"OKE","c":"ONEOK","s":"Midstream","tier":1,"note":"natural gas pipeline Magellan"},
    {"t":"KMI","c":"Kinder Morgan","s":"Midstream","tier":2,"note":"natural gas pipeline CO2"},
    {"t":"LNG","c":"Cheniere Energy","s":"Midstream","tier":1,"note":"LNG export largest US"},
    {"t":"TRGP","c":"Targa Resources","s":"Midstream","tier":2,"note":"NGL midstream Permian"},
    {"t":"WES","c":"Western Midstream","s":"Midstream","tier":2,"note":"Permian midstream gas"},
    {"t":"AM","c":"Antero Midstream","s":"Midstream","tier":3,"note":"Appalachian midstream"},
    {"t":"CTRA","c":"Coterra Energy","s":"Oil-Gas","tier":2,"note":"natural gas Marcellus Permian"},
    {"t":"AR","c":"Antero Resources","s":"Oil-Gas","tier":2,"note":"Appalachian nat gas LNG"},
    {"t":"EQT","c":"EQT Corp","s":"Oil-Gas","tier":2,"note":"largest US nat gas producer"},
    {"t":"RRC","c":"Range Resources","s":"Oil-Gas","tier":2,"note":"Appalachian natural gas"},
    {"t":"SWN","c":"Southwestern Energy","s":"Oil-Gas","tier":3,"note":"natural gas Appalachian"},
    {"t":"CHK","c":"Chesapeake Energy","s":"Oil-Gas","tier":3,"note":"natural gas reborn post-BK"},

    # ── Regional Banks (expanded) ─────────────────────────────────────────────
    {"t":"FITB","c":"Fifth Third Bancorp","s":"Reg-Bank","tier":2,"note":"Midwest regional bank"},
    {"t":"RF","c":"Regions Financial","s":"Reg-Bank","tier":2,"note":"Southeast regional bank"},
    {"t":"ZION","c":"Zions Bancorporation","s":"Reg-Bank","tier":2,"note":"Western regional bank"},
    {"t":"CFG","c":"Citizens Financial","s":"Reg-Bank","tier":2,"note":"New England regional"},
    {"t":"MTB","c":"M&T Bank","s":"Reg-Bank","tier":2,"note":"Mid-Atlantic community bank"},
    {"t":"HBAN","c":"Huntington Bancshares","s":"Reg-Bank","tier":2,"note":"Midwest regional"},
    {"t":"EWBC","c":"East West Bancorp","s":"Reg-Bank","tier":2,"note":"Asian-American bridge bank"},
    {"t":"FFIN","c":"First Financial Bankshares","s":"Reg-Bank","tier":2,"note":"Texas community bank"},
    {"t":"WTFC","c":"Wintrust Financial","s":"Reg-Bank","tier":2,"note":"Chicago community bank"},
    {"t":"BOKF","c":"BOK Financial","s":"Reg-Bank","tier":2,"note":"Oklahoma regional bank"},
    {"t":"UMBF","c":"UMB Financial","s":"Reg-Bank","tier":2,"note":"KC diversified bank"},
    {"t":"IBCP","c":"Independent Bank Corp","s":"Reg-Bank","tier":3,"note":"Michigan community bank"},
    {"t":"CVBF","c":"CVB Financial","s":"Reg-Bank","tier":3,"note":"California business bank"},
    {"t":"CATY","c":"Cathay General Bancorp","s":"Reg-Bank","tier":2,"note":"Chinese-American bank CA"},
    {"t":"HTLF","c":"Heartland Financial","s":"Reg-Bank","tier":3,"note":"Midwest community bank"},
    {"t":"PACW","c":"PacWest Bancorp","s":"Reg-Bank","tier":3,"note":"California tech bank"},
    {"t":"WAL","c":"Western Alliance","s":"Reg-Bank","tier":2,"note":"Southwest commercial bank"},
    {"t":"SFNC","c":"Simmons Financial","s":"Reg-Bank","tier":3,"note":"Arkansas regional bank"},
    {"t":"RNST","c":"Renasant Corp","s":"Reg-Bank","tier":3,"note":"Southeast community bank"},
    {"t":"CCNE","c":"CNB Financial","s":"Reg-Bank","tier":3,"note":"Pennsylvania community bank"},

    # ── Government IT / Defense Services ─────────────────────────────────────
    {"t":"SAIC","c":"Science Applications Intl","s":"Gov-IT","tier":2,"note":"government IT defense AI"},
    {"t":"LDOS","c":"Leidos Holdings","s":"Gov-IT","tier":2,"note":"defense IT health federal"},
    {"t":"CACI","c":"CACI International","s":"Gov-IT","tier":2,"note":"defense intelligence IT"},
    {"t":"MANT","c":"ManTech International","s":"Gov-IT","tier":2,"note":"federal defense IT cyber"},
    {"t":"BAH","c":"Booz Allen Hamilton","s":"Gov-IT","tier":1,"note":"management consulting AI defense"},
    {"t":"HII","c":"Huntington Ingalls","s":"Defense","tier":2,"note":"nuclear subs carriers shipbuilder"},
    {"t":"VRSN","c":"VeriSign","s":"Internet","tier":1,"note":"internet domain registry .com"},
    {"t":"DXC","c":"DXC Technology","s":"IT-Svc","tier":3,"note":"IT services outsourcing turnaround"},

    # ── Auto Parts / Services ─────────────────────────────────────────────────
    {"t":"ORLY","c":"O'Reilly Auto Parts","s":"Auto-Svc","tier":1,"note":"auto parts retail premium"},
    {"t":"AZO","c":"AutoZone","s":"Auto-Svc","tier":1,"note":"auto parts largest buyback"},
    {"t":"AAP","c":"Advance Auto Parts","s":"Auto-Svc","tier":3,"note":"auto parts turnaround"},
    {"t":"GPC","c":"Genuine Parts","s":"Auto-Svc","tier":1,"note":"NAPA auto parts industrial"},
    {"t":"LKQ","c":"LKQ Corp","s":"Auto-Svc","tier":2,"note":"aftermarket auto parts Europe"},
    {"t":"PRTS","c":"CarParts.com","s":"Auto-Svc","tier":3,"note":"online auto parts ecommerce"},
    {"t":"GT","c":"Goodyear Tire","s":"Auto-Svc","tier":3,"note":"tire manufacturer EV"},
    {"t":"MGA","c":"Magna International","s":"Auto-Parts","tier":2,"note":"auto supplier EV systems"},
    {"t":"APTV","c":"Aptiv","s":"Auto-Parts","tier":2,"note":"auto tech ADAS software"},
    {"t":"VC","c":"Visteon","s":"Auto-Parts","tier":2,"note":"cockpit electronics EV"},
    {"t":"DAN","c":"Dana Inc","s":"Auto-Parts","tier":3,"note":"EV driveline thermal"},
    {"t":"LEA","c":"Lear Corp","s":"Auto-Parts","tier":2,"note":"seating electrical auto"},
    {"t":"ALV","c":"Autoliv","s":"Auto-Parts","tier":2,"note":"airbag seatbelt safety"},
    {"t":"GNTX","c":"Gentex Corp","s":"Auto-Parts","tier":2,"note":"auto dimming mirror camera"},
    {"t":"MODV","c":"ModivCare","s":"Healthcare","tier":3,"note":"non-emergency transport home"},
    {"t":"CVNA","c":"Carvana","s":"Auto","tier":3,"note":"AI online used car ecommerce"},
    {"t":"KMX","c":"CarMax","s":"Auto","tier":2,"note":"used car retail omnichannel"},
    {"t":"AN","c":"AutoNation","s":"Auto","tier":2,"note":"dealership group EV service"},
    {"t":"LAD","c":"Lithia Motors","s":"Auto","tier":2,"note":"dealership DT omnichannel AI"},
    {"t":"PAG","c":"Penske Automotive","s":"Auto","tier":2,"note":"premium dealership truck"},

    # ── Environmental / Waste ─────────────────────────────────────────────────
    {"t":"WM","c":"Waste Management","s":"Environment","tier":1,"note":"waste recycling premium"},
    {"t":"RSG","c":"Republic Services","s":"Environment","tier":1,"note":"waste recycling landfill"},
    {"t":"CLH","c":"Clean Harbors","s":"Environment","tier":2,"note":"hazmat industrial clean"},
    {"t":"CWST","c":"Casella Waste","s":"Environment","tier":2,"note":"Northeast waste Northeast"},
    {"t":"SRCL","c":"Stericycle","s":"Environment","tier":3,"note":"medical waste secure"},
    {"t":"HCCI","c":"Heritage Crystal Clean","s":"Environment","tier":3,"note":"parts cleaning industrial"},
    {"t":"PQG","c":"PureCycle Tech","s":"Environment","tier":3,"note":"plastic recycling chemical"},
    {"t":"CEVA","c":"CEVA Logistics","s":"Logistics","tier":3,"note":"3PL supply chain tech"},

    # ── Rental / Equipment ────────────────────────────────────────────────────
    {"t":"URI","c":"United Rentals","s":"Rental","tier":1,"note":"equipment rental AI largest"},
    {"t":"TREX","c":"Trex Company","s":"Consumer","tier":2,"note":"composite decking premium"},
    {"t":"H","c":"Hertz Global","s":"Rental","tier":3,"note":"car rental EV turnaround"},
    {"t":"CAR","c":"Avis Budget","s":"Rental","tier":3,"note":"car rental EV commercial"},
    {"t":"GATX","c":"GATX Corp","s":"Rental","tier":2,"note":"railcar leasing dividend"},
    {"t":"TRTN","c":"Triton International","s":"Rental","tier":2,"note":"shipping container leasing"},
    {"t":"GBX","c":"Greenbrier Companies","s":"Rail","tier":3,"note":"railcar manufacturing leasing"},
    {"t":"FTAI","c":"FTAI Aviation","s":"Rental","tier":2,"note":"jet engine leasing maintenance"},
    {"t":"AL","c":"Air Lease Corp","s":"Rental","tier":2,"note":"commercial aircraft leasing"},
    {"t":"AER","c":"AerCap Holdings","s":"Rental","tier":2,"note":"aircraft leasing largest"},

    # ── Specialty Pharma / Med ────────────────────────────────────────────────
    {"t":"JAZZ","c":"Jazz Pharmaceuticals","s":"Spec-Pharma","tier":2,"note":"sleep narcolepsy oncology"},
    {"t":"CTLT","c":"Catalent","s":"CDMO","tier":3,"note":"drug manufacturing CDMO"},
    {"t":"PRGO","c":"Perrigo","s":"Spec-Pharma","tier":3,"note":"consumer OTC generic"},
    {"t":"SUPN","c":"Supernus Pharma","s":"Spec-Pharma","tier":3,"note":"CNS neurology specialty"},
    {"t":"ITCI","c":"Intra-Cellular Therapies","s":"Spec-Pharma","tier":2,"note":"CNS psychiatry FDA"},
    {"t":"PRAX","c":"Praxis Precision Medicine","s":"Biotech","tier":3,"note":"neurological genetic"},
    {"t":"ACAD","c":"Acadia Pharma","s":"Spec-Pharma","tier":3,"note":"CNS rare Rett syndrome"},
    {"t":"AXSM","c":"Axsome Therapeutics","s":"Spec-Pharma","tier":3,"note":"CNS AXS depression sleep"},
    {"t":"AUPH","c":"Aurinia Pharmaceuticals","s":"Spec-Pharma","tier":3,"note":"lupus nephritis"},
    {"t":"HRMY","c":"Harmony Biosciences","s":"Spec-Pharma","tier":3,"note":"narcolepsy sleep CNS"},
    {"t":"NKTR","c":"Nektar Therapeutics","s":"Biotech","tier":3,"note":"polymer-drug platform"},
    {"t":"PRLD","c":"Prelude Therapeutics","s":"Biotech","tier":3,"note":"epigenetic oncology"},
    {"t":"CYTK","c":"Cytokinetics","s":"Biotech","tier":2,"note":"muscle biology heart failure"},
    {"t":"RVMD","c":"Revolution Medicines","s":"Biotech","tier":3,"note":"RAS oncology targeted"},
    {"t":"ACLX","c":"Arcellx","s":"Biotech","tier":3,"note":"CAR-T myeloma CART"},
    {"t":"IMGO","c":"Imago BioSciences","s":"Biotech","tier":3,"note":"myeloproliferative rare"},
    {"t":"DNLI","c":"Denali Therapeutics","s":"Biotech","tier":3,"note":"neuro blood-brain AI"},
    {"t":"BLUE","c":"bluebird bio","s":"Biotech","tier":3,"note":"gene therapy sickle cell"},
    {"t":"FATE","c":"Fate Therapeutics","s":"Biotech","tier":3,"note":"iPSC cell therapy cancer"},
    {"t":"SAGE","c":"Sage Therapeutics","s":"Biotech","tier":3,"note":"CNS neurology depression"},
    {"t":"YMAB","c":"Y-mAbs Therapeutics","s":"Biotech","tier":3,"note":"antibody pediatric neuro"},
    {"t":"NUVB","c":"Nuvation Bio","s":"Biotech","tier":3,"note":"oncology precision"},
    {"t":"GOSS","c":"Gossamer Bio","s":"Biotech","tier":3,"note":"cardiopulmonary rare"},
    {"t":"ADMA","c":"ADMA Biologics","s":"Biotech","tier":3,"note":"plasma immunology"},

    # ── Healthcare Services / Tools ───────────────────────────────────────────
    {"t":"OMCL","c":"Omnicell","s":"Health-IT","tier":2,"note":"pharmacy automation AI"},
    {"t":"RCM","c":"R1 RCM","s":"Health-IT","tier":2,"note":"revenue cycle AI hospital"},
    {"t":"ACCD","c":"Accolade","s":"Dig-Health","tier":3,"note":"navigation AI health benefit"},
    {"t":"HCAT","c":"Health Catalyst","s":"Health-IT","tier":3,"note":"analytics AI hospital data"},
    {"t":"NXGN","c":"NextGen Healthcare","s":"Health-IT","tier":3,"note":"EHR ambulatory AI"},
    {"t":"MDRX","c":"Allscripts Healthcare","s":"Health-IT","tier":3,"note":"EHR hospital IT"},
    {"t":"PGNY","c":"Progyny","s":"Health-Svc","tier":3,"note":"fertility benefits employer"},
    {"t":"GDRX","c":"GoodRx","s":"Health-IT","tier":3,"note":"prescription price AI"},
    {"t":"PHR","c":"Phreesia","s":"Health-IT","tier":3,"note":"patient intake AI digital"},
    {"t":"AMWL","c":"American Well","s":"Dig-Health","tier":3,"note":"telehealth platform"},

    # ── Specialty Tech / IT Consulting ────────────────────────────────────────
    {"t":"CTSH","c":"Cognizant Tech","s":"IT-Svc","tier":2,"note":"IT consulting AI services India"},
    {"t":"WIT","c":"Wipro","s":"IT-Svc","tier":2,"note":"India IT services AI cloud"},
    {"t":"INFY","c":"Infosys","s":"IT-Svc","tier":2,"note":"India IT services AI transformation"},
    {"t":"HCL","c":"HCL Technologies","s":"IT-Svc","tier":2,"note":"India IT engineering AI"},
    {"t":"WNS","c":"WNS Holdings","s":"IT-Svc","tier":2,"note":"BPO analytics India AI"},
    {"t":"EXLS","c":"ExlService Holdings","s":"IT-Svc","tier":2,"note":"analytics BPO AI insurance"},
    {"t":"NSIT","c":"Insight Direct","s":"IT-Svc","tier":2,"note":"IT solutions hardware cloud"},
    {"t":"CDW","c":"CDW Corp","s":"IT-Svc","tier":1,"note":"IT products services enterprise"},
    {"t":"PC","c":"Panasonic","s":"IT-Svc","tier":2,"note":"EV battery electronics"},
    {"t":"TTEC","c":"TTEC Holdings","s":"IT-Svc","tier":3,"note":"CX AI automation services"},
    {"t":"TASK","c":"TaskUs","s":"IT-Svc","tier":3,"note":"AI content moderation BPO"},
    {"t":"GFED","c":"Great Southern Bancorp","s":"Reg-Bank","tier":3,"note":"Midwest community bank"},
    {"t":"EVBG","c":"Everbridge","s":"AI-SW","tier":3,"note":"critical event AI management"},
    {"t":"ALRM","c":"Alarm.com","s":"AI-SW","tier":2,"note":"AI smart home security"},
    {"t":"SMAR","c":"Smartsheet","s":"AI-SW","tier":2,"note":"AI work management cloud"},
    {"t":"PCVX","c":"Vaxcyte","s":"Biotech","tier":3,"note":"pneumococcal vaccine next-gen"},
    {"t":"AGIO","c":"Agios Pharmaceuticals","s":"Biotech","tier":3,"note":"metabolism cancer rare"},
    {"t":"AKRO","c":"Akero Therapeutics","s":"Biotech","tier":3,"note":"NASH metabolic liver"},

    # ── Specialty Finance / Mortgage ──────────────────────────────────────────
    {"t":"SLM","c":"SLM Corp (Sallie Mae)","s":"Fin-Spec","tier":3,"note":"student loan private"},
    {"t":"NAVI","c":"Navient","s":"Fin-Spec","tier":3,"note":"student loan servicer"},
    {"t":"PFSI","c":"PennyMac Financial","s":"Mortgage","tier":2,"note":"mortgage banking servicing"},
    {"t":"COOP","c":"Mr. Cooper Group","s":"Mortgage","tier":2,"note":"mortgage servicer largest"},
    {"t":"UWM","c":"UWM Holdings","s":"Mortgage","tier":2,"note":"wholesale mortgage largest"},
    {"t":"GHLD","c":"Guild Holdings","s":"Mortgage","tier":3,"note":"retail mortgage originator"},
    {"t":"RKT","c":"Rocket Companies","s":"Mortgage","tier":2,"note":"AI mortgage Rocket Mortgage"},
    {"t":"NMIH","c":"NMI Holdings","s":"Fin-Spec","tier":2,"note":"private mortgage insurance"},
    {"t":"ESNT","c":"Essent Group","s":"Fin-Spec","tier":2,"note":"private mortgage insurance"},
    {"t":"RADI","c":"Radian Group","s":"Fin-Spec","tier":2,"note":"mortgage insurance real estate"},
    {"t":"HOMB","c":"Home Bancshares","s":"Reg-Bank","tier":2,"note":"Arkansas commercial bank"},
    {"t":"TPVG","c":"TriplePoint Venture","s":"BDC","tier":3,"note":"BDC venture lending tech"},
    {"t":"NEWT","c":"Newtek Business Services","s":"BDC","tier":3,"note":"BDC SMB bank SBA"},
    {"t":"FDUS","c":"Fidus Investment","s":"BDC","tier":3,"note":"BDC lower middle market"},
    {"t":"GBDC","c":"Golub Capital BDC","s":"BDC","tier":2,"note":"BDC floating rate senior"},
    {"t":"BCSF","c":"Bain Capital Spec Finance","s":"BDC","tier":3,"note":"BDC senior secured"},
    {"t":"TRIN","c":"Trinity Capital","s":"BDC","tier":3,"note":"BDC equipment venture lend"},

    # ── Apparel / Footwear / Luxury ───────────────────────────────────────────
    {"t":"LEVI","c":"Levi Strauss","s":"Apparel","tier":2,"note":"denim global brand DTC"},
    {"t":"VFC","c":"V.F. Corp","s":"Apparel","tier":3,"note":"North Face Vans turnaround"},
    {"t":"PVH","c":"PVH Corp","s":"Apparel","tier":2,"note":"Calvin Klein Tommy Hilfiger"},
    {"t":"RL","c":"Ralph Lauren","s":"Luxury","tier":2,"note":"premium lifestyle brand global"},
    {"t":"CPRI","c":"Capri Holdings","s":"Luxury","tier":3,"note":"Michael Kors Versace Tapestry"},
    {"t":"TPR","c":"Tapestry","s":"Luxury","tier":2,"note":"Coach Kate Spade Stuart W"},
    {"t":"HBI","c":"Hanesbrands","s":"Apparel","tier":3,"note":"Champion underwear basics"},
    {"t":"UAA","c":"Under Armour A","s":"Apparel","tier":3,"note":"athletic brand turnaround"},
    {"t":"SKX","c":"Skechers","s":"Footwear","tier":2,"note":"comfort footwear global"},
    {"t":"ONON","c":"On Holding","s":"Footwear","tier":2,"note":"premium running Swiss"},
    {"t":"BIRK","c":"Birkenstock","s":"Footwear","tier":2,"note":"comfort sandals premium"},
    {"t":"DECK","c":"Deckers Outdoor","s":"Footwear","tier":1,"note":"HOKA UGG premium footwear"},
    {"t":"WWW","c":"Wolverine World Wide","s":"Footwear","tier":3,"note":"Merrell Saucony brands"},
    {"t":"CROX","c":"Crocs","s":"Footwear","tier":2,"note":"Crocs HEYDUDE casual comfort"},
    {"t":"G-III","c":"G-III Apparel","s":"Apparel","tier":3,"note":"licensed apparel brand"},

    # ── Real Estate / PropTech ────────────────────────────────────────────────
    {"t":"JLL","c":"Jones Lang LaSalle","s":"RE-Svc","tier":2,"note":"commercial real estate AI svcs"},
    {"t":"CBRE","c":"CBRE Group","s":"RE-Svc","tier":1,"note":"commercial real estate AI largest"},
    {"t":"CWK","c":"Cushman & Wakefield","s":"RE-Svc","tier":3,"note":"commercial RE services"},
    {"t":"MMI","c":"Marcus & Millichap","s":"RE-Svc","tier":3,"note":"commercial property brokerage"},
    {"t":"OPEN","c":"Opendoor","s":"Proptech","tier":3,"note":"AI instant home buying ibuyer"},
    {"t":"RDFN","c":"Redfin","s":"Proptech","tier":3,"note":"AI real estate brokerage"},
    {"t":"COMP","c":"Compass","s":"Proptech","tier":3,"note":"AI real estate tech platform"},
    {"t":"NMRK","c":"Newmark Group","s":"RE-Svc","tier":3,"note":"CRE investment brokerage"},

    # ── Semiconductors Extended ───────────────────────────────────────────────
    {"t":"ALAB","c":"Astera Labs","s":"Semis","tier":2,"note":"AI connectivity PCIe CXL"},
    {"t":"CEVA","c":"CEVA Inc","s":"Semis","tier":3,"note":"semiconductor IP AI edge"},
    {"t":"MACOM","c":"MACOM Technology","s":"Semis","tier":2,"note":"RF microwave datacenter"},
    {"t":"MTSI","c":"MACOM / M/A-COM","s":"Semis","tier":2,"note":"analog mixed-signal RF"},
    {"t":"VIAV","c":"Viavi Solutions","s":"Network","tier":3,"note":"network test optical"},
    {"t":"COHR","c":"Coherent Corp","s":"Semis","tier":2,"note":"optical components AI datacenter"},
    {"t":"IPGP","c":"IPG Photonics","s":"Semis","tier":2,"note":"fiber laser precision mfg"},
    {"t":"LITE","c":"Lumentum","s":"Semis","tier":2,"note":"laser optical AI datacenter"},
    {"t":"INFN","c":"Infinera","s":"Network","tier":3,"note":"optical networking transport"},
    {"t":"AOSL","c":"Alpha & Omega Semis","s":"Semis","tier":3,"note":"power management IC"},
    {"t":"POWI","c":"Power Integrations","s":"Semis","tier":2,"note":"energy efficient power AI"},
    {"t":"AMBA","c":"Ambarella","s":"Semis","tier":2,"note":"AI vision edge CV2 ADAS"},
    {"t":"IDCC","c":"InterDigital","s":"Semis","tier":2,"note":"wireless IP 5G royalties"},
    {"t":"RMBS","c":"Rambus","s":"Semis","tier":2,"note":"chip interface IP memory"},
    {"t":"VSH","c":"Vishay Intertechnology","s":"Semis","tier":2,"note":"passive components discrete"},
    {"t":"KLIC","c":"Kulicke and Soffa","s":"Semis","tier":2,"note":"semiconductor packaging equip"},
    {"t":"ICHR","c":"Ichor Holdings","s":"Semis","tier":3,"note":"gas delivery semis equip"},
    {"t":"UCTT","c":"Ultra Clean Holdings","s":"Semis","tier":3,"note":"subsystem semis equip"},
    {"t":"CAMT","c":"Camtek","s":"Semis","tier":3,"note":"inspection metrology Israel"},

    # ── Cloud / SaaS Extended ────────────────────────────────────────────────
    {"t":"FRSH","c":"Freshworks","s":"AI-SW","tier":3,"note":"AI CRM ITSM SMB"},
    {"t":"DOMO","c":"Domo","s":"AI-SW","tier":3,"note":"BI cloud data analytics"},
    {"t":"APPF","c":"AppFolio","s":"AI-SW","tier":2,"note":"AI property management SaaS"},
    {"t":"FROG","c":"JFrog","s":"AI-SW","tier":2,"note":"DevOps liquid software AI"},
    {"t":"DT","c":"Dynatrace","s":"AI-SW","tier":2,"note":"AI observability monitoring"},
    {"t":"ESTC","c":"Elastic NV","s":"AI-SW","tier":2,"note":"search AI observability Elastic"},
    {"t":"TENB","c":"Tenable Holdings","s":"Cyber","tier":2,"note":"vulnerability management cloud"},
    {"t":"SAIL","c":"SailPoint Tech","s":"Cyber","tier":2,"note":"identity security governance AI"},
    {"t":"ZTNA","c":"Zscaler (see ZS)","s":"Cyber","tier":2,"note":"see ZS"},
    {"t":"CYBR","c":"CyberArk Software","s":"Cyber","tier":2,"note":"privileged access identity"},
    {"t":"LYFT","c":"Lyft","s":"Mobility","tier":3,"note":"AI rideshare platform"},
    {"t":"APP","c":"AppLovin","s":"AI-SW","tier":2,"note":"AI mobile ad tech gaming"},
    {"t":"TTD","c":"Trade Desk","s":"AI-SW","tier":2,"note":"AI programmatic advertising"},
    {"t":"MGNI","c":"Magnite","s":"AI-SW","tier":3,"note":"CTV programmatic ad streaming"},
    {"t":"IS","c":"ironSource","s":"AI-SW","tier":3,"note":"mobile app growth platform"},
    {"t":"LPSN","c":"LivePerson","s":"AI-SW","tier":3,"note":"conversational AI chatbot"},
    {"t":"SPRK","c":"Sprinklr","s":"AI-SW","tier":3,"note":"AI unified CXM platform"},
    {"t":"PLTK","c":"Playtika","s":"Gaming","tier":3,"note":"mobile casual gaming AI"},
    {"t":"GLBE","c":"Global-E Online","s":"E-Com","tier":2,"note":"cross-border ecommerce AI"},
    {"t":"RELY","c":"Remitly Global","s":"Fintech","tier":2,"note":"AI digital remittance"},
    {"t":"NRDS","c":"NerdWallet","s":"Fintech","tier":3,"note":"AI personal finance compare"},
    {"t":"SOFI","c":"SoFi Technologies","s":"Fintech","tier":2,"note":"neobank student refi AI"},

    # ── Miscellaneous High-Conviction ─────────────────────────────────────────
    {"t":"BRK.B","c":"Berkshire Hathaway B","s":"Conglom","tier":1,"note":"Buffett value insurance energy"},
    {"t":"MKL","c":"Markel Group","s":"Insurance","tier":1,"note":"specialty insurance mini-Berkshire"},
    {"t":"FAST","c":"Fastenal","s":"Industrial","tier":1,"note":"industrial fasteners distribution"},
    {"t":"GWW","c":"W.W. Grainger","s":"Industrial","tier":1,"note":"MRO industrial distribution AI"},
    {"t":"MSM","c":"MSC Industrial","s":"Industrial","tier":2,"note":"metalworking MRO distribution"},
    {"t":"POOL","c":"Pool Corp","s":"Consumer","tier":2,"note":"pool equipment distribution"},
    {"t":"SNA","c":"Snap-on","s":"Industrial","tier":1,"note":"professional tools equipment"},
    {"t":"SWK","c":"Stanley Black & Decker","s":"Industrial","tier":2,"note":"tools storage industrial"},
    {"t":"MAS","c":"Masco Corp","s":"Consumer","tier":2,"note":"home plumbing cabinets paint"},
    {"t":"FND","c":"Floor & Decor","s":"Retail","tier":2,"note":"flooring retail hard surface"},
    {"t":"WSM","c":"Williams-Sonoma","s":"Retail","tier":1,"note":"premium home furnishings AI"},
    {"t":"RH","c":"RH","s":"Retail","tier":2,"note":"luxury furniture aspirational gallery"},
    {"t":"AMZN","c":"Amazon","s":"Mega-Tech","tier":1,"note":"AI AWS ecommerce marketplace"},
    {"t":"W","c":"Wayfair","s":"E-Com","tier":3,"note":"furniture ecommerce AI turnaround"},
    {"t":"CVNA","c":"Carvana","s":"Auto","tier":3,"note":"AI online car retail rebuild"},
    {"t":"AFRM","c":"Affirm","s":"Fintech","tier":3,"note":"BNPL AI Apple Pay Later"},
    {"t":"RELY","c":"Remitly","s":"Fintech","tier":2,"note":"AI digital remittance EM"},
    {"t":"GDRX","c":"GoodRx","s":"Health-IT","tier":3,"note":"prescription AI marketplace"},
    {"t":"DOCS","c":"Doximity","s":"Health-IT","tier":2,"note":"AI physician network telehealth"},
    {"t":"VEEV","c":"Veeva Systems","s":"AI-SW","tier":1,"note":"pharma cloud CRM data"},
    {"t":"NTRA","c":"Natera","s":"Genomics","tier":2,"note":"cfDNA oncology Signatera"},
    {"t":"CRNX","c":"Crinetics Pharma","s":"Biotech","tier":3,"note":"endocrine rare disease oral"},
    {"t":"ARWR","c":"Arrowhead Pharmaceuticals","s":"Biotech","tier":3,"note":"RNAi liver disease"},
    {"t":"MIRM","c":"Mirum Pharmaceuticals","s":"Biotech","tier":3,"note":"liver pediatric rare"},
    {"t":"PCVX","c":"Vaxcyte","s":"Biotech","tier":3,"note":"conjugate vaccine pneumococcal"},
    {"t":"ALKS","c":"Alkermes","s":"Spec-Pharma","tier":2,"note":"CNS addiction depression"},
    {"t":"VNDA","c":"Vanda Pharmaceuticals","s":"Spec-Pharma","tier":3,"note":"CNS rare circadian"},
    {"t":"PTCT","c":"PTC Therapeutics","s":"Biotech","tier":3,"note":"rare genetic DMD SMA"},
    {"t":"RCUS","c":"Arcus Biosciences","s":"Biotech","tier":3,"note":"IO oncology Gilead collab"},
    {"t":"IMVT","c":"Immunovant","s":"Biotech","tier":3,"note":"FcRn autoimmune MG TED"},
    {"t":"FULC","c":"Fulcrum Therapeutics","s":"Biotech","tier":3,"note":"epigenetic muscle rare"},
    {"t":"IRON","c":"Disc Medicine","s":"Biotech","tier":3,"note":"hematology rare blood"},
]


def pre_filter(macro: dict = None, n: int = 250) -> list:
    """
    Macro-aware sector filter using at_analysis macro data.
    Weights sectors by FRED rate regime, VIX risk, yield curve, DXY.
    Falls back to QQQ mood if macro is None.
    """
    try:
        from at_analysis import macro_score
    except ImportError:
        macro_score = None

    regime   = (macro or {}).get("regime", "mid_cycle")
    rate_env = (macro or {}).get("rate_env", "normal_rate")
    risk_lvl = (macro or {}).get("risk_level", "normal_risk")
    vix      = (macro or {}).get("vix") or 18

    # Base tier bonus (always)
    if vix >= 28 or risk_lvl == "high_risk":
        tier_bonus = {1: 25, 2: 8, 3: 0}   # crisis → only blue chips
    elif vix <= 15:
        tier_bonus = {1: 12, 2: 12, 3: 8}   # low vol → risk-on all tiers
    else:
        tier_bonus = {1: 16, 2: 10, 3: 4}

    # Sector weights by macro regime
    REGIME_WEIGHTS = {
        "expansion": {
            "Semis": 22, "AI-SW": 20, "AI-Infra": 20, "Mega-Tech": 18, "EDA": 16,
            "Cyber": 15, "Fintech": 13, "EV-Auto": 12, "Clean-NRG": 11, "Space": 10,
            "Defense": 10, "Crypto": 9, "Biotech": 8, "Gaming": 8, "Pharma": 7,
            "Utilities": 3, "Staples": 2, "Insurance": 3, "REIT": 4,
        },
        "mid_cycle": {
            "Semis": 17, "AI-SW": 16, "Mega-Tech": 15, "Cyber": 14, "Defense": 13,
            "Pharma": 12, "Biotech": 11, "Fintech": 11, "Mining": 9, "Industrial": 9,
            "Utilities": 8, "REIT": 8, "Staples": 7, "Oil-Gas": 7, "Insurance": 7,
            "EV-Auto": 8, "Clean-NRG": 8,
        },
        "recession_risk": {
            "Staples": 22, "Utilities": 21, "Defense": 20, "Insurance": 18,
            "Health-Ins": 17, "Pharma": 16, "Med-Tech": 14, "Rail": 13,
            "Water": 12, "REIT": 10, "BDC": 9, "Mining": 9, "Oil-Gas": 8,
            "Semis": 4, "AI-SW": 4, "Crypto": 1, "EV-Auto": 2,
        },
        "crisis": {
            "Defense": 25, "Utilities": 22, "Staples": 22, "Gold-Mining": 18,
            "Mining": 15, "Insurance": 14, "Health-Ins": 14, "Pharma": 13,
            "Semis": 3, "AI-SW": 3, "Crypto": 0, "EV-Auto": 1,
        },
        "overheating": {
            "Mining": 22, "Oil-Gas": 20, "Midstream": 18, "Refining": 16,
            "Utilities": 12, "Staples": 10, "Defense": 10, "Industrial": 9,
            "Semis": 8, "AI-SW": 7, "Fintech": 6,
        },
    }

    # Rate environment fine-tune
    RATE_ADJ = {
        "high_rate": {
            "Bank": +8, "Reg-Bank": +8, "Insurance": +6, "Fintech": -4,
            "Biotech": -6, "Crypto": -8, "REIT": -8, "EV-Auto": -5,
            "Utilities": -3, "Staples": +4, "Defense": +3,
        },
        "low_rate": {
            "Semis": +6, "AI-SW": +8, "Mega-Tech": +6, "REIT": +8,
            "Biotech": +6, "Crypto": +10, "EV-Auto": +6, "Clean-NRG": +5,
            "Bank": -4, "Insurance": -3,
        },
    }

    regime_weights = REGIME_WEIGHTS.get(regime, REGIME_WEIGHTS["mid_cycle"])
    rate_adj       = RATE_ADJ.get(rate_env, {})

    scored = []
    for entry in VAULT:
        score  = tier_bonus.get(entry["tier"], 4)
        score += regime_weights.get(entry["s"], 5)
        score += rate_adj.get(entry["s"], 0)
        scored.append((score, entry))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:n]]


def arthee_pick(candidates: list, macro: dict, scored_stocks: list, n: int = 50) -> list:
    """
    Ask ArtheeNoi with full context: FRED macro + AI scores + sector weights.
    scored_stocks: list of {sym, ai_score, action, sector, technical, fundamental}
    Falls back to score-ranked order if Ollama offline.
    """
    try:
        from at_analysis import build_arthee_context
        context = build_arthee_context(macro, scored_stocks)
    except ImportError:
        qqq_chg = macro.get("qqq_chg", 0)
        mood    = macro.get("mood", "NEUTRAL")
        ticker_list = ", ".join(c["t"] for c in candidates[:150])
        context = (f"วันนี้ตลาด {mood} (QQQ {qqq_chg:+.1f}%)\n"
                   f"Fed Rate: {macro.get('fed_rate','?')}%  VIX: {macro.get('vix','?')}\n"
                   f"Yield Curve: {macro.get('yield_curve','?')}  DXY: {macro.get('dxy','?')}\n"
                   f"Regime: {macro.get('regime','?')}\n\n"
                   f"จากหุ้นเหล่านี้เลือก {n} ตัว:\n{ticker_list}\n"
                   f"ตอบเฉพาะ ticker คั่น comma เท่านั้น")

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": context, "stream": False},
            timeout=90,
        )
        if resp.status_code == 200:
            text  = resp.json().get("response", "")
            valid = {c["t"] for c in candidates}
            picked = []
            for token in text.replace("\n", " ").replace(",", " ").split():
                t = token.strip().upper().rstrip(".")
                if t in valid and t not in picked:
                    picked.append(t)
            if len(picked) >= 10:
                print(f"  ArtheeNoi picked {len(picked)} stocks via Ollama")
                return picked[:n]
    except Exception as e:
        print(f"  ArtheeNoi offline ({e}) — using AI score ranking")

    # Fallback: rank by AI score
    scored_map = {s["sym"]: s.get("ai_score", 50) for s in scored_stocks}
    ranked = sorted(candidates, key=lambda c: -scored_map.get(c["t"], 50))
    return [c["t"] for c in ranked[:n]]


def get_vault_picks(macro: dict = None, qqq_chg: float = 0.0,
                    market_mood: str = "NEUTRAL", n: int = 50) -> list:
    """
    Full pipeline:
    1. fetch_macro() → FRED + VIX + DXY
    2. pre_filter() → sector weights by macro regime
    3. fetch_picks_lite() → price + RSI for candidates
    4. ai_score_full() → Technical + Fundamental + Macro + Sentiment per stock
    5. arthee_pick() → ArtheeNoi selects with full context
    """
    # Step 1: macro
    if macro is None:
        try:
            from at_analysis import fetch_macro
            macro = fetch_macro()
        except Exception:
            macro = {}
    macro.setdefault("qqq_chg", qqq_chg)
    macro.setdefault("mood", market_mood)

    # Step 2: pre-filter by macro (250 candidates)
    candidates = pre_filter(macro, n=250)
    print(f"  pre_filter: {len(candidates)} candidates (regime={macro.get('regime','?')})")

    # Step 3: lite fetch for candidates (price + RSI, fast)
    tickers = [c["t"] for c in candidates]
    print(f"  fetch_picks_lite: {len(tickers)} stocks ...")
    lite_data = fetch_picks_lite(tickers[:150])  # cap at 150 for speed

    # Step 4: prefetch sector ETFs once (shared cache for all ai_score calls)
    sector_map = {c["t"]: c["s"] for c in candidates}
    unique_sectors = list({c["s"] for c in candidates})
    try:
        from at_analysis import ai_score_full, prefetch_sector_etfs
        print(f"  Prefetching {len(unique_sectors)} sector ETFs ...")
        prefetch_sector_etfs(unique_sectors, also_qqq=True)
        has_analysis = True
    except ImportError:
        has_analysis = False

    scored_stocks = []
    for sym, d in lite_data.items():
        if not d.get("price"):
            continue
        if has_analysis:
            result = ai_score_full(d, macro, sector_map.get(sym, ""))
        else:
            result = {"ai_score": 50, "action": "NEUTRAL", "stars": 0, "reason": ""}
        scored_stocks.append({
            "sym":         sym,
            "ai_score":    result["ai_score"],
            "action":      result["action"],
            "sector":      sector_map.get(sym, ""),
            "rs_sector":   d.get("rs_sector"),
            "rs_qqq":      d.get("rs_qqq"),
            "rs_etf":      d.get("rs_etf"),
            "technical":   result.get("technical", {}),
            "fundamental": result.get("fundamental", {}),
            "macro":       result.get("macro", {}),
            "extra":       result.get("extra", {}),
        })

    scored_stocks.sort(key=lambda x: -x["ai_score"])
    top_info = f"{scored_stocks[0]['sym']}({scored_stocks[0]['ai_score']})" if scored_stocks else "none"
    print(f"  ai_score computed: {len(scored_stocks)} stocks | top={top_info}")

    # Step 5: ArtheeNoi picks
    return arthee_pick(candidates, macro, scored_stocks, n=n)


def vault_summary() -> dict:
    """Return summary stats for the vault."""
    sectors = {}
    for e in VAULT:
        sectors[e["s"]] = sectors.get(e["s"], 0) + 1
    return {
        "total":   len(VAULT),
        "tier1":   sum(1 for e in VAULT if e["tier"] == 1),
        "tier2":   sum(1 for e in VAULT if e["tier"] == 2),
        "tier3":   sum(1 for e in VAULT if e["tier"] == 3),
        "sectors": sectors,
    }


if __name__ == "__main__":
    import json
    s = vault_summary()
    print(f"Vault: {s['total']} stocks | T1:{s['tier1']} T2:{s['tier2']} T3:{s['tier3']}")
    print("Sectors:", json.dumps(s["sectors"], ensure_ascii=False))
    picks = get_vault_picks("BULL", 0.8, n=20)
    print(f"\nSample picks (BULL, +0.8%): {picks}")
