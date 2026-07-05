from modules import db_manager, face_recognizer
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
from modules.video_streaming.showFrame import (show_cameraOff_frame, show_resultFrame)
from modules.video_streaming.faceMessage import face_message

""" ===== 這裡放影像串流的相機處理邏輯 """

# ===== 相機開啟前，持續顯示「已關閉畫面」 =====
def wait_camera_open():
    while not config.CAMERA_ACTIVE:
        black_frame = show_cameraOff_frame()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + black_frame + b'\r\n')
        time.sleep(0.5)
        if RPI:
            rpi_time_check() # 樹梅派元件延遲關閉檢查


# ===== 尋找+開啟相機 =====
def find_and_open_camera():
    # --- 取得相機索引、可用參數 ---
    backends = CameraManager.get_camera_config()
    camera_index, backend = CameraManager.find_camera(backends)
    # --- 如果沒有找到相機或可用參數，顯示無法找到相機的畫面 ---
    if camera_index is None or backend is None:
        return False, "Camera Not Found"
    
    # --- 儲存相機實例(需要檢查有相機後才可呼叫) ---
    config.CAMERA_INSTANCE = CameraManager.open_camera(camera_index, backend)
    # --- 如果沒有相機實例或無法開啟相機 ---
    if not config.CAMERA_INSTANCE or not config.CAMERA_INSTANCE.isOpened():
        return False, "Camera Open Failed"
    
    return True, "Camera is Open"
    
# ===== 人臉辨識影像串流 =====
def stream_camera():
    frame_count = 0  # 影片幀數
    last_results = []  # 最新結果
    last_names = set()  # 辨識到的人臉集合

    while config.CAMERA_ACTIVE:
        ret, frame = config.CAMERA_INSTANCE.read()  # 讀取影像
        if not ret:
            break
        frame_count += 1  # 計算影片幀數

        # ----- 人臉辨識部分(只在警報關閉時啟用) -----
        # --- 如果幀數好是 FACE_RECOGNITION_FRAME_SKIP 的倍數時，才執行辨識 ---
        if config.fire_status_is_open == False:
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                log.info("人臉辨識中...")
                results = face_recognizer.recognize_face_from_frame(
                    db_manager, frame, use_cache=True)
                last_results = results
                frame_count = 0
            else:
                # 紀錄上一個畫面，以便保持有畫面有可以顯示
                results = last_results

            # --- 只在「辨識到的人臉名稱有變化」時，才推送辨識訊息到前端 ---
            current_names = set([r['name']
                                 for r in results])  # 辨識到的人臉集合
            # 將兩個集合比較，如果內容不同則代表是新結果
            if current_names != last_names:
                log.info("發現新人臉! 正在判定結果...")
                face_message(results, frame)  # 推送及時通知
                # 把 last_names 更新成這一幀的 current_names，以便下次比對
            last_names = current_names
            show_resultFrame(results, frame)  # 劃出辨識框

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        if RPI:
            rpi_time_check()  # 樹梅派元件延遲關閉檢查

# ===== 清空相機資源 =====
def cleanup_camera():
    if config.CAMERA_INSTANCE is not None:
        CameraManager.clean_camera(config.CAMERA_INSTANCE)
        config.CAMERA_INSTANCE = None
        log.info("[系統] 攝影機已關閉並釋放資源 by video_streaming")
