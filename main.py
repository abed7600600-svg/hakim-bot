# ============================================================
# ABED LIVE 24/7 ARABIC NEWS RADAR (أخبار عالمية مترجمة كل 30 ثانية)
# Real-Time Global Crypto & Finance News Translated to Arabic
# Sources: CoinDesk, CoinTelegraph, CryptoCompare, Decrypt
# ============================================================

from datetime import datetime, timezone
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import ssl
import os

# ============================================================
# 1) إعدادات التلجرام
# ============================================================
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"

# إرسال خبر مترجم كل 30 ثانية
SCAN_SECONDS = 30

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/xml, */*"
}

sent_news_titles = set()
news_archive = []

# ============================================================
# 2) دالة الترجمة التلقائية إلى اللغة العربية
# ============================================================
def translate_to_arabic(text):
    if not text or not text.strip():
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ar&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0 and data[0]:
                parts = [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                return "".join(parts)
        return text
    except Exception:
        return text

# ============================================================
# 3) دالة إرسال الرسائل لتليجرام
# ============================================================
def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
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
        print("✅ تم إرسال الخبر المترجم إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")
        return False

# ============================================================
# 4) محرك سحب الأخبار من الوكالات العالمية
# ============================================================
def fetch_all_sources():
    global news_archive
    articles = []

    # مصدر 1: CryptoCompare API
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for a in data.get("Data", []):
                articles.append({
                    "title": a.get("title", ""),
                    "source": a.get("source_info", {}).get("name", "CryptoNews"),
                    "url": a.get("url", ""),
                    "body": a.get("body", "")[:180] if a.get("body") else ""
                })
    except Exception:
        pass

    # مصدر 2: CoinDesk RSS
    try:
        url = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                if title:
                    articles.append({
                        "title": title,
                        "source": "CoinDesk",
                        "url": link,
                        "body": desc[:180] if desc else ""
                    })
    except Exception:
        pass

    # مصدر 3: CoinTelegraph RSS
    try:
        url = "https://cointelegraph.com/rss"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                if title:
                    articles.append({
                        "title": title,
                        "source": "CoinTelegraph",
                        "url": link,
                        "body": ""
                    })
    except Exception:
        pass

    if articles:
        news_archive = articles
    return news_archive

# ============================================================
# 5) تجهيز وترجمة النشرة الإخبارية
# ============================================================
def get_next_translated_bulletin():
    all_news = fetch_all_sources()
    if not all_news:
        return None

    # البحث عن أخبار لم تُرسل بعد
    fresh = [a for a in all_news if a["title"] not in sent_news_titles]
    
    if not fresh:
        sent_news_titles.clear()
        fresh = all_news

    # اختيار أحدث خبرين وترجمتهما فورياً
    chosen = fresh[:2]
    for c in chosen:
        sent_news_titles.add(c["title"])

    formatted_items = []
    for art in chosen:
        # ترجمة العنوان والملخص للعربية
        ar_title = translate_to_arabic(art["title"])
        ar_body = translate_to_arabic(art["body"]) if art.get("body") else ""

        item_text = (
            f"🌐 <b>المصدر:</b> <code>{art['source']}</code>\n"
            f"📌 <b>العنوان:</b> <b>{ar_title}</b>"
        )
        if ar_body:
            item_text += f"\n\n📝 <b>التفاصيل:</b> <i>{ar_body}</i>"
        if art.get("url"):
            item_text += f"\n🔗 <a href='{art['url']}'>اضغط هنا لقراءة المقال الأصلي</a>"
            
        formatted_items.append(item_text)

    bulletin = (
        f"🚨 <b>نشرة الأخبار العالمية المترجمة | رادار حكيم</b> 🚨\n\n"
        + "\n\n━━━━━━━━━━━━━━━━━━\n\n".join(formatted_items)
        + f"\n\n⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
    )
    return bulletin

# ============================================================
# 6) حلقة البث الإخباري المترجم المستمر
# ============================================================
def run_news_stream():
    print("🚀 بدء تشغيل رادار الأخبار العالمية المترجمة للعربية كل 30 ثانية...")
    
    send_telegram(
        "🟢 <b>تم تفعيل رادار الأخبار العالمية المترجمة للعربية!</b>\n\n"
        "📡 <i>ستصلك الآن أحدث الأخبار الاقتصادية والعملات الرقمية مترجمة بالكامل كل 30 ثانية باستمرار.</i>"
    )
    
    while True:
        try:
            bulletin = get_next_translated_bulletin()
            if bulletin:
                send_telegram(bulletin)
            else:
                send_telegram("📡 <b>رادار الأخبار:</b> جاري جلب وترجمة أحدث الأخبار العالمية...")
        except Exception as e:
            print(f"حدث خطأ أثناء البث: {e}")
            
