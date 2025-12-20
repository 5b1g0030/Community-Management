import os
import numpy as np
import pickle
import sqlite3

class ModelManager:
    # ===== 初始化 =====
    def __init__(self, recognizer, model_path, db_path, db_manager):
        self.recognizer = recognizer
        self.model_path = model_path
        self.db_path = db_path
        self.db_manager = db_manager
        self.load_model() # 自動載入模型

    # ===== 訓練人臉辨識模型 =====
    def train_model(self):
        data = self.train_model_faces()
        # self.train_model_processing(data)
        # ----- 檢查資料庫是否有資料 -----
        if len(data) == 0:
            print("資料庫中沒有人臉資料")
            return  # 結束此函式

        faces = []  # 存放人臉影像
        labels = []  # 每張人臉對應的 ID (主鍵)

        # ----- 資料反序列化 -----
        for face_id, face_blob in data:  # 遍歷資料
            face_array = pickle.loads(face_blob)  # 把 BLOB 格式的人臉影像還原成 NumPy 陣列
            faces.append(face_array)  # 把還原後的影像加入 faces 列表
            labels.append(face_id)  # 把人臉的 ID 加入 labels 列表，作為模型訓練的標籤

        # ----- 訓練模型 -----
        # 使用 LBPH 人臉辨識器（OpenCV 提供）
        # 參數 => (有人臉影像的 NumPy 陣列列表 , 每張人臉對應的 ID)
        self.recognizer.train(faces, np.array(labels))

        # ----- 儲存模型 -----
        # 把目前訓練好的模型儲存成檔案
        self.recognizer.save(self.model_path)

        # ----- 輸出成功訊息 -----
        print(f"模型訓練完成，已儲存至 {self.model_path} by face_detector")

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

        # ===== 訓練模型-取得訓練資料 =====
    
    # ===== 取得模型訓練資料 =====
    # 傳入 無
    # 回傳 人臉id、人臉二進位資訊
    # ==========================
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
    