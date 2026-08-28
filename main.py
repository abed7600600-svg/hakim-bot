# ============================================================
# ABED LIVE RADAR & GLOBAL CRYPTO NEWS STREAM
# Binance USD-M Futures + Real-Time Global Crypto News
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

SCAN_SECONDS = 30
BINANCE_FAPI = "https://fapi.binance.com"

# ============================================================
# 2) دالة الإرسال لتليجرام
# ============================================================
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
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("✅ تم إرسال التحديث والأخبار إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")
        return False

# ============================================================
# 3) جلب أحدث الأخبار العالمية والعاجلة (Crypto News Feed)
# ============================================================
def get_crypto_news():
    try:
        # واجهة الأخبار العالمية المباشرة (CoinDesk, Cointelegraph, Decrypt...)
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            articles = data.get("Data", [])
            news_items = []
            for art in articles[:2]:  # جلب أحدث خبرين عاجلين
                title = art.get("title", "")
                source = art.get("source_info", {}).get("name", "News")
                news_items.append(f"📰 <b>[{source}]:</b> {title}")
            return "\n\n".join(news_items) if news_items else "• السوق هادئ ولا توجد أخبار عاجلة."
    except Exception:
        return "• جاري متابعة وتحديث رادار الأخبار العالمية..."

# ============================================================
# 4) جلب بيانات أسعار السوق من بينانس
# ============================================================
def get_market_data():
    try:
        url = f"{BINANCE_FAPI}/fapi/v1/ticker/24hr"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        valid = []
        for t in data:
            sym = t.get("symbol", "")
            if sym.endswith("USDT") and not sym.startswith(("USDC", "FDUSD", "TUSD", "BUSD")):
                try:
                    vol = float(t.get("quoteVolume", 0))
                    chg = float(t.get("priceChangePercent", 0))
                    price = float(t.get("lastPrice", 0))
                    valid.append({"symbol": sym, "volume": vol, "change": chg, "price": price})
                except Exception:
                    continue
        
        valid.sort(key=lambda x: x["volume"], reverse=True)
        return valid
    except Exception as e:
        print(f"❌ خطأ بينانس: {e}")
        return []

# ============================================================
# 5) حلقة البث المباشر للأخبار والسوق
# ============================================================
def run_radar():
    print("🚀 بدء تشغيل رادار الأخبار والسوق المباشر...")
    
    send_telegram(
        "🟢 <b>تم تفعيل رادار حكيم الإخباري والفني بنجاح!</b>\n\n"
        "📡 <i>ستصلك الآن أحدث الأخبار العالمية وعناوين الكريبتو مع أسعار السوق كل 30 ثانية باستمرار.</i>"
    )
    
    while True:
        try:
            tickers = get_market_data()
            news_text = get_crypto_news()
            
            if tickers:
                by_chg = sorted(tickers, key=lambda x: x["change"], reverse=True)
                gainers = " | ".join([f"#{g['symbol'].replace('USDT','')}: +{g['change']:.1f}%" for g in by_chg[:3]])
                losers = " | ".join([f"#{l['symbol'].replace('USDT','')}: {l['change']:.1f}%" for l in by_chg[-3:]])
                btc_price = next((t["price"] for t in tickers if t["symbol"] == "BTCUSDT"), 0)
                
                msg = (
                    f"📡 <b>رادار حكيم | نشرة الأخبار والأسواق المباشرة</b>\n\n"
                    f"🪙 <b>سعر البيتكوين (BTC):</b> <code>${btc_price:,.1f}</code>\n\n"
                    f"🚀 <b>الأعلى صعوداً الآن:</b>\n{gainers}\n\n"
                    f"🔻 <b>الأعلى هبوطاً الآن:</b>\n{losers}\n\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🌐 <b>أحدث الأخبار العالمية العاجلة:</b>\n\n"
                    f"{news_text}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
                )
                send_telegram(msg)
            else:
                send_telegram(f"📡 <b>نشرة الأخبار العالمية:</b>\n\n{news_text}")
                
        except Exception as e:
            print(f"حدث خطأ: {e}")
            
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_radar()
    
