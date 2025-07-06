from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import json
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === ✅ Tokens & IDs ===
# WhatsApp verification token, Meta API access token, Gemini API key
VERIFY_TOKEN = "shreeraj123"
ACCESS_TOKEN = "EAAWBpLkKe98BPITEspfbOA3mH3QvGKt6HwMG6ZALS7fodDroBTeS9O8eFZA1yONCnJn1ejb07RVLg2dJZAOuyTKNyvavdIO1DvH1sq8oaPabvuLLSRnaAcZB2547uhjHgSRHUY5BX4v9e3y5uDtbOc4teDZAjnPKd0Q9XJY3U8OWSZBDR2pfdzdasmLv51Kk9nETSJ7D209fU2ZA7hlINpuE7GAWm0ZARvSnaOfvwDnZCsEwfeAZDZD"
WHATSAPP_PHONE_NUMBER_ID = "662731940264952"
GEMINI_API_KEY = "AIzaSyBAi_c3eKDLATHFMEi_HuGNRJ1jEoMNRQ8"

# === 🔷 Initialize Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# === 🔷 Load JSON Data ===
# Load FAQs and contact list from local JSON files
def load_json(filename, key):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(key, [])

faqs = load_json("faqs.json", "faqs")
contacts = load_json("contacts.json", "contacts")

# === 🔷 Campaign Messages ===
# Predefined marketing campaign messages
campaign_messages = [
    "🔥 Big Sale today only! Don’t miss it.",
    "🎁 New arrivals just for you! Check them out.",
    "✅ Did you know? We have a loyalty program.",
    "🌟 Exclusive discounts available now.",
    "🚀 Free shipping on all orders today!"
]

# === 🔷 Persistent Campaign Index ===
# Keeps track of which campaign message was sent last
INDEX_FILE = "campaign_index.json"

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("index", 0)
    return 0

def save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump({"index": index}, f)

current_message_index = load_index()

# === 🔷 Helper: Send WhatsApp Message ===
def send_whatsapp_message(phone_number: str, text: str):
    """
    Sends a message to a WhatsApp user via Meta Graph API.
    """
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

# === 🔷 Helper: Find FAQ Answer ===
def find_faq_answer(user_question: str) -> str:
    """
    Checks if user's question matches any FAQ and returns the answer.
    """
    user_question = user_question.lower()
    for faq in faqs:
        if faq["question"].lower() in user_question:
            return faq["answer"]
    return ""

# === 🔷 Helper: Get Gemini AI Answer ===
def generate_gemini_answer(prompt: str) -> str:
    """
    Uses Gemini AI to generate a response for user query.
    """
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

# === 🔷 Webhook Endpoint ===
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    WhatsApp webhook to handle verification and incoming messages.
    """
    if request.method == 'GET':
        # Verify webhook with Meta
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge
        return 'Invalid verification token', 403

    if request.method == 'POST':
        # Handle incoming WhatsApp message
        data = request.json
        logging.info(f"📩 Incoming webhook: {json.dumps(data, indent=2)}")

        try:
            changes = data["entry"][0]["changes"][0]["value"]
            if "messages" in changes:
                message = changes["messages"][0]
                phone_number = message["from"]
                msg_text = message["text"]["body"]

                logging.info(f"✅ User ({phone_number}) said: {msg_text}")

                # Try FAQ first
                reply = find_faq_answer(msg_text)
                if not reply:
                    # Fall back to Gemini AI
                    reply = generate_gemini_answer(msg_text)

                send_whatsapp_message(phone_number, reply)

        except Exception as e:
            logging.error(f"⚠️ Error: {e}")

        return 'OK', 200

# === 🔷 Campaign Endpoint (Cron Job) ===
@app.route('/send_daily_campaign', methods=['POST'])
def send_daily_campaign():
    """
    Sends the next marketing campaign message to all contacts.
    Called by cron job.
    """
    global current_message_index
    message = campaign_messages[current_message_index]
    logging.info(f"⏰ Sending daily campaign: {message}")

    for contact in contacts:
        personalized = f"Hi {contact['name']}, {message}"
        send_whatsapp_message(contact["phone"], personalized)

    # Update index for next time
    current_message_index = (current_message_index + 1) % len(campaign_messages)
    save_index(current_message_index)

    return jsonify({"status": "success", "message": message}), 200

# === 🔷 Main Application ===
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
