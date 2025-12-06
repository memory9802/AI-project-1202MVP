from flask import request, jsonify, render_template
from . import aichat_bp
from .services_v4 import (
    generate_recommendation, 
    agent, 
    get_db_conn
)
from decimal import Decimal

# =======================
# 👕 Jinja 版 AI 穿搭頁面（aichat.html）
# =======================
@aichat_bp.route('/', methods=['GET', 'POST'])
def chat():
    """
    這個路由用來呈現 Jinja 版的穿搭機器人頁面：
    - GET：顯示空白表單
    - POST：接收表單資料，呼叫 generate_recommendation()，再把結果 render 回 aichat.html
    """
    ai_response = None
    outfits = []
    keywords = []
    user_input = ""
    selected_model = "auto"

    if request.method == 'POST':
        user_input = request.form.get('message', '')
        selected_model = request.form.get('model', 'auto')
        session_id = "web-page-session"  # 固定給這個頁面用的 session

        ai_response, outfits, keywords = generate_recommendation(
            user_input=user_input,
            session_id=session_id,
            preferred_model=selected_model
        )

    return render_template(
        'aichat.html',
        ai_response=ai_response,
        outfits=outfits,
        keywords=keywords,
        user_input=user_input,
        selected_model=selected_model
    )

# =======================
# 📦 取得所有衣物（純 JSON API，保留）
# =======================
@aichat_bp.route('/items', methods=['GET'])
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
@aichat_bp.route('/recommend', methods=['POST'])
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

    ai_response, outfits, keywords = generate_recommendation(
        user_input=user_input,
        session_id=session_id,
        preferred_model=preferred_model
    )

    return jsonify({
        "response": ai_response,
        "session_id": session_id,
        "db_data": outfits,
        "keywords": keywords
    })

# =======================
# 🗑️ 清除對話記憶
# =======================
@aichat_bp.route('/clear_session', methods=['POST'])
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
@aichat_bp.route('/ping')
def ping():
    return jsonify({
        "status": "ok",
        "ai_enabled": bool(agent)
    })