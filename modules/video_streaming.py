from modules import socketio, db_manager, face_recognizer
from utils.camera_utils import CameraManager
from modules.face_recognition import refresh_face_cache
from modules.config import FACE_RECOGNITION_FRAME_SKIP
import modules.config as config # 給相機同步修改用
import numpy as np
import cv2
import os
from datetime import datetime
import time

# ===== 推送辨識訊息(已知, 未知, 訪客) =====
def face_message(results, frame):
    for result in results:
        name = result['name']
        print(f"[推送辨識訊息] 檢查是否為訪客? name: {name}")
        # ----- 檢查是否為訪客 -----
        if name and name.startswith('visitor_'):
            # 查詢對應的住戶名稱
            print("[推送辨識訊息] 查詢對應的住戶名稱")
            username = db_manager.get_visitor_by_face_name(name)

            if username:
                    # 推送訊息
                    print("[推送辨識訊息] 辨識為訪客")
                    socketio.emit('recognition', {
                        'type': 'recognition',
                        'message': f'偵測到{username}住戶的訪客已到大門'
                    })
                        
                    # 儲存辨識紀錄
                    face_id = result.get('id')
                    conf = float(result.get('confidence', 0.0))
                    if face_id:
                        db_manager.save_recognition_log("訪客", f"{username}住戶的訪客已到大門", face_id, conf)
                        
                    # 立即清除訪客人臉資料
                    success = db_manager.clear_visitor_face_data(name)
                        
                    if success:
                        # 重新整理快取
                        refresh_face_cache(db_manager)
                        print(f"[系統] 訪客 {name} 已辨識並清除人臉資料")
                    else:
                        print(f"[系統] 訪客 {name} 人臉資料清除失敗")
            
            # ----- 如果不是「未知」且 name 不為空，則顯示名字 -----
        
        elif name and name != '未知':
                print("[推送辨識訊息] 辨識為住戶")
                socketio.emit('recognition', {
                    'type': 'recognition',
                    'message': f'偵測到{name}住戶來到大門'
            })
            
            # ----- 如果是「未知」，顯示未知人物 -----
        elif name == '未知':
            print("[推送辨識訊息] 辨識為未知")
            socketio.emit('recognition', {
                'type': 'recognition',
                'message': '偵測到未知人物'
            })
                    
            # 儲存暫存圖片
            temp_dir = os.path.join('static', 'temp')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
            cv2.imwrite(img_path, frame)

# ===== 在影像上繪製辨識結果 =====
def draw_frame(results, frame):
    for result in results:
        x, y, w, h = result['position'] # 人臉座標
        name = result['name'] # 人名
        confidence = result['confidence'] # 信心度

        # 已知=綠色；未知=紅色
        color = (0, 255, 0) if name != '未知' else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        label = f"{name} ({confidence:.1f})"
        cv2.putText(frame, label, (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

# ===== 如果無法成功編碼時使用，嘗試顯示錯誤畫面 =====
def show_encoding_error_frame():
    print("[錯誤] 無法將黑色畫面編碼為 JPEG 格式")
    # 返回一個簡單的錯誤畫面
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Encoding Error', (150, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    ret, buffer = cv2.imencode('.jpg', frame)
    # 如果編碼再次失敗
    if not ret:
        print("[嚴重錯誤] 無法生成錯誤畫面")
        buffer = b''

    return buffer

# ===== 顯示黑色畫面 =====
def show_black_frame():
    # 返回黑色畫面提示相機已關閉
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Camera is OFF', (180, 240),
       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, 'Click "Start Camera" to begin', (120, 280),
       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    ret, buffer = cv2.imencode('.jpg', frame)
    # 如果編碼失敗
    if not ret:
        buffer = show_encoding_error_frame()
    
    # 包裝成 HTTP 響應的一部分，傳輸到客戶端（例如瀏覽器）
    frame_bytes = buffer.tobytes()

    return frame_bytes

# ===== 顯示找不到相機畫面 =====
def show_not_found_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Camera Not Found', (50, 240),
    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    ret, buffer = cv2.imencode('.jpg', frame)
    # 如果編碼失敗
    if not ret:
        buffer = show_encoding_error_frame()
    
    # 包裝成 HTTP 響應的一部分，傳輸到客戶端（例如瀏覽器）
    frame_bytes = buffer.tobytes()

    return frame_bytes

# ===== 顯示相機開啟失敗畫面 =====
def show_open_failed_frame():
    error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(error_frame, 'Camera Open Failed', (50, 240),
        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    ret, buffer = cv2.imencode('.jpg', error_frame)

    # 如果編碼失敗
    if not ret:
        buffer = show_encoding_error_frame()

    # 包裝成 HTTP 響應的一部分，傳輸到客戶端（例如瀏覽器）
    frame_bytes = buffer.tobytes()

    return frame_bytes


# ===== 影像串流&推送辨識訊息 =====
def gen_frames():
    while True:
        # --- 等待相機開啟期間，顯示黑畫面 ---
        while not config.CAMERA_ACTIVE:
            black_frame = show_black_frame()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + black_frame + b'\r\n')
            time.sleep(0.5)
        
        # ===== 影像串流 =====
        try:
            # --- 取得相機索引、可用參數 ---
            backends = CameraManager.get_camera_config()
            camera_index, backend = CameraManager.find_camera(backends)

            # --- 如果沒有找到相機或可用參數，顯示無法找到相機的畫面 ---
            if camera_index is None or backend is None:
                not_found_frame = show_not_found_frame()
            
                while config.CAMERA_ACTIVE:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + not_found_frame + b'\r\n')
                    time.sleep(0.5)
                continue  # 回到最外層 while，等待相機重新開啟
            
            # --- 儲存相機實例(需要檢查有相機後才可呼叫) ---
            config.CAMERA_INSTANCE = CameraManager.open_camera(camera_index, backend)

            # --- 如果沒有相機實例或無法開啟相機 ---
            if not config.CAMERA_INSTANCE or not config.CAMERA_INSTANCE.isOpened():
                error_frame = show_open_failed_frame()
                
                while config.CAMERA_ACTIVE:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                    time.sleep(0.5)
                continue

            # ===== 主串流迴圈 =====
            frame_count = 0 # 影片幀數
            last_results = [] # 最新結果
            last_names = set() # 辨識到的人臉集合

            while config.CAMERA_ACTIVE:
                ret, frame = config.CAMERA_INSTANCE.read() # 讀取影像
                if not ret:
                    break
                frame_count += 1 # 計算影片幀數
                # --- 如果幀數好是 FACE_RECOGNITION_FRAME_SKIP 的倍數時，才執行辨識 ---
                if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                    results = face_recognizer.recognize_face_from_frame(db_manager, frame, use_cache=True)
                    last_results = results
                    frame_count = 0
                else:
                    # 紀錄上一個畫面，以便保持有畫面有可以顯示
                    results = last_results

                # --- 只在「辨識到的人臉名稱有變化」時，才推送辨識訊息到前端 ---
                current_names = set([r['name'] for r in results]) # 辨識到的人臉集合
                # 將兩個集合比較，如果內容不同則代表是新結果
                if current_names != last_names:
                    face_message(results, frame) # 推送及時通知
                    # 把 last_names 更新成這一幀的 current_names，以便下次比對
                    last_names = current_names

                draw_frame(results, frame) # 劃出辨識框
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as e:
            print(f"[錯誤] 影像串流處理失敗: {e}")
        finally:
            if config.CAMERA_INSTANCE is not None:
                CameraManager.clean_camera(config.CAMERA_INSTANCE)
                config.CAMERA_INSTANCE = None
                print("[系統] 攝影機已關閉並釋放資源")
        # 這裡不 return，直接回到最外層 while，等待相機重新開啟