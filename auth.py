"""
帳號系統 - 處理用戶註冊、登入、資料存取
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any

# 用戶資料目錄
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
USERS_DIR = os.path.join(BASE_DIR, 'users')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')

# 確保目錄存在
os.makedirs(USERS_DIR, exist_ok=True)

def hash_password(password: str) -> str:
    """密碼雜湊處理"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def load_users() -> Dict[str, Any]:
    """載入所有用戶資料"""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_users(users: Dict[str, Any]):
    """儲存所有用戶資料"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def register_user(username: str, password: str) -> tuple[bool, str]:
    """
    註冊新用戶
    返回: (成功與否, 訊息)
    """
    # 驗證
    if not username or not password:
        return False, "帳號和密碼不能為空"
    
    if len(username) < 3:
        return False, "帳號至少需要 3 個字元"
    
    if len(password) < 4:
        return False, "密碼至少需要 4 個字元"
    
    # 檢查是否已存在
    users = load_users()
    if username in users:
        return False, "此帳號已被註冊"
    
    # 建立新用戶
    users[username] = {
        'password_hash': hash_password(password),
        'created_at': __import__('datetime').datetime.now().isoformat()
    }
    save_users(users)
    
    # 建立用戶專屬資料夾
    user_dir = get_user_dir(username)
    os.makedirs(user_dir, exist_ok=True)
    
    # 初始化用戶 XP 檔案
    xp_file = os.path.join(user_dir, 'xp.txt')
    with open(xp_file, 'w', encoding='utf-8') as f:
        f.write('0')
    
    return True, "註冊成功！"

def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    用戶登入驗證
    返回: (成功與否, 訊息)
    """
    if not username or not password:
        return False, "請輸入帳號和密碼"
    
    users = load_users()
    
    if username not in users:
        return False, "帳號不存在"
    
    if users[username]['password_hash'] != hash_password(password):
        return False, "密碼錯誤"
    
    return True, "登入成功！"

def get_user_dir(username: str) -> str:
    """取得用戶專屬資料夾路徑"""
    return os.path.join(USERS_DIR, username)

def get_user_xp_file(username: str) -> str:
    """取得用戶 XP 檔案路徑"""
    return os.path.join(get_user_dir(username), 'xp.txt')

def get_user_history_file(username: str) -> str:
    """取得用戶圖片歷史檔案路徑"""
    return os.path.join(get_user_dir(username), 'history.txt')

# === 用戶專屬的 XP 和歷史紀錄函數 ===

def get_user_xp_by_username(username: str) -> int:
    """讀取特定用戶的經驗值"""
    xp_file = get_user_xp_file(username)
    if not os.path.exists(xp_file):
        # 確保目錄和檔案存在
        user_dir = get_user_dir(username)
        os.makedirs(user_dir, exist_ok=True)
        with open(xp_file, 'w', encoding='utf-8') as f:
            f.write('0')
        return 0
    try:
        with open(xp_file, 'r', encoding='utf-8') as f:
            return int(f.read().strip())
    except:
        return 0

def update_user_xp_by_username(username: str, gained_xp: int) -> int:
    """更新特定用戶的經驗值"""
    current_xp = get_user_xp_by_username(username)
    new_total = current_xp + gained_xp
    xp_file = get_user_xp_file(username)
    
    # 確保目錄存在
    user_dir = get_user_dir(username)
    os.makedirs(user_dir, exist_ok=True)
    
    with open(xp_file, 'w', encoding='utf-8') as f:
        f.write(str(new_total))
    return new_total

def is_duplicate_image_for_user(username: str, img_hash: str) -> bool:
    """檢查圖片是否在該用戶的歷史中重複"""
    history_file = get_user_history_file(username)
    if not os.path.exists(history_file):
        return False
    with open(history_file, 'r', encoding='utf-8') as f:
        existing_hashes = {line.strip() for line in f}
    return img_hash in existing_hashes

def save_to_history_for_user(username: str, img_hash: str):
    """儲存圖片紀錄到用戶的歷史"""
    history_file = get_user_history_file(username)
    
    # 確保目錄存在
    user_dir = get_user_dir(username)
    os.makedirs(user_dir, exist_ok=True)
    
    with open(history_file, 'a', encoding='utf-8') as f:
        f.write(img_hash + '\n')

# === 每日上傳次數限制 ===
from datetime import datetime, date

DAILY_UPLOAD_LIMIT = 3  # 每日最多上傳次數

def get_user_daily_upload_file(username: str) -> str:
    """取得用戶每日上傳紀錄檔案路徑"""
    return os.path.join(get_user_dir(username), 'daily_uploads.json')

def get_daily_upload_count(username: str) -> tuple[int, str]:
    """
    取得用戶今日的上傳次數
    返回: (今日上傳次數, 紀錄日期)
    """
    upload_file = get_user_daily_upload_file(username)
    today = date.today().isoformat()  # 格式: 2026-01-29
    
    if not os.path.exists(upload_file):
        return 0, today
    
    try:
        with open(upload_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果是今天的紀錄，返回次數
        if data.get('date') == today:
            return data.get('count', 0), today
        else:
            # 不是今天的紀錄，重置為 0
            return 0, today
    except:
        return 0, today

def increment_daily_upload(username: str) -> int:
    """
    增加用戶今日的上傳次數
    返回: 更新後的次數
    """
    upload_file = get_user_daily_upload_file(username)
    today = date.today().isoformat()
    
    current_count, _ = get_daily_upload_count(username)
    new_count = current_count + 1
    
    # 確保目錄存在
    user_dir = get_user_dir(username)
    os.makedirs(user_dir, exist_ok=True)
    
    data = {
        'date': today,
        'count': new_count
    }
    
    with open(upload_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    return new_count

def can_upload_today(username: str) -> tuple[bool, int]:
    """
    檢查用戶今日是否還能上傳
    返回: (是否可以上傳, 已上傳次數)
    """
    count, _ = get_daily_upload_count(username)
    return count < DAILY_UPLOAD_LIMIT, count

def get_remaining_uploads(username: str) -> int:
    """取得用戶今日剩餘的上傳次數"""
    count, _ = get_daily_upload_count(username)
    return max(0, DAILY_UPLOAD_LIMIT - count)
