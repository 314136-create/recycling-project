from flask import Flask, render_template, render_template_string, request, redirect, url_for, send_from_directory, session, jsonify
import os
from dotenv import load_dotenv
import sqlite3
from functools import wraps
from datetime import datetime, timedelta

# 載入 .env 檔案環境變數 (必須在引入 QA.py 前執行)
load_dotenv()

# --- 新增處理圖片的套件 ---
from PIL import Image
import pillow_heif

# 確保 QA.py 與 auth.py 與此檔案在同一目錄
from QA import (recognize_item, generate_recycling_quiz, get_level, 
                XP_REWARD_CORRECT, XP_REWARD_WRONG, get_image_hash)
from auth import (register_user, login_user, get_user_xp_by_username, 
                  update_user_xp_by_username, is_duplicate_image_for_user, 
                  save_to_history_for_user, can_upload_today, increment_daily_upload,
                  get_remaining_uploads, DAILY_UPLOAD_LIMIT)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_123')

# 設定圖片上傳存檔的路徑
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# === 1. NFC 資料庫設定 (整合自 Demo.py) ===
NFC_DB = os.path.join(BASE_DIR, 'NFCtag.db')

def init_db():
    """初始化 NFC 資料庫"""
    with sqlite3.connect(NFC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS NFCtag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serialno TEXT NOT NULL,
                starttime TIMESTAMP,
                endtime TIMESTAMP
            )
        ''')
        conn.commit()

def format_duration(seconds):
    """格式化秒數為 HH:mm:ss"""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"

# === 1.1 NFC 數據處理函數 (直接讀取本地 SQLite) ===
def get_weekly_usage(username):
    weekly_seconds = {i: 0 for i in range(7)}
    try:
        today = datetime.now()
        monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        monday_str = monday.strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(NFC_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT starttime, endtime FROM NFCtag WHERE endtime IS NOT NULL AND starttime >= ? AND serialno = ?",
                (monday_str, username)
            )
            rows = cursor.fetchall()
        fmt = '%Y-%m-%d %H:%M:%S'
        for start_str, end_str in rows:
            try:
                st = datetime.strptime(start_str, fmt)
                et = datetime.strptime(end_str, fmt)
                weekly_seconds[st.weekday()] += (et - st).total_seconds()
            except:
                continue
    except Exception as e:
        print(f"時數計算失敗: {e}")
    # 改為回傳分鐘數
    return {day: round(sec / 60, 1) for day, sec in weekly_seconds.items()}

def get_weekly_sessions(username):
    weekly_sessions = {i: [] for i in range(7)}
    try:
        today = datetime.now()
        monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        monday_str = monday.strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(NFC_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT starttime, endtime FROM NFCtag WHERE starttime >= ? AND serialno = ? ORDER BY id DESC",
                (monday_str, username)
            )
            rows = cursor.fetchall()
        fmt = '%Y-%m-%d %H:%M:%S'
        for start_str, end_str in rows:
            try:
                st = datetime.strptime(start_str, fmt)
                dur = "-"
                if end_str:
                    diff = datetime.strptime(end_str, fmt) - st
                    h, m = divmod(int(diff.total_seconds()), 3600)
                    m, s = divmod(m, 60)
                    dur = f"{h:02}:{m:02}:{s:02}"
                weekly_sessions[st.weekday()].append({
                    'start': start_str.split(' ')[1],
                    'end': end_str.split(' ')[1] if end_str else "進行中",
                    'duration': dur
                })
            except:
                continue
    except Exception as e:
        print(f"Sessions 讀取失敗: {e}")
    return weekly_sessions

def get_chart_data(username):
    try:
        usage = get_weekly_usage(username)
        sessions = get_weekly_sessions(username)
        minutes_list = [usage.get(i, 0.0) for i in range(7)]
        sessions_list = [sessions.get(i, []) for i in range(7)]
        return minutes_list, sessions_list
    except Exception as e:
        print(f"圖表封裝錯誤: {e}")
        return [0.0]*7, [[] for _ in range(7)]

# === 2. 登入裝飾器 ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# === 2.5 上傳圖片路由 ===
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === 3. 核心路由 ===
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pwd = request.form.get('password', '')
        success, msg = login_user(user, pwd)
        if success:
            session['username'] = user
            return redirect(url_for('home'))
        return render_template('login.html', error=msg)
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    user = request.form.get('username', '').strip()
    pwd = request.form.get('password', '')
    if pwd != request.form.get('confirm_password', ''):
        return render_template('login.html', error='密碼輸入不一致')
    success, msg = register_user(user, pwd)
    return render_template('login.html', 
                           success='註冊成功，請登入！' if success else None, 
                           error=None if success else msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def home():
    username = session['username']
    xp = get_user_xp_by_username(username)
    minutes_list, sessions_list = get_chart_data(username)
    return render_template('demo_baby_v4.html', 
                           xp=xp, 
                           level=get_level(xp), 
                           username=username, 
                           chart_data=minutes_list, 
                           sessions_data=sessions_list)

@app.route('/scan', methods=['GET', 'POST'])
@login_required
def scan_page():
    username = session['username']
    if request.method == 'POST':
        # --- 每日上傳次數檢查 ---
        can_upload, count = can_upload_today(username)
        if not can_upload:
            return render_template('index.html', username=username,
                                   remaining_uploads=0, daily_limit=DAILY_UPLOAD_LIMIT,
                                   daily_limit_error=True)

        file = request.files.get('file')
        if file and file.filename:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # --- 新增：處理 HEIC 轉檔邏輯 ---
            if filename.lower().endswith('.heic'):
                try:
                    heif_file = pillow_heif.read_heif(filepath)
                    image = Image.frombytes(
                        heif_file.mode, 
                        heif_file.size, 
                        heif_file.data,
                        "raw",
                    )
                    # 更改副檔名為 .jpg
                    new_filename = filename.rsplit('.', 1)[0] + ".jpg"
                    new_filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    image.save(new_filepath, "JPEG")
                    
                    # 更新後續辨識使用的路徑與檔名
                    filepath = new_filepath
                    filename = new_filename
                except Exception as e:
                    return f"HEIC 轉檔失敗: {e}"
            # --------------------------

            # --- 圖片重複檢查 ---
            img_hash = get_image_hash(filepath)
            if is_duplicate_image_for_user(username, img_hash):
                return render_template('index.html', username=username,
                                       remaining_uploads=get_remaining_uploads(username),
                                       daily_limit=DAILY_UPLOAD_LIMIT,
                                       duplicate_error=True)

            # AI 辨識與題目生成 (傳入的是處理過的 filepath)
            item_result = recognize_item(filepath)
            if "失敗" in item_result or "忙碌" in item_result:
                return f"AI 辨識發生錯誤: {item_result}"
                
            q, o, a, e = generate_recycling_quiz(item_result)
            session.update({'correct_answer': a, 'explanation': e})

            # --- 記錄圖片 Hash 並增加每日上傳次數 ---
            save_to_history_for_user(username, img_hash)
            increment_daily_upload(username)
            
            return render_template('result.html', 
                                   image_file=filename, 
                                   item_result=item_result, 
                                   question=q, 
                                   options=o, 
                                   username=username)
                                   
    return render_template('index.html', 
                           username=username, 
                           remaining_uploads=get_remaining_uploads(username),
                           daily_limit=DAILY_UPLOAD_LIMIT)

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    user_ans = request.json.get('answer', '').upper()
    correct_ans = session.get('correct_answer')
    explanation = session.get('explanation', '')
    is_correct = user_ans == correct_ans
    xp = XP_REWARD_CORRECT if is_correct else XP_REWARD_WRONG

    old_xp = get_user_xp_by_username(session['username'])
    old_level = get_level(old_xp)
    new_xp = update_user_xp_by_username(session['username'], xp)
    new_level = get_level(new_xp)

    return jsonify({
        'correct': is_correct,
        'gained_xp': xp,
        'current_total_xp': new_xp,
        'correct_answer': correct_ans,
        'explanation': explanation,
        'leveled_up': new_level > old_level,
        'new_level': new_level
    })

@app.route('/healthz')
def healthz():
    return "OK", 200

# === NFC 路由 (整合自 Demo.py) ===
@app.route('/nfc_update', methods=['GET'])
def nfc_update():
    """NFC 感應器呼叫此路由進行打卡 (Check In / Check Out)"""
    sno = request.args.get('sno')
    if not sno:
        return "Missing sno", 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(NFC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM NFCtag WHERE serialno = ? AND endtime IS NULL", (sno,))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE NFCtag SET endtime = ? WHERE id = ?", (now, row[0]))
            msg = f"OK: {sno} Checked Out"
        else:
            cursor.execute("INSERT INTO NFCtag (serialno, starttime, endtime) VALUES (?, ?, NULL)", (sno, now))
            msg = f"OK: {sno} Checked In"
        conn.commit()
    return msg

@app.route('/nfc_view')
def nfc_view():
    """NFC 即時監控頁面"""
    with sqlite3.connect(NFC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, serialno, starttime, endtime FROM NFCtag ORDER BY id DESC")
        rows = cursor.fetchall()

    data = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for r in rows:
        diff_str = "-"
        color = "yellow"
        if r[3]:
            start = datetime.strptime(r[2], fmt)
            end = datetime.strptime(r[3], fmt)
            diff_str = format_duration((end - start).total_seconds())
            color = "lightgreen"
        data.append({
            "id": r[0], "sno": r[1], "start": r[2],
            "end": r[3] or "In Progress...", "duration": diff_str, "color": color
        })

    html = '''
    <html>
        <head><meta http-equiv="refresh" content="1">
        <style>
            table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
            th, td { padding: 10px; border: 1px solid #ccc; text-align: center; }
        </style>
        </head>
        <body>
            <h2>NFC Tag 即時監控清單</h2>
            <table>
                <tr style="background-color: #333; color: white;">
                    <th>ID</th><th>Serial No</th><th>Start Time</th><th>End Time</th><th>Duration (HH:mm:ss)</th>
                </tr>
                {% for item in data %}
                <tr style="background-color: {{ item.color }};">
                    <td>{{ item.id }}</td><td>{{ item.sno }}</td><td>{{ item.start }}</td>
                    <td>{{ item.end }}</td><td><b>{{ item.duration }}</b></td>
                </tr>
                {% endfor %}
            </table>
        </body>
    </html>
    '''
    return render_template_string(html, data=data)

@app.route('/nfc_stat')
def nfc_stat():
    """NFC 統計數據頁面"""
    with sqlite3.connect(NFC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT starttime, endtime FROM NFCtag WHERE endtime IS NOT NULL")
        rows = cursor.fetchall()

    total_seconds = 0
    fmt = '%Y-%m-%d %H:%M:%S'
    for r in rows:
        start = datetime.strptime(r[0], fmt)
        end = datetime.strptime(r[1], fmt)
        total_seconds += (end - start).total_seconds()

    total_time_str = format_duration(total_seconds)

    html = '''
    <html>
        <head><meta http-equiv="refresh" content="1"></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h2>NFC 統計數據</h2>
            <div style="border: 2px solid #333; padding: 15px; display: inline-block;">
                <p>已完成總筆數：<span style="font-size: 1.5em; color: blue;">{{ count }}</span></p>
                <p>總累計工時：<span style="font-size: 1.5em; color: red;">{{ total_time }}</span> (HH:mm:ss)</p>
            </div>
            <br><br><a href="/nfc_view">查看詳細清單</a>
        </body>
    </html>
    '''
    return render_template_string(html, count=len(rows), total_time=total_time_str)

if __name__ == '__main__':
    init_db()  # 初始化 NFC 資料庫
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
