-- ========================================
-- 資料庫結構修改腳本
-- 日期: 2025-12-03
-- ========================================
-- 
-- 📋 修改內容:
--   1. 刪除 outfits 表格
--   2. 刪除 outfit_items 表格
--   3. 新增 rating 表格
-- 
-- ========================================

USE outfit_db;

-- =============================
-- 1. 刪除 outfit_items 表格 (先刪除有外鍵的表)
-- =============================
DROP TABLE IF EXISTS outfit_items;
SELECT '✅ outfit_items 表格已刪除' AS status;

-- =============================
-- 2. 刪除 outfits 表格
-- =============================
DROP TABLE IF EXISTS outfits;
SELECT '✅ outfits 表格已刪除' AS status;

-- =============================
-- 3. 新增 rating 表格
-- =============================
DROP TABLE IF EXISTS rating;
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

SELECT '✅ rating 表格已建立' AS status;

-- =============================
-- 驗證結果
-- =============================
SHOW TABLES;
SELECT '✅ 資料庫結構修改完成！' AS final_status;
