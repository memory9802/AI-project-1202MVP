# UNIQLO 商品資料處理流程 - 關鍵程式檔案

> 從網頁爬蟲到資料庫匯入的完整自動化流程

---

## 📋 目錄

1. [流程概覽](#流程概覽)
2. [檔案結構](#檔案結構)
3. [執行順序](#執行順序)
4. [環境設定](#環境設定)
5. [常見問題](#常見問題)

---

## 🔄 流程概覽

```
┌─────────────────┐
│ 1. 爬取商品資料  │  → 01_crawl_uniqlo.py
└─────────────────┘
          ↓
┌─────────────────┐
│ 2. 顏色辨識處理  │  → 02_detect_colors.py
└─────────────────┘
          ↓
┌─────────────────┐
│ 3. Gemini 驗證  │  → 03_gemini_verify.py
└─────────────────┘
          ↓
┌─────────────────┐
│ 4. 資料處理合併  │  → 04_data_processing.py
└─────────────────┘
          ↓
┌─────────────────┐
│ 5. 資料庫匯入    │  → 05_database_import.py
└─────────────────┘
```

---

## 📁 檔案結構

```
pipeline/
├── 01_crawl_uniqlo.py          # 爬蟲：UNIQLO 商品資料爬取
├── 02_detect_colors.py         # 顏色辨識：K-Means + Pantone 色號
├── 03_gemini_verify.py         # AI驗證：Gemini Vision API 全欄位驗證
├── 04_data_processing.py       # 資料處理：合併、對比、統計
├── 05_database_import.py       # 資料庫：生成 SQL + 匯入 MySQL
└── README.md                   # 本文件

init/                           # 資料檔案目錄
├── uniqlo_175.csv             # 原始爬取資料
├── uniqlo_175_colored.csv     # 加入顏色辨識
├── gemini_verification_complete.csv  # Gemini完整驗證
├── gemini_results_only.csv    # 純 Gemini 結果
├── gemini_comparison.csv      # 對比分析
├── final_dataset.csv          # 最終資料集
└── outfit_db.sql              # 資料庫初始化腳本
```

---

## ⚡ 執行順序

### 步驟 1: 爬取 UNIQLO 商品資料

```bash
cd /path/to/AI-project\ 2
python pipeline/01_crawl_uniqlo.py
```

**輸入**: 無 (或已有 `init/uniqlo_175.csv`)  
**輸出**: `init/uniqlo_175.csv`  
**欄位**: `sku`, `name`, `gender`, `category`, `clothing_type`, `length`, `price`, `image_url`

**說明**:
- 從 UNIQLO 台灣官網爬取商品資料
- 自動從商品名稱提取基本屬性（性別、類別、長度等）
- 如果已有 CSV 檔案，會直接讀取並處理

---

### 步驟 2: 顏色辨識處理

```bash
python pipeline/02_detect_colors.py
```

**輸入**: `init/uniqlo_175.csv`  
**輸出**: `init/uniqlo_175_colored.csv`  
**新增欄位**: `color` (Pantone 格式)

**技術細節**:
- 使用 **K-Means 聚類** 提取主色調
- **HSV 色相分析** 優先判斷顏色類別
- 過濾陰影像素（V < 20%）
- 匹配 **Pantone 色號系統** (30+ 色號)
- 可選: 使用 `rembg` 去背提高準確度

**依賴套件**:
```bash
pip install pandas numpy pillow requests scikit-learn
pip install rembg  # 可選，用於背景去除
```

---

### 步驟 3: Gemini Vision API 驗證

```bash
# 設定 API Key
export GEMINI_API_KEY='your-api-key'

# 執行驗證
python pipeline/03_gemini_verify.py
```

**輸入**: `init/uniqlo_175_colored.csv`  
**輸出**: `init/gemini_verification_complete.csv`  
**新增欄位**: `Gemini gender`, `Gemini category`, `Gemini clothing_type`, `Gemini length`, `Gemini color`

**技術細節**:
- 使用 **Google Gemini 2.0 Flash** 視覺模型
- 分析商品圖片，驗證 5 個屬性：性別、類別、服裝類型、長度、顏色
- 自動 JSON 解析，處理 API 回應
- 每 5 筆自動存檔，支援中斷續傳

**API Key 取得**:
1. 前往 https://aistudio.google.com/app/apikey
2. 點擊「Create API Key」
3. 複製 API Key 並設定環境變數

**限速保護**:
- 每次請求間隔 2 秒
- 支援從特定行數繼續處理: `batch_verify_with_gemini(..., start_row=50)`

---

### 步驟 4: 資料處理與合併

```bash
python pipeline/04_data_processing.py
```

**輸入**: 
- `init/uniqlo_175_colored.csv`
- `init/gemini_verification_complete.csv`

**輸出**:
- `init/gemini_results_only.csv` - 純 Gemini 結果
- `init/gemini_comparison.csv` - 對比分析（含差異標記）
- `init/final_dataset.csv` - 最終資料集（混合策略）

**功能**:
1. **合併資料**: 原始 + Gemini 驗證結果
2. **對比分析**: 逐欄位標記差異 (✓/❌)
3. **統計報告**: 準確率、差異筆數、範例展示
4. **最終資料集**: 混合策略（clothing_type用Gemini，color用Pantone）

**策略選擇**:
- `gemini`: 全部使用 Gemini 結果
- `original`: 保留原始資料
- `hybrid`: 混合策略（預設，平衡準確率與資料格式）

---

### 步驟 5: 資料庫匯入

```bash
python pipeline/05_database_import.py
```

**輸入**: `init/gemini_results_only.csv`  
**輸出**: `init/outfit_db.sql`

**功能**:
1. 生成 231 條 INSERT 語句
2. 創建完整資料庫初始化腳本
3. 包含所有資料表：items, outfits, outfit_items, tags, users, user_favorites

**資料表結構**:

```sql
CREATE TABLE items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku VARCHAR(50) UNIQUE,
  name VARCHAR(100) NOT NULL,
  gender ENUM('男','女','-'),
  clothing_type VARCHAR(50),          -- Gemini category
  category ENUM('top','bottom',...),  -- 映射後的分類
  length ENUM('短','長','-'),
  color VARCHAR(50),
  price VARCHAR(20),
  image_url VARCHAR(255),
  created_at TIMESTAMP
);
```

**手動匯入方式**:
```bash
# 方法1: 命令列
mysql -u root -p outfit_db < init/outfit_db.sql

# 方法2: MySQL 內
mysql> SOURCE /path/to/init/outfit_db.sql;
```

**欄位映射**:
- CSV `Gemini clothing_type` (上衣/下身) → SQL `category` (top/bottom)
- CSV `Gemini category` (女裝T恤上衣) → SQL `clothing_type`
- CSV `price` (NT$390) → SQL `price` (VARCHAR)

---

## 🛠️ 環境設定

### Python 版本
- Python 3.8+

### 依賴套件

**核心套件**:
```bash
pip install pandas numpy pillow requests scikit-learn
```

**顏色辨識 (可選)**:
```bash
pip install rembg  # 背景去除
pip install opencv-python  # 進階圖片處理
```

**Gemini API**:
```bash
pip install google-generativeai
```

**資料庫 (可選)**:
```bash
pip install pymysql  # 直接匯入 MySQL
```

### 環境變數

```bash
# Gemini API Key
export GEMINI_API_KEY='your-api-key'

# MySQL 連線 (可選)
export MYSQL_USER='root'
export MYSQL_PASSWORD='your-password'
export MYSQL_HOST='localhost'
```

---

## 📊 資料統計

### 最終資料集

- **總筆數**: 231 筆
- **欄位數**: 9 欄

### Gemini 驗證準確率

| 欄位 | 準確率 | 差異筆數 |
|------|--------|---------|
| `gender` | 84.5% | 33 |
| `clothing_type` | 99.5% | 1 |
| `length` | 68.1% | 68 |
| `category` | 8.0% | 196 |
| `color` | 0.0% | 213 |

**分析**:
- ✅ **clothing_type** 幾乎完美 (99.5%)
- ✅ **gender** 準確率高 (84.5%)
- ⚠️ **category** 差異大：Gemini 分類更細緻（如：女裝T恤上衣 vs T恤上衣）
- ⚠️ **color** 格式差異：Gemini 純中文 vs Pantone 色號格式

---

## 🚨 常見問題

### Q1: Gemini API 請求失敗？

**原因**:
- API Key 未設定或無效
- 超過免費額度 (60 requests/min)
- 網路連線問題

**解決方案**:
```bash
# 檢查 API Key
echo $GEMINI_API_KEY

# 降低請求頻率（修改 time.sleep）
time.sleep(5)  # 每次間隔5秒

# 從特定行繼續
batch_verify_with_gemini(..., start_row=50)
```

---

### Q2: 顏色辨識不準確？

**改進方案**:
1. 啟用背景去除: `pip install rembg`
2. 調整 K-Means 參數: `k=5` → `k=7`
3. 增加陰影過濾: `v_threshold=0.2` → `0.3`
4. 使用混合策略保留 Pantone 格式

---

### Q3: 資料庫匯入失敗？

**檢查清單**:
```bash
# 1. 確認 MySQL 服務運行
mysql -u root -p -e "SELECT VERSION();"

# 2. 檢查 SQL 檔案格式
head -20 init/outfit_db.sql

# 3. 手動逐段執行
mysql -u root -p
> CREATE DATABASE outfit_db;
> USE outfit_db;
> SOURCE /path/to/outfit_db.sql;
```

**常見錯誤**:
- `Unknown column 'clothing_type'`: 欄位名稱不匹配
- `Data too long`: VARCHAR 長度不足
- `Duplicate entry`: SKU 重複（檢查資料重複）

---

### Q4: 如何新增更多商品？

```bash
# 1. 更新爬蟲目標
vim pipeline/01_crawl_uniqlo.py
# 修改 max_items 或 categories

# 2. 重新執行完整流程
python pipeline/01_crawl_uniqlo.py
python pipeline/02_detect_colors.py
python pipeline/03_gemini_verify.py
python pipeline/04_data_processing.py
python pipeline/05_database_import.py
```

---

## 🔗 相關文件

- [PROJECT_WORKFLOW.md](../docs/PROJECT_WORKFLOW.md) - 完整技術文件
- [GEMINI_QUICKSTART.md](../GEMINI_QUICKSTART.md) - Gemini API 使用指南
- [outfit_db.sql](../init/outfit_db.sql) - 資料庫腳本

---

## 📝 授權

本專案僅供學習研究使用。

---

## 👥 貢獻者

- 資料爬取與預處理
- 顏色辨識算法開發
- Gemini API 整合
- 資料庫設計與實作

---

**更新日期**: 2025-01-23
