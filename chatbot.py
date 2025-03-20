import google.generativeai as genai
import json
import os
import time

# 設定 Google Gemini API Key（請替換為你的 API Key）
genai.configure(api_key="AIzaSyCWt50sJDXDeZv6YNO2IBrUzI3fzhRlJc8")

# 選擇 Gemini AI 模型
model = genai.GenerativeModel("gemini-1.5-pro")

# 檔案名稱
HISTORY_FILE = "chat_history.json"
USER_PROFILE_FILE = "user_profile.json"

# **函式 1：讀取 JSON 資料**
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}

# **函式 2：儲存 JSON 資料**
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# **函式 3：取得使用者設定**
def get_setting(prompt):
    while True:
        try:
            value = int(input(f"{prompt}（1 = 最低, 7 = 最高，輸入 0 選擇『全部預設』）："))
            if value == 0:
                return 4  # 全部預設為 4
            elif 1 <= value <= 7:
                return value
            else:
                print("請輸入 1 到 7 之間的數字，或輸入 0 選擇『全部預設』！")
        except ValueError:
            print("請輸入一個數字！")

# 載入對話歷史與使用者個人資訊
messages = load_json(HISTORY_FILE)
user_profile = load_json(USER_PROFILE_FILE)

# **免費版可調整的 AI 朋友個性**
FREE_PERSONALITY_SETTINGS = [
    "幽默感", "主動關心頻率", "溫暖程度", "樂觀度", "回應態度", "健談程度", "AI 主動關心頻率"
]

# **進階（付費）版可調整的 AI 朋友個性**
PAID_PERSONALITY_SETTINGS = [
    "直率程度", "情緒應對方式", "建議提供程度", "深度話題程度"
]

# **確保 AI 性別設定存在**
if "ai_gender" not in user_profile:
    user_profile["ai_gender"] = "中性"

# **確保 AI 個性設定存在**
if "personality" not in user_profile or not user_profile["personality"]:
    print("🎭 讓我們設定你的 AI 朋友個性！")

    print("如果不確定如何設定，請輸入 **0**，我們會幫你設定為『預設值』！")
    user_profile["personality"] = {}

    for setting in FREE_PERSONALITY_SETTINGS:
        user_profile["personality"][setting] = get_setting(f"請設定 {setting}")

    # 付費版功能可解鎖額外設定
    if "付費用戶" in user_profile and user_profile["付費用戶"]:
        for setting in PAID_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}（付費功能）")

    save_json(USER_PROFILE_FILE, user_profile)
    print("✅ AI 個性設定完成！你可以開始聊天啦 🎉")

else:
    # **如果已有設定，詢問是否要重新調整**
    change_settings = input("你想要調整 AI 朋友的個性嗎？（輸入『是』來調整，或按 Enter 跳過）：").strip()
    if change_settings == "是":
        print("🎭 讓我們重新設定你的 AI 朋友個性！")
        for setting in FREE_PERSONALITY_SETTINGS:
            user_profile["personality"][setting] = get_setting(f"請設定 {setting}")
        if "付費用戶" in user_profile and user_profile["付費用戶"]:
            for setting in PAID_PERSONALITY_SETTINGS:
                user_profile["personality"][setting] = get_setting(f"請設定 {setting}（付費功能）")
        save_json(USER_PROFILE_FILE, user_profile)
        print("✅ AI 個性已更新！")

# **變數用來追蹤上次聊天時間**
last_interaction_time = time.time()

while True:
    # 讓使用者輸入問題
    user_input = input("你：").strip()
    last_interaction_time = time.time()  # 更新最近互動時間

    # **讀取 AI 朋友個性設定**
    personality = user_profile["personality"]
    humor = personality.get("幽默感", 4)
    caring_frequency = personality.get("主動關心頻率", 4)
    warmth = personality.get("溫暖程度", 4)
    optimism = personality.get("樂觀度", 4)
    tone = personality.get("回應態度", 4)
    talkativeness = personality.get("健談程度", 4)

    # **讓 AI 產生回應**
    prompt = (
        f"你是一個 AI 朋友，請根據以下個性設定來回應使用者：\n"
        f"- 幽默感：{humor}/7\n"
        f"- 主動關心頻率：{caring_frequency}/7\n"
        f"- 溫暖程度：{warmth}/7\n"
        f"- 樂觀度：{optimism}/7\n"
        f"- 回應風格：{tone}（1=年輕, 7=成熟）\n"
        f"- 健談程度：{talkativeness}/7\n"
        f"使用者說：{user_input}"
    )

    response = model.generate_content(prompt)
    ai_response = response.text.strip()
    print("AI：" + ai_response)

    # 儲存對話歷史
    messages.append({"user": user_input, "ai": ai_response})
    save_json(HISTORY_FILE, messages)
