# Models 套件初始化檔案

from flask import Flask
from flask_socketio import SocketIO
# from modules.database import DatabaseManager
from modules.face_recognition import FaceRecognition, init_face_cache
from modules.user import UserManager
import os
from modules.databases.databaseManager import DatabaseManager
from modules.databases.recognitionLogs import RecognitionLogs
from modules.databases.visitorBooking import VisitorBooking
from modules.databases.pickUp import PickUp

# 初始化 Flask 應用程式

# 合出專案根目錄下的 templates 和 static 資料夾的絕對路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

# 初始化 SocketIO
socketio = SocketIO(app)

# 初始化其他全域變數
db_manager = DatabaseManager() # 原資料庫類別
face_recognizer = FaceRecognition() # 人臉識別
user = UserManager() # 使用者操作類別
recognition_Logs = RecognitionLogs() # 辨識紀錄類別
visitor_Booking = VisitorBooking() # 訪客預約類別
pick_up = PickUp() # 智慧取貨類別

# 初始化人臉辨識快取
init_face_cache(db_manager)

# 初始化資料庫
db_manager.init_database()