from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import json
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === ✅ Tokens & IDs ===
VERIFY_TOKEN = "shreeraj123"
ACCESS_TOKEN = "<EAAWBpLkKe98BPA9QGk5u9dzcKxHZCY3f7ujZBc1C586fJp2GueIDeIjsL4FrZAo1fQz0oXiyRrIngQFZBNituLYEkCbonKlZARjGE5OjAlRysRob8DAQgYzZAk6RD6Rb33AHwcflDC01VeVuqeha6xXbww6TQmfoWZAa75JnJXIPHRD07RPW0kRSYWOt08aMZBLd68zluc68K3SZC3oCiYsACVOrrgLgnUKpDbMFviGKtPEerhwZDZD>"
WHATSAPP_PHONE_NUMBER_ID = "662731940264952"
GEMINI_API_KEY = "<AIzaSyBAi_c3eKDLATHFMEi_HuGNRJ1jEoMNRQ8>"

# === 🔷 Initialize Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# === 🔷 Load JSON Data ===
def load_json(filename, key):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(key, [])

faqs = load_json("faqs.json", "faqs")
contacts = load_json("contacts.json", "contacts")
campaigns = load_json("campaigns.json", "campaigns")

# === 🔷 Persistent Campaign Index ===
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

# === 🔷 Helpers ===
def send_whatsapp_message(phone_number: str, text: str):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": phone_number, "text": {"body": text}}
    res = requests.post(url, headers=headers, json=payload)
    logging.info(f"📤 Sent text to {phone_number}: {res.status_code} {res.text}")

def send_whatsapp_image(phone_number: str, image_url: str, caption: str = ""):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "image",
        "image": {"link": image_url, "caption": caption}
    }
    res = requests.post(url, headers=headers, json=payload)
    logging.info(f"📤 Sent image to {phone_number}: {res.status_code} {res.text}")

def find_faq_answer(user_question: str) -> str:
    user_question = user_question.lower()
    for faq in faqs:
        if faq["question"].lower() in user_question:
            return faq["answer"]
    return ""

def generate_gemini_answer(prompt: str) -> str:
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

def send_intelligent_reply(phone_number: str, reply: str, name: str = None):
    if name:
        reply = f"{name}, {reply}"
    if "|" in reply:
        parts = reply.split("|", 1)
        image_url = parts[0].strip()
        caption = parts[1].strip()
        if name:
            caption = f"{name}, {caption}"
        send_whatsapp_image(phone_number, image_url, caption)
    else:
        send_whatsapp_message(phone_number, reply)

def find_contact_name(phone_number: str) -> str:
    for contact in contacts:
        if contact["phone"] == phone_number:
            return contact["name"]
    return None

# === 🔷 Webhook ===
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
                msg_text = message["text"]["body"].strip().lower()

                logging.info(f"✅ User ({phone_number}) said: {msg_text}")

                name = find_contact_name(phone_number)

                reply = find_faq_answer(msg_text)
                if not reply:
                    reply = generate_gemini_answer(msg_text)

                send_intelligent_reply(phone_number, reply, name)

        except Exception as e:
            logging.error(f"⚠️ Error: {e}")

        return 'OK', 200

# === 🔷 Campaign Endpoint ===
@app.route('/send_daily_campaign', methods=['POST'])
def send_daily_campaign():
    global current_message_index
    campaign = campaigns[current_message_index]
    image_url = campaign["image"]
    message_text = campaign["text"]

    logging.info(f"⏰ Sending daily campaign: {message_text}")

    for contact in contacts:
        personalized_caption = f"{contact['name']}, {message_text}"
        send_whatsapp_image(contact["phone"], image_url, personalized_caption)

    current_message_index = (current_message_index + 1) % len(campaigns)
    save_index(current_message_index)

    return jsonify({"status": "success", "message": message_text}), 200

# === 🔷 Main ===
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

