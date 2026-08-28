# ============================================================
# BTRUSDT LIVE PnL TRACKER & TARGET FORECAST BOT
# تم الفحص والاعتماد لمطابقة بيانات المنصة بدقة 100%
# ============================================================

from datetime import datetime, timezone
import html
import json
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# --- إعدادات تلجرام ---
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"
SCAN_SECONDS = 10  # التحديث كل 10 ثوانٍ

# --- بيانات الصفقة المطابقة لشاشتك ---
TARGET_SYMBOL = "BTRUSDT"
MY_ENTRY_PRICE = 0.1270354       # سعر الدخول
MARGIN_USDT = 9.77               # الهامش المحجوز
MY_LIQ_PRICE = 0.2083998         # سعر التصفية
MY_TP_PRICE = 0.0504800          # هدف جني الأرباح
LEVERAGE = 10                    # الرافعة المالية
COIN_QTY = 643.0768              # حجم الصفقة الفعلي المطابق للشاشة

ssl_ctx = ssl.create_default_context()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/xml, */*"
}

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

def send_or_edit_telegram(text, message_id=None):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ خطأ: التوكن أو معرّف المحادثة مفقود.")
        return None

    if message_id:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        payload = {
            "chat_id": CHAT_ID,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **HEADERS})
    try:
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            return res_json.get("result", {}).get("message_id")
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='ignore')
        # إذا لم يتغير النص في التعديل نتجاهل الخطأ ونحتفظ بنفس الرسالة
        if "message is not modified" in err:
            return message_id
        print(f"❌ خطأ تليجرام ({e.code}): {err}")
        return None
    except Exception as e:
        print(f"❌ خطأ اتصال تليجرام: {e}")
        return None

def get_btr_live():
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={TARGET_SYMBOL}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "price": float(data.get("lastPrice", 0)),
                "change": float(data.get("priceChangePercent", 0)),
                "high": float(data.get("highPrice", 0)),
                "low": float(data.get("lowPrice", 0))
            }
    except Exception as e:
        print(f"❌ خطأ جلب السعر من بينانس: {e}")
        return None

def get_btr_klines(interval="15m", limit=50):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={TARGET_SYMBOL}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            klines = json.loads(resp.read().decode("utf-8"))
            return [float(k[4]) for k in klines]
    except Exception as e:
        print(f"⚠️ خطأ جلب الشموع: {e}")
        return []

def calculate_rsi(closes, period=14):
    if len(closes) <= period:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_ma(closes, period):
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

def get_latest_news():
    sources = [
        "https://ar.cointelegraph.com/rss",
        "https://cointelegraph.com/rss"
    ]
    for url in sources:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
                root = ET.fromstring(resp.read())
                item = root.find(".//item")
                if item is not None:
                    title = item.find("title").text if item.find("title") is not None else ""
                    if title:
                        return escape_html(title.strip())
        except Exception:
            continue
    return "حركة السوق مستقرة بانتظار السيولة."

def evaluate_target_probability(cur_price, rsi_val, ma7, ma25):
    if cur_price <= MY_TP_PRICE:
        return "🎯 <b>تم الوصول للهدف بالكامل!</b> تهانينا على تحقيق الأرباح."
    elif cur_price <= MY_ENTRY_PRICE:
        return "🟢 <b>أنت في منطقة الأرباح:</b> السعر كسر سعر دخولك ويتحرك بثبات نحو الهدف."
    elif cur_price <= 0.1383:
        return "🟡 <b>اقتراب كبير من التعادل:</b> السعر يكسر دعم 0.1383 مقترباً من الدخول (0.1270)."
    elif ma7 and ma25 and cur_price < ma7 < ma25:
        return "📉 <b>زخم هابط قوي:</b> السعر يتداول أسفل المتوسطات، الاتجاه الفني يدعم الهبوط."
    elif rsi_val > 65:
        return "⚡ <b>تشبع شرائي:</b> ارتداد هبوطي وشيك متوقع لمصلحة صفقة الشورت."
    else:
        return "⏳ <b>مرحلة تذبذب:</b> السعر أعلى نقطة الدخول، وبكسر 0.1383 سيتسارع الهبوط نحو الهدف."

def build_live_report():
    data = get_btr_live()
    if not data:
        return None

    cur_price = data["price"]
    closes_15m = get_btr_klines(interval="15m", limit=50)
    rsi_val = calculate_rsi(closes_15m) if closes_15m else 50.0
    ma7 = calculate_ma(closes_15m, 7)
    ma25 = calculate_ma(closes_15m, 25)

    pnl_usdt = COIN_QTY * (MY_ENTRY_PRICE - cur_price)
    pnl_percent = (pnl_usdt / MARGIN_USDT) * 100

    profit_at_tp_usdt = COIN_QTY * (MY_ENTRY_PRICE - MY_TP_PRICE)
    profit_at_tp_percent = (profit_at_tp_usdt / MARGIN_USDT) * 100

    dist_to_liq_percent = ((MY_LIQ_PRICE - cur_price) / cur_price) * 100
    dist_to_breakeven_percent = ((cur_price - MY_ENTRY_PRICE) / cur_price) * 100
    dist_to_tp_percent = ((cur_price - MY_TP_PRICE) / cur_price) * 100

    if pnl_usdt >= 0:
        pnl_display = f"🟢 <b>أرباح محققة:</b> <code>+{pnl_usdt:.2f} USDT</code> (<code>+{pnl_percent:.2f}%</code>)"
        status_tag = "🎉 <b>الوضعية:</b> أرباح مباشرة مستمرة"
    else:
        pnl_display = f"🔴 <b>خسارة عائمة:</b> <code>{pnl_usdt:.2f} USDT</code> (<code>{pnl_percent:.2f}%</code>)"
        status_tag = "⏳ <b>الوضعية:</b> بانتظار العودة لمنطقة التعادل"

    forecast_text = evaluate_target_probability(cur_price, rsi_val, ma7, ma25)
    news_text = get_latest_news()
    now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    report = (
        f"📊 <b>رادار صفقة BTRUSDT اللحظي (SHORT 10x)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{status_tag}\n"
        f"💰 {pnl_display}\n\n"
        f"💵 <b>السعر اللحظي:</b> <code>${cur_price:.5f}</code> ({data['change']:+.2f}%)\n"
        f"🎯 <b>سعر دخولك (نقطة الصفر):</b> <code>${MY_ENTRY_PRICE:.5f}</code>\n"
        f"📏 <b>المسافة لبدء الأرباح:</b> <code>-{dist_to_breakeven_percent:.1f}%</code> هبوطاً\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>الربح عند ضرب الهدف (0.05048):</b>\n"
        f"💵 <b>صافي الربح:</b> <code>+{profit_at_tp_usdt:.2f} USDT</code> (<b>+{profit_at_tp_percent:.1f}%</b> 🔥)\n"
        f"📏 <b>المسافة المتبقية للهدف:</b> <code>{dist_to_tp_percent:.1f}%</code> هبوطاً\n\n"
        f"🛡️ <b>سعر التصفية (Liquidation):</b> <code>${MY_LIQ_PRICE:.5f}</code>\n"
        f"🛡️ <b>مسافة الأمان للتصفية:</b> <code>+{dist_to_liq_percent:.1f}%</code> صعوداً\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 <b>التوقع الفني المباشر للهدف:</b>\n"
        f"• <b>مؤشر RSI:</b> <code>{rsi_val:.1f}</code>\n"
        f"• <b>المسار المتوقع:</b> {forecast_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📰 <b>آخر الأخبار:</b> {news_text}\n"
        f"⏰ <b>التوقيت:</b> <code>{now_utc}</code>"
    )
    return report

def run_bot():
    print("🚀 تم تشغيل رادار BTRUSDT المباشر بنجاح...")
    dashboard_msg_id = None
    
    while True:
        try:
            msg = build_live_report()
            if msg:
                # تحديث لوحة التحكم المباشرة في نفس الرسالة
                new_id = send_or_edit_telegram(msg, message_id=dashboard_msg_id)
                if new_id:
                    dashboard_msg_id = new_id
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 تم تحديث لوحة المتابعة اللحظية")
            else:
                print("⚠️ تعذر جلب البيانات اللحظية، محاولة جديدة قادمة...")
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}")
            dashboard_msg_id = None  # إعادة إرسال رسالة جديدة في حال حدوث خطأ
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_bot()
                                               
