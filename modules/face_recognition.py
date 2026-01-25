# ===== face_recognition 人臉辨識 =====
import os
import sqlite3
import numpy as np
import face_recognition
import json
from PIL import Image
import cv2  
from .config import FACE_RECOGNITION_TOLERANCE, FACE_RECOGNITION_RESIZE_WIDTH, FACE_RECOGNITION_MODEL # 引入信心度參數和縮放寬度

# ===== 人臉資料快取類別 =====
class FaceRecognitionCache:
    """人臉辨識快取，避免每幀都查詢資料庫"""
    
    def __init__(self):
        self.known_ids = []
        self.known_names = []
        self.known_encodings = []
        self.last_update = None
    
    def load_from_database(self, db_manager):
        """從資料庫載入所有已知人臉資料到記憶體"""
        try:
            conn, cursor = db_manager.get_db_connection()
            cursor.execute("SELECT id, name, encoding FROM face_recognition")
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.known_ids = []
                self.known_names = []
                self.known_encodings = []
                print("[快取] 資料庫中無人臉資料")
                return
            
            # 載入資料到記憶體
            self.known_ids = [row[0] for row in data]
            self.known_names = [row[1] for row in data]
            self.known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
            
            from datetime import datetime
            self.last_update = datetime.now()
            print(f"[快取] 成功載入 {len(self.known_ids)} 筆人臉資料")
            
        except Exception as e:
            print(f"[快取] 載入失敗: {e}")
            self.known_ids = []
            self.known_names = []
            self.known_encodings = []
    
    def is_empty(self):
        """檢查快取是否為空"""
        return len(self.known_ids) == 0
    
    def refresh(self, db_manager):
        """重新整理快取"""
        print("[快取] 正在重新整理...")
        self.load_from_database(db_manager)

# 建立全域快取實例
_face_cache = FaceRecognitionCache()

# ===== 初始化快取 =====
def init_face_cache(db_manager):
    """初始化人臉快取（在應用啟動時呼叫）"""
    _face_cache.load_from_database(db_manager)

# ===== 重新整理快取 =====
def refresh_face_cache(db_manager):
    """重新整理人臉快取（新增人臉後呼叫）"""
    _face_cache.refresh(db_manager)

# ===== 圖片轉RGB三通道 =====
def changeRGB(input_data):
    """
    將圖片轉換為 RGB 格式並確保記憶體連續
    
    參數:
        input_data: 可以是圖片路徑(str) 或 numpy array (OpenCV frame)
    
    返回:
        numpy array: RGB 格式的圖片，記憶體連續
    """
    try:
        # 判斷輸入類型
        if isinstance(input_data, str):
            # 輸入是檔案路徑
            # 1. 使用 PIL 打開圖片
            pil_image = Image.open(input_data).convert('RGB')
            
            # 2. 限制圖片大小 (如果寬度超過 1000 像素就縮小，減少 dlib 負擔)
            max_width = 1000
            if pil_image.width > max_width:
                ratio = max_width / float(pil_image.width)
                new_height = int(float(pil_image.height) * ratio)
                pil_image = pil_image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 3. 轉回 numpy array
            image = np.array(pil_image)
            
        elif isinstance(input_data, np.ndarray):
            # 輸入是 numpy array (OpenCV frame, BGR 格式)
            # 轉換 BGR -> RGB
            image = cv2.cvtColor(input_data, cv2.COLOR_BGR2RGB)
            
        else:
            raise ValueError(f"不支援的輸入類型: {type(input_data)}")
        
        # 4. 【關鍵】確保數據類型為 uint8 且記憶體是連續的
        image = np.ascontiguousarray(image, dtype=np.uint8)
        
        return image
        
    except Exception as e:
        print(f"[changeRGB] [錯誤] changeRGB 失敗: {e}")
        return None

# ===== 獲取資料夾內的圖片檔案 =====
def getFiles(folder_path):
    # 掃描資料夾內的('.jpg', '.png', '.jpeg')圖片
    files = [] # 資料夾內的檔案名稱列表
    for f in os.listdir(folder_path):
        # 轉成小寫，檢查副檔名
        if f.lower().endswith(('.jpg', '.png', '.jpeg')):
            files.append(f)
    return files

# ===== 註冊人臉到資料庫 =====
# 輸入 資料庫連結物件、名稱、資料夾路徑、檔案名稱列表 
def register_faces(conn, name, folder_path, files):
    cursor = conn.cursor() # SQL 游標
    count = 0 # 特徵數據總數
    # 批次處理檔案
    for f in files:
        # 組合成完整的檔案路徑
        img_path = os.path.join(folder_path, f) 
        
        # 加載圖片+轉RGB三通道
        #image = face_recognition.load_image_file(img_path)
        print("加載圖片+轉RGB三通道...")
        image = changeRGB(img_path)        

        # 提取特徵向量 (列表)
        # print("提取特徵向量...")
        # encodings = face_recognition.face_encodings(image)
        print("  [步驟] 手動定位人臉位置...")
        # 1. 先用 face_locations 找出臉部位置 (這步如果報錯，代表 dlib 核心損毀)
        face_locations = face_recognition.face_locations(image)
        print(f"  [步驟] 提取特徵向量 (偵測到 {len(face_locations)} 張臉)...")
        # 2. 傳入臉部位置進行編碼
        encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)
        
        # 如果有特徵向量(有偵測到人臉)
        print("有偵測到人臉")
        if len(encodings) > 0:
            # 將 numpy array 轉成 list 再轉成 json 字串存入
            encoding_str = json.dumps(encodings[0].tolist())
            # 將名稱、特徵向量加入資料庫，成為該人名的特徵資料(此方法不用訓練模型，是直接將特徵存入資料庫)
            cursor.execute("INSERT INTO users (name, encoding) VALUES (?, ?)", (name, encoding_str))
            count += 1 # 計數
        else:
            print(f"[警告] 圖片 {f} 未偵測到人臉，跳過。")
    
    conn.commit() # 更新資料庫
    print(f"[系統] 成功為 {name} 註冊了 {count} 筆特徵數據。")

# ===== 辨識邏輯 =====
# 輸入 資料庫連結物件、測試圖片路徑
def recognize_face(conn, test_img_path):
    # 從資料庫讀取所有已知資料
    cursor = conn.cursor() # SQL 游標
    # 選取 name（姓名）和 encoding（人臉特徵向量）這兩個欄位的所有資料
    cursor.execute("SELECT name, encoding FROM face_recognition")
    data = cursor.fetchall() # 取出資料
    
    # 如果沒有任何以註冊人臉，則結束程式
    if not data:
        print("[系統] 資料庫內無任何已知人臉，請先註冊。")
        return

    # 取出所有名稱、特徵向量(轉成 numpy 陣列)，用於後續比對
    known_names = [row[0] for row in data]
    known_encodings = [np.array(json.loads(row[1])) for row in data]

    # 處理測試圖片，檢查是否有圖片
    if not os.path.exists(test_img_path):
        print("[錯誤] 找不到測試圖片路徑。")
        return

    # 加載圖片+轉RGB三通道
    #image = face_recognition.load_image_file(img_path)
    test_image = changeRGB(test_img_path)  
    # 提取特徵向量 (列表)
    test_encodings = face_recognition.face_encodings(test_image)

    # 如果測試圖片未取到特徵向量，則結束函式
    if len(test_encodings) == 0:
        print("[結果] 測試圖片中未偵測到人臉。")
        return

    # 比對圖中偵測到的每一張臉(考慮多人照的情況)
    for unknown_encoding in test_encodings:
        # tolerance=0.4 較嚴格，0.6 是預設值
        results = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=0.5)
        
        # 如果有比對到相似的人臉(results 列表裡有 Ture)
        if True in results:
            # 找出距離最近的那一個
            face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
            # 找出最有可能是同一個人的那筆資料的索引值
            best_match_index = np.argmin(face_distances)
            # 確認該索引有資料
            if results[best_match_index]:
                name = known_names[best_match_index] # 取用名稱列表裡同樣位置的資料
                print(f"[結果] 辨識成功！此人是: {name} (信心距離: {face_distances[best_match_index]:.4f})")
        else:
            print("[結果] 未知人士")

# ===== 針對即時影像幀進行人臉辨識 =====
def recognize_face_from_frame(db_manager, frame):
    """
    針對即時影像幀進行人臉辨識
    
    參數:
        db_manager: DatabaseManager 物件
        frame: OpenCV 的影像幀 (numpy array, BGR 格式)
    
    返回:
        list: 辨識結果列表，每個元素包含 {'name': 姓名, 'id': 資料庫ID, 'confidence': 信心值}
    """
    
    # 使用 DatabaseManager 取得連接
    conn, cursor = db_manager.get_db_connection()
    cursor.execute("SELECT id, name, encoding FROM face_recognition")
    data = cursor.fetchall()
    conn.close()
    # 檢查有沒有資料
    if not data:
        return []
    
    # 準備已知人臉資料
    known_ids = [row[0] for row in data]
    known_names = [row[1] for row in data]
    known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
    #known_encodings = [np.array(json.loads(row[2])) for row in data]
    
    # 使用 changeRGB 處理 frame (BGR -> RGB)
    rgb_frame = changeRGB(frame)
    # 檢查有沒有轉換成功
    if rgb_frame is None:
        return []
    
    # 偵測人臉位置
    face_locations = face_recognition.face_locations(rgb_frame)
    # 檢查有沒有偵測到人臉
    if len(face_locations) == 0:
        return []
    
    # 提取特徵向量
    face_encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
    
    # 辨識結果列表
    results = []
    
    # 批次處理特徵向量
    for i, face_encoding in enumerate(face_encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_RECOGNITION_TOLERANCE)
        # 處理臉部座標資訊
        position = face_locations[i]  # (top, right, bottom, left)
        # 轉成 (x, y, w, h)
        top, right, bottom, left = position
        x, y, w, h = left, top, right - left, bottom - top

        if True in matches:
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                results.append({
                    'id': known_ids[best_match_index],
                    'name': known_names[best_match_index],
                    'confidence': 1 - face_distances[best_match_index],  # 轉換為相似度
                    'position': (x, y, w, h)
                })
            else:
                results.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
        else:
            results.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
    
    return results

# ===== 針對即時影像幀進行人臉辨識（優化版）=====
def recognize_face_from_frame(db_manager, frame, use_cache=True, resize_width=FACE_RECOGNITION_RESIZE_WIDTH, model=FACE_RECOGNITION_MODEL):
    """
    針對即時影像幀進行人臉辨識（優化版）
    
    參數:
        db_manager: DatabaseManager 物件
        frame: OpenCV 的影像幀 (numpy array, BGR 格式)
        use_cache: 是否使用快取（預設 True）
        resize_width: 辨識用影像寬度（預設從 config 讀取）
        model: 人臉偵測模型 'hog'(快) 或 'cnn'(準)（預設從 config 讀取）
    
    返回:
        list: 辨識結果列表，每個元素包含 {'name': 姓名, 'id': 資料庫ID, 'confidence': 信心值, 'position': 座標}
    """
    
    # === 1. 取得已知人臉資料（使用快取或即時查詢）===
    if use_cache:
        # 如果快取是空的，先載入
        if _face_cache.is_empty():
            _face_cache.load_from_database(db_manager)
        
        known_ids = _face_cache.known_ids
        known_names = _face_cache.known_names
        known_encodings = _face_cache.known_encodings
    else:
        # 即時查詢資料庫（原始方法）
        conn, cursor = db_manager.get_db_connection()
        cursor.execute("SELECT id, name, encoding FROM face_recognition")
        data = cursor.fetchall()
        conn.close()
        
        if not data:
            return []
        
        known_ids = [row[0] for row in data]
        known_names = [row[1] for row in data]
        known_encodings = [np.frombuffer(row[2], dtype=np.float64) for row in data]
    
    # 檢查有沒有資料
    if len(known_ids) == 0:
        return []
    
    # === 2. 影像預處理：降低解析度 ===
    original_height, original_width = frame.shape[:2]
    
    # 計算縮放比例
    if original_width > resize_width:
        scale = resize_width / original_width
        new_width = resize_width
        new_height = int(original_height * scale)
        small_frame = cv2.resize(frame, (new_width, new_height))
    else:
        scale = 1.0
        small_frame = frame
    
    # === 3. 使用 changeRGB 處理 frame (BGR -> RGB) ===
    rgb_frame = changeRGB(small_frame)
    if rgb_frame is None:
        return []
    
    # === 4. 偵測人臉位置（使用指定模型）===
    face_locations = face_recognition.face_locations(rgb_frame, model=model)
    if len(face_locations) == 0:
        return []
    
    # === 5. 提取特徵向量 ===
    face_encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=face_locations)
    
    # === 6. 辨識結果列表 ===
    results = []
    
    # 批次處理特徵向量
    for i, face_encoding in enumerate(face_encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_RECOGNITION_TOLERANCE)
        
        # 處理臉部座標資訊（映射回原始尺寸）
        position = face_locations[i]  # (top, right, bottom, left)
        top, right, bottom, left = position
        
        # 將座標映射回原始影像尺寸
        if scale != 1.0:
            top = int(top / scale)
            right = int(right / scale)
            bottom = int(bottom / scale)
            left = int(left / scale)
        
        # 轉成 (x, y, w, h)
        x, y, w, h = left, top, right - left, bottom - top

        if True in matches:
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            
            if matches[best_match_index]:
                results.append({
                    'id': known_ids[best_match_index],
                    'name': known_names[best_match_index],
                    'confidence': 1 - face_distances[best_match_index],
                    'position': (x, y, w, h)
                })
            else:
                results.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
        else:
            results.append({'id': None, 'name': '未知', 'confidence': 0.0, 'position': (x, y, w, h)})
    
    return results
