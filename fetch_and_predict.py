import os
import json
import datetime
import requests

# በብዛት የሚገበያዩባቸው ታዋቂ ኮይኖች
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_binance_data(symbol):
    """ከ Binance ነጻ ህዝባዊ API የ 24 ሰአት መረጃ እና የ 15 ደቂቃ ሻማዎችን ያመጣል"""
    ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=8"
    
    ticker_res = requests.get(ticker_url).json()
    klines_res = requests.get(klines_url).json()
    
    history_prices = [float(k[4]) for k in klines_res] # Closing prices of last 8 candles
    
    return {
        "symbol": symbol,
        "price": float(ticker_res.get("lastPrice", 0)),
        "high_24h": float(ticker_res.get("highPrice", 0)),
        "low_24h": float(ticker_res.get("lowPrice", 0)),
        "volume_24h": float(ticker_res.get("volume", 0)),
        "price_change_pct": float(ticker_res.get("priceChangePercent", 0)),
        "history": history_prices
    }

def analyze_with_gemini(coin_data):
    """የ ገበያውን መረጃ ለ Gemini ልኮ የ ትንበያ JSON ይቀበላል"""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY አልተገኘም! እባክህ በ GitHub Secrets ውስጥ አስገባ።")
        return None

    prompt = f"""
    You are an expert AI Crypto Quantitative Analyst.
    Analyze the following market data for {coin_data['symbol']}:
    - Current Price: ${coin_data['price']}
    - 24h High: ${coin_data['high_24h']}     - 24h Low:${coin_data['low_24h']}
    - 24h Price Change: {coin_data['price_change_pct']}%
    - Recent 15m Price History (oldest to newest): {coin_data['history']}

    Predict short-term future price trends for +15m, +30m, and +60m.
    Return ONLY a valid raw JSON object matching EXACTLY this structure without any markdown wrap or extra formatting text:
    {{
      "signal": "BULLISH" or "BEARISH" or "NEUTRAL",
      "confidence": number between 50 and 99,
      "pred_15m": predicted float price for +15 minutes,
      "pred_30m": predicted float price for +30 minutes,
      "pred_60m": predicted float price for +60 minutes,
      "summary": "Short 2 sentence technical reasoning in Amharic explaining key signals."
    }}
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        res_data = response.json()
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Clean potential markdown block formatting
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
    except Exception as e:
        print(f"Error calling Gemini for {coin_data['symbol']}: {e}")
        # Default fallback prediction structure
        cp = coin_data['price']
        return {
            "signal": "NEUTRAL",
            "confidence": 60,
            "pred_15m": round(cp * 1.001, 4),
            "pred_30m": round(cp * 1.002, 4),
            "pred_60m": round(cp * 0.999, 4),
            "summary": "የገበያ መዋዠቅ በመኖሩ ጥንቃቄ ያድርጉ። ትንተናው በበቂ ሁኔታ አልተጠናቀቀም።"
        }

def main():
    results = []
    updated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    for symbol in COINS:
        print(f"መረጃ በመሰብሰብ ላይ: {symbol}...")
        market_data = get_binance_data(symbol)
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
        
    print("መረጃው በትክክል ተተንትኖ data.json ላይ ተጽፏል!")

if __name__ == "__main__":
    main()

