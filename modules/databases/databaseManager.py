# 【資料庫初始化類別】
from modules.config import DATABASE # 從上一層資料夾中匯入該模組
import sqlite3

# ===== 資料庫初始化類別 =====
# 提供資料庫連接函式、初始化資料表
# ===========================
class DatabaseManager:

    # ====== 初始化 ======
    def __init__(self, db_path=DATABASE):
        self.db_path = db_path # 設定路徑
        # self._init_database()

    # ===== 初始化資料庫 =====
    # 建立資料庫表格(已存在則不建立)
    # =======================
    def init_database(self):
        conn, cursor = self.get_db_connection() # 使用統一的連接方法

        # ----- 新人臉識別(face_recognition) -----
        # (儲存姓名與 128 維特徵向量；存成 text，內容為 json 格式)
        # id(自動編號)
        # 名稱
        # 維特徵向量
        # ---------------------------------------
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_recognition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding BLOB NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ------ 創建辨識記錄表(recognition_log) -----
        # id: 主鍵、自動遞增、不可重複
        # created_date: 事件發生日期時間
        # event_type: 事件類型 (住戶、未知、訪客)
        # event_message: 事件訊息描述
        # face_id: 參照faces表格id (選填，未知人物時為NULL)
        # confidence: 信心度，REAL => 小數點 (選填)
        # -------------------------------------------- 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recognition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_message TEXT NOT NULL,
                face_id INTEGER,
                confidence REAL,
                FOREIGN KEY (face_id) REFERENCES faces (id)
            )
        ''')

        # ----- 建立訪客預約紀錄表(visitor_bookings) -----
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS visitor_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    visitor_face_name TEXT NOT NULL,
                    visitor_face_id INTEGER NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used INTEGER DEFAULT 0,
                    used_date TIMESTAMP,
                    FOREIGN KEY (visitor_face_id) REFERENCES face_recognition (id)
                )    
        ''')

        # ----- 建立使用者資料表格(users) -----
        # id: 主鍵、自動遞增、不可重複
        # username: 使用者名稱、文字、不可為空、不重複
        # password_hash: 密碼(加密後)、文字、不可為空
        # created_date: 帳戶建立時間、時間戳記、預設當前時間
        # -----------------------------
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT '住戶',
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP       
                )    
        ''')

        # ----- 建立包裹櫃位表格(package_lockers) -----
        # id: 主鍵、自動遞增、不可重複
        # locker_number: 櫃號、整數、唯一、不為空，用於標識每個櫃位
        # recipient_name: 收件人、文字，存儲包裹的收件人
        # registered_date: 登記的日期和時間、文字
        # is_occupied: 櫃位是否被佔用、整數、預設值0，0 表示空閒，1 表示已佔用
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS package_lockers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    locker_number INTEGER UNIQUE NOT NULL,
                    recipient_name TEXT,
                    registered_date TEXT,
                    is_occupied INTEGER DEFAULT 0
                )
            """)    
        # 插入初始櫃位資料（1號和2號）
        cursor.execute("INSERT OR IGNORE INTO package_lockers (locker_number, is_occupied) VALUES (1, 0)")
        cursor.execute("INSERT OR IGNORE INTO package_lockers (locker_number, is_occupied) VALUES (2, 0)")

        conn.commit() # 確認變更(寫入磁碟)
        conn.close() # 關閉連接
        print("資料庫初始化完成 by databaseManager")

    # ===== 建立資料庫連接與游標 =====
    # 回傳 連接物件和游標物件
    # ===============================
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        return conn, cursor