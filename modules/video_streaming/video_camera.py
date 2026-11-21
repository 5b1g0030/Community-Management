from modules import db_manager, face_recognizer, sio
from utils.camera_utils import CameraManager
from modules.config import FACE_RECOGNITION_FRAME_SKIP
import modules.config as config 
from modules.resberryPi import rpi_time_check 
import cv2
import time
import asyncio # 新增 asyncio 以支援 Quart 非同步作業[cite: 1]
from modules.config import RPI
import logging as log
from modules.video_streaming.showFrame import (show_cameraOff_frame, show_resultFrame)
from modules.video_streaming.faceMessage import face_message

""" ===== 這裡放影像串流的相機處理邏輯 ====="""

# ===== 相機開啟前，持續顯示「已關閉畫面」 =====
async def wait_camera_open(): # 修改為 async def 產生器[cite: 1]
    while not config.CAMERA_ACTIVE:
        black_frame = show_cameraOff_frame()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + black_frame + b'\r\n')
        await asyncio.sleep(0.5) # 將 time.sleep 改為 await asyncio.sleep，避免阻塞事件迴圈[cite: 1]
        if RPI:
            await rpi_time_check() 

# ===== 尋找+開啟相機 (負責硬體 I/O，維持一般函式即可) =====
def find_and_open_camera():
    backends = CameraManager.get_camera_config()
    camera_index, backend = CameraManager.find_camera(backends)
    if camera_index is None or backend is None:
        return False, "Camera Not Found"
    
    config.CAMERA_INSTANCE = CameraManager.open_camera(camera_index, backend)
    if not config.CAMERA_INSTANCE or not config.CAMERA_INSTANCE.isOpened():
        return False, "Camera Open Failed"
    
    return True, "Camera is Open"
    
# ===== 人臉辨識影像串流 =====
async def stream_camera(): # 修改為 async def 產生器[cite: 1]
    frame_count = 0  
    last_results = []  
    last_names = set()  

    # 區域偵測
    # 引入偵測主模組、警報事件紀錄模組
    from modules import intrusion_monitor, intrusion_event_log
    intrusion_monitor.reset_tracking() # 重置追蹤器，避免上一個串流的追蹤資訊影響新串流
    intrusion_last_error = None # 記錄上一個錯誤訊息，避免重複推送相同錯誤訊息

    while config.CAMERA_ACTIVE:
        # log.info("進入影像串流...")
        ret, frame = config.CAMERA_INSTANCE.read()  
        if not ret:
            break
        frame_count += 1  

        if config.fire_status_is_open == False:
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                log.info("人臉辨識中...")
                # 建議：若 face_recognizer 運算極度耗時，未來可包裝為 asyncio.to_thread 執行
                results = await face_recognizer.recognize_face_from_frame(
                    db_manager, frame, use_cache=True)
                last_results = results
                frame_count = 0
            else:
                results = last_results

            current_names = set([r['name'] for r in results])  
            if current_names != last_names:
                log.info("發現新人臉! 正在判定結果...")
                await face_message(results, frame)  
            last_names = current_names
            show_resultFrame(results, frame)  

        """
                    區域偵測-影像分析
                """
                # 以原始影像進行禁止區域偵測，避免人臉框影響 YOLO。
                # 發生模型錯誤時不讓既有的人臉辨識/影像串流中斷。
        try:
                    frame, intrusion_alert = intrusion_monitor.process_frame(frame)
                    if intrusion_alert is not None:
                        await sio.emit('intrusion_alert', intrusion_alert)
                        try:
                            intrusion_event_log.add(intrusion_alert)
                        except Exception as log_exc:
                            print('[區域入侵] 事件紀錄寫入失敗:', log_exc)
                        print('[區域入侵]', intrusion_alert['message'])
                    intrusion_last_error = None
        except Exception as exc:
                    err = str(exc)
                    if intrusion_last_error != err:
                        print('[區域入侵] 偵測模組錯誤:', err)
                        await sio.emit('intrusion_error', {'message': err})
                        intrusion_last_error = err

        """
            區域偵測-影像分析結束
        """

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        if RPI:
            await rpi_time_check()  
            
        await asyncio.sleep(0) # 加入 await asyncio.sleep(0) 主動讓出控制權給 Quart 處理其他 HTTP 請求[cite: 1]

# ===== 清空相機資源 =====
def cleanup_camera():
    if config.CAMERA_INSTANCE is not None:
        CameraManager.clean_camera(config.CAMERA_INSTANCE)
        config.CAMERA_INSTANCE = None
        log.info("[系統] 攝影機已關閉並釋放資源 by video_streaming")