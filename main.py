# ============================================================
# ABED LIVE RADAR & NEWS STREAM - V2
# Binance USD-M Futures + CoinGecko Live News
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

# فاصل البث والتحديث بالثواني
SCAN_SECONDS = 30

# قوة الإشارة الأدنى
MIN_SCORE = 65

# عدد العملات المفحوصة
MAX_SYMBOLS = 35
MIN_QUOTE_VOLUME = 5_000_000
SIGNAL_COOLDOWN = 1200

BINANCE_FAPI = "https://fapi.binance.com"
EXCLUDED = {"USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT"}

last_signals = {}

# ============================================================
# 2) دوال الاتصال وتليجرام
# ============================================================

def http_get(url, headers=None, timeout=10):
    if headers is None:
        headers = {}
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ABED-RADAR/2.0", **headers}
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
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("✅ تم الإرسال إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")
        return False

# ============================================================
# 3) جلب بيانات السوق والأخبار العالمية
# ============================================================

def get_market_tickers():
    try:
        tickers = http_get(BINANCE_FAPI + "/fapi/v1/ticker/24hr")
        valid = []
        for t in tickers:
            sym = t.get("symbol", "")
            if not sym.endswith("USDT") or sym in EXCLUDED:
                continue
            try:
                vol = float(t.get("quoteVolume", 0))
                chg = float(t.get("priceChangePercent", 0))
                prc = float(t.get("lastPrice", 0))
            except Exception:
                continue
            if vol >= MIN_QUOTE_VOLUME:
                valid.append({"symbol": sym, "volume": vol, "change": chg, "price": prc})
        valid.sort(key=lambda x: x["volume"], reverse=True)
        return valid
    except Exception:
        return []


def get_global_trending():
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        data = http_get(url, timeout=7)
        coins = data.get("coins", [])
        trending = [f"#{c['item']['symbol']}" for c in coins[:5]]
        return ", ".join(trending)
    except Exception:
        return "#BTC, #ETH, #SOL, #BNB, #XRP"

# ============================================================
# 4) التحليل الفني والشموع
# ============================================================

def get_klines(symbol, interval, limit=100):
    params = urllib.parse.urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    return http_get(f"{BINANCE_FAPI}/fapi/v1/klines?{params}")


def parse_klines(klines):
    opens = [float(k[1]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    return opens, highs, lows, closes, volumes


def EMA(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    res = sum(values[:period]) / period
    for p in values[period:]:
        res = (p - res) * k + res
    return res


def RSI(values, period=14):
    if len(values) <= period:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    return 100 if al == 0 else 100 - (100 / (1 + ag / al))


def ATR(highs, lows, closes, period=14):
    if len(closes) <= period:
        return None
    trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(closes))]
    return sum(trs[-period:]) / period


def btc_status():
    try:
        klines = get_klines("BTCUSDT", "1h", 100)
        _, _, _, c, _ = parse_klines(klines)
        e50 = EMA(c, 50)
        if not e50:
            return "محايد ⚪", c[-1]
        trend = "صاعد 🟢" if c[-1] > e50 else "هابط 🔴"
        return trend, c[-1]
    except Exception:
        return "مستقر", 0

# ============================================================
# 5) فحص العملات واكتشاف الإشارات
# ============================================================

def quick_analyze(symbol):
    try:
        k5 = get_klines(symbol, "5m", 80)
        k1h = get_klines(symbol, "1h", 80)
        if not k5 or not k1h:
            return None
        _, h5, l5, c5, v5 = parse_klines(k5)
        _, _, _, c1h, _ = parse_klines(k1h)

        e20 = EMA(c5, 20)
        e50 = EMA(c5, 50)
        rsi_val = RSI(c5)
        atr_val = ATR(h5, l5, c5)
        e1h = EMA(c1h, 50)

        bull = 0
        bear = 0

        if e20 and e50 and c5[-1] > e20 > e50:
            bull += 35
        elif e20 and e50 and c5[-1] < e20 < e50:
            bear += 35

        if e1h and c1h[-1] > e1h:
            bull += 25
        elif e1h and c1h[-1] < e1h:
            bear += 25

        if rsi_val:
            if 50 <= rsi_val <= 70: bull += 20
            elif 30 <= rsi_val <= 50: bear += 20

        # Breakout
        if c5[-1] >= max(h5[-10:-1]): bull += 20
        elif c5[-1] <= min(l5[-10:-1]): bear += 20

        if bull >= MIN_SCORE and bull > bear:
            direction = "LONG"
            score = bull
        elif bear >= MIN_SCORE and bear > bull:
            direction = "SHORT"
            score = bear
        else:
            return None

        price = c5[-1]
        atr_use = atr_val or (price * 0.01)
        if direction == "LONG":
            entry_low = price - (atr_use * 0.15)
            entry_high = price + (atr_use * 0.05)
            sl = price - (atr_use * 1.5)
            risk = max(price - sl, atr_use)
            tp1, tp2, tp3 = price + risk, price + (risk * 2), price + (risk * 3)
        else:
            entry_low = price - (atr_use * 0.05)
            entry_high = price + (atr_use * 0.15)
            sl = price + (atr_use * 1.5)
            risk = max(sl - price, atr_use)
            tp1, tp2, tp3 = price - risk, price - (risk * 2), price - (risk * 3)

        return {
            "symbol": symbol, "direction": direction, "score": score, "price": price,
            "entry_low": entry_low, "entry_high": entry_high, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3
        }
    except Exception:
        return None

# ============================================================
# 6) تنسيق رسائل التداول ونبض الأخبار
# ============================================================

def format_signal_msg(sig, btc_t):
    dir_txt = "🟢 LONG (شراء / صعود)" if sig["direction"] == "LONG" else "🔴 SHORT (بيع / هبوط)"
    return (
        f"🚨 <b>إشارة تداول عاجلة | رادار حكيم</b> 🚨\n\n"
        f"🪙 <b>العملة:</b> <code>#{sig['symbol']}</code>\n"
        f"📊 <b>الاتجاه:</b> {dir_txt}\n"
        f"⭐ <b>قوة الإشارة:</b> {sig['score']}/100\n"
        f"💵 <b>السعر اللحظي:</b> <code>{sig['price']:.4f}</code>\n\n"
        f"🎯 <b>منطقة الدخول:</b> <code>{sig['entry_low']:.4f}</code> ⬅️ <code>{sig['entry_high']:.4f}</code>\n"
        f"🛑 <b>وقف الخسارة (SL):</b> <code>{sig['sl']:.4f}</code>\n"
        f"🎯 <b>الهدف 1:</b> <code>{sig['tp1']:.4f}</code>\n"
        f"🎯 <b>الهدف 2:</b> <code>{sig['tp2']:.4f}</code>\n"
        f"🎯 <b>الهدف 3:</b> <code>{sig['tp3']:.4f}</code>\n\n"
        f"🌐 <b>حالة البيتكوين:</b> {btc_t}\n"
        f"⏰ <b>الوقت:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
    )


def format_radar_pulse(gainers, losers, trending, btc_t, btc_p):
    gainers_str = " | ".join([f"#{g['symbol'].replace('USDT','')}: +{g['change']:.1f}%" for g in gainers[:3]])
    losers_str = " | ".join([f"#{l['symbol'].replace('USDT','')}: {l['change']:.1f}%" for l in losers[:3]])
    
    return (
        f"📡 <b>نبض السوق والأخبار المباشرة | رادار حكيم</b>\n\n"
        f"🪙 <b>سعر البيتكوين (BTC):</b> <code>${btc_p:,.1f}</code> ({btc_t})\n"
        f"🔥 <b>العملات الأكثر رواجاً عالمياً (CoinGecko):</b>\n{trending}\n\n"
        f"🚀 <b>الأعلى صعوداً الآن في بينانس:</b>\n{gainers_str}\n\n"
        f"🔻 <b>الأعلى هبوطاً الآن في بينانس:</b>\n{losers_str}\n\n"
        f"🔍 <i>تم فحص السوق - جاري المراقبة للدخول الآمن...</i>\n"
        f"⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
    )

# ============================================================
# 7) حلقة البث المباشر
# ============================================================

def live_stream_cycle():
    all_tickers = get_market_tickers()
    if not all_tickers:
        return

    btc_t, btc_p = btc_status()
    top_symbols = [t["symbol"] for t in all_tickers[:MAX_SYMBOLS]]
    
    # فرز الأعلى ارتفاعاً وانخفاضاً
    by_change = sorted(all_tickers, key=lambda x: x["change"], reverse=True)
    gainers = by_change[:3]
    losers = by_change[-3:]
    losers.reverse()

    # فحص صفقات التداول
    signal_sent = False
    for sym in top_symbols:
        now = time.time()
        if sym in last_signals and (now - last_signals[sym] < SIGNAL_COOLDOWN):
            continue

        sig = quick_analyze(sym)
        if sig:
            msg = format_signal_msg(sig, btc_t)
            send_telegram(msg)
            last_signals[sym] = now
            signal_sent = True
            break

    # إذا لم تكن هناك صفقة مؤكدة، نرسل نبض السوق والأخبار
    if not signal_sent:
        trending = get_global_trending()
        pulse_msg = format_radar_pulse(gainers, losers, trending, btc_t, btc_p)
        send_telegram(pulse_msg)


def run_radar():
    print("🚀 بدء البث المباشر لرادار حكيم V2...")
    send_telegram(
        "🟢 <b>تم تفعيل البث المباشر لرادار حكيم!</b>\n\n"
        "📡 <i>ستصلك الآن تحديثات ونبض السوق والأخبار والصفقات كل 30 ثانية باستمرار.</i>"
    )
    while True:
        try:
            live_stream_cycle()
        except Exception as e:
            print(f"خطأ: {e}")
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run_radar()
    
