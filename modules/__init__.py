# Models 套件初始化檔案

from flask import Flask
from flask_socketio import SocketIO
from modules.face.faceRecognition import FaceRecognition
from modules.face.face_cache import init_face_cache
from modules.user import UserManager
import os
from modules.databases.databaseManager import DatabaseManager
from modules.databases.recognitionLogs import RecognitionLogs
from modules.databases.visitorBooking import VisitorBooking
from modules.databases.pickUp import PickUp
import logging as log

# 初始化紀錄訊息設定
log.basicConfig(
    # filename='app.log',     # 日誌檔名，若不指定則預設輸出到主控台
    # filemode='w',           # 'w' 為覆寫，'a' 為接續寫入 (預設是 'a')
    # level=log.DEBUG,     # 將追蹤層級調低到 DEBUG，這樣所有訊息都會被記錄
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S' # 自訂時間格式
)
"""
常用格式化欄位：
%(asctime)s：人類可讀的執行時間。
%(levelname)s：日誌層級名稱（如 INFO, ERROR）。
%(filename)s：引發日誌的 Python 原始碼檔名。
%(lineno)d：引發日誌的程式碼行號。
%(message)s：你輸入的日誌訊息。

方法一：使用 __init__.py 或主程式進行根記錄器（Root）初始化
這是最簡單的做法。你只需要在主程式一開始呼叫 logging.basicConfig() 
或設定好 Logger，其他檔案直接使用 logging.getLogger(__name__) 即可。

# 這些預設不會印出（因為層級低於 WARNING）
logging.debug("這是一條 DEBUG 訊息")
logging.info("這是一條 INFO 訊息")

# 這些預設會印出
logging.warning("這是一條 WARNING 警告")
logging.error("這是一條 ERROR 錯誤")
logging.critical("這是一條 CRITICAL 嚴重錯誤")
"""

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