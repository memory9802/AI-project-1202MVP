# 📁 資料庫檔案說明

## ⚠️ 重要規則:統一檔名!

**所有組員必須遵守:**
```
✅ 正確: init/outfit_db_with_data.sql  ← 唯一檔名
❌ 錯誤: init/outfit_db_20251126.sql   ← 不要自創檔名!
❌ 錯誤: init/outfit_db_john.sql
❌ 錯誤: init/outfit_db_final_v2.sql
```

**為什麼這麼重要?**
1. ✅ Git 自動追蹤版本,不需要檔名加日期
2. ✅ 大家永遠知道「最新版本」是哪個
3. ✅ 避免混亂 (不會有 10 個不同檔名)
4. ✅ 腳本和文檔都指向同一個檔案

**如何查看歷史版本?**
```bash
# Git 會保留所有版本歷史
git log init/outfit_db_with_data.sql

# 恢復舊版本 (如果需要)
git checkout <commit-hash> init/outfit_db_with_data.sql
```

---

## 🎯 給新組員:你只需要這個!

```bash
# 一鍵匯入完整資料庫
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < init/outfit_db_with_data.sql
```

**或使用自動化腳本:**
```bash
./scripts/setup_database_for_teammates.sh
```

---

## 📄 檔案說明

### ⭐ `outfit_db_with_data.sql` (8.2 MB)

**用途:** 完整資料庫備份 (結構 + 所有資料)

**包含內容:**
- ✅ 所有表格結構 (CREATE TABLE)
- ✅ 50 個測試用戶 (INSERT INTO users)
- ✅ 49,707 筆商品資料 (INSERT INTO items)
- ✅ 其他相關資料

**何時使用:**
- ✅ **新組員第一次設定** ← 最常用!
- ✅ 其他人通知「資料庫已更新」時
- ✅ 想要獲得完全相同的資料庫

**執行方式:**
```bash
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < init/outfit_db_with_data.sql
```

---

### 📋 `outfit_db.sql` (10 KB)

**用途:** 資料庫結構定義 (不含資料)

**包含內容:**
- ✅ CREATE DATABASE
- ✅ CREATE TABLE (所有表格結構)
- ❌ 沒有任何資料 (需要另外執行 Python 腳本)

**何時使用:**
- 📚 理解資料庫結構設計
- 🏗️ 從零建立空資料庫 (不常用)
- 🔧 修改表格結構時參考

**⚠️ 注意:**
- 如果你想要有資料的資料庫,請用 `outfit_db_with_data.sql`
- 執行此檔案後資料庫是空的,需要執行:
  ```bash
  python3 scripts/import_csv_to_db.py      # 匯入商品
  python3 scripts/generate_users_with_bcrypt.py  # 生成用戶
  ```

---

## 🤔 我該用哪個檔案?

| 情況 | 使用檔案 | 說明 |
|------|---------|------|
| 🆕 第一次設定環境 | `outfit_db_with_data.sql` | 一次獲得所有資料 |
| 🔄 同步組員的更新 | `outfit_db_with_data.sql` | 與其他人保持一致 |
| 📚 查看資料庫結構 | `outfit_db.sql` | 只看表格定義 |
| 🏗️ 從零建立空資料庫 | `outfit_db.sql` | 然後執行 Python 腳本 |

---

## ⚠️ 常見錯誤

### ❌ 錯誤:只匯入 outfit_db.sql

**症狀:** 資料庫建立成功,但查詢時:
```sql
SELECT COUNT(*) FROM users;
-- 結果: 0 (應該是 50)

SELECT COUNT(*) FROM items;
-- 結果: 0 (應該是 49,707)
```

**原因:** `outfit_db.sql` 只有結構,沒有資料

**解決方法:**
```bash
# 重新匯入完整備份
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < init/outfit_db_with_data.sql

# 驗證
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SELECT COUNT(*) FROM users;"
# 應該顯示: 50
```

---

### ❌ 錯誤:中文顯示亂碼

**症狀:** DBeaver 查詢結果顯示 `ä¸Šè¡£` 而非「上衣」

**解決方法:**

1. **DBeaver 連接設定** (推薦)
   - 右鍵點擊連接 → Edit Connection
   - Driver properties 頁籤
   - 新增屬性:
     - `characterEncoding` = `UTF-8`
     - `useUnicode` = `true`

2. **執行 SQL 修復** (如果方法 1 無效)
   ```sql
   ALTER DATABASE outfit_db CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
   ALTER TABLE items CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

---

## 📊 驗證資料是否正確

```bash
# 方法 1: 使用 Docker 指令
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "
SELECT 'users 表' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'items 表' as table_name, COUNT(*) as count FROM items;
"

# 預期結果:
# table_name | count
# -----------|--------
# users 表   | 50
# items 表   | 49,707
```

```sql
-- 方法 2: 在 DBeaver 執行
-- 檢查資料來源分佈
SELECT source, COUNT(*) as count 
FROM items 
GROUP BY source 
ORDER BY count DESC;

-- 預期結果:
-- source            | count
-- ------------------|--------
-- styles_dataset    | 44,407
-- fashion_small     | 4,999
-- uniqlo            | 221
-- malefashion       | 80
```

---

## 🔄 更新流程

### 開發者 (匯出資料)

```bash
# 當你新增/修改資料後
./scripts/export_database.sh

# 腳本會自動匯出到: init/outfit_db_with_data.sql
# ⚠️ 不要改檔名!不要手動加日期!
```

**完整流程:**
```bash
# 1. 匯出 (自動覆蓋 outfit_db_with_data.sql)
./scripts/export_database.sh

# 2. 提交 (Git 會追蹤變更)
git add init/outfit_db_with_data.sql
git commit -m "更新資料庫:新增 500 個 UNIQLO 秋冬商品"
git push origin Crawler&Detection

# 3. 通知組員
# 「資料庫已更新!請 git pull 並重新匯入」
```

**Git 會自動處理:**
- ✅ 追蹤檔案變更 (diff)
- ✅ 保留完整歷史
- ✅ 解決衝突 (如果兩人同時修改)

---

### 組員 (同步資料)

```bash
# 1. 下載更新
git pull

# 2. 重新匯入
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < init/outfit_db_with_data.sql

# 3. 驗證
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SELECT COUNT(*) FROM items;"
```

---

## 🆘 需要幫助?

- 📖 查看主要文檔: [README.md](../README.md)
- � 完整資料庫指南: [docs/DATABASE_GUIDE.md](../docs/DATABASE_GUIDE.md) ⭐
- � 快速開始: [QUICK_START.md](../QUICK_START.md)

---

**最後更新:** 2025-11-26  
**維護者:** liaoyiting
