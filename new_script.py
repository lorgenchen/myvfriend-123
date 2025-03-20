import google.generativeai as genai

genai.configure(api_key="AIzaSyCWt50sJDXDeZv6YNO2IBrUzI3fzhRlJc8")

try:
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content("請回答：API 測試成功。")
    print("API 測試結果：")
    print(response.text)
except Exception as e:
    print(f"API 測試失敗: {e}")
