import numpy as np 
import logging as log


""" ===== 這裡放人臉辨識的快取邏輯 ===== """

# ===== 人臉資料快取類別 =====
class FaceRecognitionCache:
    """人臉辨識快取，避免每幀都查詢資料庫"""
    def __init__(self):
        self.known_ids = []     # 人臉id
        self.known_names = []   # 名字
        self.known_encodings = [] # 特徵
        self.last_update = None # 上次更新資訊
    
    # ===== 從資料庫載入所有已知人臉資料到記憶體 =====
    def load_from_database(self, db_manager):
        try:
            conn, cursor = db_manager.get_db_connection()
            cursor.execute("SELECT id, name, encoding FROM face_recognition")
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.known_ids = []
                self.known_names = []
                self.known_encodings = []
                log.info("[快取] 資料庫中無人臉資料")
                return
            
            # 載入資料到記憶體
            self.known_ids = [row[0] for row in data]
            self.known_names = [row[1] for row in data]
            self.known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
            
            from datetime import datetime
            self.last_update = datetime.now()
            log.info(f"[快取] 成功載入 {len(self.known_ids)} 筆人臉資料")
            
        except Exception as e:
            log.error(f"[快取] 載入失敗: {e}")
            self.known_ids = []
            self.known_names = []
            self.known_encodings = []
        
    # ===== 檢查快取是否為空 =====
    def is_empty(self):
        return len(self.known_ids) == 0
    

# 建立全域快取實例
face_cache = FaceRecognitionCache()

# ===== 初始化快取（在應用啟動時呼叫）=====
def init_face_cache(db_manager):
    log.info("[快取] 正在初始化...")
    face_cache.load_from_database(db_manager)

# ===== 重新整理快取（新增人臉後呼叫）=====
def refresh_face_cache(db_manager):
    log.info("[快取] 正在重新整理...")
    face_cache.load_from_database(db_manager)