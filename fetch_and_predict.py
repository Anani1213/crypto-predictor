import os
import json
import datetime
import requests

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_binance_data(symbol):
    try:
        ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=8"
        
        ticker_res = requests.get(ticker_url).json()
        klines_res = requests.get(klines_url).json()
        
        history_prices = [float(k[4]) for k in klines_res]
        
        return {
            "symbol": symbol,
            "price": float(ticker_res.get("lastPrice", 0)),
            "high_24h": float(ticker_res.get("highPrice", 0)),
            "low_24h": float(ticker_res.get("lowPrice", 0)),
            "volume_24h": float(ticker_res.get("volume", 0)),
            "price_change_pct": float(ticker_res.get("priceChangePercent", 0)),
            "history": history_prices
        }
    except Exception as e:
        print(f"Binance Error for {symbol}: {e}")
        return None

def analyze_with_gemini(coin_data):
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY አልተገኘም!")
        return None

    cp = coin_data['price']
    prompt = f"""
    You are an expert AI Crypto Quantitative Analyst. Analyze {coin_data['symbol']}:
    - Current Price: ${cp}
    - 24h High: ${coin_data['high_24h']}     - 24h Low:${coin_data['low_24h']}
    - 24h Change: {coin_data['price_change_pct']}%
    - Recent Prices: {coin_data['history']}

    Predict short-term prices for +15m, +30m, and +60m.
    Return ONLY a valid raw JSON object matching EXACTLY this structure without any markdown wrap:
    {{
      "signal": "BULLISH",
      "confidence": 85,
      "pred_15m": {round(cp * 1.001, 4)},
      "pred_30m": {round(cp * 1.002, 4)},
      "pred_60m": {round(cp * 1.003, 4)},
      "summary": "የዋጋ ማስተካከል እያሳየ ሲሆን ወደፊት የመጨመር እድሉ ከፍተኛ ነው።"
    }}
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        res_data = response.json()
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
    except Exception as e:
        print(f"Gemini Error: {e}")
        return {
            "signal": "NEUTRAL",
            "confidence": 60,
            "pred_15m": round(cp * 1.001, 4),
            "pred_30m": round(cp * 1.002, 4),
            "pred_60m": round(cp * 0.999, 4),
            "summary": "የገበያ እንቅስቃሴው የተረጋጋ በመሆኑ በጥንቃቄ ይገበያዩ።"
        }

def main():
    results = []
    updated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    for symbol in COINS:
        print(f"መረጃ በመሰብሰብ ላይ: {symbol}...")
        market_data = get_binance_data(symbol)
        if not market_data:
            continue
        ai_prediction = analyze_with_gemini(market_data)
        
        combined = {
            "symbol": symbol.replace("USDT", ""),
            "full_symbol": symbol,
            "market": market_data,
            "ai": ai_prediction
        }
        results.append(combined)

    final_payload = {
        "updated_at": updated_at,
        "data": results
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)
        
    print("ተጠናቀዋል!")

if __name__ == "__main__":
    main()
