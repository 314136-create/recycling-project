import os
import re
import hashlib
from PIL import Image
import google.generativeai as genai  # 統一標準導入方式

# ==========================================
# 1. 初始化設定
# ==========================================
# 從環境變數讀取 API Key (建議使用截圖中那組健康的 "0302" Key)
API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # 回復使用 1.5-flash 模型，3.1 preview 目前可能不支援或無權限
    MODEL_NAME = "gemini-1.5-flash"
    model = genai.GenerativeModel(MODEL_NAME)
else:
    # 防止 API Key 缺失導致整個程式崩潰
    model = None
    print("警告：未設定 GEMINI_API_KEY 環境變數")

# 🎮 遊戲平衡設定
XP_REWARD_CORRECT = 50
XP_REWARD_WRONG = 10
XP_PER_LEVEL = 50

# ==========================================
# 2. 功能函數
# ==========================================

def get_image_hash(image_path):
    """計算圖片 Hash 以防止重複上傳獲得經驗值"""
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_level(xp):
    """根據經驗值計算等級"""
    return (xp or 0) // XP_PER_LEVEL

def recognize_item(image_path):
    """呼叫 AI 辨識圖片中的回收物"""
    if not model:
        return "辨識失敗：API 未初始化，請檢查 API Key 設定。"
    
    try:
        img = Image.open(image_path)
        # 設定辨識指令
        prompt = "請辨識圖片中的物品名稱與材質，用繁體中文回答。格式：這是一個(物品)，材質是(材質)。"
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        # 捕捉如 404 或 429 (流量限制) 等錯誤
        return f"AI 辨識暫時忙碌中: {str(e)}"

def generate_recycling_quiz(item_description):
    """根據辨識結果生成回收問答題"""
    if not model:
        return "如何回收？", "(A)資源回收 (B)一般垃圾", "A", "請依規定處理。"

    prompt = f"針對【{item_description}】出一個回收知識選擇題。格式必須嚴格遵守：\nQUESTION_START 題目 QUESTION_END \nOPTIONS_START (A)選項 (B)選項 OPTIONS_END \nANSWER_START 答案字母 ANSWER_END \nEXPLANATION_START 解析 EXPLANATION_END"
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        # 使用正則表達式解析 AI 回傳的固定格式
        q = re.search(r'QUESTION_START(.*?)QUESTION_END', text, re.S).group(1).strip()
        o = re.search(r'OPTIONS_START(.*?)OPTIONS_END', text, re.S).group(1).strip()
        a = re.search(r'ANSWER_START\s*([A-D])\s*ANSWER_END', text, re.I).group(1).upper()
        e = re.search(r'EXPLANATION_START(.*?)EXPLANATION_END', text, re.S).group(1).strip()
        return q, o, a, e
    except Exception:
        # 萬一 AI 回傳格式不符，提供一組保底題目防止 500 錯誤
        return "關於此物品的回收方式？", "(A)清洗後丟回收桶 (B)直接丟垃圾桶", "A", "正確的回收流程能減少環境負擔。"