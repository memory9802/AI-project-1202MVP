import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import numpy as np
from sklearn.cluster import KMeans
import time
import re

# 定義基本顏色及其 RGB 值
COLORS = {
    '白色': (255, 255, 255),
    '黑色': (0, 0, 0),
    '灰色': (128, 128, 128),
    '紅色': (255, 0, 0),
    '粉紅色': (255, 192, 203),
    '橘色': (255, 165, 0),
    '米色': (245, 245, 220),
    '棕色': (165, 42, 42),
    '卡其色': (195, 176, 145),
    '黃色': (255, 255, 0),
    '綠色': (0, 128, 0),
    '藍色': (0, 0, 255),
    '深藍色': (0, 0, 139),
    '紫色': (128, 0, 128),
    '牛仔藍': (70, 130, 180),
}

def get_closest_color_name(rgb):
    min_dist = float('inf')
    closest_name = '未指定'
    
    r, g, b = rgb
    
    for name, color_rgb in COLORS.items():
        cr, cg, cb = color_rgb
        # 使用歐幾里得距離
        dist = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest_name = name
            
    return closest_name

def is_skin_tone(r, g, b):
    # 簡單的膚色檢測規則 (這只是一個粗略的近似)
    return r > 95 and g > 40 and b > 20 and r > g and r > b and abs(r - g) > 15 and r > 150 and g > 100

def extract_dominant_color(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGB')
        img = img.resize((100, 100)) # 縮小以加速處理
        
        # 轉換為 numpy array
        data = np.array(img)
        pixels = data.reshape(-1, 3)
        
        # 過濾背景 (假設背景接近白色)
        # 過濾掉亮度非常高的像素
        filtered_pixels = []
        for p in pixels:
            r, g, b = p
            # 過濾白色/接近白色背景
            if r > 240 and g > 240 and b > 240:
                continue
            # 嘗試過濾膚色 (如果需要) - 這裡先保留，因為有些衣服可能是膚色/米色
            # if is_skin_tone(r, g, b):
            #     continue
            filtered_pixels.append(p)
            
        if not filtered_pixels:
            # 如果過濾後沒剩什麼 (例如全白衣服)，就用原始像素，但排除絕對白色
             filtered_pixels = [p for p in pixels if not (p[0] > 250 and p[1] > 250 and p[2] > 250)]
             if not filtered_pixels:
                 return (255, 255, 255) # 真的全白

        filtered_pixels = np.array(filtered_pixels)
        
        if len(filtered_pixels) == 0:
             return (255, 255, 255)

        # 使用 KMeans 找出主要顏色
        kmeans = KMeans(n_clusters=1, n_init=10)
        kmeans.fit(filtered_pixels)
        dominant_color = kmeans.cluster_centers_[0]
        
        return tuple(map(int, dominant_color))
        
    except Exception as e:
        print(f"Error processing {image_url}: {e}")
        return None

def main():
    input_file = 'init/uniqlo_175.csv'
    output_file = 'init/uniqlo_175_colored.csv'
    
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    # 為了測試，先只跑前 10 筆，如果要跑全部請註解掉下面這行
    # df = df.head(10) 
    
    print("Starting color recognition...")
    
    for index, row in df.iterrows():
        image_url = row['image_url']
        name = row['name']
        
        if pd.isna(image_url):
            continue
            
        print(f"Processing [{index+1}/{len(df)}]: {name}")
        
        rgb = extract_dominant_color(image_url)
        
        if rgb:
            color_name = get_closest_color_name(rgb)
            print(f"  -> Detected RGB: {rgb}, Color: {color_name}")
            df.at[index, 'color'] = color_name
        else:
            print("  -> Failed to detect color")
            
        # 避免請求過於頻繁
        time.sleep(0.5)
        
    print(f"Saving results to {output_file}...")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("Done!")

if __name__ == "__main__":
    main()
