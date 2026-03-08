import sqlite3
from datetime import datetime
from .user import UserManager
from .config import DATABASE

# ===== 資料庫存取類別 =====
class DatabaseManager:
    # ===== 初始化資料庫觸發函式 =====
    def __init__(self, db_path=DATABASE):
        self.db_path = db_path # 設定路徑
        self.init_database()
        # 建立 user manager 以維持舊有 API 的轉發
        self.user_manager = UserManager(self.db_path)
    
    # ===== 建立資料庫連接與游標 =====
    # 回傳 連接物件和游標物件
    # ===============================
    def get_db_connection(self):
        """統一建立資料庫連接和游標"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        return conn, cursor
    
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
        print("資料庫初始化完成 by database")

    # ===== 列出資料庫中的所有辨識紀錄 =====
    # 回傳 字典格式資料
    # =================================== 
    def get_all_recognition_logs(self):
        try:
            conn, cursor = self.get_db_connection() # 使用統一的連接方法
            
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
    
    # ===== 辨識紀錄儲存 ======
    # 傳入 事件類型、事件訊息、人臉id(選填)、信心度(選填)
    # 回傳 無 
    # =========================================== 
    def save_recognition_log(self, event_type, event_message, face_id=None, confidence=None):
        try:
            conn, cursor = self.get_db_connection() # 使用統一的連接方法

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
        conn, cursor = self.get_db_connection() # 使用統一的連接方法
        cursor.execute("SELECT name FROM face_recognition WHERE id = ?", (face_id,))# SQL 查詢，跟據 ID 查詢人名
        result = cursor.fetchone() # 只取出一筆資料，有資料就會是 (name,)，否則是 None
        conn.close() # 關閉連接
        return result

    # ===== 儲存訪客預約記錄 =====
    def save_visitor_booking(self, username, visitor_face_name, visitor_face_id):
        """
        儲存訪客預約記錄
        
        參數:
            username: 住戶名稱
            visitor_face_name: 訪客人臉識別名稱 (如 visitor_20240101_123456)
            visitor_face_id: 關聯到 face_recognition 表格的 ID
        
        返回:
            tuple: (success, message)
        """
        try:
            conn, cursor = self.get_db_connection()
            
            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                INSERT INTO visitor_bookings 
                (username, visitor_face_name, visitor_face_id, created_date)
                VALUES (?, ?, ?, ?)
            ''', (username, visitor_face_name, visitor_face_id, created_date))
            
            conn.commit()
            conn.close()
            
            print(f"[資料庫] 成功儲存訪客預約: {username} -> {visitor_face_name}")
            return True, f'訪客預約成功，訪客可直接到門口進行人臉辨識'
        
        except Exception as e:
            print(f"[資料庫] 儲存訪客預約失敗: {e}")
            return False, f'儲存失敗: {str(e)}'

    # ===== 根據訪客人臉名稱查詢住戶名稱 =====
    def get_visitor_by_face_name(self, visitor_face_name):
        """
        根據訪客人臉名稱查詢對應的住戶名稱
        預約紀錄（visitor_bookings）會保留，只是標記為已使用（used = TRUE），
        這樣既能保留歷史紀錄，又能確保人臉資料不會被重複使用或濫用
        
        參數:
            visitor_face_name: 訪客人臉識別名稱 (如 visitor_20240101_123456)
        
        返回:
            str: 住戶名稱，若查詢不到則回傳 None
        """
        try:
            conn, cursor = self.get_db_connection()
            
            cursor.execute('''
                SELECT username FROM visitor_bookings 
                WHERE visitor_face_name = ? AND used = FALSE
            ''', (visitor_face_name,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]  # 回傳住戶名稱
            return None
        
        except Exception as e:
            print(f"[資料庫] 查詢訪客住戶失敗: {e}")
            return None

    # ===== 清除訪客人臉資料 =====
    def clear_visitor_face_data(self, visitor_face_name):
        """
        清除訪客的人臉資料（完全刪除，不保留記錄）
        訪客的人臉資料屬於一次性用途，當辨識完成、通行後，為了保護住戶與訪客的隱私
        
        參數:
            visitor_face_name: 訪客人臉識別名稱
        
        返回:
            bool: 是否成功清除
        """
        try:
            conn, cursor = self.get_db_connection()
            
            # 1. 從 face_recognition 表格刪除人臉資料
            cursor.execute('DELETE FROM face_recognition WHERE name = ?', (visitor_face_name,))
            
            # 2. 更新 visitor_bookings 表格，標記為已使用
            used_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                UPDATE visitor_bookings 
                SET used = TRUE, used_date = ?
                WHERE visitor_face_name = ?
            ''', (used_date, visitor_face_name))
            
            conn.commit()
            conn.close()
            
            print(f"[資料庫] 成功清除訪客人臉資料: {visitor_face_name}")
            return True
        
        except Exception as e:
            print(f"[資料庫] 清除訪客人臉資料失敗: {e}")
            return False
    
    # ===== 取得可用的櫃號（返回最小的空閒櫃號） =====
    def get_available_locker(self):
        conn, cursor = self.get_db_connection()
        try:
            cursor.execute("""
                SELECT locker_number FROM package_lockers 
                WHERE is_occupied = 0 
                ORDER BY locker_number ASC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    # ====== 自動分配櫃號並登記包裹 ======
    def register_package(self, recipient_name):
        conn, cursor = self.get_db_connection()
        try:
            # 取得可用櫃號
            locker_number = self.get_available_locker()
            
            # 檢查是否櫃位已滿
            if locker_number is None:
                return False, None, "所有櫃位已滿，請稍後再試"
            
            # 登記包裹(紀錄時間)
            registered_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新此櫃號(locker_number)的收件人、登記時間、佔用狀態
            cursor.execute("""
                UPDATE package_lockers 
                SET recipient_name = ?, registered_date = ?, is_occupied = 1 
                WHERE locker_number = ?
            """, (recipient_name, registered_date, locker_number))
            conn.commit() # 更新資料庫

            print(f"[資料庫] 包裹已登記至 {locker_number} 號櫃，收件人：{recipient_name}")
            return True, locker_number, f"包裹已登記至 {locker_number} 號櫃"
        
        except Exception as e:
            print(f"[資料庫] 登記包裹失敗: {e}")
            conn.rollback()
            return False, None, f"登記失敗: {str(e)}"
        finally:
            conn.close()
    
    # ===== 根據住戶名稱查詢櫃號 =====
    def get_locker_by_name(self, name):
        conn, cursor = self.get_db_connection()
        try:
            # 根據名字查詢，且確保是占用狀態
            cursor.execute("""
                SELECT locker_number FROM package_lockers 
                WHERE recipient_name = ? AND is_occupied = 1
            """, (name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    # ===== 清除櫃位資訊 ======
    def clear_locker(self, locker_number):
        conn, cursor = self.get_db_connection()
        try:
            # 
            cursor.execute("""
                UPDATE package_lockers 
                SET recipient_name = NULL, registered_date = NULL, is_occupied = 0 
                WHERE locker_number = ?
            """, (locker_number,))
            conn.commit()

            print(f"[資料庫] {locker_number} 號櫃已清除")
            return True, "櫃位已清除"
        except Exception as e:
            print(f"[資料庫] 清除櫃位失敗: {e}")
            conn.rollback()
            return False, f"清除失敗: {str(e)}"
        finally:
            conn.close()
    
    def get_all_lockers_status(self):
        """取得所有櫃位狀態"""
        conn, cursor = self.get_db_connection()
        try:
            cursor.execute("""
                SELECT locker_number, recipient_name, registered_date, is_occupied 
                FROM package_lockers 
                ORDER BY locker_number ASC
            """)
            rows = cursor.fetchall()
            
            lockers = []
            for row in rows:
                lockers.append({
                    'locker_number': row[0],
                    'recipient_name': row[1],
                    'registered_date': row[2],
                    'is_occupied': bool(row[3])
                })
            return lockers
        finally:
            conn.close()


