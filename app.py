""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import cv2
import numpy as np
from modules.face_detector import FaceDetector  # 修改引用
from modules.database import DatabaseManager    # 修改引用
from modules.user import UserManager
from modules.face_recognition import FaceRecognition, init_face_cache, refresh_face_cache  # 新增引用
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random
import face_recognition
from modules.config import FACE_RECOGNITION_TOLERANCE, FACE_RECOGNITION_FRAME_SKIP


app = Flask(__name__)
socketio = SocketIO(app)

# 初始化系統組件
face_detector = FaceDetector()  # 人臉辨識器
db_manager = DatabaseManager()  # 資料庫管理器
user = UserManager()            # 使用者資料管理
face_recognizer = FaceRecognition()  # 人臉註冊與辨識

# 初始化人臉辨識快取
init_face_cache(db_manager)

latest_frame = None

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
    
    global last_names, latest_frame # 本次辨識到的人臉, 紀錄最新影像 

    """ 相機設定&開啟 """
    # ----- 攝影機自動搜尋 -----
    backends = CameraManager.get_camera_config() # 取得系統後端
    camera_index, backend = CameraManager.find_camera(backends) # 取得可用的相機設定
    # ----- 檢查是否有找到攝影機 -----
    if camera_index and backend is None:
        print("無法找到可用的攝影機")
        return
    # ----- 使用找到的最佳攝影機設定開啟攝影機 -----
    cap = CameraManager.open_camera(camera_index, backend)
    # ----- 檢查攝影機有沒有打開 -----
    if not cap.isOpened():
        print("攝影機開啟失敗")
        return


    """ 開始讀取影像&播放 """
    frame_count = 0  # 幀計數器
    last_results = []  # 儲存上次辨識結果
    
    try:
        while True:
            ret, frame = cap.read() # 讀取影像
            # ----- 檢查是否正確讀取，沒有的話則跳出回圈 -----
            if not ret:
                break
            
            latest_frame = frame.copy() # 紀錄最新影像(給人工審核視窗更新照片)

            # ----- 幀數控制：每 N 幀才執行一次辨識 -----
            frame_count += 1
            if frame_count % FACE_RECOGNITION_FRAME_SKIP == 0:
                # 進行人臉辨識（使用實例方法）
                results = face_recognizer.recognize_face_from_frame(db_manager, frame, use_cache=True)
                last_results = results  # 儲存辨識結果
                frame_count = 0  # 重置計數器
            else:
                # 使用上次的辨識結果
                results = last_results

            current_names = set([r['name'] for r in results])  # 本次影像中所有被辨識到的人名（不重複）

            # ----- 第一次啟動時，主動推送辨識紀錄 -----
            if last_names is None:
                face_message(results) # 呼叫「根據辨識情況推送訊息函式」
                last_names = current_names # 紀錄本次辨識到的人臉 

            # ----- 在新住戶或未知人物出現時推送 -----
            elif current_names != last_names:
                if not results:
                    socketio.emit('recognition', {
                                'type': 'recognition', 'message': '未偵測到人臉'})
                    # 【辨識紀錄-未知人物事件儲存】
                    db_manager.save_recognition_log("未知", "未偵測到人臉")
                else:
                    face_message(results) # 呼叫「根據辨識情況推送訊息函式」
                    # ----- 儲存辨識紀錄 -----
                    # 直接用 results 裡的 id 與 confidence 儲存：只存「新出現且為已知」的人

                    # 【辨識紀錄-已知人物事件儲存】
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
                        print(f"儲存辨識紀錄失敗: {e} by app")

                last_names = current_names  # 更新偵測結果(名字或 null)

            # ----- 在影像上繪製辨識結果 -----
            face_detector.draw_frame(results, frame) # 呼叫函式

            # ----- 將影像轉換為 JPEG 格式，輸出到網頁 -----
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # 把每一張即時攝影機畫面傳給前端網頁
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        CameraManager.clean_camera(cap) # 釋放資源
        print("攝影機已關閉")


# ===== 鏡頭影像顯示 =====
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


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
        image_file = request.files.get('image')
        
        if not image_file:
            return jsonify({'success': False, 'message': '請提供照片'})
        
        # 建立臨時資料夾
        temp_dir = os.path.join('static', 'temp_uploads')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # 儲存上傳的圖片到臨時資料夾
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'test_{timestamp}.jpg'
        temp_path = os.path.join(temp_dir, filename)
        image_file.save(temp_path)
        
        # 呼叫 recognize_face 函式（使用實例方法）
        result = face_recognizer.recognize_face(db_manager, temp_path)
        
        if result['success']:
            return jsonify({'success': True, 'results': result['results'], 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'錯誤: {str(e)}'})

# ===== 取得人臉資料 =====
@app.route('/get_faces')
def get_faces():
    try:
        conn = db_manager.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM faces")
        faces = cursor.fetchall()
        conn.close()
        
        face_list = [{'id': face[0], 'name': face[1]} for face in faces]
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
