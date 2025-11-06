import sqlite3
import hashlib
from datetime import datetime

# ===== 資料庫存取類別 =====
class DatabaseManager:
    # ===== 初始化資料庫觸發函式 =====
    def __init__(self, db_path='face_database/face_database.db'):
        self.db_path = db_path # 設定路徑
        self.init_database()
    
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
        # face_id: 參照faces表格id
        # recognition_date: 辨識發生日期時間
        # confidence: 信心度，REAL => 小數點 
        # 補充:
        # IF NOT EXISTS: 只有在表格不存在時才建立，避免重複建立錯誤
        # 資料關聯性: 透過外鍵建立兩個表格間的關聯，確保資料完整性
        # FOREIGN KEY: 建立與 faces 表格的關聯性
        # REFERENCES faces (id): 參照表格欄位  
        # -------------------------------------------- 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recognition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id INTEGER,
                recognition_date TEXT,
                confidence REAL,
                FOREIGN KEY (face_id) REFERENCES faces (id)
            )
        ''')

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
        # -----------------------------
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_message (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    visitor_image_path TEXT NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    booking_code TEXT
                )    
        ''')

        conn.commit() # 確認變更(寫入磁碟)
        conn.close() # 關閉連接
        print("資料庫初始化完成 by database")
    
    # ===== 註冊使用者 =====
    # 回傳 執行結果, 訊息
    # =====================  
    def register_user(self, username, password, role='住戶'):
        try:
            conn = sqlite3.connect(self.db_path) # 連接資料庫
            cursor = conn.cursor() # 建立游標執行 SQL 指令

            # 檢查使用者是否已存在
            cursor.execute("SELECT id FROM users WHERE username= ?", (username,))
            # 檢查第一筆資料，如果重複則結束函式並告訴使用者「此名稱已存在」
            if cursor.fetchone():
                conn.close() # 關閉資料庫連接
                return False, "使用者名稱已被使用 by database"
            
            # 驗證 role
            if role not in ('住戶', '管理員'):
                conn.close()
                return False, "不支援的身分 by database"
            
            # 密碼加密
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # 插入新使用者（包含 role）
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                           (username, password_hash, role)
                           )
            
            conn.commit() # 更新資料庫
            conn.close() # 關閉連接

            return True, "註冊成功 by database"

        # 例外錯誤處理
        except Exception as e:
            return False, f"註冊失敗 by database: {str(e)}"
    
    # ===== 使用者登入 =====
    # 回傳 執行結果
    # =====================  
    def login_user(self, username, password):
        try:
            conn = sqlite3.connect(self.db_path) # 連接資料庫
            cursor = conn.cursor() # 建立游標執行 SQL 指令

            # 把使用者輸入的密碼加密
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # 查詢使用者與密碼
            cursor.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?",
                           (username, password_hash)
                           )
            
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]  # 回傳 role
            else:
                return None

        # 例外錯誤處理
        except Exception as e:
            return None
    
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
            
            # 查詢辨識紀錄，並與人臉表格做關聯以取得人名(人臉id => 人臉資料庫 => 查詢人名)
            cursor.execute('''
                SELECT rl.id, f.name, rl.recognition_date, rl.confidence
                FROM recognition_log rl
                LEFT JOIN faces f ON rl.face_id = f.id
                ORDER BY rl.recognition_date DESC
            ''')
            
            # 資料轉換為字典格式
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'name': row[1],
                    'recognition_date': row[2],
                    'confidence': row[3]
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
    
    # ===== recognize_face 辨識紀錄儲存部分 ======
    # 傳入 人臉id、信心度
    # 回傳 無 
    # =========================================== 
    def save_recognition_log(self, face_id, confidence):
        try:
            conn = sqlite3.connect(self.db_path) # 連結資料庫
            cursor = conn.cursor()               # 建立 SQL 游標

            # 記錄辨識發生時間
            recognition_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 取得目前的日期和時間，並格式化成字串
            
            # SQL 指令，寫入人臉ID、辨識時間、信心度
            cursor.execute('''
                INSERT INTO recognition_log (face_id, recognition_date, confidence)
                VALUES (?, ?, ?)
            ''', (face_id, recognition_date, confidence))
            
            conn.commit() # 提交變更、確保資料真的儲存到資料庫。
            # print("辨識紀錄已儲存 by database") # 成功訊息
        
        # 例外錯誤處理
        except Exception as e:
            print(f"儲存辨識紀錄失敗 by database: {e}")
            raise   # 重新拋出相同的例外，讓上層程式碼也能處理
        
        # 無論如何都會執行的程式碼
        finally:
            if 'conn' in locals(): # 檢查 conn 是否存在
                conn.close() # 關閉資料庫

    # ===== 透過id從資料庫查詢人名 =====
    # 傳入 
    # 傳出 人臉資料
    # =========================== 
    def search_face(self, face_id):
        conn = sqlite3.connect(self.db_path) # 連接資料庫
        cursor = conn.cursor() # 建立游標物件執行 SQL 指令
        cursor.execute("SELECT name FROM faces WHERE id = ?", (face_id,))# SQL 查詢，跟據 ID 查詢人名
        result = cursor.fetchone() # 只取出一筆資料，有資料就會是 (name,)，否則是 None
        return result
    

    # ===== 訓練模型-取得訓練資料 =====
    # 傳入 無
    # 回傳 人臉id、人臉二進位資訊
    # =======================
    def train_model_faces(self):
        '''
            訓練模型真正需要的只有「特徵向量」(face_encoding) 和對應的「類別標籤」(id)
            其他的欄位不影響結果，如果要知道是哪一個人可以透過id查詢
        '''
        # ------ 連接資料庫取得人臉資料 ----- 
        conn = sqlite3.connect(self.db_path) # 連接 SQLite
        cursor = conn.cursor() # 建立游標物件來執行 SQL 指令
        cursor.execute("SELECT id, face_encoding FROM faces") # 資料查詢(所有人臉資料)
        data = cursor.fetchall() # 取得查詢結果
        conn.close() # 關閉資料庫連接
        return data
    
    # ===== 建立訪客預約 =====
    # 輸入 使用者名稱、驗證碼
    # 回傳 執行結果(T,F) 訊息
    # =====================  
    def create_visitor_booking(self, username, booking_code):
        try:
            # ---連接資料庫--
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # ---檢查預約碼是否已存在---
            # 查詢符合指定驗證碼的欄位，只回傳id編號
            cursor.execute("SELECT id FROM visitor_bookings WHERE booking_code = ?", (booking_code,))
            if cursor.fetchone(): # 取得第一筆資料看是否有值，找不到為None
                conn.close()
                return False, "預約碼已存在，請重新生成"
            
            # ---插入新預約---
            cursor.execute("INSERT INTO visitor_bookings (username, booking_code) VALUES (?, ?)",
                           (username, booking_code))
            
            conn.commit() # 更新資料庫
            conn.close()  # 關閉資料庫
            return True, "預約成功"
        # 
        except Exception as e:
            return False, f"預約失敗: {str(e)}"

    # ===== 驗證並使用訪客預約碼 =====
    # 回傳 執行結果, 住戶名稱
    # ==============================  
    def verify_visitor_booking(self, booking_code):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查詢未使用的預約碼
            cursor.execute("SELECT username FROM visitor_bookings WHERE booking_code = ? AND used = FALSE", 
                           (booking_code,))
            row = cursor.fetchone()
            
            if row:
                username = row[0]
                # 標記為已使用
                cursor.execute("UPDATE visitor_bookings SET used = TRUE, used_date = CURRENT_TIMESTAMP WHERE booking_code = ?",
                               (booking_code,))
                conn.commit()
                conn.close()
                return True, username
            else:
                conn.close()
                return False, "無效或已使用的預約碼"

        except Exception as e:
            return False, f"驗證失敗: {str(e)}"

    # ===== 儲存訪客留言 =====
    # 傳入 住戶名稱、訪客照片路徑、預約碼（選填）
    # 回傳 執行結果, 訊息
    # =====================  
    def save_visitor_message(self, username, visitor_image_path, booking_code=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 插入訪客留言資料
            cursor.execute("""
                INSERT INTO user_message (username, visitor_image_path, booking_code) 
                VALUES (?, ?, ?)
            """, (username, visitor_image_path, booking_code))
            
            message_id = cursor.lastrowid  # 取得新插入資料的ID
            
            conn.commit()
            conn.close()
            
            print(f"成功儲存訪客留言 (ID: {message_id}) for {username}")
            return True, f"訪客留言已儲存 (ID: {message_id})"

        except Exception as e:
            print(f"儲存訪客留言失敗: {str(e)}")
            return False, f"儲存失敗: {str(e)}"

    # ===== 取得所有訪客留言 =====
    # 回傳 字典格式資料列表
    # ===========================
    def get_all_visitor_messages(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查詢所有訪客留言，按時間倒序排列
            cursor.execute("""
                SELECT id, username, visitor_image_path, created_date, booking_code
                FROM user_message 
                ORDER BY created_date DESC
            """)
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'username': row[1],
                    'visitor_image_path': row[2],
                    'created_date': row[3],
                    'booking_code': row[4]
                })
            
            conn.close()
            return messages
            
        except Exception as e:
            print(f"查詢訪客留言失敗: {str(e)}")
            return []

    # ===== 取得特定使用者的訪客留言 =====
    # 傳入 使用者名稱
    # 回傳 字典格式資料列表
    # ===================================
    def get_user_visitor_messages(self, username):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查詢特定使用者的訪客留言，按時間倒序排列
            cursor.execute("""
                SELECT id, username, visitor_image_path, created_date, booking_code
                FROM user_message 
                WHERE username = ?
                ORDER BY created_date DESC
            """, (username,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'username': row[1],
                    'visitor_image_path': row[2],
                    'created_date': row[3],
                    'booking_code': row[4]
                })
            
            conn.close()
            return messages
            
        except Exception as e:
            print(f"查詢使用者訪客留言失敗: {str(e)}")
            return []
