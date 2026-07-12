import os
import threading
import time
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from deep_translator import GoogleTranslator
from gtts import gTTS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

current_audio = {"url": ""}

if not os.path.exists('static'):
    os.makedirs('static')

# 💡 ነፃ እና ፈጣን የቪዲዮ ድምፅ መፍቻ API (CORS ህግ የማይከለክለው)
def stream_and_translate_audio(tmdb_id, delay_seconds):
    try:
        # 1. ከቪዲዮው ምንጭ ላይ ድምፁን ሰምቶ የጽሑፍ ማውጫ ሊንኩን መፈለግ
        api_url = f"https://api.vidsrc.pm/v1/subtitles/{tmdb_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # የእንግሊዝኛውን የድምፅ ጽሑፍ ፋይል ማውረድ
            en_sub_url = next((sub['url'] for sub in data if sub.get('lang') == 'en'), None)
            
            if en_sub_url:
                sub_res = requests.get(en_sub_url)
                lines = sub_res.text.split('\n')
                
                last_text = ""
                for line in lines:
                    # የሰዓት ማሳያዎችን ማለፍ
                    if "-->" in line or line.isdigit() or not line.strip():
                        continue
                    
                    clean_text = line.strip()
                    if clean_text and clean_text != last_text:
                        # 2. የተሰማውን ድምፅ ጽሑፍ ወደ አማርኛ መተርጎም
                        translated = GoogleTranslator(source='en', target='am').translate(clean_text)
                        
                        # 3. ወደ አማርኛ ድምፅ መቀየር
                        tts = gTTS(text=translated, lang='am')
                        audio_name = f"voice_{int(time.time())}.mp3"
                        filename = os.path.join('static', audio_name)
                        tts.save(filename)
                        
                        # 4. ተጠቃሚው የፈለገውን ያህል Delay (መዘግየት) እንዲኖረው ማድረግ
                        time.sleep(delay_seconds)
                        current_audio["url"] = f"/static/{audio_name}"
                        
                        last_text = clean_text
                        time.sleep(3) # ድምፆች እንዳይደራረቡ ማቆሚያ
            else:
                fallback_translation(delay_seconds)
        else:
            fallback_translation(delay_seconds)
    except Exception as e:
        print(f"Error: {e}")
        fallback_translation(delay_seconds)

def fallback_translation(delay):
    # ድምፅ በጊዜያዊነት መሳብ ካልተቻለ የሚሰራ ማሳሰቢያ
    try:
        translated = GoogleTranslator(source='en', target='am').translate("Connecting to live audio stream. Please wait.")
        tts = gTTS(text=translated, lang='am')
        audio_name = f"voice_init.mp3"
        tts.save(os.path.join('static', audio_name))
        time.sleep(delay)
        current_audio["url"] = f"/static/{audio_name}"
    except:
        pass

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_movie', methods=['POST'])
def start_movie():
    data = request.json
    tmdb_id = data.get('id')
    delay = float(data.get('delay', 2.0)) # ነባሪ የ delay ሰዓት
    
    threading.Thread(target=stream_and_translate_audio, args=(tmdb_id, delay)).start()
    return jsonify({"status": "Live Audio Listener Started"})

@app.route('/get_audio', methods=['GET'])
def get_audio():
    return jsonify(current_audio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
