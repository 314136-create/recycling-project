import sqlite3
from flask import Flask, request, render_template_string
from datetime import datetime




app = Flask(__name__)
DB_NAME = "NFCtag.db"




def init_db():
    with sqlite3.connect(DB_NAME) as conn:
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




# 新的時間格式化函式：傳回 HH:mm:ss
def format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"




@app.route('/nfc_update', methods=['GET'])
def nfc_update():
    sno = request.args.get('sno')
    if not sno:
        return "Missing sno", 400
   
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(DB_NAME) as conn:
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




@app.route('/view')
def view():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, serialno, starttime, endtime FROM NFCtag ORDER BY id DESC")
        rows = cursor.fetchall()
   
    data = []
    fmt = '%Y-%m-%d %H:%M:%S'
    for r in rows:
        diff_str = "-"
        color = "yellow"
        if r[3]: # 如果 endtime 不是 NULL
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




@app.route('/stat')
def stat():
    with sqlite3.connect(DB_NAME) as conn:
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
            <br><br><a href="/view">查看詳細清單</a>
        </body>
    </html>
    '''
    return render_template_string(html, count=len(rows), total_time=total_time_str)




if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)