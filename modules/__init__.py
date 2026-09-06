import os
import logging as log
from quart import Quart
import socketio

# 模組引入
from modules.face.faceRecognition import FaceRecognition
from modules.face.face_cache import init_face_cache
from modules.user import UserManager
from modules.databases.databaseManager import DatabaseManager
from modules.databases.recognitionLogs import RecognitionLogs
from modules.databases.visitorBooking import VisitorBooking
from modules.databases.pickUp import PickUp

# 初始化紀錄訊息設定
log.basicConfig(
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=log.INFO
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

# 取得根目錄絕對路徑
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. 初始化 Quart 應用程式
quart_app = Quart(
    __name__, 
    template_folder=os.path.join(BASE_DIR, 'templates'), 
    static_folder=os.path.join(BASE_DIR, 'static')
)
# 【修改 2】把 session 必須的金鑰設定給 quart_app[cite: 13]
quart_app.secret_key = 'MySecretKey950907'

# 2. 初始化 Async SocketIO，並封裝成 ASGI 應用程式
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, quart_app)

# 3. 初始化商務邏輯類別
db_manager = DatabaseManager()
face_recognizer = FaceRecognition()
user = UserManager()
recognition_Logs = RecognitionLogs()
visitor_Booking = VisitorBooking()
pick_up = PickUp()

# 4. 利用 Quart 生命週期管理 I/O 初始化
@quart_app.before_serving
async def startup():
    # 若 db 或 cache 內部有非同步方法，可在此使用 await
    # 例如：await db_manager.init_database()
    await db_manager.init_database()
    await init_face_cache()