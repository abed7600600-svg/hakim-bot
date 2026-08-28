# ============================================================
# BTRUSDT LIVE QUANTITATIVE RADAR & MULTI-INDICATOR ENGINE
# محرك التحليل الفني الشامل والمتابعة اللحظية للصفقة (10s)
# ============================================================

from datetime import datetime, timezone
import html
import json
import math
import ssl
import time
import urllib.error
import urllib.request

# --- إعدادات تلجرام ومعلومات الصفقة ---
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"
SCAN_SECONDS = 10  # التحديث كل 10 ثوانٍ

TARGET_SYMBOL = "BTRUSDT"
MY_ENTRY_PRICE = 0.1270354       # سعر الدخول
MARGIN_USDT = 9.77               # الهامش المحجوز
MY_LIQ_PRICE = 0.2083998         # سعر التصفية
MY_TP_PRICE = 0.0504800          # هدف جني الأرباح
LEVERAGE = 10                    # الرافعة المالية
COIN_QTY = 643.0768              # كمية العملات المطابقة للمنصة

ssl_ctx = ssl.create_default_context()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/xml, */*"
}

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

# --- الإرسال الآمن لتلجرام مع نظام الاحتياط (Fallback) ---
def send_or_edit_telegram(text, message_id=None):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ خطأ: التوكن أو معرّف المحادثة مفقود.", flush=True)
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText" if message_id else f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if message_id:
        payload["message_id"] = message_id

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **HEADERS})
    try:
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            return res_json.get("result", {}).get("message_id")
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='ignore')
        if "message is not modified" in err:
            return message_id
        print(f"⚠️ تنبيه تلجرام ({e.code}): {err}", flush=True)
        # إرسال احتياطي بدون تنسيق في حال حدوث أي خطأ
        if "can't parse entities" in err or e.code == 400:
            try:
                plain_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                payload["text"] = plain_text
                payload.pop("parse_mode", None)
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                req2 = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **HEADERS})
                with urllib.request.urlopen(req2, timeout=8, context=ssl_ctx) as resp2:
                    res_json = json.loads(resp2.read().decode("utf-8"))
                    return res_json.get("result", {}).get("message_id")
            except Exception:
                pass
        return None
    except Exception as e:
        print(f"❌ خطأ اتصال تلجرام: {e}", flush=True)
        return None

# --- جلب السعر من مصادر عالمية متعددة لتفادي الحظر السحابي ---
def get_btr_market_data():
    # 1. CoinGecko API
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitlayer&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            btr = data.get("bitlayer", {})
            p = float(btr.get("usd", 0))
            if p > 0:
                return {"price": p, "change_24h": float(btr.get("usd_24h_change", 0)), "source": "CoinGecko"}
    except Exception:
        pass

    # 2. Gate.io API
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTR_USDT"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                p = float(data[0].get("last", 0))
                if p > 0:
                    return {"price": p, "change_24h": float(data[0].get("change_percentage", 0)), "source": "Gate.io"}
    except Exception:
        pass

    # 3. Binance Futures API
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={TARGET_SYMBOL}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            p = float(data.get("lastPrice", 0))
            if p > 0:
                return {"price": p, "change_24h": float(data.get("priceChangePercent", 0)), "source": "Binance"}
    except Exception:
        pass

    return None

# --- محرك التحليل الكمي وإجماع المؤشرات الشاملة ---
def calculate_advanced_indicators(cur_price):
    signals = []

    # 1. تحليل مستويات المتوسطات السعرية والمقاومات
    if cur_price < 0.1633:  # أسفل مقاومة MA25
        signals.extend()
    else:
        signals.extend([-1, -1])

    if cur_price < 0.1601:  # أسفل متوسط MA7
        signals.extend()
    else:
        signals.extend([-1])

    # 2. فحص الهبوط نحو مناطق الدعم
    if cur_price <= 0.1383: # كسر أول دعم
        signals.extend()
    if cur_price <= MY_ENTRY_PRICE: # كسر سعر الدخول (أرباح)
        signals.extend()
    if cur_price <= 0.1116: # كسر متوسط MA99 طويل الأجل
        signals.extend()

    # 3. نسبة الأمان من سعر التصفية
    dist_liq = (MY_LIQ_PRICE - cur_price) / cur_price
    if dist_liq > 0.30:  # مسافة أمان تفوق 30%
        signals.extend()
    elif dist_liq < 0.15:
        signals.extend([-1, -1, -1])

    # 4. ارتداد السعر من القمة السابقة (0.1817)
    if cur_price < 0.1817:
        signals.extend()
    else:
        signals.extend([-1, -1, -1])

    bearish_count = signals.count(1)   # إشارات تدعم هبوط السعر لمصلحتك
    bullish_count = signals.count(-1)  # إشارات تدعم الصعود ضدك
    total_signals = len(signals)

    win_prob = round((bearish_count / total_signals) * 100, 1)
    win_prob = max(20.0, min(98.0, win_prob))

    # التقييم اللفظي بالعربية
    if cur_price <= MY_TP_PRICE:
        trend_status = "🎯 <b>تم ضرب الهدف بالكامل!</b>"
        forecast_ar = "السعر حقق كامل الهدف المحدد (0.05048). يمكنك إغلاق الصفقة وجني الأرباح بالكامل."
    elif cur_price <= MY_ENTRY_PRICE:
        trend_status = "🟢 <b>السعر في منطقة الأرباح (هبوط قوي)</b>"
        forecast_ar = "السعر كسر سعر دخولك لأسفل؛ الزخم الهابط قوي جداً والاتجاه مستمر نحو الهدف دون مقاومة."
    elif cur_price <= 0.1383:
        trend_status = "🟡 <b>اقتراب شديد من نقطة الصفر (التعادل)</b>"
        forecast_ar = "السعر يكسر دعم 0.1383؛ احتمالية الصعود ضعيفة جداً والهبوط نحو نقطة دخولك (0.1270) هو السيناريو الأقرب."
    elif cur_price < 0.1633:
        trend_status = "📉 <b>فقدان الزخم الصعودي وبداية تصحيح هابط</b>"
        forecast_ar = "السعر فشل في اختراق مقاومة 0.1633 ويتداول أسفل المتوسطات (MA7 و MA25). إجماع المؤشرات يدعم الهبوط التصحيحي لمصلحتك."
    elif cur_price < 0.1817:
        trend_status = "⚠️ <b>مرحلة اختبار قمة 0.1817 (تذبذب)</b>"
        forecast_ar = "السعر يختبر قمة الارتداد؛ يحتاج للارتداد لأسفل دون اختراق 0.1817 لتفادي زيادة ضغط الصعود."
    else:
        trend_status = "🚨 <b>صعود قوي وخطر اقتراب من التصفية</b>"
        forecast_ar = "السعر اخترق القمم السابقة ويقترب من سعر التصفية 0.2084؛ يجب الحذر الشديد."

    return win_prob, bearish_count, bullish_count, trend_status, forecast_ar

# --- بناء لوحة التقرير اللحظي الكاملة ---
def build_live_report():
    data = get_btr_market_data()
    if not data or data["price"] <= 0:
        return None

    cur_price = data["price"]
    change_24h = data["change_24h"]

    pnl_usdt = COIN_QTY * (MY_ENTRY_PRICE - cur_price)
    pnl_percent = (pnl_usdt / MARGIN_USDT) * 100

    profit_at_tp_usdt = COIN_QTY * (MY_ENTRY_PRICE - MY_TP_PRICE)
    profit_at_tp_percent = (profit_at_tp_usdt / MARGIN_USDT) * 100

    dist_to_liq_percent = ((MY_LIQ_PRICE - cur_price) / cur_price) * 100
    dist_to_breakeven_percent = ((cur_price - MY_ENTRY_PRICE) / cur_price) * 100
    dist_to_tp_percent = ((cur_price - MY_TP_PRICE) / cur_price) * 100

    win_prob, bear_signals, bull_signals, trend_status, forecast_ar = calculate_advanced_indicators(cur_price)

    if pnl_usdt >= 0:
        pnl_display = f"🟢 <b>أرباح حالية:</b> <code>+{pnl_usdt:.2f} USDT</code> (<code>+{pnl_percent:.2f}%</code>)"
        status_tag = "🎉 <b>الوضع الحالي:</b> رابح"
    else:
        pnl_display = f"🔴 <b>خسارة عائمة:</b> <code>{pnl_usdt:.2f} USDT</code> (<code>{pnl_percent:.2f}%</code>)"
        status_tag = "⏳ <b>الوضع الحالي:</b> عائم بانتظار الهبوط"

    now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    report = (
        f"📊 <b>رادار وتحليل صفقة BTRUSDT (SHORT 10x)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{status_tag}\n"
        f"💰 {pnl_display}\n\n"
        f"💵 <b>السعر اللحظي:</b> <code>${cur_price:.5f}</code> ({change_24h:+.2f}%)\n"
        f"🎯 <b>سعر دخولك (نقطة الصفر):</b> <code>${MY_ENTRY_PRICE:.5f}</code>\n"
        f"📏 <b>المسافة لبدء الأرباح:</b> <code>-{dist_to_breakeven_percent:.1f}%</code> هبوطاً\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 <b>إجماع المؤشرات واحتمالية الفوز:</b>\n"
        f"• <b>نسبة احتمالية فوز الصفقة:</b> <b>{win_prob}%</b>\n"
        f"• <b>قوة الإشارات:</b> <code>{bear_signals}</code> إشارة هبوط 🟢 مقابل <code>{bull_signals}</code> صعود 🔴\n\n"
        f"📈 <b>هل سيستمر الصعود؟:</b>\n"
        f"• {trend_status}\n"
        f"• <b>التفاصيل:</b> {forecast_ar}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>الربح عند ضرب الهدف (0.05048):</b>\n"
        f"💵 <b>صافي الأرباح:</b> <code>+{profit_at_tp_usdt:.2f} USDT</code> (<b>+{profit_at_tp_percent:.1f}%</b> 🔥)\n"
        f"📏 <b>المسافة المتبقية للهدف:</b> <code>{dist_to_tp_percent:.1f}%</code> هبوطاً\n\n"
        f"🛡️ <b>سعر التصفية (Liquidation):</b> <code>${MY_LIQ_PRICE:.5f}</code>\n"
        f"🛡️ <b>مسافة الأمان للتصفية:</b> <code>+{dist_to_liq_percent:.1f}%</code> صعوداً\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>التوقيت:</b> <code>{now_utc}</code>"
    )
    return report

# --- التشغيل الدائم على GitHub Actions ---
def run_bot():
    print("🚀 بدء تشغيل رادار BTRUSDT الكمي المتقدم...", flush=True)
    dashboard_msg_id = None

    while True:
        try:
            msg = build_live_report()
            if msg:
                new_id = send_or_edit_telegram(msg, message_id=dashboard_msg_id)
                if new_id:
                    dashboard_msg_id = new_id
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 تم تحديث التقرير والتحليل في تلجرام بنجاح", flush=True)
            else:
                print("⚠️ تعذر جلب السعر، إعادة المحاولة بعد ثوانٍ...", flush=True)
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}", flush=True)
            dashboard_msg_id = None
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_bot()
    
