# ====== 路徑&參數設定 =====

# 資料庫
DATABASE = "face_database/face_database.db"

# 信心度(越小越相似)
FACE_RECOGNITION_TOLERANCE = 0.5

# ===== 人臉辨識優化參數 =====
FACE_RECOGNITION_FRAME_SKIP = 12  # 每 n 幀才執行一次辨識（原本 3，提高以減少運算）
FACE_RECOGNITION_RESIZE_WIDTH = 480  # 辨識用影像寬度（原本 640，降低解析度）
FACE_RECOGNITION_MODEL = 'hog'  # 人臉偵測模型：'hog' 較快但不準確，'cnn' 較慢但準確
CACHE_REFRESH_ON_ADD = True  # 新增人臉時是否自動重新整理快取

# ===== 相機狀態控制 =====
import threading
CAMERA_ACTIVE = False
CAMERA_LOCK = threading.Lock() 
CAMERA_INSTANCE = None
LATEST_FRAME = None

# ===== 取貨串流控制 =====
PICKUP_STREAM_ACTIVE = False
PICKUP_FACE_DETECTED = False  # 標記是否辨識到人臉