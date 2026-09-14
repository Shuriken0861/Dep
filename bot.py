import os
from threading import Thread
from flask import Flask
import telebot
import ccxt
import pandas as pd
import pandas_ta as ta
from openai import OpenAI

# 1. RENDER KAPANMASIN DİYE WEB SUNUCUSU (KEEP-ALIVE)
app = Flask('')

@app.route('/')
def home():
    return "Bot 7/24 Aktif!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# 2. API ANAHTARLARI (Render Environment Variables Üzerinden Alınır)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = OpenAI(api_key=OPENAI_API_KEY)
exchange = ccxt.binance({'enableRateLimit': True})

def fetch_ta_data(symbol="BTC/USDT", timeframe="4h"):
    try:
        if "/" not in symbol and len(symbol) > 4:
            symbol = f"{symbol[:-4]}/{symbol[-4:]}".upper()
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        df['EMA_50'] = ta.ema(df['close'], length=50)
        
        latest = df.iloc[-1]
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": latest['close'],
            "rsi": round(latest['RSI'], 2),
            "ema_20": round(latest['EMA_20'], 2),
            "ema_50": round(latest['EMA_50'], 2),
            "trend": "Yükseliş / Boğa" if latest['EMA_20'] > latest['EMA_50'] else "Düşüş / Ayı"
        }
    except Exception as e:
        return None

def get_ai_analysis(ta_data):
    prompt = f"""
    Aşağıdaki teknik analiz verilerine göre kısa ve net teknik bir yorum yap:
    Sembol: {ta_data['symbol']} ({ta_data['timeframe']})
    Fiyat: ${ta_data['current_price']}
    RSI: {ta_data['rsi']}
    EMA 20: ${ta_data['ema_20']} | EMA 50: ${ta_data['ema_50']}
    Trend: {ta_data['trend']}
    """

    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Disiplinli bir kripto teknik analiz uzmanısın."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Kripto Analiz Botu Hazır!\nÖrnek Kullanım: `/analiz BTC/USDT 4h`", parse_mode="Markdown")

@bot.message_handler(commands=['analiz'])
def analyze_crypto(message):
    args = message.text.split()[1:]
    symbol = args[0] if len(args) > 0 else "BTC/USDT"
    timeframe = args[1] if len(args) > 1 else "4h"
    
    status_msg = bot.reply_to(message, f"⏳ `{symbol}` verileri çekiliyor...", parse_mode="Markdown")
    
    ta_data = fetch_ta_data(symbol, timeframe)
    if not ta_data:
        bot.edit_message_text("❌ Veri çekilemedi. Sembolü kontrol edin.", chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        return

    analysis = get_ai_analysis(ta_data)
    bot.edit_message_text(analysis, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
if __name__ == "__main__":
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        print("❌ HATA: TELEGRAM_TOKEN veya OPENAI_API_KEY Render Environment alanında tanımlı değil!")
    else:
        print("🚀 Bot başarıyla başlatıldı ve dinlemeye geçti...")
        bot.infinity_polling()
