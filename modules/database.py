import sqlite3
from datetime import datetime
from .user import UserManager

# ===== 資料庫存取類別 =====
class DatabaseManager:
    # ===== 初始化資料庫觸發函式 =====
    def __init__(self, db_path='face_database/face_database.db'):
        self.db_path = db_path # 設定路徑
        self.init_database()
        # 建立 user manager 以維持舊有 API 的轉發
        self.user_manager = UserManager(self.db_path)
    
    # ===== 初始化資料庫 =====
    # 建立資料庫表格(已存在則不建立)
    # =======================  
    def init_database(self):
        conn = sqlite3.connect(self.db_path) # 連接到指定路徑的 SQLite 資料庫
        cursor = conn.cursor() # 建立游標物件用於執行 SQL 指令
        
        # ----- 創建人臉資料表(faces) -----
        # id: 主鍵、自動遞增、不可重複
        # name: 人名、不可為空值
        # face_encoding: 人臉特徵資料、BLOB 格式序列化陣列
        # image_path: 原始圖片(可不存)
        # create_date: 資料建立日期時間
        # ------------------------- 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                face_encoding BLOB,
                image_path TEXT,
                created_date TEXT
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

        # 檢查並升級舊的 recognition_log 表格
        try:
            cursor.execute("PRAGMA table_info(recognition_log)")
            cols = [row[1] for row in cursor.fetchall()]
            
            # 如果是舊版本的表格，需要重新建構
            if 'event_type' not in cols or 'event_message' not in cols:
                # 備份舊資料
                cursor.execute("ALTER TABLE recognition_log RENAME TO recognition_log_old")
                
                # 建立新表格
                cursor.execute('''
                    CREATE TABLE recognition_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_date TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_message TEXT NOT NULL,
                        face_id INTEGER,
                        confidence REAL,
                        FOREIGN KEY (face_id) REFERENCES faces (id)
                    )
                ''')
                
                # 遷移舊資料 (將舊的 recognition_date 轉為 created_date，設定預設事件類型)
                cursor.execute('''
                    INSERT INTO recognition_log (created_date, event_type, event_message, face_id, confidence)
                    SELECT 
                        recognition_date,
                        '住戶',
                        '舊版本辨識紀錄',
                        face_id,
                        confidence
                    FROM recognition_log_old
                ''')
                
                # 刪除舊表格
                cursor.execute("DROP TABLE recognition_log_old")
                print("辨識紀錄表格已升級至新版本")
        except Exception as e:
            print(f"升級辨識紀錄表格時發生錯誤: {e}")

        # ----- 建立使用者資料表格 -----
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
        
        # 如果已有舊的 users 表但沒有 role 欄位，嘗試加入欄位（避免破壞既有資料）
        try:
            cursor.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'role' not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT '住戶'")
        except Exception:
            # 若 ALTER 失敗則忽略（不致命）
            pass

        # ----- 建立訪客預約資料表格 -----
        # id: 主鍵、自動遞增、不可重複
        # username: 住戶名稱、文字、不可為空
        # booking_code: 6位數預約碼、文字、不可為空、不重複
        # created_date: 預約建立時間
        # used: 是否已使用、布林值、預設為False
        # used_date: 使用時間
        # -----------------------------
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS visitor_bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    booking_code TEXT UNIQUE NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE,
                    used_date TIMESTAMP       
                )    
        ''')

        # ----- 建立訪客留言資料表格 -----
        # id: 主鍵、自動遞增、不可重複
        # username: 住戶名稱、文字、不可為空
        # visitor_image_path: 訪客照片路徑、文字、不可為空
        # created_date: 留言建立時間
        # booking_code: 對應的預約碼（選填）
        # status: 審核狀態 (pending, approved, rejected)
        # reviewed_date: 審核時間
        # -----------------------------
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    visitor_image_path TEXT NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    booking_code TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_date TIMESTAMP
                )    
        ''')

        # 如果已有舊的 user_message 表但沒有 status 和 reviewed_date 欄位，嘗試加入欄位
        try:
            cursor.execute("PRAGMA table_info(user_message)")
            cols = [row[1] for row in cursor.fetchall()]
            if 'status' not in cols:
                cursor.execute("ALTER TABLE user_message ADD COLUMN status TEXT DEFAULT 'pending'")
            if 'reviewed_date' not in cols:
                cursor.execute("ALTER TABLE user_message ADD COLUMN reviewed_date TIMESTAMP")
        except Exception:
            # 若 ALTER 失敗則忽略（不致命）
            pass

        conn.commit() # 確認變更(寫入磁碟)
        conn.close() # 關閉連接
        print("資料庫初始化完成 by database")

    # ===== 列出資料庫中的所有人臉資料 =====
    # 回傳 字典格式資料
    # ==================================== 
    def get_all_faces(self):
        try:
            conn = sqlite3.connect(self.db_path) # 連接資料庫
            cursor = conn.cursor()               # 建立物件執行 SQL 指令
            
            # 查詢資料(face 表格中的三個欄位(id, name, created_date))
            cursor.execute("SELECT id, name, created_date FROM faces")

            # 資料轉換(列表推導式，把原始資料轉換為字典格式)
            faces = [{
                'id': row[0],
                'name': row[1],
                'created_date': row[2]}
                for row in cursor.fetchall()
                ]
            conn.close() # 關閉連接
            return faces # 回傳資料查詢結果
        
        # 查詢資料庫時的例外錯誤(資料庫檔案不存在、權限問題、資料庫鎖定等)
        except sqlite3.DatabaseError as e:
            print(f"資料庫查詢時發生錯誤 by database: {e}")
            return [] # 回傳空列表，防止程式崩潰
        
        # 查詢人臉資料時發生的例外錯誤
        except Exception as e:
            print(f"查詢人臉資料時發生錯誤 by database: {e}")
            return [] # 回傳空列表
        
        # 一定會執行的部分
        finally:
            if 'conn' in locals(): # 檢查 conn 是否存在
                conn.close() # 關閉資料庫

    # ===== 列出資料庫中的所有辨識紀錄 =====
    # 回傳 字典格式資料
    # =================================== 
    def get_all_recognition_logs(self):
        try:
            conn = sqlite3.connect(self.db_path) # 連接資料庫
            cursor = conn.cursor()               # 建立物件執行 SQL 指令
            
            # 查詢辨識紀錄，並與人臉表格做關聯以取得人名，同時包含face_id和confidence
            cursor.execute('''
                SELECT rl.id, rl.created_date, rl.event_type, rl.event_message, f.name, rl.confidence, rl.face_id
                FROM recognition_log rl
                LEFT JOIN faces f ON rl.face_id = f.id
                ORDER BY rl.created_date DESC
            ''')
            
            # 資料轉換為字典格式
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'created_date': row[1],
                    'event_type': row[2],
                    'event_message': row[3],
                    'name': row[4],
                    'confidence': row[5],
                    'face_id': row[6]
                })
            
            conn.close() # 關閉連接
            return logs  # 回傳資料查詢結果
        
        # 查詢資料庫時的例外錯誤(資料庫檔案不存在、權限問題、資料庫鎖定等)
        except sqlite3.DatabaseError as e:
            print(f"查詢時發生錯誤 by database: {e}")
        
        # 查詢辨識紀錄時發生的例外錯誤
        except Exception as e:
            print(f"查詢辨識紀錄時發生錯誤 by database: {e}")
        
        # 一定會執行的部分
        finally:
            if 'conn' in locals(): # 確認 conn 存在
                conn.close()
    
    # ===== add_face_to_database 儲存人臉資料部分 =====
    # 傳入 人臉名稱、人臉資訊(二進位)、圖片
    # ================================================ 
    def save_face_to_db(self, name, face_blob, image_path=None):
        conn = sqlite3.connect(self.db_path)  # 連接SQLite
        cursor = conn.cursor()  # 建立游標物件，用來執行 SQL 指令（查詢、插入、更新等）

        # 取得目前的日期和時間，並格式化成字串，記錄資料建立的時間
        created_date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")

        # SQL 指令，意思是「新增一筆資料到 faces 表格」。
        # ? 是參數佔位符，防止 SQL injection（安全性）。
        # 插入的資料，分別是人名、序列化後的人臉影像、圖片路徑、建立時間。
        cursor.execute('''
                INSERT INTO faces (name, face_encoding, image_path, created_date)
                VALUES (?, ?, ?, ?)
            ''', (name, face_blob, image_path, created_date))

        face_id = cursor.lastrowid  # 取得剛剛插入資料的「自動遞增主鍵」ID (唯一編號)
        conn.commit()  # 提交變更，確保資料儲存到資料庫
        conn.close()  # 關閉連接，避免記憶體洩漏或效能問題

        # ----- 顯示成功訊息 -----
        print(f"成功將 {name} 的人臉資料加入資料庫 (ID: {face_id}) by database")
    
    # ===== 辨識紀錄儲存 ======
    # 傳入 事件類型、事件訊息、人臉id(選填)、信心度(選填)
    # 回傳 無 
    # =========================================== 
    def save_recognition_log(self, event_type, event_message, face_id=None, confidence=None):
        try:
            conn = sqlite3.connect(self.db_path) # 連結資料庫
            cursor = conn.cursor()               # 建立 SQL 游標

            # 記錄事件發生時間
            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # SQL 指令，寫入事件類型、事件訊息、人臉ID、信心度
            cursor.execute('''
                INSERT INTO recognition_log (created_date, event_type, event_message, face_id, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (created_date, event_type, event_message, face_id, confidence))
            
            conn.commit() # 提交變更、確保資料真的儲存到資料庫。
            print(f"事件紀錄已儲存: {event_type} - {event_message} by database") # 成功訊息
        
        # 例外錯誤處理
        except Exception as e:
            print(f"儲存事件紀錄失敗 by database: {e}")
            raise   # 重新拋出相同的例外，讓上層程式碼也能處理
        
        # 無論如何都會執行的程式碼
        finally:
            if 'conn' in locals(): # 檢查 conn 是否存在
                conn.close() # 關閉資料庫

    # ===== 透過id從資料庫查詢人名 =====
    # 傳入 人臉 id
    # 傳出 人臉資料
    # =========================== 
    def search_face(self, face_id):
        conn = sqlite3.connect(self.db_path) # 連接資料庫
        cursor = conn.cursor() # 建立游標物件執行 SQL 指令
        cursor.execute("SELECT name FROM faces WHERE id = ?", (face_id,))# SQL 查詢，跟據 ID 查詢人名
        result = cursor.fetchone() # 只取出一筆資料，有資料就會是 (name,)，否則是 None
        return result
    

