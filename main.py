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
    "🔥 تم تفعيل رادار عبد الحكيم رائد (English News & Futures Signals)"
    " بنجاح!\nجاري الآن بث الأخبار الإنجليزية وصفقات العقود الآجلة كل 30"
    " ثانية..."
)

EXCLUDED = ["USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "EURUSDT"]
seen_news_ids = set()
news_idx = 0
loop_count = 0

while True:
  loop_count += 1
  now_str = datetime.utcnow().strftime("%H:%M:%S UTC")

  # 1. بث الأخبار العالمية باللغة الإنجليزية كما هي
  try:
    news_res = get_json(
        "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
    )
    if "Data" in news_res and len(news_res["Data"]) > 0:
      item = news_res["Data"][news_idx % len(news_res["Data"])]
      news_id = item.get("id")

      if news_id not in seen_news_ids:
        seen_news_ids.add(news_id)
        source = item.get("source_info", {}).get("name", "Global Media")
        t_en = item.get("title", "")
        b_en = item.get("body", "")[:180] + "..."
        link = item.get("url", "")
        categories = item.get("categories", "")

        label = (
            "🪙 [أخبار العملات]"
            if any(
                c in categories
                for c in ["BTC", "ETH", "ALTCOIN", "SOL", "BNB"]
            )
            else "📰 [خبر عاجل]"
        )

        news_msg = (
            f"{label}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Source: {source} | ⏱ {now_str}\n\n"
            f"📌 Title: {t_en}\n\n"
            f"📝 Summary: {b_en}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🔗 Link: {link}"
        )
        send_telegram(news_msg)
        news_idx += 1
  except Exception as e:
    print("News error:", e)

  time.sleep(15)

  # 2. فحص العقود الآجلة وصفقات الشورت
  try:
    tickers = []
    endpoints = [
        "https://data-api.binance.vision/api/v3/ticker/24hr",
        "https://fapi.binance.com/fapi/v1/ticker/24hr",
    ]
    for ep in endpoints:
      try:
        d = get_json(ep)
        if isinstance(d, list) and len(d) > 0:
          tickers = [
              t
              for t in d
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

      # فحص صفقات الشورت للعملات الصاعدة
      for t in by_change[:8]:
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
                    "🚨 [صفقة شورت - Futures Trade] 🚨\n"
                    "👑 منظومة عبد الحكيم رائد للتحليل\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"📌 Coin: #{sym}\n"
                    f"📈 24h Surge: +{pump:.1f}%\n"
                    f"📊 RSI (15m): {rsi_val:.1f}\n"
                    f"🌊 Volume Spike: {v_spike:.1f}x\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Entry Price: {last_c}\n"
                    f"🛑 Stop Loss (SL): {sl}\n"
                    f"🎯 Take Profit 1 (TP1): {tp1}\n"
                    f"🎯 Take Profit 2 (TP2): {tp2}\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "💡 نصيحة: افتح صفقة Short برافعة 3x-5x ومخاطرة 1-2% فقط،"
                    " وحرك الوقف لنقطة الدخول عند الهدف الأول."
                )
                send_telegram(sig_msg)
                time.sleep(2)
                break
          except Exception:
            continue
  except Exception as e:
    print("Scan error:", e)

  time.sleep(15)
  
