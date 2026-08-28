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


send_telegram(
    "⚡ تم تفعيل رادار عبد الحكيم رائد اللحظي بنجاح!\nسيبدأ الآن بث التقرير"
    " وفحص الصفقات كل 25 ثانية بشكل مستمر..."
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

  top_g_txt = "جاري الرصد..."
  top_l_txt = "جاري الرصد..."
  top_v_txt = "جاري الرصد..."
  tickers = []

  # جلب بيانات بينانس عبر السيرفر السحابي المفتوح Binance Vision
  endpoints = [
      "https://data-api.binance.vision/api/v3/ticker/24hr",
      "https://api1.binance.com/api/v3/ticker/24hr",
      "https://api2.binance.com/api/v3/ticker/24hr",
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
            and float(t.get("quoteVolume", 0)) > 500000
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
      by_vol = sorted(
          tickers, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True
      )

      g = by_change[0]
      l = by_change[-1]
      v = by_vol[0]

      top_g_txt = (
          f"#{g['symbol']} (+{float(g['priceChangePercent']):.2f}%) | السعر:"
          f" {g['lastPrice']}"
      )
      top_l_txt = (
          f"#{l['symbol']} ({float(l['priceChangePercent']):.2f}%) | السعر:"
          f" {l['lastPrice']}"
      )
      top_v_txt = (
          f"#{v['symbol']} ({float(v['quoteVolume'])/1000000:.1f} مليون $)"
      )
    except Exception as e:
      print("Sort Error:", e)

  # إرسال التقرير اللحظي المؤكد كل دورة
  msg = (
      "📊 رادار عبد الحكيم رائد | التقرير اللحظي للسوق\n"
      "━━━━━━━━━━━━━━━━━━\n"
      f"⏱ التوقيت: {now_str} (تحديث #{loop_count})\n\n"
      f"🔥 أعلى عملة صاعدة: {top_g_txt}\n\n"
      f"📉 أكبر عملة هابطة: {top_l_txt}\n\n"
      f"💰 أعلى سيولة بالسوق: {top_v_txt}\n"
      "━━━━━━━━━━━━━━━━━━\n"
      "🔍 جاري فحص صفقات الشورت لجميع العملات..."
  )
  send_telegram(msg)

  # فحص صفقات الشورت لأعلى العملات صعوداً
  if len(tickers) > 0:
    for t in by_change[:5]:
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
          body = abs(last_c - last_o)
          wick = last_h - max(last_o, last_c)

          if pump >= 5.0 and v_spike >= 1.3:
            if wick > (body * 0.3) or (last_c < last_h * 0.985):
              sl = round(last_h * 1.015, 4)
              tp1 = round(last_c - (last_h - past_c) * 0.382, 4)
              tp2 = round(last_c - (last_h - past_c) * 0.50, 4)

              sig_msg = (
                  "🚨 إشارة شورت مؤكدة (Signal Alert) 🚨\n👑 منظومة عبد الحكيم"
                  f" رائد للتحليل\n━━━━━━━━━━━━━━━━━━\n📌 العملة:"
                  f" {sym}\n📈 نسبة الصعود: +{pump:.1f}%\n🌊 تدفق الفوليوم:"
                  f" {v_spike:.1f}x ضعف المعدل\n━━━━━━━━━━━━━━━━━━\n💰 سعر"
                  f" الدخول المقترح: {last_c}\n🛑 وقف الخسارة (SL):"
                  f" {sl}\n🎯 الهدف الأول: {tp1}\n🎯 الهدف الثاني:"
                  f" {tp2}\n━━━━━━━━━━━━━━━━━━\n💡 نصيحة عبد الحكيم: الدخول"
                  " بـ 1-2% مع رافعة 3x-5x وتأمين الصفقة عند الهدف الأول."
              )
              send_telegram(sig_msg)
              break
        except Exception:
          continue

  time.sleep(25)
  
