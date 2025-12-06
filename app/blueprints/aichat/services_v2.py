"""
AI 穿搭推薦服務模組 (v2)
整合 LangChain Agent 和新的 `items` 資料庫查詢功能
"""

import os
import sys
import pymysql
from decimal import Decimal
from datetime import datetime

# 確保 Python 使用 UTF-8 編碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 導入 LangChain Agent（從 app 根目錄）
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from langchain_agent import OutfitAIAgent

# =======================
# 環境設定
# =======================
DB_HOST = os.getenv('DB_HOST', 'mysql')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', 'rootpassword')
DB_NAME = os.getenv('DB_NAME', 'outfit_db')

# AI 模型設定
LLM_API_KEY = os.getenv('LLM_API_KEY')
USE_GEMINI = bool(LLM_API_KEY)

# 初始化 LangChain Agent
agent = None
if USE_GEMINI:
    try:
        agent = OutfitAIAgent(
            gemini_key=LLM_API_KEY,
            groq_key=os.getenv('GROQ_API_KEY'),
            deepseek_key=os.getenv('DEEPSEEK_API_KEY')
        )
        print("✅ AI Agent (v2) 初始化成功", flush=True)
    except Exception as e:
        print(f"⚠️ AI Agent 初始化失敗: {e}", flush=True, file=sys.stderr)

# =======================
# 資料庫連線
# =======================
def get_db_conn():
    """建立資料庫連線"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        use_unicode=True
    )

# =======================
# 關鍵字映射 (RAG)
# =======================
# 關鍵字映射到 clothing_type 或 category
KEYWORD_MAPPING = {
    'T恤': ['T恤', 't-shirt', 'tee'],
    '襯衫': ['襯衫', 'shirt'],
    '褲': ['褲', 'trousers', 'pants'],
    '外套': ['外套', 'jacket', 'coat'],
    '鞋': ['鞋', 'shoes', 'footwear'],
    '配件': ['配件', 'accessories'],
    '運動': ['運動', 'sport'],
    '休閒': ['休閒', 'casual'],
    '正式': ['正式', 'formal', '商務'],
}

def extract_keywords(text: str):
    """從使用者輸入中提取關鍵字，用於資料庫查詢"""
    found_keywords = []
    text_lower = text.lower()
    for key, synonyms in KEYWORD_MAPPING.items():
        for synonym in synonyms:
            if synonym.lower() in text_lower:
                found_keywords.append(key)
                break
    return list(set(found_keywords))

def serialize_item(item):
    """將資料庫查詢出的 item 序列化，處理 Decimal 和 datetime"""
    if not item:
        return None
    for key, value in item.items():
        if isinstance(value, Decimal):
            item[key] = float(value)
        elif isinstance(value, datetime):
            item[key] = value.isoformat()
    return item

# =======================
# 🤖 AI 穿搭推薦邏輯 (v2)
# =======================
def generate_recommendation(user_input: str,
                            session_id: str = 'default',
                            preferred_model: str = 'auto'):
    """
    根據使用者輸入產生推薦：
    1. 從 `items` 表中檢索相關衣物
    2. 將檢索到的衣物資訊傳遞給 AI
    3. AI 生成推薦文案
    """
    if not user_input:
        return "請輸入您的穿搭需求", [], []

    # 1. RAG - 檢索 (Retrieval)
    keywords = extract_keywords(user_input)
    items = []
    
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            if keywords:
                # 建立模糊查詢條件
                # 例如: "T恤" 或 "褲" -> clothing_type LIKE '%T恤%' OR clothing_type LIKE '%褲%'
                like_clauses = [f"(clothing_type LIKE %s OR category LIKE %s)" for _ in keywords]
                sql_query = f"SELECT * FROM items WHERE {' OR '.join(like_clauses)} ORDER BY RAND() LIMIT 5"
                # 參數需要是兩倍的關鍵字，分別給 clothing_type 和 category
                query_params = []
                for kw in keywords:
                    query_params.extend([f'%{kw}%', f'%{kw}%'])
                
                cur.execute(sql_query, query_params)
                items = cur.fetchall()

            # 如果關鍵字查詢沒有結果，隨機推薦幾件
            if not items:
                cur.execute("SELECT * FROM items ORDER BY RAND() LIMIT 5")
                items = cur.fetchall()
            
            # 序列化查詢結果
            items = [serialize_item(item) for item in items]

    except Exception as e:
        print(f"❌ 資料庫查詢失敗: {e}", flush=True, file=sys.stderr)
        # 即使資料庫失敗，也要讓 AI 繼續工作
        items = []
    finally:
        conn.close()

    # 2. 增強 (Augmented) - 準備給 AI 的上下文
    rag_context = ""
    if items:
        rag_context += "\n\n資料庫找到了這些衣物，請你參考並以條列式推薦給使用者：\n"
        for item in items:
            # 建立每個衣物的描述，包含顏色和類型
            item_desc = f"- 一件 {item.get('color', '未知顏色')} 的 {item.get('clothing_type', '未知類型')}"
            rag_context += f"{item_desc}\n"
    else:
        rag_context = "\n\n資料庫中沒有找到符合條件的衣物。"

    # 如果未啟用 AI，僅返回資料庫內容
    if not USE_GEMINI or not agent:
        text = "AI 尚未啟用，以下為資料庫隨機推薦：\n"
        text += rag_context
        return text, items, keywords

    # 3. 生成 (Generation) - 呼叫 AI
    try:
        # 將使用者問題和 RAG 上下文結合，傳給 AI
        final_prompt = user_input + rag_context
        
        ai_response = agent.chat(
            session_id=session_id,
            user_input=final_prompt,
            db_outfits=items,  # 雖然變數名是 db_outfits，但傳入的是 items
            preferred_model=preferred_model
        )
        # 將 items 回傳給前端，即使 AI 可能沒有用到
        return ai_response, items, keywords

    except Exception as e:
        error_msg = str(e)
        print(f"❌ AI 服務錯誤: {error_msg}", flush=True, file=sys.stderr)
        
        # 建立備援回應
        fallback_text = f"⚠️ AI 服務暫時無法使用 ({error_msg[:50]}...)\n\n"
        if items:
            fallback_text += "不過，我仍在資料庫中為您找到了一些推薦：\n"
            fallback_text += rag_context
        else:
            fallback_text += "抱歉，目前無法提供任何推薦。"
            
        return fallback_text, items, keywords
