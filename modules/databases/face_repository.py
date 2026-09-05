from modules.databases.databaseManager import DatabaseManager
import logging as log

""" ===== 這裡放人臉辨識的所有SQL操作 ====="""

db = DatabaseManager()

# ===== 取得所有人臉資料 =====
# 【修改】函式宣告加上 async 轉換為非同步函式
async def get_all_face():
    # 【修改】呼叫非同步的資料庫連線需加上 await
    conn, cursor = await db.get_db_connection()
    # 讀取全部已註冊人臉
    # 【修改】執行 SQL 查詢需加上 await
    await cursor.execute("SELECT id, name, encoding FROM face_recognition")
    # 【修改】取得資料 (fetchall) 在 aiosqlite 中為非同步操作，需加上 await
    data = await cursor.fetchall() # 取得資料
    # 【修改】關閉連線需加上 await
    await conn.close()
    log.info(f"已讀取全部已註冊人臉，結果 {data}")

    return data

# ===== 插入人臉資料 =====
# 【修改】函式宣告加上 async 轉換為非同步函式
async def insert_face(name, encoding_blob):
    # 【修改】呼叫非同步的資料庫連線需加上 await
    conn, cursor = await db.get_db_connection()
    # 把一筆新的人臉資料寫進 face_recognition 表
    # 寫入欄位包含: 姓名、特徵向量、建立時間、更新時間
    # 【修改】非同步寫入資料庫加上 await
    await cursor.execute(
        "INSERT INTO face_recognition "
        "(name, encoding, created_date, updated_date) " \
        "VALUES (?, ?, datetime('now'), datetime('now'))", 
        (name, encoding_blob)
    )
    # 備註：在 aiosqlite 中，lastrowid 是屬性，因此不需要 await
    id = cursor.lastrowid # 回傳這筆新增資料的 id，方便做關聯
    log.info(f"插入人臉資料，該資料id= {id}")
    # 【修改】非同步確認交易 (commit) 加上 await
    await conn.commit()
    # 【修改】非同步關閉連線加上 await
    await conn.close()

    return id