""" Quart 網頁後端 """

import asyncio
from quart import Quart, render_template, request, jsonify, Response, redirect, session
from modules.face.face_cache import refresh_face_cache
from modules.face.image_processor import validate_image_file, process_uploaded_image
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random
from modules.config import RPI
import modules.config as config  # 給相機做同步修改
from modules.video_streaming.video_streaming import gen_frames, pick_up_frame
from modules import app, quart_app, db_manager, face_recognizer, user, recognition_Logs, visitor_Booking, pick_up
from modules.resberryPi import rpi_to_dht22, rpi_to_mq135, rpi_to_buzzer, rpi_to_redled, rpi_to_servo
from modules.cameraController import set_camera_state
from modules.video_streaming.faceMessage import save_log
from utils.response_utils import *
from utils.directory_utils import make_new_dir
import cv2
import logging as log

# app = Quart(__name__)
# app.secret_key = 'MySecretKey950907' 

# ===== 管理者端 =====
@quart_app.route('/manager')
async def manager():
    if session.get('role') != '管理員':
        return redirect('/login') 
    return await render_template('manager.html')

# ===== 登入(首頁) =====
@quart_app.route('/')

@quart_app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'GET':
        return await render_template('login.html')
    
    form = await request.form
    username = form.get('username')
    password = form.get('password')

    if not username or not password:
        return error_response('請輸入使用者名稱和密碼')
    
    role = user.login_user(username, password)
    log.info(f"login_user returned role: {repr(role)}")
    if role:
        session['username'] = username
        session['role'] = role

        log.info('根據身分導向不同頁面 By app')
        if role == '管理員':
            return success_response('登入成功', redirect='/manager')
        else:
            return success_response('登入成功', redirect='/residents')
    else:
        return error_response('使用者名稱或密碼錯誤', status=401)

# ===== 註冊 =====
@quart_app.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'GET':
        return await render_template('register.html')
    
    form = await request.form
    username = form.get('username')
    password = form.get('password')
    confirm_password = form.get('confirm_password')
    role = form.get('role', '住戶')

    if not username or not password or not confirm_password:
        return error_response('所有欄位都需要填寫')
    
    if role not in ('住戶', '管理員'):
        return error_response('身分選擇不正確')

    if len(username.strip()) < 3:
        return error_response('使用者名稱至少要三字元')
    
    if len(password) < 6:
        return error_response('密碼需要超過6字元')
    
    if password != confirm_password:
        return error_response('兩次密碼不相同')
    
    success, message = user.register_user(username, password, role)

    if success:
        return success_response(message, redirect='/login')
    else:
        return error_response(message)

# ===== 登出 =====
@quart_app.route('/logout')
async def logout():
    session.clear()
    return redirect('/login')

# ===== 鏡頭影像顯示 =====
@quart_app.route('/video_feed')
async def video_feed():
    # 確保 gen_frames 是 async generator 或相容的串流格式
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===== 開啟相機 API =====
@quart_app.route('/start_camera', methods=['POST'])
async def start_camera():
    with config.CAMERA_LOCK:
        if config.CAMERA_ACTIVE:
            return success_response('相機已經在運行中')
        config.CAMERA_ACTIVE = True
    log.info("[系統] 相機已開啟")
    return success_response('相機已開啟')

# ===== 關閉相機 API =====
@quart_app.route('/stop_camera', methods=['POST'])
async def stop_camera():
    try:
        with config.CAMERA_LOCK:
            if not config.CAMERA_ACTIVE:
                return success_response('相機已經關閉')
            config.CAMERA_ACTIVE = False
            
            if config.CAMERA_INSTANCE is not None:
                try:
                    CameraManager.clean_camera(config.CAMERA_INSTANCE)
                    log.info("[系統] 已釋放攝影機資源")
                except Exception as e:
                    log.warning(f"[警告] 釋放攝影機資源時發生錯誤: {e}")
                finally:
                    config.CAMERA_INSTANCE = None
        
        log.info("[系統] 相機已關閉")
        await asyncio.sleep(0.5)  # 替換 time.sleep 避免阻塞 event loop
        return success_response('相機已關閉')
    
    except Exception as e:
        log.error(f"[錯誤] 關閉相機失敗: {e}")
        return error_response(f'關閉失敗: {str(e)}', status=500)

# ===== 取得相機狀態 API =====
@quart_app.route('/camera_status', methods=['GET'])
async def camera_status():
    return jsonify({'active': config.CAMERA_ACTIVE}), 200

# ===== 加入人臉到資料庫 =====
@quart_app.route('/add_face', methods=['POST'])
async def add_face():
    try:
        form = await request.form
        files = await request.files
        name = form.get('name')
        image_file = files.get('image')
        
        if not name or not image_file:
            return error_response('請提供姓名和照片')
        
        temp_dir = os.path.join('static', 'temp_uploads')
        make_new_dir(temp_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{name}_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        
        await image_file.save(temp_path)  # Quart 檔案儲存需 await
        
        result = face_recognizer.register_faces(name, temp_dir, [filename])
        
        if result['success']:
            refresh_face_cache(db_manager)
            log.info(f"[系統] 已新增 {name} 並重新整理快取")
            return success_response(result['message'])
        else:
            return error_response(result['message'])
    
    except Exception as e:
        return error_response(f'錯誤: {str(e)}')

# ===== 測試辨識人臉 =====
@quart_app.route('/test_face', methods=['POST'])
async def test_face():
    temp_path = None
    try:
        log.info("[測試辨識] 開始處理請求")
        
        camera_was_active = config.CAMERA_ACTIVE
        if camera_was_active:
            set_camera_state(False)
            log.info("[測試辨識] 已自動關閉相機")
            await asyncio.sleep(1.0)
        
        files = await request.files
        image_file = files.get('image')
        
        valid, error = validate_image_file(image_file)
        if not valid:
            return error_response(error)

        temp_dir = os.path.join('static', 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'test_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        
        img = process_uploaded_image(image_file, temp_path)
                
        log.info("[測試辨識] 開始辨識人臉...")
        result = face_recognizer.recognize_face(temp_path)
        log.info(f"[測試辨識] 辨識結果：{result}")
        
        frist_result = result['results'][0]
        name = frist_result['name']
        log.info(f"[測試辨識] 辨識結果：{name}")

        if name and name.startswith('visitor_'):
            username = visitor_Booking.get_visitor_by_face_name(name)
            send_recognition_message(f'偵測到{username}住戶的訪客已到大門')

            face_id = frist_result.get('id')
            confidence_str = frist_result.get('confidence', '0.0%')
            conf = float(confidence_str.strip('%')) / 100
            if face_id:
                recognition_Logs.save_recognition_log("訪客", f"{username}住戶的訪客已到大門", face_id, conf)
                log.info("辨識紀錄已儲存 by app")
                        
            success = visitor_Booking.clear_visitor_face_data(name)   
            if success:
                refresh_face_cache(db_manager)
                log.info(f"[系統] 訪客 {name} 已辨識並清除人臉資料")
            else:
                log.error(f"[系統] 訪客 {name} 人臉資料清除失敗")

        elif name == "未知":
            send_recognition_message('偵測到未知人物')
            save_log("未知", "偵測到未知人物")
            log.info("辨識紀錄已儲存 by app")
                    
            temp_dir = os.path.join('static', 'temp')
            make_new_dir(temp_dir)
            
            try:
                import numpy as np
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                img_path = os.path.join(temp_dir, f'unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg')
                cv2.imwrite(img_path, img_cv)
                print(f"[測試辨識] 未知人物圖片已儲存到：{img_path}")
            except Exception as save_error:
                print(f"[測試辨識] 儲存未知人物圖片失敗：{save_error}")

        elif name and name != "未知":
            send_recognition_message(f'偵測到{name}住戶來到大門')
            
            face_id = frist_result.get('id')
            log.info(f"人臉索引: {face_id}")
            confidence_str = frist_result.get('confidence', '0.0%')
            conf = float(confidence_str.strip('%')) / 100
            if face_id:
                recognition_Logs.save_recognition_log("住戶", f"住戶{name}已來到大門", face_id, conf)
                log.info("辨識紀錄已儲存 by app")

        if result['success']:
            return success_response(result['message'], results=result['results'])
        else:
            return error_response(result['message'])
    
    except Exception as e:        
        log.error(f"[測試辨識] 發生未預期的錯誤：{e}")
        import traceback
        traceback.print_exc()
        return error_response(f'系統錯誤：{str(e)}', status=500)
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                log.info(f"[測試辨識] 已刪除臨時檔案：{temp_path}")
        except Exception as cleanup_error:
            log.error(f"[測試辨識] 清理臨時檔案失敗：{cleanup_error}")

# ===== 取得人臉資料 =====
@quart_app.route('/get_faces')
async def get_faces():
    try:
        conn, cursor = db_manager.get_db_connection()
        cursor.execute("SELECT id, name, created_date, updated_date FROM face_recognition")
        faces = cursor.fetchall()
        conn.close()
        
        face_list = [{'id': face[0], 'name': face[1], 'created_date': face[2], 'updated_date': face[3]} for face in faces]
        return success_response(faces=face_list)
    except Exception as e:
        return error_response(f'錯誤: {str(e)}')

# ===== 刪除人臉資料 =====
@quart_app.route('/api/delete_faces', methods=['POST'])
async def delete_faces():
    try:
        data = await request.get_json()
        face_ids = data.get('ids', [])

        if not face_ids:
            return error_response('未提供需刪除的 ID')

        conn, cursor = db_manager.get_db_connection()
        placeholders = ','.join(['?'] * len(face_ids))
        cursor.execute(f"DELETE FROM face_recognition WHERE id IN ({placeholders})", tuple(face_ids))
        conn.commit()
        
        deleted_count = cursor.rowcount
        conn.close()

        refresh_face_cache(db_manager)
        return success_response(f'成功刪除 {deleted_count} 筆記錄')
    except Exception as e:
        log.error(f"[錯誤] 刪除人臉失敗: {e}")
        return error_response(f'刪除失敗: {str(e)}', status=500)

# ===== 取得辨識紀錄資料 (DataTables 篩選專用) =====
@quart_app.route('/api/recognition_logs')
async def get_recognition_logs_datatables():
    logs = recognition_Logs.get_all_recognition_logs()
    
    data = []
    for item in logs:
        face_id = item['face_id'] if item['face_id'] is not None else '無'
        confidence = f"{item['confidence']:.1f}" if item['confidence'] is not None else '無'
        
        data.append([
            item['id'],
            item['created_date'],
            item['event_type'],
            item['event_message'],
            face_id,
            confidence
        ])
    
    response = jsonify({'data': data})
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

# ===== 住戶頁面路由 =====
@quart_app.route('/residents')
async def residents():
    if not session.get('role') == "住戶":
        return redirect('/login')
    return await render_template('residents.html')

# ===== 生成訪客預約通行證 =====
@quart_app.route('/generate_booking_code', methods=['POST'])
async def generate_booking_code():
    try:
        form = await request.form
        files = await request.files
        
        username = form.get('username')
        if not username:
            return error_response('請提供住戶名稱')
        
        front_face = files.get('front_face')
        left_face = files.get('left_face')
        right_face = files.get('right_face')
        
        if not front_face or not left_face or not right_face:
            return error_response('請上傳三張照片（正面、左微側、右微側）')
        
        image_files = {
            'front': front_face,
            'left': left_face,
            'right': right_face
        }
        
        validation_result = face_recognizer.validate_face_images(image_files)
        if not validation_result['success']:
            return error_response(validation_result['message'])
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        visitor_name = f"visitor_{timestamp}_{random_suffix}"
        
        register_result = face_recognizer.register_visitor_faces(visitor_name, image_files)
        if not register_result['success']:
            return error_response(register_result['message'])
        
        success, message = visitor_Booking.save_visitor_booking(
            username, 
            visitor_name, 
            register_result['visitor_face_id']
        )
        if not success:
            return error_response(message)
        
        refresh_face_cache(db_manager)
        return success_response(message)
    
    except Exception as e:
        log.error(f"[錯誤] 訪客預約失敗: {e}")
        return error_response(f'預約失敗: {str(e)}', status=500)

# ===== 取貨影像串流 =====
@quart_app.route('/pick_up_feed')
async def pick_up_feed():
    return Response(pick_up_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===== 取得櫃位狀態 API =====
@quart_app.route('/api/locker_status', methods=['GET'])
async def get_locker_status():
    try:
        lockers = pick_up.get_all_lockers_status()
        return success_response(lockers=lockers)
    except Exception as e:
        log.error(f"[錯誤] 取得櫃位狀態失敗: {e}")
        return error_response(f'取得失敗: {str(e)}')

# ===== 登記包裹 API =====
@quart_app.route('/api/register_package', methods=['POST'])
async def register_package():
    try:
        data = await request.get_json()
        recipient_name = data.get('recipient_name', '').strip()
        
        if not recipient_name:
            return error_response('請輸入取件人姓名')
        
        success, locker_number, message = pick_up.register_package(recipient_name)
        if success:
            return success_response(message, locker_number=locker_number)
        else:
            return error_response(message)
    except Exception as e:
        log.error(f"[錯誤] 登記包裹失敗: {e}")
        return error_response(f'登記失敗: {str(e)}', status=500)

# ===== 手動清除櫃位 API =====
@quart_app.route('/api/clear_locker/<int:locker_number>', methods=['POST'])
async def clear_locker(locker_number):
    try:
        if locker_number not in [1, 2]:
            return error_response('無效的櫃號')
        
        success, message = pick_up.clear_locker(locker_number)
        if success:
            return success_response(message)
        else:
            return error_response(message)
    except Exception as e:
        log.error(f"[錯誤] 清除櫃位失敗: {e}")
        return error_response(f'清除失敗: {str(e)}', status=500)

# ===== 取得火災監測狀態 API =====
@quart_app.route('/api/fire_status', methods=['GET'])
async def get_fire_status():
    try:
        if RPI:
            dht22 = rpi_to_dht22()
            mq135 = rpi_to_mq135()

            dht22_data = dht22['data'] if dht22['success'] else {'error': dht22['error']}
            mq135_data = mq135['data'] if mq135['success'] else {'error': mq135['error']}

            return success_response(dht22=dht22_data, mq135=mq135_data)
        else:
            temp = random.randint(24, 28)
            return success_response(
                dht22={'temperature': temp, 'status': 'Normal'},
                mq135={'status': 'Safe', 'message': '無異常'}
            )
    except Exception as e:
        return error_response(str(e))

# ===== 火災警報共用函式 =====
def set_fire_status(is_danger):
    if not RPI:
        return
    if is_danger:
        rpi_to_buzzer('on')
        rpi_to_servo('0')
        rpi_to_redled('on')
    else:
        rpi_to_buzzer('off')
        rpi_to_servo('90')
        rpi_to_redled('off')

# ===== 火災警報開啟 API ======
@quart_app.route('/api/fire_status/danger')
async def fire_status_danger():
    set_fire_status(is_danger=True)
    config.fire_status_is_open = True
    return success_response('火災警報已啟動')

# ===== 火災警報關閉 API ======
@quart_app.route('/api/fire_status/safe')
async def fire_status_safe():
    set_fire_status(is_danger=False)
    config.fire_status_is_open = False
    return success_response('火災警報已關閉')

# ===== 手動關閉警報 API =====
@quart_app.route('/api/fire_status/close')
async def fire_status_close():
    set_fire_status(is_danger=False)
    config.fire_status_is_open = False
    return success_response('火災警報已手動關閉')

if __name__ == '__main__':
    # 本地直接執行 (生產環境建議使用 hypercorn app:app)
    app.run(debug=True, host='127.0.0.1', port=5000)