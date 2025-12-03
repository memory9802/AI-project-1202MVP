"""
LangChain 整合模組：穿搭推薦 AI Agent
支援對話記憶、工具呼叫、資料庫查詢、多 AI 備援
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import os
import json
import sys
import time
from datetime import datetime
from threading import Lock
from functools import lru_cache

# 確保 Python 使用 UTF-8 編碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# JSON 對話記錄檔案路徑
CONVERSATIONS_FILE = "/app/data/conversations.json"
file_lock = Lock()  # 防止多執行緒同時寫入

# 速率限制設定
last_request_time = {}
rate_limit_lock = Lock()
MIN_REQUEST_INTERVAL = 2  # 最少間隔 2 秒 (降低 RPM)

# =========================
# 🔧 初始化 LangChain 模型
# =========================
class OutfitAIAgent:
    def __init__(self, gemini_key: str = None, groq_key: str = None, deepseek_key: str = None):
        """初始化 AI Agent（使用 LangChain，支援多模型備援）"""
        
        # 初始化多個 LLM（按優先順序：Gemini -> Groq -> DeepSeek）
        self.llms = []
        
        # 1. Gemini (優先) - 使用 Lite 版本,配額更高
        if gemini_key:
            try:
                self.llms.append({
                    "name": "Gemini",
                    "llm": ChatGoogleGenerativeAI(
                        model="gemini-2.0-flash-lite",  # Lite 版本:更高 RPM/TPM
                        google_api_key=gemini_key,
                        temperature=0.5,  # 降低溫度,減少隨機性
                        max_output_tokens=300  # 減少輸出長度,降低 TPM
                    )
                })
            except Exception as e:
                print(f"⚠️  Gemini 初始化失敗: {e}")
        
        # 2. Groq (備援)
        if groq_key:
            try:
                self.llms.append({
                    "name": "Groq",
                    "llm": ChatGroq(
                        model="llama-3.3-70b-versatile",
                        groq_api_key=groq_key,
                        temperature=1.0,
                        max_tokens=200
                    )
                })
            except Exception as e:
                print(f"⚠️  Groq 初始化失敗: {e}")
        
        # 3. DeepSeek (最終備援)
        if deepseek_key:
            try:
                self.llms.append({
                    "name": "DeepSeek",
                    "llm": ChatOpenAI(
                        model="deepseek-chat",
                        openai_api_key=deepseek_key,
                        openai_api_base="https://api.deepseek.com",
                        temperature=1.0,
                        max_tokens=200
                    )
                })
            except Exception as e:
                print(f"⚠️  DeepSeek 初始化失敗: {e}")
        
        if not self.llms:
            raise ValueError("❌ 至少需要一個可用的 API Key")
        
        print(f"✅ 已初始化 {len(self.llms)} 個 LLM: {[m['name'] for m in self.llms]}")
        
        # 對話記憶（每個 session 一個）
        self.sessions = {}
        
        # System Prompt - 超自然對話版
        self.system_prompt = """你是「搭搭」，一個活潑親切的穿搭顧問。

🎯 核心原則：像真人朋友一樣聊天，不要像客服機器人！

對話指引：
• 用戶打招呼 → 熱情回應 + 閒聊幾句
• 用戶閒聊 → 自然對話，不要急著推薦
• 用戶問穿搭 → 才開始專業推薦
• 語氣要輕鬆口語，像在 IG 聊天
• 可以用「欸」「對啊」「超讚」等口語詞
• 適度使用 emoji 😊👗✨

推薦穿搭時：
1. 有【資料庫選項】就從中挑
2. 每組 1-2 行簡短說明
3. 不超過 200 字

❌ 避免：
- 「很高興為您服務」（太正式）
- 「我是您的穿搭顧問」（太官方）
- 直接就開始推薦（太生硬）

✅ 要像這樣：
用戶：你好
你：嗨嗨！今天想聊什麼呢～ 😊

用戶：天氣好熱
你：對啊超熱的！這種天氣最適合穿輕薄的衣服了，需要推薦嗎？

用戶：我要去約會
你：約會欸！緊張嗎 😆 來幫你搭配幾套：
1. 休閒約會裝 - 白T + 牛仔褲，輕鬆自在
2. 浪漫約會裝 - 碎花洋裝，溫柔甜美"""
    
    def _load_conversations(self):
        """從 JSON 檔案載入對話記錄"""
        try:
            if os.path.exists(CONVERSATIONS_FILE):
                with file_lock:
                    with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except Exception as e:
            print(f"⚠️ 載入對話記錄失敗: {e}", file=sys.stderr)
        return {}
    
    def _save_conversations(self, conversations):
        """儲存對話記錄到 JSON 檔案"""
        try:
            os.makedirs(os.path.dirname(CONVERSATIONS_FILE), exist_ok=True)
            with file_lock:
                with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 儲存對話記錄失敗: {e}", file=sys.stderr)
    
    def get_or_create_session(self, session_id: str):
        """取得或建立對話 session（從 JSON 載入或建立新的）"""
        if session_id not in self.sessions:
            # 嘗試從 JSON 載入
            all_conversations = self._load_conversations()
            if session_id in all_conversations:
                self.sessions[session_id] = all_conversations[session_id]
                print(f"📂 載入 {session_id} 的歷史對話 ({len(all_conversations[session_id]['messages'])} 則)", file=sys.stderr)
            else:
                # 建立新 session
                self.sessions[session_id] = {
                    "history": [],
                    "messages": [],
                    "created_at": datetime.now().isoformat()
                }
                print(f"🆕 建立新的對話 session: {session_id}", file=sys.stderr)
        
        return self.sessions[session_id]
    
    def chat(self, session_id: str, user_input: str, db_outfits=None, preferred_model: str = "auto"):
        """對話式推薦（使用 LangChain，支援多模型備援和手動選擇）
        
        Args:
            session_id: 對話 session ID
            user_input: 用戶輸入
            db_outfits: 資料庫檢索的穿搭資料
            preferred_model: 偏好模型 ("auto", "gemini", "groq", "deepseek")
        """
        # ⏱️ 速率限制: 確保請求之間有最小間隔
        with rate_limit_lock:
            current_time = time.time()
            if session_id in last_request_time:
                elapsed = current_time - last_request_time[session_id]
                if elapsed < MIN_REQUEST_INTERVAL:
                    wait_time = MIN_REQUEST_INTERVAL - elapsed
                    print(f"⏳ 速率限制: 等待 {wait_time:.1f} 秒...", file=sys.stderr)
                    time.sleep(wait_time)
            last_request_time[session_id] = time.time()
        
        session = self.get_or_create_session(session_id)
        
        # 🎯 建立精簡對話上下文 - 減少 token 消耗
        context = ""
        if db_outfits and len(db_outfits) > 0:
            # 只用前2組穿搭,只顯示名稱和場合
            simplified = []
            for outfit in db_outfits[:2]:
                name = outfit.get('name', '未命名')
                occasion = outfit.get('occasion', '')
                simplified.append(f"{name}({occasion})")
            context = f"\n資料庫: {', '.join(simplified)}"
        
        # 只保留最近1輪對話 (大幅減少 token)
        history_text = ""
        if session["messages"]:
            last_msg = session["messages"][-1]
            history_text = f"上次: {last_msg['user'][:30]}...\n"
        
        # 🔥 精簡提示詞
        simple_prompt = f"你是穿搭顧問。{history_text}用戶: {user_input}{context}\n建議:"
        
        # 調試信息
        import sys
        print(f"\n{'='*50}", flush=True, file=sys.stderr)
        print(f"📝 用戶輸入: {user_input}", flush=True, file=sys.stderr)
        print(f"📦 資料庫穿搭數量: {len(db_outfits) if db_outfits else 0}", flush=True, file=sys.stderr)
        print(f"{'='*50}\n", flush=True, file=sys.stderr)
        
        # 根據用戶選擇決定使用哪些模型
        if preferred_model != "auto":
            # 手動選擇模式：只嘗試指定的模型
            models_to_try = [m for m in self.llms if m["name"].lower() == preferred_model.lower()]
            if not models_to_try:
                return f"❌ 模型 {preferred_model} 未設定或不可用"
            print(f"🎯 手動選擇使用 {preferred_model}", flush=True, file=sys.stderr)
        else:
            # 自動模式：依序嘗試所有模型
            models_to_try = self.llms
            print(f"🔄 自動模式：依序嘗試 {[m['name'] for m in models_to_try]}", flush=True, file=sys.stderr)
        
        # 依序嘗試 LLM
        response_text = None
        used_model = None
        
        for model_info in models_to_try:
            try:
                llm = model_info["llm"]
                model_name = model_info["name"]
                
                print(f"🔄 嘗試使用 {model_name}...", flush=True, file=sys.stderr)
                response = llm.invoke(simple_prompt)  # 使用精簡提示詞
                response_text = response.content if hasattr(response, 'content') else str(response)
                used_model = model_name
                print(f"✅ {model_name} 回應成功", flush=True, file=sys.stderr)
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ {model_name} 失敗: {error_msg}", flush=True, file=sys.stderr)
                
                if preferred_model != "auto":
                    # 手動模式失敗時返回友善的錯誤訊息
                    if "Insufficient Balance" in error_msg or "402" in error_msg:
                        return f"❌ {model_name} 餘額不足,請切換到「自動切換」模式或選擇其他模型 (Gemini/Groq)"
                    else:
                        return f"❌ {model_name} 回應失敗: {error_msg}\n\n💡 建議切換到「自動切換」模式或選擇其他模型"
                continue
        
        # 如果所有模型都失敗
        if response_text is None:
            response_text = "抱歉，目前所有 AI 服務都無法使用，請稍後再試。"
            used_model = "None"
        
        # 儲存對話（附註使用的模型和時間戳）
        session["messages"].append({
            "user": user_input,
            "ai": response_text,
            "model": used_model,
            "timestamp": datetime.now().isoformat()
        })
        
        session["history"].append({
            "user": user_input,
            "ai": response_text
        })
        
        # 儲存到 JSON 檔案
        all_conversations = self._load_conversations()
        all_conversations[session_id] = session
        self._save_conversations(all_conversations)
        
        return response_text
    
    def clear_session(self, session_id: str):
        """清除對話記憶（記憶體和 JSON 檔案）"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # 同時從 JSON 移除
        all_conversations = self._load_conversations()
        if session_id in all_conversations:
            del all_conversations[session_id]
            self._save_conversations(all_conversations)
        
        return True
    
    def get_session_history(self, session_id: str):
        """取得對話歷史"""
        if session_id in self.sessions:
            return self.sessions[session_id]["history"]
        return None


# =========================
# 🧪 測試範例
# =========================
if __name__ == "__main__":
    api_key = os.getenv("LLM_API_KEY", "")
    
    if not api_key:
        print("❌ 請設定 LLM_API_KEY 環境變數")
        exit(1)
    
    agent = OutfitAIAgent(api_key)
    
    # 模擬對話
    session_id = "test-user-123"
    
    print("=== 第一輪對話 ===")
    response1 = agent.chat(session_id, "今天要去約會，天氣有點涼")
    print(f"AI: {response1}\n")
    
    print("=== 第二輪對話（測試記憶） ===")
    response2 = agent.chat(session_id, "那如果改成去運動呢？")
    print(f"AI: {response2}\n")
    
    print("=== 對話歷史 ===")
    history = agent.get_session_history(session_id)
    print(json.dumps(history, ensure_ascii=False, indent=2))

