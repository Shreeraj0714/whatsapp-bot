from flask import Flask, request
import requests
import google.generativeai as genai
import json

app = Flask(__name__)

# ✅ Tokens & IDs
VERIFY_TOKEN = "shreeraj123"
ACCESS_TOKEN = "EAAWBpLkKe98BPEitTxbHPeZCyICK5ga4pjwpd1teaOeuCNijvANZAhDZBOL1jHvHglLrZCV8MEskM9eezfTnlQAyO4rl13tSeIwLXDOUY3iw6lXQawoyWxvPvrnov936qcAALBZA02n4j2riKUPZAbymzSMRkDfD2U81vFS9w45MQ9uCmKdNUIDNubORDj0LngyONgstdmvSDo3bbPixyUKroGCYUZCEcoFpVHXKDZBbLhtZBtU0y"
WHATSAPP_PHONE_NUMBER_ID = "662731940264952"
GEMINI_API_KEY = "AIzaSyBAi_c3eKDLATHFMEi_HuGNRJ1jEoMNRQ8"

# ✅ Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ✅ Load FAQs
with open("faqs.json", "r", encoding="utf-8") as f:
    faqs_data = json.load(f)

faqs = faqs_data["faqs"]  # ✅ Extract the list of FAQs

def find_faq_answer(user_question):
    user_question = user_question.lower()
    for faq in faqs:
        if faq["question"].lower() in user_question:
            return faq["answer"]
    return None

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge
        return 'Invalid verification token', 403

    if request.method == 'POST':
        data = request.json
        print("📩 Incoming webhook data:")
        print(data)

        try:
            changes = data["entry"][0]["changes"][0]["value"]
            if "messages" in changes:
                message = changes["messages"][0]
                phone_number = message["from"]
                msg_text = message["text"]["body"]

                print(f"✅ User said: {msg_text}")

                # ✨ First, try FAQ
                reply_text = find_faq_answer(msg_text)

                # 🧠 If not found in FAQ, use Gemini
                if not reply_text:
                    response = model.generate_content(msg_text)
                    reply_text = response.text.strip()

                send_whatsapp_message(phone_number, reply_text)

        except Exception as e:
            print("⚠️ Error:", e)

        return 'OK', 200

def send_whatsapp_message(to, message):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }

    res = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent: {res.status_code} {res.text}")

if __name__ == '__main__':
    app.run(port=5000)
