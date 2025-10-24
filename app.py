""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import cv2
import numpy as np
from face_recognition_for_window import FaceRecognitionSystem
from utils.camera_utils import CameraManager # 相機管理工具
import os
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# 初始化人臉辨識系統
face_system = FaceRecognitionSystem()

latest_frame = None # 紀錄最新影像

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
    
    # POST 處理
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({'message': '請輸入使用者名稱和密碼'}), 400
    
    # 驗證使用者 -> 現在 login_user 會回傳身分字串或 None
    role = face_system.db_manager.login_user(username, password)
    # 偵錯：在伺服器印出回傳值，檢查是否有空白或其他字元
    print(f"login_user returned role: {repr(role)}")
    if role:
        # 根據身分導向不同頁面
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
    
    # POST 處理
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role = request.form.get('role', '住戶')  # 預設為住戶

    # ----- 後端驗證 -----
    if not username or not password or not confirm_password:
        return jsonify({'message': '所有欄位都需要填寫'}), 400
    
    if role not in ('住戶', '管理員'):
        return jsonify({'message': '身分選擇不正確'}), 400

    # 使用者名稱
    if len(username.strip()) < 3:
        return jsonify({'message': '使用者名稱至少要三字元'}), 400
    
    # 密碼
    if len(password) < 6:
        return jsonify({'message': '密碼需要超過6字元'}), 400
    
    # 二次密碼驗證
    if password != confirm_password:
        return jsonify({'message': '兩次密碼不相同'}), 400
    
    # ----- 註冊使用者 -----
    success, message = face_system.db_manager.register_user(username, password, role)

    # 如果註冊成功
    if success:
        return jsonify({'message': message}), 200
    # 如果註冊失敗
    else:
        return jsonify({'message': message}), 400

last_names = set() # 本次影像中所有被辨識到的人名（空集合，不重複）

# ===== 影像串流&推送辨識訊息 =====
def gen_frames():
    # ----- 推送辨識訊息(已知, 未知) -----
    def face_message():
        # 查看每一筆資料
        for result in results:
            name = result['name']  # 名字欄位

            # ----- 如果不是「未知」，則顯示名字 -----
            if name != '未知':
                # 辨識紀錄訊息「偵測到xxx住戶來到大門」，包含「事件名稱, 資料(資料類型, 訊息內容)」
                socketio.emit('recognition', {
                              'type': 'recognition', 'message': f'偵測到{name}住戶來到大門'})
            # ----- 如果是「未知」，顯示未知人物 -----
            else:
                # ------ 辨識紀錄訊息「偵測到未知人物」 -----
                socketio.emit('recognition', {
                              'type': 'recognition', 'message': '偵測到未知人物'})

                # ----- 檢查 static/temp 路徑是否存在，若無則建立 -----
                temp_dir = os.path.join('static', 'temp')
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)

                # ----- 儲存暫存圖片(請確保路徑存在) -----
                img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
                cv2.imwrite(img_path, frame)
                # 推送未知人臉的圖片路徑
                # replace('\\', '/') => 確保在 Windows 系統上路徑分隔符號正確
                socketio.emit('unknown_face', {
                    'image_url': '/' + img_path.replace('\\', '/')
                })
    
    global last_names, latest_frame # 本次辨識到的人臉, 紀錄最新影像

    # ----- 攝影機自動搜尋 -----
    # print("正在尋找攝影機...")
    # camera_index, backend = face_system.camera_type() # 呼叫「決定鏡頭所用參數函式」
    backends = CameraManager.get_camera_config()        # 取得系統後端
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

    try:
        while True:
            ret, frame = cap.read() # 讀取影像
            # ----- 檢查是否正確讀取，沒有的話則跳出回圈 -----
            if not ret:
                break
            
            latest_frame = frame.copy() # 紀錄最新影像(給人工審核視窗更新照片)

            # ----- 進行人臉辨識 -----
            results = face_system.recognize_face(frame)  # 呼叫「辨識人臉」函式
            current_names = set([r['name']
                                for r in results])  # 本次影像中所有被辨識到的人名（不重複）

            # ----- 第一次啟動時，主動推送辨識紀錄 -----
            if last_names is None:
                # 如果辨識結果為 None，表示沒有偵測到人臉
                if not results:
                    socketio.emit('recognition', {
                                'type': 'recognition', 'message': '未偵測到人臉'})
                else:
                    face_message() # 呼叫「根據辨識情況推送訊息函式」
                last_names = current_names # 紀錄本次辨識到的人臉 
            # ----- 在新住戶或未知人物出現時推送 -----
            elif current_names != last_names:
                if not results:
                    socketio.emit('recognition', {
                                'type': 'recognition', 'message': '未偵測到人臉'})
                else:
                    face_message() # 呼叫「根據辨識情況推送訊息函式」
                last_names = current_names  # 更新偵測結果(名字或 null)

            # ----- 在影像上繪製辨識結果 -----
            for result in results: # 遍歷每個人臉
                x, y, w, h = result['position']     # 人臉位置與大小
                name = result['name']               # 人臉名稱
                confidence = result['confidence']   # 人臉辨識信心度()

                color = (0, 255, 0) if name != '未知' else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

                label = f"{name} ({confidence:.1f})"
                cv2.putText(frame, label, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # 將影像轉換為 JPEG 格式
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
        success = face_system.add_face_to_database(image, name) # 呼叫「將人臉加入資料庫函式」
        # 當函式完整執行完的結果
        if success:
            return jsonify({'message': '成功加入人臉資料'}) # flask 錯誤訊息回應語法，狀態碼預設為 200
        else:
            return jsonify({'message': '加入失敗：未偵測到人臉'}), 400
    except Exception as e:
        return jsonify({'message': f'加入失敗：{str(e)}'}), 500


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
    results = face_system.recognize_face(image)

    if not results:
        return jsonify({'message': '未偵測到人臉'})

    messages = []
    for result in results:
        name = result['name']
        confidence = result['confidence']
        messages.append(f"{name} (信心度: {confidence:.1f})")

    return jsonify({'message': '辨識結果：' + '、'.join(messages)})

# ===== 取得資料庫資料 =====
@app.route('/get_faces')
def get_faces():
    faces = face_system.db_manager.get_all_faces() # 呼叫「列出資料庫中的所有人臉資料(網頁)函式」
    return jsonify(faces)               # 轉 json 格式

# ===== 取得辨識紀錄資料 =====
@app.route('/get_recognition_logs')
def get_recognition_logs():
    logs = face_system.db_manager.get_all_recognition_logs() # 呼叫「列出資料庫中的所有辨識紀錄(網頁)函式」
    return jsonify(logs)                          # 轉 json 格式

# ===== 再拍一張功能-獲取最新人物影像 =====
@app.route('/latest_unknown_face')
def latest_unknown_face():
    global latest_frame
    if latest_frame is None:
        return jsonify({'image_url': None})
    temp_dir = os.path.join('static', 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    img_path = f'static/temp/unknown_{datetime.now().strftime("%Y%m%d%H%M%S")}.jpg'
    cv2.imwrite(img_path, latest_frame)
    image_url = '/' + img_path.replace('\\', '/')
    return jsonify({'image_url': image_url})

# 新增住戶頁面路由
@app.route('/residents')
def residents():
    return render_template('residents.html')


if __name__ == '__main__':
    socketio.run(app, debug=True)
