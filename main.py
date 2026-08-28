# ============================================================
# ABED LIVE 24/7 GLOBAL NEWS RADAR (بث الأخبار كل 30 ثانية)
# Real-Time Global Crypto & Finance News Feed
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

# إرسال خبر كل 30 ثانية
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
# 2) دالة إرسال الرسائل لتليجرام
# ============================================================
def send_telegram(text):
    try:
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
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response:
            response.read()
        print("✅ تم إرسال الخبر إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")
        return False

# ============================================================
# 3) محرك سحب الأخبار من المصادر الدولية
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
                    "body": a.get("body", "")[:160] + "..." if a.get("body") else ""
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
                        "body": desc[:160] + "..." if desc else ""
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


def get_next_news_bulletin():
    all_news = fetch_all_sources()
    if not all_news:
        return None

    # البحث عن أخبار جديدة لم تُرسل بعد
    fresh = [a for a in all_news if a["title"] not in sent_news_titles]
    
    if not fresh:
        sent_news_titles.clear()
        fresh = all_news

    # اختيار أحدث خبرين
    chosen = fresh[:2]
    for c in chosen:
        sent_news_titles.add(c["title"])

    formatted_items = []
    for art in chosen:
        item_text = (
            f"🌐 <b>مصدر الخبر:</b> <code>{art['source']}</code>\n"
            f"📌 <b>العنوان:</b> <b>{art['title']}</b>"
        )
        if art.get("body"):
            item_text += f"\n\n📝 <i>{art['body']}</i>"
        if art.get("url"):
            item_text += f"\n🔗 <a href='{art['url']}'>اضغط هنا لقراءة الخبر كاملاً</a>"
        formatted_items.append(item_text)

    bulletin = (
        f"🚨 <b>نشرة الأخبار العاجلة | رادار حكيم</b> 🚨\n\n"
        + "\n\n━━━━━━━━━━━━━━━━━━\n\n".join(formatted_items)
        + f"\n\n⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
    )
    return bulletin

# ============================================================
# 4) دورة البث الإخباري المستمر
# ============================================================
def run_news_stream():
    print("🚀 بدء تشغيل رادار الأخبار الحية كل 30 ثانية...")
    
    send_telegram(
        "🟢 <b>تم تفعيل رادار حكيم للأخبار العالمية!</b>\n\n"
        "📡 <i>ستصلك الآن نشرة بأحدث الأخبار والمستجدات الاقتصادية وأسواق الكريبتو كل 30 ثانية باستمرار.</i>"
    )
    
    while True:
        try:
            bulletin = get_next_news_bulletin()
            if bulletin:
                send_telegram(bulletin)
            else:
                send_telegram("📡 <b>رادار الأخبار:</b> جاري تحديث ومتابعة وكالات الأنباء العالمية...")
        except Exception as e:
            print(f"حدث خطأ أثناء البث: {e}")
            
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run_news_stream()
    
