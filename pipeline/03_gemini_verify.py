"""
Gemini Vision API 驗證 - 整合版
使用 Google Gemini 2.0 Flash 驗證所有商品屬性

輸入: init/uniqlo_175_colored.csv
輸出: init/gemini_verification_complete.csv
驗證欄位: gender, category, clothing_type, length, color
"""

import os
import pandas as pd
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
import time
import json
from datetime import datetime

# ==================== 配置 ====================
API_KEY = os.environ.get('GEMINI_API_KEY', '')

if not API_KEY:
    print("=" * 80)
    print("❌ 請設定 GEMINI_API_KEY 環境變數")
    print("=" * 80)
    print("\n方法1: 臨時設定 (當前終端有效)")
    print("  export GEMINI_API_KEY='your-api-key'")
    print("\n方法2: 永久設定 (寫入 ~/.zshrc 或 ~/.bash_profile)")
    print("  echo \"export GEMINI_API_KEY='your-api-key'\" >> ~/.zshrc")
    print("\n🔑 取得 API Key: https://aistudio.google.com/app/apikey")
    print("=" * 80)
    exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# ==================== 圖片處理 ====================
def download_image(url: str, timeout: int = 10) -> Image.Image:
    """下載商品圖片"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
        'Referer': 'https://www.uniqlo.com/',
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert('RGB')


# ==================== Gemini 分析 ====================
def analyze_with_gemini(image_url: str, product_name: str) -> dict:
    """
    使用 Gemini Vision 分析商品所有屬性
    
    Args:
        image_url: 圖片URL
        product_name: 商品名稱
        
    Returns:
        dict: {
            'gender': '男' or '女',
            'category': str (如: 男裝T恤上衣),
            'clothing_type': '上衣' or '下身',
            'length': '長' or '短',
            'color': str (中文顏色名)
        }
    """
    try:
        # 下載圖片
        img = download_image(image_url)
        
        # 構建 prompt
        prompt = f"""請仔細觀察這張 UNIQLO 服裝商品圖片，並分析以下5個屬性：

商品名稱：{product_name}

請依序判斷：

1. **性別 (gender)**：這是男裝還是女裝？
   - 觀察剪裁（男裝寬鬆/女裝修身）、領口設計、模特兒體型
   - 只回答：男 或 女

2. **類別 (category)**：這是什麼類型的服裝？
   - 例如：T恤上衣、襯衫、外套、牛仔褲、長褲等
   - 如果是男裝，格式：男裝XXX 或 男士XXX
   - 如果是女裝，格式：女裝XXX 或 女士XXX

3. **服裝類型 (clothing_type)**：這是上衣還是下身？
   - 觀察服裝覆蓋的身體部位
   - 只回答：上衣 或 下身

4. **長度 (length)**：袖長或褲長？
   - 上衣：長袖、短袖、五分袖、無袖 → 長 或 短
   - 下身：長褲、短褲、七分褲 → 長 或 短
   - 只回答：長 或 短

5. **顏色 (color)**：主要顏色是什麼？
   - 請用中文回答（如：白色、黑色、深藍色、淺灰色等）
   - 如果有多種顏色，回答最主要的顏色

**重要**：
- 請嚴格按照以下 JSON 格式回答
- 不要有任何額外說明或推測
- 如果無法判斷，該欄位填 "-"

JSON格式：
{{
  "gender": "男",
  "category": "男裝T恤上衣",
  "clothing_type": "上衣",
  "length": "短",
  "color": "白色"
}}
"""
        
        # 呼叫 Gemini API
        response = model.generate_content([prompt, img])
        result_text = response.text.strip()
        
        # 解析 JSON
        # 去除可能的 markdown 包裝
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            result_text = result_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(result_text)
        
        return {
            'Gemini gender': result.get('gender', '-'),
            'Gemini category': result.get('category', '-'),
            'Gemini clothing_type': result.get('clothing_type', '-'),
            'Gemini length': result.get('length', '-'),
            'Gemini color': result.get('color', '-')
        }
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 解析失敗: {e}")
        print(f"  原始回應: {result_text[:200]}")
        return {
            'Gemini gender': '-',
            'Gemini category': '-',
            'Gemini clothing_type': '-',
            'Gemini length': '-',
            'Gemini color': '-'
        }
    except Exception as e:
        print(f"  ❌ Gemini 分析失敗: {e}")
        return {
            'Gemini gender': '-',
            'Gemini category': '-',
            'Gemini clothing_type': '-',
            'Gemini length': '-',
            'Gemini color': '-'
        }


# ==================== 批次處理 ====================
def batch_verify_with_gemini(input_csv: str, output_csv: str, start_row: int = 0):
    """
    批次使用 Gemini 驗證所有商品
    
    Args:
        input_csv: 輸入CSV檔案
        output_csv: 輸出CSV檔案
        start_row: 從第幾行開始 (0-based)
    """
    print("=" * 80)
    print("🔍 Gemini Vision API 批次驗證")
    print("=" * 80)
    
    df = pd.read_csv(input_csv)
    print(f"讀取 {len(df)} 筆商品")
    print(f"開始行數: {start_row}")
    
    # 初始化 Gemini 結果欄位
    for col in ['Gemini gender', 'Gemini category', 'Gemini clothing_type', 'Gemini length', 'Gemini color']:
        if col not in df.columns:
            df[col] = '-'
    
    # 逐筆處理
    failed_count = 0
    for idx in range(start_row, len(df)):
        row = df.iloc[idx]
        print(f"\n處理 [{idx+1}/{len(df)}] {row['name']}")
        
        try:
            # 呼叫 Gemini
            gemini_result = analyze_with_gemini(row['image_url'], row['name'])
            
            # 更新結果
            for key, value in gemini_result.items():
                df.at[idx, key] = value
            
            print(f"  ✅ 性別: {gemini_result['Gemini gender']}, "
                  f"類別: {gemini_result['Gemini category']}, "
                  f"顏色: {gemini_result['Gemini color']}")
            
        except Exception as e:
            print(f"  ❌ 處理失敗: {e}")
            failed_count += 1
        
        # 每5筆自動存檔
        if (idx + 1) % 5 == 0:
            df.to_csv(output_csv, index=False, encoding='utf-8')
            print(f"\n💾 已自動存檔 ({idx+1}/{len(df)})")
        
        # API 限速保護
        time.sleep(2)
    
    # 最終儲存
    df.to_csv(output_csv, index=False, encoding='utf-8')
    
    print("\n" + "=" * 80)
    print(f"✅ 驗證完成")
    print(f"   成功: {len(df) - failed_count - start_row}")
    print(f"   失敗: {failed_count}")
    print(f"   輸出: {output_csv}")
    print("=" * 80)
    
    # 顯示對比統計
    if 'gender' in df.columns:
        print("\n📊 對比統計:")
        for col_base in ['gender', 'clothing_type', 'length']:
            col_gemini = f'Gemini {col_base}'
            if col_gemini in df.columns:
                differences = (df[col_base] != df[col_gemini]).sum()
                total = len(df) - (df[col_gemini] == '-').sum()
                accuracy = (1 - differences / total) * 100 if total > 0 else 0
                print(f"  {col_base}: {differences} 筆不同 (準確率: {accuracy:.1f}%)")


def main():
    """主程式"""
    input_file = 'init/uniqlo_175_colored.csv'
    output_file = 'init/gemini_verification_complete.csv'
    
    print("\n提示: 如需從特定行繼續處理，請修改 start_row 參數")
    print("例如: batch_verify_with_gemini(input_file, output_file, start_row=50)\n")
    
    batch_verify_with_gemini(input_file, output_file, start_row=0)


if __name__ == '__main__':
    main()
