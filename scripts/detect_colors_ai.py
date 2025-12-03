import pandas as pd
import requests
import base64
import os
import time
import json
import re

# 讀取 .env 檔案中的 API Key
def get_api_key():
    api_key = os.getenv('LLM_API_KEY')
    if not api_key:
        # 嘗試從 .env 檔案讀取
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('LLM_API_KEY='):
                        api_key = line.strip().split('=')[1]
                        break
        except:
            pass
    return api_key

def analyze_image_with_gemini(api_key, image_url, item_name):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    
    try:
        # 下載圖片
        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()
        img_data = base64.b64encode(img_response.content).decode('utf-8')
        
        # 建構請求
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"請看這張圖片。請辨識圖片中名為「{item_name}」的商品的主要顏色。請只回答顏色名稱（例如：白色、黑色、深藍色、卡其色等），不要有其他文字。如果無法辨識，請回答「未指定」。"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 20
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            try:
                color = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return color
            except (KeyError, IndexError):
                return "解析失敗"
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return "API錯誤"
            
    except Exception as e:
        print(f"Error: {e}")
        return "處理失敗"

def main():
    input_file = 'init/uniqlo_175.csv'
    output_file = 'init/uniqlo_175_colored_ai.csv'
    
    api_key = get_api_key()
    if not api_key:
        print("❌ 找不到 LLM_API_KEY，請檢查 .env 檔案")
        return

    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # 測試模式：只跑前 5 筆
    # 如果要跑全部，請註解掉下面這行
    df_to_process = df.head(5).copy()
    # df_to_process = df.copy() # 跑全部
    
    print(f"Starting AI color recognition for {len(df_to_process)} items...")
    print(f"Using model: gemini-2.0-flash-lite")
    
    results = []
    
    for index, row in df_to_process.iterrows():
        image_url = row['image_url']
        name = row['name']
        
        print(f"Processing [{index+1}/{len(df_to_process)}]: {name}")
        
        if pd.isna(image_url):
            color = "無圖片"
        else:
            color = analyze_image_with_gemini(api_key, image_url, name)
            # 清理結果 (移除換行符號等)
            color = color.replace('\n', '').strip()
            
        print(f"  -> AI Result: {color}")
        
        # 更新 DataFrame
        df.at[index, 'color'] = color
        
        # 速率限制 (Gemini 2.0 Flash Lite 限制較寬鬆，但安全起見)
        time.sleep(2)
        
    print(f"Saving results to {output_file}...")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("Done!")

if __name__ == "__main__":
    main()
