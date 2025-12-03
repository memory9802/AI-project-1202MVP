import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import random
import re

LIST_URL = "https://themewagon.github.io/malefashion/shop.html"
BASE_URL = "https://themewagon.github.io/malefashion/"

# 目標要爬到的筆數（如果原始頁面筆數不足，會用簡單變體補足）
# 可以設定成 50 到 100 之間，例如 80
TARGET_COUNT = 80

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RubyCrawler/1.0; +https://example.com)"
}

# 關鍵字簡單判斷 top / bottom
CLOTHING_KEYWORDS_TOP = [
    "jacket", "t-shirt", "shirt", "coat", "hoodie", "sweatshirt"
]
CLOTHING_KEYWORDS_BOTTOM = [
    "jeans", "pant", "trouser", "shorts"
]
COLOR_WORDS = ["black", "white", "blue", "red", "green",
               "brown", "grey", "gray", "yellow", "beige"]


def guess_category(name: str) -> str:
    n = name.lower()
    if any(k in n for k in CLOTHING_KEYWORDS_TOP):
        return "top"
    if any(k in n for k in CLOTHING_KEYWORDS_BOTTOM):
        return "bottom"
    return "other"


def guess_color(name: str) -> str:
    n = name.lower()
    for c in COLOR_WORDS:
        if c in n:
            return c
    return ""


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_list_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # 這個模板的商品圖片區塊會有 data-setbg 屬性
    img_blocks = soup.find_all(attrs={"data-setbg": True})
    print(f"DEBUG: 找到 data-setbg 圖片區塊 {len(img_blocks)} 個")

    for img_block in img_blocks:
        # 從圖片區塊往後找最近的商品名稱 (h6) 和價格 (h5)
        name_tag = img_block.find_next("h6")
        price_tag = name_tag.find_next("h5") if name_tag else None

        if not (name_tag and price_tag):
            continue

        name = name_tag.get_text(strip=True)
        price = price_tag.get_text(strip=True)

        # 只保留衣服 / 褲子
        category = guess_category(name)
        if category == "other":
            continue

        img_rel = img_block.get("data-setbg", "").strip()
        if not img_rel:
            continue

        image_url = urljoin(BASE_URL, img_rel)

        color = guess_color(name)

        items.append({
            "name": name,
            "category": category,
            "color": color,
            "price": price,
            "image_url": image_url,
        })

    return items


def save_to_csv(items, filename="items_malefashion.csv"):
    if not items:
        print("沒有資料，CSV 不會產生。")
        return

    fieldnames = ["sku", "name", "category", "color", "price", "image_url"]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, item in enumerate(items, start=1):
            sku = f"MF-{idx:03d}"
            writer.writerow({
                "sku": sku,
                "name": item["name"],
                "category": item["category"],
                "color": item["color"],
                "price": item["price"],
                "image_url": item["image_url"],
            })

    print(f"已寫入 {len(items)} 筆商品到 {filename}")


def augment_items(items, target_count: int):
    """如果 items 筆數小於 target_count，就用現有 items 製造變體來補足。

    變體策略：重複現有商品，對名稱加上 (Variant N)，並隨機調整價格 +/-15%。
    這是為了在測試或資料準備階段快速產生較多的商品；長期應改為爬多個分頁或更多來源。
    """
    if not items:
        return items

    out = list(items)
    i = 0
    while len(out) < target_count:
        base = items[i % len(items)]
        new = base.copy()

        variant_num = len(out) + 1
        new['name'] = f"{base['name']} (Variant {variant_num})"

        # 嘗試解析數字價格並隨機調整
        price_text = base.get('price', '')
        m = re.search(r"[\d\.,]+", price_text)
        if m:
            raw = m.group(0).replace(',', '')
            try:
                pv = float(raw)
                change = random.uniform(-0.15, 0.15)
                new_price = max(0.5, pv * (1 + change))
                new['price'] = f"${new_price:,.2f}"
            except Exception:
                new['price'] = price_text
        else:
            new['price'] = price_text

        # 小幅調整 color 保持一致（可擴充）
        new['color'] = base.get('color', '')

        out.append(new)
        i += 1

    return out


def main():
    html = fetch_html(LIST_URL)
    items = parse_list_page(html)
    print(f"實際留下 {len(items)} 筆『服飾』商品，預覽前幾筆：")
    for i, item in enumerate(items[:5], start=1):
        print(f"{i}. {item['name']} | {item['price']} | {item['category']} | {item['color']}")
        print(f"   img: {item['image_url']}")
        print("-" * 50)

    # 如果筆數不足，就用簡單變體補足到 TARGET_COUNT
    if len(items) < TARGET_COUNT:
        print(f"筆數 {len(items)} 少於 TARGET_COUNT={TARGET_COUNT}，將使用 augment_items 補足。")
        items = augment_items(items, TARGET_COUNT)
        print(f"補足後共有 {len(items)} 筆（含變體）。")

    save_to_csv(items)


if __name__ == "__main__":
    main()
