"""
AI 穿搭推薦服務模組 (v4)
- 融合 v1 的「場合/風格」推薦邏輯與 v2 的 RAG 查詢模式
- 針對新的 `items` 資料庫結構進行查詢
- 透過關鍵字映射，將抽象的「場合/風格」對應到具體的「衣物類型」
- **優化: 同時查詢 `clothing_type` 和 `name` 欄位，提高準確率**
"""

import os
import sys
import pymysql
from decimal import Decimal
from datetime import datetime

# ==============================================================================
# 區塊 1: 環境與前置設定
# 說明:
# - 設定 Python 的編碼，確保能處理中文字元。
# - 引入 LangChain Agent，這是與大型語言模型互動的核心。
# - 從環境變數讀取資料庫和 AI 模型的設定。
# ==============================================================================
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from langchain_agent import OutfitAIAgent

DB_HOST = os.getenv('DB_HOST', 'mysql')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', 'rootpassword')
DB_NAME = os.getenv('DB_NAME', 'outfit_db')

LLM_API_KEY = os.getenv('LLM_API_KEY')
USE_GEMINI = bool(LLM_API_KEY)

agent = None
if USE_GEMINI:
    try:
        agent = OutfitAIAgent(
            gemini_key=LLM_API_KEY,
            groq_key=os.getenv('GROQ_API_KEY'),
            deepseek_key=os.getenv('DEEPSEEK_API_KEY')
        )
        print("✅ AI Agent (v4) 初始化成功", flush=True)
    except Exception as e:
        print(f"⚠️ AI Agent 初始化失敗: {e}", flush=True, file=sys.stderr)

# ==============================================================================
# 區塊 2: 關鍵字映射 (核心邏輯)
# 說明:
# - 這是 v4 的核心，用於彌補 `items` 表沒有 `occasion` 或 `style` 欄位的問題。
# - `OCCASION_STYLE_MAPPING` 將使用者可能輸入的「場合」或「風格」關鍵字，
#   映射到一個或多個在 `items` 表中可以被查詢的 `clothing_type` 或 `name`。
# - `extract_keywords` 函數則負責從使用者的問句中找出這些關鍵字。
# ==============================================================================
OCCASION_STYLE_MAPPING = {
    '運動': ['運動褲', '運動鞋', '運動上衣', '運動外套', 'T恤'],
    '正式': ['襯衫', '西裝褲', '皮鞋', '西裝外套', '領帶', '正裝襯衫'],
    '上班': ['襯衫', '西裝褲', '皮鞋', '西裝外套', '針織衫', '卡其褲'],
    '約會': ['洋裝', '襯衫', '裙子', '休閒鞋', '針織衫'],
    '休閒': ['T恤', '牛仔褲', '休閒褲', '運動鞋', '連帽衫'],
    '街頭': ['連帽衫', '牛仔褲', '運動鞋', '棒球帽', 'T恤'],
    '文青': ['襯衫', '帆布鞋', '卡其褲', '針織衫', '漁夫帽'],
    '韓風': ['寬褲', '老爹鞋', '大學T', '西裝外套', '襯衫'],
    '工裝': ['工作褲', '靴子', '工作襯衫', '吊帶褲'],
}

def extract_keywords(text: str):
    """從使用者輸入中提取「場合」或「風格」關鍵字"""
    found_keywords = []
    text_lower = text.lower()
    for key in OCCASION_STYLE_MAPPING.keys():
        if key.lower() in text_lower:
            found_keywords.append(key)
    return list(set(found_keywords))

# ==============================================================================
# 區塊 3: 資料庫連線與序列化
# 說明:
# - `get_db_conn` 負責建立與資料庫的連線。
# - `serialize_item` 是一個輔助函數，用於將從資料庫取出的資料（可能包含
#   Decimal、datetime 等特殊格式）轉換為 Python 能直接處理的 float 和 string，
#   以便後續傳遞給 AI 或前端。
# ==============================================================================
def get_db_conn():
    """建立資料庫連線"""
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        db=DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
        use_unicode=True
    )

def serialize_item(item):
    """將資料庫查詢出的 item 序列化"""
    if not item: return None
    for key, value in item.items():
        if isinstance(value, Decimal): item[key] = float(value)
        elif isinstance(value, datetime): item[key] = value.isoformat()
    return item

# ==============================================================================
# 區塊 4: AI 穿搭推薦主函數
# 說明:
# - 這是整個服務的入口，整合了前面所有的邏輯。
# - 步驟 1 (檢索):
#   - 呼叫 `extract_keywords` 找出使用者想問的「場合/風格」。
#   - 如果找到關鍵字，就用 `OCCASION_STYLE_MAPPING` 把它們轉換成衣物類型列表。
#   - **優化**: 產生同時查詢 `clothing_type` (精確比對) 和 `name` (模糊比對) 的 SQL。
#   - 如果沒有找到關鍵字或查詢無結果，就隨機推薦幾件單品作為備案。
# - 步驟 2 (增強):
#   - 將查詢到的單品資訊（包含您指定的 color 和 clothing_type）整理成一段文字，
#     這段文字就是提供給 AI 的「上下文 (Context)」。
# - 步驟 3 (生成):
#   - 將使用者的原始問題和我們準備的上下文結合，一起傳給 AI。
#   - AI 會根據這些資訊，生成一段更自然、更完整的推薦文案。
#   - 如果 AI 服務失敗，會提供一個備援的回應，至少讓使用者看到資料庫的查詢結果。
# ==============================================================================
def generate_recommendation(user_input: str,
                            session_id: str = 'default',
                            preferred_model: str = 'auto'):
    """
    根據使用者輸入的「場合」或「風格」產生推薦
    """
    if not user_input:
        return "請告訴我您想要的風格或場合，例如「適合上班的穿搭」", [], []

    # 1. RAG - 檢索 (Retrieval)
    keywords = extract_keywords(user_input)
    items = []
    
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            if keywords:
                # 將場合/風格關鍵字轉換為衣物類型
                target_clothing_types = []
                for kw in keywords:
                    target_clothing_types.extend(OCCASION_STYLE_MAPPING.get(kw, []))
                
                if target_clothing_types:
                    # 建立一個同時查詢 clothing_type 和 name 的 SQL 語句
                    # 例如: (clothing_type = %s OR name LIKE %s)
                    where_clauses = []
                    query_params = []
                    for t_type in set(target_clothing_types): # 使用 set 避免重複
                        where_clauses.append("(clothing_type = %s OR name LIKE %s)")
                        query_params.extend([t_type, f'%{t_type}%'])

                    sql_query = f"""
                        SELECT * FROM items 
                        WHERE {' OR '.join(where_clauses)}
                        ORDER BY RAND() 
                        LIMIT 5
                    """
                    cur.execute(sql_query, tuple(query_params))
                    items = cur.fetchall()

            # 如果關鍵字查詢沒有結果，隨機推薦幾件
            if not items:
                cur.execute("SELECT * FROM items ORDER BY RAND() LIMIT 5")
                items = cur.fetchall()
            
            items = [serialize_item(item) for item in items]

    except Exception as e:
        print(f"❌ 資料庫查詢失敗: {e}", flush=True, file=sys.stderr)
        items = []
    finally:
        conn.close()

    # 2. 增強 (Augmented) - 準備給 AI 的上下文
    rag_context = ""
    if items:
        rag_context += f"\n\n資料庫根據你提到的「{'、'.join(keywords)}」風格/場合，找到了這些衣物，請你參考並以條列式推薦給使用者：\n"
        for item in items:
            # 建立包含 color 和 clothing_type 的描述
            item_desc = f"- 一件 {item.get('color', '未知顏色')} 的 {item.get('clothing_type', '未知類型')} ({item.get('name', '')})"
            rag_context += f"{item_desc}\n"
    else:
        rag_context = "\n\n資料庫中沒有找到符合條件的衣物。"

    # 如果未啟用 AI，僅返回資料庫內容
    if not USE_GEMINI or not agent:
        text = "AI 尚未啟用，以下為資料庫推薦：\n"
        text += rag_context
        return text, items, keywords

    # 3. 生成 (Generation) - 呼叫 AI
    try:
        final_prompt = user_input + rag_context
        ai_response = agent.chat(
            session_id=session_id,
            user_input=final_prompt,
            db_outfits=items,
            preferred_model=preferred_model
        )
        return ai_response, items, keywords

    except Exception as e:
        error_msg = str(e)
        print(f"❌ AI 服務錯誤: {error_msg}", flush=True, file=sys.stderr)
        fallback_text = f"⚠️ AI 服務暫時無法使用。\n\n"
        if items:
            fallback_text += "不過，我仍在資料庫中為您找到了一些推薦：\n"
            fallback_text += rag_context
        else:
            fallback_text += "抱歉，目前無法提供任何推薦。"
        return fallback_text, items, keywords
