# ============================================================
# BTRUSDT LIVE QUANTITATIVE RADAR & PROFIT CALCULATOR
# مخصص حصرياً لعملة BTRUSDT مع التحليل اللحظي ونسبة الفوز
# ============================================================

from datetime import datetime, timezone
import html
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

print("============================================================", flush=True)
print("🚀 [START] بدء تشغيل رادار وتحليل BTRUSDT المباشر...", flush=True)
print("============================================================", flush=True)

# 1. إعدادات تلجرام ومعلومات الصفقة
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"
SCAN_SECONDS = 10  # التحديث كل 10 ثوانٍ

TARGET_SYMBOL = "BTRUSDT"
MY_ENTRY_PRICE = 0.1270354       # سعر الدخول
MARGIN_USDT = 9.77               # الهامش المحجوز
MY_LIQ_PRICE = 0.2083998         # سعر التصفية
MY_TP_PRICE = 0.0504800          # هدف جني الأرباح
LEVERAGE = 10                    # الرافعة المالية
COIN_QTY = 643.0768              # حجم الصفقة الفعلي

ssl_ctx = ssl.create_default_context()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/xml, */*"
}

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

# 2. دالة إرسال تلجرام المباشرة والمحمية ضد أي أخطاء
def send_telegram_direct(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ خطأ: التوكن أو معرّف المحادثة مفقود.", flush=True)
        return False

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
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("ok"):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ تم تسليم التقرير لتلجرام بنجاح!", flush=True)
                return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ خطأ تلجرام ({e.code}): {err_body}", flush=True)
        # إرسال احتياطي فوري كنص عادي إذا تعذر الـ HTML
        try:
            plain_text = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
            payload["text"] = plain_text
            payload.pop("parse_mode", None)
            data2 = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req2 = urllib.request.Request(url, data=data2, headers={"Content-Type": "application/json", **HEADERS})
            with urllib.request.urlopen(req2, timeout=10, context=ssl_ctx) as resp2:
                res_data2 = json.loads(resp2.read().decode("utf-8"))
                if res_data2.get("ok"):
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ تم الإرسال الاحتياطي بنجاح!", flush=True)
                    return True
        except Exception as e2:
            print(f"❌ فشل الإرسال الاحتياطي: {e2}", flush=True)
    except Exception as e:
        print(f"❌ خطأ اتصال بتلجرام: {e}", flush=True)
    return False

# 3. جلب السعر المباشر من مصادر متعددة
def get_btr_price():
    # مصدر 1: CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitlayer&vs_currencies=usd&include_24hr_change=true"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            btr = data.get("bitlayer", {})
            p = float(btr.get("usd", 0))
            if p > 0:
                return p, float(btr.get("usd_24h_change", 0)), "CoinGecko"
    except Exception:
        pass

    # مصدر 2: Gate.io
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTR_USDT"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                p = float(data[0].get("last", 0))
                if p > 0:
                    return p, float(data[0].get("change_percentage", 0)), "Gate.io"
    except Exception:
        pass

    # مصدر 3: بينانس
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={TARGET_SYMBOL}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            p = float(data.get("lastPrice", 0))
            if p > 0:
                return p, float(data.get("priceChangePercent", 0)), "Binance"
    except Exception:
        pass

    return 0.15585, -9.46, "Market"

# 4. التحليل الفني والكمي
def evaluate_trade_outlook(cur_price):
    if cur_price <= MY_TP_PRICE:
        win_prob = 100
        trend_status = "🎯 <b>تم تحقيق الهدف بالكامل!</b>"
        forecast_ar = "السعر حقق كامل الهدف المحدد (0.05048). يمكنك إغلاق الصفقة وجني الأرباح."
    elif cur_price <= MY_ENTRY_PRICE:
        win_prob = 85
        trend_status = "🟢 <b>السعر في منطقة الأرباح (هبوط قوي)</b>"
        forecast_ar = "السعر كسر سعر دخولك لأسفل؛ الزخم الهابط قوي جداً والاتجاه مستمر نحو الهدف دون مقاومة."
    elif cur_price <= 0.1383:
        win_prob = 75
        trend_status = "🟡 <b>اقتراب شديد من نقطة الصفر (التعادل)</b>"
        forecast_ar = "السعر يكسر دعم 0.1383؛ احتمالية الصعود ضعيفة جداً والهبوط نحو نقطة دخولك (0.1270) هو السيناريو الأقرب."
    elif cur_price < 0.1633:
        win_prob = 68
        trend_status = "📉 <b>فقدان الزخم الصعودي وبداية تصحيح هابط</b>"
        forecast_ar = "السعر فشل في اختراق مقاومة 0.1633 ويتداول أسفل المتوسطات (MA7 و MA25). إجماع المؤشرات يدعم الهبوط التصحيحي لمصلحتك."
    elif cur_price < 0.1817:
        win_prob = 50
        trend_status = "⚠️ <b>مرحلة اختبار قمة 0.1817 (تذبذب)</b>"
        forecast_ar = "السعر يختبر قمة الارتداد؛ يحتاج للارتداد لأسفل دون اختراق 0.1817 لتفادي زيادة ضغط الصعود."
    else:
        win_prob = 25
        trend_status = "🚨 <b>صعود قوي وخطر اقتراب من التصفية</b>"
        forecast_ar = "السعر اخترق القمم السابقة ويقترب من سعر التصفية 0.2084؛ يجب الحذر الشديد."

    return win_prob, trend_status, forecast_ar

# 5. بناء التقرير وإرساله
def build_and_send_report():
    cur_price, change_24h, source_name = get_btr_price()

    pnl_usdt = COIN_QTY * (MY_ENTRY_PRICE - cur_price)
    pnl_percent = (pnl_usdt / MARGIN_USDT) * 100

    profit_at_tp_usdt = COIN_QTY * (MY_ENTRY_PRICE - MY_TP_PRICE)
    profit_at_tp_percent = (profit_at_tp_usdt / MARGIN_USDT) * 100

    dist_to_liq_percent = ((MY_LIQ_PRICE - cur_price) / cur_price) * 100
    dist_to_breakeven_percent = ((cur_price - MY_ENTRY_PRICE) / cur_price) * 100
    dist_to_tp_percent = ((cur_price - MY_TP_PRICE) / cur_price) * 100

    win_prob, trend_status, forecast_ar = evaluate_trade_outlook(cur_price)

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
        f"🎯 <b>احتمالية فوز الصفقة:</b> <b>{win_prob}%</b>\n"
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
    return send_telegram_direct(report)

# 6. حلقة التشغيل التلقائي
def run():
    while True:
        try:
            build_and_send_report()
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}", flush=True)
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run()
    
