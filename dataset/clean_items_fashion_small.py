import pandas as pd

INPUT = "items_fashion_small.csv"
OUTPUT = "items_fashion_small_clean.csv"

df = pd.read_csv(INPUT)

# 只保留你要的 6 個欄位（順序也統一）
cols = ["sku", "name", "category", "color", "price", "image_url"]
df_clean = df[cols]

df_clean.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
print(f"輸出 {OUTPUT}，筆數：", len(df_clean))
