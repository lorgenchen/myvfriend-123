import google.generativeai as genai
import json
import os
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import TextMessage
from dotenv import load_dotenv
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Flask app starting")

# 根路由（健康檢查用）
@app.route("/", methods=['GET'])
def home():
    logger.debug("Handling / request")
    return "Welcome to myvfriend-123!", 200

# 測試路由
@app.route("/test", methods=['GET'])
def test():
    logger.debug("Handling /test request")
    return "Hello, test!", 200

# LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    logger.debug("Handling /callback request")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature error")
        abort(400)
    return 'OK'

# 載入環境變數
load_dotenv()

# LINE 憑證
configuration = Configuration(access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
line_bot_api = MessagingApi(configuration)
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))
logger.debug("LINE Bot API and Webhook handler initialized")

# Gemini AI 設定
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")
logger.debug("Gemini AI configured")

# 檔案名稱模板
def get_user_file(user_id, file_type):
    return f"{file_type}_{user_id}.json"

# 讀取與儲存 JSON
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 設定個性（預設值）
def get_setting(prompt):
    return 4

# 處理 LINE 訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()
    logger.debug(f"Received message from {user_id}: {user_input}")

    user_profile = load_json(get_user_file(user_id, "user_profile"))
    messages = load_json(get_user_file(user_id, "chat_history"))
    logger.debug(f"Loaded profile and history for {user_id}")

    FREE_PERSONALITY_SETTINGS = ["幽默感", "溫暖程度", "樂觀度", "回應態度", "健談程度"]
    PAID_PERSONALITY_SETTINGS = ["直率程度", "情緒應對方式", "建議提供程度", "深度話題程度"]

    if "ai_gender" not in user_profile:
        user_profile["ai_gender"] = "中性"
        logger.debug(f"Set default ai_gender for {user_id}")

    if "personality" not in user_profile or not user_profile["personality"]:
        user_profile["personality"] = {}
        for setting in FREE_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        if "付費用戶" in user_profile and user_profile["付費用戶"]:
            for setting in PAID_PERSONALITY_SETTINGS:
                user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        save_json(get_user_file(user_id, "user_profile"), user_profile)
        logger.debug(f"Initialized personality for {user_id}")
        line_bot_api.reply(event.reply_token, [TextMessage(text="✅ 你的 AI 朋友個性已設定完成！開始聊天吧 🎉")])
        return

    if user_input == "調整設定":
        for setting in FREE_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        if "付費用戶" in user_profile and user_profile["付費用戶"]:
            for setting in PAID_PERSONALITY_SETTINGS:
                user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        save_json(get_user_file(user_id, "user_profile"), user_profile)
        logger.debug(f"Updated personality for {user_id}")
        line_bot_api.reply(event.reply_token, [TextMessage(text="✅ AI 個性已更新！請繼續聊天～")])
        return

    personality = user_profile["personality"]
    humor = personality.get("幽默感", 4)
    warmth = personality.get("溫暖程度", 4)
    optimism = personality.get("樂觀度", 4)
    tone = personality.get("回應態度", 4)
    talkativeness = personality.get("健談程度", 4)
    logger.debug(f"Personality settings for {user_id}: humor={humor}, warmth={warmth}, optimism={optimism}, tone={tone}, talkativeness={talkativeness}")

    prompt = (
        f"你是一個 AI 朋友，請根據以下個性設定來回應使用者：\n"
        f"- 幽默感：{humor}/7\n"
        f"- 溫暖程度：{warmth}/7\n"
        f"- 樂觀度：{optimism}/7\n"
        f"- 回應風格：{tone}（1=年輕, 7=成熟）\n"
        f"- 健談程度：{talkativeness}/7\n"
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

    line_bot_api.reply(event.reply_token, [TextMessage(text=ai_response)])
    logger.debug(f"Sent response to {user_id}: {ai_response}")

    messages.append({"user": user_input, "ai": ai_response})
    save_json(get_user_file(user_id, "chat_history"), messages)
    logger.debug(f"Saved chat history for {user_id}")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    logger.debug(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port)