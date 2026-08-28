# ============================================================
# ABED FUTURES RADAR - V2
# Binance USD-M Futures
# LONG + SHORT
# Multi Time Frame
# EMA + RSI + MACD + ATR + VWAP
# Volume + Support/Resistance
# Funding Rate + Open Interest
# BTC Market Filter
# Entry + SL + TP1 + TP2 + TP3
# Signal Score
# Telegram Alerts
#
# ALERT ONLY - NO REAL TRADING
# ============================================================

from datetime import datetime, timezone
import json
import time
import urllib.request
import urllib.parse
import os

# ============================================================
# 1) TELEGRAM
# ============================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PUT_NEW_BOT_TOKEN_HERE")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PUT_CHAT_ID_HERE")

# ============================================================
# 2) SETTINGS
# ============================================================

SCAN_SECONDS = 30

# لا ترسل إشارة إلا إذا وصلت لهذه الدرجة
MIN_SCORE = 82

# عدد العملات التي يتم فحصها
MAX_SYMBOLS = 70

# أقل حجم تداول 24 ساعة
MIN_QUOTE_VOLUME = 5_000_000

# منع تكرار نفس العملة ونفس الاتجاه (بالثواني)
SIGNAL_COOLDOWN = 1800

# ============================================================
# 3) BINANCE FUTURES
# ============================================================

BINANCE = "https://fapi.binance.com"

EXCLUDED = {
    "USDCUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
}

last_signal_time = {}

# ============================================================
# 4) HTTP
# ============================================================

def get_json(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ABED-FUTURES-RADAR/2.0"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ============================================================
# 5) TELEGRAM
# ============================================================

def send_telegram(text):
    if (
        not BOT_TOKEN
        or BOT_TOKEN == "PUT_NEW_BOT_TOKEN_HERE"
        or not CHAT_ID
        or CHAT_ID == "PUT_CHAT_ID_HERE"
    ):
        print("⚠️ يرجى ضبط BOT_TOKEN و CHAT_ID في Secrets أو كمتغيرات بيئة")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
        print("✅ Telegram: Delivered")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False


# ============================================================
# 6) BINANCE TICKERS
# ============================================================

def get_tickers():
    return get_json(BINANCE + "/fapi/v1/ticker/24hr")


# ============================================================
# 7) SELECT LIQUID SYMBOLS
# ============================================================

def get_symbols():
    try:
        tickers = get_tickers()
        result = []

        for t in tickers:
            symbol = t.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue
            if symbol in EXCLUDED:
                continue

            try:
                volume = float(t.get("quoteVolume", 0))
                change = float(t.get("priceChangePercent", 0))
            except Exception:
                continue

            if volume < MIN_QUOTE_VOLUME:
                continue

            result.append({
                "symbol": symbol,
                "volume": volume,
                "change": change
            })

        # ترتيب حسب السيولة
        result.sort(key=lambda x: x["volume"], reverse=True)
        return [x["symbol"] for x in result[:MAX_SYMBOLS]]

    except Exception as e:
        print(f"Symbol Error: {e}")
        return []


# ============================================================
# 8) KLINES
# ============================================================

def get_klines(symbol, interval, limit=220):
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    })
    url = f"{BINANCE}/fapi/v1/klines?{params}"
    return get_json(url)


# ============================================================
# 9) CANDLE DATA
# ============================================================

def parse_klines(klines):
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in klines:
        opens.append(float(k))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return opens, highs, lows, closes, volumes


# ============================================================
# 10) EMA
# ============================================================

def EMA(values, period):
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result


# ============================================================
# 11) RSI
# ============================================================

def RSI(values, period=14):
    if len(values) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ============================================================
# 12) ATR
# ============================================================

def ATR(highs, lows, closes, period=14):
    if len(closes) <= period:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


# ============================================================
# 13) MACD
# ============================================================

def MACD(values):
    if len(values) < 50:
        return None, None

    macd_values = []
    for i in range(len(values)):
        e12 = EMA(values[:i + 1], 12)
        e26 = EMA(values[:i + 1], 26)
        if e12 is not None and e26 is not None:
            macd_values.append(e12 - e26)

    if len(macd_values) < 9:
        return None, None

    signal = EMA(macd_values, 9)
    if signal is None:
        return None, None

    return macd_values[-1], signal


# ============================================================
# 14) VWAP
# ============================================================

def VWAP(klines):
    total_volume = 0
    total_value = 0
    for k in klines:
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])
        volume = float(k[5])
        typical = (high + low + close) / 3
        total_value += (typical * volume)
        total_volume += volume

    if total_volume == 0:
        return None
    return total_value / total_volume


# ============================================================
# 15) VOLUME SPIKE
# ============================================================

def volume_spike(volumes, period=20):
    if len(volumes) < period + 1:
        return 1
    average = sum(volumes[-period - 1:-1]) / period
    if average <= 0:
        return 1
    return volumes[-1] / average


# ============================================================
# 16) SUPPORT / RESISTANCE
# ============================================================

def support_resistance(highs, lows, lookback=60):
    support = min(lows[-lookback:])
    resistance = max(highs[-lookback:])
    return support, resistance


# ============================================================
# 17) FUNDING RATE
# ============================================================

def get_funding(symbol):
    try:
        params = urllib.parse.urlencode({"symbol": symbol, "limit": 1})
        url = f"{BINANCE}/fapi/v1/fundingRate?{params}"
        data = get_json(url)
        if not data:
            return 0
        return float(data[-1]["fundingRate"])
    except Exception:
        return 0


# ============================================================
# 18) OPEN INTEREST
# ============================================================

def get_open_interest(symbol):
    try:
        params = urllib.parse.urlencode({"symbol": symbol})
        url = f"{BINANCE}/fapi/v1/openInterest?{params}"
        data = get_json(url)
        return float(data.get("openInterest", 0))
    except Exception:
        return 0


# ============================================================
# 19) BTC MARKET REGIME
# ============================================================

def btc_regime():
    try:
        klines = get_klines("BTCUSDT", "1h", 220)
        _, _, _, c, _ = parse_klines(klines)
        price = c[-1]
        e50 = EMA(c, 50)
        e200 = EMA(c, 200)

        if not e50 or not e200:
            return "UNKNOWN"

        if price > e50 and e50 > e200:
            return "BULLISH"
        if price < e50 and e50 < e200:
            return "BEARISH"
        return "SIDEWAYS"
    except Exception:
        return "UNKNOWN"


# ============================================================
# 20) ANALYZE ONE TIMEFRAME
# ============================================================

def analyze(symbol, interval):
    try:
        klines = get_klines(symbol, interval, 220)
        if not klines or len(klines) < 100:
            return None

        opens, highs, lows, closes, volumes = parse_klines(klines)
        price = closes[-1]

        e20 = EMA(closes, 20)
        e50 = EMA(closes, 50)
        e200 = EMA(closes, 200)

        rsi = RSI(closes)
        atr = ATR(highs, lows, closes)
        macd, macd_signal = MACD(closes)
        vwap = VWAP(klines[-100:])
        vol_spike = volume_spike(volumes)
        support, resistance = support_resistance(highs, lows)

        bullish = 0
        bearish = 0

        # EMA TREND
        if e20 and e50 and e200:
            if price > e20 and e20 > e50 and e50 > e200:
                bullish += 20
            elif price < e20 and e20 < e50 and e50 < e200:
                bearish += 20

        # RSI
        if rsi is not None:
            if 52 <= rsi <= 68:
                bullish += 10
            elif 32 <= rsi <= 48:
                bearish += 10

        # MACD
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                bullish += 10
            elif macd < macd_signal:
                bearish += 10

        # VWAP
        if vwap:
            if price > vwap:
                bullish += 10
            elif price < vwap:
                bearish += 10

        # VOLUME
        if vol_spike >= 1.4:
            if price > opens[-1]:
                bullish += 10
            elif price < opens[-1]:
                bearish += 10

        # BREAKOUT / BREAKDOWN
        previous_high = max(highs[-11:-1])
        previous_low = min(lows[-11:-1])

        if price > previous_high:
            bullish += 15
        if price < previous_low:
            bearish += 15

        return {
            "price": price,
            "ema20": e20,
            "ema50": e50,
            "ema200": e200,
            "rsi": rsi,
            "atr": atr,
            "macd": macd,
            "macd_signal": macd_signal,
            "vwap": vwap,
            "volume_spike": vol_spike,
            "support": support,
            "resistance": resistance,
            "bullish": bullish,
            "bearish": bearish
        }
    except Exception as e:
        return None


# ============================================================
# 21) BUILD SIGNAL
# ============================================================

def build_signal(symbol):
    try:
        # Multi Time Frame
        tf4h = analyze(symbol, "4h")
        tf1h = analyze(symbol, "1h")
        tf15 = analyze(symbol, "15m")
        tf5 = analyze(symbol, "5m")

        if not all([tf4h, tf1h, tf15, tf5]):
            return None

        funding = get_funding(symbol)
        oi = get_open_interest(symbol)
        btc = btc_regime()

        long_score = 0
        short_score = 0

        # 4H TREND
        if tf4h["bullish"] >= 25:
            long_score += 20
        if tf4h["bearish"] >= 25:
            short_score += 20

        # 1H
        if tf1h["bullish"] >= 25:
            long_score += 15
        if tf1h["bearish"] >= 25:
            short_score += 15

        # 15M
        if tf15["bullish"] >= 25:
            long_score += 15
        if tf15["bearish"] >= 25:
            short_score += 15

        # 5M
        if tf5["bullish"] >= 25:
            long_score += 15
        if tf5["bearish"] >= 25:
            short_score += 15

        # BTC FILTER
        if btc == "BULLISH":
            long_score += 10
            short_score -= 10
        elif btc == "BEARISH":
            short_score += 10
            long_score -= 10

        # FUNDING
        if funding > 0.0005:
            short_score += 5
        elif funding < -0.0005:
            long_score += 5

        # VOLUME
        if tf5["volume_spike"] >= 1.5:
            if tf5["price"] > tf5["vwap"]:
                long_score += 5
            elif tf5["price"] < tf5["vwap"]:
                short_score += 5

        # SELECT DIRECTION
        if long_score >= MIN_SCORE and long_score > short_score + 10:
            direction = "LONG"
            score = min(long_score, 100)
        elif short_score >= MIN_SCORE and short_score > long_score + 10:
            direction = "SHORT"
            score = min(short_score, 100)
        else:
            return None

        # ENTRY / SL / TP
        price = tf5["price"]
        atr = tf5["atr"]

        if not atr or atr <= 0:
            return None

        support = tf15["support"]
        resistance = tf15["resistance"]

        if direction == "LONG":
            entry_low = price - (atr * 0.20)
            entry_high = price + (atr * 0.10)
            sl = min(support - (atr * 0.15), price - (atr * 1.5))
            risk = price - sl
            if risk <= 0:
                risk = atr * 1.5
                sl = price - risk
            tp1 = price + (risk * 1.0)
            tp2 = price + (risk * 2.0)
            tp3 = price + (risk * 3.0)
        else:
            entry_low = price - (atr * 0.10)
            entry_high = price + (atr * 0.20)
            sl = max(resistance + (atr * 0.15), price + (atr * 1.5))
            risk = sl - price
            if risk <= 0:
                risk = atr * 1.5
                sl = price + risk
            tp1 = price - (risk * 1.0)
            tp2 = price - (risk * 2.0)
            tp3 = price - (risk * 3.0)

        return {
            "symbol": symbol,
            "direction": direction,
            "score": score,
            "price": price,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "btc": btc,
            "funding": funding,
            "oi": oi
        }
    except Exception as e:
        print(f"Error building signal for {symbol}: {e}")
        return None


# ============================================================
# 22) FORMAT & SEND ALERT
# ============================================================

def format_alert(signal):
    dir_emoji = "🟢 LONG" if signal["direction"] == "LONG" else "🔴 SHORT"
    text = (
        f"🚨 <b>ABED FUTURES RADAR V2</b> 🚨\n\n"
        f"🪙 <b>العملة:</b> #{signal['symbol']}\n"
        f"📊 <b>الاتجاه:</b> {dir_emoji}\n"
        f"⭐ <b>قوة الإشارة:</b> {signal['score']}/100\n"
        f"💵 <b>السعر الحالي:</b> <code>{signal['price']:.4f}</code>\n\n"
        f"🎯 <b>منطقة الدخول:</b> <code>{signal['entry_low']:.4f}</code> - <code>{signal['entry_high']:.4f}</code>\n"
        f"🛑 <b>وقف الخسارة (SL):</b> <code>{signal['sl']:.4f}</code>\n"
        f"🎯 <b>الهدف الأول (TP1):</b> <code>{signal['tp1']:.4f}</code>\n"
        f"🎯 <b>الهدف الثاني (TP2):</b> <code>{signal['tp2']:.4f}</code>\n"
        f"🎯 <b>الهدف الثالث (TP3):</b> <code>{signal['tp3']:.4f}</code>\n\n"
        f"🌐 <b>حالة البيتكوين:</b> {signal['btc']}\n"
        f"📈 <b>Funding Rate:</b> {signal['funding']:.5%}\n"
        f"⏰ <b>الوقت:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    return text


# ============================================================
# 23) MAIN SCAN LOOP
# ============================================================

def scan_once():
    symbols = get_symbols()
    print(f"🔍 فحص {len(symbols)} عملة نشطة...")

    for symbol in symbols:
        now = time.time()
        # Cooldown check
        if symbol in last_signal_time:
            if now - last_signal_time[symbol] < SIGNAL_COOLDOWN:
                continue

        signal = build_signal(symbol)
        if signal:
            msg = format_alert(signal)
            print(f"🔥 إشارة مكتشفة: {symbol} - {signal['direction']} ({signal['score']} pts)")
            send_telegram(msg)
            last_signal_time[symbol] = now


def run_radar():
    print("🚀 بدء تشغيل Abed Futures Radar V2...")
    while True:
        try:
            scan_once()
        except Exception as e:
            print(f"Error in scan cycle: {e}")
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run_radar()
            
