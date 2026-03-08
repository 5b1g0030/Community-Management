# Models 套件初始化檔案

from flask import Flask
from flask_socketio import SocketIO
from modules.database import DatabaseManager
from modules.face_recognition import FaceRecognition, init_face_cache
from modules.user import UserManager
import os

# 初始化 Flask 應用程式

# 合出專案根目錄下的 templates 和 static 資料夾的絕對路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))

# 初始化 SocketIO
socketio = SocketIO(app)

# 初始化其他全域變數
db_manager = DatabaseManager()
face_recognizer = FaceRecognition()
user = UserManager()

# 初始化人臉辨識快取
init_face_cache(db_manager)

# 初始化包裹櫃位資料表
# db_manager.init_package_lockers()