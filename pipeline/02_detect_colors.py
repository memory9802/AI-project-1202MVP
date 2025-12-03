"""
顏色辨識處理 - 整合版
結合 K-Means 聚類、HSV 色相分析、Pantone 色號對應

輸入: init/uniqlo_175.csv
輸出: init/uniqlo_175_colored.csv
新增欄位: color (Pantone格式)
"""

import pandas as pd
import numpy as np
import requests
from PIL import Image
from io import BytesIO
from sklearn.cluster import KMeans
from collections import Counter
import time
import colorsys

# 可選依賴
try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("⚠️  rembg 未安裝，將使用原始圖片")

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("⚠️  OpenCV 未安裝，部分功能受限")


# ==================== Pantone 色號系統 ====================
PANTONE_COLORS = {
    # 無彩色系
    "黑色 (Pantone Black 6)": {"rgb": (0, 0, 0), "h_range": None, "v_max": 20},
    "白色 (Pantone White)": {"rgb": (255, 255, 255), "h_range": None, "v_min": 90},
    "深灰色 (Pantone Cool Gray 11)": {"rgb": (83, 86, 90), "h_range": (180, 270), "v_range": (20, 40)},
    "灰色 (Pantone Cool Gray 8)": {"rgb": (147, 149, 152), "h_range": (180, 270), "v_range": (40, 65)},
    "淺灰色 (Pantone Cool Gray 3)": {"rgb": (200, 201, 202), "h_range": (180, 270), "v_range": (65, 90)},
    
    # 藍色系 (H: 180-240)
    "深藍色 (Pantone 2767 C)": {"rgb": (13, 36, 107), "h_range": (200, 240)},
    "藍色 (Pantone 2945 C)": {"rgb": (0, 102, 179), "h_range": (190, 220)},
    "淺藍色 (Pantone 283 C)": {"rgb": (155, 194, 230), "h_range": (180, 210)},
    
    # 綠色系 (H: 80-180)
    "深綠色 (Pantone 3308 C)": {"rgb": (0, 86, 63), "h_range": (130, 160)},
    "綠色 (Pantone 355 C)": {"rgb": (0, 135, 68), "h_range": (120, 180)},
    "淺綠色 (Pantone 351 C)": {"rgb": (175, 215, 145), "h_range": (80, 130)},
    
    # 紅色系 (H: 330-30)
    "正紅色 (Pantone 186 C)": {"rgb": (200, 16, 46), "h_range": (350, 10)},
    "深紅色 (Pantone 1815 C)": {"rgb": (135, 0, 35), "h_range": (340, 0)},
    "粉紅色 (Pantone 189 C)": {"rgb": (247, 168, 184), "h_range": (330, 360)},
    "酒紅色 (Pantone 209 C)": {"rgb": (123, 30, 66), "h_range": (330, 350)},
    
    # 黃色系 (H: 40-60)
    "黃色 (Pantone 109 C)": {"rgb": (255, 209, 0), "h_range": (45, 60)},
    "淺黃色 (Pantone 100 C)": {"rgb": (244, 223, 142), "h_range": (40, 55)},
    
    # 橘色系 (H: 10-40)
    "橘色 (Pantone 021 C)": {"rgb": (254, 80, 0), "h_range": (15, 35)},
    
    # 紫色系 (H: 270-330)
    "深紫色 (Pantone 2627 C)": {"rgb": (82, 35, 152), "h_range": (270, 290)},
    "紫色 (Pantone 2685 C)": {"rgb": (140, 91, 170), "h_range": (280, 310)},
    "淺紫色 (Pantone 2567 C)": {"rgb": (199, 180, 217), "h_range": (270, 300)},
    
    # 棕色系 (H: 20-40, 低飽和度)
    "深咖啡色 (Pantone 476 C)": {"rgb": (75, 56, 42), "h_range": (20, 40), "s_max": 50},
    "咖啡色 (Pantone 4625 C)": {"rgb": (120, 94, 74), "h_range": (20, 40)},
    "米色 (Pantone 468 C)": {"rgb": (214, 196, 166), "h_range": (30, 50), "s_max": 40},
    "卡其色 (Pantone 7502 C)": {"rgb": (164, 143, 110), "h_range": (30, 50)},
}


# ==================== 圖片處理函數 ====================
def download_image(url: str, timeout: int = 20) -> Image.Image:
    """下載圖片"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.uniqlo.com/',
    }
    response = requests.get(url, timeout=timeout, headers=headers)
    response.raise_for_status()
    img = Image.open(BytesIO(response.content)).convert('RGB')
    return img


def remove_background(img: Image.Image) -> Image.Image:
    """背景去除 (可選)"""
    if not HAS_REMBG:
        return img
    try:
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        result = remove(img_bytes.read())
        return Image.open(BytesIO(result)).convert('RGB')
    except Exception as e:
        print(f"背景去除失敗: {e}")
        return img


def extract_dominant_color_kmeans(img: Image.Image, k: int = 5) -> tuple:
    """
    使用 K-Means 提取主色調
    
    Args:
        img: PIL Image
        k: 聚類數量
        
    Returns:
        (r, g, b) 主色調RGB值
    """
    # 縮小圖片加速處理
    img_small = img.resize((150, 150))
    pixels = np.array(img_small).reshape(-1, 3)
    
    # 過濾低亮度像素 (陰影)
    hsv_pixels = np.array([colorsys.rgb_to_hsv(r/255, g/255, b/255) for r, g, b in pixels])
    mask = hsv_pixels[:, 2] > 0.2  # 保留 V > 20% 的像素
    filtered_pixels = pixels[mask]
    
    if len(filtered_pixels) < k:
        filtered_pixels = pixels  # 回退到全部像素
    
    # K-Means 聚類
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)
    
    # 找出最大聚類的中心點
    labels = kmeans.labels_
    counts = Counter(labels)
    dominant_cluster = counts.most_common(1)[0][0]
    dominant_color = kmeans.cluster_centers_[dominant_cluster]
    
    return tuple(map(int, dominant_color))


def rgb_to_hsv_360(r: int, g: int, b: int) -> tuple:
    """RGB轉HSV (H: 0-360)"""
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    return (h * 360, s * 100, v * 100)


def match_pantone_color(rgb: tuple) -> str:
    """
    匹配 Pantone 色號
    
    Args:
        rgb: (r, g, b) tuple
        
    Returns:
        最接近的 Pantone 色號字串
    """
    r, g, b = rgb
    h, s, v = rgb_to_hsv_360(r, g, b)
    
    # 優先處理無彩色
    if v < 20:
        return "黑色 (Pantone Black 6)"
    if v > 90 and s < 10:
        return "白色 (Pantone White)"
    if 180 <= h <= 270 and s < 20:
        if v < 40:
            return "深灰色 (Pantone Cool Gray 11)"
        elif v < 65:
            return "灰色 (Pantone Cool Gray 8)"
        else:
            return "淺灰色 (Pantone Cool Gray 3)"
    
    # 有彩色匹配
    best_match = None
    min_distance = float('inf')
    
    for color_name, color_data in PANTONE_COLORS.items():
        # 跳過無彩色
        if color_data.get('h_range') is None:
            continue
            
        # 色相範圍檢查
        h_min, h_max = color_data['h_range']
        if h_min > h_max:  # 跨越0度的情況 (紅色)
            in_range = (h >= h_min or h <= h_max)
        else:
            in_range = (h_min <= h <= h_max)
        
        if not in_range:
            continue
            
        # 特殊條件檢查 (飽和度、明度)
        if 's_max' in color_data and s > color_data['s_max']:
            continue
        if 'v_range' in color_data:
            v_min, v_max = color_data['v_range']
            if not (v_min <= v <= v_max):
                continue
        
        # 計算歐式距離
        ref_r, ref_g, ref_b = color_data['rgb']
        distance = np.sqrt((r - ref_r)**2 + (g - ref_g)**2 + (b - ref_b)**2)
        
        if distance < min_distance:
            min_distance = distance
            best_match = color_name
    
    return best_match or "灰色 (Pantone Cool Gray 8)"


# ==================== 批次處理 ====================
def process_color_detection(input_csv: str, output_csv: str):
    """
    批次顏色辨識
    
    Args:
        input_csv: 輸入CSV檔案路徑
        output_csv: 輸出CSV檔案路徑
    """
    print("=" * 80)
    print("🎨 顏色辨識處理")
    print("=" * 80)
    
    df = pd.read_csv(input_csv)
    print(f"讀取 {len(df)} 筆商品")
    
    # 如果已有 color 欄位，備份
    if 'color' in df.columns:
        df['color_old'] = df['color']
    
    colors = []
    failed_count = 0
    
    for idx, row in df.iterrows():
        print(f"\n處理 [{idx+1}/{len(df)}] {row['name']}")
        
        try:
            # 下載圖片
            img = download_image(row['image_url'], timeout=20)
            
            # 去背 (可選)
            if HAS_REMBG:
                img = remove_background(img)
            
            # 提取主色調
            dominant_rgb = extract_dominant_color_kmeans(img, k=5)
            print(f"  主色調 RGB: {dominant_rgb}")
            
            # 匹配 Pantone
            pantone = match_pantone_color(dominant_rgb)
            colors.append(pantone)
            print(f"  ✅ {pantone}")
            
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
            colors.append('-')
            failed_count += 1
        
        # 每10筆自動存檔
        if (idx + 1) % 10 == 0:
            df_temp = df.copy()
            df_temp['color'] = colors + ['-'] * (len(df) - len(colors))
            df_temp.to_csv(output_csv, index=False, encoding='utf-8')
            print(f"\n💾 已自動存檔 ({idx+1}/{len(df)})")
        
        time.sleep(1)  # 避免請求過快
    
    # 最終儲存
    df['color'] = colors
    df.to_csv(output_csv, index=False, encoding='utf-8')
    
    print("\n" + "=" * 80)
    print(f"✅ 處理完成")
    print(f"   成功: {len(df) - failed_count}")
    print(f"   失敗: {failed_count}")
    print(f"   輸出: {output_csv}")
    print("=" * 80)


def main():
    """主程式"""
    input_file = 'init/uniqlo_175.csv'
    output_file = 'init/uniqlo_175_colored.csv'
    
    process_color_detection(input_file, output_file)


if __name__ == '__main__':
    main()
