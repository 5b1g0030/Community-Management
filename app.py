""" Flask 網頁後端"""

from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
import cv2
import numpy as np
from face_recognition_for_window import FaceRecognitionSystem
import os
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# 初始化人臉辨識系統
face_system = FaceRecognitionSystem()

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 進行人臉辨識
        results = face_system.recognize_face(frame)
        
        # 在影像上繪製辨識結果
        for result in results:
            x, y, w, h = result['position']
            name = result['name']
            confidence = result['confidence']
            
            color = (0, 255, 0) if name != '未知' else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            label = f"{name} ({confidence:.1f})"
            cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # 發送辨識結果到前端
            if name != '未知':
                socketio.emit('recognition', {'type': 'recognition', 'message': f'偵測到{name}住戶來到大門'})
            else:
                socketio.emit('recognition', {'type': 'recognition', 'message': '偵測到未知人物'})
        
        # 將影像轉換為 JPEG 格式
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/add_face', methods=['POST'])
def add_face():
    if 'image' not in request.files:
        return jsonify({'message': '未選擇圖片'}), 400
    
    file = request.files['image']
    name = request.form.get('name')
    
    if not name:
        return jsonify({'message': '未輸入姓名'}), 400
    
    # 讀取並處理圖片
    image_bytes = file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 加入人臉到資料庫
    face_system.add_face_to_database(image, name)
    
    return jsonify({'message': '成功加入人臉資料'})

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

@app.route('/get_faces')
def get_faces():
    faces = face_system.get_all_faces()
    return jsonify(faces)

if __name__ == '__main__':
    socketio.run(app, debug=True)