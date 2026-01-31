# ===== face_recognition 人臉辨識 =====
import os
import numpy as np
import face_recognition
from PIL import Image
import cv2  
from .config import FACE_RECOGNITION_TOLERANCE, FACE_RECOGNITION_RESIZE_WIDTH, FACE_RECOGNITION_MODEL

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

# ===== 初始化快取（全域函式）=====
def init_face_cache(db_manager):
    """初始化人臉快取（在應用啟動時呼叫）"""
    _face_cache.load_from_database(db_manager)

# ===== 重新整理快取（全域函式）=====
def refresh_face_cache(db_manager):
    """重新整理人臉快取（新增人臉後呼叫）"""
    _face_cache.refresh(db_manager)

# ===== 人臉註冊&辨識類別 =====
class FaceRecognition:

    # ===== 圖片轉RGB三通道（私有方法）=====
    def _changeRGB(self, input_data):
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
                pil_image = Image.open(input_data).convert('RGB')
                
                # 限制圖片大小
                max_width = 1000
                if pil_image.width > max_width:
                    ratio = max_width / float(pil_image.width)
                    new_height = int(float(pil_image.height) * ratio)
                    pil_image = pil_image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                image = np.array(pil_image)
                
            elif isinstance(input_data, np.ndarray):
                # 輸入是 numpy array (OpenCV frame, BGR 格式)
                image = cv2.cvtColor(input_data, cv2.COLOR_BGR2RGB)
                
            else:
                raise ValueError(f"不支援的輸入類型: {type(input_data)}")
            
            # 確保數據類型為 uint8 且記憶體是連續的
            image = np.ascontiguousarray(image, dtype=np.uint8)
            
            return image
            
        except Exception as e:
            print(f"[changeRGB] [錯誤] changeRGB 失敗: {e}")
            return None

    # ===== 獲取資料夾內的圖片檔案（私有方法）=====
    def _getFiles(self, folder_path):
        """掃描資料夾內的圖片檔案"""
        files = []
        for f in os.listdir(folder_path):
            if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                files.append(f)
        return files

    # ===== 註冊人臉到資料庫 =====
    def register_faces(self, db_manager, name, folder_path, files):
        """
        註冊人臉到資料庫
        
        參數:
            db_manager: DatabaseManager 物件
            name: 人名
            folder_path: 圖片資料夾路徑
            files: 檔案名稱列表
        
        返回:
            dict: {'success': bool, 'message': str, 'count': int}
        """
        try:
            conn, cursor = db_manager.get_db_connection()
            count = 0
            
            for f in files:
                img_path = os.path.join(folder_path, f)
                
                # 加載圖片+轉RGB三通道
                print(f"[註冊] 處理圖片: {f}")
                image = self._changeRGB(img_path)
                
                if image is None:
                    print(f"[警告] 圖片 {f} 載入失敗，跳過。")
                    continue
                
                # 提取特徵向量
                print("  [步驟] 手動定位人臉位置...")
                face_locations = face_recognition.face_locations(image)
                print(f"  [步驟] 提取特徵向量 (偵測到 {len(face_locations)} 張臉)...")
                encodings = face_recognition.face_encodings(image, known_face_locations=face_locations)
                
                # 如果有特徵向量
                if len(encodings) > 0:
                    # 將 numpy array 轉成二進位 BLOB
                    encoding_blob = encodings[0].tobytes()
                    # 插入到 face_recognition 表格
                    cursor.execute("INSERT INTO face_recognition (name, encoding) VALUES (?, ?)", 
                                 (name, encoding_blob))
                    count += 1
                else:
                    print(f"[警告] 圖片 {f} 未偵測到人臉，跳過。")
            
            conn.commit()
            conn.close()
            
            if count > 0:
                print(f"[系統] 成功為 {name} 註冊了 {count} 筆特徵數據。")
                return {'success': True, 'message': f'成功註冊 {count} 筆人臉資料', 'count': count}
            else:
                return {'success': False, 'message': '所有圖片都未偵測到人臉', 'count': 0}
                
        except Exception as e:
            print(f"[錯誤] 註冊人臉失敗: {e}")
            return {'success': False, 'message': f'註冊失敗: {str(e)}', 'count': 0}

    # ===== 辨識邏輯 =====
    def recognize_face(self, db_manager, test_img_path):
        """
        辨識靜態圖片中的人臉
        
        參數:
            db_manager: DatabaseManager 物件
            test_img_path: 測試圖片路徑
        
        返回:
            dict: {'success': bool, 'message': str, 'results': list}
        """
        try:
            # 從資料庫讀取所有已知資料
            conn, cursor = db_manager.get_db_connection()
            cursor.execute("SELECT name, encoding FROM face_recognition")
            data = cursor.fetchall()
            conn.close()
            
            # 如果沒有任何已註冊人臉
            if not data:
                return {'success': False, 'message': '資料庫內無任何已知人臉，請先註冊'}
            
            # 取出所有名稱、特徵向量
            known_names = [row[0] for row in data]
            known_encodings = [np.frombuffer(row[1], dtype=np.float64) for row in data]
            
            # 處理測試圖片
            if not os.path.exists(test_img_path):
                return {'success': False, 'message': '找不到測試圖片路徑'}
            
            # 加載圖片+轉RGB三通道
            test_image = self._changeRGB(test_img_path)
            
            if test_image is None:
                return {'success': False, 'message': '測試圖片載入失敗'}
            
            # 提取特徵向量
            test_encodings = face_recognition.face_encodings(test_image)
            
            # 如果測試圖片未取到特徵向量
            if len(test_encodings) == 0:
                return {'success': False, 'message': '測試圖片中未偵測到人臉'}
            
            # 比對結果列表
            results = []
            
            # 比對圖中偵測到的每一張臉
            for unknown_encoding in test_encodings:
                matches = face_recognition.compare_faces(known_encodings, unknown_encoding, 
                                                        tolerance=FACE_RECOGNITION_TOLERANCE)
                
                # 如果有比對到相似的人臉
                if True in matches:
                    face_distances = face_recognition.face_distance(known_encodings, unknown_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        name = known_names[best_match_index]
                        confidence = 1 - face_distances[best_match_index]
                        results.append({
                            'name': name,
                            'confidence': f'{confidence:.2%}',
                            'distance': float(face_distances[best_match_index])
                        })
                        print(f"[結果] 辨識成功！此人是: {name} (信心距離: {face_distances[best_match_index]:.4f})")
                    else:
                        results.append({'name': '未知', 'confidence': 'N/A'})
                else:
                    results.append({'name': '未知', 'confidence': 'N/A'})
            
            return {'success': True, 'message': '辨識完成', 'results': results}
            
        except Exception as e:
            print(f"[錯誤] 辨識失敗: {e}")
            return {'success': False, 'message': f'辨識失敗: {str(e)}'}

    # ===== 針對即時影像幀進行人臉辨識（優化版）=====
    def recognize_face_from_frame(self, db_manager, frame, use_cache=True, resize_width=FACE_RECOGNITION_RESIZE_WIDTH, model=FACE_RECOGNITION_MODEL):
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
            # 即時查詢資料庫
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
        rgb_frame = self._changeRGB(small_frame)
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
            position = face_locations[i]
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

    # ===== 驗證上傳的照片是否能偵測到人臉 =====
    def validate_face_images(self, image_files):
        """
        驗證上傳的照片是否能偵測到人臉
        
        參數:
            image_files: dict，格式 {'front': file_obj, 'left': file_obj, 'right': file_obj}
        
        返回:
            dict: {'success': bool, 'message': str, 'failed_images': list}
        """
        try:
            failed_images = []
            
            for position, file_obj in image_files.items():
                # 讀取圖片
                image_data = np.frombuffer(file_obj.read(), np.uint8)
                image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                if image is None:
                    failed_images.append(position)
                    continue
                
                # 轉換為 RGB
                rgb_image = self._changeRGB(image)
                
                if rgb_image is None:
                    failed_images.append(position)
                    continue
                
                # 偵測人臉
                face_locations = face_recognition.face_locations(rgb_image)
                
                if len(face_locations) == 0:
                    failed_images.append(position)
            
            if len(failed_images) > 0:
                position_names = {
                    'front': '正面照',
                    'left': '左微側臉',
                    'right': '右微側臉'
                }
                failed_names = [position_names.get(pos, pos) for pos in failed_images]
                return {
                    'success': False,
                    'message': f'以下照片未偵測到人臉：{", ".join(failed_names)}',
                    'failed_images': failed_images
                }
            
            return {
                'success': True,
                'message': '所有照片驗證成功',
                'failed_images': []
            }
        
        except Exception as e:
            print(f"[驗證] 照片驗證失敗: {e}")
            return {
                'success': False,
                'message': f'驗證失敗: {str(e)}',
                'failed_images': []
            }

    # ===== 註冊訪客人臉（從上傳的檔案）=====
    def register_visitor_faces(self, db_manager, visitor_name, image_files):
        """
        註冊訪客人臉到資料庫（從上傳的檔案物件）
        
        參數:
            db_manager: DatabaseManager 物件
            visitor_name: 訪客識別名稱 (如 visitor_20240101_123456)
            image_files: dict，格式 {'front': file_obj, 'left': file_obj, 'right': file_obj}
        
        返回:
            dict: {'success': bool, 'message': str, 'visitor_face_id': int}
        """
        try:
            conn, cursor = db_manager.get_db_connection()
            count = 0
            first_face_id = None
            
            for position, file_obj in image_files.items():
                # 讀取圖片
                file_obj.seek(0)  # 重置檔案指標
                image_data = np.frombuffer(file_obj.read(), np.uint8)
                image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                
                # 轉換為 RGB
                rgb_image = self._changeRGB(image)
                
                if rgb_image is None:
                    continue
                
                # 提取特徵向量
                face_locations = face_recognition.face_locations(rgb_image)
                encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
                
                if len(encodings) > 0:
                    encoding_blob = encodings[0].tobytes()
                    cursor.execute("INSERT INTO face_recognition (name, encoding) VALUES (?, ?)", 
                                 (visitor_name, encoding_blob))
                    
                    if first_face_id is None:
                        first_face_id = cursor.lastrowid
                    
                    count += 1
            
            conn.commit()
            conn.close()
            
            if count > 0:
                print(f"[註冊] 成功為訪客 {visitor_name} 註冊了 {count} 筆特徵數據")
                return {
                    'success': True,
                    'message': f'成功註冊 {count} 筆訪客人臉資料',
                    'visitor_face_id': first_face_id
                }
            else:
                return {
                    'success': False,
                    'message': '所有照片都未能成功提取特徵',
                    'visitor_face_id': None
                }
        
        except Exception as e:
            print(f"[註冊] 註冊訪客人臉失敗: {e}")
            return {
                'success': False,
                'message': f'註冊失敗: {str(e)}',
                'visitor_face_id': None
            }
