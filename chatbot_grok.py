import google.generativeai as genai
import os
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import json
import logging
import time

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Flask app starting")

# 從環境變數載入 Firebase 憑證
firestore_creds = os.environ.get("FIRESTORE_CREDENTIALS")
if not firestore_creds:
    logger.error("FIRESTORE_CREDENTIALS environment variable is not set")
    raise ValueError("FIRESTORE_CREDENTIALS is required")
cred_dict = json.loads(firestore_creds)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/", methods=['GET'])
def home():
    logger.debug("Handling / request")
    return "Welcome to myvfriend-123!", 200

@app.route("/test", methods=['GET'])
def test():
    logger.debug("Handling /test request")
    return "Hello, test!", 200

@app.route("/callback", methods=['POST'])
def callback():
    logger.debug("Handling /callback request")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    logger.debug(f"Received webhook with signature: {signature}, body: {body}")
    try:
        handler.handle(body, signature)
        logger.debug("Webhook handled successfully")
    except InvalidSignatureError:
        logger.error("Invalid signature error")
        abort(400)
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        abort(500)
    return 'OK'

load_dotenv()

channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
if not channel_access_token:
    logger.error("LINE_CHANNEL_ACCESS_TOKEN is not set")
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required")
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
channel_secret = os.environ.get("LINE_CHANNEL_SECRET")
if not channel_secret:
    logger.error("LINE_CHANNEL_SECRET is not set")
    raise ValueError("LINE_CHANNEL_SECRET is required")
handler = WebhookHandler(channel_secret)
logger.debug(f"LINE Bot API initialized with token: {channel_access_token[:10]}...")
logger.debug(f"Webhook handler initialized with secret: {channel_secret[:10]}...")

gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    logger.error("GEMINI_API_KEY is not set")
    raise ValueError("GEMINI_API_KEY is required")
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-pro")
logger.debug(f"Gemini AI configured with key: {gemini_api_key[:10]}...")

def send_reply(reply_token, message):
    retries = 3
    for attempt in range(retries):
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=message)]
                )
            )
            logger.debug(f"Reply sent successfully with token: {reply_token}")
            return True
        except InvalidSignatureError:
            logger.error(f"Invalid reply token: {reply_token}")
            break
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    logger.error(f"Failed to send reply after {retries} attempts")
    return False

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()
    logger.debug(f"Received message from {user_id}: {user_input}")

    # 從 Firestore 載入用戶資料
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        user_profile = user_data.get("profile", {
            "ai_gender": "中性",
            "personality": {
                "幽默感": 4,
                "溫暖程度": 4,
                "樂觀度": 4,
                "回應態度": 4,
                "健談程度": 4
            },
            "name": None
        })
        messages = user_data.get("messages", [])
    else:
        user_profile = {
            "ai_gender": "中性",
            "personality": {
                "幽默感": 4,
                "溫暖程度": 4,
                "樂觀度": 4,
                "回應態度": 4,
                "健談程度": 4
            },
            "name": None
        }
        messages = []

    logger.debug(f"Loaded profile for {user_id}: {user_profile}")

    # 檢查是否包含名字
    if user_input.startswith("我叫") or user_input.startswith("我的名字是"):
        name = user_input.replace("我叫", "").replace("我的名字是", "").strip()
        user_profile["name"] = name
        logger.debug(f"Set name for {user_id} to {name}")
        if send_reply(event.reply_token, f"好的，我記住了，你叫{name}！有什麼我可以幫你的？"):
            logger.debug(f"Sent name confirmation to {user_id}")
        messages.append({"user": user_input, "ai": f"好的，我記住了，你叫{name}！有什麼我可以幫你的？"})
        user_ref.set({"profile": user_profile, "messages": messages})
        return

    if user_input == "調整設定":
        user_profile["personality"] = {
            "幽默感": 4,
            "溫暖程度": 4,
            "樂觀度": 4,
            "回應態度": 4,
            "健談程度": 4
        }
        logger.debug(f"Updated personality for {user_id}: {user_profile}")
        if send_reply(event.reply_token, "✅ AI 個性已更新！請繼續聊天～"):
            logger.debug(f"Sent update response to {user_id}")
        messages.append({"user": user_input, "ai": "✅ AI 個性已更新！請繼續聊天～"})
        user_ref.set({"profile": user_profile, "messages": messages})
        return

    personality = user_profile["personality"]
    humor = personality.get("幽默感", 4)
    warmth = personality.get("溫暖程度", 4)
    optimism = personality.get("樂觀度", 4)
    tone = personality.get("回應態度", 4)
    talkativeness = personality.get("健談程度", 4)
    name = user_profile.get("name", "朋友")
    logger.debug(f"Personality settings for {user_id}: humor={humor}, warmth={warmth}, optimism={optimism}, tone={tone}, talkativeness={talkativeness}, name={name}")

    history_str = "\n".join([f"使用者: {msg['user']}\nAI: {msg['ai']}" for msg in messages[-5:]])
    prompt = (
        f"你是一個 AI 朋友，請根據以下個性設定和對話歷史回應使用者：\n"
        f"- 幽默感：{humor}/7\n"
        f"- 溫暖程度：{warmth}/7\n"
        f"- 樂觀度：{optimism}/7\n"
        f"- 回應風格：{tone}（1=年輕, 7=成熟）\n"
        f"- 健談程度：{talkativeness}/7\n"
        f"使用者名字：{name}\n"
        f"對話歷史：\n{history_str}\n"
        f"使用者說：{user_input}"
    )
    logger.debug(f"Generated prompt: {prompt}")

    try:
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        logger.debug(f"Generated AI response: {ai_response}")
    except Exception as e:
        ai_response = "哎呀，好像出了點問題，我晚點再試試吧！"
        logger.error(f"Error generating response: {e}")

    if send_reply(event.reply_token, ai_response):
        logger.debug(f"Sent response to {user_id}: {ai_response}")
    else:
        logger.error(f"Failed to send response")
        return

    messages.append({"user": user_input, "ai": ai_response})
    user_ref.set({"profile": user_profile, "messages": messages})
    logger.debug(f"Saved history to Firestore for {user_id}: {messages[-5:]}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.debug(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)