from datetime import datetime, timezone
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
import html
import ssl

BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"
SCAN_SECONDS = 10

TARGET_SYMBOL = "BTRUSDT"
MY_ENTRY_PRICE = 0.1270354
POSITION_SIZE_USDT = 98.18
MARGIN_USDT = 9.77
MY_LIQ_PRICE = 0.2083998
MY_TP_PRICE = 0.0504800
LEVERAGE = 10

COIN_QTY = POSITION_SIZE_USDT / MY_ENTRY_PRICE

ssl_ctx = ssl.create_default_context()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/xml, */*"
}

def escape_html(text):
    if not text:
        return ""
    return html.escape(str(text))

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ خطأ: BOT_TOKEN أو CHAT_ID غير محدد.")
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
        headers={"Content-Type": "application/json", **HEADERS}
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response:
            response.read()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ تم إرسال التقرير لتليجرام بنجاح")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"❌ خطأ تليجرام ({e.code}): {error_body}")
        return False
    except Exception as e:
        print(f"❌ خطأ اتصال تليجرام: {e}")
        return False

def get_btr_live():
    try:
        url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={TARGET_SYMBOL}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "price": float(data.get("lastPrice", 0)),
                "change": float(data.get("priceChangePercent", 0)),
                "high": float(data.get("highPrice", 0)),
                "low": float(data.get("lowPrice", 0)),
                "volume": float(data.get("quoteVolume", 0))
            }
    except Exception as e:
        print(f"❌ خطأ جلب سعر بينانس: {e}")
        return None

def get_btr_klines():
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={TARGET_SYMBOL}&interval=15m&limit=40"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
            klines = json.loads(resp.read().decode("utf-8"))
            return [float(k[4]) for k in klines]
    except Exception as e:
        print(f"⚠️ خطأ جلب الشموع (سيتم تخطي RSI): {e}")
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

def get_latest_news():
    try:
        url = "https://ar.cointelegraph.com/rss"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            item = root.find(".//item")
            if item is not None:
                title = item.find("title").text if item.find("title") is not None else ""
                return escape_html(title.strip())
    except Exception as e:
        print(f"⚠️ خطأ جلب الأخبار: {e}")
    return "حركة السوق مستقرة بانتظار السيولة."

def build_live_pnl_report():
    data = get_btr_live()
    if not data:
        return None

    cur_price = data["price"]
    closes = get_btr_klines()
    rsi_val = calculate_rsi(closes) if closes else 50.0

    pnl_usdt = COIN_QTY * (MY_ENTRY_PRICE - cur_price)
    pnl_percent = (pnl_usdt / MARGIN_USDT) * 100

    profit_at_tp_usdt = COIN_QTY * (MY_ENTRY_PRICE - MY_TP_PRICE)
    profit_at_tp_percent = (profit_at_tp_usdt / MARGIN_USDT) * 100

    dist_to_liq_percent = ((MY_LIQ_PRICE - cur_price) / cur_price) * 100
    dist_to_breakeven_percent = ((cur_price - MY_ENTRY_PRICE) / cur_price) * 100

    if pnl_usdt >= 0:
        pnl_display = f"🟢 <b>ربح حالي:</b> <code>+{pnl_usdt:.2f} USDT</code> (<code>+{pnl_percent:.1f}%</code>)"
        status_banner = "🎉 <b>أنت في منطقة الأرباح الآن!</b>"
    else:
        pnl_display = f"🔴 <b>خسارة عائمة:</b> <code>{pnl_usdt:.2f} USDT</code> (<code>{pnl_percent:.1f}%</code>)"
        status_banner = "⏳ <b>في انتظار ارتداد السعر لأسفل نحو الدخول...</b>"

    if rsi_val > 65:
        rsi_status = "تشبع شرائي 🟢 (السعر جاهز للهبوط لمصلحتك)"
    elif rsi_val < 35:
        rsi_status = "تشبع بيعي 🔴 (ضغط شراء مؤقت ضدك)"
    else:
        rsi_status = "حركة متوازنة ⚪"

    if cur_price <= MY_ENTRY_PRICE:
        forecast_text = "🚀 السعر الآن أسفل نقطة دخولك وبدأ في تحقيق الأرباح نحو الأهداف!"
    elif cur_price > 0.163:
        forecast_text = "⚠️ السعر يختبر مقاومة 0.163، يحتاج للهبوط تحت 0.138 لتسريع الوصول لأرباحك."
    else:
        forecast_text = "📉 السعر يتراجع نحو نقطة دخولك (0.1270). بمجرد كسرها تبدأ الأرباح."

    news_title = get_latest_news()

    report = (
        f"📊 <b>رادار الأرباح المباشر | BTRUSDT (صفقة SHORT 10x)</b>\n\n"
        f"{status_banner}\n\n"
        f"💰 {pnl_display}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>السعر اللحظي:</b> <code>${cur_price:.5f}</code> ({data['change']:+.2f}%)\n"
        f"🎯 <b>سعر دخولك (التعادل):</b> <code>${MY_ENTRY_PRICE:.5f}</code>\n"
        f"📏 <b>المسافة للتعادل والربح:</b> <code>-{dist_to_breakeven_percent:.1f}%</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>الربح عند الهدف (0.05048):</b>\n"
        f"💵 <b>صافي الربح المتوقع:</b> <code>+{profit_at_tp_usdt:.2f} USDT</code> (<b>+{profit_at_tp_percent:.1f}%</b> 🔥)\n\n"
        f"🛡️ <b>سعر التصفية (Liquidation):</b> <code>${MY_LIQ_PRICE:.5f}</code>\n"
        f"🛡️ <b>المسافة الآمنة للتصفية:</b> <code>+{dist_to_liq_percent:.1f}%</code> صعوداً\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔮 <b>التحليل الفني والزخم:</b>\n"
        f"• <b>مؤشر RSI:</b> <code>{rsi_val:.1f}</code> ({rsi_status})\n"
        f"• <b>التوقع المباشر:</b> {forecast_text}\n\n"
        f"📰 <b>آخر خبر:</b> {news_title}\n"
        f"⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
    )
    return report

def run_live_pnl_bot():
    print("🚀 بدء المتابعة الحية لصفقة BTR...")
    send_telegram(
        "🟢 <b>تم تفعيل رادار الأرباح اللحظية لعملة BTRUSDT!</b>\n\n"
        "📡 <i>ستصلك الآن الأرباح والخسائر بالدولار والنسبة بدقة متناهية.</i>"
    )
    while True:
        try:
            msg = build_live_pnl_report()
            if msg:
                send_telegram(msg)
            else:
                print("⚠️ تعذر إنشاء التقرير في هذه الدورة.")
        except Exception as e:
            print(f"❌ خطأ أثناء التحديث: {e}")
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_live_pnl_bot()
    
