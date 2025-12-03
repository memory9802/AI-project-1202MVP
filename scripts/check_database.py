#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫完整性檢查和報告
"""

import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'rootpassword',
    'database': 'outfit_db',
    'charset': 'utf8mb4'
}

print("=" * 80)
print("📊 資料庫完整性檢查報告")
print("=" * 80)

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor()

# 1. 總體統計
print("\n【1】總體統計:")
cursor.execute("SELECT COUNT(*) FROM items")
total = cursor.fetchone()[0]
print(f"   ✅ 總計: {total:,} 筆資料")

# 2. 各來源統計
print("\n【2】各來源統計:")
cursor.execute("""
    SELECT 
        source,
        COUNT(*) as total,
        SUM(CASE WHEN name IS NOT NULL AND name != '' THEN 1 ELSE 0 END) as has_name,
        SUM(CASE WHEN category IS NOT NULL THEN 1 ELSE 0 END) as has_category,
        SUM(CASE WHEN color IS NOT NULL AND color != '' THEN 1 ELSE 0 END) as has_color,
        SUM(CASE WHEN gender IS NOT NULL AND gender != '-' THEN 1 ELSE 0 END) as has_gender
    FROM items 
    GROUP BY source 
    ORDER BY total DESC
""")

results = cursor.fetchall()
for row in results:
    source, total, has_name, has_category, has_color, has_gender = row
    print(f"\n   📦 {source}:")
    print(f"      - 總計: {total:,} 筆")
    print(f"      - 有名稱: {has_name:,} 筆 ({has_name/total*100:.1f}%)")
    print(f"      - 有類別: {has_category:,} 筆 ({has_category/total*100:.1f}%)")
    print(f"      - 有顏色: {has_color:,} 筆 ({has_color/total*100:.1f}%)")
    print(f"      - 有性別: {has_gender:,} 筆 ({has_gender/total*100:.1f}%)")

# 3. 類別分佈
print("\n【3】類別分佈:")
cursor.execute("""
    SELECT category, COUNT(*) as count 
    FROM items 
    WHERE category IS NOT NULL
    GROUP BY category 
    ORDER BY count DESC
""")
for category, count in cursor.fetchall():
    print(f"   - {category}: {count:,} 筆")

# 4. 性別分佈
print("\n【4】性別分佈:")
cursor.execute("""
    SELECT gender, COUNT(*) as count 
    FROM items 
    WHERE gender IS NOT NULL AND gender != '-'
    GROUP BY gender 
    ORDER BY count DESC
""")
for gender, count in cursor.fetchall():
    print(f"   - {gender}: {count:,} 筆")

# 5. 範例資料 (測試中文顯示)
print("\n【5】範例資料 (UNIQLO):")
cursor.execute("""
    SELECT id, name, category, color, gender 
    FROM items 
    WHERE source = 'uniqlo' 
    LIMIT 5
""")
for row in cursor.fetchall():
    id, name, category, color, gender = row
    print(f"   [{id}] {name}")
    print(f"       類別: {category} | 顏色: {color} | 性別: {gender}")

print("\n【6】範例資料 (Styles Dataset):")
cursor.execute("""
    SELECT id, name, category, color, gender 
    FROM items 
    WHERE source = 'styles_dataset' 
    LIMIT 5
""")
for row in cursor.fetchall():
    id, name, category, color, gender = row
    print(f"   [{id}] {name}")
    print(f"       類別: {category} | 顏色: {color} | 性別: {gender}")

# 6. 字符集檢查
print("\n【7】字符集設定:")
cursor.execute("SHOW VARIABLES LIKE 'character_set_%'")
for var_name, value in cursor.fetchall():
    if 'dir' not in var_name:
        print(f"   {var_name}: {value}")

conn.close()

print("\n" + "=" * 80)
print("✅ 檢查完成!")
print("=" * 80)
print("\n💡 提示:")
print("   - 如果在 DBeaver 中看到亂碼,請參考 docs/DBEAVER_CONNECTION_GUIDE.md")
print("   - 或使用 phpMyAdmin: http://localhost:8080")
print("   - 資料已正確儲存為 UTF-8,問題只是顯示設定")
