# ============================================================
# ABED FUTURES RADAR - V2 (بوت حكيم)
# Binance USD-M Futures
# LONG + SHORT | Multi Time Frame (4H, 1H, 15M, 5M)
# EMA + RSI + MACD + ATR + VWAP + Volume + S/R
# Funding Rate + Open Interest + BTC Market Filter
# Entry + SL + TP1 + TP2 + TP3 + Signal Score + Telegram Alerts
# ============================================================

from datetime import datetime, timezone
import json
import time
import urllib.request
import urllib.parse
import os

# ============================================================
# 1) إعدادات التلجرام
# ============================================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8493446835")

# ============================================================
# 2) إعدادات الرادار
# ============================================================

# الفاصل الزمني بين كل دورة فحص بالثواني
SCAN_SECONDS = 30

# الحد الأدنى لقوة الإشارة لإرسال التنبيه (من 100)
MIN_SCORE = 78

# عدد العملات الأكثر سيولة التي يتم فحصها
MAX_SYMBOLS = 70

# الحد الأدنى لحجم التداول في 24 ساعة (بالدولار)
MIN_QUOTE_VOLUME = 5_000_000

# فترة الانتظار قبل تكرار نفس العملة (1800 ثانية = 30 دقيقة)
SIGNAL_COOLDOWN = 1800

# ============================================================
# 3) منصة بينانس
# ============================================================

BINANCE = "https://fapi.binance.com"

# استبعاد العملات المستقرة
EXCLUDED = {
    "USDCUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
}

last_signal_time = {}

# ============================================================
# 4) طلبات HTTP
# ============================================================

def get_json(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ABED-RADAR/2.0"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ============================================================
# 5) إرسال تنبيهات التلجرام
# ============================================================

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ يرجى التأكد من ضبط BOT_TOKEN و CHAT_ID")
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
        print("✅ Telegram: تم إرسال الرسالة بنجاح")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False


# ============================================================
# 6) جلب قائمة العملات النشطة
# ============================================================

def get_tickers():
    return get_json(BINANCE + "/fapi/v1/ticker/24hr")


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

        # ترتيب حسب أعلى سيولة
        result.sort(key=lambda x: x["volume"], reverse=True)
        return [x["symbol"] for x in result[:MAX_SYMBOLS]]

    except Exception as e:
        print(f"Symbol Error: {e}")
        return []


# ============================================================
# 7) جلب بيانات الشموع (Klines)
# ============================================================

def get_klines(symbol, interval, limit=220):
    params = urllib.parse.urlencode({
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    })
    url = f"{BINANCE}/fapi/v1/klines?{params}"
    return get_json(url)


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
# 8) المؤشرات الفنية (EMA, RSI, ATR, MACD, VWAP)
# ============================================================

def EMA(values, period):
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result


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


def volume_spike(volumes, period=20):
    if len(volumes) < period + 1:
        return 1
    average = sum(volumes[-period - 1:-1]) / period
    if average <= 0:
        return 1
    return volumes[-1] / average


def support_resistance(highs, lows, lookback=60):
    support = min(lows[-lookback:])
    resistance = max(highs[-lookback:])
    return support, resistance


# ============================================================
# 9) معدل التمويل والعقود المفتوحة
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


def get_open_interest(symbol):
    try:
        params = urllib.parse.urlencode({"symbol": symbol})
        url = f"{BINANCE}/fapi/v1/openInterest?{params}"
        data = get_json(url)
        return float(data.get("openInterest", 0))
    except Exception:
        return 0


# ============================================================
# 10) فحص اتجاه البيتكوين العام
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
# 11) تحليل فريم زمني واحد
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

        # اتجاه EMA
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

        # Volume Spike
        if vol_spike >= 1.4:
            if price > opens[-1]:
                bullish += 10
            elif price < opens[-1]:
                bearish += 10

        # Breakout / Breakdown
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
    except Exception:
        return None


# ============================================================
# 12) بناء وحساب قوة الإشارة (Multi-Timeframe)
# ============================================================

def build_signal(symbol):
    try:
        # فحص الفريمات المتعددة
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

        # اتجاه 4H
        if tf4h["bullish"] >= 25:
            long_score += 20
        if tf4h["bearish"] >= 25:
            short_score += 20

        # فريم 1H
        if tf1h["bullish"] >= 25:
            long_score += 15
        if tf1h["bearish"] >= 25:
            short_score += 15

        # فريم 15M
        if tf15["bullish"] >= 25:
            long_score += 15
        if tf15["bearish"] >= 25:
            short_score += 15

        # فريم 5M
        if tf5["bullish"] >= 25:
            long_score += 15
        if tf5["bearish"] >= 25:
            short_score += 15

        # تأثير اتجاه البيتكوين
        if btc == "BULLISH":
            long_score += 10
            short_score -= 10
        elif btc == "BEARISH":
            short_score += 10
            long_score -= 10

        # معدل التمويل Funding Rate
        if funding > 0.0005:
            short_score += 5
        elif funding < -0.0005:
            long_score += 5

        # فوليوم فريم 5M مع VWAP
        if tf5["volume_spike"] >= 1.5:
            if tf5["price"] > tf5["vwap"]:
                long_score += 5
            elif tf5["price"] < tf5["vwap"]:
                short_score += 5

        # اختيار اتجاه الصفقة
        if long_score >= MIN_SCORE and long_score > short_score + 10:
            direction = "LONG"
            score = min(long_score, 100)
        elif short_score >= MIN_SCORE and short_score > long_score + 10:
            direction = "SHORT"
            score = min(short_score, 100)
        else:
            return None

        # حساب مستويات الدخول والوقف والأهداف بناءً على ATR والدعم/المقاومة
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
# 13) صياغة التنبيه باللغة العربية وتنسيق HTML
# ============================================================

def format_alert(signal):
    dir_emoji = "🟢 LONG (شراء)" if signal["direction"] == "LONG" else "🔴 SHORT (بيع)"
    text = (
        f"🚨 <b>إشارة تداول جديدة | رادار حكيم</b> 🚨\n\n"
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
        f"⏰ <b>التوقيت:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    return text


# ============================================================
# 14) دورة الفحص الرئيسية
# ============================================================

def scan_once():
    symbols = get_symbols()
    print(f"🔍 فحص {len(symbols)} عملة في سوق العقود الآجلة...")

    for symbol in symbols:
        now = time.time()
        # منع تكرار نفس العملة خلال مدة التبريد
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
    print("🚀 بدء تشغيل بوت حكيم - Abed Futures Radar V2...")
    
    # إرسال رسالة ترحيبية وتأكيد فور تشغيل الكود
    send_telegram(
        "🟢 <b>تم تشغيل رادار حكيم للعقود الآجلة بنجاح!</b>\n\n"
        "📡 <i>جاري فحص وتتبع إشارات السوق عبر منصة بينانس...</i>"
    )
    
    while True:
        try:
            scan_once()
        except Exception as e:
            print(f"حدث خطأ أثناء الفحص: {e}")
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run_radar()
        
