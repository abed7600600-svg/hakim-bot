# ============================================================
# ABED FUTURES RADAR - V2 (بوت حكيم)
# Binance USD-M Futures
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
SCAN_SECONDS = 30
MIN_SCORE = 70  # تم تقليلها للتجربة، يمكنك رفعها لاحقاً لـ 78
MAX_SYMBOLS = 70
MIN_QUOTE_VOLUME = 5_000_000
SIGNAL_COOLDOWN = 1800

BINANCE = "https://fapi.binance.com"
EXCLUDED = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT"}
last_signal_time = {}

# ============================================================
# 4) طلبات HTTP
# ============================================================
def get_json(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ABED-RADAR/2.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
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
            if not symbol.endswith("USDT") or symbol in EXCLUDED:
                continue
            try:
                volume = float(t.get("quoteVolume", 0))
            except:
                continue
            if volume >= MIN_QUOTE_VOLUME:
                result.append({"symbol": symbol, "volume": volume})
        result.sort(key=lambda x: x["volume"], reverse=True)
        return [x["symbol"] for x in result[:MAX_SYMBOLS]]
    except:
        return []

# ============================================================
# 7) جلب بيانات الشموع (تم تصحيح الخطأ هنا)
# ============================================================
def get_klines(symbol, interval, limit=220):
    params = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    url = f"{BINANCE}/fapi/v1/klines?{params}"
    return get_json(url)

def parse_klines(klines):
    opens, highs, lows, closes, volumes = [], [], [], [], []
    for k in klines:
        opens.append(float(k[1]))  # تم التصحيح هنا
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
        volumes.append(float(k[5]))
    return opens, highs, lows, closes, volumes

# ============================================================
# 8) المؤشرات الفنية
# ============================================================
def EMA(values, period):
    if len(values) < period: return None
    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period
    for price in values[period:]:
        result = ((price - result) * multiplier) + result
    return result

def RSI(values, period=14):
    if len(values) <= period: return None
    gains, losses = [], []
    for i in range(1, len(values)):
        change = values[i] - values[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
    if avg_loss == 0: return 100
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def ATR(highs, lows, closes, period=14):
    if len(closes) <= period: return None
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
    return sum(trs[-period:]) / period

def MACD(values):
    if len(values) < 50: return None, None
    macd_values = []
    for i in range(len(values)):
        e12, e26 = EMA(values[:i+1], 12), EMA(values[:i+1], 26)
        if e12 and e26: macd_values.append(e12 - e26)
    if len(macd_values) < 9: return None, None
    return macd_values[-1], EMA(macd_values, 9)

def VWAP(klines):
    total_volume = total_value = 0
    for k in klines:
        typical = (float(k[2]) + float(k[3]) + float(k[4])) / 3
        total_value += typical * float(k[5])
        total_volume += float(k[5])
    return total_value / total_volume if total_volume else None

def volume_spike(volumes, period=20):
    if len(volumes) < period + 1: return 1
    avg = sum(volumes[-period-1:-1]) / period
    return volumes[-1] / avg if avg > 0 else 1

def support_resistance(highs, lows, lookback=60):
    return min(lows[-lookback:]), max(highs[-lookback:])

# ============================================================
# 9) التمويل والبيتكوين
# ============================================================
def get_funding(symbol):
    try:
        data = get_json(f"{BINANCE}/fapi/v1/fundingRate?symbol={symbol}&limit=1")
        return float(data[-1]["fundingRate"]) if data else 0
    except: return 0

def btc_regime():
    try:
        klines = get_klines("BTCUSDT", "1h", 220)
        _, _, _, c, _ = parse_klines(klines)
        e50, e200 = EMA(c, 50), EMA(c, 200)
        if not e50 or not e200: return "UNKNOWN"
        return "BULLISH" if c[-1] > e50 > e200 else ("BEARISH" if c[-1] < e50 < e200 else "SIDEWAYS")
    except: return "UNKNOWN"

# ============================================================
# 11) تحليل وبناء الإشارة
# ============================================================
def analyze(symbol, interval):
    try:
        klines = get_klines(symbol, interval, 220)
        if not klines or len(klines) < 100: return None
        opens, highs, lows, closes, volumes = parse_klines(klines)
        price = closes[-1]
        
        bullish = bearish = 0
        e20, e50, e200 = EMA(closes, 20), EMA(closes, 50), EMA(closes, 200)
        if e20 and e50 and e200:
            if price > e20 > e50 > e200: bullish += 20
            elif price < e20 < e50 < e200: bearish += 20
            
        rsi = RSI(closes)
        if rsi:
            if 52 <= rsi <= 68: bullish += 10
            elif 32 <= rsi <= 48: bearish += 10
            
        macd, macd_sig = MACD(closes)
        if macd and macd_sig:
            if macd > macd_sig: bullish += 10
            elif macd < macd_sig: bearish += 10
            
        vwap = VWAP(klines[-100:])
        if vwap:
            if price > vwap: bullish += 10
            elif price < vwap: bearish += 10
            
        if volume_spike(volumes) >= 1.4:
            if price > opens[-1]: bullish += 10
            elif price < opens[-1]: bearish += 10

        return {"price": price, "atr": ATR(highs, lows, closes), "support": min(lows[-11:-1]), "resistance": max(highs[-11:-1]), "bullish": bullish, "bearish": bearish, "vwap": vwap, "vol_spike": volume_spike(volumes)}
    except Exception as e:
        print(f"Error in analyze {symbol}: {e}")
        return None

def build_signal(symbol):
    try:
        tf4h, tf1h, tf15, tf5 = analyze(symbol, "4h"), analyze(symbol, "1h"), analyze(symbol, "15m"), analyze(symbol, "5m")
        if not all([tf4h, tf1h, tf15, tf5]): return None

        funding = get_funding(symbol)
        btc = btc_regime()
        long_score = short_score = 0

        for tf in [tf4h, tf1h, tf15, tf5]:
            if tf["bullish"] >= 25: long_score += 15
            if tf["bearish"] >= 25: short_score += 15

        if btc == "BULLISH": long_score += 10; short_score -= 10
        elif btc == "BEARISH": short_score += 10; long_score -= 10

        if funding > 0.0005: short_score += 5
        elif funding < -0.0005: long_score += 5

        if long_score >= MIN_SCORE and long_score > short_score + 10:
            direction = "LONG"
            score = min(long_score, 100)
        elif short_score >= MIN_SCORE and short_score > long_score + 10:
            direction = "SHORT"
            score = min(short_score, 100)
        else: return None

        price, atr = tf5["price"], tf5["atr"]
        if not atr: return None

        if direction == "LONG":
            entry_low, entry_high = price - (atr * 0.20), price + (atr * 0.10)
            sl = price - (atr * 1.5)
            risk = price - sl
            tp1, tp2, tp3 = price + (risk * 1.0), price + (risk * 2.0), price + (risk * 3.0)
        else:
            entry_low, entry_high = price - (atr * 0.10), price + (atr * 0.20)
            sl = price + (atr * 1.5)
            risk = sl - price
            tp1, tp2, tp3 = price - (risk * 1.0), price - (risk * 2.0), price - (risk * 3.0)

        return {"symbol": symbol, "direction": direction, "score": score, "price": price, "entry_low": entry_low, "entry_high": entry_high, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3, "btc": btc, "funding": funding}
    except Exception as e: return None

# ============================================================
# 13) إرسال التنبيه
# ============================================================
def format_alert(signal):
    dir_emoji = "🟢 LONG (شراء)" if signal["direction"] == "LONG" else "🔴 SHORT (بيع)"
    return (
        f"🚨 <b>إشارة تداول | رادار حكيم</b> 🚨\n\n"
        f"🪙 <b>العملة:</b> #{signal['symbol']}\n"
        f"📊 <b>الاتجاه:</b> {dir_emoji}\n"
        f"⭐ <b>قوة الإشارة:</b> {signal['score']}/100\n"
        f"💵 <b>السعر الحالي:</b> <code>{signal['price']:.4f}</code>\n\n"
        f"🎯 <b>منطقة الدخول:</b> <code>{signal['entry_low']:.4f}</code> - <code>{signal['entry_high']:.4f}</code>\n"
        f"🛑 <b>وقف الخسارة (SL):</b> <code>{signal['sl']:.4f}</code>\n"
        f"🎯 <b>الأهداف:</b>\n"
        f"TP1: <code>{signal['tp1']:.4f}</code>\n"
        f"TP2: <code>{signal['tp2']:.4f}</code>\n"
        f"TP3: <code>{signal['tp3']:.4f}</code>\n\n"
        f"🌐 <b>حالة BTC:</b> {signal['btc']}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

# ============================================================
# 14) التشغيل
# ============================================================
def scan_once():
    symbols = get_symbols()
    print(f"🔍 فحص {len(symbols)} عملة...")
    for symbol in symbols:
        now = time.time()
        if symbol in last_signal_time and (now - last_signal_time[symbol] < SIGNAL_COOLDOWN):
            continue
        signal = build_signal(symbol)
        if signal:
            send_telegram(format_alert(signal))
            print(f"🔥 إشارة مكتشفة: {symbol}")
            last_signal_time[symbol] = now
        time.sleep(0.1)

def run_radar():
    print("🚀 بدء التشغيل...")
    send_telegram("🟢 <b>تم تحديث وتشغيل رادار حكيم بنجاح!</b>\n\n📡 <i>جاري فحص السوق...</i>")
    while True:
        try: scan_once()
        except Exception as e: print(f"خطأ عام: {e}")
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_radar()
                
