import os
import threading
import time
import re
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from playwright.sync_api import sync_playwright
from deep_translator import GoogleTranslator
from gtts import gTTS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# የቅርብ ጊዜ የተገኘውን የአማርኛ ድምፅ ፋይል ስም ለመያዝ
current_audio = {"url": ""}

# static ፎልደር መኖሩን ማረጋገጫ
if not os.path.exists('static'):
    os.makedirs('static')

def speak_amharic(text_to_speak, delay_seconds):
    try:
        translated = GoogleTranslator(source='en', target='am').translate(text_to_speak)
        print(f"የተተረጎመ: {translated}")
        
        tts = gTTS(text=translated, lang='am')
        audio_name = f"subtitle_{int(time.time())}.mp3"
        filename = os.path.join('static', audio_name)
        tts.save(filename)
        
        time.sleep(delay_seconds)
        # ለባቡር መንገድ (Railway) እንዲስማማ Hostname ን Dynamic ማድረግ
        current_audio["url"] = f"/static/{audio_name}"
    except Exception as e:
        print(f"Error in TTS: {e}")

def intercept_response(response, delay_seconds):
    if ".vtt" in response.url or "subtitle" in response.url:
        try:
            text_data = response.text()
            subtitles = re.findall(r'(\d{2}:\d{2}:\d{2}.\d{3} --> \d{2}:\d{2}:\d{2}.\d{3})\s+(.*?)(?=\n\n|\n\d|\Z)', text_data, re.DOTALL)
            
            last_spoken = ""
            for timestamp, line in subtitles:
                clean_line = re.sub(r'<[^>]*>', '', line).replace('\n', ' ').strip()
                if clean_line and clean_line != last_spoken:
                    threading.Thread(target=speak_amharic, args=(clean_line, delay_seconds)).start()
                    last_spoken = clean_line
                    time.sleep(3) 
        except:
            pass

def run_playwright(tmdb_id, delay):
    movie_url = f"https://vidsrc.pm/embed/movie/{tmdb_id}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page()
        page.on("response", lambda res: intercept_response(res, delay))
        try:
            page.goto(movie_url, timeout=60000)
            page.wait_for_timeout(9999999)
        except:
            browser.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_movie', methods=['POST'])
def start_movie():
    data = request.json
    tmdb_id = data.get('id')
    delay = float(data.get('delay', 1.0))
    threading.Thread(target=run_playwright, args=(tmdb_id, delay)).start()
    return jsonify({"status": "Live Interceptor Started"})

@app.route('/get_audio', methods=['GET'])
def get_audio():
    return jsonify(current_audio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
