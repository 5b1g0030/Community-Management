""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import cv2
import numpy as np
from modules.database import DatabaseManager    # 修改引用
from modules.user import UserManager
from modules.face_recognition import FaceRecognition, init_face_cache, refresh_face_cache  # 新增引用
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random
import face_recognition
from modules.config import FACE_RECOGNITION_RESIZE_WIDTH, FACE_RECOGNITION_FRAME_SKIP


app = Flask(__name__)
#app.config['SECRET_KEY'] = 'your-secret-key-here' cors_allowed_origins="*", async_mode='threading'
socketio = SocketIO(app)

# ===== 初始化系統組件 =====
db_manager = DatabaseManager()  # 資料庫管理器
user = UserManager()            # 使用者資料管理
face_recognizer = FaceRecognition()  # 人臉註冊與辨識

# 初始化人臉辨識快取
init_face_cache(db_manager)

latest_frame = None

# ===== 相機狀態管理 =====
import threading
camera_active = False  # 預設關閉
camera_lock = threading.Lock()
camera_instance = None  # 新增：儲存攝影機實例

print("[系統] 相機狀態管理已初始化 (預設關閉)")


# ===== 新增相機狀態管理 =====
def init_camera_lock():
    """初始化相機鎖"""
    global camera_lock
    if camera_lock is None:
        import threading
        camera_lock = threading.Lock()
        print("[系統] camera_lock 已初始化")

init_camera_lock()

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


'''
===== 影像辨識與串流播放 =====
'''

# 本次辨識到的人臉(集合)
last_names = set()

# ===== 影像串流&推送辨識訊息 =====
def gen_frames():
    # ----- 推送辨識訊息(已知, 未知, 訪客) -----
    def face_message(results):
        for result in results:
            name = result['name']

            # ----- 檢查是否為訪客 -----
            if name and name.startswith('visitor_'):
                # 查詢對應的住戶名稱
                username = db_manager.get_visitor_by_face_name(name)
                
                if username:
                    # 推送訊息
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
                socketio.emit('recognition', {
                    'type': 'recognition',
                    'message': f'偵測到{name}住戶來到大門'
                })
            
            # ----- 如果是「未知」，顯示未知人物 -----
            elif name == '未知':
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
            x, y, w, h = result['position']
            name = result['name']
            confidence = result['confidence']

            color = (0, 255, 0) if name != '未知' else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            label = f"{name} ({confidence:.1f})"
            cv2.putText(frame, label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    global last_names, latest_frame, camera_active, camera_instance

    """ 相機設定&開啟 """
    try:
        # 等待相機開啟
        print(f"[系統] gen_frames 啟動，相機狀態: {camera_active}")
        
        while not camera_active:
            # 返回黑色畫面提示相機已關閉
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(black_frame, 'Camera is OFF', (180, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(black_frame, 'Click "Start Camera" to begin', (120, 280),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            ret, buffer = cv2.imencode('.jpg', black_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            import time
            time.sleep(0.5)
        
        print("[系統] 相機已啟動，開始初始化攝影機...")
        
        # ----- 攝影機自動搜尋 -----
        backends = CameraManager.get_camera_config()
        camera_index, backend = CameraManager.find_camera(backends)
        
        # ----- 檢查是否有找到攝影機 -----
        if camera_index is None or backend is None:
            print("[錯誤] 無法找到可用的攝影機")
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, 'Camera Not Found', (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            frame_bytes = buffer.tobytes()
            while camera_active:
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                import time
                time.sleep(0.5)
            return
        
        # ----- 使用找到的最佳攝影機設定開啟攝影機 -----
        cap = CameraManager.open_camera(camera_index, backend)
        camera_instance = cap  # 儲存攝影機實例
        
        # ----- 檢查攝影機有沒有打開 -----
        if not cap or not cap.isOpened():
            print("[錯誤] 攝影機開啟失敗")
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, 'Camera Open Failed', (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            frame_bytes = buffer.tobytes()
            while camera_active:
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                import time
                time.sleep(0.5)
            return

    except Exception as e:
        print(f"[錯誤] 攝影機初始化失敗: {e}")
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, f'Error: {str(e)}', (50, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame_bytes = buffer.tobytes()
        while camera_active:
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            import time
            time.sleep(0.5)
        return

    """ ===== 開始讀取影像&播放 ====== """
    frame_count = 0
    last_results = []
    
    try:
        while camera_active:  # 改為檢查 camera_active
            ret, frame = cap.read()
            if not ret:
                print("[警告] 無法讀取影像幀")
                break
            
            latest_frame = frame.copy()

            # ----- 幀數控制：每 N 幀才執行一次辨識 -----
            frame_count += 1
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                results = face_recognizer.recognize_face_from_frame(db_manager, frame, use_cache=True)
                last_results = results
                frame_count = 0
            else:
                results = last_results

            current_names = set([r['name'] for r in results])

            # ----- 第一次啟動時，主動推送辨識紀錄 -----
            if last_names is None:
                face_message(results)
                last_names = current_names

            # ----- 在新住戶或未知人物出現時推送 -----
            elif current_names != last_names:
                if not results:
                    socketio.emit('recognition', {
                                'type': 'recognition', 'message': '未偵測到人臉'})
                    db_manager.save_recognition_log("未知", "未偵測到人臉")
                else:
                    face_message(results)
                    try:
                        for r in results:
                            name = r.get('name')
                            if name and name != '未知' and (last_names is None or name not in last_names):
                                face_id = r.get('id')
                                conf = float(r.get('confidence', 0.0))
                                if face_id is not None:
                                    db_manager.save_recognition_log("住戶", f"{name}住戶已來到大門", face_id, conf)
                            elif name == '未知':
                                db_manager.save_recognition_log("未知", "未知人物")
                    except Exception as e:
                        print(f"儲存辨識紀錄失敗: {e}")

                last_names = current_names

            # ----- 在影像上繪製辨識結果 -----
            draw_frame(results, frame)

            # ----- 將影像轉換為 JPEG 格式，輸出到網頁 -----
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
    except Exception as e:
        print(f"[錯誤] 影像串流處理失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cap is not None:
            CameraManager.clean_camera(cap)
            camera_instance = None
            print("[系統] 攝影機已關閉並釋放資源")
        
        # 關閉後繼續提供黑屏，等待重新開啟
        while True:
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(black_frame, 'Camera is OFF', (180, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(black_frame, 'Click "Start Camera" to begin', (120, 280),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            ret, buffer = cv2.imencode('.jpg', black_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            import time
            time.sleep(0.5)
            
            # 如果相機被重新開啟，重新初始化
            if camera_active:
                print("[系統] 偵測到相機重新開啟，重新啟動串流")
                # 遞迴呼叫自己重新開始
                yield from gen_frames()
                return

# ===== 鏡頭影像顯示 =====
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ===== 開啟相機 API =====
@app.route('/start_camera', methods=['POST'])
def start_camera():
    global camera_active
    try:
        with camera_lock:
            if camera_active:
                return jsonify({'success': True, 'message': '相機已經在運行中'}), 200
            camera_active = True
        print("[系統] 相機已開啟")
        return jsonify({'success': True, 'message': '相機已開啟'}), 200
    except Exception as e:
        print(f"[錯誤] 開啟相機失敗: {e}")
        return jsonify({'success': False, 'message': f'開啟失敗: {str(e)}'}), 500

# ===== 關閉相機 API =====
@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    global camera_active, camera_instance
    try:
        with camera_lock:
            if not camera_active:
                return jsonify({'success': True, 'message': '相機已經關閉'}), 200
            camera_active = False
            
            # 立即釋放攝影機資源
            if camera_instance is not None:
                try:
                    CameraManager.clean_camera(camera_instance)
                    print("[系統] 已釋放攝影機資源")
                except Exception as e:
                    print(f"[警告] 釋放攝影機資源時發生錯誤: {e}")
                finally:
                    camera_instance = None
        
        print("[系統] 相機已關閉")
        import time
        time.sleep(0.5)  # 給予時間讓串流停止
        return jsonify({'success': True, 'message': '相機已關閉'}), 200
    except Exception as e:
        print(f"[錯誤] 關閉相機失敗: {e}")
        return jsonify({'success': False, 'message': f'關閉失敗: {str(e)}'}), 500

# ===== 取得相機狀態 API =====
@app.route('/camera_status', methods=['GET'])
def camera_status():
    global camera_active
    return jsonify({'active': camera_active}), 200

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
        global camera_active
        camera_was_active = camera_active
        if camera_was_active:
            with camera_lock:
                camera_active = False
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
        
        # 清理臨時檔案（可選）
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
                with camera_lock:
                    camera_active = True
                print("[測試辨識] 已重新開啟相機")
            
            return jsonify({'success': True, 'results': result['results'], 'message': result['message']}), 200
        else:
            # 如果之前相機是開啟的，重新開啟
            if camera_was_active:
                with camera_lock:
                    camera_active = True
                print("[測試辨識] 已重新開啟相機")
            
            return jsonify({'success': False, 'message': result['message']}), 200
    
    except Exception as e:
        # 發生錯誤時也要恢復相機狀態
        if camera_was_active:
            with camera_lock:
                camera_active = True
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

"""
===== 訪客預約功能 ===== 
"""

# ===== 取得辨識紀錄資料 (DataTables 篩選專用) =====
@app.route('/api/recognition_logs')
def get_recognition_logs_datatables():
    """提供給 DataTables 讀取的 JSON 格式辨識紀錄資料"""
    logs = db_manager.get_all_recognition_logs()  # 修改引用
    
    # 轉換為 DataTables 期望的格式 (陣列的陣列)
    data = []
    for log in logs:
        # 處理 None 值，顯示為 "無"
        face_id = log['face_id'] if log['face_id'] is not None else '無'
        confidence = f"{log['confidence']:.1f}" if log['confidence'] is not None else '無'
        
        # 加入資料
        data.append([
            log['id'],            # id編號
            log['created_date'],  # 資料建立時間
            log['event_type'],    # 事件類型
            log['event_message'], # 事件訊息
            face_id,              # 辨識到的人臉id
            confidence            # 信心值
        ])
    
    return jsonify({'data': data})

# ===== 新增住戶頁面路由 =====
@app.route('/residents')
def residents():
    return render_template('residents.html')

# ===== 生成訪客預約碼 =====
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
        
        if not validation_result['success']:
            return jsonify({
                'success': False,
                'message': validation_result['message']
            }), 400
        
        # 生成唯一的訪客識別名稱
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        visitor_name = f"visitor_{timestamp}_{random_suffix}"
        
        # 註冊訪客人臉
        register_result = face_recognizer.register_visitor_faces(
            db_manager, 
            visitor_name, 
            image_files
        )
        
        if not register_result['success']:
            return jsonify({
                'success': False,
                'message': register_result['message']
            }), 400
        
        # 儲存訪客預約記錄
        success, message = db_manager.save_visitor_booking(
            username, 
            visitor_name, 
            register_result['visitor_face_id']
        )
        
        if not success:
            return jsonify({'success': False, 'message': message}), 400
        
        # 重新整理人臉快取
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


if __name__ == '__main__':
    socketio.run(app, debug=True)
