import pandas as pd

# 讀 Kaggle 的 styles.csv（圖片檔在 images/ 資料夾）
STYLES_CSV = "styles.csv"

df = pd.read_csv(STYLES_CSV, on_bad_lines="skip")

# 只保留我們要用的欄位
def build_items(df):
    rows = []

    for _, row in df.iterrows():
        sku = str(row["id"])
        name = str(row.get("productDisplayName", "")).strip()

        # 這邊先用 articleType 當 category（之後你要再 mapping 成 top/bottom/outer也可以）
        category = str(row.get("articleType", "")).strip()
        color = str(row.get("baseColour", "")).strip()

        # 這份 dataset 沒有價格，先留空或之後自己生
        price = ""

        # 圖片檔通常是 images/<id>.jpg，你之後可以把 images/ 這個資料夾當成靜態服務目錄
        image_url = f"images/{sku}.jpg"

        source = "kaggle_fashion_small"
        url = ""  # 原始商品頁網址不可得，先留空

        rows.append({
            "sku": sku,
            "name": name,
            "category": category,
            "color": color,
            "price": price,
            "image_url": image_url,
            "source": source,
            "url": url,
        })

    return pd.DataFrame(rows)

items_df = build_items(df)

# 你不一定要全部 44k，先取 5000 筆也可以
items_df = items_df.head(5000)

items_df.to_csv("items_fashion_small.csv", index=False, encoding="utf-8-sig")
print("輸出 items_fashion_small.csv，筆數：", len(items_df))
