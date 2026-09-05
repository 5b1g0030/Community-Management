from modules import socketio, db_manager, face_recognizer, recognition_Logs, pick_up
from utils.camera_utils import CameraManager
from modules.config import FACE_RECOGNITION_FRAME_SKIP
import modules.config as config 
from modules.resberryPi import rpi_time_check 
import cv2
import time
import asyncio # 新增 asyncio 以支援 Quart 非同步作業[cite: 2]
from modules.config import RPI
import logging as log
from modules.video_streaming.showFrame import (create_message_frame, show_resultFrame)
# 注意：這裡假設引入的 functions 都已經改為上方的 async 版本
from modules.video_streaming.video_camera import (wait_camera_open, find_and_open_camera,
                                                   stream_camera, cleanup_camera)

# ===== 影像串流&推送辨識訊息 =====
async def gen_frames(): # 修改為 async def[cite: 2]
    while True:
        # --- 等待相機開啟期間，顯示黑畫面 ---
        async for frame in wait_camera_open(): # 使用 async for 迭代非同步產生器[cite: 2]
            yield frame
        
        try:
            log.info("嘗試尋找、開啟相機...")
            success, message = find_and_open_camera()
            if not success:
                not_found_frame = create_message_frame(message)
                while config.CAMERA_ACTIVE:
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + not_found_frame + b'\r\n')
                        await asyncio.sleep(0.5) # 將 time.sleep 改為 await asyncio.sleep[cite: 2]
                        if RPI:
                            await rpi_time_check() 
                continue  

            log.info("進入主串流迴圈...")
            async for frame in stream_camera(): # 使用 async for 迭代非同步產生器[cite: 2]
                yield frame

        except Exception as e:
            log.error(f"[錯誤] 影像串流處理失敗: {e} by video_streaming")
        finally:
            cleanup_camera()


# ===== 取貨專用影像串流 =====
async def pick_up_frame(): # 修改為 async def[cite: 2]
    log.info("[取貨串流] 開始取貨串流")
    config.PICKUP_STREAM_ACTIVE = True
    config.PICKUP_FACE_DETECTED = False
    
    try:
        backends = CameraManager.get_camera_config()
        camera_index, backend = CameraManager.find_camera(backends)

        if camera_index is None or backend is None:
            not_found_frame = create_message_frame("Camera Not Found")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + not_found_frame + b'\r\n')
            return
        
        camera = CameraManager.open_camera(camera_index, backend)

        if not camera or not camera.isOpened():
            error_frame = create_message_frame("Camera Open Failed")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
            return

        frame_count = 0 
        last_results = [] 

        while config.PICKUP_STREAM_ACTIVE:
            ret, frame = camera.read()
            if not ret:
                break
            
            frame_count += 1
            
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                results = face_recognizer.recognize_face_from_frame(
                    db_manager, frame, use_cache=True
                )
                last_results = results
                frame_count = 0
                
                for result in results:
                    name = result['name']
                    if name and name != '未知' and not name.startswith('visitor_'):
                        log.info(f"[取貨串流] 辨識到住戶：{name} by video_streaming")
                        locker_number = await pick_up.get_locker_by_name(name)
                        
                        if locker_number:
                            log.info(f"[取貨串流] {name} 有包裹在 {locker_number} 號櫃 by video_streaming")
                            # 若 socketio 也是非同步版本（如 quart-socketio），這裡可能需要加上 await
                            socketio.emit('pickup_success', {
                                'type': 'pickup',
                                'name': name,
                                'locker_number': locker_number,
                                'message': f'{locker_number} 號取貨櫃已開啟，請立即取貨'
                            })

                            face_id = result.get('id')
                            conf = float(result.get('confidence', 0.0))
                            if face_id:
                                await recognition_Logs.save_recognition_log("取貨", f"{name}已到{locker_number}號櫃取貨", face_id, conf)
                            
                            await pick_up.clear_locker(locker_number)
                            log.info(f"[取貨串流] {locker_number} 號櫃已清除 by video_streaming")
                            
                            config.PICKUP_FACE_DETECTED = True
                            config.PICKUP_STREAM_ACTIVE = False
                            break
                        else:
                            log.info(f"[取貨串流] {name} 沒有登記包裹，繼續辨識 by video_streaming")
            else:
                results = last_results

            show_resultFrame(results, frame)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            if config.PICKUP_FACE_DETECTED:
                await asyncio.sleep(0.5)  # 將 time.sleep 改為 await asyncio.sleep[cite: 2]
                break
                
            await asyncio.sleep(0) # 防止 While 迴圈獨佔 CPU，保持 Quart 路由暢通[cite: 2]
            
    except Exception as e:
        log.error(f"[錯誤] 取貨串流處理失敗: {e} by video_streaming")
    finally:
        if camera is not None:
            CameraManager.clean_camera(camera)
            log.info("[取貨串流] 相機資源已釋放 by video_streaming")
        
        config.PICKUP_STREAM_ACTIVE = False
        log.info("[取貨串流] 取貨串流已結束 by video_streaming")