import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, date
import streamlit.components.v1 as components
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Heidis Aktien-Assistent", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f8f4ff 0%, #f0e8ff 50%, #faf5ff 100%);
}
[data-testid="stHeader"] { background: transparent; }
h1 { color: #472d93 !important; letter-spacing: -0.5px; }
h2, h3 { color: #472d93 !important; }
[data-testid="stTabs"] button { color: #472d93 !important; font-weight: 600; }
[data-testid="stTabs"] button[aria-selected="true"] {
    border-bottom: 3px solid #472d93 !important; color: #472d93 !important;
}
[data-testid="stExpander"] {
    background: white; border-radius: 14px;
    border: 1px solid #e5c5f1; box-shadow: 0 2px 12px #472d9312;
}
[data-testid="stMetric"] {
    background: white; border-radius: 12px; padding: 14px 18px;
    border: 1px solid #e5c5f1; box-shadow: 0 2px 8px #472d930e;
}
[data-testid="stMetricLabel"] { color: #7c5cbf !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #472d93 !important; font-weight: 700 !important; }
[data-testid="stButton"] > button {
    background: #472d93 !important; color: white !important;
    border-radius: 10px !important; border: none !important; font-weight: 600 !important;
}
[data-testid="stButton"] > button:hover { background: #5e3db3 !important; }
[data-testid="stTextInput"] input {
    border-radius: 10px !important; border: 2px solid #e5c5f1 !important;
}
[data-testid="stTextInput"] input:focus { border-color: #472d93 !important; }
[data-testid="stRadio"] label { color: #472d93 !important; font-weight: 500; }
hr { border-color: #e5c5f1 !important; }
.big-signal {
    font-size: 1.7rem; font-weight: 800; padding: 12px 26px;
    border-radius: 12px; display: inline-block; letter-spacing: 1px;
}
.green-bg  { background: #e8fff2; color: #00a844; border: 2px solid #00c853; }
.orange-bg { background: #fff8e8; color: #d97700; border: 2px solid #ff9800; }
.red-bg    { background: #fff0f0; color: #d32f2f; border: 2px solid #f44336; }
.gray-bg   { background: #f5f5f5; color: #888;    border: 2px solid #ccc; }
.check-row { padding: 5px 0; font-size: 0.95rem; color: #2d1f4e; }
.ema-card {
    background: white; border-radius: 12px; padding: 14px 18px;
    border: 1px solid #e5c5f1; box-shadow: 0 2px 8px #472d930e; margin-bottom: 8px;
}
.ema-label { color: #7c5cbf; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.ema-value { color: #472d93; font-size: 1.15rem; font-weight: 700; }
.ema-sub   { font-size: 0.78rem; }
.alert-box {
    border-radius: 14px; padding: 20px 24px; margin: 12px 0;
    font-weight: 600; font-size: 1rem; line-height: 1.6;
}
.alert-buy   { background: #e8fff2; border: 2px solid #00c853; color: #1a6635; }
.alert-watch { background: #fff8e8; border: 2px solid #ff9800; color: #7a4500; }
.alert-skip  { background: #fff0f0; border: 2px solid #f44336; color: #7a1515; }
.ceo-card {
    background: white; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #e5c5f1; box-shadow: 0 2px 8px #472d930e; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Datenhaltung (lokal + Cloud-kompatibel) ───────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio.json")

DEFAULT_DATA = {
    "portfolio": [],
    "watchlist": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "V", "MA", "UNH", "COST", "HD"]
}

def load_data():
    # Session State hat Vorrang (Cloud-kompatibel)
    if "portfolio_data" in st.session_state:
        return st.session_state["portfolio_data"]
    # Lokale Datei laden falls vorhanden
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                st.session_state["portfolio_data"] = d
                return d
    except Exception:
        pass
    d = DEFAULT_DATA.copy()
    d["portfolio"] = []
    d["watchlist"] = list(DEFAULT_DATA["watchlist"])
    st.session_state["portfolio_data"] = d
    return d

def save_data(d):
    st.session_state["portfolio_data"] = d
    # Lokal speichern falls möglich
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass  # Auf Cloud-Servern ist das okay — Session State reicht

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
def fmt_pct(v):
    return f"{v:+.1f}%" if v is not None else "—"

def fmt_usd(v, digits=2):
    return f"${v:.{digits}f}" if v is not None else "—"

def score_icon(v):
    return "✅" if v is True else ("❌" if v is False else "❓")

def signal_css(s):
    return {"KAUFEN": "green-bg", "ABWARTEN": "orange-bg", "FINGER WEG": "red-bg"}.get(s, "gray-bg")

# ── Ticker-Suche ─────────────────────────────────────────────────────────────
NAME_MAP = {
    "apple": "AAPL", "äpple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN",
    "nvidia": "NVDA",
    "meta": "META", "facebook": "META",
    "tesla": "TSLA",
    "netflix": "NFLX",
    "visa": "V",
    "mastercard": "MA",
    "costco": "COST",
    "home depot": "HD",
    "united health": "UNH", "unitedhealth": "UNH",
    "broadcom": "AVGO",
    "salesforce": "CRM",
    "servicenow": "NOW",
    "eli lilly": "LLY", "lilly": "LLY",
    "berkshire": "BRK-B",
    "jpmorgan": "JPM", "jp morgan": "JPM",
    "johnson": "JNJ", "johnson & johnson": "JNJ",
    "procter": "PG", "procter & gamble": "PG",
    "coca cola": "KO", "coca-cola": "KO",
    "pepsico": "PEP", "pepsi": "PEP",
    "walmart": "WMT",
    "disney": "DIS",
    "nike": "NKE",
    "starbucks": "SBUX",
    "paypal": "PYPL",
    "adobe": "ADBE",
    "amd": "AMD", "advanced micro": "AMD",
    "intel": "INTC",
    "qualcomm": "QCOM",
    "palantir": "PLTR",
    "snowflake": "SNOW",
    "crowdstrike": "CRWD",
    "datadog": "DDOG",
    "s&p": "SPY", "sp500": "SPY",
}

def resolve_ticker(query: str) -> str:
    q = query.strip()
    lookup = q.lower()
    if lookup in NAME_MAP:
        return NAME_MAP[lookup]
    for name, ticker in NAME_MAP.items():
        if lookup in name or name in lookup:
            return ticker
    return q.upper()

# ── Marktlage ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_market_context():
    try:
        spy  = yf.Ticker("SPY").history(period="1y")
        vix  = yf.Ticker("^VIX").history(period="5d")
        spy["EMA200"] = spy["Close"].ewm(span=200, adjust=False).mean()
        spy_above_200 = float(spy["Close"].iloc[-1]) > float(spy["EMA200"].iloc[-1])
        spy_trend_1m  = (spy["Close"].iloc[-1] / spy["Close"].iloc[-21] - 1) * 100
        vix_level     = float(vix["Close"].iloc[-1]) if len(vix) > 0 else 20
        if vix_level < 15:    vix_status = "ruhig"
        elif vix_level < 25:  vix_status = "normal"
        elif vix_level < 35:  vix_status = "erhöht"
        else:                 vix_status = "Panik"
        return {
            "spy_above_200": spy_above_200,
            "spy_trend_1m":  round(float(spy_trend_1m), 1),
            "vix":           round(vix_level, 1),
            "vix_status":    vix_status,
            "bull_market":   spy_above_200 and vix_level < 25,
        }
    except Exception:
        return {"spy_above_200": True, "spy_trend_1m": 0, "vix": 20, "vix_status": "normal", "bull_market": True}

# ── Kernanalyse ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            return None
    except Exception:
        return None

    # CEO / Management
    ceo_name, ceo_title, ceo_pay = "—", "—", None
    try:
        officers = info.get("companyOfficers", [])
        ceo = next(
            (o for o in officers if "CEO" in (o.get("title") or "") or "Chief Executive" in (o.get("title") or "")),
            officers[0] if officers else None
        )
        if ceo:
            ceo_name  = ceo.get("name", "—")
            ceo_title = ceo.get("title", "—")
            ceo_pay   = ceo.get("totalPay")
    except Exception:
        pass

    r = {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "sector": info.get("sector", "—"),
        "industry": info.get("industry", "—"),
        "current_price": price,
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps_ttm": info.get("trailingEps"),
        "eps_forward": info.get("forwardEps"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "roe": info.get("returnOnEquity"),
        "profit_margin": info.get("profitMargins"),
        "description": (info.get("longBusinessSummary") or "")[:500],
        "employees": info.get("fullTimeEmployees"),
        "website": info.get("website", ""),
        "ceo_name": ceo_name,
        "ceo_title": ceo_title,
        "ceo_pay": ceo_pay,
        # technisch
        "ema20": None, "ema50": None, "ema200": None,
        "ema20_above_50": None, "price_above_ema200": None,
        "macd_bullish": None, "atr14": None,
        "stop_atr": None, "stop_swing": None, "perf_5y": None,
        "rsi": None, "rsi_signal": None,
        "high_52w": None, "low_52w": None, "pct_from_52w_high": None,
        "typical_pullback": None, "stop_individual": None,
        # fundamental
        "debt_to_fcf": None, "fair_price": None, "margin_of_safety": None,
    }

    # ── Verschuldung / FCF — direkt aus info (kein Extra-API-Call) ───────────
    try:
        fcf  = info.get("freeCashflow")
        debt = info.get("totalDebt")
        if fcf and fcf > 0 and debt:
            r["debt_to_fcf"] = round(debt / fcf, 1)
    except Exception:
        pass

    # ── Kurshistorie + Technik ────────────────────────────────────────────────
    try:
        hist = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        hist.columns = hist.columns.get_level_values(0)
        if len(hist) > 50:
            hist["EMA20"]  = hist["Close"].ewm(span=20,  adjust=False).mean()
            hist["EMA50"]  = hist["Close"].ewm(span=50,  adjust=False).mean()
            hist["EMA200"] = hist["Close"].ewm(span=200, adjust=False).mean()
            r["ema20"]  = float(hist["EMA20"].iloc[-1])
            r["ema50"]  = float(hist["EMA50"].iloc[-1])
            r["ema200"] = float(hist["EMA200"].iloc[-1])
            r["ema20_above_50"]     = r["ema20"]  > r["ema50"]
            r["price_above_ema200"] = price > r["ema200"]

            e12  = hist["Close"].ewm(span=12, adjust=False).mean()
            e26  = hist["Close"].ewm(span=26, adjust=False).mean()
            macd = e12 - e26
            sig  = macd.ewm(span=9, adjust=False).mean()
            r["macd_bullish"] = float(macd.iloc[-1]) > float(sig.iloc[-1])
            r["macd_just_crossed"] = (
                float(macd.iloc[-1]) > float(sig.iloc[-1]) and
                float(macd.iloc[-2]) <= float(sig.iloc[-2])
            )

            hl  = hist["High"] - hist["Low"]
            hpc = (hist["High"] - hist["Close"].shift(1)).abs()
            lpc = (hist["Low"]  - hist["Close"].shift(1)).abs()
            tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            r["atr14"]      = float(atr)
            r["stop_atr"]   = round(price - 2.5 * atr, 2)
            r["stop_swing"] = round(float(hist["Low"].tail(60).min()), 2)

            dist_series = (hist["Close"] - hist["EMA20"]) / hist["EMA20"] * 100
            r["dist_ema20_pct"]  = float(dist_series.iloc[-1])
            r["dist_ema20_mean"] = float(dist_series.tail(252).mean())
            r["dist_ema20_std"]  = float(dist_series.tail(252).std())
            zscore = (r["dist_ema20_pct"] - r["dist_ema20_mean"]) / r["dist_ema20_std"] if r["dist_ema20_std"] > 0 else 0
            r["dist_ema20_zscore"] = round(zscore, 2)
            r["pullback_likely"]   = zscore > 1.3

            delta = hist["Close"].diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss.replace(0, 1e-9)
            rsi   = 100 - (100 / (1 + rs))
            r["rsi"] = round(float(rsi.iloc[-1]), 1)
            if r["rsi"] >= 75:   r["rsi_signal"] = "überkauft"
            elif r["rsi"] >= 55: r["rsi_signal"] = "neutral-bullisch"
            elif r["rsi"] >= 45: r["rsi_signal"] = "neutral"
            elif r["rsi"] >= 25: r["rsi_signal"] = "neutral-bärisch"
            else:                r["rsi_signal"] = "überverkauft"

            h252 = hist.tail(252)
            r["high_52w"] = round(float(h252["High"].max()), 2)
            r["low_52w"]  = round(float(h252["Low"].min()), 2)
            r["pct_from_52w_high"] = round((price - r["high_52w"]) / r["high_52w"] * 100, 1)

            roll_max  = hist["Close"].tail(252).rolling(20).max()
            drawdowns = ((hist["Close"].tail(252) - roll_max) / roll_max * 100).dropna()
            r["typical_pullback"] = round(float(drawdowns.quantile(0.10)), 1)
            breathing_room = abs(r["typical_pullback"]) * 1.2
            r["stop_individual"] = round(price * (1 - breathing_room / 100), 2)

            # 5J-Performance: aus info ableiten (kein extra API-Call)
            try:
                fw52 = info.get("fiftyTwoWeekChange")   # 1J-Rendite
                fw52_3y = info.get("threeYearAverageReturn")
                if fw52 is not None and fw52_3y is not None:
                    r["perf_5y"] = round(((1 + fw52_3y) ** 5 - 1) * 100, 1)
                elif fw52 is not None:
                    r["perf_5y"] = round(fw52 * 100, 1)
            except Exception:
                pass

            # ── Trendstruktur: Höhere Hochs + Höhere Tiefs (Dow-Theorie) ─────
            try:
                seg = hist["High"].tail(60)
                sl  = hist["Low"].tail(60)
                h1, h2, h3 = seg[:20].max(), seg[20:40].max(), seg[40:].max()
                l1, l2, l3 = sl[:20].min(), sl[20:40].min(), sl[40:].min()
                if h3 > h2 > h1 and l3 > l2 > l1:
                    r["trend_structure"] = "Aufwärtstrend"
                    r["trend_structure_detail"] = "Höhere Hochs + höhere Tiefs — Trend intakt"
                    r["trend_structure_signal"] = "bullish"
                elif h3 < h2 < h1 and l3 < l2 < l1:
                    r["trend_structure"] = "Abwärtstrend"
                    r["trend_structure_detail"] = "Tiefere Hochs + tiefere Tiefs — Vorsicht"
                    r["trend_structure_signal"] = "bearish"
                else:
                    r["trend_structure"] = "Seitwärtstrend"
                    r["trend_structure_detail"] = "Kein klarer Trend — Geduld"
                    r["trend_structure_signal"] = "neutral"
            except Exception:
                pass

            # ── Support & Widerstand aus Pivot-Hochs/-Tiefs ───────────────────
            try:
                # Quarterly Hochs/Tiefs als natürliche S/R-Zonen
                q = hist.tail(252)
                period_highs = [q["High"][i:i+63].max() for i in range(0, 252, 63)]
                period_lows  = [q["Low"][i:i+63].min()  for i in range(0, 252, 63)]
                all_r = sorted(set([round(v, 2) for v in period_highs if v > price]))
                all_s = sorted(set([round(v, 2) for v in period_lows  if v < price]), reverse=True)
                r["resistance"] = all_r[0] if all_r else r.get("high_52w")
                r["support"]    = all_s[0] if all_s else r.get("low_52w")
            except Exception:
                pass

            # ── Letzte Kerzenformation erkennen ───────────────────────────────
            try:
                c2 = hist.iloc[-2]
                c1 = hist.iloc[-1]
                o, h, l, c = float(c1["Open"]), float(c1["High"]), float(c1["Low"]), float(c1["Close"])
                po, pc = float(c2["Open"]), float(c2["Close"])
                body = abs(c - o)
                rng  = h - l if h > l else 0.001
                up_sh = h - max(c, o)
                lo_sh = min(c, o) - l
                br = body / rng

                if br < 0.08:
                    r["candle_pattern"] = "Doji"
                    r["candle_signal"]  = "neutral"
                    r["candle_tip"]     = "Markt unentschlossen — auf nächste Kerze warten."
                elif br > 0.70:
                    if c > o:
                        r["candle_pattern"] = "Power Candle (bullisch)"
                        r["candle_signal"]  = "bullish"
                        r["candle_tip"]     = "Starke grüne Kerze — Käufer klar in der Führung."
                    else:
                        r["candle_pattern"] = "Power Candle (bärisch)"
                        r["candle_signal"]  = "bearish"
                        r["candle_tip"]     = "Starke rote Kerze — Verkäufer dominieren."
                elif lo_sh > 2 * body and up_sh < body and c > o:
                    r["candle_pattern"] = "Hammer"
                    r["candle_signal"]  = "bullish"
                    r["candle_tip"]     = "Hammer: Verkäufer wurden zurückgeschlagen — bullisches Umkehrsignal."
                elif up_sh > 2 * body and lo_sh < body and c < o:
                    r["candle_pattern"] = "Shooting Star"
                    r["candle_signal"]  = "bearish"
                    r["candle_tip"]     = "Shooting Star: Käufer konnten sich nicht halten — bärisches Warnsignal."
                elif c > o and pc < po and c > po and o < pc:
                    r["candle_pattern"] = "Bullish Engulfing"
                    r["candle_signal"]  = "bullish"
                    r["candle_tip"]     = "Bullish Engulfing: Grüne Kerze schluckt die rote — starkes Kaufsignal."
                elif c < o and pc > po and c < po and o > pc:
                    r["candle_pattern"] = "Bearish Engulfing"
                    r["candle_signal"]  = "bearish"
                    r["candle_tip"]     = "Bearish Engulfing: Rote Kerze schluckt die grüne — Vorsicht."
                elif c > o:
                    r["candle_pattern"] = "Steigende Kerze"
                    r["candle_signal"]  = "bullish"
                    r["candle_tip"]     = "Normale grüne Kerze — Kurs stieg heute."
                else:
                    r["candle_pattern"] = "Fallende Kerze"
                    r["candle_signal"]  = "bearish"
                    r["candle_tip"]     = "Normale rote Kerze — Kurs fiel heute."
            except Exception:
                pass

            hist_plot = hist.tail(365).copy()
            r["_hist"] = {
                "dates":  hist_plot.index.strftime("%Y-%m-%d").tolist(),
                "open":   hist_plot["Open"].round(2).tolist(),
                "high":   hist_plot["High"].round(2).tolist(),
                "low":    hist_plot["Low"].round(2).tolist(),
                "close":  hist_plot["Close"].round(2).tolist(),
                "volume": hist_plot["Volume"].tolist(),
                "ema20":  hist_plot["EMA20"].round(2).tolist(),
                "ema50":  hist_plot["EMA50"].round(2).tolist(),
                "ema200": hist_plot["EMA200"].round(2).tolist(),
            }
    except Exception:
        pass

    # ── Fairer Preis (Dr. Mayer) ──────────────────────────────────────────────
    try:
        eps    = r["eps_ttm"] or 0
        growth = max(0.05, min(r["earnings_growth"] or 0.10, 0.35))
        pe     = r["pe_ratio"] or 20
        fut_pe = min(growth * 200, pe, 35)
        r["fair_price"] = round(eps * ((1 + growth) ** 10) * fut_pe / (1.15 ** 10), 2)
        r["margin_of_safety"] = round(
            (r["fair_price"] - price) / r["fair_price"] * 100, 1
        )
    except Exception:
        pass

    # ── Scoring ───────────────────────────────────────────────────────────────
    s = {}
    s["Umsatzwachstum ≥10% (YoY)"]   = bool((r["revenue_growth"]  or 0) >= 0.10) if r["revenue_growth"]  is not None else None
    s["Gewinnwachstum ≥10% (YoY)"]   = bool((r["earnings_growth"] or 0) >= 0.10) if r["earnings_growth"] is not None else None
    s["ROIC/ROE ≥10%"]               = bool((r["roe"]             or 0) >= 0.10) if r["roe"]             is not None else None
    s["Verschuldung ≤3× FCF"]        = bool((r["debt_to_fcf"]     or 999) <= 3)  if r["debt_to_fcf"]     is not None else None
    s["5J-Performance ≥150%"]        = bool((r["perf_5y"]         or 0) >= 150)  if r["perf_5y"]         is not None else None
    s["Fairer Preis (≤10% drüber)"]  = bool((r["margin_of_safety"] or -999) >= -10) if r["fair_price"]  is not None else None
    s["Aufwärtstrend EMA20 > EMA50"] = r["ema20_above_50"]
    s["MACD bullisch"]               = r["macd_bullish"]
    # RSI: nicht überkauft (unter 75) und nicht im freien Fall (über 35)
    if r["rsi"] is not None:
        s["RSI gesund (35–74)"] = bool(35 <= r["rsi"] <= 74)
    else:
        s["RSI gesund (35–74)"] = None
    # Nicht zu nah am 52-Wochen-Hoch (mehr als 5% Luft)
    if r["pct_from_52w_high"] is not None:
        s["Nicht am Jahreshoch (>5% Abstand)"] = bool(r["pct_from_52w_high"] <= -5)
    else:
        s["Nicht am Jahreshoch (>5% Abstand)"] = None
    # Trendstruktur: echter Aufwärtstrend (höhere Hochs + Tiefs)
    if r.get("trend_structure"):
        s["Aufwärtstrend (Marktstruktur)"] = r["trend_structure"] == "Aufwärtstrend"
    else:
        s["Aufwärtstrend (Marktstruktur)"] = None

    r["scores"] = s
    green = sum(1 for v in s.values() if v is True)
    total = sum(1 for v in s.values() if v is not None)
    r["green"]       = green
    r["total"]       = total
    r["score_ratio"] = f"{green}/{total}"

    ratio = green / total if total > 0 else 0
    if   ratio >= 0.75: r["signal"] = "KAUFEN"
    elif ratio >= 0.50: r["signal"] = "ABWARTEN"
    else:               r["signal"] = "FINGER WEG"

    # ── Fundamentale vs. Technische Analyse getrennt ──────────────────────────
    FUND_KEYS = {
        "Umsatzwachstum ≥10% (YoY)", "Gewinnwachstum ≥10% (YoY)",
        "ROIC/ROE ≥10%", "Verschuldung ≤3× FCF",
        "5J-Performance ≥150%", "Fairer Preis (≤10% drüber)"
    }
    fund_s = {k: v for k, v in s.items() if k in FUND_KEYS}
    tech_s = {k: v for k, v in s.items() if k not in FUND_KEYS}

    def _sig(g, t):
        if t == 0: return "ABWARTEN"
        ratio = g / t
        if ratio >= 0.75: return "KAUFEN"
        if ratio >= 0.50: return "ABWARTEN"
        return "FINGER WEG"

    fg = sum(1 for v in fund_s.values() if v is True)
    ft = sum(1 for v in fund_s.values() if v is not None)
    tg = sum(1 for v in tech_s.values() if v is True)
    tt = sum(1 for v in tech_s.values() if v is not None)

    r["fundamental_signal"] = _sig(fg, ft)
    r["fundamental_score"]  = f"{fg}/{ft}"
    r["fundamental_scores"] = fund_s
    r["technical_signal"]   = _sig(tg, tt)
    r["technical_score"]    = f"{tg}/{tt}"
    r["technical_scores"]   = tech_s

    # ── Nächster Earnings-Termin aus info ─────────────────────────────────────
    try:
        ts = info.get("earningsTimestampStart") or info.get("earningsTimestamp")
        if ts and int(ts) > 0:
            r["next_earnings_date"] = datetime.fromtimestamp(int(ts)).strftime("%d.%m.%Y")
    except Exception:
        pass

    # ── Kaufempfehlung Text ───────────────────────────────────────────────────
    r["buy_text"] = _buy_timing_text(r)

    return r

def _buy_timing_text(r):
    sig    = r.get("signal", "")
    price  = r.get("current_price", 0)
    mos    = r.get("margin_of_safety")
    dist20 = r.get("dist_ema20_pct")
    above200 = r.get("price_above_ema200")
    macd_ok  = r.get("macd_bullish")
    crossed  = r.get("macd_just_crossed")
    trend_ok = r.get("ema20_above_50")

    pullback = r.get("pullback_likely", False)
    dist_mean = r.get("dist_ema20_mean")
    zscore   = r.get("dist_ema20_zscore", 0)

    if sig == "KAUFEN":
        if pullback and dist20 and dist20 > 5:
            return (
                f"Unternehmen stark — aber jetzt warten. "
                f"Kurs ist {dist20:.1f}% über dem EMA20, historisch im Schnitt nur {dist_mean:.1f}%. "
                f"Die Aktie atmet normalerweise auf den EMA20 zurück. "
                f"Warte auf diesen Rücksetzer — dann einsteigen."
            )
        parts = []
        if mos and mos > 15:
            parts.append(f"Kurs liegt {mos:.0f}% unter dem fairen Wert.")
        if dist20 and abs(dist20) < 3 and trend_ok:
            parts.append("Kurs am EMA20 im Aufwärtstrend — klassischer Einstiegspunkt.")
        if crossed:
            parts.append("MACD gerade nach oben gedreht — Momentum dreht.")
        if above200 and trend_ok and macd_ok:
            parts.append("Alle drei EMAs im Aufwärtstrend.")
        if not parts:
            parts.append("Fundamentaldaten und Technik zeigen grünes Licht.")
        return "Guter Einstieg. " + " ".join(parts)

    elif sig == "ABWARTEN":
        hints = []
        if pullback and dist20 and dist20 > 5:
            hints.append(f"Kurs {dist20:.1f}% über EMA20 — Rücksetzer auf EMA20 ({fmt_usd(r.get('ema20'))} Bereich) abwarten.")
        elif dist20 and dist20 > 8:
            hints.append(f"Kurs {dist20:.1f}% über EMA20 — etwas überhitzt.")
        if not trend_ok:
            hints.append("EMA20 noch unter EMA50 — kein klarer Aufwärtstrend.")
        if not macd_ok:
            hints.append("MACD noch kein positives Signal.")
        if mos and mos < -10:
            hints.append(f"Kurs {abs(mos):.0f}% über fairem Wert — zu teuer.")
        if not hints:
            hints.append("Noch nicht alle Kriterien erfüllt.")
        return "Abwarten. " + " ".join(hints)

    else:
        return "Nicht kaufen. Zu viele rote Signale — warte bis sich das Bild klar verbessert."

@st.cache_data(ttl=1800, show_spinner=False)
def get_news(ticker):
    try:
        items = yf.Ticker(ticker).news or []
        return items[:6]
    except Exception:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def quick_check(ticker):
    """Schneller technischer Check — nur Kursdaten, kein stock.info."""
    try:
        hist = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        hist.columns = hist.columns.get_level_values(0)
        if len(hist) < 50:
            return None
        price  = float(hist["Close"].iloc[-1])
        ema20  = float(hist["Close"].ewm(span=20,  adjust=False).mean().iloc[-1])
        ema50  = float(hist["Close"].ewm(span=50,  adjust=False).mean().iloc[-1])
        ema200 = float(hist["Close"].ewm(span=200, adjust=False).mean().iloc[-1])
        # RSI
        delta = hist["Close"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rsi   = float((100 - 100 / (1 + gain / loss.replace(0, 1e-9))).iloc[-1])
        # MACD
        macd  = hist["Close"].ewm(span=12,adjust=False).mean() - hist["Close"].ewm(span=26,adjust=False).mean()
        macd_bull = float(macd.iloc[-1]) > float(macd.ewm(span=9,adjust=False).mean().iloc[-1])
        high_52w  = float(hist["High"].max())
        pct_high  = round((price - high_52w) / high_52w * 100, 1)
        perf_1y   = round((price / float(hist["Close"].iloc[0]) - 1) * 100, 1)
        # Punkte (rein technisch)
        pts = sum([
            price > ema200,
            ema20  > ema50,
            35 <= rsi <= 74,
            pct_high <= -5,
            macd_bull,
            perf_1y > 20,
        ])
        if pts >= 5:
            verdict, col, bg, brd = "Sehr interessant", "#00a844", "#e8fff2", "#00c853"
        elif pts >= 3:
            verdict, col, bg, brd = "Beobachten",      "#d97700", "#fff8e8", "#ff9800"
        else:
            verdict, col, bg, brd = "Nicht jetzt",     "#d32f2f", "#fff0f0", "#f44336"
        return {
            "verdict": verdict, "col": col, "bg": bg, "brd": brd,
            "price": round(price, 2), "rsi": round(rsi, 1),
            "above_ema200": price > ema200, "ema20_above_50": ema20 > ema50,
            "macd_bull": macd_bull, "pct_high": pct_high, "perf_1y": perf_1y,
        }
    except Exception:
        return None

# ── Kauf-Signal Scanner ───────────────────────────────────────────────────────
SCAN_UNIVERSE = [
    # Mega Cap Tech
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AVGO","ORCL","ADBE",
    "CRM","INTU","NFLX","AMD","QCOM","TXN","AMAT","LRCX","KLAC","CDNS",
    "SNPS","MCHP","ON","MPWR","MU","ADI","INTC","SMCI","ARM","PLTR",
    # Gesundheit
    "LLY","UNH","JNJ","ABT","TMO","ABBV","MRK","MDT","ELV","ISRG",
    "REGN","VRTX","IDXX","DXCM","BSX","PODD","WST","GEHC","HUM","CI",
    "BIIB","MRNA","ILMN","ZBH","RMD","BDX","ALGN","HOLX","IQV","STE",
    # Finanzen
    "JPM","BAC","WFC","GS","MS","AXP","BLK","SCHW","ICE","CME",
    "COF","V","MA","SPGI","MCO","CB","PGR","AON","MMC","MSCI",
    "NDAQ","FIS","FISV","AMP","LPLA","LPL","MKTX","STT","BEN","IVZ",
    # Industrie
    "CAT","DE","HON","ITW","GE","UPS","FDX","LMT","RTX","NOC",
    "GD","BA","MMM","EMR","ROK","PH","ETN","AME","FAST","FIX",
    "GEV","MLM","VMC","CBRE","CARR","OTIS","XYL","IEX","GNRC","URI",
    "NSC","CSX","UNP","WAB","JBHT","CHRW","EXPD","GWW","PWR","MTZ",
    # Energie
    "XOM","CVX","COP","SLB","EOG","MPC","PSX","VLO","OXY","HAL",
    "DVN","FANG","HES","BKR","KMI","WMB","OKE","LNG","COP","APA",
    # Konsum
    "COST","HD","WMT","TGT","LOW","MCD","SBUX","NKE","BKNG","HLT",
    "MAR","RCL","DECK","ROST","TJX","ULTA","DRI","YUM","CMG","ABNB",
    "UBER","EXPE","CVNA","CAVA","WING","DKNG","LVS","WYNN","MGM",
    "KO","PEP","PM","MO","STZ","TAP","SYY","HSY","GIS","K",
    "CPB","HRL","MKC","CAG","SJM","CLX","CHD","ENR","PG","CL",
    # Kommunikation / Medien
    "GOOGL","META","NFLX","DIS","CMCSA","T","VZ","TMUS","CHTR","EA",
    "TTWO","RBLX","SPOT","SNAP","PINS","ZM","MTCH","IAC","OMC","IPG",
    # Software / Cloud / Cyber
    "NOW","SNOW","DDOG","NET","ZS","CRWD","OKTA","PANW","FTNT","HUBS",
    "VEEV","WDAY","ADSK","ANSS","PTC","TTD","SHOP","MELI","SE","U",
    "MDB","GTLB","CFLT","SAMSF","BILL","PCTY","PAYC","PAYX","ADP","JKHY",
    # Rohstoffe / Materialien
    "NEM","FCX","SCCO","AA","ALB","MP","LIN","APD","ECL","PPG",
    "NUE","STLD","CLF","X","CF","MOS","FMC","CE","LYB","DOW",
    # Versorger
    "NEE","DUK","SO","AEP","D","EXC","ED","SRE","PCG","XEL",
    # REITs
    "AMT","CCI","PLD","EQIX","SPG","O","VICI","PSA","IRM","WY",
    # Mid Cap Wachstum
    "AXON","CELH","ELF","TOST","NTRA","CAVA","MEDP","RXRX","SOUN",
    "SMMT","POWL","ONTO","TMDX","NUVL","SKX","YETI","VRSK","WEX",
    "KSPI","GTLS","FND","LPX","NVR","PHM","DHI","LEN","TOL","MDC",
    # Extra S&P 500
    "ACGL","AFL","AIZ","APH","ARE","ATO","AVB","AVY","AZO","BAX",
    "BRK-B","BWA","C","CBOE","CDW","CF","CINF","CMS","CNP","COO",
    "CPRT","CTSH","CTVA","DAL","DD","DLTR","DOV","DTE","DVA","ECL",
    "EFX","EIX","EL","EQT","ES","EW","EXR","F","FDS","FE",
    "FFIV","FMC","GL","GLW","GM","GPC","GRMN","HAS","HPE","HPQ",
    "HST","HUBB","HWM","IBM","IFF","INCY","IP","J","JCI","KEY",
    "KHC","KMB","KMX","L","LH","LUV","LYV","MAS","MKC","MOH",
    "MSCI","MTB","MTD","NEM","NRG","NTAP","NUE","OKE","PEG","PFG",
    "PKG","PNC","PPL","PRU","RSG","SBAC","SNA","STX","SWK","SYF",
    "SYK","TAP","TDG","TER","TFC","TGT","TPR","TRMB","TSCO","TSN",
    "TT","TXT","UAL","UDR","UHS","USB","VFC","VMW","VTR","WAT",
    "WBA","WELL","WHR","WM","WRB","WYNN","XEL","XRAY","ZBRA","ZION",
]

@st.cache_data(ttl=86400, show_spinner=False)
def scan_top_picks():
    """Batch-Scan aller Aktien auf technische Kaufsignale. Einmal am Tag gecacht."""
    try:
        tickers = list(dict.fromkeys(SCAN_UNIVERSE))  # Duplikate entfernen
        # Batch-Download: alle Aktien auf einmal — deutlich schneller
        raw = yf.download(tickers, period="1y", progress=False,
                          auto_adjust=True, group_by="ticker", threads=True)

        results = []
        for ticker in tickers:
            try:
                # Daten für diesen Ticker extrahieren
                if len(tickers) > 1:
                    df = raw[ticker].dropna(how="all")
                else:
                    df = raw.dropna(how="all")
                df.columns = df.columns.get_level_values(0) if hasattr(df.columns, "get_level_values") else df.columns

                if len(df) < 60 or "Close" not in df.columns:
                    continue

                close  = df["Close"].astype(float)
                high   = df["High"].astype(float)
                low    = df["Low"].astype(float)
                volume = df["Volume"].astype(float)
                price  = float(close.iloc[-1])

                if price < 10:
                    continue

                # EMAs
                ema20  = close.ewm(span=20,  adjust=False).mean()
                ema50  = close.ewm(span=50,  adjust=False).mean()
                ema200 = close.ewm(span=200, adjust=False).mean()

                # MACD
                macd_line   = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                macd_hist   = macd_line - signal_line
                macd_bullish  = bool(macd_hist.iloc[-1] > 0)
                macd_crossed  = bool(macd_hist.iloc[-1] > 0 and macd_hist.iloc[-4] <= 0)

                # RSI
                delta = close.diff()
                gain  = delta.clip(lower=0).rolling(14).mean()
                loss  = (-delta.clip(upper=0)).rolling(14).mean()
                rsi   = float((100 - 100 / (1 + gain / loss.replace(0, 1e-9))).iloc[-1])

                # Trendstruktur (höhere Hochs + höhere Tiefs)
                seg = high.iloc[-60:].reset_index(drop=True)
                sl  = low.iloc[-60:].reset_index(drop=True)
                h1, h2, h3 = seg[:20].max(), seg[20:40].max(), seg[40:].max()
                l1, l2, l3 = sl[:20].min(),  sl[20:40].min(),  sl[40:].min()
                is_uptrend = bool(h3 > h2 > h1 and l3 > l2 > l1)

                # EMA-Ausrichtung
                e20, e50, e200 = float(ema20.iloc[-1]), float(ema50.iloc[-1]), float(ema200.iloc[-1])
                ema_perfect   = price > e20 > e50 > e200
                ema_ok        = price > e200 and e20 > e50

                # Flaggen-Muster (Konsolidierung nach starkem Anstieg)
                move_20d = (price / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else 0
                move_5d  = (price / float(close.iloc[-6])  - 1) * 100 if len(close) > 6 else 0
                std_5d   = float(close.iloc[-6:].pct_change().std() * 100)
                flag_detected = bool(move_20d > 8 and abs(move_5d) < 3 and std_5d < 2.5)

                # 52-Wochen
                high_52w  = float(high.max())
                pct_high  = (price - high_52w) / high_52w * 100

                # Volumen-Bestätigung
                avg_vol    = float(volume.rolling(20).mean().iloc[-1])
                recent_vol = float(volume.iloc[-5:].mean())
                vol_up     = recent_vol > avg_vol * 1.1

                # ── Technische Wahrscheinlichkeit (0–95) ──────────────────────
                score   = 0
                reasons = []

                if is_uptrend:
                    score += 22
                    reasons.append("Aufwärtstrend — höhere Hochs und höhere Tiefs")
                if ema_perfect:
                    score += 20
                    reasons.append("EMA perfekt ausgerichtet: Kurs > EMA20 > EMA50 > EMA200")
                elif ema_ok:
                    score += 10
                    reasons.append("Kurs über EMA200, EMA20 über EMA50")
                if macd_bullish:
                    score += 13
                    reasons.append("MACD positiv — Momentum bullisch")
                if macd_crossed:
                    score += 7
                    reasons.append("MACD gerade nach oben gekreuzt — frisches Kaufsignal")
                if 50 <= rsi <= 68:
                    score += 15
                    reasons.append(f"RSI {rsi:.0f} — bullisch, nicht überkauft")
                elif 40 <= rsi < 50:
                    score += 7
                    reasons.append(f"RSI {rsi:.0f} — erholt sich, zeigt Stärke")
                if flag_detected:
                    score += 15
                    reasons.append(f"Flaggen-Muster — {move_20d:.0f}% Anstieg, jetzt gesunde Pause")
                if -20 <= pct_high <= -5:
                    score += 5
                    reasons.append(f"{abs(pct_high):.0f}% unter 52W-Hoch — Luft nach oben")
                if vol_up and macd_bullish:
                    score += 3
                    reasons.append("Volumen bestätigt das Momentum")

                # Mindest-Score: Aufwärtstrend MUSS vorhanden sein
                if not (is_uptrend or ema_ok):
                    continue

                results.append({
                    "ticker":      ticker,
                    "price":       round(price, 2),
                    "score":       score,
                    "probability": min(score, 95),
                    "reasons":     reasons,
                    "rsi":         round(rsi, 1),
                    "macd_crossed": macd_crossed,
                    "flag":        flag_detected,
                    "uptrend":     is_uptrend,
                    "ema_perfect": ema_perfect,
                    "pct_high":    round(pct_high, 1),
                    "move_20d":    round(move_20d, 1),
                })

            except Exception:
                continue

        results.sort(key=lambda x: -x["score"])
        return results

    except Exception:
        return []

# ── Seite ─────────────────────────────────────────────────────────────────────
data = load_data()

# Session State für persistente Analyse (Chart-Wechsel ohne Datenverlust)
if "res" not in st.session_state:
    st.session_state["res"] = None

st.markdown(
    '<h1><a href="/" style="color:#472d93;text-decoration:none;cursor:pointer" '
    'title="Zurück zur Startseite">📈 Heidis Aktien-Assistent</a></h1>',
    unsafe_allow_html=True
)
st.caption("⚠️ Dieses Tool dient ausschließlich zur persönlichen Information. Keine Finanz- oder Anlageberatung. Alle Entscheidungen liegen allein bei dir. Kursdaten von Yahoo Finance — keine Gewähr für Richtigkeit.")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Analyse", "💼 Portfolio", "👁️ Watchlist", "🎯 Kauf-Signale", "📚 Wie funktioniert das?"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – ANALYSE
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_inp, col_btn = st.columns([4, 1])
    ticker_input = col_inp.text_input(
        "Ticker", placeholder="Name oder Kürzel, z.B. Apple oder AAPL",
        label_visibility="collapsed"
    )
    analyse_btn = col_btn.button("Analysieren", type="primary", use_container_width=True)

    if ticker_input and analyse_btn:
        ticker_resolved = resolve_ticker(ticker_input)
        with st.spinner(f"Analysiere {ticker_resolved} …"):
            result = analyze_stock(ticker_resolved)
        if not result:
            st.error("Aktie nicht gefunden. Bitte Namen oder US-Ticker eingeben.")
            st.session_state["res"] = None
        else:
            st.session_state["res"] = result

    res = st.session_state.get("res")

    # ── Top US-Aktien ─────────────────────────────────────────────────────────
    if not res:
        st.markdown("---")
        st.subheader("Top US-Aktien — Gerade interessant")
        st.caption("~90 Aktien werden gescannt — typisch über 80$ pro Aktie, quer durch alle Sektoren. Einmalig 4-6 Minuten, danach gecacht.")

        TOP_UNIVERSE = [
            # Mega Cap
            "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","LLY","UNH","JPM",
            "V","MA","AVGO","COST","HD","JNJ","PG","ABBV","BRK-B","XOM",
            # Tech & Software
            "NFLX","CRM","ADBE","INTU","NOW","MELI","ASML","FICO","ISRG","TMO",
            "IDXX","MCO","SPGI","VEEV","HUBS","PANW","CRWD","FTNT","ZS","ANET",
            # Halbleiter
            "ORCL","QCOM","TXN","KLAC","LRCX","AMAT","MU","ADI","CDNS","SNPS",
            # Wachstum / Mid Cap
            "DDOG","NET","TTD","PLTR","SHOP","AXON","CAVA","ABNB","SNOW","MDB",
            "OKTA","UBER",
            # Industrie / Infrastruktur
            "FIX","GEV","MLM","VMC","CBRE","CAT","DE","HON","ITW","ADP",
            # Gesundheit
            "PODD","WST","ELV","REGN","BIIB","DXCM","GEHC","ALGN",
            # Finanzen
            "GS","MS","AXP","BLK","SCHW","ICE","CME",
            # Konsum / Reise
            "BKNG","RCL","HLT","MAR","SBUX","DECK","NKE",
        ]

        load_top = st.button("Top-Aktien laden", type="primary")
        if load_top or st.session_state.get("top_loaded"):
            st.session_state["top_loaded"] = True
            if "top_results" not in st.session_state:
                prog = st.progress(0, text="Scanne US-Markt …")
                top_results = []
                for idx, t in enumerate(TOP_UNIVERSE):
                    prog.progress((idx+1)/len(TOP_UNIVERSE), text=f"Analysiere {t} …")
                    r = analyze_stock(t)
                    if r:
                        top_results.append(r)
                prog.empty()
                top_results.sort(key=lambda x: (-x["green"], -(x.get("margin_of_safety") or -99)))
                st.session_state["top_results"] = top_results

            top_results = st.session_state.get("top_results", [])
            kaufen  = [r for r in top_results if r["signal"] == "KAUFEN"][:5]
            warten  = [r for r in top_results if r["signal"] == "ABWARTEN"][:3]
            show    = kaufen + warten

            if show:
                for r in show:
                    sig_color = {"KAUFEN":"#00a844","ABWARTEN":"#d97700"}.get(r["signal"],"#888")
                    sig_bg    = {"KAUFEN":"#e8fff2","ABWARTEN":"#fff8e8"}.get(r["signal"],"#f5f5f5")
                    sig_border= {"KAUFEN":"#00c853","ABWARTEN":"#ff9800"}.get(r["signal"],"#ccc")
                    mos_text  = f" · {r['margin_of_safety']:+.0f}% zum fairen Preis" if r.get("margin_of_safety") else ""
                    trend_txt = "↑ Aufwärtstrend" if r.get("ema20_above_50") else "→ Seitwärts"

                    col_info, col_btn2 = st.columns([5, 1])
                    with col_info:
                        st.markdown(f"""
                        <div style="background:{sig_bg};border:1px solid {sig_border};border-radius:12px;
                             padding:14px 18px;margin-bottom:8px;cursor:pointer">
                            <div style="display:flex;justify-content:space-between;align-items:center">
                                <div>
                                    <span style="color:#472d93;font-weight:700;font-size:1rem">{r['ticker']}</span>
                                    <span style="color:#888;font-size:0.85rem;margin-left:8px">{r['name'][:35]}</span>
                                </div>
                                <span style="color:{sig_color};font-weight:800;font-size:0.95rem">{r['signal']}  {r['score_ratio']}</span>
                            </div>
                            <div style="color:#555;font-size:0.82rem;margin-top:6px">
                                {fmt_usd(r['current_price'])} · Fairer Preis {fmt_usd(r.get('fair_price'))}{mos_text} · {trend_txt}
                            </div>
                            <div style="color:#7c5cbf;font-size:0.8rem;margin-top:4px">{r.get('buy_text','')[:120]}…</div>
                        </div>""", unsafe_allow_html=True)
                    with col_btn2:
                        if st.button("Analysieren", key=f"top_{r['ticker']}"):
                            st.session_state["res"] = r
                            st.rerun()

    if res:
        # ── Zwei-Signal-Banner: Unternehmen vs. Timing ────────────────────────
        f_sig = res.get("fundamental_signal", "ABWARTEN")
        t_sig = res.get("technical_signal",   "ABWARTEN")

        # Timing-Signal: wenn fundamental gut aber Timing schlecht → explizit ABWARTEN
        if f_sig == "KAUFEN" and t_sig in ("ABWARTEN", "FINGER WEG"):
            timing_label = "JETZT ABWARTEN"
            timing_bg, timing_border, timing_col = "#fff8e8", "#ff9800", "#d97700"
            timing_icon  = "⏳"
        elif f_sig == "KAUFEN" and t_sig == "KAUFEN":
            timing_label = "JETZT EINSTEIGEN"
            timing_bg, timing_border, timing_col = "#e8fff2", "#00c853", "#00a844"
            timing_icon  = "✅"
        elif f_sig == "FINGER WEG":
            timing_label = "NICHT KAUFEN"
            timing_bg, timing_border, timing_col = "#fff0f0", "#f44336", "#d32f2f"
            timing_icon  = "🚫"
        else:
            timing_label = "BEOBACHTEN"
            timing_bg, timing_border, timing_col = "#fff8e8", "#ff9800", "#d97700"
            timing_icon  = "👀"

        f_bg  = {"KAUFEN":"#e8fff2","ABWARTEN":"#fff8e8","FINGER WEG":"#fff0f0"}.get(f_sig,"#f5f5f5")
        f_brd = {"KAUFEN":"#00c853","ABWARTEN":"#ff9800","FINGER WEG":"#f44336"}.get(f_sig,"#ccc")
        f_col = {"KAUFEN":"#00a844","ABWARTEN":"#d97700","FINGER WEG":"#d32f2f"}.get(f_sig,"#888")

        f_text = {
            "KAUFEN":     "Starkes Unternehmen. Gute Zahlen, solides Wachstum.",
            "ABWARTEN":   "Solides Unternehmen, aber nicht alle Kriterien erfüllt.",
            "FINGER WEG": "Schwache Fundamentaldaten — Vorsicht.",
        }.get(f_sig, "")

        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:12px">
          <div style="flex:1;background:{f_bg};border:2px solid {f_brd};border-radius:14px;padding:18px 22px">
            <div style="color:#666;font-size:0.75rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.5px;margin-bottom:6px">Das Unternehmen</div>
            <div style="color:{f_col};font-size:1.5rem;font-weight:900;margin-bottom:4px">{f_sig}</div>
            <div style="color:#555;font-size:0.88rem">{f_text}</div>
          </div>
          <div style="flex:1;background:{timing_bg};border:2px solid {timing_border};border-radius:14px;padding:18px 22px">
            <div style="color:#666;font-size:0.75rem;font-weight:700;text-transform:uppercase;
                 letter-spacing:0.5px;margin-bottom:6px">Einstieg jetzt?</div>
            <div style="color:{timing_col};font-size:1.5rem;font-weight:900;margin-bottom:4px">{timing_icon} {timing_label}</div>
            <div style="color:#555;font-size:0.88rem">{res["buy_text"]}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Marktlage ─────────────────────────────────────────────────────────
        mkt = get_market_context()
        mkt_color  = "#e8fff2" if mkt["bull_market"] else "#fff0f0"
        mkt_border = "#00c853" if mkt["bull_market"] else "#f44336"
        mkt_icon   = "🟢" if mkt["bull_market"] else "🔴"
        vix_warn   = f"  ·  ⚠️ VIX {mkt['vix']} ({mkt['vix_status']}) — Markt nervös, Positionsgrößen reduzieren" if mkt["vix"] >= 25 else f"  ·  VIX {mkt['vix']} ({mkt['vix_status']})"
        st.markdown(
            f'<div style="background:{mkt_color};border:1px solid {mkt_border};border-radius:10px;'
            f'padding:10px 16px;margin-bottom:8px;font-size:0.88rem;color:#333">'
            f'{mkt_icon} <strong>Marktlage:</strong> S&P 500 {"im Aufwärtstrend" if mkt["spy_above_200"] else "unter EMA200 — Vorsicht"}  '
            f'·  1M-Performance: {fmt_pct(mkt["spy_trend_1m"])}{vix_warn}</div>',
            unsafe_allow_html=True
        )

        # ── Header ────────────────────────────────────────────────────────────
        st.subheader(f"{res['name']}  ({res['ticker']})")
        st.caption(f"{res['sector']}  ·  {res['industry']}")

        st.divider()

        # ── Kennzahlen ────────────────────────────────────────────────────────
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Aktueller Kurs", fmt_usd(res["current_price"]))
        c2.metric(
            "Fairer Preis",
            fmt_usd(res.get("fair_price")),
            delta=fmt_pct(res.get("margin_of_safety")) if res.get("margin_of_safety") is not None else None,
            help="EPS-Wachstum × zukünftiges KGV, diskontiert mit 15% Mindestrendite"
        )
        c3.metric("5J-Performance", fmt_pct(res.get("perf_5y")),
                  help="Wie viel Prozent hat die Aktie in den letzten 5 Jahren gewonnen? Ziel: mindestens +150%.")
        c4.metric("KGV (trailing)", f"{res['pe_ratio']:.1f}" if res.get("pe_ratio") else "—",
                  help="Kurs-Gewinn-Verhältnis: Wie viel zahlst du für 1€ Jahresgewinn? KGV 20 = du zahlst 20€ für 1€ Gewinn. Quelle: Yahoo Finance.")
        c5.metric("EPS (ttm)", fmt_usd(res.get("eps_ttm")),
                  help="Earnings Per Share = Gewinn pro Aktie der letzten 12 Monate. Je höher und steigender, desto besser. Quelle: Yahoo Finance.")
        rsi_val = res.get("rsi")
        c6.metric("RSI (14)", f"{rsi_val}" if rsi_val else "—",
                  delta=res.get("rsi_signal"), delta_color="off",
                  help="Relative Strength Index: unter 35 = überverkauft (günstig), 35–74 = gesunder Bereich, über 74 = überkauft (zu teuer, warten). Quelle: Kurshistorie.")
        c7.metric("Vom Jahreshoch", fmt_pct(res.get("pct_from_52w_high")),
                  help="Wie weit ist der Kurs vom 52-Wochen-Hoch entfernt? Wert nahe 0% = am Jahreshoch = Vorsicht. Wert unter -15% = mögliche Kaufzone.")

        st.divider()

        # ── Chart mit Plotly + MACD ───────────────────────────────────────────
        st.subheader("Chart")
        c_radio, c_tv = st.columns([3, 1])
        zeitrahmen = c_radio.radio(
            "Zeitrahmen", ["Tag (1 Jahr)", "Woche (3 Jahre)"],
            horizontal=True, label_visibility="collapsed", key="chart_interval"
        )
        exchange = "NASDAQ" if res.get("sector") in ["Technology","Consumer Cyclical","Communication Services","Healthcare"] else "NYSE"
        tv_url = f"https://www.tradingview.com/chart/?symbol={exchange}%3A{res['ticker']}"
        c_tv.markdown(f"<a href='{tv_url}' target='_blank' style='text-decoration:none'><div style='background:white;color:#472d93;border:2px solid #472d93;border-radius:10px;padding:10px 14px;text-align:center;font-weight:800;font-size:0.88rem;cursor:pointer;line-height:1.4'>📊 Auf TradingView öffnen<br><span style=\"color:#7c5cbf;font-size:0.75rem;font-weight:500\">&#8599; hier klicken</span></div></a>", unsafe_allow_html=True)

        h = res.get("_hist")
        if h:
            # Wochendaten laden falls nötig
            if zeitrahmen == "Woche (3 Jahre)":
                try:
                    hw = yf.Ticker(res["ticker"]).history(period="3y", interval="1wk")
                    hw["EMA20"]  = hw["Close"].ewm(span=20,  adjust=False).mean()
                    hw["EMA50"]  = hw["Close"].ewm(span=50,  adjust=False).mean()
                    hw["EMA200"] = hw["Close"].ewm(span=200, adjust=False).mean()
                    dates  = hw.index.strftime("%Y-%m-%d").tolist()
                    opens  = hw["Open"].round(2).tolist()
                    highs  = hw["High"].round(2).tolist()
                    lows   = hw["Low"].round(2).tolist()
                    closes = hw["Close"].round(2).tolist()
                    e20 = hw["EMA20"].round(2).tolist()
                    e50 = hw["EMA50"].round(2).tolist()
                    e200= hw["EMA200"].round(2).tolist()
                except Exception:
                    dates, opens, highs, lows, closes = h["dates"], h["open"], h["high"], h["low"], h["close"]
                    e20, e50, e200 = h["ema20"], h["ema50"], h["ema200"]
            else:
                dates, opens, highs, lows, closes = h["dates"], h["open"], h["high"], h["low"], h["close"]
                e20, e50, e200 = h["ema20"], h["ema50"], h["ema200"]

            # MACD berechnen
            cl = pd.Series(closes)
            macd_line   = cl.ewm(span=12, adjust=False).mean() - cl.ewm(span=26, adjust=False).mean()
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram   = macd_line - signal_line
            hist_colors = ["rgba(0,200,83,0.7)" if v >= 0 else "rgba(244,67,54,0.7)" for v in histogram]

            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.70, 0.30],
                vertical_spacing=0.04
            )

            # Kerzen
            fig.add_trace(go.Candlestick(
                x=dates, open=opens, high=highs, low=lows, close=closes,
                name=res["ticker"],
                increasing_line_color="#00c853", decreasing_line_color="#f44336",
                increasing_fillcolor="rgba(0,200,83,0.5)",
                decreasing_fillcolor="rgba(244,67,54,0.5)",
            ), row=1, col=1)

            # EMAs
            fig.add_trace(go.Scatter(x=dates, y=e20,  mode="lines", name="EMA 20",  line=dict(color="#FFD700", width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=dates, y=e50,  mode="lines", name="EMA 50",  line=dict(color="#00C853", width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=dates, y=e200, mode="lines", name="EMA 200", line=dict(color="#F44336", width=2)), row=1, col=1)

            # MACD
            fig.add_trace(go.Bar(x=dates, y=histogram.tolist(), name="MACD Hist", marker_color=hist_colors, showlegend=False), row=2, col=1)
            fig.add_trace(go.Scatter(x=dates, y=macd_line.tolist(),   mode="lines", name="MACD",   line=dict(color="#472d93", width=1.5)), row=2, col=1)
            fig.add_trace(go.Scatter(x=dates, y=signal_line.tolist(), mode="lines", name="Signal", line=dict(color="#e5c5f1", width=1.5)), row=2, col=1)

            fig.update_layout(
                height=560, margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white", paper_bgcolor="#f8f4ff",
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
                xaxis2=dict(gridcolor="#f0e8ff"),
                yaxis=dict(gridcolor="#f0e8ff"),
                yaxis2=dict(gridcolor="#f0e8ff", title="MACD"),
                dragmode="zoom",
            )
            fig.update_xaxes(showgrid=True, gridcolor="#f0e8ff")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Zoom: Bereich markieren. Zurücksetzen: Doppelklick. Für Zeichenwerkzeuge → TradingView-Button oben rechts.")
        else:
            st.info("Keine Chartdaten verfügbar.")

        st.divider()

        # ── Fundamentale vs. Technische Analyse ──────────────────────────────
        st.subheader("Analyse-Urteil")
        c_fund, c_tech = st.columns(2)

        def analysis_card(title, signal, score, scores_dict, description):
            css  = signal_css(signal)
            colors = {"KAUFEN": ("#e8fff2","#00c853","#00a844"),
                      "ABWARTEN": ("#fff8e8","#ff9800","#d97700"),
                      "FINGER WEG": ("#fff0f0","#f44336","#d32f2f")}
            bg, border, txt = colors.get(signal, ("#f5f5f5","#ccc","#888"))
            rows = "".join(
                f'<div style="padding:3px 0;font-size:0.88rem;color:#2d1f4e">'
                f'{score_icon(v)}&nbsp;{k}</div>'
                for k, v in scores_dict.items()
            )
            return f"""
            <div style="background:{bg};border:2px solid {border};border-radius:14px;
                 padding:18px 20px;height:100%">
                <div style="color:#472d93;font-weight:700;font-size:0.85rem;
                     text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px">{title}</div>
                <div style="color:{txt};font-size:1.6rem;font-weight:900;margin-bottom:4px">{signal}</div>
                <div style="color:#888;font-size:0.8rem;margin-bottom:12px">Score: {score}</div>
                <div style="font-size:0.78rem;color:#7c5cbf;margin-bottom:10px">{description}</div>
                {rows}
            </div>"""

        with c_fund:
            st.markdown(analysis_card(
                "Fundamentale Analyse",
                res.get("fundamental_signal","—"),
                res.get("fundamental_score","—"),
                res.get("fundamental_scores",{}),
                "Umsatz, Gewinn, Schulden, fairer Preis — wie gesund ist das Unternehmen?"
            ), unsafe_allow_html=True)

        with c_tech:
            st.markdown(analysis_card(
                "Technische Analyse",
                res.get("technical_signal","—"),
                res.get("technical_score","—"),
                res.get("technical_scores",{}),
                "Trend, MACD, RSI, Abstand vom Hoch — ist jetzt ein guter Einstiegszeitpunkt?"
            ), unsafe_allow_html=True)

            def mini_badge(signal):
                cfg = {
                    "KAUFEN":     ("#e8fff2","#00c853","#00a844"),
                    "ABWARTEN":   ("#fff8e8","#ff9800","#d97700"),
                    "FINGER WEG": ("#fff0f0","#f44336","#d32f2f"),
                }
                bg, border, col = cfg.get(signal, ("#f5f5f5","#ccc","#888"))
                return (f'<span style="background:{bg};color:{col};border:1px solid {border};'
                        f'border-radius:6px;padding:2px 10px;font-size:0.78rem;font-weight:800">{signal}</span>')

            # Trendstruktur
            ts     = res.get("trend_structure", "")
            ts_det = res.get("trend_structure_detail", "")
            ts_sig = res.get("trend_structure_signal", "neutral")
            ts_col = {"bullish":"#00a844","bearish":"#d32f2f","neutral":"#d97700"}.get(ts_sig,"#888")
            ts_ico = {"bullish":"↑","bearish":"↓","neutral":"→"}.get(ts_sig,"→")
            ts_badge_sig = {"bullish":"KAUFEN","bearish":"FINGER WEG","neutral":"ABWARTEN"}.get(ts_sig,"ABWARTEN")
            if ts:
                st.markdown(f"""
                <div style="background:white;border:1px solid #e5c5f1;border-radius:10px;
                     padding:12px 16px;margin-top:10px">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                    <span style="color:#7c5cbf;font-size:0.72rem;font-weight:600;text-transform:uppercase">Trendstruktur (Dow-Theorie)</span>
                    {mini_badge(ts_badge_sig)}
                  </div>
                  <div style="color:{ts_col};font-weight:700;font-size:1rem">{ts_ico} {ts}</div>
                  <div style="color:#666;font-size:0.8rem;margin-top:2px">{ts_det}</div>
                </div>""", unsafe_allow_html=True)

            # Kerzenformation
            cp  = res.get("candle_pattern","")
            cs  = res.get("candle_signal","neutral")
            ct  = res.get("candle_tip","")
            cp_col   = {"bullish":"#00a844","bearish":"#d32f2f","neutral":"#d97700"}.get(cs,"#888")
            cp_badge = {"bullish":"KAUFEN","bearish":"FINGER WEG","neutral":"ABWARTEN"}.get(cs,"ABWARTEN")
            if cp:
                st.markdown(f"""
                <div style="background:white;border:1px solid #e5c5f1;border-radius:10px;
                     padding:12px 16px;margin-top:8px">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                    <span style="color:#7c5cbf;font-size:0.72rem;font-weight:600;text-transform:uppercase">Letzte Kerze 🕯️</span>
                    {mini_badge(cp_badge)}
                  </div>
                  <div style="color:{cp_col};font-weight:700;font-size:0.95rem">{cp}</div>
                  <div style="color:#666;font-size:0.8rem;margin-top:2px">{ct}</div>
                </div>""", unsafe_allow_html=True)

            # Support & Widerstand
            sup  = res.get("support")
            res2 = res.get("resistance")
            if sup or res2:
                cur_p = res["current_price"]
                near_sup = sup and abs(cur_p - sup) / cur_p < 0.04
                near_res = res2 and abs(res2 - cur_p) / cur_p < 0.05
                sr_badge = "KAUFEN" if near_sup else ("ABWARTEN" if near_res else "ABWARTEN")
                sr_hint  = ("Kurs nah an Unterstützung — gute Einstiegszone." if near_sup
                            else "Kurs nah am Widerstand — erst Ausbruch abwarten." if near_res
                            else f"Kurs liegt zwischen Support und Widerstand.")
                st.markdown(f"""
                <div style="background:white;border:1px solid #e5c5f1;border-radius:10px;
                     padding:12px 16px;margin-top:8px">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="color:#7c5cbf;font-size:0.72rem;font-weight:600;text-transform:uppercase">Support & Widerstand</span>
                    {mini_badge(sr_badge)}
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="color:#333;font-size:0.85rem">Widerstand (oben)</span>
                    <span style="color:#d32f2f;font-weight:700">{fmt_usd(res2)}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <span style="color:#333;font-size:0.85rem">Unterstützung (unten)</span>
                    <span style="color:#00a844;font-weight:700">{fmt_usd(sup)}</span>
                  </div>
                  <div style="color:#666;font-size:0.78rem">{sr_hint}</div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Earnings & Nachrichten (aufklappbar) ─────────────────────────────
        rev_g  = res.get("revenue_growth")
        earn_g = res.get("earnings_growth")
        news_label = f"📰 Nachrichten & Quartalszahlen — {res['name']}"
        with st.expander(news_label, expanded=False):
            # Quartalszahlen oben
            st.markdown("#### Quartalszahlen")
            ea, eb, ec, ed = st.columns(4)
            ea.metric("Nächster Earnings-Termin",
                      res.get("next_earnings_date") or "—",
                      help="An diesem Tag veröffentlicht das Unternehmen seine nächsten Quartalsergebnisse. Oft gibt es dann starke Kursbewegungen.")
            eb.metric("EPS aktuell (ttm)",
                      fmt_usd(res.get("eps_ttm")),
                      help="Gewinn pro Aktie der letzten 12 Monate.")
            ec.metric("EPS Prognose",
                      fmt_usd(res.get("eps_forward")),
                      help="Erwarteter Gewinn pro Aktie der nächsten 12 Monate laut Analysten.")
            ed.metric("Forward KGV",
                      f"{res['forward_pe']:.1f}" if res.get("forward_pe") else "—",
                      help="Wie viel zahlst du heute für den erwarteten Gewinn des nächsten Jahres?")

            st.markdown(f"""
            <div style="display:flex;gap:12px;margin:12px 0">
              <div style="flex:1;background:{'#e8fff2' if (rev_g or 0)>=0.10 else '#fff0f0'};
                   border-radius:10px;padding:12px 16px;border:1px solid {'#00c853' if (rev_g or 0)>=0.10 else '#f44336'}">
                <div style="color:#666;font-size:0.75rem;font-weight:600;text-transform:uppercase">Umsatzwachstum</div>
                <div style="color:{'#00a844' if (rev_g or 0)>=0.10 else '#d32f2f'};font-size:1.4rem;font-weight:800">
                  {f'+{rev_g*100:.1f}%' if rev_g else '—'}</div>
                <div style="color:#888;font-size:0.75rem">Ziel: mindestens +10%</div>
              </div>
              <div style="flex:1;background:{'#e8fff2' if (earn_g or 0)>=0.10 else '#fff0f0'};
                   border-radius:10px;padding:12px 16px;border:1px solid {'#00c853' if (earn_g or 0)>=0.10 else '#f44336'}">
                <div style="color:#666;font-size:0.75rem;font-weight:600;text-transform:uppercase">Gewinnwachstum</div>
                <div style="color:{'#00a844' if (earn_g or 0)>=0.10 else '#d32f2f'};font-size:1.4rem;font-weight:800">
                  {f'+{earn_g*100:.1f}%' if earn_g else '—'}</div>
                <div style="color:#888;font-size:0.75rem">Ziel: mindestens +10%</div>
              </div>
              <div style="flex:1;background:white;border-radius:10px;padding:12px 16px;border:1px solid #e5c5f1">
                <div style="color:#666;font-size:0.75rem;font-weight:600;text-transform:uppercase">Gewinnmarge</div>
                <div style="color:#472d93;font-size:1.4rem;font-weight:800">
                  {f'{res["profit_margin"]*100:.1f}%' if res.get("profit_margin") else '—'}</div>
                <div style="color:#888;font-size:0.75rem">Wieviel bleibt vom Umsatz übrig</div>
              </div>
            </div>""", unsafe_allow_html=True)

            st.divider()

            # Nachrichten
            st.markdown("#### Aktuelle Nachrichten & Infos")
            with st.spinner("Lade Nachrichten…"):
                news_items = get_news(res["ticker"])
            if news_items:
                for item in news_items:
                    title   = item.get("title", "")
                    url     = item.get("link") or item.get("url", "#")
                    pub     = item.get("publisher", "")
                    pub_ts  = item.get("providerPublishTime", 0)
                    age = ""
                    if pub_ts:
                        diff = datetime.now() - datetime.fromtimestamp(int(pub_ts))
                        age = f"vor {diff.seconds//3600}h" if diff.days == 0 else f"vor {diff.days}T"
                    st.markdown(
                        f'<div style="border-left:3px solid #472d93;padding:8px 14px;margin-bottom:10px;background:white;border-radius:0 8px 8px 0">'
                        f'<a href="{url}" target="_blank" style="color:#472d93;font-weight:600;'
                        f'font-size:0.92rem;text-decoration:none;line-height:1.4">{title}</a><br>'
                        f'<span style="color:#999;font-size:0.78rem">{pub} &nbsp;·&nbsp; {age}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("Keine aktuellen Nachrichten gefunden.")

        st.divider()

        col_left, col_right = st.columns(2)

        # ── Checkliste ────────────────────────────────────────────────────────
        SCORE_TIPS = {
            "Umsatzwachstum ≥10% (YoY)":   "Wächst der Jahresumsatz um mindestens 10%? Zeigt ob das Unternehmen mehr verkauft. Quelle: Yahoo Finance.",
            "Gewinnwachstum ≥10% (YoY)":   "Wächst der Gewinn um mindestens 10% pro Jahr? Wichtiger als Umsatz — das ist das Geld das übrig bleibt. Quelle: Yahoo Finance.",
            "ROIC/ROE ≥10%":               "Return on Equity: Wie effizient arbeitet das Unternehmen mit seinem Kapital? Über 10% ist gut. Wie eine Sparbuch-Rendite — aber fürs Unternehmen. Quelle: Yahoo Finance.",
            "Verschuldung ≤3× FCF":        "Langfristige Schulden geteilt durch Free Cashflow. ≤3 bedeutet: das Unternehmen könnte seine Schulden in 3 Jahren abbezahlen. Alles darüber ist riskant. Quelle: Yahoo Finance.",
            "5J-Performance ≥150%":        "Hat die Aktie in 5 Jahren mindestens 150% zugelegt? Zeigt ob das Unternehmen langfristig stark wächst. Quelle: Yahoo Finance Kurshistorie.",
            "Fairer Preis (≤10% drüber)":  "Liegt der aktuelle Kurs nahe oder unter dem berechneten fairen Wert? Wert = EPS × (1+Wachstum)^10 × KGV, diskontiert mit 15%.",
            "Aufwärtstrend EMA20 > EMA50": "EMA20 (20-Tage-Schnitt) über EMA50 (50-Tage-Schnitt) = kurzfristiger Aufwärtstrend bestätigt. Beide aus Kurshistorie berechnet.",
            "MACD bullisch":               "MACD-Linie über Signallinie = Momentum dreht nach oben. MACD = Differenz EMA12 minus EMA26. Aus Kurshistorie berechnet.",
            "RSI gesund (35–74)":          "RSI zwischen 35 und 74 = weder überkauft noch überverkauft. Über 74 = zu heiß, warten. Unter 35 = möglicherweise Kaufchance. Aus Kurshistorie berechnet.",
            "Nicht am Jahreshoch (>5% Abstand)": "Ist die Aktie mehr als 5% unter ihrem 52-Wochen-Hoch? Direkt am Jahreshoch = höheres Rücksetzer-Risiko. Mehr Abstand = mehr Sicherheit beim Einstieg.",
        }
        with col_left:
            st.subheader("Checkliste")
            for name, val in res["scores"].items():
                tip = SCORE_TIPS.get(name, "")
                st.markdown(
                    f'<div class="check-row" title="{tip}">{score_icon(val)}&nbsp;&nbsp;{name}'
                    f'&nbsp;<span style="color:#b39ddb;font-size:0.75rem;cursor:help" title="{tip}">ⓘ</span></div>',
                    unsafe_allow_html=True
                )
            st.caption("Wachstum basiert auf aktuellen Jahresdaten von Yahoo Finance.")

            st.subheader("Stop-Loss Vorschlag")
            if res.get("stop_atr"):
                c_s1, c_s2, c_s3 = st.columns(3)
                c_s1.metric("Individuell (typ. Rücksetzer)",  fmt_usd(res.get("stop_individual")),
                            help=f"Basiert auf dem typischen Rücksetzer dieser Aktie: {res.get('typical_pullback', '—')}% (schlechteste 10% der letzten 12 Monate). Passt sich automatisch an das Verhalten der jeweiligen Aktie an.")
                c_s2.metric("ATR-basiert (2,5×)", fmt_usd(res["stop_atr"]),
                            help="ATR = Average True Range: die durchschnittliche tägliche Schwankung der letzten 14 Tage. 2,5× ATR = normaler Spielraum. Quelle: Kurshistorie.")
                c_s3.metric("60-Tage Swing Low",  fmt_usd(res["stop_swing"]),
                            help="Das tiefste Kursniveau der letzten 60 Handelstage. Fällt der Kurs darunter, ist der Aufwärtstrend gebrochen. Quelle: Kurshistorie.")
                st.caption("Empfehlung: Individuellen Stop verwenden — er berücksichtigt wie viel Luft diese Aktie historisch braucht. Beim Nachziehen: auf letztes bestätigtes Tief anpassen.")

        # ── Technik & CEO ─────────────────────────────────────────────────────
        with col_right:
            st.subheader("Gleitende Durchschnitte")
            if res.get("ema20"):
                price = res["current_price"]
                for label, val, col in [
                    ("EMA 20 — kurzfristig (gelb)",   res["ema20"],  "#FFD700"),
                    ("EMA 50 — mittelfristig (grün)",  res["ema50"],  "#00C853"),
                    ("EMA 200 — langfristig (rot)",    res["ema200"], "#F44336"),
                ]:
                    above = price > val
                    arrow = "▲" if above else "▼"
                    tcolor = "#00a844" if above else "#d32f2f"
                    diff  = price - val
                    st.markdown(f"""
                    <div class='ema-card'>
                        <div class='ema-label' style='color:{col}'>{label}</div>
                        <div class='ema-value'>{fmt_usd(val)}</div>
                        <div class='ema-sub' style='color:{tcolor}'>
                            {arrow} Kurs {'+' if diff>=0 else ''}{diff:.2f}$ {'darüber' if above else 'darunter'}
                        </div>
                    </div>""", unsafe_allow_html=True)

                trend = "Aufwärtstrend ✅" if res["ema20_above_50"] else "Kein klarer Trend ❌"
                macd  = "MACD bullisch ✅" if res["macd_bullish"]   else "MACD bärisch ❌"
                st.caption(f"{trend}  ·  {macd}")

            # CEO / Management
            st.subheader("Management")
            st.markdown(f"""
            <div class='ceo-card'>
                <div style='color:#7c5cbf;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>CEO / Top Management</div>
                <div style='color:#472d93;font-size:1.1rem;font-weight:700;margin:4px 0'>{res['ceo_name']}</div>
                <div style='color:#888;font-size:0.85rem'>{res['ceo_title']}</div>
                {'<div style="color:#7c5cbf;font-size:0.82rem;margin-top:6px">Vergütung: ${:,.0f}</div>'.format(res['ceo_pay']) if res.get('ceo_pay') else ''}
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Unternehmen Info ──────────────────────────────────────────────────
        if res.get("description"):
            with st.expander("Über das Unternehmen"):
                st.write(res["description"])
                if res.get("employees"):
                    st.caption(f"Mitarbeiter: {res['employees']:,}  ·  {res.get('website', '')}")

        # ── Kaufposition / Watchlist ──────────────────────────────────────────
        c_port, c_watch = st.columns(2)

        with c_port:
            st.subheader("Kaufposition eintragen")
            with st.form(f"form_port_{res['ticker']}"):
                ep  = st.number_input("Einstiegspreis ($)", min_value=0.01, value=float(res["current_price"]), format="%.2f")
                qty = st.number_input("Anzahl Aktien", min_value=1, value=1)
                bd  = st.date_input("Kaufdatum", value=date.today())
                sl  = st.number_input(
                    "Stop-Loss ($)", min_value=0.01,
                    value=float(res.get("stop_atr") or res["current_price"] * 0.90), format="%.2f"
                )
                note = st.text_input("Notiz (optional)")
                if st.form_submit_button("Kaufposition speichern", type="primary"):
                    data["portfolio"].append({
                        "ticker": res["ticker"], "name": res["name"],
                        "entry_price": ep, "quantity": qty,
                        "buy_date": str(bd), "stop_loss": sl, "notes": note,
                    })
                    save_data(data)
                    st.success(f"{res['ticker']} zum Portfolio hinzugefügt!")

        with c_watch:
            st.subheader("Watchlist")
            if res["ticker"] not in data["watchlist"]:
                if st.button(f"➕ {res['ticker']} zur Watchlist hinzufügen"):
                    data["watchlist"].append(res["ticker"])
                    save_data(data)
                    st.success("Hinzugefügt!")
            else:
                st.info(f"{res['ticker']} ist bereits in deiner Watchlist.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    data = load_data()

    # ── Manuell hinzufügen ────────────────────────────────────────────────────
    with st.expander("➕ Aktie manuell hinzufügen", expanded=not data["portfolio"]):
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            m_ticker = c1.text_input("Ticker oder Name", placeholder="z.B. AAPL oder Apple")
            m_name   = c2.text_input("Bezeichnung (optional)", placeholder="z.B. Apple Inc.")
            c3, c4, c5 = st.columns(3)
            m_price  = c3.number_input("Einstiegspreis ($)", min_value=0.01, value=100.00, format="%.2f")
            m_qty    = c4.number_input("Anzahl Aktien", min_value=1, value=1)
            m_sl     = c5.number_input("Stop-Loss ($)", min_value=0.01, value=90.00, format="%.2f")
            m_date   = st.date_input("Kaufdatum", value=date.today())
            m_note   = st.text_input("Notiz (optional)")
            if st.form_submit_button("Hinzufügen", type="primary"):
                if m_ticker:
                    t = resolve_ticker(m_ticker)
                    name = m_name or t
                    data["portfolio"].append({
                        "ticker": t, "name": name,
                        "entry_price": m_price, "quantity": m_qty,
                        "buy_date": str(m_date), "stop_loss": m_sl, "notes": m_note,
                    })
                    save_data(data)
                    st.success(f"{t} zum Portfolio hinzugefügt!")
                    st.rerun()

    # ── Export / Import ───────────────────────────────────────────────────────
    with st.expander("💾 Portfolio sichern & wiederherstellen"):
        st.caption("Wichtig wenn du das Tool im Browser nutzt: Daten gehen beim Schließen verloren. Hier sichern!")
        col_ex, col_im = st.columns(2)
        with col_ex:
            st.markdown("**Exportieren (herunterladen)**")
            portfolio_json = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            st.download_button(
                label="📥 Portfolio als Datei speichern",
                data=portfolio_json,
                file_name="mein_portfolio.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_im:
            st.markdown("**Importieren (wiederherstellen)**")
            uploaded = st.file_uploader("📤 Portfolio-Datei laden", type="json", label_visibility="collapsed")
            if uploaded:
                try:
                    imported = json.load(uploaded)
                    if "portfolio" in imported:
                        save_data(imported)
                        st.success("Portfolio wiederhergestellt!")
                        st.rerun()
                except Exception:
                    st.error("Datei konnte nicht gelesen werden.")

    st.subheader("Mein Portfolio")

    if not data["portfolio"]:
        st.info("Noch keine Positionen eingetragen.")
    else:
        total_invested, total_current = 0.0, 0.0

        @st.cache_data(ttl=300, show_spinner=False)
        def get_price(ticker):
            try:
                return yf.Ticker(ticker).fast_info["lastPrice"]
            except Exception:
                return None

        for i, pos in enumerate(data["portfolio"]):
            cur = get_price(pos["ticker"]) or pos["entry_price"]

            invested = pos["entry_price"] * pos["quantity"]
            cur_val  = cur * pos["quantity"]
            pnl      = cur_val - invested
            pnl_pct  = pnl / invested * 100 if invested > 0 else 0
            total_invested += invested
            total_current  += cur_val

            sl       = pos.get("stop_loss", 0)
            at_stop  = bool(sl and cur <= sl * 1.02)
            label    = f"{pos['ticker']} — {pos['name']}"
            if at_stop:
                label += "  🚨 STOP ERREICHT — bitte prüfen!"

            with st.expander(label, expanded=at_stop):
                # P&L Banner
                pnl_color = "#00a844" if pnl >= 0 else "#d32f2f"
                pnl_icon  = "📈" if pnl >= 0 else "📉"
                st.markdown(
                    f'<div style="background:{"#e8fff2" if pnl>=0 else "#fff0f0"};border-radius:10px;'
                    f'padding:12px 18px;border:1px solid {"#00c853" if pnl>=0 else "#f44336"};margin-bottom:12px">'
                    f'<span style="color:{pnl_color};font-size:1.3rem;font-weight:800">'
                    f'{pnl_icon} {fmt_usd(pnl)}  ({fmt_pct(pnl_pct)})</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Einstieg",  fmt_usd(pos["entry_price"]))
                c2.metric("Aktuell",   fmt_usd(cur),
                          delta=fmt_pct((cur - pos["entry_price"]) / pos["entry_price"] * 100))
                c3.metric("Investiert", fmt_usd(invested))
                c4.metric("Stop-Loss",  fmt_usd(sl))

                st.caption(f"Gekauft: {pos['buy_date']}  ·  {pos['quantity']} Aktien")
                if pos.get("notes"):
                    st.caption(f"Notiz: {pos['notes']}")

                c_sl, c_del = st.columns([3, 1])
                with c_sl:
                    new_sl = st.number_input(
                        "Stop-Loss anpassen ($)", min_value=0.01,
                        value=float(sl or cur * 0.90), key=f"sl_{i}", format="%.2f"
                    )
                    if st.button("Stop aktualisieren", key=f"upd_{i}"):
                        data["portfolio"][i]["stop_loss"] = new_sl
                        save_data(data)
                        st.success("Stop-Loss aktualisiert.")
                with c_del:
                    if st.button("Position schließen", key=f"del_{i}"):
                        data["portfolio"].pop(i)
                        save_data(data)
                        st.rerun()

        st.divider()
        total_pnl     = total_current - total_invested
        total_pnl_pct = total_pnl / total_invested * 100 if total_invested > 0 else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Investiert gesamt", fmt_usd(total_invested))
        c2.metric("Aktueller Wert",    fmt_usd(total_current))
        c3.metric("Gesamt P&L",        fmt_usd(total_pnl), delta=fmt_pct(total_pnl_pct))

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 – WATCHLIST
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Meine Watchlist")
    data = load_data()

    # ── Aktie hinzufügen ──────────────────────────────────────────────────────
    c_inp, c_add = st.columns([4, 1])
    new_t = c_inp.text_input("Ticker", placeholder="z.B. Nvidia oder NVDA", label_visibility="collapsed")
    if c_add.button("Hinzufügen", use_container_width=True) and new_t:
        t = resolve_ticker(new_t)
        if t not in data["watchlist"]:
            data["watchlist"].append(t)
            save_data(data)
            st.rerun()

    if not data["watchlist"]:
        st.info("Watchlist ist leer. Füge oben eine Aktie hinzu.")
    else:
        # ── Schnellscan Button ────────────────────────────────────────────────
        qc_cache = st.session_state.get("wl_quick", {})
        c_hint, c_btn = st.columns([3, 1])
        c_hint.caption("Schnellcheck lädt Kursdaten für alle Aktien — dauert ca. 5–10 Sek. Danach 1h gecacht.")
        do_scan = c_btn.button("Schnellcheck starten", type="primary", use_container_width=True)

        if do_scan:
            prog = st.progress(0, text="Scanne …")
            for idx, t in enumerate(data["watchlist"]):
                prog.progress((idx + 1) / len(data["watchlist"]), text=f"Prüfe {t} …")
                qc_cache[t] = quick_check(t)
            prog.empty()
            st.session_state["wl_quick"] = qc_cache

        st.markdown("---")

        # ── Aktien anzeigen — sortiert nach Attraktivität ─────────────────────
        order = {"Sehr interessant": 0, "Beobachten": 1, "Nicht jetzt": 2, None: 3}
        sorted_list = sorted(
            enumerate(data["watchlist"]),
            key=lambda x: order.get((qc_cache.get(x[1]) or {}).get("verdict"), 3)
        )

        for orig_i, t in sorted_list:
            qc = qc_cache.get(t)

            if qc:
                bg  = qc["bg"]
                brd = qc["brd"]
                col = qc["col"]
                verdict = qc["verdict"]
                trend = "↑ Aufwärts" if qc["ema20_above_50"] else "→ Seitwärts"
                macd  = "MACD ▲" if qc["macd_bull"] else "MACD ▼"
                ema_txt = "Über EMA200 ✅" if qc["above_ema200"] else "Unter EMA200 ❌"
                details = f"Kurs: {fmt_usd(qc['price'])}  ·  RSI: {qc['rsi']}  ·  {trend}  ·  {macd}  ·  {ema_txt}  ·  1J: {fmt_pct(qc['perf_1y'])}  ·  Abstand Jahreshoch: {fmt_pct(qc['pct_high'])}"
            else:
                bg, brd, col = "white", "#e5c5f1", "#472d93"
                verdict = "Noch nicht gescannt"
                details = "Klicke 'Schnellcheck starten' für eine Vorschau."

            c_card, c_analyse, c_del = st.columns([6, 1, 1])
            with c_card:
                st.markdown(f"""
                <div style="background:{bg};border:1px solid {brd};border-radius:12px;
                     padding:12px 18px;margin-bottom:6px">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="color:#472d93;font-weight:800;font-size:1rem">{t}</span>
                    <span style="color:{col};font-weight:800;font-size:0.9rem">{verdict}</span>
                  </div>
                  <div style="color:#777;font-size:0.78rem;margin-top:4px">{details}</div>
                </div>""", unsafe_allow_html=True)
            with c_analyse:
                if st.button("Analyse", key=f"wa_{orig_i}", use_container_width=True):
                    with st.spinner(f"Lade {t}…"):
                        r = analyze_stock(t)
                    if r:
                        st.session_state["res"] = r
                        st.success(f"{t} bereit — Analyse-Tab öffnen.")
            with c_del:
                if st.button("✕", key=f"rm_{orig_i}", use_container_width=True):
                    data["watchlist"].pop(orig_i)
                    save_data(data)
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 – ERKLÄRUNGEN
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 – KAUF-SIGNALE SCANNER
    # ═══════════════════════════════════════════════════════════════════════════
    st.subheader("Technische Kauf-Signale — Top 3 aus ~350 US-Aktien")
    st.caption(
        "Rein technische Analyse. Kein Fundamentals. "
        "Das Tool prüft: Aufwärtstrend, MACD, gleitende Durchschnitte, RSI, Flaggen-Muster. "
        "Einmal täglich gecacht — beim ersten Start dauert es 3-5 Minuten."
    )
    st.markdown("---")

    col_scan, col_reset = st.columns([3, 1])
    with col_scan:
        start_scan = st.button("Scanner starten", type="primary", use_container_width=True)
    with col_reset:
        if st.button("Neu laden", use_container_width=True):
            st.cache_data.clear()
            if "scan_done" in st.session_state:
                del st.session_state["scan_done"]
            st.rerun()

    if start_scan:
        st.session_state["scan_done"] = True

    if st.session_state.get("scan_done"):
        with st.spinner("Scanne ~350 US-Aktien auf technische Kaufsignale … (beim ersten Mal 3-5 Min)"):
            picks = scan_top_picks()

        if not picks:
            st.error("Scan fehlgeschlagen. Bitte später nochmal versuchen.")
        else:
            top3 = picks[:3]
            rest = picks[3:10]

            st.markdown(f"**{len(picks)} Aktien mit positivem Signal gefunden — hier die stärksten:**")
            st.markdown("---")

            for rank, p in enumerate(top3, 1):
                prob = p["probability"]
                # Farbe nach Score
                if prob >= 70:
                    bar_col, bg_col, brd_col, medal = "#00c853", "#e8fff2", "#00c853", ["🥇","🥈","🥉"][rank-1]
                elif prob >= 50:
                    bar_col, bg_col, brd_col, medal = "#ff9800", "#fff8e8", "#ff9800", ["🥇","🥈","🥉"][rank-1]
                else:
                    bar_col, bg_col, brd_col, medal = "#888", "#f5f5f5", "#ccc", ["🥇","🥈","🥉"][rank-1]

                with st.container():
                    st.markdown(f"""
                    <div style="background:{bg_col};border:2px solid {brd_col};border-radius:16px;
                                padding:20px 24px;margin-bottom:16px">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <div>
                                <span style="font-size:1.6rem">{medal}</span>
                                <span style="color:#472d93;font-weight:800;font-size:1.3rem;margin-left:8px">{p['ticker']}</span>
                                <span style="color:#888;font-size:0.9rem;margin-left:6px">| ${p['price']:.2f}</span>
                            </div>
                            <div style="text-align:right">
                                <div style="color:{bar_col};font-weight:800;font-size:1.5rem">{prob}%</div>
                                <div style="color:#888;font-size:0.75rem">techn. Wahrscheinlichkeit</div>
                            </div>
                        </div>
                        <div style="background:#e0e0e0;border-radius:8px;height:10px;margin:12px 0">
                            <div style="background:{bar_col};width:{prob}%;height:10px;border-radius:8px"></div>
                        </div>
                        <div style="margin-top:10px">
                            {"".join(f'<div style="color:#2d1f4e;font-size:0.9rem;margin:4px 0">✅ {r}</div>' for r in p['reasons'])}
                        </div>
                        <div style="margin-top:10px;font-size:0.8rem;color:#888">
                            RSI: {p['rsi']} &nbsp;|&nbsp;
                            {'MACD ↑ Frisches Kreuz ' if p['macd_crossed'] else 'MACD positiv ' if p.get('macd_crossed') is False else ''}
                            {'&nbsp;|&nbsp; 🚩 Flagge erkannt' if p['flag'] else ''}
                            {'&nbsp;|&nbsp; ' + str(abs(p['pct_high'])) + '% unter 52W-Hoch' if p['pct_high'] < -5 else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Button zur Vollanalyse
                    if st.button(f"Vollanalyse {p['ticker']}", key=f"scan_btn_{p['ticker']}"):
                        with st.spinner(f"Analysiere {p['ticker']} …"):
                            full = analyze_stock(p["ticker"])
                        if full:
                            st.session_state["res"] = full
                            st.info(f"Vollanalyse geladen. Wechsle zum Tab 🔍 Analyse um sie zu sehen.")

            # Weitere Kandidaten
            if rest:
                st.markdown("---")
                st.markdown("**Weitere Kandidaten auf dem Radar:**")
                cols = st.columns(len(rest))
                for i, p in enumerate(rest):
                    with cols[i]:
                        clr = "#00a844" if p["probability"] >= 60 else "#d97700"
                        st.markdown(f"""
                        <div style="background:white;border:1px solid #e5c5f1;border-radius:10px;
                                    padding:10px;text-align:center">
                            <div style="font-weight:700;color:#472d93">{p['ticker']}</div>
                            <div style="font-weight:800;color:{clr};font-size:1.1rem">{p['probability']}%</div>
                            <div style="font-size:0.75rem;color:#888">${p['price']:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("⚠️ Rein technische Signale — keine Anlageberatung. Hohe Wahrscheinlichkeit bedeutet nicht garantierter Gewinn.")

with tab5:
    st.subheader("Wie funktioniert das alles? Einfach erklärt.")
    st.caption("Hier findest du alles erklärt — so einfach wie möglich.")

    def erklaer(titel, text):
        st.markdown(f"""
        <div style="background:white;border-radius:12px;padding:18px 22px;
             border:1px solid #e5c5f1;box-shadow:0 2px 8px #472d930e;margin-bottom:12px">
            <div style="color:#472d93;font-weight:700;font-size:1rem;margin-bottom:6px">{titel}</div>
            <div style="color:#333;font-size:0.92rem;line-height:1.7">{text}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### Grundbegriffe")

    erklaer("Was ist eine Aktie?",
        "Stell dir vor, ein Unternehmen ist eine große Pizza. Eine Aktie ist ein Stück dieser Pizza. "
        "Wenn das Unternehmen wächst und mehr wert wird, wird auch dein Stück mehr wert. "
        "Du kaufst also ein kleines Stück eines echten Unternehmens — zum Beispiel Apple oder Nike.")

    erklaer("Was ist ein Ticker?",
        "Das ist der kurze Spitzname einer Aktie an der Börse. Apple heißt AAPL, Microsoft heißt MSFT, Nvidia heißt NVDA. "
        "Du kannst hier im Tool beides eingeben — den echten Namen oder den Ticker.")

    erklaer("Was bedeutet KAUFEN / ABWARTEN / FINGER WEG?",
        "<strong style='color:#00a844'>KAUFEN</strong> — Das Tool sieht viele grüne Signale. Das Unternehmen ist stark, "
        "der Preis ist fair oder günstig, der Trend zeigt nach oben. Guter Zeitpunkt.<br><br>"
        "<strong style='color:#d97700'>ABWARTEN</strong> — Nicht schlecht, aber noch nicht perfekt. Vielleicht ist die Aktie "
        "gerade etwas teuer, oder der Trend ist noch nicht klar. Beobachten und warten.<br><br>"
        "<strong style='color:#d32f2f'>FINGER WEG</strong> — Zu viele rote Signale. Das Unternehmen wächst nicht genug, "
        "oder die Aktie ist viel zu teuer, oder der Trend zeigt nach unten.")

    erklaer("Was ist der Score, z.B. 8/10?",
        "Das Tool prüft 10 Dinge — Umsatz, Gewinn, Schulden, fairer Preis, Trend und mehr. "
        "8/10 bedeutet: 8 von 10 Punkten sind grün. Je höher, desto besser. "
        "Ab 8/10 wird KAUFEN angezeigt. Unter 5/10 kommt FINGER WEG.")

    st.markdown("### Zahlen & Kennzahlen")

    erklaer("Was ist der faire Preis?",
        "Jede Aktie hat einen 'echten' Wert — basierend darauf, wie viel Geld das Unternehmen verdient und wie schnell es wächst. "
        "Wenn die Aktie unter diesem fairen Preis liegt, kaufst du günstig ein — wie ein Produkt im Sale. "
        "Das Tool berechnet das automatisch — basierend auf Gewinn, Wachstum und einer Mindestrendite von 15% pro Jahr.")

    erklaer("Was ist die Margin of Safety (MoS)?",
        "Das ist der Rabatt. Zum Beispiel: Fairer Preis ist 100€, die Aktie kostet 80€ — das ist 20% Rabatt (MoS = +20%). "
        "Je höher dieser Wert, desto günstiger kaufst du. Negativ bedeutet: die Aktie ist gerade teurer als sie sein sollte.")

    erklaer("Was ist das KGV (Kurs-Gewinn-Verhältnis)?",
        "Das KGV sagt dir, wie teuer eine Aktie im Verhältnis zu ihrem Gewinn ist. "
        "KGV 20 bedeutet: du zahlst 20€ für jeden 1€ Jahresgewinn des Unternehmens. "
        "Niedrig ist meist besser — aber bei Wachstumsaktien kann ein höheres KGV okay sein.")

    erklaer("Was ist EPS?",
        "EPS steht für Gewinn pro Aktie (Earnings Per Share). "
        "Wenn ein Unternehmen 1 Milliarde Gewinn macht und 100 Millionen Aktien hat, ist EPS = 10€. "
        "Steigendes EPS über die Jahre ist ein sehr gutes Zeichen.")

    erklaer("Was ist ROIC / ROE?",
        "Das misst, wie gut ein Unternehmen mit seinem Geld umgeht. "
        "Stell dir vor, du gibst jemandem 100€ — und er gibt dir am Ende des Jahres 115€ zurück. Das wäre 15% ROE. "
        "Alles über 10% pro Jahr ist gut. Das beste Unternehmen macht das konstant über viele Jahre.")

    erklaer("Was bedeutet Verschuldung ≤3× FCF?",
        "Das zeigt, ob ein Unternehmen zu viele Schulden hat. "
        "FCF ist das Geld, das das Unternehmen wirklich übrig hat — nach allen Ausgaben. "
        "Wenn die Schulden mehr als 3 Jahresgewinne betragen, ist das ein Warnsignal.")

    st.markdown("### Technische Analyse")

    erklaer("Was sind die gleitenden Durchschnitte (EMA 20 / 50 / 200)?",
        "Stell dir vor, du verfolgst die Temperatur jeden Tag. Statt dem heutigen Wert schaust du auf den Durchschnitt "
        "der letzten 20, 50 oder 200 Tage — das glättet kurzfristige Schwankungen.<br><br>"
        "<strong style='color:#FFD700'>EMA 20 (gelb)</strong> — kurzfristiger Trend. Reagiert schnell.<br>"
        "<strong style='color:#00C853'>EMA 50 (grün)</strong> — mittelfristiger Trend. Stabiler.<br>"
        "<strong style='color:#F44336'>EMA 200 (rot)</strong> — langfristiger Trend. Der wichtigste.<br><br>"
        "Wenn der Kurs über allen drei liegt und EMA20 über EMA50 liegt — starkes Kaufsignal.")

    erklaer("Was ist der MACD?",
        "MACD ist wie ein Stimmungsbarometer für die Aktie. Er zeigt, ob der Schwung gerade zunimmt oder abnimmt. "
        "Bullisch bedeutet: der Schwung dreht nach oben — gutes Zeichen. "
        "Bärisch bedeutet: der Schwung dreht nach unten — Vorsicht.")

    erklaer("Was ist die Trendstruktur (Dow-Theorie)?",
        "Ein echter Aufwärtstrend macht immer höhere Hochs und höhere Tiefs. Stell dir eine Treppe vor: jede Stufe ist höher als die vorherige. "
        "Sobald eine Stufe niedriger wird, ist der Trend in Frage gestellt. "
        "Das Tool prüft das automatisch für die letzten 60 Handelstage.")

    erklaer("Was ist Support und Widerstand?",
        "Widerstand (rot) ist ein Preisbereich, an dem die Aktie in der Vergangenheit oft nach unten gedreht hat — wie eine Decke. "
        "Unterstützung (grün) ist ein Bereich, an dem die Aktie oft aufgefangen wurde — wie ein Boden. "
        "Wenn eine Aktie durch den Widerstand bricht, wird dieser oft zur neuen Unterstützung. Das ist ein Kaufsignal.")

    erklaer("Was bedeuten die Kerzenformationen?",
        "<strong>Hammer</strong>: Langer Docht nach unten, kleiner Körper oben — Verkäufer wurden zurückgeschlagen. Bullisches Zeichen.<br>"
        "<strong>Shooting Star</strong>: Langer Docht nach oben, kleiner Körper unten — Käufer konnten nicht halten. Bärisches Zeichen.<br>"
        "<strong>Power Candle</strong>: Sehr große Kerze ohne viele Schatten — starke Bewegung, Käufer oder Verkäufer klar in Führung.<br>"
        "<strong>Bullish Engulfing</strong>: Grüne Kerze schluckt die vorherige rote komplett — starkes Kaufsignal.<br>"
        "<strong>Doji</strong>: Fast kein Körper — der Markt ist unentschlossen, auf die nächste Kerze warten.")

    erklaer("Was ist der Stop-Loss?",
        "Das ist deine Sicherheitsleine. Du sagst vorher: 'Wenn die Aktie auf diesen Preis fällt, verkaufe ich automatisch.' "
        "So begrenzt du deinen Verlust. Beispiel: du kaufst bei 100€, setzt Stop-Loss bei 88€. "
        "Wenn die Aktie auf 88€ fällt, steigst du aus — du verlierst maximal 12%, nicht mehr.<br><br>"
        "Wichtig: Den Stop immer nachziehen wenn die Aktie steigt. So sicherst du Gewinne ab.")

    erklaer("Was bedeutet Stop nachziehen?",
        "Wenn deine Aktie von 100€ auf 130€ steigt, ziehst du den Stop hoch — zum Beispiel auf 118€. "
        "So kannst du nie mehr verlieren als du ursprünglich eingeplant hast, und sicherst trotzdem den Großteil des Gewinns. "
        "Das nennt man Trailing Stop — wie ein Hund an der Leine, der immer ein Stück hinter dir bleibt.")

    st.markdown("### Portfolio & Watchlist")

    erklaer("Was ist das Portfolio?",
        "Das ist deine persönliche Aktiensammlung — alle Aktien die du gerade besitzt. "
        "Das Tool zeigt dir für jede Position: was hast du bezahlt, was ist sie jetzt wert, wie viel Gewinn oder Verlust hast du. "
        "Und es warnt dich wenn eine Aktie deinen Stop-Loss erreicht.")

    erklaer("Was ist die Watchlist?",
        "Das sind Aktien, die dich interessieren — aber die du noch nicht gekauft hast. "
        "Du beobachtest sie, wartest auf den richtigen Moment. "
        "Das Tool zeigt dir mit einem Klick ob das Signal gerade auf Kaufen, Abwarten oder Finger weg steht.")

    erklaer("Was bedeutet P&L?",
        "P&L steht für Profit and Loss — also Gewinn und Verlust. "
        "Grün bedeutet: du bist im Plus. Rot bedeutet: du bist im Minus. "
        "Das Tool berechnet das automatisch mit dem aktuellen Kurs.")

    st.markdown("---")
    st.caption("Dieses Tool ersetzt keine Finanzberatung. Alle Entscheidungen triffst du selbst.")
