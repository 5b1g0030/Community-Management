from modules.databases.databaseManager import DatabaseManager
import logging as log

""" ===== 這裡放人臉辨識的所有SQL操作 ====="""

db = DatabaseManager()

# ===== 取得所有人臉資料 =====
def get_all_face():
    conn, cursor = db.get_db_connection()
    # 讀取全部已註冊人臉
    cursor.execute("SELECT id, name, encoding FROM face_recognition")
    data = cursor.fetchall() # 取得資料
    conn.close()
    log.info(f"已讀取全部已註冊人臉，結果 {data}")

    return data

# ===== 插入人臉資料 =====
def insert_face(name, encoding_blob):
    conn, cursor = db.get_db_connection()
    # 把一筆新的人臉資料寫進 face_recognition 表
    # 寫入欄位包含: 姓名、特徵向量、建立時間、更新時間
    cursor.execute(
        "INSERT INTO face_recognition "
        "(name, encoding, created_date, updated_date) " \
        "VALUES (?, ?, datetime('now'), datetime('now'))", 
        (name, encoding_blob)
    )
    id = cursor.lastrowid # 回傳這筆新增資料的 id，方便做關聯
    log.info(f"插入人臉資料，該資料id= {id}")
    conn.commit()
    conn.close()

    return id