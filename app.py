import os
import threading
import time
import re
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

def clean_old_files():
    """የድሮ የድምፅ ፋይሎችን በማጽዳት ሰርቨሩ እንዳይሞላ ማድረግ"""
    try:
        now = time.time()
        for f in os.listdir('static'):
            f_path = os.path.join('static', f)
            if os.path.isfile(f_path) and f.endswith('.mp3'):
                if os.stat(f_path).st_mtime < now - 60: # ከአንድ ደቂቃ በላይ የቆዩትን አጥፋ
                    os.remove(f_path)
    except Exception as e:
        print(f"Error cleaning files: {e}")

def process_subtitle_text(text_data, delay):
    # .vtt ወይም .srt ላይ ያሉ የትርጉም ጽሑፎችን መለየት
    subtitles = re.findall(r'(\d{2}:\d{2}:\d{2}.\d{3} --> \d{2}:\d{2}:\d{2}.\d{3})\s+(.*?)(?=\n\n|\n\d|\Z)', text_data, re.DOTALL)
    if not subtitles:
        # ለቀላል የ SRT ፎርማት መሞከሪያ
        subtitles = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\s+(.*?)(?=\n\n|\n\d|\Z)', text_data, re.DOTALL)

    last_spoken = ""
    for timestamp, line in subtitles:
        clean_line = re.sub(r'<[^>]*>', '', line).replace('\n', ' ').strip()
        if clean_line and clean_line != last_spoken:
            try:
                # 1. ወደ አማርኛ መተርጎም
                translated = GoogleTranslator(source='en', target='am').translate(clean_line)
                print(f"Live Translation: {translated}")
                
                # 2. የድምፅ ፋይል መፍጠር
                tts = gTTS(text=translated, lang='am')
                audio_name = f"sub_{int(time.time())}_{os.urandom(4).hex()}.mp3"
                filename = os.path.join('static', audio_name)
                tts.save(filename)
                
                # የተጠቃሚውን የ delay ሰዓት መጠበቅ
                time.sleep(delay)
                current_audio["url"] = f"/static/{audio_name}"
                
                clean_old_files()
                last_spoken = clean_line
                time.sleep(4) # ንግግሮች እንዳይደራረቡ ሰፊ ጊዜ መስጠት
            except Exception as e:
                print(f"Error in TTS loop: {e}")

def fetch_subtitle_directly(tmdb_id, delay):
    """በትክክል ከሕዝባዊ የትርጉም ምንጮች (ሊንኮች) ጽሑፉን Live መሳብ"""
    urls = [
        f"https://api.vidsrc.pm/v1/subtitles/{tmdb_id}", 
        f"https://subtitles.vidsrc.me/movie/{tmdb_id}.vtt"
    ]
    
    subtitle_text = ""
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200 and len(res.text) > 100:
                subtitle_text = res.text
                break
        except:
            continue
            
    # ካልተገኘ ነባሪ የትርጉም ማሳያ (Fallback Mock)
    if not subtitle_text:
        subtitle_text = "00:00:05.000 --> 00:00:10.000\nWelcome to CineScope Premium.\n\n00:00:12.000 --> 00:00:18.000\nEnjoy the live Amharic AI voice translation."

    process_subtitle_text(subtitle_text, delay)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start_movie', methods=['POST'])
def start_movie():
    data = request.json
    tmdb_id = data.get('id')
    delay = float(data.get('delay', 0.5))
    
    # በአዲሱ መንገድ በጀርባ ስራውን ማስጀመር
    threading.Thread(target=fetch_subtitle_directly, args=(tmdb_id, delay)).start()
    return jsonify({"status": "Direct Subtitle Fetcher Started"})

@app.route('/get_audio', methods=['GET'])
def get_audio():
    return jsonify(current_audio)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
