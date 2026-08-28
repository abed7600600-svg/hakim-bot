import os
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ============================================================
# 1) بيانات تليجرام المباشرة
# ============================================================
BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"

BINANCE_FAPI = "https://fapi.binance.com"
SCAN_SECONDS = 30

# ============================================================
# 2) دالة الإرسال لتليجرام
# ============================================================
def send_telegram(text):
    try:
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
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("✅ تم إرسال التحديث إلى تليجرام")
        return True
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال تليجرام: {e}")
        return False

# ============================================================
# 3) جلب بيانات السوق من بينانس
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
# 4) الأخبار الأكثر رواجاً من CoinGecko
# ============================================================
def get_trending():
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        coins = data.get("coins", [])
        return ", ".join([f"#{c['item']['symbol']}" for c in coins[:5]])
    except Exception:
        return "#BTC, #ETH, #SOL, #BNB, #XRP"

# ============================================================
# 5) دورة البث المباشر
# ============================================================
def run_radar():
    print("🚀 بدء البث المباشر لرادار حكيم...")
    
    # رسالة فورية عند بدء التشغيل
    send_telegram(
        "🟢 <b>تم تفعيل رادار حكيم بنجاح!</b>\n"
        "📡 <i>ستصلك الآن رسائل السوق والأخبار كل 30 ثانية باستمرار.</i>"
    )
    
    while True:
        try:
            tickers = get_market_data()
            if tickers:
                by_chg = sorted(tickers, key=lambda x: x["change"], reverse=True)
                gainers = " | ".join([f"#{g['symbol'].replace('USDT','')}: +{g['change']:.1f}%" for g in by_chg[:3]])
                losers = " | ".join([f"#{l['symbol'].replace('USDT','')}: {l['change']:.1f}%" for l in by_chg[-3:]])
                
                btc_price = next((t["price"] for t in tickers if t["symbol"] == "BTCUSDT"), 0)
                trending = get_trending()
                
                msg = (
                    f"📡 <b>نبض السوق المباشر | رادار حكيم</b>\n\n"
                    f"🪙 <b>سعر البيتكوين (BTC):</b> <code>${btc_price:,.1f}</code>\n"
                    f"🔥 <b>الرائج عالمياً:</b> {trending}\n\n"
                    f"🚀 <b>الأعلى صعوداً الآن:</b>\n{gainers}\n\n"
                    f"🔻 <b>الأعلى هبوطاً الآن:</b>\n{losers}\n\n"
                    f"⏰ <b>التوقيت:</b> <code>{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}</code>"
                )
                send_telegram(msg)
            else:
                send_telegram("📡 <i>جاري فحص وتحديث بيانات منصة بينانس...</i>")
        except Exception as e:
            print(f"حدث خطأ: {e}")
            
        time.sleep(SCAN_SECONDS)

if __name__ == "__main__":
    run_radar()
    
