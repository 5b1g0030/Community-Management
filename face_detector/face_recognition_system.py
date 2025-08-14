import cv2                      # 電腦視覺處理和人臉辨識
import sqlite3                  # 本地資料庫管理
import numpy as np              # 數值計算和陣列操作
import os                       # 作業系統相關操作
import pickle                   # 物件序列化和反序列化
from datetime import datetime   # 日期和時間處理

# ===== 人臉辨識系統類別 =====
# 裡面包含:
# 1. 初始化系統
# 2. 人臉資料管理
# 3. 人臉辨識
# 4. 資料庫管理
# 5. 模型訓練    
# ===========================  
class FaceRecognitionSystem:
    
    # ===== 初始化系統 =====
    # 1. 檔案路徑
    # 2. 人臉辨識器
    # 3. 資料庫
    # 4. 載入模型
    # =====================    
    def __init__(self, db_path='face_database.db', model_path='face_model.pkl'):
        # 初始化檔案路徑
        self.db_path = db_path # 指定 SQLite 資料庫
        self.model_path = model_path # 指定訓練好的人臉辨識模型
        
        # ----- 初始化人臉辨識器 -----
        # face_cascade: OpenCV 內建的 Haar 級聯分類器，用於偵測人臉
        # recognizer: LBPH 人臉辨識器，用於訓練和辨識人臉
        # --------------------------- 
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # 初始化資料庫(建立或檢查資料庫表格)
        self.init_database()
        
        # 載入已存在的模型（如果有的話）
        self.load_model()
    
    # ===== 初始化SQLite資料庫 =====
    # 1. 創建人臉資料表
    # 2. 創建辨識紀錄資料表
    # 3. 確認變更(寫入磁碟)
    # 4. 關閉連接
    # ============================== 
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
        # FOREIGN KEY: 建立與 faces 表格的關聯性
        # 補充:
        # IF NOT EXISTS: 只有在表格不存在時才建立，避免重複建立錯誤
        # 資料關聯性: 透過外鍵建立兩個表格間的關聯，確保資料完整性
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
        
        conn.commit() # 確認變更(寫入磁碟，表格才會建立)
        conn.close() # 關閉連接(不關閉資料庫連線會導致資源洩漏、效能問題，甚至程式崩潰。)
        print("資料庫初始化完成")
    
    # ===== 偵測圖像中的人臉 =====
    # 1. 影像轉灰階
    # 2. 取得所有人臉的座標（x, y, w, h）
    # 3. 回傳出結果(包含灰階影像、人臉座標)
    # 補充: 
    # (gray, 1.3, 5) => (灰階影像, 影像尺寸縮小比例, 判定為人臉的分數)
    # 影像尺寸縮小比例 => 每次影像縮小到原本的 1/1.3，有些人臉可能比較大或比較小，偵測器會在不同尺寸的影像中都嘗試偵測，增加找到人臉的機會。
    # =========================== 
    def detect_faces(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) # 的影像轉灰階（因為人臉偵測只需灰階資訊）
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5) # Haar 級聯分類器偵測人臉，回傳所有人臉的座標（x, y, w, h）
        return faces, gray # 兩者皆為 NumPy 陣列
    
    # ===== 將人臉加入資料庫 =====
    # 1. 取得人臉座標、灰階影像
    # 2. 檢查有沒有偵測到人臉
    # 3. 取第一個人臉(簡化流程，確保指輸入一張人臉資料)
    # 4. 調整人臉大小(方便辨識與儲存)
    # 5. 儲存到資料庫
    # 6. 顯示成功訊息
    # 7. 重新訓練模型
    # =========================== 
    def add_face_to_database(self, image, name, image_path=None):

        # ---- 取得人臉座標、灰階影像 -----
        faces, gray = self.detect_faces(image)
        
        # ----- 檢查有沒有偵測到人臉 -----
        if len(faces) == 0:
            print("未偵測到人臉")
            return False
        
        # ----- 取第一個偵測到的人臉 -----
        # (x,y,w,h)=faces[0] => 是 Python 的「序列解包」語法。
        # 序列解包 => 可以一次把這 4 個值分別存到 4 個變數裡，方便後續使用
        # y:y+h => 從第 y 列開始，到第 y+h 列（不包含 y+h），即人臉區域的高度範圍。
        # x:x+w => 從第 x 行開始，到第 x+w 行（不包含 x+w），即人臉區域的寬度範圍。
        # ------------------------------ 
        (x, y, w, h) = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        # ----- 調整人臉大小(方便辨識與儲存) -----
        # face_roi => 原本裁切出來的人臉影像，大小不一定。
        # (100, 100)：指定要縮放成的目標尺寸（寬 100、高 100）。
        # 樣做可以讓所有人臉影像在資料庫和模型訓練時，尺寸一致，方便後續辨識與比對。
        # -------------------------------------- 
        face_resized = cv2.resize(face_roi, (100, 100))
        
        # ----- 儲存到資料庫 -----
        conn = sqlite3.connect(self.db_path) # 連接SQLite
        cursor = conn.cursor() # 建立游標物件，用來執行 SQL 指令（查詢、插入、更新等）
        
        face_blob = pickle.dumps(face_resized) # 人臉影像（NumPy 陣列）序列化成二進位資料（BLOB），方便儲存到資料庫。
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 取得目前的日期和時間，並格式化成字串，記錄資料建立的時間。
        
        # SQL 指令，意思是「新增一筆資料到 faces 表格」。
        # ? 是參數佔位符，防止 SQL injection（安全性）。
        # 插入的資料，分別是人名、序列化後的人臉影像、圖片路徑、建立時間。 
        cursor.execute('''
            INSERT INTO faces (name, face_encoding, image_path, created_date)
            VALUES (?, ?, ?, ?)
        ''', (name, face_blob, image_path, created_date))
        

        face_id = cursor.lastrowid # 取得剛剛插入資料的「自動遞增主鍵」ID (唯一編號)
        conn.commit() # 提交變更，確保資料儲存到資料庫
        conn.close() # 關閉連接，避免記憶體洩漏或效能問題
        
        # ----- 顯示成功訊息 -----
        print(f"成功將 {name} 的人臉資料加入資料庫 (ID: {face_id})")
        
        # ----- 重新訓練模型 -----
        self.train_model()

        return True
    
    # ===== 訓練人臉辨識模型 =====
    # 1. 連接資料庫取得人臉資料
    # 2. 檢查資料庫是否有資料
    # 3. 資料反序列化
    # 4. 訓練模型
    # 5. 儲存模型
    # ========================== 
    def train_model(self):

        # ------ 連接資料庫取得人臉資料 ----- 
        conn = sqlite3.connect(self.db_path) # 連接 SQLite
        cursor = conn.cursor() # 建立游標物件來執行 SQL 指令
        
        cursor.execute("SELECT id, face_encoding FROM faces") # 資料查詢(所有人臉資料)
        data = cursor.fetchall() # 取得查詢結果
        conn.close() # 關閉資料庫連接
        
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
        print(f"模型訓練完成，已儲存至 {self.model_path}")
    
    # ===== 載入已訓練的模型 =====
    # 1. 檢查模型檔案是否存在
    # 2. 載入模型(如果有檔案)
    # 3. 顯示載入結果 
    def load_model(self):
        
        # 檢查模型檔案是否存在
        if os.path.exists(self.model_path):
            # 載入模型
            self.recognizer.read(self.model_path)
            # 成功訊息
            print("模型載入成功")
        else:
            # 失敗訊息
            print("未找到已訓練的模型")
    
    # ===== 辨識人臉 =====
    # 1. 取得所有人臉座標和灰階影像
    # 2. 逐一處理每一張人臉
    # 3. 進行人臉辨識
    # 4. 查詢人名
    # 5. 根據信心度閾值紀錄辨識結果
    # 6. 回傳結果
    # =================== 
    def recognize_face(self, image):
        
        # ----- 取得所有人臉座標和灰階影像 -----
        faces, gray = self.detect_faces(image)
        
        results = [] # 儲存辨識結果

        # ----- 逐一處理每一張人臉 -----
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w] # 裁切出人臉區域
            face_resized = cv2.resize(face_roi, (100, 100)) # 縮放成 100x100 像素
            
            try:
                # ----- 進行人臉辨識 -----
                label, confidence = self.recognizer.predict(face_resized)
                
                # ----- 查詢人名 -----
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM faces WHERE id = ?", (label,))
                result = cursor.fetchone()
                
                if result and confidence < 100:  # 信心度閾值
                    name = result[0]
                    
                    # ---- 記錄辨識結果 -----
                    recognition_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute('''
                        INSERT INTO recognition_log (face_id, recognition_date, confidence)
                        VALUES (?, ?, ?)
                    ''', (label, recognition_date, confidence))
                    conn.commit()
                    
                    # 辨識成功的資料
                    results.append({
                        'name': name,
                        'confidence': confidence,
                        'position': (x, y, w, h)
                    })
                else:
                    # 辨識失敗的資料
                    results.append({
                        'name': '未知',
                        'confidence': confidence,
                        'position': (x, y, w, h)
                    })
                
                conn.close()
                
            # 辨識錯誤的資料
            except cv2.error:
                results.append({
                    'name': '無法辨識',
                    'confidence': 0,
                    'position': (x, y, w, h)
                })
        
        # ----- 回傳結果 -----
        return results
    
    def process_image(self, image_path):
        """處理靜態圖片"""
        image = cv2.imread(image_path)
        if image is None:
            print(f"無法讀取圖片: {image_path}")
            return
        
        results = self.recognize_face(image)
        
        # 在圖片上標記辨識結果
        for result in results:
            x, y, w, h = result['position']
            name = result['name']
            confidence = result['confidence']
            
            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            label = f"{name} ({confidence:.1f})"
            cv2.putText(image, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        cv2.imshow('Face Recognition - Image', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    def camera_recognition(self):
        """即時鏡頭辨識"""
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        print("開始鏡頭辨識，按 'q' 退出，按 's' 截圖並加入資料庫")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            results = self.recognize_face(frame)
            
            # 在畫面上標記辨識結果
            for result in results:
                x, y, w, h = result['position']
                name = result['name']
                confidence = result['confidence']
                
                color = (0, 255, 0) if name != '未知' else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                label = f"{name} ({confidence:.1f})"
                cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            cv2.imshow('Face Recognition - Camera', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 截圖並加入資料庫
                name = input("請輸入人名: ")
                if name:
                    self.add_face_to_database(frame, name)
        
        cap.release()
        cv2.destroyAllWindows()
    
    def list_faces(self):
        """列出資料庫中的所有人臉資料"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, created_date FROM faces")
        faces = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM recognition_log")
        total_recognitions = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n資料庫中共有 {len(faces)} 個人臉資料:")
        print("=" * 50)
        for face_id, name, created_date in faces:
            print(f"ID: {face_id}, 姓名: {name}, 建立時間: {created_date}")
        
        print(f"\n總辨識次數: {total_recognitions}")

def main():
    system = FaceRecognitionSystem()
    
    while True:
        print("\n=== 人臉辨識系統 ===")
        print("1. 從圖片加入人臉資料")
        print("2. 從鏡頭加入人臉資料")
        print("3. 辨識圖片中的人臉")
        print("4. 開始鏡頭辨識")
        print("5. 查看資料庫資料")
        print("6. 退出")
        
        choice = input("\n請選擇功能 (1-6): ")
        
        if choice == '1':
            image_path = input("請輸入圖片路徑: ")
            name = input("請輸入人名: ")
            
            image = cv2.imread(image_path)
            if image is not None:
                system.add_face_to_database(image, name, image_path)
            else:
                print("無法讀取圖片")
        
        elif choice == '2':
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Windows專用參數
            print("按空白鍵拍照，按 'q' 退出")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                cv2.imshow('Camera - Press SPACE to capture', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' '):
                    name = input("請輸入人名: ")
                    if name:
                        system.add_face_to_database(frame, name)
                    break
                elif key == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
        
        elif choice == '3':
            image_path = input("請輸入圖片路徑: ")
            system.process_image(image_path)
        
        elif choice == '4':
            system.camera_recognition()
        
        elif choice == '5':
            system.list_faces()
        
        elif choice == '6':
            print("程式結束")
            break
        
        else:
            print("請輸入有效選項")

if __name__ == "__main__":
    main()