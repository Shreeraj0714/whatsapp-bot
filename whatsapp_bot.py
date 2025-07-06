from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import json
import logging
import schedule
import time
from threading import Thread
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === ✅ Tokens & IDs ===
VERIFY_TOKEN = "shreeraj123"
ACCESS_TOKEN = "EAAWBpLkKe98BPMvx7bRNiO6EcLWwGO0LjUj5PHb0ofiCZBAxqtaOAH0H3wh0wMuXU9H3OJZCMPanzhSS6QVc3CYEU29nftTBZBZBWA0c4x0eL3e5ZCIGfD5KmLVbNWcA87wOtx56stKQUsb7WZAZB6DpE53wA9UjSCiDbJKA7ZBTJirV0UM7xYKOdR1tZAnZCdlmintRlBoV2w4iZBOG3kYJfPI9LcW5ZBZCQiZCajSPAVlGVceJEGZCgZDZD"
WHATSAPP_PHONE_NUMBER_ID = "662731940264952"
GEMINI_API_KEY = "AIzaSyBAi_c3eKDLATHFMEi_HuGNRJ1jEoMNRQ8"

# === Initialize Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# === Load Data ===
def load_json(filename, key):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(key, [])

faqs = load_json("faqs.json", "faqs")
contacts = load_json("contacts.json", "contacts")

# === Marketing Messages ===
campaign_messages = [
    "🔥 Big Sale today only! Don’t miss it.",
    "🎁 New arrivals just for you! Check them out.",
    "✅ Did you know? We have a loyalty program.",
    "🌟 Exclusive discounts available now.",
    "🚀 Free shipping on all orders today!"
]

# === Persistent Index ===
INDEX_FILE = "campaign_index.json"

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            return json.load(f).get("index", 0)
    return 0

def save_index(index):
    with open(INDEX_FILE, "w") as f:
        json.dump({"index": index}, f)

current_message_index = load_index()

# === Helpers ===
def send_whatsapp_message(phone_number: str, text: str):
    """Send message to a WhatsApp user via Meta Graph API."""
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": text}
    }
    res = requests.post(url, headers=headers, json=payload)
    logging.info(f"📤 Sent to {phone_number}: {res.status_code} {res.text}")

def find_faq_answer(user_question: str) -> str:
    user_question = user_question.lower()
    for faq in faqs:
        if faq["question"].lower() in user_question:
            return faq["answer"]
    return ""

def generate_gemini_answer(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

# === Routes ===

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
        logging.info(f"📩 Incoming webhook: {json.dumps(data, indent=2)}")

        try:
            changes = data["entry"][0]["changes"][0]["value"]
            if "messages" in changes:
                message = changes["messages"][0]
                phone_number = message["from"]
                msg_text = message["text"]["body"]

                logging.info(f"✅ User ({phone_number}) said: {msg_text}")

                reply = find_faq_answer(msg_text)
                if not reply:
                    reply = generate_gemini_answer(msg_text)

                send_whatsapp_message(phone_number, reply)

        except Exception as e:
            logging.error(f"⚠️ Error: {e}")

        return 'OK', 200

@app.route('/send_campaign', methods=['POST'])
def send_campaign():
    req = request.json
    message = req.get("message", "Hello! Check out our latest offers.")
    logging.info(f"📢 Sending campaign: {message}")

    for contact in contacts:
        personalized = f"Hi {contact['name']}, {message}"
        send_whatsapp_message(contact["phone"], personalized)

    return jsonify({"status": "success", "message": "Campaign sent"}), 200

# === Scheduled Campaign ===

def send_daily_campaign():
    global current_message_index
    message = campaign_messages[current_message_index]
    logging.info(f"⏰ Scheduled campaign triggered. Message: {message}")

    for contact in contacts:
        personalized = f"Hi {contact['name']}, {message}"
        send_whatsapp_message(contact["phone"], personalized)

    current_message_index = (current_message_index + 1) % len(campaign_messages)
    save_index(current_message_index)

# Schedule at 14:55 PM every day (UTC)
schedule.every().day.at("14:55").do(send_daily_campaign)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# === Main ===
if __name__ == '__main__':
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=5000))
    flask_thread.start()

    run_scheduler()

