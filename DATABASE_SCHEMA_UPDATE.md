# 資料庫結構更新報告

**日期**: 2025-12-03  
**分支**: 1202MVP  
**更新人員**: AI Assistant

---

## 📋 更新摘要

本次更新對資料庫結構進行了重大調整，刪除了穿搭相關表格，新增了商品評分功能。

---

## 🗑️ 刪除的表格

### 1. `outfits` 表格
- **原用途**: 儲存預設的穿搭組合
- **刪除原因**: 簡化資料庫結構，專注於單品推薦

### 2. `outfit_items` 表格  
- **原用途**: 關聯表，連接 outfits 和 items
- **刪除原因**: 隨 outfits 表格一併移除

---

## ✅ 新增的表格

### `rating` 表格

**用途**: 記錄使用者對商品的評分和評論

**結構定義**:
```sql
CREATE TABLE rating (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL COMMENT '評分的使用者ID',
  item_id INT NOT NULL COMMENT '被評分的商品ID',
  rating_value INT NOT NULL COMMENT '評分值 (建議 1-5 星)',
  review_text TEXT DEFAULT NULL COMMENT '評論內容',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '評分時間',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
  
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
  
  INDEX idx_user_id (user_id),
  INDEX idx_item_id (item_id),
  INDEX idx_rating_value (rating_value),
  INDEX idx_created_at (created_at),
  
  UNIQUE KEY unique_user_item (user_id, item_id) COMMENT '同一使用者對同一商品只能評分一次'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='商品評分表 - 記錄使用者對商品的評分和評論';
```

**功能特點**:
- ✅ 支援 1-5 星評分系統
- ✅ 可選的文字評論
- ✅ 記錄建立和更新時間
- ✅ 唯一約束：每個使用者對每個商品只能評分一次
- ✅ 外鍵關聯：自動維護資料完整性

---

## 📊 資料庫當前結構

更新後的資料庫包含以下 6 個表格：

| 表格名稱 | 用途 | 狀態 |
|---------|------|------|
| `users` | 使用者資料 | ✅ 保留 |
| `items` | 商品資料 | ✅ 保留 |
| `user_wardrobe` | 使用者個人衣櫃 | ✅ 保留 |
| `partner_products` | 合作品牌商品 | ✅ 保留 |
| `conversation_history` | AI 對話記錄 | ✅ 保留 |
| `rating` | 商品評分 | 🆕 新增 |

---

## 🔧 應用程式更新

### `app/app.py` 主要修改

1. **移除的功能**:
   - `detect_outfit_fields()` - outfit 欄位偵測
   - `fuzzy_match_fields()` - 模糊匹配函數
   - `standardize_outfit()` - outfit 資料標準化
   - `get_outfit_fields()` - 欄位快取函數
   - `/data_quality` 路由 - 資料品質檢查

2. **更新的功能**:
   - `generate_recommendation()` - 改為使用 `items` 表格進行推薦
   - `recommend_page()` - 變數名稱從 `outfits` 改為 `items`
   - `/recommend` API - 回傳資料從 `outfits` 改為 `items`

3. **新的推薦邏輯**:
   ```python
   # 舊版：查詢 outfits 表格
   SELECT * FROM outfits WHERE occasion IN (...) LIMIT 5
   
   # 新版：查詢 items 表格
   SELECT * FROM items WHERE 
     name LIKE %keyword% OR 
     description LIKE %keyword% OR 
     category LIKE %keyword%
   LIMIT 10
   ```

---

## 📝 SQL 腳本更新

### 1. `init/01_schema_only.sql`
- ✅ 新增 `rating` 表格定義
- ✅ 保持其他表格結構不變

### 2. `init/03_modify_tables.sql` (新增)
- ✅ 提供資料庫遷移腳本
- ✅ 安全刪除 `outfit_items` 和 `outfits`
- ✅ 建立 `rating` 表格

### 3. `init/02_add_outfits_tables.sql` (已刪除)
- ❌ 不再需要，已從專案中移除

---

## ✅ 測試結果

### 資料庫測試
```bash
# 驗證表格已正確建立
mysql> SHOW TABLES;
+------------------------+
| Tables_in_outfit_db    |
+------------------------+
| conversation_history   |
| items                  |
| partner_products       |
| rating                 | ← 新增
| user_wardrobe          |
| users                  |
+------------------------+
6 rows in set (0.00 sec)
```

### 應用程式測試
```bash
# AI 推薦功能正常運作
$ curl -X POST http://localhost:5001/recommend_page -d "message=推薦上衣"
✅ 返回 200 OK
✅ 顯示商品推薦
✅ AI 回應正常
```

---

## 🚀 部署步驟

如果需要在新環境中部署此更新：

### 1. 更新資料庫結構
```bash
docker exec -i outfit-mysql mysql -uroot -prootpassword outfit_db < init/03_modify_tables.sql
```

### 2. 重建 Flask 容器
```bash
docker compose build --no-cache flask
docker compose up -d flask
```

### 3. 驗證更新
```bash
# 檢查表格
docker exec outfit-mysql mysql -uroot -prootpassword outfit_db -e "SHOW TABLES;"

# 測試 API
curl -X POST http://localhost:5001/recommend_page -d "message=test"
```

---

## 💡 未來擴展建議

### 1. 評分系統應用
- [ ] 在前端新增評分 UI 組件
- [ ] 實作 `/rate_item` API 端點
- [ ] 基於評分數據優化推薦演算法
- [ ] 顯示商品平均評分和評論數量

### 2. 推薦演算法優化
- [ ] 整合 `rating` 表格數據
- [ ] 實作協同過濾推薦
- [ ] 考慮使用者評分歷史
- [ ] 優化關鍵字匹配邏輯

### 3. 資料分析
- [ ] 分析使用者評分趨勢
- [ ] 識別熱門商品
- [ ] 計算商品推薦分數

---

## 📞 聯絡資訊

如有問題或需要協助，請聯繫開發團隊。

---

**Commit**: `356163c`  
**推送至**: `https://github.com/memory9802/AI-project` (分支: 1202MVP)
