import cv2
import numpy as np
import pickle
import os
import platform
import datetime
from models.database import DatabaseManager

# ===== 影像處理類別 =====
class FaceDetector:
    # ===== 初始化 =====
    def __init__(self, model_path='face_database/face_model.pkl', db_path='face_database/face_database.db'):
        # 訓練模型路徑
        self.model_path = model_path

        # OpenCV 的 Haar cascade 人臉偵測模型檔案，用於偵測影像中的人臉位置
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # 從已訓練的人臉樣本學習特徵並對新人臉做預測（回傳 id 與「相似度/距離」分數）
        self.recognizer = cv2.face.LBPHFaceRecognizer_create() # 
        
        # 資料庫路徑
        self.db_manager = DatabaseManager(db_path)
        
        # 載入模型
        self.load_model()
    
    # ===== 偵測圖像中的人臉 =====
    # 傳入 圖片
    # 回傳 灰階影像、人臉座標
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
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # 的影像轉灰階（因為人臉偵測只需灰階資訊）
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5) # Haar 級聯分類器偵測人臉，回傳所有人臉的座標（x, y, w, h）
        return faces, gray # 兩者皆為 NumPy 陣列
    
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
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, (100, 100))
            face_blob = pickle.dumps(face_resized)
            
            self.db_manager.save_face_to_db(name, face_blob, image_path)
            self.train_model()
            return True
        
        except Exception as e:
            print(f'加入人臉資料失敗: {str(e)}')
            raise e

    # ===== 訓練人臉辨識模型 =====
    def train_model(self):
        data = self.db_manager.train_model_faces()
        # self.train_model_processing(data)
        # ----- 檢查資料庫是否有資料 -----
        if len(data) == 0:
            print("資料庫中沒有人臉資料")
            return # 結束此函式
        
        faces = [] # 存放人臉影像
        labels = [] # 每張人臉對應的 ID (主鍵)
        
        # ----- 資料反序列化 ----- 
        for face_id, face_blob in data: # 遍歷資料
            face_array = pickle.loads(face_blob) # 把 BLOB 格式的人臉影像還原成 NumPy 陣列
            faces.append(face_array) # 把還原後的影像加入 faces 列表
            labels.append(face_id) # 把人臉的 ID 加入 labels 列表，作為模型訓練的標籤
        
        # ----- 訓練模型 -----
        # 使用 LBPH 人臉辨識器（OpenCV 提供）
        # 參數 => (有人臉影像的 NumPy 陣列列表 , 每張人臉對應的 ID) 
        self.recognizer.train(faces, np.array(labels))
        
        # ----- 儲存模型 -----
        # 把目前訓練好的模型儲存成檔案 
        self.recognizer.save(self.model_path)

        # ----- 輸出成功訊息 -----
        print(f"模型訓練完成，已儲存至 {self.model_path} by face_detector")

    # # ====== 訓練模型-資料處理 =====
    # # 傳入 人臉資料(id, 二進位資訊)
    # # 回傳 無
    # # ====================   
    # def train_model_processing(self, faces_data):
    #     # ...existing train_model code...
    #     '''
    #         1. 連接資料庫取得人臉資料
    #         2. 檢查資料庫是否有資料
    #         3. 資料反序列化
    #         4. 訓練模型
    #         5. 儲存模型
    #     '''
    #     self.db_manager.train_model_faces()

    #     # ----- 檢查資料庫是否有資料 -----
    #     if len(faces_data) == 0:
    #         print("資料庫中沒有人臉資料")
    #         return # 結束此函式
        
    #     faces = [] # 存放人臉影像
    #     labels = [] # 每張人臉對應的 ID (主鍵)
        
    #     # ----- 資料反序列化 ----- 
    #     for face_id, face_blob in faces_data: # 遍歷資料
    #         face_array = pickle.loads(face_blob) # 把 BLOB 格式的人臉影像還原成 NumPy 陣列
    #         faces.append(face_array) # 把還原後的影像加入 faces 列表
    #         labels.append(face_id) # 把人臉的 ID 加入 labels 列表，作為模型訓練的標籤
        
    #     # ----- 訓練模型 -----
    #     # 使用 LBPH 人臉辨識器（OpenCV 提供）
    #     # 參數 => (有人臉影像的 NumPy 陣列列表 , 每張人臉對應的 ID) 
    #     self.recognizer.train(faces, np.array(labels))
        
    #     # ----- 儲存模型 -----
    #     # 把目前訓練好的模型儲存成檔案 
    #     self.recognizer.save(self.model_path)

    #     # ----- 輸出成功訊息 -----
    #     print(f"模型訓練完成，已儲存至 {self.model_path} by face_detector")

    # ===== 載入已訓練模型 =====
    def load_model(self):
        # ...existing load_model code...
        '''
            1. 檢查模型檔案是否存在
            2. 載入模型(如果有檔案)
            3. 顯示載入結果 
        '''
        # 檢查模型檔案是否存在
        if os.path.exists(self.model_path):
            # 載入模型
            self.recognizer.read(self.model_path)
            # 成功訊息
            print("模型載入成功 by face_detector")
        else:
            # 失敗訊息
            print("未找到已訓練的模型 by face_detector")
    
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
            face_roi = gray[y:y+h, x:x+w] # 從影像中切出人臉部分
            face_resized = cv2.resize(face_roi, (100, 100)) # 影像裁切成100*100

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