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
      print("Message sent to Telegram")
  except Exception as e:
    print("Telegram Error:", e)


def get_json(url):
  req = urllib.request.Request(
      url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
  )
  with urllib.request.urlopen(req, timeout=15) as r:
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
    "🔥 تم تفعيل رادار عبد الحكيم رائد اللحظي بنجاح!\nسيبدأ الآن إرسال نبضات"
    " السوق والصفقات كل 30 ثانية بدون أي توقف..."
)

loop_count = 0

while loop_count < 300:
  loop_count += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  try:
    # جلب جميع بيانات عقود بينانس الآجلة اللحظية
    tickers = get_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    usdt_tickers = [t for t in tickers if t["symbol"].endswith("USDT")]

    # ترتيب العملات حسب نسبة التغير والسيولة
    by_change = sorted(
        usdt_tickers, key=lambda x: float(x["priceChangePercent"]), reverse=True
    )
    by_volume = sorted(
        usdt_tickers, key=lambda x: float(x["quoteVolume"]), reverse=True
    )

    top_gainer = by_change[0]
    top_loser = by_change[-1]
    top_volume = by_volume[0]

    g_sym = top_gainer["symbol"]
    g_change = float(top_gainer["priceChangePercent"])
    g_price = float(top_gainer["lastPrice"])

    l_sym = top_loser["symbol"]
    l_change = float(top_loser["priceChangePercent"])
    l_price = float(top_loser["lastPrice"])

    v_sym = top_volume["symbol"]
    v_vol = float(top_volume["quoteVolume"]) / 1000000  # تحويل للمليون دولار

    # رسالة النبض اللحظي لكل 30 ثانية
    market_msg = (
        "📊 رادار عبد الحكيم رائد | التقرير اللحظي للسوق\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⏱ التوقيت: {now_str} (دورة #{loop_count})\n\n"
        f"🔥 أعلى عملة صاعدة: #{g_sym}\n"
        f"📈 نسبة الصعود: +{g_change:.2f}% | السعر: {g_price}\n\n"
        f"📉 أكبر عملة هابطة: #{l_sym}\n"
        f"🔻 نسبة الهبوط: {l_change:.2f}% | السعر: {l_price}\n\n"
        f"💰 أعلى سيولة بالسوق: #{v_sym} ({v_vol:.1f} مليون $)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔍 الرادار يفحص الآن كل العملات لرصد صفقات الشورت..."
    )
    send_telegram(market_msg)

    # فحص صفقات الشورت الفنية
    for t in by_change[:15]:
      sym = t["symbol"]
      change = float(t["priceChangePercent"])
      if change >= 5.0:
        try:
          klines = get_json(
              "https://fapi.binance.com/fapi/v1/klines?symbol="
              + sym
              + "&interval=15m&limit=50"
          )
          if len(klines) < 50:
            continue
          opens = [float(k[1]) for k in klines]
          highs = [float(k[2]) for k in klines]
          closes = [float(k[4]) for k in klines]
          vols = [float(k[5]) for k in klines]

          last_o, last_h, last_c = opens[-1], highs[-1], closes[-1]
          last_v = vols[-1]
          past_c = closes[-8]
          pump = ((last_h - past_c) / past_c) * 100
          avg_v = sum(vols[-20:-1]) / 19
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
              time.sleep(2)
              break
        except Exception:
          continue

  except Exception as e:
    print("Market Scan Error:", e)

  time.sleep(30)
  
