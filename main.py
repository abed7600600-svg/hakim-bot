# ============================================================
# ABED LIVE 24/7 ARABIC CRYPTO & MARKET NEWS RADAR
# مصادر إخبارية عربية أصلية + عالمية مترجمة
# Sources: Cointelegraph Arabic, BeInCrypto Arabic, Investing.com Arabic
# ============================================================

from datetime import datetime, timezone
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import ssl
import os

# ============================================================
# 1) إعدادات التلجرام
# ============================================================
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"

# الفاصل الزمني (كل 30 ثانية)
SCAN_SECONDS = 30

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8"
}

sent_titles = set()
news_archive = []

def clean_html(raw_html):
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.replace('&quot;', '"').replace('&amp;', '&').replace('&nbsp;', ' ').strip()

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
        print("✅ تم إرسال الخبر العربي بنجاح إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")
        return False

# ============================================================
# 2) جلب الأخبار من كبرى المصادر العربية
# ============================================================
def fetch_arabic_news():
    global news_archive
    articles = []

    # مصدر 1: كوينتيليغراف عربي (Cointelegraph Arabic)
    try:
        url = "https://ar.cointelegraph.com/rss"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                if title:
                    articles.append({
                        "title": clean_html(title),
                        "source": "كوينتيليغراف عربي (Cointelegraph AR)",
                        "url": link.strip() if link else "",
                        "body": clean_html(desc)[:160] + "..." if desc else ""
                    })
    except Exception:
        pass

    # مصدر 2: بي إن كريبتو بالعربية (BeInCrypto Arabic)
    try:
        url = "https://ar.beincrypto.com/feed/"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                if title:
                    articles.append({
                        "title": clean_html(title),
                        "source": "بي إن كريبتو (BeInCrypto AR)",
                        "url": link.strip() if link else "",
                        "body": clean_html(desc)[:160] + "..." if desc else ""
                    })
    except Exception:
        pass

    # مصدر 3: Investing.com بالعربية (العملات الرقمية والأسواق)
    try:
        url = "https://sa.investing.com/rss/news_25.rss"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=7, context=ssl_ctx) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                if title:
                    articles.append({
                        "title": clean_html(title),
                        "source": "إنفستنج بالعربية (Investing AR)",
                        "url": link.strip() if link else "",
                        "body": ""
                    })
    except Exception:
        pass

    # في حال هدوء المصادر العربية، نجلب الأخبار العالمية ونترجمها فورياً
    if not articles:
        try:
            url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for a in data.get("Data", []):
                    ar_t = translate_to_arabic(a.get("title", ""))
                    ar_b = translate_to_arabic(a.get("body", "")[:150])
                    articles.append({
                        "title": ar_t,
                        "source": f"أخبار عالمية ({a.get('source_info', {}).get('name', 'Global')})",
                        "url": a.get("url", ""),
                        "body": ar_b + "..." if ar_b else ""
                    })
        except Exception:
            pass

    if articles:
        news_archive = articles
    return news_archive

# ============================================================
# 3) تجهيز النشرة الإخبارية العربية
# ============================================================
def get_next_arabic_news():
    all_news = fetch_arabic_news()
    if not all_news:
        return None

    # فرز الأخبار الجديدة التي لم ترسل بعد
    fresh = [a for a in all_news if a["title"] not in sent_titles]
    if not fresh:
        sent_titles.clear()
        fresh = all_news

    chosen = fresh[:2]
    for c in chosen:
        sent_titles.add(c["title"])

    formatted_items = []
    for art in chosen:
        item_text = (
            f"📰 <b>المصدر:</b> <code>{art['source']}</code>\n"
            f"📌 <b>العنوان:</b> <b>{art['title']}</b>"
        )
        if art.get("body"):
            item_text += f"\n\n📝 <b>التفاصيل:</b> <i>{art['body']}</i>"
        if art.get("url"):
            item_text += f"\n🔗 <a href='{art['url']}'>اضغط هنا لقراءة الخبر كاملاً</a>"
            
        formatted_items.append(item_text)

    bulletin = (
        f"🚨 <b>رادار الأخبار العربية والعالمية المباشرة</b> 🚨\n\n"
        + "\n\n━━━━━━━━━━━━━━━━━━\n\n".join(formatted_items)
        + f"\n\n⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
    )
    return bulletin

# ============================================================
# 4) حلقة البث المباشر
# ============================================================
def run_arabic_news_stream():
    print("🚀 بدء تشغيل رادار الأخبار العربية المباشرة كل 30 ثانية...")
    
    send_telegram(
        "🟢 <b>تم تفعيل رادار الأخبار العربية للعملات والأسواق المالية!</b>\n\n"
        "📡 <i>المصادر: Cointelegraph Arabic, BeInCrypto Arabic, Investing.com Arabic</i>\n"
        "ستصلك الآن نشرة الأخبار باللغة العربية كل 30 ثانية باستمرار."
    )
    
    while True:
        try:
            bulletin = get_next_arabic_news()
            if bulletin:
                send_telegram(bulletin)
            else:
                send_telegram("📡 <b>رادار الأخبار:</b> جاري متابعة وتحديث وكالات الأنباء العربية...")
        except Exception as e:
            print(f"حدث خطأ أثناء البث: {e}")
            
        time.sleep(SCAN_SECONDS)


if __name__ == "__main__":
    run_arabic_news_stream()
    
