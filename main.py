# ============================================================
# ABED FUTURES RADAR V1
# Binance USDⓈ-M Futures + Telegram + News
#
# LONG / SHORT
# Multi-Timeframe
# EMA / RSI / MACD / ATR / VWAP / Volume
# Open Interest / Funding
# BTC Market Filter
# Entry / SL / TP1 / TP2 / TP3
# Signal Score
#
# V1 = ALERT ONLY
# لا يوجد تنفيذ صفقات حقيقية
# ============================================================

import os
import json
import time
import math
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# اختياري - أخبار CoinGecko
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

# كل دورة
SCAN_SECONDS = 30

# الحد الأدنى لقوة الإشارة
MIN_SCORE = 82

# لا نريد عددًا ضخمًا من العملات
MAX_SYMBOLS = 80

# الحد الأدنى للسيولة اليومية
MIN_QUOTE_VOLUME = 5_000_000

# منع تكرار نفس الإشارة
SIGNAL_COOLDOWN = 60 * 30

# ملف سجل الصفقات
SIGNAL_LOG_FILE = "signals.json"

# ============================================================
# BINANCE FUTURES
# ============================================================

BINANCE_FAPI = "https://fapi.binance.com"

# ============================================================
# EXCLUDED
# ============================================================

EXCLUDED = {
    "USDCUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
}

# ============================================================
# MEMORY
# ============================================================

last_signals = {}

# ============================================================
# HTTP
# ============================================================

def http_get(url, headers=None, timeout=15):

    if headers is None:
        headers = {}

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ABED-FUTURES-RADAR/1.0",
            **headers
        }
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")

    return json.loads(raw)


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(text):

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are missing.")
        return False

    url = (
        "https://api.telegram.org/bot"
        + TELEGRAM_BOT_TOKEN
        + "/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        }
    )

    try:

        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()

        return True

    except Exception as e:

        print("Telegram error:", e)

        return False


# ============================================================
# FILE LOG
# ============================================================

def load_signal_log():

    if not os.path.exists(SIGNAL_LOG_FILE):
        return []

    try:

        with open(
            SIGNAL_LOG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return []


def save_signal(signal):

    logs = load_signal_log()

    logs.append(signal)

    # نحتفظ بآخر 5000 إشارة
    logs = logs[-5000:]

    with open(
        SIGNAL_LOG_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            logs,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# BINANCE EXCHANGE INFO
# ============================================================

def get_futures_symbols():

    url = BINANCE_FAPI + "/fapi/v1/exchangeInfo"

    data = http_get(url)

    symbols = []

    for s in data.get("symbols", []):

        symbol = s.get("symbol")

        if not symbol:
            continue

        if not symbol.endswith("USDT"):
            continue

        if symbol in EXCLUDED:
            continue

        if s.get("status") != "TRADING":
            continue

        if s.get("contractType") != "PERPETUAL":
            continue

        symbols.append(symbol)

    return symbols


# ============================================================
# 24H TICKERS
# ============================================================

def get_24h_tickers():

    url = BINANCE_FAPI + "/fapi/v1/ticker/24hr"

    return http_get(url)


# ============================================================
# SELECT LIQUID COINS
# ============================================================

def select_symbols():

    try:

        tickers = get_24h_tickers()

        candidates = []

        for t in tickers:

            symbol = t.get("symbol", "")

            if not symbol.endswith("USDT"):
                continue

            if symbol in EXCLUDED:
                continue

            try:

                volume = float(
                    t.get("quoteVolume", 0)
                )

                price_change = float(
                    t.get("priceChangePercent", 0)
                )

            except Exception:

                continue

            if volume < MIN_QUOTE_VOLUME:
                continue

            candidates.append(
                {
                    "symbol": symbol,
                    "volume": volume,
                    "change": price_change,
                }
            )

        # ترتيب السيولة
        candidates.sort(
            key=lambda x: x["volume"],
            reverse=True
        )

        return [
            x["symbol"]
            for x in candidates[:MAX_SYMBOLS]
        ]

    except Exception as e:

        print("Symbol scanner error:", e)

        return []


# ============================================================
# KLINES
# ============================================================

def get_klines(symbol, interval, limit=250):

    params = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
    )

    url = (
        BINANCE_FAPI
        + "/fapi/v1/klines?"
        + params
    )

    return http_get(url)


# ============================================================
# FLOAT DATA
# ============================================================

def candle_data(klines):

    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    for k in klines:

        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))

    return (
        opens,
        highs,
        lows,
        closes,
        volumes
    )


# ============================================================
# EMA
# ============================================================

def ema(values, period):

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    result = sum(
        values[:period]
    ) / period

    for price in values[period:]:

        result = (
            (price - result)
            * multiplier
            + result
        )

    return result


# ============================================================
# RSI
# ============================================================

def rsi(values, period=14):

    if len(values) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(values)):

        change = values[i] - values[i - 1]

        gains.append(
            max(change, 0)
        )

        losses.append(
            max(-change, 0)
        )

    avg_gain = (
        sum(gains[:period]) / period
    )

    avg_loss = (
        sum(losses[:period]) / period
    )

    for i in range(period, len(gains)):

        avg_gain = (
            (avg_gain * (period - 1))
            + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1))
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (
        100 / (1 + rs)
    )


# ============================================================
# ATR
# ============================================================

def atr(highs, lows, closes, period=14):

    if len(closes) <= period:
        return None

    trs = []

    for i in range(1, len(closes)):

        tr = max(
            highs[i] - lows[i],
            abs(
                highs[i]
                - closes[i - 1]
            ),
            abs(
                lows[i]
                - closes[i - 1]
            )
        )

        trs.append(tr)

    return (
        sum(trs[-period:])
        / period
    )


# ============================================================
# MACD
# ============================================================

def macd(values):

    if len(values) < 35:
        return None, None

    fast = []
    slow = []

    for i in range(len(values)):

        fast.append(
            ema(
                values[:i + 1],
                12
            )
        )

        slow.append(
            ema(
                values[:i + 1],
                26
            )
        )

    macd_values = []

    for f, s in zip(fast, slow):

        if f is not None and s is not None:
            macd_values.append(f - s)

    if len(macd_values) < 9:
        return None, None

    signal = ema(
        macd_values,
        9
    )

    return macd_values[-1], signal


# ============================================================
# VWAP
# ============================================================

def vwap(klines):

    total_volume = 0
    total_value = 0

    for k in klines:

        high = float(k[2])
        low = float(k[3])
        close = float(k[4])
        volume = float(k[5])

        typical_price = (
            high + low + close
        ) / 3

        total_value += (
            typical_price * volume
        )

        total_volume += volume

    if total_volume == 0:
        return None

    return (
        total_value
        / total_volume
    )


# ============================================================
# VOLUME SPIKE
# ============================================================

def volume_spike(volumes, period=20):

    if len(volumes) < period + 1:
        return 1.0

    current = volumes[-1]

    average = (
        sum(volumes[-period-1:-1])
        / period
    )

    if average <= 0:
        return 1.0

    return current / average


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def support_resistance(
    highs,
    lows,
    lookback=50
):

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    resistance = max(recent_highs)
    support = min(recent_lows)

    return support, resistance


# ============================================================
# FUNDING
# ============================================================

def get_funding(symbol):

    try:

        params = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "limit": 1
            }
        )

        url = (
            BINANCE_FAPI
            + "/fapi/v1/fundingRate?"
            + params
        )

        data = http_get(url)

        if not data:
            return 0.0

        return float(
            data[-1]["fundingRate"]
        )

    except Exception:

        return 0.0


# ============================================================
# OPEN INTEREST
# ============================================================

def get_open_interest(symbol):

    try:

        params = urllib.parse.urlencode(
            {
                "symbol": symbol
            }
        )

        url = (
            BINANCE_FAPI
            + "/fapi/v1/openInterest?"
            + params
        )

        data = http_get(url)

        return float(
            data.get("openInterest", 0)
        )

    except Exception:

        return 0.0


# ============================================================
# BTC MARKET FILTER
# ============================================================

def get_btc_context():

    try:

        klines = get_klines(
            "BTCUSDT",
            "1h",
            220
        )

        (
            o,
            h,
            l,
            c,
            v
        ) = candle_data(klines)

        current = c[-1]

        e50 = ema(c, 50)
        e200 = ema(c, 200)

        if not e50 or not e200:
            return "UNKNOWN"

        if (
            current > e50
            and e50 > e200
        ):
            return "BULLISH"

        if (
            current < e50
            and e50 < e200
        ):
            return "BEARISH"

        return "NEUTRAL"

    except Exception:

        return "UNKNOWN"


# ============================================================
# ANALYZE TIMEFRAME
# ============================================================

def analyze_timeframe(
    symbol,
    interval
):

    klines = get_klines(
        symbol,
        interval,
        220
    )

    if len(klines) < 100:
        return None

    (
        opens,
        highs,
        lows,
        closes,
        volumes
    ) = candle_data(klines)

    price = closes[-1]

    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)

    rsi_value = rsi(closes)

    atr_value = atr(
        highs,
        lows,
        closes
    )

    macd_value, macd_signal = macd(
        closes
    )

    current_vwap = vwap(
        klines[-100:]
    )

    v_spike = volume_spike(
        volumes
    )

    support, resistance = (
        support_resistance(
            highs,
            lows
        )
    )

    bullish = 0
    bearish = 0

    # ----------------------------
    # EMA
    # ----------------------------

    if e20 and e50 and e200:

        if (
            price > e20
            and e20 > e50
            and e50 > e200
        ):
            bullish += 15

        if (
            price < e20
            and e20 < e50
            and e50 < e200
        ):
            bearish += 15

    # ----------------------------
    # RSI
    # ----------------------------

    if rsi_value is not None:

        if 50 < rsi_value < 70:
            bullish += 10

        elif 30 < rsi_value < 50:
            bearish += 10

    # ----------------------------
    # MACD
    # ----------------------------

    if (
        macd_value is not None
        and macd_signal is not None
    ):

        if macd_value > macd_signal:
            bullish += 10

        elif macd_value < macd_signal:
            bearish += 10

    # ----------------------------
    # VWAP
    # ----------------------------

    if current_vwap:

        if price > current_vwap:
            bullish += 10

        elif price < current_vwap:
            bearish += 10

    # ----------------------------
    # VOLUME
    # ----------------------------

    if v_spike >= 1.5:

        if price > opens[-1]:
            bullish += 10

        elif price < opens[-1]:
            bearish += 10

    # ----------------------------
    # STRUCTURE
    # ----------------------------

    previous_high = max(
        highs[-10:-1]
    )

    previous_low = min(
        lows[-10:-1]
    )

    if price > previous_high:
        bullish += 10

    if price < previous_low:
        bearish += 10

    # ----------------------------

    return {
        "price": price,
        "ema20": e20,
        "ema50": e50,
        "ema200": e200,
        "rsi": rsi_value,
        "atr": atr_value,
        "macd": macd_value,
        "macd_signal": macd_signal,
        "vwap": current_vwap,
        "volume_spike": v_spike,
        "support": support,
        "resistance": resistance,
        "bullish": bullish,
        "bearish": bearish,
    }


# ============================================================
# SIGNAL ENGINE
# ============================================================

def build_signal(symbol):

    try:

        tf4h = analyze_timeframe(
            symbol,
            "4h"
        )

        tf1h = analyze_timeframe(
            symbol,
            "1h"
        )

        tf15 = analyze_timeframe(
            symbol,
            "15m"
        )

        tf5 = analyze_timeframe(
            symbol,
            "5m"
        )

        if not all(
            [tf4h, tf1h, tf15, tf5]
        ):
            return None

        funding = get_funding(symbol)

        oi = get_open_interest(symbol)

        btc_context = get_btc_context()

        long_score = 0
        short_score = 0

        # ====================================================
        # 4H
        # ====================================================

        if tf4h["bullish"] >= 25:
            long_score += 20

        if tf4h["bearish"] >= 25:
            short_score += 20

        # ====================================================
        # 1H
        # ====================================================

        if tf1h["bullish"] >= 25:
            long_score += 15

        if tf1h["bearish"] >= 25:
            short_score += 15

        # ====================================================
        # 15M
        # ====================================================

        if tf15["bullish"] >= 25:
            long_score += 15

        if tf15["bearish"] >= 25:
            short_score += 15

        # ====================================================
        # 5M ENTRY
        # ====================================================

        if tf5["bullish"] >= 25:
            long_score += 15

        if tf5["bearish"] >= 25:
            short_score += 15

        # ====================================================
        # BTC FILTER
        # ====================================================

        if btc_context == "BULLISH":

            long_score += 10
            short_score -= 10

        elif btc_context == "BEARISH":

            short_score += 10
            long_score -= 10

        # ====================================================
        # FUNDING
        # ====================================================

        # Funding موجب جدًا =
        # ازدحام نسبي في الـ Long
        if funding > 0.0005:

            short_score += 5

        # Funding سالب جدًا =
        # ازدحام نسبي في الـ Short
        elif funding < -0.0005:

            long_score += 5

        # ====================================================
        # VOLUME
        # ====================================================

        if tf5["volume_spike"] >= 1.5:

            if tf5["price"] > tf5["vwap"]:
                long_score += 5

            elif tf5["price"] < tf5["vwap"]:
                short_score += 5

        # ====================================================
        # FINAL
        # ====================================================

        direction = None
        score = 0

        if (
            long_score >= MIN_SCORE
            and long_score > short_score + 8
        ):

            direction = "LONG"
            score = min(
                long_score,
                100
            )

        elif (
            short_score >= MIN_SCORE
            and short_score > long_score + 8
        ):

            direction = "SHORT"
            score = min(
                short_score,
                100
            )

else:
