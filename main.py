import json
import time
import urllib.parse
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
      print("Sent to Telegram successfully")
  except Exception as e:
    print("Telegram Error:", e)


def get_json(url):
  req = urllib.request.Request(
      url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
  )
  with urllib.request.urlopen(req, timeout=15) as r:
    return json.loads(r.read().decode("utf-8"))


def translate_to_ar(text):
  try:
    q = urllib.parse.quote(text[:250])
    url = (
        "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ar&dt=t&q="
        + q
    )
    res = get_json(url)
    return "".join([i[0] for i in res[0] if i[0]])
  except Exception:
    return text


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


# رسالة فورية للتأكيد عند بدء التشغيل
send_telegram(
    "🔥 تم تشغيل منظومة عبد الحكيم رائد السحابية بنجاح!\nجاري الآن بث الأخبار"
    " وفحص صفقات السوق كل 30 ثانية..."
)

news_idx = 0
loop_count = 0

while loop_count < 300:
  loop_count += 1
  print(f"Cycle {loop_count} running...")

  # 1. جلب وبث الأخبار العالمية المترجمة
  try:
    news_data = get_json(
        "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    )
    if "Data" in news_data and len(news_data["Data"]) > 0:
      item = news_data["Data"][news_idx % len(news_data["Data"])]
      source = item.get("source_info", {}).get("name", "Crypto News")
      t_en = item.get("title", "")
      b_en = item.get("body", "")[:130] + "..."
      link = item.get("url", "")

      t_ar = translate_to_ar(t_en)
      b_ar = translate_to_ar(b_en)

      msg = (
          "📰 خبر عاجل | رادار عبد الحكيم رائد\n━━━━━━━━━━━━━━━━━━\n🌐 المصدر:"
          f" {source}\n\n📌 العنوان: {t_ar}\n\n📝 التفاصيل:"
          f" {b_ar}\n━━━━━━━━━━━━━━━━━━\n🔗 الرابط: {link}"
      )
      send_telegram(msg)
      news_idx += 1
  except Exception as e:
    print("News error:", e)

  time.sleep(15)

  # 2. فحص صفقات بينانس
  try:
    tickers = get_json("https://fapi.binance.com/fapi/v1/ticker/24hr")
    for t in tickers:
      sym = t.get("symbol", "")
      if sym.endswith("USDT") and float(t.get("priceChangePercent", 0)) >= 5.0:
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
                  "🚨 فرصة شورت مؤكدة (Signal Alert) 🚨\n👑 منظومة عبد الحكيم"
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
    print("Scan error:", e)

  time.sleep(15)
  
