import os
import json
import time
import google.generativeai as genai
from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

# 設定 Google Gemini API Key
genai.configure(api_key="AIzaSyCWt50sJDXDeZv6YNO2IBrUzI3fzhRlJc8")

# 設定 LINE API 金鑰
LINE_CHANNEL_ACCESS_TOKEN = "ZYpzlW52BLY2pTn83wKh5N2FfJbr/6URE6ViA44MgpilumDlugc2uORE4ayfEjSFlIbONKLFxkLpn84bn8aeCre/J45SO7YnRX3eH0u1VuskXhsIqXEFYfoiamKFB2/3A4+TQQQpaoRQ40ScwltAMwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "e4420ff35c2ce0c086c765faa0c3a3b2"

app = Flask(__name__)

# **修正 `MessagingApi` 初始化方式**
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 設定 Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"Webhook Error: {e}")
        abort(400)
    return "OK", 200

# 處理 LINE 訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_input = event.message.text.strip()

    # 讓 AI 產生回應
    prompt = f"使用者說：{user_input}"
    response = genai.GenerativeModel("gemini-1.5-pro").generate_content(prompt)
    response_text = response.text.strip()

    # **修正 `push_message` 方法**
    line_bot_api.push_message(
        user_id,
        TextMessageContent(text=response_text)
    )

# 啟動 Flask 伺服器
if __name__ == "__main__":
    app.run(port=5000)
