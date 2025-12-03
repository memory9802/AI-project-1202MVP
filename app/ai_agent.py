import google.generativeai as genai
import os

# 檢查 API key
api_key = os.getenv("LLM_API_KEY")
if not api_key:
    print("沒有讀到 API key，請確認 docker-compose.yml 是否有設定 LLM_API_KEY")
else:
    print("已讀取 API key:", api_key[:10], "...")

try:
    # 設定模型（請用 gemini-pro，不要用 gemini-1.5）
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    print("正在呼叫 Gemini API ...")

    # 呼叫模型產生內容
    response = model.generate_content("幫我推薦今天適合穿什麼？")

    # 輸出結果
    print("AI 回覆：", response.text)

except Exception as e:
    print("發生錯誤：", str(e))
