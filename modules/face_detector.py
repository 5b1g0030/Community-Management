import cv2
import pickle
from modules.database import DatabaseManager
from modules.model import ModelManager

# ===== 影像處理類別 =====
class FaceDetector:
    # ===== 初始化 =====
    def __init__(self, model_path='face_database/face_model.pkl', db_path='face_database/face_database.db'):
        # 訓練模型路徑
        self.model_path = model_path

        # 資料庫路徑
        self.db_path = db_path

        # OpenCV 的 Haar cascade 人臉偵測模型檔案，用於偵測影像中的人臉位置
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # 從已訓練的人臉樣本學習特徵並對新人臉做預測（回傳 id 與「相似度/距離」分數）
        self.recognizer = cv2.face.LBPHFaceRecognizer_create() # 
        
        # 資料庫路徑
        self.db_manager = DatabaseManager(db_path)
        
        # 建立 ModelManager
        self.model_manager = ModelManager(self.recognizer, self.model_path, self.db_path, self.db_manager)
    
    # ===== 將影像轉灰階 =====
    # 傳入 影像
    # 輸出 灰階影像or空值
    # ======================= 
    def to_gray(self, image):
        # 是彩圖，典型的 BGR 彩色圖像形狀為 (H, W, 3)，image.ndim => n維列(灰色是2，彩色是3)
        if image.ndim == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # 把影像轉為灰階
            return image
        # 已經是灰階圖，直接輸出
        elif image.ndim == 2:
            return image
        else:
            return None

    # ===== 載入圖片 =====
    def load_image(self, image):
        # 檢查是否有圖片
        if image is None:
            return None
        # 如果傳入的是檔案路徑字串（不確定情況），嘗試讀檔
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                return None
        
        return image

    # ===== 偵測圖像中的人臉 =====
    # 傳入 圖片
    # 回傳 人臉座標、灰階影像
    # ===========================   
    def detect_faces(self, image):
        # ...existing detect_faces code...
        '''
            1. 影像轉灰階
            2. 取得所有人臉的座標（x, y, w, h）
            3. 回傳出結果(包含灰階影像、人臉座標)
            補充: 
            (gray, 1.3, 5) => (灰階影像, 影像尺寸縮小比例, 判定為人臉的分數)
            影像尺寸縮小比例 => 每次影像縮小到原本的 1/1.3，有些人臉可能比較大或比較小，
            偵測器會在不同尺寸的影像中都嘗試偵測，增加找到人臉的機會。
        '''
        # ----- 載入圖片 -----
        image = self.load_image(image)
        # 如果未載入成功，則回傳空值
        if image is None:
            print("image 為空 by face_detector")
            return (), None

        # ----- 影像轉灰階 -----
        gray = self.to_gray(image)
        # 如果轉換不成功，則輸出空值
        if gray is None:
            print("gray 為空 by face_detector")
            return (), None

        # 保證 dtype 為 uint8
        if gray.dtype != 'uint8':
            gray = (gray.astype('float32')).astype('uint8')

        h, w = gray.shape[:2]
        if h == 0 or w == 0:
            return (), gray

        # 呼叫偵測時加上保護與較保守參數
        try:
            faces = self.face_cascade.detectMultiScale(
                gray,   # 輸入的灰階影像
                scaleFactor=1.1, # 每次縮放影像的比例: 從臉占比大的圖片找起，慢慢到小的
                minNeighbors=5,  # 偵測過程中會產生很多候選框，至少 5 個框都指向同一區域
                minSize=(30, 30) # 比這標準小的人臉一律忽略(30px*30px)
            )
        except cv2.error as e:
            print(f"detectMultiScale 發生錯誤: {e}")
            return (), gray

        return faces, gray
    
    # ===== 裁切&縮小影像 =====
    # 傳入 灰階影像、人臉座標
    # 輸出 已縮小的影像
    # ======================== 
    def crop_and_resize(self, gray, bbox, size=(100,100)):
        x, y, w, h = bbox
        face_roi = gray[y:y+h, x:x+w]
        return cv2.resize(face_roi, size)

    # ===== 將人臉加入資料庫 =====
    # 傳入 圖片、名稱、圖片路徑
    # 回傳 成功與否
    # ===========================
    def add_face_to_database(self, image, name, image_path=None):
        try:
            faces, gray = self.detect_faces(image)
            
            if len(faces) == 0:
                print("未偵測到人臉")
                return False
            
            (x, y, w, h) = faces[0]
            # face_roi = gray[y:y+h, x:x+w]
            # face_resized = cv2.resize(face_roi, (100, 100))
            face_resized = self.crop_and_resize(gray, (x,y,w,h))
            face_blob = pickle.dumps(face_resized)
            
            self.db_manager.save_face_to_db(name, face_blob, image_path) # 儲存人臉到資料庫
            self.model_manager.train_model() # 訓練模型
            return True
        
        except Exception as e:
            print(f'加入人臉資料失敗: {str(e)}')
            raise e
    
    # ===== 辨識人臉 =====
    # 輸入 圖片
    # 輸出 人名、信心度、座標 OR 空列表
    # ====================  
    def recognize_face(self, image):
        faces, gray = self.detect_faces(image) # 取得黑白影像
        results = [] # 儲存人臉資訊

        # 如果沒偵測到人臉就直接回傳空列表，避免呼叫 recognizer.predict
        if len(faces) == 0:
            return []

        # 對 detect_faces 回傳的每個人臉 bbox (x,y,w,h) 逐一處理並產生辨識結果列表
        # 包括: 裁切影像、取得座標 
        for (x, y, w, h) in faces:
            # face_roi = gray[y:y+h, x:x+w] # 從影像中切出人臉部分
            # face_resized = cv2.resize(face_roi, (100, 100)) # 影像裁切成100*100
            # ----- 影像裁切成100*100 -----
            face_resized = self.crop_and_resize(gray, (x,y,w,h))

            # ----- 安全裁切：夾取邊界，並跳過過小的 bbox（避免誤偵測）-----
            h_img, w_img = gray.shape[:2]
            x1 = max(0, x); y1 = max(0, y)
            x2 = min(x + w, w_img); y2 = min(y + h, h_img)
            if (x2 - x1) < 40 or (y2 - y1) < 40:
                # 太小，視為雜訊，跳過
                continue
            face_roi = gray[y1:y2, x1:x2]
            face_resized = cv2.resize(face_roi, (100, 100))
            result = self.predict_face(face_resized, position=(x, y, w, h)) # 分析人臉信心度
            # -----只加入有效結果-----
            if result is not None:  
                results.append(result) # 加入列表(人名、信心度、座標)
        
        return results

    # ===== 分析人臉信心度 =====
    # 輸入 已裁切的影像、人臉座標、標準信心度(90)
    # 輸出 人名、信心度、座標(顯示在畫面上)
    # ====================
    def predict_face(self, face_resized, position=None, confidence_threshold=85, confidence_invalid=105):
        # 從 recognize_face 中提取預測部分
                
        try:
            # 傳入已裁切的影像，進行臉部分析，得到人臉 id
            face_id, confidence = self.recognizer.predict(face_resized)

            # -----檢查有無超過「無效信心值」-----
            if confidence < confidence_invalid:
                # -----信心度大於等於「標準信心度」，判定為「未知」-----
                if confidence >= confidence_threshold:
                    name = '未知'
                    #print(f'未知={confidence}')
                # -----分數小於標準值，則是「已知」-----
                else:
                    row = self.db_manager.search_face(face_id) # 用 id 查詢人名
                    name = row[0] if row else '未知'
            else:
                return None

            return {'id': face_id ,'name': name, 'confidence': confidence, 'position': position} # 回傳結果(便是紀錄上顯示)
        
        # 例外錯誤處理
        except cv2.error:
            return {'id': face_id ,'name': '發生錯誤，無法辨識', 'confidence': 0, 'position': position}

    # ===== 在影像上繪製辨識結果 =====
    def draw_frame(self, results, frame):
        for result in results: # 遍歷每個人臉
                x, y, w, h = result['position']     # 人臉位置與大小
                name = result['name']               # 人臉名稱
                confidence = result['confidence']   # 人臉辨識信心度()

                color = (0, 255, 0) if name != '未知' else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

                label = f"{name} ({confidence:.1f})"
                cv2.putText(frame, label, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)