from datetime import datetime
import json
import time
import urllib.request

BOT_TOKEN = "8641484254:AAGs6MFyxo52A_Y2bkznogpZ9-s9g6NbjXk"
CHAT_ID = "8493446835"


def send_telegram(text):
  url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
  data = json.dumps({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
  req = urllib.request.Request(
      url, data=data, headers={"Content-Type": "application/json"}
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as r:
      print("Delivered")
  except Exception as e:
    print("Telegram Error:", e)


def get_json(url):
  req = urllib.request.Request(
      url,
      headers={
          "User-Agent": (
              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          )
      },
  )
  with urllib.request.urlopen(req, timeout=10) as r:
    return json.loads(r.read().decode("utf-8"))


def calculate_rsi(closes, period=14):
  if len(closes) < period + 1:
    return 50
  deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
  gains = [d if d > 0 else 0 for d in deltas]
  losses = [-d if d < 0 else 0 for d in deltas]
  avg_gain = sum(gains[:period]) / period
  avg_loss = sum(losses[:period]) / period
  for i in range(period, len(deltas)):
    avg_gain = (avg_gain * (period - 1) + gains[i]) / period
    avg_loss = (avg_loss * (period - 1) + losses[i]) / period
  if avg_loss == 0:
    return 100
  return 100 - (100 / (1 + (avg_gain / avg_loss)))


send_telegram(
    "⚡ تم تفعيل رادار العقود الآجلة السريع بنجاح!\n(Binance Futures"
    " 24/7)\nسيبدأ الآن تدفق التقارير والصفقات كل 25 إلى 30 ثانية..."
)

EXCLUDED = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "EURUSDT"]
loop_count = 0

while True:
  loop_count += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  try:
    data = get_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    if isinstance(data, list) and len(data) > 0:
      futures_tickers = [
          t
          for t in data
          if t.get("symbol", "").endswith("USDT")
          and t.get("symbol") not in EXCLUDED
      ]

      by_change = sorted(
          futures_tickers,
          key=lambda x: float(x.get("priceChangePercent", 0)),
          reverse=True,
      )
      by_volume = sorted(
          futures_tickers,
          key=lambda x: float(x.get("quoteVolume", 0)),
          reverse=True,
      )

      g = by_change[0]
      l = by_change[-1]
      v = by_volume[0]

      g_info = (
          f"#{g['symbol']} (+{float(g['priceChangePercent']):.2f}%) | السعر:"
          f" {g['lastPrice']}"
      )
      l_info = (
          f"#{l['symbol']} ({float(l['priceChangePercent']):.2f}%) | السعر:"
          f" {l['lastPrice']}"
      )
      v_info = f"#{v['symbol']} ({float(v['quoteVolume'])/1000000:.1f} مليون $)"

      # إرسال التقرير اللحظي السريع
      market_msg = (
          "📊 رادار عبد الحكيم رائد | نبض العقود الآجلة (Futures)\n"
          "━━━━━━━━━━━━━━━━━━\n"
          f"⏱ التوقيت: {now_str} (تحديث #{loop_count})\n\n"
          f"🔥 أعلى عملة عقود صاعدة: {g_info}\n\n"
          f"📉 أكبر عملة عقود هابطة: {l_info}\n\n"
          f"💰 أعلى سيولة عقود: {v_info}\n"
          "━━━━━━━━━━━━━━━━━━\n"
          "🔍 فحص مستمر لصفقات الشورت في بينانس..."
      )
      send_telegram(market_msg)

      # فحص إشارات الشورت لأعلى 5 عملات صاعدة
      for t in by_change[:5]:
        sym = t["symbol"]
        change = float(t.get("priceChangePercent", 0))
        if change >= 5.0:
          try:
            klines = get_json(
                f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=15m&limit=50"
            )
            if len(klines) < 50:
              continue
            opens = [float(k[1]) for k in klines]
            highs = [float(k[2]) for k in klines]
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]

            last_o, last_h, last_c = opens[-1], highs[-1], closes[-1]
            last_v = vols[-1]
            past_c = closes[-8]
            pump = ((last_h - past_c) / past_c) * 100
            avg_v = sum(volumes[-20:-1]) / 19
            v_spike = last_v / avg_v if avg_v > 0 else 1
            rsi_val = calculate_rsi(closes)
            body = abs(last_c - last_o)
            wick = last_h - max(last_o, last_c)

            if pump >= 5.0 and v_spike >= 1.3 and rsi_val >= 68:
              if wick > (body * 0.3) or (last_c < last_h * 0.985):
                sl = round(last_h * 1.015, 4)
                tp1 = round(last_c - (last_h - past_c) * 0.382, 4)
                tp2 = round(last_c - (last_h - past_c) * 0.50, 4)

                sig_msg = (
                    "🚨 إشارة شورت في العقود الآجلة (Futures Alert) 🚨\n"
                    "👑 منظومة عبد الحكيم رائد للتحليل\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"📌 العملة: {sym}\n"
                    f"📈 نسبة الصعود: +{pump:.1f}%\n"
                    f"📊 مؤشر RSI: {rsi_val:.1f}\n"
                    f"🌊 تدفق الفوليوم: {v_spike:.1f}x ضعف المعدل\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"💰 سعر الدخول المقترح: {last_c}\n"
                    f"🛑 وقف الخسارة (SL): {sl}\n"
                    f"🎯 الهدف الأول: {tp1}\n"
                    f"🎯 الهدف الثاني: {tp2}\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "💡 نصيحة عبد الحكيم: افتح صفقة Short في قسم العقود الآجلة"
                    " برافعة 3x-5x ومخاطرة 1-2% فقط."
                )
                send_telegram(sig_msg)
                break
          except Exception:
            continue
  except Exception as e:
    print(f"Error: {e}")

  time.sleep(25)
            
