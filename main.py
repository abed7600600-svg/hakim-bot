from datetime import datetime
import json
import time
import urllib.request

# ==========================================
# رادار عبد الحكيم رائد - الأخبار والتحليل والعقود 24/7
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


# خوارزمية تحليل أثر الخبر على السوق
def analyze_news_impact(title, body):
  text = (title + " " + body).lower()
  bullish_keywords = [
      "surge",
      "rally",
      "approval",
      "record",
      "high",
      "jump",
      "inflow",
      "gain",
      "buy",
      "bull",
      "etf",
      "launch",
      "partnership",
      "growth",
      "soar",
      "adopt",
  ]
  bearish_keywords = [
      "drop",
      "crash",
      "hack",
      "fall",
      "ban",
      "lawsuit",
      "sec",
      "delist",
      "fraud",
      "bear",
      "plunge",
      "outflow",
      "dump",
      "scam",
      "investigation",
      "breach",
  ]

  bull_score = sum(1 for w in bullish_keywords if w in text)
  bear_score = sum(1 for w in bearish_keywords if w in text)

  if bull_score > bear_score:
    impact = "🟢 إيجابي / صعودي (Bullish Impact)"
    explanation = (
        "الخبر يعزز السيولة الشرائية ويدعم صعود الأسعار وزيادة إقبال"
        " المتداولين."
    )
  elif bear_score > bull_score:
    impact = "🔴 سلبي / هبوطي (Bearish Impact)"
    explanation = (
        "الخبر يولد ضغوطاً بيعية ومخاوف في السوق، مما قد يؤدي لتصحيح أو هبوط"
        " سعري."
    )
  else:
    impact = "⚪ محايد / استقراري (Neutral Impact)"
    explanation = (
        "الخبر ذو تأثير متوازن ويساعد على استقرار حركة التداول دون تقلبات عنيفة."
    )

  return impact, explanation


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
    "🌟 تم تفعيل رادار عبد الحكيم رائد المتكامل (أخبار عالمية + تحليل + عقود"
    " آجلة) بنجاح!\nسيبدأ الآن البث الحي المتواصل كل 30 ثانية..."
)

EXCLUDED = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "EURUSDT"]
news_idx = 0
loop_count = 0

while True:
  loop_count += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  # -------------------------------------------------------------
  # 1. بث الأخبار العالمية مع التحليل اللحظي للمصدر والأثر
  # -------------------------------------------------------------
  try:
    news_res = get_json(
        "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    )
    if "Data" in news_res and len(news_res["Data"]) > 0:
      articles = news_res["Data"]
      article = articles[news_idx % len(articles)]

      source_name = article.get("source_info", {}).get("name", "Global Media")
      title = article.get("title", "No Title")
      body = article.get("body", "")[:180] + "..."
      news_url = article.get("url", "")
      pub_timestamp = article.get("published_on", time.time())
      pub_date_str = datetime.utcfromtimestamp(pub_timestamp).strftime(
          "%Y-%m-%d | %H:%M:%S UTC"
      )

      impact_tag, impact_desc = analyze_news_impact(title, body)

      news_card = (
          "📰 رادار الأخبار العالمية والتحليل | عبد الحكيم رائد\n"
          "━━━━━━━━━━━━━━━━━━━━━\n"
          f"🌐 منصة المصدر: {source_name} (اللغة الأصلية للموقع: English)\n"
          f"⏱ تاريخ ووقت النشر الرسمي: {pub_date_str}\n\n"
          "📌 عنوان الخبر الأصلي:\n"
          f"{title}\n\n"
          "📝 ملخص وتفاصيل الخبر:\n"
          f"{body}\n\n"
          "🧠 التحليل الفني وتأثير الخبر على السوق:\n"
          f"• التقييم: {impact_tag}\n"
          f"• التفسير: {impact_desc}\n"
          "━━━━━━━━━━━━━━━━━━━━━\n"
          f"🔗 رابط المقال الأصلي والمصدر: {news_url}"
      )

      send_telegram(news_card)
      news_idx += 1
  except Exception as e:
    print("News processing error:", e)

  time.sleep(15)

  # -------------------------------------------------------------
  # 2. فحص العقود الآجلة اللحظي ورصد صفقات الشورت
  # -------------------------------------------------------------
  try:
    data = get_json("https://data-api.binance.vision/api/v3/ticker/24hr")
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

      market_card = (
          "📊 رادار نبض العقود الآجلة | عبد الحكيم رائد\n"
          "━━━━━━━━━━━━━━━━━━━━━\n"
          f"⏱ التوقيت: {now_str} (دورة #{loop_count})\n\n"
          f"🔥 أعلى عملة عقود صاعدة: {g_info}\n"
          f"📉 أكبر عملة عقود هابطة: {l_info}\n"
          f"💰 أعلى سيولة عقود آجلة: {v_info}\n"
          "━━━━━━━━━━━━━━━━━━━━━\n"
          "🔍 حالة الرادار: مسح مباشر لجميع الصفقات والفرص..."
      )
      send_telegram(market_card)

      # فحص إشارات الشورت
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

                sig_card = (
                    "🚨 إشارة شورت مؤكدة (Signal Alert) 🚨\n"
                    "👑 منظومة عبد الحكيم رائد للتحليل الكمي\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📌 العملة: {sym}\n"
                    f"📈 نسبة الصعود: +{pump:.1f}%\n"
                    f"📊 مؤشر RSI: {rsi_val:.1f}\n"
                    f"🌊 تدفق الفوليوم: {v_spike:.1f}x ضعف المعدل\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💰 سعر الدخول المقترح: {last_c}\n"
                    f"🛑 وقف الخسارة الصارم (SL): {sl}\n"
                    f"🎯 الهدف الأول (TP1): {tp1}\n"
                    f"🎯 الهدف الثاني (TP2): {tp2}\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    "💡 نصيحة عبد الحكيم الاستراتيجية: ادخل بـ 1-2% فقط مع"
                    " رافعة 3x-5x وحرك الوقف لنقطة الدخول عند الهدف الأول."
                )
                send_telegram(sig_card)
                break
          except Exception:
            continue
  except Exception as e:
    print("Market error:", e)

  time.sleep(15)
        
