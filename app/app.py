from flask import Flask, request, jsonify, render_template
import pymysql, os, requests, json, sys
from langchain_agent import OutfitAIAgent
import uuid
from datetime import datetime
from decimal import Decimal

# 確保 Python 使用 UTF-8 編碼
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 設定 Flask 應用的 templates 和 static 資料夾路徑
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
# 確保 JSON 正確顯示中文
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False
app.json.ensure_ascii = False  # Flask 2.2+ 的新設定方式

# JSON 序列化輔助函數（目前主要用在 debug / 如需自訂 json.dumps 時）
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

# =======================
# 環境設定
# =======================
DB_HOST = os.getenv('DB_HOST', 'mysql')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', 'rootpassword')
DB_NAME = os.getenv('DB_NAME', 'outfit_db')

# 只用 Gemini
LLM_API_KEY = os.getenv('LLM_API_KEY')

# 只要有 Gemini key 就啟用 AI
USE_GEMINI = bool(LLM_API_KEY)

# 初始化 LangChain Agent（只給 Gemini）
agent = None
if USE_GEMINI:
    agent = OutfitAIAgent(
        gemini_key=LLM_API_KEY,
        groq_key=None,
        deepseek_key=None
    )

# 使用 Lite 版本,配額更充足
GEMINI_MODEL = "gemini-2.0-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={LLM_API_KEY}"

# =======================
# 資料庫連線
# =======================
def get_db_conn():
    print("DB 連線資訊：", DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME, flush=True)
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
# 🔑 RAG 關鍵字映射
# =======================
KEYWORD_MAPPING = {
    '約會': ['約會', 'date', '浪漫', '晚餐'],
    '運動': ['運動', 'sport', '健身', '跑步', '瑜珈'],
    '上班': ['上班', '辦公', '正式', '商務', 'office'],
    '休閒': ['休閒', '逛街', '週末', 'casual', '放鬆'],
    '派對': ['派對', 'party', '聚會', '夜店'],
    '旅遊': ['旅遊', '旅行', '出遊', 'travel'],
}

def extract_keywords(text: str):
    """從使用者輸入中提取關鍵字"""
    found_keywords = []
    for key, synonyms in KEYWORD_MAPPING.items():
        for synonym in synonyms:
            if synonym in text:
                found_keywords.append(key)
                break
    return list(set(found_keywords))  # 去重

# =======================
# 🤖 共用：AI 穿搭推薦邏輯（Jinja / JSON 共用）
# =======================
def generate_recommendation(user_input: str,
                            session_id: str = 'default',
                            preferred_model: str = 'auto'):
    """
    根據使用者輸入產生推薦：
    回傳 (ai_response文字, items資料(list), keywords(list))
    """

    if not user_input:
        return "請輸入訊息", [], []

    # 🔍 RAG: 從使用者輸入提取關鍵字
    keywords = extract_keywords(user_input)

    # 先從資料庫取出可能的商品
    conn = get_db_conn()
    items = []
    try:
        with conn.cursor() as cur:
            # 如果有關鍵字，可以基於關鍵字搜尋相關商品（例如顏色、類別等）
            if keywords:
                # 根據關鍵字搜尋商品 (可擴展為更複雜的邏輯)
                # 這裡示範簡單搜尋：從 description 或 name 中找關鍵字
                keyword_conditions = ' OR '.join([f"name LIKE %s OR description LIKE %s OR category LIKE %s" for _ in keywords])
                keyword_params = []
                for kw in keywords:
                    keyword_params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
                
                sql = f"SELECT * FROM items WHERE {keyword_conditions} LIMIT 10"
                cur.execute(sql, keyword_params)
                items = cur.fetchall()

                # 如果找不到，返回隨機商品
                if not items:
                    cur.execute("SELECT * FROM items ORDER BY RAND() LIMIT 10")
                    items = cur.fetchall()
            else:
                # 沒有關鍵字，返回隨機商品
                cur.execute("SELECT * FROM items ORDER BY RAND() LIMIT 10")
                items = cur.fetchall()

            # 轉換 datetime 和 Decimal 為可序列化類型
            for item in items:
                if 'created_at' in item:
                    item['created_at'] = item['created_at'].isoformat() if item['created_at'] else None
                if 'price' in item and isinstance(item['price'], Decimal):
                    item['price'] = float(item['price'])
    finally:
        conn.close()

    # 若未啟用 AI，僅返回資料庫內容（組一段說明文字）
    if not USE_GEMINI or not agent:
        text = "AI 尚未啟用，以下為資料庫推薦商品：\n"
        for idx, item in enumerate(items[:5], 1):
            text += f"\n推薦 {idx}：{item.get('name', '未命名商品')}\n"
            text += f"類別：{item.get('category', '未分類')} | "
            text += f"顏色：{item.get('color', '未指定')}\n"
            if item.get('price'):
                text += f"價格：${item.get('price')}\n"
        return text, items, keywords

    # 使用 LangChain Agent 處理對話（帶 RAG context）
    try:
        rag_context = ""
        if keywords:
            rag_context = f"\n\n偵測到關鍵字：{', '.join(keywords)}，已替你檢索到 {len(items)} 件相關商品。"

        ai_response = agent.chat(
            session_id=session_id,
            user_input=user_input + rag_context,
            db_outfits=items,  # 傳遞商品資料給 AI
            preferred_model=preferred_model
        )
        return ai_response, items, keywords

    except Exception as e:
        # 詳細的錯誤處理
        error_msg = str(e)
        print(f"❌ AI 錯誤: {error_msg}", flush=True, file=sys.stderr)
        
        # 判斷錯誤類型並提供對應的友善訊息
        if "Insufficient Balance" in error_msg or "402" in error_msg:
            fallback = ("❌ AI 服務餘額不足\n\n"
                       "目前 API 配額已用完，請稍後再試或聯繫管理員補充配額。\n\n"
                       "📋 以下為資料庫推薦：")
        elif "429" in error_msg or "Rate Limit" in error_msg:
            fallback = ("⚠️ AI 服務請求過於頻繁\n\n"
                       "請稍等片刻後再試。系統已為您準備資料庫推薦：\n")
        elif "401" in error_msg or "403" in error_msg or \
             "API key" in error_msg:
            fallback = ("❌ AI 服務認證失敗\n\n"
                       "API Key 可能無效或過期，請聯繫管理員檢查設定。\n\n"
                       "📋 以下為資料庫推薦：")
        elif "timeout" in error_msg.lower() or \
             "timed out" in error_msg.lower():
            fallback = ("⏱️ AI 服務回應超時\n\n"
                       "網路連線可能不穩定，請重試。"
                       "系統已為您準備資料庫推薦：\n")
        elif "Connection" in error_msg or "連線" in error_msg:
            fallback = ("🔌 無法連接 AI 服務\n\n"
                       "請檢查網路連線或稍後再試。\n\n"
                       "📋 以下為資料庫推薦：")
        else:
            fallback = (f"⚠️ AI 服務暫時無法使用\n\n"
                       f"錯誤資訊：{error_msg[:100]}...\n\n"
                       f"📋 以下為資料庫推薦：")
        
        # 附上資料庫推薦作為備選方案
        for idx, item in enumerate(items[:5], 1):
            fallback += (f"\n\n推薦 {idx}：{item.get('name', '未命名商品')}\n"
                        f"類別：{item.get('category', '未分類')} | "
                        f"顏色：{item.get('color', '未指定')}")
        
        return fallback, items, keywords


# =======================
# 🔹 首頁(home.html,新版中文頁面)
# =======================
@app.route('/')
@app.route('/home')
def home():
    """
    首頁:使用新的中文版 home.html
    內含浮動 AI 對話框,會載入 /recommend_page 作為 iframe
    """
    return render_template('home.html')

# =======================
# 🗂️ 衣櫃頁面
# =======================
@app.route('/wardrobe')
def wardrobe():
    """
    我的衣櫃頁面:上傳和管理衣物
    """
    return render_template('wardrobe.html')

# =======================
# 🤝 分享互動頁面
# =======================
@app.route('/share')
def share():
    """
    分享 & 互動頁面:展示穿搭作品
    """
    return render_template('share.html')

# =======================
# 🔐 登入頁面
# =======================
@app.route('/login')
def login():
    """
    登入/註冊頁面
    """
    return render_template('login.html')

# =======================
# 💡 穿搭推薦頁面(獨立頁面版本)
# =======================
@app.route('/recommendation')
def recommendation():
    """
    穿搭推薦頁面:聊天式 AI 推薦介面
    這是獨立的完整頁面版本
    """
    return render_template('recommendation.html')

# =======================
# 👕 Jinja 版 AI 穿搭頁面(index.html)
# =======================
@app.route('/recommend_page', methods=['GET', 'POST'])
def recommend_page():
    """
    這個路由用來呈現 Jinja 版的穿搭機器人頁面：
    - GET：顯示空白表單
    - POST：接收表單資料，呼叫 generate_recommendation()，再把結果 render 回 index.html
    """
    ai_response = None
    items = []
    keywords = []
    user_input = ""
    selected_model = "auto"

    if request.method == 'POST':
        user_input = request.form.get('message', '')
        selected_model = request.form.get('model', 'auto')
        session_id = "web-page-session"  # 固定給這個頁面用的 session

        ai_response, items, keywords = generate_recommendation(
            user_input=user_input,
            session_id=session_id,
            preferred_model=selected_model
        )

    return render_template(
        'index.html',  # Jinja 版的穿搭機器人頁面
        ai_response=ai_response,
        items=items,
        keywords=keywords,
        user_input=user_input,
        selected_model=selected_model
    )

# =======================
# 📦 取得所有衣物（純 JSON API，保留）
# =======================
@app.route('/items', methods=['GET'])
def get_items():
    color = request.args.get('color')
    category = request.args.get('category')
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            sql = "SELECT * FROM items WHERE 1=1"
            params = []
            if color:
                sql += " AND color LIKE %s"
                params.append(f"%{color}%")
            if category:
                sql += " AND category=%s"
                params.append(category)
            cur.execute(sql, params)
            items = cur.fetchall()
            
            # 轉換 datetime 和 Decimal 為可序列化類型
            for item in items:
                if 'created_at' in item:
                    item['created_at'] = item['created_at'].isoformat() if item['created_at'] else None
                if 'price' in item and isinstance(item['price'], Decimal):
                    item['price'] = float(item['price'])
    finally:
        conn.close()
    return jsonify(items)

# =======================
# 🤖 JSON 版 AI 穿搭推薦 API（保留給前端 fetch 用）
# =======================
@app.route('/recommend', methods=['POST'])
def recommend():
    """
    純後端 API 版本：
    - 接收 JSON：{"message": "...", "session_id": "...", "model": "..."}
    - 回傳 JSON，給前端 fetch / axios 使用
    """
    data = request.json or {}
    user_input = data.get('message', '')
    session_id = data.get('session_id', 'default')
    preferred_model = data.get('model', 'auto')

    if not user_input:
        return jsonify({"error": "請輸入訊息"}), 400

    ai_response, items, keywords = generate_recommendation(
        user_input=user_input,
        session_id=session_id,
        preferred_model=preferred_model
    )

    return jsonify({
        "response": ai_response,
        "session_id": session_id,
        "db_data": items,
        "keywords": keywords
    })

# =======================
# 🗑️ 清除對話記憶
# =======================
@app.route('/clear_session', methods=['POST'])
def clear_session():
    data = request.json or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "請提供 session_id"}), 400
    
    if agent:
        success = agent.clear_session(session_id)
        return jsonify({
            "success": success,
            "message": "對話記憶已清除" if success else "找不到該 session"
        })
    
    return jsonify({"error": "AI 未啟用"}), 400

# =======================
# ✅ 健康檢查
# =======================
@app.route('/ping')
def ping():
    return jsonify({
        "status": "ok",
        "db_host": DB_HOST,
        "gemini_model": GEMINI_MODEL,
        "ai_enabled": USE_GEMINI
    })

# =======================
# 🏁 主程式
# =======================
# 🏁 主程式
# =======================
if __name__ == '__main__':
    print("\n" + "🚀 " + "="*60, flush=True)
    print("正在啟動 AI 穿搭推薦系統...", flush=True)
    print("="*62 + "\n", flush=True)
    
    print("\n✅ 系統啟動完成，準備接受請求\n", flush=True)
    
    # 修正：在 Docker 環境中必須監聽 0.0.0.0，埠號使用容器內部埠號 5000
    app.run(debug=True, host='0.0.0.0', port=5000)

