# 【修改 1】從 modules 引入修改後的 sio 或其他非同步變數（若原本的 socketio 已移除，此處要確保引入正確）
from modules import db_manager, recognition_Logs, visitor_Booking
from modules.face.face_cache import refresh_face_cache
import modules.config as config  # 給相機同步修改用
from modules.resberryPi import open_door_and_rbgled  # 樹梅派函式
from utils.response_utils import send_recognition_message
import cv2
import os
from datetime import datetime
import logging as log # 除錯用
import asyncio # 【修改 2】匯入 asyncio 處理非同步背景轉執行緒
from modules.config import RPI


""" ===== 這裡放人臉判斷+訊息分送邏輯+紀錄資料流程 ===== """

# ===== 儲存辨識紀錄流程 =====
# 【修改 3】改為 async def，並在呼叫非同步的 save_recognition_log 時加上 await
async def save_log(messageType, message, result=None):
    # 取得人臉索引+信心值
    if messageType == "未知":
        face_id = None
        conf = None
    else:
        if result is None: return # 確保result不是空值
        face_id = result.get('id')
        conf = float(result.get('confidence', 0.0))
    
    # 儲存紀錄（因為在上一動已改為 async，此處必須 await）
    await recognition_Logs.save_recognition_log(
        messageType,
        message,
        face_id,
        conf
    )


# ===== 樹莓派-不開門參數設定 ======
def deny_open_door():
    config.door_open = False  # 不開門
    config.rgbled_color = 'red'  # LED紅色

# ===== 樹莓派-開門參數設定 ======
def allow_open_door():
    config.door_open = True
    config.rgbled_color = 'green'

# ===== 處理訪客 =====
# 【修改 4】改為 async def
async def process_visitor(name, result):
    # 查詢對應的住戶名稱（若資料庫查詢為同步，可用 asyncio.to_thread 包裝避免阻塞）
    log.info("[推送辨識訊息] 查詢對應的住戶名稱 by video_streaming")
    username = await asyncio.to_thread(visitor_Booking.get_visitor_by_face_name, name)

    if username:
        # 樹梅派操作
        allow_open_door()

        # 推送訊息（非同步，需 await）
        await send_recognition_message(message=f'偵測到{username}住戶的訪客已到大門')

        # --- 儲存辨識紀錄 ---
        await save_log(messageType="訪客", message=f"{username}住戶的訪客已到大門", result=result)

        # 立即清除訪客人臉資料（同步 IO 包裝）
        success = await asyncio.to_thread(visitor_Booking.clear_visitor_face_data, name)
        if success:
            # 重新整理快取
            await asyncio.to_thread(refresh_face_cache, db_manager)
            log.info(f"[系統] 訪客 {name} 已辨識並清除人臉資料 by video_streaming")
        else:
            log.error(f"[系統] 訪客 {name} 人臉資料清除失敗 by video_streaming")

# ===== 處理已知(住戶) =====
# 【修改 5】改為 async def
async def process_resident(name, result):
    log.info("處理已知")
    # 樹梅派操作
    allow_open_door()

    # 推送訊息（非同步，需 await）
    await send_recognition_message(message=f'偵測到{name}住戶來到大門')

    # --- 儲存辨識紀錄 ---
    await save_log(messageType="住戶", message=f"住戶{name}已來到大門", result=result)

# ===== 處理未知 =====
# 【修改 6】改為 async def
async def process_unknown(frame):
    log.info("[推送辨識訊息] 辨識為未知 by video_streaming")
    # 樹梅派操作
    deny_open_door()

    # 推送訊息（非同步，需 await）
    await send_recognition_message(message='偵測到未知人物')
    
    # --- 儲存辨識紀錄 ---
    await save_log(messageType="未知", message="偵測到未知人物")

    # 儲存暫存圖片（檔案寫入屬 I/O 阻塞，包進 asyncio.to_thread）
    def _save_temp_image():
        temp_dir = os.path.join('static', 'temp')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
        cv2.imwrite(img_path, frame)
        return img_path

    await asyncio.to_thread(_save_temp_image)

# ===== 推送辨識訊息(已知, 未知, 訪客) =====
# 【修改 7】整個流程入口改為 async def，讓內部所有的 await 可以順利執行
async def face_message(results, frame):
    log.info("已進入 face_message ...")
    for result in results:
        name = result['name']
        log.info(f"[推送辨識訊息] 檢查是否為訪客? name: {name} by video_streaming")
        
        # ----- 檢查是否為訪客 -----
        if name and name.startswith('visitor_'):
            await process_visitor(name, result)

        # ----- 如果不是「未知」且 name 不為空，則顯示名字 -----
        elif name and name != '未知':
            await process_resident(name, result)

        # ----- 如果是「未知」，顯示未知人物 -----
        elif name == '未知':
            await process_unknown(frame)

        # ===== 樹梅派操作 =====
        # 當下達開門指令 and 門的上一次狀態為關
        # (假設 open_door_and_rbgled 若為一般 GPIO 脈衝，通常很短，若會卡住也可考慮放入 thread)
        if RPI:
            await open_door_and_rbgled()