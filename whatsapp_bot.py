from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === ✅ Tokens & IDs ===
VERIFY_TOKEN = "shreeraj123"
ACCESS_TOKEN = "EAAWBpLkKe98BPEitTxbHPeZCyICK5ga4pjwpd1teaOeuCNijvANZAhDZBOL1jHvHglLrZCV8MEskM9eezfTnlQAyO4rl13tSeIwLXDOUY3iw6lXQawoyWxvPvrnov936qcAALBZA02n4j2riKUPZAbymzSMRkDfD2U81vFS9w45MQ9uCmKdNUIDNubORDj0LngyONgstdmvSDo3bbPixyUKroGCYUZCEcoFpVHXKDZBbLhtZBtU0y"
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
    """Try to find an FAQ answer matching the user's question."""
    user_question = user_question.lower()
    for faq in faqs:
        if faq["question"].lower() in user_question:
            return faq["answer"]
    return ""

def generate_gemini_answer(prompt: str) -> str:
    """Get a generative response from Gemini if no FAQ matches."""
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

# === Routes ===

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Meta webhook verification
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

                # First try FAQ
                reply = find_faq_answer(msg_text)

                # If no FAQ match, use Gemini
                if not reply:
                    reply = generate_gemini_answer(msg_text)

                send_whatsapp_message(phone_number, reply)

        except Exception as e:
            logging.error(f"⚠️ Error: {e}")

        return 'OK', 200

@app.route('/send_campaign', methods=['POST'])
def send_campaign():
    """Send a marketing campaign message to all contacts."""
    req = request.json
    message = req.get("message", "Hello! Check out our latest offers.")

    logging.info(f"📢 Sending campaign: {message}")

    for contact in contacts:
        personalized = f"Hi {contact['name']}, {message}"
        send_whatsapp_message(contact["phone"], personalized)

    return jsonify({"status": "success", "message": "Campaign sent"}), 200

# === Main ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
