from datetime import datetime
import json
import time
import urllib.parse
import urllib.request

# ==========================================
# رادار عبد الحكيم رائد - البث المتواصل 24/7
# ==========================================
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
      pass
  except Exception as e:
    print(f"Telegram Error: {e}")


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
    "🚀 تم تشغيل منظومة عبد الحكيم رائد الشاملة بنجاح!\n(أخبار + صفقات شراء +"
    " صفقات بيع + نصائح كل 10 ثوانٍ)..."
)

EXCLUDED = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "EURUSDT"]
news_idx = 0
step_counter = 0

while True:
  step_counter += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  # ==========================================
  # 1. إرسال خبر عاجل مترجم (كل دورة بالتناوب)
  # ==========================================
  if step_counter % 3 == 1:
    try:
      news_data = get_json(
          "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
      )
      if "Data" in news_data and len(news_data["Data"]) > 0:
        item = news_data["Data"][news_idx % len(news_data["Data"])]
        source = item.get("source_info", {}).get("name", "Global Media")
        t_en = item.get("title", "")
        b_en = item.get("body", "")[:130] + "..."
        link = item.get("url", "")

        news_msg = (
            "📰 [هذا خبر عاجل في سوق الكريبتو] 📰\n"
            "👑 منظومة عبد الحكيم رائد للرصد الشامل\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🌐 المصدر: {source} | ⏱ {now_str}\n\n"
            f"📌 العنوان: {t_en}\n\n"
            f"📝 التفاصيل: {b_en}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🔗 المصدر: {link}\n\n"
            "💡 نصيحة عبد الحكيم: تابع الأخبار العالمية وتأثيرها على السيولة"
            " قبل دخول أي صفقة برافعة مالية."
        )
        send_telegram(news_msg)
        news_idx += 1
    except Exception as e:
      print("News error:", e)

  # ==========================================
  # 2. فحص وإرسال صفقات الشراء والبيع والتقرير
  # ==========================================
  else:
    try:
      tickers = []
      endpoints = [
          "https://data-api.binance.vision/api/v3/ticker/24hr",
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
        by_change = sorted(
            tickers,
            key=lambda x: float(x.get("priceChangePercent", 0)),
            reverse=True,
        )
        by_volume = sorted(
            tickers, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True
        )

        top_g = by_change[0]
        top_l = by_change[-1]
        top_v = by_volume[0]

        # أ. إرسال صفقة بيع (Short) إذا وجدت عملة في قمة
        if step_counter % 3 == 2 and float(top_g.get("priceChangePercent", 0)) >= 4.0:
          sym = top_g["symbol"]
          price = float(top_g["lastPrice"])
          pump = float(top_g["priceChangePercent"])
          sl = round(price * 1.02, 5)
          tp1 = round(price * 0.96, 5)
          tp2 = round(price * 0.93, 5)

          sell_msg = (
              "🔴 [هذه صفقة بيع / Short من القمة] 🔴\n"
              "👑 منظومة عبد الحكيم رائد للتحليل\n"
              "━━━━━━━━━━━━━━━━━━\n"
              f"📌 العملة: #{sym}\n"
              f"📈 نسبة الصعود: +{pump:.2f}%\n"
              "📊 السلوك: وصول العملة لذروة الشراء وبدء ضغط بيعي\n"
              "━━━━━━━━━━━━━━━━━━\n"
              f"💰 سعر الدخول المقترح (Short): {price}\n"
              f"🛑 وقف الخسارة (SL): {sl}\n"
              f"🎯 الهدف الأول (TP1): {tp1}\n"
              f"🎯 الهدف الثاني (TP2): {tp2}\n"
              "━━━━━━━━━━━━━━━━━━\n"
              "💡 نصيحة عبد الحكيم: لا تطارد القمم المشتعلة؛ افتح صفقة البيع"
              " برافعة 3x-5x وأمن ربحك فور ملامسة الهدف الأول."
          )
          send_telegram(sell_msg)

        # ب. إرسال صفقة شراء (Long) لعملة في قاع ارتدادي
        elif (
            step_counter % 3 == 0
            and float(top_l.get("priceChangePercent", 0)) <= -3.0
        ):
          sym = top_l["symbol"]
          price = float(top_l["lastPrice"])
          drop = float(top_l["priceChangePercent"])
          sl = round(price * 0.975, 5)
          tp1 = round(price * 1.04, 5)
          tp2 = round(price * 1.08, 5)

          buy_msg = (
              "🟢 [هذه صفقة شراء / Long من القاع] 🟢\n"
              "👑 منظومة عبد الحكيم رائد للتحليل\n"
              "━━━━━━━━━━━━━━━━━━\n"
              f"📌 العملة: #{sym}\n"
              f"📉 نسبة التراجع: {drop:.2f}%\n"
              "📊 السلوك: ارتداد صاعد وتجميع سيولة عند منطقة دعم\n"
              "━━━━━━━━━━━━━━━━━━\n"
              f"💰 سعر الدخول المقترح (Long): {price}\n"
              f"🛑 وقف الخسارة (SL): {sl}\n"
              f"🎯 الهدف الأول (TP1): {tp1}\n"
              f"🎯 الهدف الثاني (TP2): {tp2}\n"
              "━━━━━━━━━━━━━━━━━━\n"
              "💡 نصيحة عبد الحكيم: الدخول تدريجي عند مناطق الدعم ولا تخاطر"
              " بأكثر من 1-2% من محفظتك في الصفقة."
          )
          send_telegram(buy_msg)

        # ج. إرسال تقرير حركة وسيولة السوق
        else:
          g_info = f"#{top_g['symbol']} (+{float(top_g['priceChangePercent']):.2f}%) | السعر: {top_g['lastPrice']}"
          l_info = f"#{top_l['symbol']} ({float(top_l['priceChangePercent']):.2f}%) | السعر: {top_l['lastPrice']}"
          v_info = f"#{top_v['symbol']} ({float(top_v['quoteVolume'])/1000000:.1f} مليون $)"

          report_msg = (
              "📊 [هذا تقرير نبض وسيولة السوق] 📊\n"
              "👑 منظومة عبد الحكيم رائد للرصد اللحظي\n"
              "━━━━━━━━━━━━━━━━━━\n"
              f"⏱ التوقيت: {now_str}\n\n"
              f"🔥 أعلى عملة صاعدة: {g_info}\n\n"
              f"📉 أكبر عملة هابطة: {l_info}\n\n"
              f"💰 أعلى سيولة بالسوق: {v_info}\n"
              "━━━━━━━━━━━━━━━━━━\n"
              "💡 نصيحة عبد الحكيم: راقب اتجاه العملة صاحبة أعلى سيولة (BTC)"
              " لأنها تحدد اتجاه السوق بالكامل."
          )
          send_telegram(report_msg)

    except Exception as e:
      print("Market error:", e)

  # فاصل زمني 10 ثوانٍ فقط بين كل رسالة والأخرى
  time.sleep(10)
  
