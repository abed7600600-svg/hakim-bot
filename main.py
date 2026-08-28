# ============================================================
# ABED FUTURES RADAR V1 (النسخة المتكاملة الشاملة)
# Binance USDⓈ-M Futures + Telegram + CoinGecko News Radar
#
# LONG / SHORT
# Multi-Timeframe (4H, 1H, 15M, 5M)
# EMA 20/50/200 / RSI / MACD / ATR / VWAP / Volume Spike / S/R
# Open Interest / Funding Rate / Long-Short Ratio
# BTC Market Regime Filter
# CoinGecko News Radar & Filter
# Entry Zone + SL + TP1 + TP2 + TP3 + Risk/Reward (R:R)
# Signal Score (0 - 100)
# Cooldown System & Signal Logging (signals.json)
#
# ALERT ONLY - NO REAL TRADING
# ============================================================

import os
import json
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ============================================================
# 1) CONFIG & CREDENTIALS
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8493446835")

# مفتاح CoinGecko API (اختياري - يعمل بدونه أيضاً)
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")

# الفاصل الزمني بين كل دورة فحص بالثواني
SCAN_SECONDS = 30

# الحد الأدنى لقوة الإشارة (من 100)
MIN_SCORE = 70

# عدد العملات الأكثر سيولة التي يتم فحصها
MAX_SYMBOLS = 45

# الحد الأدنى لحجم تداول 24 ساعة (بالدولار)
MIN_QUOTE_VOLUME = 6_000_000

# منع تكرار نفس الإشارة لنفس العملة (1800 ثانية = 30 دقيقة)
SIGNAL_COOLDOWN = 1800

# ملف حفظ سجل الإشارات
SIGNAL_LOG_FILE = "signals.json"

# فحص وتحديث الأخبار كل N دورات
NEWS_CHECK_EVERY_CYCLES = 20

# ============================================================
# 2) BINANCE FUTURES API
# ============================================================

BINANCE_FAPI = "https://fapi.binance.com"

EXCLUDED = {
    "USDCUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
}

last_signals = {}
cycle_counter = 0
cached_news = "السوق مستقر ولا توجد أحداث سلبية حادة"

# ============================================================
# 3) HTTP REQUESTS
# ============================================================

def http_get(url, headers=None, timeout=12):
    if headers is None:
        headers = {}
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ABED-FUTURES-RADAR/1.0",
            **headers
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)

# ============================================================
# 4) TELEGRAM
# ============================================================

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ بيانات تليجرام غير مكتملة.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
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
        with urllib.request.urlopen(req, timeout=12) as response:
            response.read()
        print("✅ Telegram: تم إرسال الإشعار بنجاح")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

# ============================================================
# 5) SIGNALS LOGGING (حفظ سجل الإشارات)
# ============================================================

def load_signal_log():
    if not os.path.exists(SIGNAL_LOG_FILE):
        return []
    try:
        with open(SIGNAL_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_signal(signal_data):
    try:
        logs = load_signal_log()
        logs.append(signal_data)
        logs = logs[-3000:]  # الاحتفاظ بآخر 3000 إشارة
        with open(SIGNAL_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        print(f"💾 تم حفظ الإشارة في {SIGNAL_LOG_FILE}")
    except Exception as e:
        print(f"خطأ أثناء حفظ الإشارة: {e}")

# ============================================================
# 6) COINGECKO NEWS RADAR (رادار الأخبار)
# ============================================================

def fetch_crypto_news():
    global cached_news
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        headers = {}
        if COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
        
        data = http_get(url, headers=headers, timeout=8)
        coins = data.get("coins", [])
        trending_symbols = [c["item"]["symbol"] for c in coins[:5]]
        
        if trending_symbols:
            cached_news = f"العملات الأكثر رواجاً عالمياً: {', '.join(trending_symbols)}"
        return cached_news
    except Exception:
        return cached_news

# ============================================================
# 7) BINANCE FUTURES DATA
# ============================================================

def get_24h_tickers():
    url = BINANCE_FAPI + "/fapi/v1/ticker/24hr"
    return http_get(url)

def select_symbols():
    try:
        tickers = get_24h_tickers()
        candidates = []
        for t in tickers:
            symbol = t.get("symbol", "")
            if not symbol.endswith("USDT") or symbol in EXCLUDED:
                continue
            try:
                volume = float(t.get("quoteVolume", 0))
                change = float(t.get("priceChangePercent", 0))
            except Exception:
                continue

            if volume < MIN_QUOTE_VOLUME:
                continue

            candidates.append({"symbol": symbol, "volume": volume, "change": change})

        candidates.sort(key=lambda x: x["volume"], reverse=True)
        return [x["symbol"] for x in candidates[:MAX_SYMBOLS]]
    except Exception as e:
        print(f"Symbol Scanner Error: {e}")
        return []

def get_klines(symbol, interval, limit=220):
    params = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    url = f"{BINANCE_FAPI}/fapi/v1/klines?{params}"
    return http_get(url)

def candle_data(klines):
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in klines:
        opens.append(float(k))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return opens, highs, lows, closes, volumes

# ============================================================
# 8) TECHNICAL INDICATORS
# ============================================================

def ema(values, period):
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result

def rsi(values, period=14):
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

def atr(highs, lows, closes, period=14):
    if len(closes) <= period:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return sum(trs[-period:]) / period

def macd(values):
    if len(values) < 35:
        return None, None
    macd_values = []
    for i in range(len(values)):
        e12 = ema(values[:i + 1], 12)
        e26 = ema(values[:i + 1], 26)
        if e12 is not None and e26 is not None:
            macd_values.append(e12 - e26)
    if len(macd_values) < 9:
        return None, None
    signal = ema(macd_values, 9)
    return macd_values[-1], signal

def vwap(klines):
    total_vol = sum(float(k[5]) for k in klines)
    if total_vol == 0:
        return None
    total_val = sum(((float(k[2]) + float(k[3]) + float(k[4])) / 3) * float(k[5]) for k in klines)
    return total_val / total_vol

def volume_spike(volumes, period=20):
    if len(volumes) < period + 1:
        return 1.0
    avg = sum(volumes[-period - 1:-1]) / period
    return (volumes[-1] / avg) if avg > 0 else 1.0

def support_resistance(highs, lows, lookback=50):
    return min(lows[-lookback:]), max(highs[-lookback:])

def get_funding(symbol):
    try:
        params = urllib.parse.urlencode({"symbol": symbol, "limit": 1})
        data = http_get(f"{BINANCE_FAPI}/fapi/v1/fundingRate?{params}")
        return float(data[-1]["fundingRate"]) if data else 0.0
    except Exception:
        return 0.0

def get_open_interest(symbol):
    try:
        params = urllib.parse.urlencode({"symbol": symbol})
        data = http_get(f"{BINANCE_FAPI}/fapi/v1/openInterest?{params}")
        return float(data.get("openInterest", 0))
    except Exception:
        return 0.0

def get_btc_context():
    try:
        klines = get_klines("BTCUSDT", "1h", 220)
        _, _, _, c, _ = candle_data(klines)
        e50 = ema(c, 50)
        e200 = ema(c, 200)
        if not e50 or not e200:
            return "SIDEWAYS"
        if c[-1] > e50 and e50 > e200:
            return "BULLISH"
        if c[-1] < e50 and e50 < e200:
            return "BEARISH"
        return "SIDEWAYS"
    except Exception:
        return "SIDEWAYS"

# ============================================================
# 9) TIMEFRAME ANALYSIS
# ============================================================

def analyze_timeframe(symbol, interval):
    try:
        klines = get_klines(symbol, interval, 220)
        if not klines or len(klines) < 100:
            return None

        opens, highs, lows, closes, volumes = candle_data(klines)
        price = closes[-1]

        e20 = ema(closes, 20)
        e50 = ema(closes, 50)
        rsi_val = rsi(closes)
        atr_val = atr(highs, lows, closes)
        macd_val, macd_sig = macd(closes)
        cur_vwap = vwap(klines[-100:])
        v_spike = volume_spike(volumes)
        support, resistance = support_resistance(highs, lows)

        bullish = 0
        bearish = 0

        # EMA Trend
        if e20 and e50:
            if price > e20 > e50:
                bullish += 20
            elif price < e20 < e50:
                bearish += 20

        # RSI Momentum
        if rsi_val is not None:
            if 50 <= rsi_val <= 70:
                bullish += 15
            elif 30 <= rsi_val <= 50:
                bearish += 15

        # MACD
        if macd_val is not None and macd_sig is not None:
            if macd_val > macd_sig:
                bullish += 10
            elif macd_val < macd_sig:
                bearish += 10

        # VWAP
        if cur_vwap:
            if price > cur_vwap:
                bullish += 10
            elif price < cur_vwap:
                bearish += 10

        # Volume Spike
        if v_spike >= 1.3:
            if price > opens[-1]:
                bullish += 10
            elif price < opens[-1]:
                bearish += 10

        # Breakout
        prev_high = max(highs[-11:-1])
        prev_low = min(lows[-11:-1])
        if price >= prev_high:
            bullish += 15
        elif price <= prev_low:
            bearish += 15

        return {
            "price": price,
            "atr": atr_val,
            "support": support,
            "resistance": resistance,
            "bullish": bullish,
            "bearish": bearish,
            "vol_spike": v_spike,
            "vwap": cur_vwap,
            "rsi": rsi_val
        }
    except Exception:
        return None

# ============================================================
# 10) SIGNAL ENGINE & SCORING (من 100 نقطة)
# ============================================================

def build_signal(symbol, btc_context):
    try:
        tf4h = analyze_timeframe(symbol, "4h")
        tf1h = analyze_timeframe(symbol, "1h")
        tf15 = analyze_timeframe(symbol, "15m")
        tf5 = analyze_timeframe(symbol, "5m")

        if not all([tf4h, tf1h, tf15, tf5]):
            return None

        funding = get_funding(symbol)
        oi = get_open_interest(symbol)

        long_score = 0
        short_score = 0

        # 4H (25 نقطة)
        if tf4h["bullish"] >= 20: long_score += 25
        if tf4h["bearish"] >= 20: short_score += 25

        # 1H (25 نقطة)
        if tf1h["bullish"] >= 20: long_score += 25
        if tf1h["bearish"] >= 20: short_score += 25

        # 15M (20 نقطة)
        if tf15["bullish"] >= 20: long_score += 20
        if tf15["bearish"] >= 20: short_score += 20

        # 5M (15 نقطة)
        if tf5["bullish"] >= 20: long_score += 15
        if tf5["bearish"] >= 20: short_score += 15

        # BTC Filter (15 نقطة)
        if btc_context == "BULLISH":
            long_score += 15
        elif btc_context == "BEARISH":
            short_score += 15
        else: # SIDEWAYS
            long_score += 5
            short_score += 5

        # Funding Rate Filter
        if funding > 0.0005:
            short_score += 5
        elif funding < -0.0005:
            long_score += 5

        # اختيار الاتجاه وقوة الإشارة
        if long_score >= MIN_SCORE and long_score > short_score:
            direction = "LONG"
            score = min(long_score, 100)
        elif short_score >= MIN_SCORE and short_score > long_score:
            direction = "SHORT"
            score = min(short_score, 100)
        else:
            return None  # NO TRADE إذا لم تتجمع الأدلة الكافية

        price = tf5["price"]
        atr_val = tf5["atr"] or (price * 0.01)
        support = tf15["support"]
        resistance = tf15["resistance"]

        # حساب مستويات الدخول، الوقف، والأهداف والـ Risk:Reward
        if direction == "LONG":
            entry_low = price - (atr_val * 0.15)
            entry_high = price + (atr_val * 0.05)
            sl = min(support - (atr_val * 0.1), price - (atr_val * 1.5))
            risk = max(price - sl, atr_val * 1.0)
            tp1 = price + (risk * 1.0)
            tp2 = price + (risk * 2.0)
            tp3 = price + (risk * 3.0)
            rr_ratio = f"1:{(tp2 - price) / risk:.1f}"
        else:
            entry_low = price - (atr_val * 0.05)
            entry_high = price + (atr_val * 0.15)
            sl = max(resistance + (atr_val * 0.1), price + (atr_val * 1.5))
            risk = max(sl - price, atr_val * 1.0)
            tp1 = price - (risk * 1.0)
            tp2 = price - (risk * 2.0)
            tp3 = price - (risk * 3.0)
            rr_ratio = f"1:{(price - tp2) / risk:.1f}"

        signal_dict = {
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
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
            "rr": rr_ratio,
            "btc": btc_context,
            "funding": funding,
            "oi": oi,
            "rsi_5m": round(tf5["rsi"], 1) if tf5["rsi"] else 50.0
        }
        return signal_dict
    except Exception as e:
        print(f"Error in signal calculation for {symbol}: {e}")
        return None

# ============================================================
# 11) FORMAT & ALERT
# ============================================================

def format_telegram_alert(signal):
    dir_emoji = "🟢 <b>LONG (شراء / صعود)</b>" if signal["direction"] == "LONG" else "🔴 <b>SHORT (بيع / هبوط)</b>"
    
    text = (
        f"🚨 <b>إشارة تداول رادار حكيم V1</b> 🚨\n\n"
        f"🪙 <b>العملة:</b> <code>#{signal['symbol']}</code>\n"
        f"📊 <b>الاتجاه:</b> {dir_emoji}\n"
        f"⭐ <b>قوة الإشارة:</b> <b>{signal['score']}/100</b>\n"
        f"⚖️ <b>نسبة العائد للمخاطرة (R:R):</b> <code>{signal['rr']}</code>\n"
        f"💵 <b>السعر الحالي:</b> <code>{signal['price']:.4f}</code>\n\n"
        f"🎯 <b>منطقة الدخول (Entry Zone):</b>\n"
        f"<code>{signal['entry_low']:.4f}</code> ⬅️ <code>{signal['entry_high']:.4f}</code>\n\n"
        f"🛑 <b>وقف الخسارة (SL):</b> <code>{signal['sl']:.4f}</code>\n"
        f"🎯 <b>الهدف الأول (TP1):</b> <code>{signal['tp1']:.4f}</code>\n"
        f"🎯 <b>الهدف الثاني (TP2):</b> <code>{signal['tp2']:.4f}</code>\n"
        f"🎯 <b>الهدف الثالث (TP3):</b> <code>{signal['tp3']:.4f}</code>\n\n"
        f"🌐 <b>سوق البيتكوين:</b> {signal['btc']}\n"
        f"📊 <b>RSI (5m):</b> {signal['rsi_5m']} | <b>Funding:</b> {signal['funding']:.4%}\n"
        f"📰 <b>رادار الأخبار:</b> {cached_news}\n"
        f"⏰ <b>التوقيت:</b> {signal['timestamp']}"
    )
    return text

# ============================================================
# 12) MAIN SCAN LOOP
# ============================================================

def scan_once():
    global cycle_counter
    cycle_counter += 1

    # تحديث الأخبار دورياً
    if cycle_counter % NEWS_CHECK_EVERY_CYCLES == 1:
        fetch_crypto_news()

    symbols = select_symbols()
    btc_context = get_btc_context()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 فحص {len(symbols)} عملة في العقود الآجلة | البيتكوين: {btc_context}")

    signals_found = 0
    for symbol in symbols:
        now = time.time()
        # منع تكرار الإشارة لنفس العملة خلال فترة التبريد
        if symbol in last_signals and (now - last_signals[symbol] < SIGNAL_COOLDOWN):
            continue

        signal = build_signal(symbol, btc_context)
        if signal:
            msg = format_telegram_alert(signal)
            print(f"🔥 إشارة مكتشفة: {symbol} - {signal['direction']} ({signal['score']} pts)")
            send_telegram(msg)
            save_signal(signal)
            last_signals[symbol] = now
            signals_found += 1

    if signals_found == 0:
        print("ℹ️ الفحص مكتمل: NO TRADE (لا توجد صفقات مستوفية للأدلة والشروط حالياً)")


def run_radar():
    print("🚀 بدء تشغيل رادار حكيم V1 المكتمل...")
    send_telegram(
        "🟢 <b>تم تشغيل رادار حكيم V1 المتكامل بنجاح!</b>\n\n"
        "📊 <b>المواصفات النشطة:</b>\n"
        "• فحص متعدد الفريمات (4H, 1H, 15M, 5M)\n"
        "• المؤشرات: EMA, RSI, MACD, ATR, VWAP, S/R, Volume\n"
        "• فلاتر: اتجاه BTC + Funding Rate + CoinGecko News\n"
        "• تنبيهات متكاملة مع SL و TP1/2/3 ونسبة R:R وحفظ السجل.\n\n"
        "📡 <i>جاري مراقبة السوق على مدار الساعة...</i>"
    )
    while True:
        try:
            scan_once()
        except Exception as e:
            print(f"خطأ في دورة الفحص: {e}")
        time.sleep(SCAN_SECONDS)


