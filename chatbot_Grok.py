import google.generativeai as genai
import json
import os
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration  # 新版 Messaging API
from linebot.v3.webhook import WebhookHandler  # 新版 Webhook
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent  # 新版事件處理
from linebot.v3.messaging import TextMessage  # 新版訊息格式
from dotenv import load_dotenv

app = Flask(__name__)

# 載入環境變數
load_dotenv()

# LINE 憑證（從環境變數讀取，或直接填入）
configuration = Configuration(access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
line_bot_api = MessagingApi(configuration)
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# Gemini AI 設定
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-pro")

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
    return 4  # 預設值，未來可改進為訊息輸入

# LINE Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理 LINE 訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()

    # 載入使用者資料與對話歷史
    user_profile = load_json(get_user_file(user_id, "user_profile"))
    messages = load_json(get_user_file(user_id, "chat_history"))

    # 免費版與付費版個性設定
    FREE_PERSONALITY_SETTINGS = ["幽默感", "溫暖程度", "樂觀度", "回應態度", "健談程度"]
    PAID_PERSONALITY_SETTINGS = ["直率程度", "情緒應對方式", "建議提供程度", "深度話題程度"]

    # 初始化 AI 性別與個性
    if "ai_gender" not in user_profile:
        user_profile["ai_gender"] = "中性"

    if "personality" not in user_profile or not user_profile["personality"]:
        user_profile["personality"] = {}
        for setting in FREE_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        if "付費用戶" in user_profile and user_profile["付費用戶"]:
            for setting in PAID_PERSONALITY_SETTINGS:
                user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        save_json(get_user_file(user_id, "user_profile"), user_profile)
        line_bot_api.reply(event.reply_token, [TextMessage(text="✅ 你的 AI 朋友個性已設定完成！開始聊天吧 🎉")])
        return

    # 調整個性設定
    if user_input == "調整設定":
        for setting in FREE_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        if "付費用戶" in user_profile and user_profile["付費用戶"]:
            for setting in PAID_PERSONALITY_SETTINGS:
                user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        save_json(get_user_file(user_id, "user_profile"), user_profile)
        line_bot_api.reply(event.reply_token, [TextMessage(text="✅ AI 個性已更新！請繼續聊天～")])
        return

    # 讀取個性設定
    personality = user_profile["personality"]
    humor = personality.get("幽默感", 4)
    warmth = personality.get("溫暖程度", 4)
    optimism = personality.get("樂觀度", 4)
    tone = personality.get("回應態度", 4)
    talkativeness = personality.get("健談程度", 4)

    # 生成 AI 回應
    prompt = (
        f"你是一個 AI 朋友，請根據以下個性設定來回應使用者：\n"
        f"- 幽默感：{humor}/7\n"
        f"- 溫暖程度：{warmth}/7\n"
        f"- 樂觀度：{optimism}/7\n"
        f"- 回應風格：{tone}（1=年輕, 7=成熟）\n"
        f"- 健談程度：{talkativeness}/7\n"
        f"使用者說：{user_input}"
    )

    try:
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
    except Exception as e:
        ai_response = "哎呀，好像出了點問題，我晚點再試試吧！"
        print(f"Error: {e}")

    # 回覆使用者
    line_bot_api.reply(event.reply_token, [TextMessage(text=ai_response)])

    # 儲存對話歷史
    messages.append({"user": user_input, "ai": ai_response})
    save_json(get_user_file(user_id, "chat_history"), messages)

if __name__ == "__main__":
    app.run(port=5000)