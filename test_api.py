import google.generativeai as genai

# 設定 Google Gemini API Key（請替換為你的 API Key）
genai.configure(api_key="AIzaSyD0Y3DhXEFg-4Ymj4cksNDmfQwaTqHNKGY")

# 測試 API 是否可用
try:
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content("請回答：API 測試成功。")
    print("API 測試結果：")
    print(response.text)  # 讓 AI 回應簡單的測試訊息
except Exception as e:
    print(f"API 測試失敗: {e}")
