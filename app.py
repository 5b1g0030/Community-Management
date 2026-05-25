""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from modules.faceRecognition import refresh_face_cache
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random
import time
from modules.config import FACE_RECOGNITION_RESIZE_WIDTH #FACE_RECOGNITION_FRAME_SKIP
import modules.config as config # 給相機做同步修改
from modules.video_streaming import gen_frames, pick_up_frame
from modules import app, socketio, db_manager, face_recognizer, user, recognition_Logs, visitor_Booking, pick_up
from modules.resberryPi import rpi_to_dht22, rpi_to_mq135, rpi_to_buzzer, rpi_to_redled,rpi_to_servo
from modules.config import RPI
import cv2


# ===== 管理者端 =====
@app.route('/manager')
def manager():
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
        return jsonify({'message': '請輸入使用者名稱和密碼'}), 400
    
    role = user.login_user(username, password)  # 修改引用
    print(f"login_user returned role: {repr(role)} By app") # 除錯
    if role:
        # --- 根據身分導向不同頁面 ---
        print('根據身分導向不同頁面 By app') # 除錯
        if role == '管理員':
            return jsonify({'message': '登入成功', 'redirect': '/manager'}), 200
        else:
            return jsonify({'message': '登入成功', 'redirect': '/residents'}), 200
    else:
        return jsonify({'message': '使用者名稱或密碼錯誤'}), 401

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
        return jsonify({'message': '所有欄位都需要填寫'}), 400
    
    if role not in ('住戶', '管理員'):
        return jsonify({'message': '身分選擇不正確'}), 400

    if len(username.strip()) < 3:
        return jsonify({'message': '使用者名稱至少要三字元'}), 400
    
    if len(password) < 6:
        return jsonify({'message': '密碼需要超過6字元'}), 400
    
    if password != confirm_password:
        return jsonify({'message': '兩次密碼不相同'}), 400
    
    # 嘗試將使用者加入資料庫
    success, message = user.register_user(username, password, role)  # 修改引用

    # 如果加入成功，則顯示成功訊息並跳轉到登入介面
    if success:
        return jsonify({'message': message, 'redirect': '/login'}), 200
    else:
        return jsonify({'message': message}), 400


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
            return jsonify({'success': True, 'message': '相機已經在運行中'}), 200
        config.CAMERA_ACTIVE = True
    print("[系統] 相機已開啟")
    return jsonify({'success': True, 'message': '相機已開啟'}), 200

# ===== 關閉相機 API =====
@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    # global camera_active, camera_instance
    try:
        with config.CAMERA_LOCK:
            if not config.CAMERA_ACTIVE:
                return jsonify({'success': True, 'message': '相機已經關閉'}), 200
            config.CAMERA_ACTIVE = False
            
            # 立即釋放攝影機資源
            if config.CAMERA_INSTANCE is not None:
                try:
                    CameraManager.clean_camera(config.CAMERA_INSTANCE)
                    print("[系統] 已釋放攝影機資源")
                except Exception as e:
                    print(f"[警告] 釋放攝影機資源時發生錯誤: {e}")
                finally:
                    config.CAMERA_INSTANCE = None
        
        print("[系統] 相機已關閉")
        time.sleep(0.5)  # 給予時間讓串流停止
        return jsonify({'success': True, 'message': '相機已關閉'}), 200
    except Exception as e:
        print(f"[錯誤] 關閉相機失敗: {e}")
        return jsonify({'success': False, 'message': f'關閉失敗: {str(e)}'}), 500

# ===== 取得相機狀態 API =====
@app.route('/camera_status', methods=['GET'])
def camera_status():
    return jsonify({'active': config.CAMERA_ACTIVE}), 200

# ===== 加入人臉到資料庫 =====
@app.route('/add_face', methods=['POST'])
def add_face():
    try:
        name = request.form.get('name')
        image_file = request.files.get('image')
        
        if not name or not image_file:
            return jsonify({'success': False, 'message': '請提供姓名和照片'})
        
        # 建立臨時資料夾
        temp_dir = os.path.join('static', 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # 儲存上傳的圖片到臨時資料夾
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{name}_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        image_file.save(temp_path)
        
        # 呼叫 register_faces 函式（使用實例方法）
        result = face_recognizer.register_faces(db_manager, name, temp_dir, [filename])
        
        if result['success']:
            # 重新整理快取
            refresh_face_cache(db_manager)
            print(f"[系統] 已新增 {name} 並重新整理快取")
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'錯誤: {str(e)}'})

# ===== 測試辨識人臉 =====
@app.route('/test_face', methods=['POST'])
def test_face():
    try:
        print("[測試辨識] 開始處理請求")
        
        # ===== 自動關閉相機 =====
        camera_was_active = config.CAMERA_ACTIVE
        if camera_was_active:
            with config.CAMERA_LOCK:
                config.CAMERA_ACTIVE = False
            print("[測試辨識] 已自動關閉相機")
            import time
            time.sleep(1.0)  # 增加等待時間確保相機完全關閉
        
        image_file = request.files.get('image')
        
        if not image_file:
            print("[測試辨識] 錯誤：未提供照片")
            return jsonify({'success': False, 'message': '請提供照片'}), 400
        
        print(f"[測試辨識] 收到檔案：{image_file.filename}")
        
        # 驗證檔案類型
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        file_ext = os.path.splitext(image_file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'message': f'不支援的檔案格式：{file_ext}'}), 400
        
        # 建立臨時資料夾
        temp_dir = os.path.join('static', 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            print(f"[測試辨識] 建立資料夾：{temp_dir}")
        
        # 準備檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'test_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        
        # 先讀取並驗證圖片
        try:
            from PIL import Image
            
            # 讀取上傳的圖片（重要：在任何操作前先讀取）
            image_data = image_file.read()
            print(f"[測試辨識] 讀取圖片資料，大小：{len(image_data)} bytes")
            
            # 驗證圖片是否有效
            import io
            img = Image.open(io.BytesIO(image_data))
            print(f"[測試辨識] 圖片資訊 - 格式：{img.format}, 尺寸：{img.size}, 模式：{img.mode}")
            
            # 轉換為 RGB 模式（如果是 RGBA 或其他格式）
            if img.mode != 'RGB':
                print(f"[測試辨識] 轉換圖片模式從 {img.mode} 到 RGB")
                img = img.convert('RGB')
            
            # ===== 調整圖片大小（重要：避免圖片過大） =====
            max_size = FACE_RECOGNITION_RESIZE_WIDTH  # 最大寬度或高度
            if img.width > max_size or img.height > max_size:
                print(f"[測試辨識] 圖片過大，正在縮小...")
                # 計算縮放比例
                if img.width > img.height:
                    new_width = max_size
                    new_height = int(img.height * (max_size / img.width))
                else:
                    new_height = max_size
                    new_width = int(img.width * (max_size / img.height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"[測試辨識] 圖片已調整為：{img.size}")
            
            # 儲存處理後的圖片
            img.save(temp_path, 'JPEG', quality=95)
            print(f"[測試辨識] 圖片已儲存到：{temp_path}")   
        except Exception as img_error:
            print(f"[測試辨識] 圖片處理失敗：{img_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'圖片處理失敗：{str(img_error)}'}), 400
        
        # 呼叫 recognize_face 函式（使用實例方法）
        print("[測試辨識] 開始辨識人臉...")
        result = face_recognizer.recognize_face(db_manager, temp_path)
        print(f"[測試辨識] 辨識結果：{result}")

        # 提取第一個辨識結果
        frist_result = result['results'][0]
        name = frist_result['name']
        print(f"[測試辨識] 辨識結果：{name}")

        # 如果結果為訪客，則把訪客資料刪除
        if name and name.startswith('visitor_'):
            username = visitor_Booking.get_visitor_by_face_name(name) # 查詢申請此訪客的住戶
            # 推送訊息
            print("[推送辨識訊息] 辨識為訪客 by app")
            socketio.emit('recognition', {
                    'type': 'recognition',
                    'message': f'偵測到{username}住戶的訪客已到大門'
            })

            # --- 儲存辨識紀錄 ---
            face_id = result.get('id')
            conf = float(result.get('confidence', 0.0))
            if face_id:
                recognition_Logs.save_recognition_log("訪客", f"{username}住戶的訪客已到大門", face_id, conf)
                print("辨識紀錄已儲存 by app")
                       
            # 立即清除訪客人臉資料
            success = visitor_Booking.clear_visitor_face_data(name)   
            if success:
                # 重新整理快取
                refresh_face_cache(db_manager)
                print(f"[系統] 訪客 {name} 已辨識並清除人臉資料 by video_streaming")
            else:
                print(f"[系統] 訪客 {name} 人臉資料清除失敗 by video_streaming")
        # 如果結果為未知
        elif name == "未知":
            print("[推送辨識訊息] 辨識為未知 by app")
            socketio.emit('recognition', {
                'type': 'recognition',
                'message': '偵測到未知人物'
            })
            # --- 儲存辨識紀錄 ---
            recognition_Logs.save_recognition_log("未知", "偵測到未知人物")
            print("辨識紀錄已儲存 by app")
                    
            # 儲存暫存圖片
            temp_dir = os.path.join('static', 'temp')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
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
            print("[推送辨識訊息] 辨識為住戶 by app")
            socketio.emit('recognition', {
                'type': 'recognition',
                'message': f'偵測到{name}住戶來到大門'
            })
            # --- 儲存辨識紀錄 ---
            face_id = frist_result.get('id')
            print(f"人臉索引: {face_id}")
            # 解析信心值
            confidence_str = frist_result.get('confidence', '0.0%')  # 預設為 '0.0%'
            conf = float(confidence_str.strip('%')) / 100  # 移除 '%' 並轉換為小數
            if face_id:
                recognition_Logs.save_recognition_log("住戶", f"住戶{name}已來到大門", face_id, conf)
                print("辨識紀錄已儲存 by app")

        # 清理臨時檔案
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"[測試辨識] 已刪除臨時檔案：{temp_path}")
        except Exception as cleanup_error:
            print(f"[測試辨識] 清理臨時檔案失敗：{cleanup_error}")

        # 輸出結果
        if result['success']:
            # 如果之前相機是開啟的，重新開啟
            if camera_was_active:
                with config.CAMERA_LOCK:
                    config.CAMERA_ACTIVE = True
                print("[測試辨識] 已重新開啟相機")
            
            return jsonify({'success': True, 'results': result['results'], 'message': result['message']}), 200
        else:
            # 如果之前相機是開啟的，重新開啟
            if camera_was_active:
                with config.CAMERA_LOCK:
                    config.CAMERA_ACTIVE = True
                print("[測試辨識] 已重新開啟相機")
            
            return jsonify({'success': False, 'message': result['message']}), 200
    
    except Exception as e:
        # 發生錯誤時也要恢復相機狀態
        if camera_was_active:
            with config.CAMERA_LOCK:
                config.CAMERA_ACTIVE = True
            print("[測試辨識] 錯誤發生，已重新開啟相機")
        
        print(f"[測試辨識] 發生未預期的錯誤：{e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'系統錯誤：{str(e)}'}), 500

# ===== 取得人臉資料 =====
@app.route('/get_faces')
def get_faces():
    try:
        conn, cursor = db_manager.get_db_connection()
        cursor.execute("SELECT id, name, created_date, updated_date FROM face_recognition")
        faces = cursor.fetchall()
        conn.close()
        
        face_list = [{'id': face[0], 'name': face[1], 'created_date': face[2], 'updated_date': face[3]} for face in faces]
        return jsonify({'success': True, 'faces': face_list})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'錯誤: {str(e)}'})


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
            return jsonify({'success': False, 'message': '請提供住戶名稱'}), 400
        
        # 取得3張照片
        front_face = request.files.get('front_face')
        left_face = request.files.get('left_face')
        right_face = request.files.get('right_face')
        
        # 檢查是否有三張照片
        if not front_face or not left_face or not right_face:
            return jsonify({'success': False, 'message': '請上傳三張照片（正面、左微側、右微側）'}), 400
        
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
            return jsonify({
                'success': False,
                'message': validation_result['message']
            }), 400
        
        # 生成唯一的訪客識別名稱(用於儲存)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        visitor_name = f"visitor_{timestamp}_{random_suffix}"
        
        # 註冊訪客人臉
        register_result = face_recognizer.register_visitor_faces(
            db_manager, 
            visitor_name, 
            image_files
        )
        
        # # 驗證失敗時(沒註冊成功)，回傳錯誤訊息和 400 狀態碼
        if not register_result['success']:
            return jsonify({
                'success': False,
                'message': register_result['message']
            }), 400
        
        # 儲存訪客預約記錄
        success, message = visitor_Booking.save_visitor_booking(
            username, 
            visitor_name, 
            register_result['visitor_face_id']
        )
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
        
        # 重新整理人臉快取(更新數據庫)
        refresh_face_cache(db_manager)
        
        return jsonify({
            'success': True,
            'message': message
        }), 200
    
    except Exception as e:
        print(f"[錯誤] 訪客預約失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'預約失敗: {str(e)}'
        }), 500

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
        return jsonify({'success': True, 'lockers': lockers}), 200
    except Exception as e:
        print(f"[錯誤] 取得櫃位狀態失敗: {e}")
        return jsonify({'success': False, 'message': f'取得失敗: {str(e)}'}), 500

# ===== 登記包裹 API =====
@app.route('/api/register_package', methods=['POST'])
def register_package():
    """登記包裹（系統自動分配櫃號）"""
    try:
        data = request.get_json()
        recipient_name = data.get('recipient_name', '').strip()
        
        if not recipient_name:
            return jsonify({'success': False, 'message': '請輸入取件人姓名'}), 400
        
        success, locker_number, message = pick_up.register_package(recipient_name)
        
        if success:
            return jsonify({
                'success': True,
                'locker_number': locker_number,
                'message': message
            }), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    except Exception as e:
        print(f"[錯誤] 登記包裹失敗: {e}")
        return jsonify({'success': False, 'message': f'登記失敗: {str(e)}'}), 500

# ===== 手動清除櫃位 API =====
@app.route('/api/clear_locker/<int:locker_number>', methods=['POST'])
def clear_locker(locker_number):
    """手動清除櫃位"""
    try:
        if locker_number not in [1, 2]:
            return jsonify({'success': False, 'message': '無效的櫃號'}), 400
        
        success, message = pick_up.clear_locker(locker_number)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
    
    except Exception as e:
        print(f"[錯誤] 清除櫃位失敗: {e}")
        return jsonify({'success': False, 'message': f'清除失敗: {str(e)}'}), 500

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
            # 回傳資料內容:
            # 感測器 => 如果成功讀取，回傳資料 
            return jsonify({
                'success': True,
                'dht22': dht22['data'] if dht22['success'] else {'error': dht22['error']},
                'mq135': mq135['data'] if mq135['success'] else {'error': mq135['error']}
            }), 200
        else:
             # 樹莓派未啟用，返回模擬數據
            temp = random.randint(24,28)
            return jsonify({
                'success': True,
                'dht22': {'temperature': temp, 'status': 'Normal'},  # 模擬溫度數據
                'mq135': {'status': 'Safe', 'message': '無異常'}  # 模擬煙霧數據
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ===== 火災警報開啟 API ======
@app.route('/api/fire_status/danger')
def fire_status_danger():
    if RPI:
        # 【蜂鳴器鳴叫】
        rpi_to_buzzer('on')
        # 【開啟大門(不記錄時間)】
        rpi_to_servo('0')
        # 【REDLED，長亮】
        rpi_to_redled('on')
    config.fire_status_is_open = True
    # 【由前端呼叫】
    return jsonify({'success': True, 'message': '火災警報已啟動'})

# ===== 火災警報關閉 API ======
@app.route('/api/fire_status/safe')
def fire_status_safe():
    if RPI:
        # 【蜂鳴器靜音】
        rpi_to_buzzer('off')
        # 【關閉大門(不記錄時間)】
        rpi_to_servo('90')
        # 【REDLED關閉】
        rpi_to_redled('off')
    config.fire_status_is_open = False # 提示警報已解除，重啟人臉辨識
    # 【由前端呼叫，不須返回資料，所以返回簡單文字以符合Flask規則】
    return jsonify({'success': True, 'message': '火災警報已關閉'})

# ===== 手動關閉警報 API =====
# 包括關閉蜂鳴器、關閉大門、重新開啟人臉辨識
@app.route('/api/fire_status/close')
def fire_status_close():
    if RPI:
        # 【蜂鳴器靜音】
        rpi_to_buzzer('off')
        # 【關閉大門(不記錄時間)】
        rpi_to_servo('90')
    config.fire_status_is_open = False # 提示警報已解除，重啟人臉辨識
    # 【由前端呼叫，不須返回資料，所以返回簡單文字以符合Flask規則】
    return jsonify({'success': True, 'message': '火災警報已手動關閉'})


if __name__ == '__main__':
    socketio.run(app, debug=True)
