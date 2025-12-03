# SQL 檔案使用說明

## 📂 檔案清單與用途

### 1. `outfit_db.sql` (7.3K)
- **用途**: 僅包含資料庫結構定義 (CREATE TABLE 語句)
- **資料**: ❌ 無資料
- **使用時機**: 從零建立新資料庫結構時使用
- **適用對象**: 需要空白資料庫結構的情況

### 2. `outfit_db_with_data.sql` (8.2M) ⚠️ 已過期
- **用途**: 包含資料庫結構 + 原始完整資料
- **資料**: ✅ 有資料 (但包含 fashion_small 虛擬資料)
- **狀態**: **已過期,不建議使用**
- **問題**: 包含約 5,000 筆 fashion_small 虛擬資料

### 3. `outfit_db_with_data_clean.sql` (7.4M) ⭐ **推薦使用**
- **用途**: 包含資料庫結構 + 完全清理後的資料
- **資料**: ✅ 有資料 (已完全移除 fashion_small)
- **狀態**: **最新、最乾淨** (2025-12-02 更新)
- **fashion_small 數量**: 0 筆 ✅
- **使用時機**: 想要取得最新乾淨資料時使用
- **資料來源**: styles_dataset (44,407筆) + malefashion (80筆) + uniqlo (221筆) = 44,708筆

### 4. `outfit_db_clean.sql` (7.4M)
- **用途**: 第一次清理版本
- **資料**: ✅ 有資料 (但還有 14 筆殘留)
- **狀態**: 中間版本,已被 completely_clean 取代
- **fashion_small 數量**: 14 筆 ⚠️

### 5. `outfit_db_final_clean.sql` (7.4M)
- **用途**: 第二次清理版本
- **資料**: ✅ 有資料 (但還有 13 筆殘留)
- **狀態**: 中間版本,已被 completely_clean 取代
- **fashion_small 數量**: 13 筆 ⚠️

---

## 🎯 建議使用方式

### 方案 A: 完整重建資料庫 (推薦)
```bash
# 1. 停止並刪除舊容器
docker-compose down -v

# 2. 使用最新乾淨的 SQL 檔案啟動
docker-compose up -d mysql

# 3. 等待 MySQL 啟動完成 (約 10 秒)
sleep 10

# 4. 匯入最新乾淨資料
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < /Users/liaoyiting/Desktop/stylerec/init/outfit_db_with_data_clean.sql

# 5. 驗證資料
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SELECT COUNT(*) as total, source FROM items GROUP BY source;"
```

### 方案 B: 只更新現有資料庫 (快速)
```bash
# 1. 備份現有資料庫 (安全起見)
docker exec outfit-mysql mysqldump -uroot -prootpassword outfit_db > /Users/liaoyiting/Desktop/stylerec/init/backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 刪除舊資料並重新匯入
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SET FOREIGN_KEY_CHECKS=0; DROP TABLE IF EXISTS items, users, user_wardrobe, partner_products, conversation_history, outfit_ratings; SET FOREIGN_KEY_CHECKS=1;"

docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < /Users/liaoyiting/Desktop/stylerec/init/outfit_db_with_data_clean.sql

# 3. 驗證資料
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SELECT COUNT(*) as total, source FROM items GROUP BY source;"
```

---

## 🧹 清理建議

為了避免混淆,建議刪除或重新命名舊檔案:

```bash
cd /Users/liaoyiting/Desktop/stylerec/init

# 建立備份目錄
mkdir -p old_versions

# 移動舊版本
mv outfit_db_with_data.sql old_versions/outfit_db_with_data.sql.old
mv outfit_db_clean.sql old_versions/outfit_db_clean.sql.old
mv outfit_db_final_clean.sql old_versions/outfit_db_final_clean.sql.old

# 重新命名最新版本為標準名稱 (可選)
cp outfit_db_with_data_clean.sql outfit_db_with_data.sql
```

---

## 📊 資料來源統計 (outfit_db_completely_clean.sql)

預期包含以下資料來源:
- **styles_dataset**: ~44,407 筆 (Kaggle 時尚資料集)
- **malefashion**: ~80 筆 (男裝資料)
- **uniqlo**: ~222 筆 (UNIQLO 爬蟲資料)
- **fashion_small**: ✅ 0 筆 (已完全移除)

**總計**: 約 44,709 筆乾淨資料

---

## ⚠️ 重要提醒

1. **outfit_db_with_data.sql 已過期**: 建議不再使用,避免重新匯入虛擬資料
2. **推薦使用 outfit_db_completely_clean.sql**: 這是最乾淨的版本
3. **備份很重要**: 在執行任何資料庫操作前,請先備份
4. **驗證資料**: 匯入後請執行 GROUP BY source 查詢確認資料正確

---

## 📝 更新日期
- 建立日期: 2025-12-02
- 最新清理版本: `outfit_db_with_data_clean.sql`
- Fashion_small 資料: 已完全移除 ✅
- 當前資料庫狀態: 已更新為最新乾淨資料 (44,708 筆)
