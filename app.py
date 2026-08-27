""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response, redirect, session
from modules.face.face_cache import refresh_face_cache
from modules.face.image_processor import validate_image_file, process_uploaded_image
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random
import time
from modules.config import RPI
import modules.config as config # 給相機做同步修改
from modules.video_streaming.video_streaming import gen_frames, pick_up_frame
from modules import app, socketio, db_manager, face_recognizer, user, recognition_Logs, visitor_Booking, pick_up
from modules.resberryPi import rpi_to_dht22, rpi_to_mq135, rpi_to_buzzer, rpi_to_redled,rpi_to_servo
from modules.cameraController import set_camera_state
from modules.video_streaming.faceMessage import save_log
from utils.response_utils import *
from utils.directory_utils import make_new_dir
import cv2
import logging as log

# 設定 secret_key (設定一個複雜的以便加密)
app.secret_key = 'MySecretKey950907' 

# ===== 管理者端 =====
@app.route('/manager')
def manager():
    # 檢查是否為管理員
    if session.get('role') != '管理員':
        return redirect('/login') 
    return render_template('manager.html')

# ===== 登入(首頁) =====
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return error_response('請輸入使用者名稱和密碼')
    
    role = user.login_user(username, password)  # 修改引用
    log.info(f"login_user returned role: {repr(role)}") # 除錯
    if role:
        # --- 記錄使用者的登入狀態 ---
        session['username'] = username
        session['role'] = role

        # --- 根據身分導向不同頁面 ---
        log.info('根據身分導向不同頁面 By app') # 除錯
        if role == '管理員':
            return success_response('登入成功', redirect='/manager')
        else:
            return success_response('登入成功', redirect='/residents')
    else:
        return error_response('使用者名稱或密碼錯誤', status=401)

# ===== 註冊 =====
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', '住戶')

    # ----- 後端驗證 -----
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
    
    # 嘗試將使用者加入資料庫
    success, message = user.register_user(username, password, role)  # 修改引用

    # 如果加入成功，則顯示成功訊息並跳轉到登入介面
    if success:
        return success_response(message, redirect='/login')
    else:
        return error_response(message)

# ===== 登出 =====
@app.route('/logout')
def logout():
    session.clear() # 清除所有會話紀錄，讓之前的登入資料失效
    return redirect('/login')

# ===== 鏡頭影像顯示 =====
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ===== 開啟相機 API =====
@app.route('/start_camera', methods=['POST'])
def start_camera():
    with config.CAMERA_LOCK:
        if config.CAMERA_ACTIVE:
            return success_response('相機已經在運行中')
        config.CAMERA_ACTIVE = True
    log.info("[系統] 相機已開啟")
    return success_response('相機已開啟')

# ===== 關閉相機 API =====
@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    try:
        with config.CAMERA_LOCK:
            if not config.CAMERA_ACTIVE:
                return success_response('相機已經關閉')
            config.CAMERA_ACTIVE = False
            
            # 立即釋放攝影機資源
            if config.CAMERA_INSTANCE is not None:
                try:
                    CameraManager.clean_camera(config.CAMERA_INSTANCE)
                    log.info("[系統] 已釋放攝影機資源")
                except Exception as e:
                    log.warning(f"[警告] 釋放攝影機資源時發生錯誤: {e}")
                finally:
                    config.CAMERA_INSTANCE = None
        
        log.info("[系統] 相機已關閉")
        time.sleep(0.5)  # 給予時間讓串流停止
        return success_response('相機已關閉')
    
    except Exception as e:
        log.error(f"[錯誤] 關閉相機失敗: {e}")
        return error_response(f'關閉失敗: {str(e)}', status=500)

# ===== 取得相機狀態 API =====
@app.route('/camera_status', methods=['GET'])
def camera_status():
    return jsonify({'active': config.CAMERA_ACTIVE}), 200

# ===== 加入人臉到資料庫 =====***
@app.route('/add_face', methods=['POST'])
def add_face():
    try:
        name = request.form.get('name')
        image_file = request.files.get('image')
        
        if not name or not image_file:
            return error_response('請提供姓名和照片')
        
        # 建立臨時資料夾**
        temp_dir = os.path.join('static', 'temp_uploads')
        make_new_dir(temp_dir)
        
        # 儲存上傳的圖片到臨時資料夾
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{name}_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        image_file.save(temp_path)
        
        # 呼叫 register_faces 函式（使用實例方法）
        result = face_recognizer.register_faces(name, temp_dir, [filename])
        
        if result['success']:
            # 重新整理快取
            refresh_face_cache(db_manager)
            log.info(f"[系統] 已新增 {name} 並重新整理快取")
            return success_response(result['message'])
        else:
            return error_response(result['message'])
    
    except Exception as e:
        return error_response(f'錯誤: {str(e)}')

# ===== 測試辨識人臉 =====***
@app.route('/test_face', methods=['POST'])
def test_face():
    try:
        log.info("[測試辨識] 開始處理請求")
        
        # ===== 自動關閉相機 =====
        camera_was_active = config.CAMERA_ACTIVE
        if camera_was_active:
            set_camera_state(False)
            log.info("[測試辨識] 已自動關閉相機")
            time.sleep(1.0)  # 增加等待時間確保相機完全關閉
        
        image_file = request.files.get('image')
        
        valid, error = validate_image_file(image_file)

        if not valid:
            return error_response(error)

        # 建立臨時資料夾**
        temp_dir = os.path.join('static', 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            # print(f"[測試辨識] 建立資料夾：{temp_dir}")
        # 準備檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'test_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        
        # 先讀取並驗證圖片
        img = process_uploaded_image(image_file, temp_path)
               
        # 呼叫 recognize_face 函式（使用實例方法）
        log.info("[測試辨識] 開始辨識人臉...")
        result = face_recognizer.recognize_face(temp_path)
        log.info(f"[測試辨識] 辨識結果：{result}")
        # 提取第一個辨識結果
        frist_result = result['results'][0]
        name = frist_result['name']
        log.info(f"[測試辨識] 辨識結果：{name}")

        # 如果結果為訪客，則把訪客資料刪除
        if name and name.startswith('visitor_'):
            username = visitor_Booking.get_visitor_by_face_name(name) # 查詢申請此訪客的住戶
            # 推送訊息
            send_recognition_message(f'偵測到{username}住戶的訪客已到大門')

            # --- 儲存辨識紀錄 ---
            face_id = frist_result.get('id')
            # 解析信心值
            confidence_str = frist_result.get('confidence', '0.0%')  # 預設為 '0.0%'
            conf = float(confidence_str.strip('%')) / 100  # 移除 '%' 並轉換為小數
            if face_id:
                recognition_Logs.save_recognition_log("訪客", f"{username}住戶的訪客已到大門", face_id, conf)
                log.info("辨識紀錄已儲存 by app")
                       
            # 立即清除訪客人臉資料
            success = visitor_Booking.clear_visitor_face_data(name)   
            if success:
                # 重新整理快取
                refresh_face_cache(db_manager)
                log.info(f"[系統] 訪客 {name} 已辨識並清除人臉資料")
            else:
                log.error(f"[系統] 訪客 {name} 人臉資料清除失敗")

        # 如果結果為未知
        elif name == "未知":
            send_recognition_message('偵測到未知人物')
        
            # --- 儲存辨識紀錄 ---
            save_log("未知", "偵測到未知人物")
            log.info("辨識紀錄已儲存 by app")
                    
            # 儲存暫存圖片**
            temp_dir = os.path.join('static', 'temp')
            make_new_dir(temp_dir)
            
            # 將 PIL 圖片轉換為 OpenCV 格式
            try:
                import numpy as np
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                img_path = os.path.join(temp_dir, f'unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg')
                cv2.imwrite(img_path, img_cv)
                print(f"[測試辨識] 未知人物圖片已儲存到：{img_path}")
            except Exception as save_error:
                print(f"[測試辨識] 儲存未知人物圖片失敗：{save_error}")

        # 如果結果為住戶名稱(為排除例外情況，所以採用此判斷方式)
        elif name and name != "未知":
            send_recognition_message(f'偵測到{name}住戶來到大門')
            
            # --- 儲存辨識紀錄 ---
            face_id = frist_result.get('id')
            log.info(f"人臉索引: {face_id}")
            # 解析信心值
            confidence_str = frist_result.get('confidence', '0.0%')  # 預設為 '0.0%'
            conf = float(confidence_str.strip('%')) / 100  # 移除 '%' 並轉換為小數
            if face_id:
                recognition_Logs.save_recognition_log("住戶", f"住戶{name}已來到大門", face_id, conf)
                log.info("辨識紀錄已儲存 by app")

        # 輸出結果
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
        # 清理臨時檔案
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                log.info(f"[測試辨識] 已刪除臨時檔案：{temp_path}")
        except Exception as cleanup_error:
            log.error(f"[測試辨識] 清理臨時檔案失敗：{cleanup_error}")

# ===== 取得人臉資料 =====
@app.route('/get_faces')
def get_faces():
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
@app.route('/api/delete_faces', methods=['POST'])
def delete_faces():
    try:
        data = request.get_json()
        face_ids = data.get('ids', [])

        if not face_ids:
            return error_response('未提供需刪除的 ID')

        conn, cursor = db_manager.get_db_connection()
        
        # 刪除多筆資料，SQL語法如 DELETE FROM face_recognition WHERE id IN (1, 2, 3)
        placeholders = ','.join(['?'] * len(face_ids))
        cursor.execute(f"DELETE FROM face_recognition WHERE id IN ({placeholders})", tuple(face_ids))
        conn.commit()
        
        deleted_count = cursor.rowcount
        conn.close()

        # 刷新辨識用的快取，避免被刪除的人臉仍然認得出來
        refresh_face_cache(db_manager)

        return success_response(f'成功刪除 {deleted_count} 筆記錄')
    except Exception as e:
        log.error(f"[錯誤] 刪除人臉失敗: {e}")
        return error_response(f'刪除失敗: {str(e)}', status=500)

# ===== 取得辨識紀錄資料 (DataTables 篩選專用) =====
@app.route('/api/recognition_logs')
def get_recognition_logs_datatables():
    # 從資料庫獲取提供給 DataTables 讀取的 JSON 格式辨識紀錄資料
    logs = recognition_Logs.get_all_recognition_logs()  # 修改引用
    
    # 轉換為 DataTables 期望的格式
    data = []
    for log in logs:
        # 處理 None 值，顯示為 "無"
        face_id = log['face_id'] if log['face_id'] is not None else '無'
        confidence = f"{log['confidence']:.1f}" if log['confidence'] is not None else '無'
        
        # 加入資料(每個欄位的順序對應於前端 DataTables 的欄位索引)
        data.append([
            log['id'],            # id編號
            log['created_date'],  # 資料建立時間
            log['event_type'],    # 事件類型
            log['event_message'], # 事件訊息
            face_id,              # 辨識到的人臉id
            confidence            # 信心值
        ])
    
    response = jsonify({'data': data}) # 轉json
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # 禁用快取(利於即時更新)

    return response

# ===== 住戶頁面路由 =====
@app.route('/residents')
def residents():
    # 檢查是否有登入 (只有住戶能進)
    if not session.get('role') == "住戶":
        return redirect('/login')
    return render_template('residents.html')

# ===== 生成訪客預約通行證 =====
@app.route('/generate_booking_code', methods=['POST'])
def generate_booking_code():
    """
    訪客預約（需上傳3張照片進行人臉註冊）
    """
    try:
        # 取得住戶名稱
        username = request.form.get('username')
        
        if not username:
            return error_response('請提供住戶名稱')
        
        # 取得3張照片
        front_face = request.files.get('front_face')
        left_face = request.files.get('left_face')
        right_face = request.files.get('right_face')
        
        # 檢查是否有三張照片
        if not front_face or not left_face or not right_face:
            return error_response('請上傳三張照片（正面、左微側、右微側）')
        
        # 組織照片檔案
        image_files = {
            'front': front_face,
            'left': left_face,
            'right': right_face
        }
        
        # 驗證照片是否能偵測到人臉
        validation_result = face_recognizer.validate_face_images(image_files)
        
        # 驗證失敗時(沒偵測到人臉)，回傳錯誤訊息和 400 狀態碼
        if not validation_result['success']:
            return error_response(validation_result['message'])
        
        # 生成唯一的訪客識別名稱(用於儲存)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        visitor_name = f"visitor_{timestamp}_{random_suffix}"
        
        # 註冊訪客人臉
        register_result = face_recognizer.register_visitor_faces(
            visitor_name, 
            image_files
        )
        
        # # 驗證失敗時(沒註冊成功)，回傳錯誤訊息和 400 狀態碼
        if not register_result['success']:
            return error_response(register_result['message'])
        
        # 儲存訪客預約記錄
        success, message = visitor_Booking.save_visitor_booking(
            username, 
            visitor_name, 
            register_result['visitor_face_id']
        )
        
        if not success:
            return error_response(message)
        
        # 重新整理人臉快取(更新數據庫)
        refresh_face_cache(db_manager)
        
        return success_response(message)
    
    except Exception as e:
        log.error(f"[錯誤] 訪客預約失敗: {e}")
        return error_response(f'預約失敗: {str(e)}', status=500)

# ===== 取貨影像串流（辨識但不儲存、不推送通知） =====
@app.route('/pick_up_feed')
def pick_up_feed():
    return Response(pick_up_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ===== 取得櫃位狀態 API =====
@app.route('/api/locker_status', methods=['GET'])
def get_locker_status():
    """取得所有櫃位的狀態"""
    try:
        lockers = pick_up.get_all_lockers_status()
        return success_response(lockers=lockers)
    except Exception as e:
        log.error(f"[錯誤] 取得櫃位狀態失敗: {e}")
        return error_response(f'取得失敗: {str(e)}')

# ===== 登記包裹 API =====
@app.route('/api/register_package', methods=['POST'])
def register_package():
    """登記包裹（系統自動分配櫃號）"""
    try:
        data = request.get_json()
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
@app.route('/api/clear_locker/<int:locker_number>', methods=['POST'])
def clear_locker(locker_number):
    """手動清除櫃位"""
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
@app.route('/api/fire_status', methods=['GET'])
def get_fire_status():
    """取得火災監測區域 A/B 的數值"""
    try:
        if RPI:
            dht22 = rpi_to_dht22() # 溫度感測器
            mq135 =rpi_to_mq135() # 煙霧感測器
            # print(f"dht22: {dht22}")
            # print(f"mq135: {mq135}")

            # 取出需要的資料
            # 感測器 => 如果成功讀取，回傳資料
            dht22_data = dht22['data'] if dht22['success'] else {'error': dht22['error']}
            mq135_data = mq135['data'] if mq135['success'] else {'error': mq135['error']}

            # 回傳資料內容 
            return success_response(dht22=dht22_data, mq135=mq135_data)
    
        else:
            # 樹莓派未啟用，返回模擬數據
            temp = random.randint(24,28)
            return success_response(
                dht22={'temperature': temp, 'status': 'Normal'},
                mq135={'status': 'Safe', 'message': '無異常'}
            )
    except Exception as e:
        return error_response(str(e))


# ===== 火災警報共用函式 =====
def set_fire_status(is_danger):
    # 確認是否啟用樹梅派
    if not RPI:
        return

    # 開啟警報
    if is_danger:
        rpi_to_buzzer('on') # 蜂鳴器鳴叫
        rpi_to_servo('0') # 開啟大門
        rpi_to_redled('on') # 紅燈長亮

    # 關閉警報
    else:
        rpi_to_buzzer('off') # 蜂鳴器靜音
        rpi_to_servo('90') # 關閉大門
        rpi_to_redled('off') # 紅燈關閉

# ===== 火災警報開啟 API 【由前端呼叫】 ======
@app.route('/api/fire_status/danger')
def fire_status_danger():
    set_fire_status(is_danger=True)

    config.fire_status_is_open = True

    return success_response('火災警報已啟動')

# ===== 火災警報關閉 API 【由前端呼叫】 ======
@app.route('/api/fire_status/safe')
def fire_status_safe():
    set_fire_status(is_danger=False)
    
    config.fire_status_is_open = False # 提示警報已解除，重啟人臉辨識

    return success_response('火災警報已關閉')

# ===== 手動關閉警報 API 【由前端呼叫】 =====
# 包括關閉蜂鳴器、關閉大門、重新開啟人臉辨識
@app.route('/api/fire_status/close')
def fire_status_close():
    set_fire_status(is_danger=False)
    
    config.fire_status_is_open = False # 提示警報已解除，重啟人臉辨識

    return success_response('火災警報已手動關閉')


if __name__ == '__main__':
    socketio.run(app, debug=True)
