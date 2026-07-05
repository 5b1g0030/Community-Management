from modules import socketio, db_manager, recognition_Logs, visitor_Booking
from modules.faceRecognition import refresh_face_cache
import modules.config as config  # 給相機同步修改用
from modules.resberryPi import open_door_and_rbgled  # 樹梅派函式
import cv2
import os
from datetime import datetime
# import time
# from modules.config import RPI
import logging as log # 除錯用


""" ===== 這裡放人臉判斷+訊息分送邏輯+紀錄資料流程 ===== """

# ===== 儲存辨識紀錄流程 =====
def save_log(messageType, message, result):
    # 取得人臉索引+信心值
    if messageType == "未知":
        face_id = None
        conf = None
    else:
        face_id = result.get('id')
        conf = float(result.get('confidence', 0.0))
    # 儲存紀錄
    recognition_Logs.save_recognition_log(
        messageType,
        message,
        face_id,
        conf
    )

# ===== 發送辨識訊息 =====
def send_recognition_message(message):
    log.info(f"[推送辨識訊息] => {message}")
    socketio.emit('recognition', {
            'type': 'recognition',
            'message': message
        })

# ===== 樹莓派-不開門參數設定 ======
def deny_open_door():
    config.door_open = False  # 不開門
    config.rgbled_color = 'red'  # LED紅色

# ===== 樹莓派-開門參數設定 ======
def allow_open_door():
    config.door_open = True
    config.rgbled_color = 'green'

# ===== 處理訪客 =====
def process_visitor(name, result):
    # 查詢對應的住戶名稱
    log.info("[推送辨識訊息] 查詢對應的住戶名稱 by video_streaming")
    username = visitor_Booking.get_visitor_by_face_name(name)

    if username:
        # 樹梅派操作
        allow_open_door()

        # 推送訊息
        send_recognition_message(message=f'偵測到{username}住戶的訪客已到大門')

        # --- 儲存辨識紀錄 ---
        save_log(messageType="訪客", message=f"{username}住戶的訪客已到大門", result=result)

        # 立即清除訪客人臉資料
        success = visitor_Booking.clear_visitor_face_data(name)
        if success:
            # 重新整理快取
            refresh_face_cache(db_manager)
            log.info(f"[系統] 訪客 {name} 已辨識並清除人臉資料 by video_streaming")
        else:
            log.error(f"[系統] 訪客 {name} 人臉資料清除失敗 by video_streaming")

# ===== 處理已知(住戶) =====
def process_resident(name, result):
    # 樹梅派操作
    allow_open_door()

    # 推送訊息
    send_recognition_message(message=f'偵測到{name}住戶來到大門')

    # --- 儲存辨識紀錄 ---
    save_log(messageType="住戶", message=f"住戶{name}已來到大門", result=result)

# ===== 處理未知 =====
def process_unknown(frame):
    log.info("[推送辨識訊息] 辨識為未知 by video_streaming")
    # 樹梅派操作
    deny_open_door()

    # 推送訊息
    send_recognition_message(message='偵測到未知人物')
    
    # --- 儲存辨識紀錄 ---
    save_log(messageType="未知", message="偵測到未知人物")

    # 儲存暫存圖片
    temp_dir = os.path.join('static', 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
    cv2.imwrite(img_path, frame)

# ===== 推送辨識訊息(已知, 未知, 訪客) =====
def face_message(results, frame):
    for result in results:
        name = result['name']
        log.info(f"[推送辨識訊息] 檢查是否為訪客? name: {name} by video_streaming")
        # ----- 檢查是否為訪客 -----
        if name and name.startswith('visitor_'):
            process_visitor(name, result)

            # ----- 如果不是「未知」且 name 不為空，則顯示名字 -----
        elif name and name != '未知':
            process_resident(name, result)

        # ----- 如果是「未知」，顯示未知人物 -----
        elif name == '未知':
            process_unknown(frame)

        # ===== 樹梅派操作 =====
        # 當下達開門指令 and 門的上一次狀態為關
        open_door_and_rbgled()
        
