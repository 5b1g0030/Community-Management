import cv2                      # 電腦視覺處理和人臉辨識
import sqlite3                  # 本地資料庫管理
import numpy as np              # 數值計算和陣列操作
import os                       # 作業系統相關操作
import pickle                   # 物件序列化和反序列化
from datetime import datetime   # 日期和時間處理
import platform                 # 獲取作業系統資訊(選擇鏡頭系統參數用)
import hashlib                  # 使用者密碼加密用
from models.database import DatabaseManager # 資料庫管理工具(自製)
from models.face_detector import FaceDetector # 影像處理工具(自製)

""" 網頁將引用 FaceRecognitionSystem 類別 """

# ===== 人臉辨識系統類別 ===== 
class FaceRecognitionSystem:
    
    # ===== 初始化系統 =====
    # 1. 檔案路徑
    # 2. 人臉辨識器
    # 3. 資料庫
    # 4. 載入模型
    # =====================    
    def __init__(self, db_path='face_database/face_database.db', model_path='face_database/face_model.pkl'):
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
        self.db_manager = DatabaseManager(db_path)
        
        # 初始化影像處理工具
        self.face_detector = FaceDetector()
        
        # 載入已存在的模型（如果有的話）
        #self.load_model()

    
    # ====== 決定鏡頭所用參數 =====
    # 1. 取得作業系統資訊
    # 2. 根據作業系統選擇後端參數
    # 3. 回傳這個作業系統的鏡頭參數
    # ============================ 
    def camera_type(self):
        # ***** 攝影機參數 *****
        # cv2.VideoCapture(0) => 使用預設後端(有可能使用到不適合的系統)
        # cv2.VideoCapture(0, cv2.【系統參數】) => 可以指定適合的系統 
        # Windows => CAP_DSHOW(推薦), CAP_MSMF
        # macOS => CAP_AVFOUNDATION(推薦)
        # Linux => CAP_V4L2(推薦), CAP_GSTREAMER
        # ********************* 

        # ----- 取得作業系統資訊 -----
        os_type = platform.system() # 會回傳一個字串，代表你目前的作業系統
        backends = [] # 作業系統可用參數(回傳值)

        # ----- 根據作業系統選擇後端參數 -----
        if os_type == "Windows":    # windows系統
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_VFW]
        elif os_type == "Darwin":   # macOS系統
            backends = [cv2.CAP_AVFOUNDATION]
        elif os_type == "Linux":    # linux系統
            backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER]
        else:
            backends = [cv2.CAP_ANY]

        # ----- 自動搜尋可用的攝影機 -----
        print("搜尋可用的攝影機...")
        
        for index in range(6):  # 測試攝影機索引 0-5
            print(f"  測試攝影機索引 {index}...")
            
            for backend in backends: # 逐個嘗試系統參數
                try:
                    print(f"    嘗試後端: {backend}")
                    cap = cv2.VideoCapture(index, backend) # 測試攝影機

                    # # 測試是否能讀取影像
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cap.release()
                            print(f"✅ 找到可用攝影機: 索引 {index}, 後端 {backend}")
                            return index, backend  # 立即回傳找到的設定(相機索引, 系統參數)

                    cap.release()

                except Exception as e:
                    print(f"    後端 {backend} 失敗: {e}")
                    continue
        # ✅ 沒有找到任何可用攝影機
        print("❌ 沒有找到可用的攝影機")
        return None, None
        
    
    
    # ===== 將人臉加入資料庫 =====
    # 1. 取得人臉座標、灰階影像
    # 2. 檢查有沒有偵測到人臉 -> false
    # 3. 取第一個人臉(簡化流程，確保指輸入一張人臉資料)
    # 4. 調整人臉大小(方便辨識與儲存)
    # 5. 儲存到資料庫
    # 6. 顯示成功訊息
    # 7. 重新訓練模型 -> true
    # =========================== 
    def add_face_to_database(self, image, name, image_path=None):
        try:
            # ---- 取得人臉座標、灰階影像 -----
            faces, gray = self.face_detector.detect_faces(image)
            
            # ----- 檢查有沒有偵測到人臉 -----
            if len(faces) == 0:
                print("未偵測到人臉")
                return False # 結束函式
            
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
            face_blob = pickle.dumps(face_resized) # 人臉影像（NumPy 陣列）序列化成二進位資料（BLOB），方便儲存到資料庫。
            
            # ----- 儲存到資料庫 -----
            self.db_manager.save_face_to_db(name, face_blob, image_path)
            
            
            # ----- 重新訓練模型 -----
            self.train_model()

            return True # 成功
        
        # 如果執行過程中出錯
        except Exception as e:
            print(f'加入人臉資料失敗: {str(e)}') # 顯示錯誤訊息(終端顯示)
            raise e # 重新拋出例外讓 Flask 處理(網頁顯示)
    
    # ===== 訓練人臉辨識模型 =====
    # 1. 連接資料庫取得人臉資料
    # 2. 檢查資料庫是否有資料
    # 3. 資料反序列化
    # 4. 訓練模型
    # 5. 儲存模型
    # ========================== 
    def train_model(self):

        # ----- 訓練模型-取得訓練資料 -----
        data = self.db_manager.train_model_faces()
        
        # -----訓練模型-資料處理 -----
        self.face_detector.train_model_processing(data)

    
    # ===== 載入已訓練的模型 =====
    # 1. 檢查模型檔案是否存在
    # 2. 載入模型(如果有檔案)
    # 3. 顯示載入結果 
    # def load_model(self):
        
    #     # 檢查模型檔案是否存在
    #     if os.path.exists(self.model_path):
    #         # 載入模型
    #         self.recognizer.read(self.model_path)
    #         # 成功訊息
    #         print("模型載入成功")
    #     else:
    #         # 失敗訊息
    #         print("未找到已訓練的模型")
    
    # ===== 辨識人臉 =====
    # 1. 取得所有人臉座標和灰階影像
    # 2. 逐一處理每一張人臉
    # 3. 進行人臉辨識
    # 4. 查詢人名
    # 5. 根據信心度閾值儲存辨識結果
    # 6. 回傳結果
    # =================== 
    def recognize_face(self, image):
        
        # ----- 取得所有人臉座標和灰階影像 -----
        faces, gray = self.face_detector.detect_faces(image)

        results = [] # 儲存辨識結果        

        # # ----- 逐一處理每一張人臉 -----
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w] # 裁切出人臉區域
            face_resized = cv2.resize(face_roi, (100, 100)) # 縮放成 100x100 像素

            try:
                #face_id, confidence = self.recognizer.predict(face_resized)
                result = self.face_detector.predict_face(face_resized, position=(x, y, w, h))
                
                results.append(result)  
                    
                # 辨識錯誤的資料
            except cv2.error: # 例外處理與法，捕捉 OpenCV 執行過程中發生的錯誤
                    results.append({
                        'name': '發生錯誤，無法辨識',
                        'confidence': 0,
                        'position': (x, y, w, h)
                    })
        
        # ----- 回傳結果 -----
        return results
    
    # ===== 處理靜態圖片 =====
    # 1. 讀取圖片
    # 2. 呼叫「辨識人臉函式」
    # 3. 在圖片上標記辨識結果
    # 4. 顯示標記後的圖片
    # 5. 等待使用者關閉視窗
    # ======================= 
    def process_image(self, image_path):

        # ----- 讀取圖片 -----
        image = cv2.imread(image_path) # 從指定路徑讀取圖片，轉換成 NumPy 陣列，路徑錯誤或檔案不存在會是 None
        if image is None:
            print(f"無法讀取圖片: {image_path}")
            return
        
        # ----- 呼叫「辨識人臉函式」 -----
        results = self.recognize_face(image) 
        
        # ----- 在圖片上標記辨識結果 -----
        # 假設你想要顯示 800x600
        target_size = (800, 600)
        image_resized = cv2.resize(image, target_size) 

        # 你也要根據縮放比例調整框的座標
        scale_x = target_size[0] / image.shape[1]
        scale_y = target_size[1] / image.shape[0]
        for result in results:                  # 逐一處理所有辨識到的人臉結果。
            print("辨識結果：", results) 
            x, y, w, h = result['position']     # 人臉座標
            x = int(x * scale_x)
            y = int(y * scale_y)
            w = int(w * scale_x)
            h = int(h * scale_y)
            print(f"框座標: x={x}, y={y}, w={w}, h={h}")
            name = result['name']               # 人名
            confidence = result['confidence']   # 辨識信心度
            
            cv2.rectangle(image_resized, (x, y), (x+w, y+h), (0, 255, 0), 2) # 以綠色方框標記人臉區域
            
            label = f"{name} ({confidence:.1f})" # 要顯示的文字
            cv2.putText(image_resized, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2) # 在方框上方顯示人名和信心度
        
        # ----- 顯示標記後的圖片 -----
        cv2.namedWindow('Face Recognition - Image', cv2.WINDOW_NORMAL) # 讓視窗可自由縮放
        #cv2.resizeWindow('Face Recognition - Image', 800, 600)          # 設定初始大小為 800x600
        cv2.imshow('Face Recognition - Image', image_resized) 
        cv2.waitKey(0) # 等待使用者關閉視窗
        cv2.destroyAllWindows() # 關閉所有 OpenCV 視窗
    
    # ===== 即時鏡頭辨識 =====
    # 1. 開啟攝影機(根據作業系統選擇後端參數)
    # 2. 設定解析度與編碼格式
    # 3. 讀取影像
    # 4. 在畫面上標記辨識結果
    # 5. 顯示標記後的畫面
    # 6. 退出或截圖儲存資料庫
    # ======================= 
    def camera_recognition(self):
        # ----- 開啟攝影機 -----
        backends = self.camera_type() # 呼叫「決定鏡頭所用參數函式」
        cap = None
        for backend in backends: # 依序測試系統參數
            try:
                cap = cv2.VideoCapture(0, backend) # 放入參數
                if cap.isOpened(): # 如果攝影機成功開啟，則跳出迴圈
                    break
                else:
                    cap.release()
            except Exception: # 錯誤處理
                continue
        
        # 沒有參數適合的情況
        if cap is None or not cap.isOpened():
            print("無法開啟攝影機，請檢查設備或驅動程式。")
            return

        # ----- 設定解析度與編碼格式 -----
        # cv2.CAP_PROP_FRAME_WIDTH => 影像寬度
        # cv2.CAP_PROP_FRAME_HEIGHT => 影像高度
        # 影像寬度 + 影像高度 = 影像解析度(寬*高)
        # 常見解析度:
        # VGA (640*480)
        # HD 720p (1280*720)
        # Full HD 1080p (1920*1080)
        # 注意事項: 
        # 1. 攝影機不一定支援所有解析度
        # 2. 解析度越高，處理速度越慢(延遲高)
        # 3. 要在攝影機開啟後立即設定
        # 4. 如果攝影機不支援該解析度，OpenCV 會自動選擇最接近的解析度
        # -------------------------------
        # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 920)
        # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG')) # 用 MJPG 編碼減少延遲
        
        print("開始鏡頭辨識，按 'q' 退出，按 's' 截圖並加入資料庫") # 提示操作說明
        
        while True:
            # ----- 讀取影像 -----
            ret, frame = cap.read()
            if not ret: # 檢查有沒有讀取到影像
                break
            
            results = self.recognize_face(frame) # 呼叫「人臉辨識函式」
            
            # ----- 在畫面上標記辨識結果 -----
            for result in results:
                x, y, w, h = result['position']
                name = result['name']
                confidence = result['confidence']
                
                color = (0, 255, 0) if name != '未知' else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                label = f"{name} ({confidence:.1f})"
                cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # ----- 顯示標記後的畫面 -----
            cv2.imshow('Face Recognition - Camera', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): # 按 q 退出
                break
            elif key == ord('s'): # 按 s 截圖儲存到資料庫
                # 截圖並加入資料庫
                name = input("請輸入人名: ")
                if name:
                    self.add_face_to_database(frame, name) # 呼叫「將人臉加入資料庫函式」
        
        cap.release()
        cv2.destroyAllWindows()
    
    # ===== 列出資料庫中的所有人臉資料(終端) =====
    # 1. 連接資料庫
    # 2. 查詢人臉資料
    # 3. 查詢辨識紀錄
    # 4. 關閉資料庫
    # 5. 顯示資料
    # ==================================== 
    def list_faces(self):
        
        # ----- 連接資料庫 -----
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor() # 建立游標物件執行 SQL 指令
        
        # ----- 查詢人臉資料 -----
        cursor.execute("SELECT id, name, created_date FROM faces")
        faces = cursor.fetchall()
        
        # ----- 查詢辨識紀錄 -----
        cursor.execute("SELECT COUNT(*) FROM recognition_log")
        total_recognitions = cursor.fetchone()[0]
        
        conn.close() # 關閉資料庫
        
        # ----- 顯示資料 -----
        print(f"\n資料庫中共有 {len(faces)} 個人臉資料:")
        print("=" * 50)
        for face_id, name, created_date in faces:
            print(f"ID: {face_id}, 姓名: {name}, 建立時間: {created_date}")
        
        print(f"\n總辨識次數: {total_recognitions}")

    # ===== 列出資料庫中的所有人臉資料(網頁) =====
    # 1. 連接資料庫
    # 2. 查詢所有資料
    # 3. 把內容轉為字典格式
    # 4. 關閉資料庫
    # 5. 回傳字典格式的資料 
    # ==========================================   
    # def get_all_faces(self):
    #     conn = sqlite3.connect(self.db_path) # 連接資料庫
    #     cursor = conn.cursor()               # 建立物件執行 SQL 指令
    #     cursor.execute("SELECT id, name, created_date FROM faces") # 查詢資料(face 表格中的三個欄位(id, name, created_date))
    #     faces = [{'id': row[0], 'name': row[1], 'created_date': row[2]} for row in cursor.fetchall()] # 資料轉換(列表推導式，把原始資料轉換為字典格式)
    #     conn.close() # 關閉連接
    #     return faces # 回傳資料查詢結果
    
    # ===== 列出資料庫中的所有辨識紀錄(網頁) =====
    # 1. 連接資料庫
    # 2. 查詢辨識紀錄與對應人名
    # 3. 把內容轉為字典格式
    # 4. 關閉資料庫
    # 5. 回傳字典格式的資料
    # ============================================
    # def get_all_recognition_logs(self):
    #     conn = sqlite3.connect(self.db_path) # 連接資料庫
    #     cursor = conn.cursor()               # 建立物件執行 SQL 指令
        
    #     # 查詢辨識紀錄，並與人臉表格做關聯以取得人名
    #     cursor.execute('''
    #         SELECT rl.id, f.name, rl.recognition_date, rl.confidence
    #         FROM recognition_log rl
    #         LEFT JOIN faces f ON rl.face_id = f.id
    #         ORDER BY rl.recognition_date DESC
    #     ''')
        
    #     # 資料轉換為字典格式
    #     logs = []
    #     for row in cursor.fetchall():
    #         logs.append({
    #             'id': row[0],
    #             'name': row[1],
    #             'recognition_date': row[2],
    #             'confidence': row[3]
    #         })
        
    #     conn.close() # 關閉連接
    #     return logs  # 回傳資料查詢結果

    # ===== 使用者註冊 =====
    # 回傳 執行結果, 訊息
    # ===================== 
    # def register_uer(self, username, password):
    #     try:
    #         conn = sqlite3.connect(self.db_path) # 連接資料庫
    #         cursor = conn.cursor() # 建立游標執行 SQL 指令

    #         # 檢查使用者是否已存在
    #         cursor.execute("SELECT id FROM users WHERE username= ?", (username,))
    #         # 檢查第一筆資料，如果重複則結束函式並告訴使用者「此名稱已存在」
    #         if cursor.fetchone():
    #             conn.close() # 關閉資料庫連接
    #             return False, "使用者名稱已被使用"
            
    #         # 密碼加密
    #         password_hash = hashlib.sha256(password.encode()).hexdigest()

    #         # 插入新使用者
    #         cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
    #                        (username, password_hash)
    #                        )
            
    #         conn.commit() # 更新資料庫
    #         conn.close() # 關閉連接

    #         return True, "註冊成功"

    #     # 例外錯誤處理
    #     except Exception as e:
    #         return False, f"註冊失敗: {str(e)}"
    
    # ===== 使用者登入 =====
    # 回傳 執行結果
    # ===================== 
    # def login_user(self, username, password):
    #     try:
    #         conn = sqlite3.connect(self.db_path) # 連接資料庫
    #         cursor = conn.cursor() # 建立游標執行 SQL 指令

    #         # 把使用者輸入的密碼加密
    #         password_hash = hashlib.sha256(password.encode()).hexdigest()

    #         # 查詢使用者與密碼
    #         cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?",
    #                        (username, password_hash)
    #                        )
            
    #         # 紀錄第一筆資料
    #         user = cursor.fetchone()
    #         conn.close() # 關閉連接

    #         return user is not None

    #     # 例外錯誤處理
    #     except Exception as e:
    #         return False
    

# ===== 主程式 =====
# 1. 引入類別
# 2. 顯示功能表
# 3. 使用者輸入
# 4. 根據選擇啟動不同功能
# 5. 例外處理
# 6. 直到使用者輸入 6 退出函式
# ================== 
def main():
    # ----- 引入類別 -----
    system = FaceRecognitionSystem() 
    
    while True:
        # ----- 顯示功能表 -----
        print("\n=== 人臉辨識系統 ===")
        print("1. 從圖片加入人臉資料")
        print("2. 從鏡頭加入人臉資料")
        print("3. 辨識圖片中的人臉")
        print("4. 開始鏡頭辨識")
        print("5. 查看資料庫資料")
        print("6. 退出")
        
        # ----- 使用者輸入 -----
        choice = input("\n請選擇功能 (1-6): ") 
        
        # ----- 選1: 輸入圖片加入資料庫訓練模型 -----
        # 1. 輸入圖片
        # 2. 讀取圖片
        # 3. 加入資料庫或輸出錯誤
        # ----------------------------------------- 
        if choice == '1':
            # --- 輸入圖片 ---
            image_path = input("請輸入圖片路徑: ")
            name = input("請輸入人名: ")
            
            # --- 讀取圖片 ---
            image = cv2.imread(image_path) 
            
            # --- 加入資料庫或輸出錯誤 ---
            if image is not None: # 如果有圖片
                system.add_face_to_database(image, name, image_path) # 呼叫「將人臉加入資料庫函式」
            else:
                print("無法讀取圖片")
        
        # ----- 選2: 用鏡頭拍照加入資料庫訓練模型 -----
        # 1. 開啟攝影機
        # 2. 顯示畫面
        # 3. 按下空白鍵拍照並儲存資料庫
        # 4. 退出
        # ------------------------------------------- 
        elif choice == '2':
            # --- 開啟攝影機 ---
            backends = system.camera_type() # 呼叫「決定鏡頭所用參數函式」
            cap = None
            for backend in backends: # 依序測試系統參數
                try:
                    cap = cv2.VideoCapture(0, backend) # 放入參數
                    if cap.isOpened(): # 如果攝影機成功開啟，則跳出迴圈
                        break
                    else:
                        cap.release()
                except Exception: # 錯誤處理
                    continue
        
            # 沒有參數適合的情況
            if cap is None or not cap.isOpened():
                print("無法開啟攝影機，請檢查設備或驅動程式。")
                return
            
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 920)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            
            print("按空白鍵拍照，按 'q' 退出") # 提示詞
            
            while True:
                ret, frame = cap.read() # 讀取影像
                if not ret:
                    break
                
                # --- 顯示畫面 ---
                cv2.imshow('Camera - Press SPACE to capture', frame)
                
                key = cv2.waitKey(1) & 0xFF # 即時更新
                
                # --- 按下空白鍵拍照並儲存資料庫 ---
                if key == ord(' '):
                    name = input("請輸入人名: ")
                    if name:
                        system.add_face_to_database(frame, name) # 呼叫「將人臉加入資料庫函式」
                    break
                elif key == ord('q'): # 按 q 退出
                    break
            
            cap.release() # 釋放資源
            cv2.destroyAllWindows() # 關閉所有 OpenCV 視窗
        
        # ----- 選3: 辨識圖片中的人臉 -----
        # 1. 輸入圖片
        # 2. 呼叫「處理靜態圖片」
        # -------------------------------  
        elif choice == '3':
            # --- 輸入圖片 ---
            image_path = input("請輸入圖片路徑: ") 
            # --- 呼叫「處理靜態圖片」 ---
            system.process_image(image_path)
        
        # ----- 選4: 開始鏡頭辨識 -----
        # 1. 呼叫「即時鏡頭辨識」
        # ----------------------- 
        elif choice == '4':
            # --- 呼叫「即時鏡頭辨識」 ---
            system.camera_recognition()
        
        # ----- 選5: 查看資料庫資料 -----
        # 1. 列出資料庫中的所有人臉資料
        # ------------------------------ 
        elif choice == '5':
            system.list_faces()
        
        # ----- 選6: 退出 -----
        # 1. 顯示退出訊息
        # 2. 跳出無限迴圈結束此函式運行
        # -------------------- 
        elif choice == '6':
            # --- 顯示退出訊息 ---
            print("程式結束")
            # --- 跳出無限迴圈結束此函式運行 ---
            break
        
        else:
            print("請輸入有效選項") # 例外處理

# 在此檔案被執行時才執行主程式
if __name__ == "__main__":
    main() # 呼叫「主程式」