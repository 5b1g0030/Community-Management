from modules import socketio, db_manager, face_recognizer, recognition_Logs, pick_up
from utils.camera_utils import CameraManager
from modules.config import FACE_RECOGNITION_FRAME_SKIP
import modules.config as config # 給相機同步修改用
from modules.resberryPi import rpi_time_check # 樹梅派函式
# import numpy as np
import cv2
# import os
# from datetime import datetime
import time
from modules.config import RPI
# import threading
import logging as log
from modules.video_streaming.showFrame import (create_message_frame, show_resultFrame)
from modules.video_streaming.video_camera import (wait_camera_open, find_and_open_camera,
                                                   stream_camera, cleanup_camera)


# ===== 影像串流&推送辨識訊息 =====
def gen_frames():
    while True:
        # --- 等待相機開啟期間，顯示黑畫面 ---
        for frame in wait_camera_open():
            yield frame
        
        # ===== 影像串流 =====
        try:
            # ----- 嘗試尋找、開啟相機 -----
            log.info("嘗試尋找、開啟相機...")
            success, message = find_and_open_camera()
            if not success:
                not_found_frame = create_message_frame(message)
                while config.CAMERA_ACTIVE:
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + not_found_frame + b'\r\n')
                        time.sleep(0.5)
                        if RPI:
                            rpi_time_check() # 樹梅派元件延遲關閉檢查
                continue  # 回到最外層 while，等待相機重新開啟

            # ===== 主串流迴圈 =====
            log.info("進入主串流迴圈...")
            # 把畫面資料接力送出去
            for frame in stream_camera():
                yield frame
            

        except Exception as e:
            log.error(f"[錯誤] 影像串流處理失敗: {e} by video_streaming")
        finally:
            cleanup_camera()
        # 這裡不 return，直接回到最外層 while，等待相機重新開啟


# ***** 預計要刪除 ******
# ===== 取貨專用影像串流（辨識但不儲存、不推送通知） =====
def pick_up_frame():
    """
    取貨專用串流：
    - 執行人臉辨識並繪製框
    - 儲存辨識紀錄
    - 不推送通知
    - 辨識到人物後查詢包裹櫃號
    - 如有包裹則推送開櫃訊息並結束串流
    """
    print("[取貨串流] 開始取貨串流")
    
    # 設定取貨串流為啟用狀態
    config.PICKUP_STREAM_ACTIVE = True
    config.PICKUP_FACE_DETECTED = False
    
    try:
        # --- 取得相機索引、可用參數 ---
        backends = CameraManager.get_camera_config()
        camera_index, backend = CameraManager.find_camera(backends)

        # --- 如果沒有找到相機或可用參數 ---
        if camera_index is None or backend is None:
            not_found_frame = create_message_frame("Camera Not Found")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + not_found_frame + b'\r\n')
            return
        
        # --- 開啟相機 ---
        camera = CameraManager.open_camera(camera_index, backend)

        # --- 如果無法開啟相機 ---
        if not camera or not camera.isOpened():
            error_frame = create_message_frame("Camera Open Failed")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
            return

        # ===== 取貨串流迴圈 =====
        frame_count = 0 # 畫面幀數
        last_results = [] # 最新辨識結果

        # 開始辨識
        while config.PICKUP_STREAM_ACTIVE:
            ret, frame = camera.read()
            if not ret:
                break
            
            frame_count += 1
            
            # --- 每 N 幀執行一次辨識 ---
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                results = face_recognizer.recognize_face_from_frame(
                    db_manager, frame, use_cache=True
                )
                last_results = results
                frame_count = 0
                
                # --- 檢查是否辨識到已知人臉（不包含未知、訪客） ---
                for result in results:
                    name = result['name']
                    # 過濾掉: 空值、訪客、未知的辨識結果
                    if name and name != '未知' and not name.startswith('visitor_'):
                        print(f"[取貨串流] 辨識到住戶：{name} by video_streaming")
                        
                        # 查詢是否有包裹
                        locker_number = pick_up.get_locker_by_name(name)
                        
                        if locker_number:
                            # 有包裹，推送開櫃訊息
                            print(f"[取貨串流] {name} 有包裹在 {locker_number} 號櫃 by video_streaming")
                            socketio.emit('pickup_success', {
                                'type': 'pickup',
                                'name': name,
                                'locker_number': locker_number,
                                'message': f'{locker_number} 號取貨櫃已開啟，請立即取貨'
                            })

                            face_id = result.get('id')
                            conf = float(result.get('confidence', 0.0))
                            if face_id:
                                recognition_Logs.save_recognition_log("取貨", f"{name}已到{locker_number}號櫃取貨", face_id, conf)
                            
                            # 清除櫃位資料
                            pick_up.clear_locker(locker_number)
                            print(f"[取貨串流] {locker_number} 號櫃已清除 by video_streaming")
                            
                            # 【操作對應馬達開啟】
                            
                            # 標記已偵測到並準備結束
                            config.PICKUP_FACE_DETECTED = True
                            config.PICKUP_STREAM_ACTIVE = False
                            break
                        else:
                            # 無包裹，繼續辨識
                            print(f"[取貨串流] {name} 沒有登記包裹，繼續辨識 by video_streaming")
            else:
                results = last_results

            # --- 繪製辨識框 ---
            show_resultFrame(results, frame)
            
            # --- 編碼並傳送影像 ---
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # --- 如果辨識到人臉且有包裹，再傳送最後一幀後結束 ---
            if config.PICKUP_FACE_DETECTED:
                time.sleep(0.5)  # 讓前端顯示最後一幀
                break
    except Exception as e:
        print(f"[錯誤] 取貨串流處理失敗: {e} by video_streaming")
    finally:
        if camera is not None:
            CameraManager.clean_camera(camera)
            print("[取貨串流] 相機資源已釋放 by video_streaming")
        
        config.PICKUP_STREAM_ACTIVE = False
        print("[取貨串流] 取貨串流已結束 by video_streaming")