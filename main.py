import os
import requests
from flask import Flask, request, jsonify, render_template_string

# 1. API Setup (Key-ዩን Render ላይ በ Secrets ውስጥ እናስገባዋለን)
API_KEY = os.environ.get("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# አባይ በአክብሮት እና በአራዳነት እንዲመልስ
SYSTEM_INSTRUCTION = "አንተ ስምህ አባይ ይባላል። ኢትዮጵያዊ አራዳ እና የፍቅር አማካሪ ነህ። የምታወራው በአማርኛ ብቻ ነው። ለሰዎች መልካም አመለካከት ይኑርህ።"

app = Flask(__name__)

@app.route('/')
def home():
    return "አባይ AI አሁን በ Render ላይ በሰላም እየተንሳፈፈ ነው! 🌊"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_msg = request.json.get("message", "")
        payload = {
            "contents": [{"parts": [{"text": f"{SYSTEM_INSTRUCTION}\n\nተጠቃሚ: {user_msg}\nአባይ:"}]}]
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(URL, headers=headers, json=payload)
        result = response.json()
        
        if 'candidates' in result:
            reply = result['candidates'][0]['content']['parts'][0]['text']
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "አባይ ትንሽ እያሰበ ነው... ቆይተሽ ሞክሪኝ።"})
    except:
        return jsonify({"reply": "ኔትወርክ ተቋረጠ! 🔄"})

if __name__ == "__main__":
    # Render የራሱን Port ስለሚሰጥ በ os.environ እናነበዋለን
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
