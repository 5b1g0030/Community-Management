""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import cv2
import numpy as np
from models.face_detector import FaceDetector  # 修改引用
from models.database import DatabaseManager    # 修改引用
from utils.camera_utils import CameraManager
import os
from datetime import datetime
import random

app = Flask(__name__)
socketio = SocketIO(app)

# 初始化系統組件
face_detector = FaceDetector()      # 人臉偵測器
db_manager = DatabaseManager()      # 資料庫管理器

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
    
    role = db_manager.login_user(username, password)  # 修改引用
    print(f"login_user returned role: {repr(role)}")
    if role:
        # --- 根據身分導向不同頁面 ---
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
    
    success, message = db_manager.register_user(username, password, role)  # 修改引用

    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'message': message}), 400


'''
===== 影像辨識與串流播放 =====
'''

# 本次辨識到的人臉(集合)
last_names = set()

# ===== 影像串流&推送辨識訊息 =====
def gen_frames():
    # ----- 推送辨識訊息(已知, 未知) -----
    def face_message():
        # 查看每一筆資料
        for result in results:
            name = result['name']  # 名字欄位

            # ----- 如果不是「未知」且 name 不為空，則顯示名字 -----
            if name and name != '未知':
                # 辨識紀錄訊息「偵測到xxx住戶來到大門」，包含「事件名稱, 資料(資料類型, 訊息內容)」
                socketio.emit('recognition', {
                              'type': 'recognition', 'message': f'偵測到{name}住戶來到大門'})
            # ----- 如果是「未知」，顯示未知人物 -----
            elif name == '未知':
                # ------ 辨識紀錄訊息「偵測到未知人物」 -----
                socketio.emit('recognition', {
                              'type': 'recognition', 'message': '偵測到未知人物'})

                # ----- 檢查 static/temp 路徑是否存在，若無則建立 -----
                temp_dir = os.path.join('static', 'temp')
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)

                # ----- 儲存暫存圖片(請確保路徑存在) -----
                img_path = None
                # 儲存整個畫面
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
    try:
        while True:
            ret, frame = cap.read() # 讀取影像
            # ----- 檢查是否正確讀取，沒有的話則跳出回圈 -----
            if not ret:
                break
            
            latest_frame = frame.copy() # 紀錄最新影像(給人工審核視窗更新照片)

            # ----- 進行人臉辨識 -----
            results = face_detector.recognize_face(frame)  # 修改引用
            current_names = set([r['name']
                                for r in results])  # 本次影像中所有被辨識到的人名（不重複）

            # ----- 第一次啟動時，主動推送辨識紀錄 -----
            if last_names is None:
                face_message() # 呼叫「根據辨識情況推送訊息函式」
                last_names = current_names # 紀錄本次辨識到的人臉 

            # ----- 在新住戶或未知人物出現時推送 -----
            elif current_names != last_names:
                if not results:
                    socketio.emit('recognition', {
                                'type': 'recognition', 'message': '未偵測到人臉'})
                    # 【辨識紀錄-未知人物事件儲存】
                    db_manager.save_recognition_log("未知", "未偵測到人臉")
                else:
                    face_message() # 呼叫「根據辨識情況推送訊息函式」
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
    # 檢查是否有圖片
    if 'image' not in request.files:
        return jsonify({'message': '未選擇圖片'}), 400 # flask 錯誤訊息回應語法轉json格式 , 網頁狀態碼

    file = request.files['image']   # 上傳的圖片
    name = request.form.get('name') # 上傳的姓名

    # 檢查是否有姓名
    if not name:
        return jsonify({'message': '未輸入姓名'}), 400

    # 讀取並處理圖片
    image_bytes = file.read()                       # 讀取圖片資料(二進位)
    nparr = np.frombuffer(image_bytes, np.uint8)    # 轉換為 numpy 陣列
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)   # 解碼為 opencv 可用的影像格式

    # 加入人臉到資料庫(使用例外處理)
    try:
        success = face_detector.add_face_to_database(image, name)  # 修改引用
        # 當函式完整執行完的結果
        if success:
            return jsonify({'message': '成功加入人臉資料'}) # flask 錯誤訊息回應語法，狀態碼預設為 200
        else:
            return jsonify({'message': '加入失敗：未偵測到人臉'}), 400
    except Exception as e:
        return jsonify({'message': f'加入失敗：{str(e)}'}), 500

# ===== 測試辨識人臉 =====
@app.route('/test_face', methods=['POST'])
def test_face():
    if 'image' not in request.files:
        return jsonify({'message': '未選擇圖片'}), 400

    file = request.files['image']

    # 讀取並處理圖片
    image_bytes = file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 進行人臉辨識
    results = face_detector.recognize_face(image)  # 修改引用

    if not results:
        return jsonify({'message': '未偵測到人臉'})

    messages = []
    for result in results:
        name = result['name']
        confidence = result['confidence']
        messages.append(f"{name} (信心度: {confidence:.1f})")

    return jsonify({'message': '辨識結果：' + '、'.join(messages)})

# ===== 取得人臉資料 =====
@app.route('/get_faces')
def get_faces():
    faces = db_manager.get_all_faces()  # 修改引用
    return jsonify(faces)               # 轉 json 格式

# ===== 取得辨識紀錄資料 =====
@app.route('/get_recognition_logs')
def get_recognition_logs():
    logs = db_manager.get_all_recognition_logs()  # 修改引用
    return jsonify(logs)                          # 轉 json 格式

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


# # ===== 再拍一張功能-獲取最新人物影像 =====
# @app.route('/latest_unknown_face')
# def latest_unknown_face():
#     global latest_frame
#     if latest_frame is None:
#         return jsonify({'image_url': None})
#     temp_dir = os.path.join('static', 'temp')
#     if not os.path.exists(temp_dir):
#         os.makedirs(temp_dir)
#     img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
#     cv2.imwrite(img_path, latest_frame)
#     image_url = '/' + img_path.replace('\\', '/')
#     return jsonify({'image_url': image_url})

# ===== 新增住戶頁面路由 =====
@app.route('/residents')
def residents():
    return render_template('residents.html')


"""
===== 訪客預約功能 ===== 
"""

# ===== 生成訪客預約碼 =====
@app.route('/generate_booking_code', methods=['POST'])
def generate_booking_code():
    # ---取得表單'username'欄位的資料---
    username = request.form.get('username')

    # ---檢查是否有使用者名稱---
    if not username: # 如果沒有資料(None)
        # 回傳400狀態(請求錯誤)+訊息
        return jsonify({'message': '請提供使用者名稱'}), 400
    
    # ---生成6位數隨機數字，轉為字串，作為驗證碼---
    booking_code = str(random.randint(100000, 999999))
    
    # ---儲存到資料庫(包含使用者名稱, 驗證碼)---
    # success => 函式執行結果(T,F)
    # message => 成功/錯誤訊息 
    success, message = db_manager.create_visitor_booking(username, booking_code)
    
    # ---如果函式有執行成功，則回傳(訊息+驗證碼)，沒有則只回傳(訊息)---
    if success:
        return jsonify({'message': message, 'booking_code': booking_code}), 200
    else:
        return jsonify({'message': message}), 400

# ===== 驗證訪客預約碼 =====
@app.route('/verify_booking_code', methods=['POST'])
def verify_booking_code():
    # 從表單獲取驗證碼
    booking_code = request.form.get('booking_code')
    
    # 如果沒有驗證碼
    if not booking_code:
        return jsonify({'message': '請輸入預約碼'}), 400
    
    # 紀錄執行結果、回傳訊息或資料
    success, result = db_manager.verify_visitor_booking(booking_code)  # 呼叫函式
    
    # 如果有查詢到住戶名稱，代表此驗證碼有效
    if success:
        # 推送辨識訊息
        socketio.emit('recognition', {
            'type': 'recognition', 
            'message': f'偵測到{result}住戶的訪客已到大門'
        })

        # 回傳資料
        return jsonify({
            'message': f'驗證成功，{result}住戶的訪客', 
            'username': result, 
            'booking_code': booking_code,
            'start_countdown': True
        }), 200
    else:
        return jsonify({'message': result}), 400

# ===== 擷取訪客照片 =====
@app.route('/capture_visitor_photo', methods=['POST'])
def capture_visitor_photo():
    global latest_frame # 最新影像(全域變數，影像串流中固定紀錄)
    
    # 如果沒有最新影像
    if latest_frame is None:
        return jsonify({'message': '無法取得鏡頭影像'}), 400
    
    # 從提交過來的表單取得住戶名稱和預約碼
    username = request.form.get('username') # 使用者名稱
    booking_code = request.form.get('booking_code') # 驗證碼
    
    #　如果沒有使用者名稱
    if not username:
        return jsonify({'message': '缺少住戶名稱'}), 400
    
    try:
        # 用來存訪客照片的資料夾
        visitors_dir = os.path.join('static', 'visitors') 

        # 檢查 visitors 資料夾是否存在，若無則建立
        # 檢查該資料夾路徑，找不到會回傳 True
        if not os.path.exists(visitors_dir):
            os.makedirs(visitors_dir) # 建立資料夾
        
        # 產生檔案名稱（包含時間戳記）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # 時間戳記
        filename = f'visitor_{timestamp}.jpg' # 檔案名稱+副檔名
        file_path = os.path.join(visitors_dir, filename) # 合成一個「完整路徑」字串(資料夾+檔案)
        
        # 儲存影像
        # 將 OpenCV 的影像資料（通常為 numpy 陣列）寫入磁碟成為圖片檔，路徑為 file_path 
        success = cv2.imwrite(file_path, latest_frame)
        
        # 如果儲存成功
        if success:
            # 將資料存入 user_message 資料表
            db_success, db_message = db_manager.save_visitor_message(  # 呼叫函式
                username=username,
                visitor_image_path=file_path,
                booking_code=booking_code
            )
            
            # 如果成功儲存到資料庫
            if db_success:
                return jsonify({
                    'message': '訪客照片已成功儲存並記錄到資料庫',
                    'filename': filename,
                    'file_path': file_path,
                    'db_message': db_message
                }), 200
            else:
                return jsonify({
                    'message': '照片已儲存但資料庫記錄失敗',
                    'filename': filename,
                    'file_path': file_path,
                    'db_error': db_message
                }), 500
        else:
            return jsonify({'message': '照片儲存失敗'}), 500
            
    except Exception as e:
        return jsonify({'message': f'拍照失敗：{str(e)}'}), 500

# ===== 取得訪客留言記錄 =====
@app.route('/get_visitor_messages')
def get_visitor_messages():
    messages = db_manager.get_all_visitor_messages()  # 修改引用
    return jsonify(messages)

# ===== 取得特定使用者的訪客留言 =====
@app.route('/get_user_messages')
def get_user_messages():
    # 從 HTTP 請求的查詢字串 (query string) 取得名為 username 的參數值
    # 例如：GET /get_user_messages?username=Gina → username 會是 "Gina"
    username = request.args.get('username')
    if not username:
        return jsonify({'message': '缺少使用者名稱'}), 400
    
    try:
        messages = db_manager.get_user_visitor_messages(username)  # 呼叫函式
        return jsonify({'messages': messages}), 200
    except Exception as e:
        return jsonify({'message': f'查詢失敗：{str(e)}'}), 500

# ===== 審核訪客留言 =====
@app.route('/review_visitor', methods=['POST'])
def review_visitor():
    # 取得表單資料
    message_id = request.form.get('message_id')
    status = request.form.get('status')
    username = request.form.get('username')
    
    # 驗證必要參數
    if not all([message_id, status, username]):
        return jsonify({'message': '缺少必要參數'}), 400
    
    # 驗證狀態值
    if status not in ['approved', 'rejected']:
        return jsonify({'message': '無效的審核狀態'}), 400
    
    try:
        # 更新資料庫
        success, message = db_manager.update_visitor_message_status(message_id, status, username)
        
        if success:
            # 推送辨識訊息到管理員端
            if status == 'approved':
                socketio.emit('recognition', {
                    'type': 'recognition', 
                    'message': f'{username}已允許訪客進入'
                })
                # 【辨識紀錄-xxx住戶訪客允許進入事件儲存】
                db_manager.save_recognition_log("訪客", f"{username}住戶的訪客允許進入")
            else:
                socketio.emit('recognition', {
                    'type': 'recognition', 
                    'message': f'{username}不允許訪客進入'
                })
                # 【辨識紀錄-xxx住戶訣客不允許進入事件儲存】
                db_manager.save_recognition_log("訪客", f"{username}住戶的訪客不允許進入")
            
            return jsonify({'message': message}), 200
        else:
            return jsonify({'message': message}), 400
            
    except Exception as e:
        return jsonify({'message': f'審核失敗：{str(e)}'}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True)
