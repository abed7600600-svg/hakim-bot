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
    with urllib.request.urlopen(req, timeout=15) as r:
      print("Delivered to Telegram")
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
    "⚡ تم تفعيل رادار عبد الحكيم رائد اللحظي بنجاح!\nسيبدأ الآن تدفق التقارير"
    " وفحص الصفقات كل 25 إلى 30 ثانية..."
)

EXCLUDED = [
    "USDCUSDT",
    "FDUSDUSDT",
    "TUSDUSDT",
    "BUSDUSDT",
    "EURUSDT",
    "CREAMUSDT",
]
loop_count = 0

while True:
  loop_count += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  top_gainer_info = "جاري التحديث..."
  top_loser_info = "جاري التحديث..."
  top_vol_info = "جاري التحديث..."
  tickers = []

  # جلب بيانات بينانس مع روابط بديلة مضادة للحظر السحابي
  endpoints = [
      "https://data-api.binance.vision/api/v3/ticker/24hr",
      "https://api1.binance.com/api/v3/ticker/24hr",
      "https://api.binance.com/api/v3/ticker/24hr",
  ]
  for ep in endpoints:
    try:
      data = get_json(ep)
      if isinstance(data, list) and len(data) > 0:
        tickers = [
            t
            for t in data
            if t.get("symbol", "").endswith("USDT")
            and t.get("symbol") not in EXCLUDED
        ]
        if len(tickers) > 0:
          break
    except Exception:
      continue

  if len(tickers) > 0:
    try:
      by_change = sorted(
          tickers,
          key=lambda x: float(x.get("priceChangePercent", 0)),
          reverse=True,
      )
      by_volume = sorted(
          tickers, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True
      )

      g = by_change[0]
      l = by_change[-1]
      v = by_volume[0]

      top_gainer_info = (
          f"#{g['symbol']} (+{float(g['priceChangePercent']):.2f}%) | السعر:"
          f" {g['lastPrice']}"
      )
      top_loser_info = (
          f"#{l['symbol']} ({float(l['priceChangePercent']):.2f}%) | السعر:"
          f" {l['lastPrice']}"
      )
      top_vol_info = (
          f"#{v['symbol']} ({float(v['quoteVolume'])/1000000:.1f} مليون $)"
      )
    except Exception as e:
      print("Sort error:", e)

  # إرسال التقرير اللحظي السريع
  market_msg = (
      "📊 رادار عبد الحكيم رائد | التقرير اللحظي للسوق\n"
      "━━━━━━━━━━━━━━━━━━\n"
      f"⏱ التوقيت: {now_str} (تحديث #{loop_count})\n\n"
      f"🔥 أعلى عملة صاعدة: {top_gainer_info}\n\n"
      f"📉 أكبر عملة هابطة: {top_loser_info}\n\n"
      f"💰 أعلى سيولة بالسوق: {top_vol_info}\n"
      "━━━━━━━━━━━━━━━━━━\n"
      "🔍 فحص مستمر لصفقات الشورت في بينانس..."
  )
  send_telegram(market_msg)

  # فحص صفقات الشورت لأعلى العملات الصاعدة
  if len(tickers) > 0:
    for t in by_change[:6]:
      sym = t["symbol"]
      change = float(t.get("priceChangePercent", 0))
      if change >= 5.0:
        try:
          klines = get_json(
              "https://data-api.binance.vision/api/v3/klines?symbol="
              + sym
              + "&interval=15m&limit=50"
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
                  "🚨 إشارة شورت مؤكدة (Signal Alert) 🚨\n👑 منظومة عبد الحكيم"
                  f" رائد للتحليل\n━━━━━━━━━━━━━━━━━━\n📌 العملة:"
                  f" {sym}\n📈 نسبة الصعود: +{pump:.1f}%\n📊 مؤشر RSI:"
                  f" {rsi_val:.1f}\n🌊 تدفق الفوليوم: {v_spike:.1f}x ضعف"
                  " المعدل\n━━━━━━━━━━━━━━━━━━\n💰 سعر الدخول المقترح:"
                  f" {last_c}\n🛑 وقف الخسارة (SL): {sl}\n🎯 الهدف الأول:"
                  f" {tp1}\n🎯 الهدف الثاني: {tp2}\n━━━━━━━━━━━━━━━━━━\n💡"
                  " نصيحة عبد الحكيم: الدخول بـ 1-2% فقط مع رافعة 3x-5x وتأمين"
                  " الصفقة عند الهدف الأول."
              )
              send_telegram(sig_msg)
              break
        except Exception:
          continue

  time.sleep(25)
    
