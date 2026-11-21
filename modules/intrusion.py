"""
Polygon intrusion detection for the existing community camera stream.

The model is loaded lazily, only when intrusion monitoring is enabled.
One normalized polygon is shared by all administrator browser clients.
Notifications fire on confirmed entry, not on every frame.

區域入侵偵測模組，使用 YOLOv8n 人員模型對現有社區攝影機串流進行監控。
模型僅在啟用入侵監控時才會延遲載入，所有管理員瀏覽器客戶端共用同一個正規化多邊形區域設定。
警報僅在確認入侵時觸發，而非每個影格都觸發。
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

# ===== 全域設定與調校參數 =====
BASE_DIR = Path(__file__).resolve().parent.parent # 根目錄
CONFIG_PATH = BASE_DIR / "data" / "intrusion_zone.json"
EVENT_DB = BASE_DIR / "data" / "intrusion_events.db"
MODEL_PATH = BASE_DIR / "models" / "yolov8n.pt"

# Tune these if inference on CPU is slow.
DETECT_EVERY_N_FRAMES = 6 # 每隔幾個影格進行一次 YOLO 推論（越大越省資源，但延遲越高）
PERSON_CONFIDENCE = 0.45 # YOLO 判斷為「人」的信心度門檻
CONFIRM_HITS = 2 # 連續幾次推論都在區域內才算「確認入侵」
RESET_MISSES = 2 # 連續幾次推論都不在區域內才算「確認離開」
ALERT_COOLDOWN_SECONDS = 10.0 # 兩次入侵警報之間的最短間隔（秒）


# ===== 幾何運算與防呆驗證層（純函式） =====
# 主要防呆情況：

# 頂點數量不對: 檢查點數是否為 3～20 個 => 少於 3 個點圍不出一個區域；超過 20 個點會拖慢後續即時偵測的計算速度。
# 座標格式錯誤: 檢查每個頂點是否剛好包含 x、y 兩個值 => 防止前端傳來缺漏或多餘的資料，導致程式讀取時直接當機。
# 數值異常或混入布林值: 檢查座標是否為正常的有限數字（排除 True/False、NaN、無限大） => 避免無效數值讓幾何公式算不出來，也防止 Python 把 True/False 誤當成數字 1 和 0。
# 超出畫面範圍: 檢查 x、y 座標是否都介於 0～1 之間 => 確保畫出來的警戒區完全落在攝影機畫面內，不會拉到畫面外面。
# 區域太小或點重疊: 檢查多邊形的總面積是否大於門檻值 => 防止使用者滑鼠連點兩下，或把所有點拉成一條直線，畫出「沒有面積」的無效警戒區。
# 線條打結或碰觸: 檢查不相鄰的邊線是否互相交叉（例如畫成 8 字型） => 只要線條打結，後續用來判斷「目標是否在框內」的射線演算法就會計算錯亂、產生誤判。

# --- 判斷點 pt 是否落在線段 ab 上 ---
def _is_point_on_segment(pt, a, b, eps=1e-7):
    px, py = pt
    ax, ay = a
    bx, by = b
    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    return (abs(cross) <= eps and min(ax, bx)-eps <= px <= max(ax, bx)+eps
            and min(ay, by)-eps <= py <= max(ay, by)+eps)

# --- 判斷點是否在多邊形內（含邊界） ---
def point_in_polygon(point, polygon):
    """Even/odd ray casting with points on polygon edges counted as inside."""
    px, py = point
    inside = False
    for i, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(i + 1) % len(polygon)]
        if _is_point_on_segment(point, (ax, ay), (bx, by)):
            return True
        if (ay > py) != (by > py):
            x_intersection = ax + (py - ay) * (bx - ax) / (by - ay)
            if px < x_intersection:
                inside = not inside
    return inside

# --- 判斷兩線段是否相交（不含端點） ---
def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

# --- 判斷兩線段是否相交（含端點） ---
def _segments_intersect(a, b, c, d):
    """Reject proper crossings and touching non-adjacent edges."""
    vals = (_orientation(a, b, c), _orientation(a, b, d),
            _orientation(c, d, a), _orientation(c, d, b))
    if vals[0] * vals[1] < 0 and vals[2] * vals[3] < 0:
        return True
    return (_is_point_on_segment(c, a, b) or _is_point_on_segment(d, a, b)
            or _is_point_on_segment(a, c, d) or _is_point_on_segment(b, c, d))

# ----- 防呆驗證 -----
def validate_polygon(points):
    if not isinstance(points, list) or not 3 <= len(points) <= 20:
        raise ValueError("警戒區必須有 3～20 個頂點")
    out = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("每個頂點都必須包含 x、y 座標")
        if (isinstance(point[0], bool) or isinstance(point[1], bool)
                or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in point)):
            raise ValueError("座標必須是有限數字")
        x, y = float(point[0]), float(point[1])
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise ValueError("頂點座標必須介於 0～1")
        out.append([x, y])
    area2 = abs(sum(out[i][0] * out[(i + 1) % len(out)][1]
                    - out[(i + 1) % len(out)][0] * out[i][1]
                    for i in range(len(out))))
    if area2 < 0.001:
        raise ValueError("區域面積太小或頂點重疊")
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            if j == i + 1 or (i == 0 and j == len(out)-1):
                continue
            if _segments_intersect(out[i], out[(i+1) % len(out)],
                                   out[j], out[(j+1) % len(out)]):
                raise ValueError("警戒區不可自我交叉")
    return out


# ===== 核心監控引擎 =====
# 負責管理警戒區設定、延遲載入 YOLO 模型、對影像影格進行推論，並透過「狀態機」決定何時發送警報
class IntrusionMonitor:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = Path(config_path) # 存放警戒區設定的 JSON 檔案
        self.lock = threading.RLock() # 讀寫警戒區設定、狀態機、推論結果的鎖
        self.model_lock = threading.Lock() # 讀寫 YOLO 模型的鎖
        self.model = None  # 延遲載入的 YOLO 模型物件，None = 尚未載入
        self.model_error = None # YOLO 模型載入失敗的錯誤訊息，None = 尚未載入或載入成功
        self.frame_count = 0 # 影格計數器，用於控制每隔幾個影格才進行一次 YOLO 推論
        self.hits = 0 # 連續幾次推論都在區域內的計數器
        self.misses = 0 # 連續幾次推論都不在區域內的計數器
        self.active_presence = False # 狀態機：目前是否有確認入侵的存在
        self.last_alert_at = float("-inf") # 狀態機：上一次發送警報的時間戳記
        self.revision = 0 # 警戒區設定的版本號，每次修改設定都會 +1，用於避免舊的推論結果影響新的設定
        self.zone = {"enabled": False, "points": []} # 目前的警戒區設定
        self._load_config() # 讀取 JSON 檔案，載入警戒區設定，如果檔案不存在或格式錯誤，則使用預設值（監控關閉、空區域）

    # --- 內部方法：讀取與儲存警戒區設定 ---
    # 讓使用者設定好的「警戒區域座標」與「監控開關狀態」能跨越程式的生命週期保存下來，不會因為程式重啟而歸零。
    def _load_config(self):
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                saved = json.load(f)
            points = validate_polygon(saved.get("points", []))
            self.zone = {"enabled": bool(saved.get("enabled", False)), "points": points}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # No persisted zone = monitoring off (fail closed).
            self.zone = {"enabled": False, "points": []}

    # --- 內部方法：儲存警戒區設定 ---
    # 將目前的警戒區設定保存到 JSON 檔案中。給下一次程式啟動後繼承設定
    def _save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.config_path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(self.zone, f, ensure_ascii=False, indent=2)
        os.replace(temp, self.config_path)

    # --- 內部方法：重置狀態機 ---
    # 當使用者修改警戒區設定或重新啟動攝影機串流時，會呼叫此方法重置狀態機，避免舊的推論結果影響新的設定。
    def _reset(self):
        self.hits = self.misses = 0
        self.active_presence = False
        self.last_alert_at = float("-inf")
        self.revision += 1

    # --- 內部方法：重置追蹤 ---
    # 當攝影機串流重新啟動時，會呼叫此方法重置追蹤，忘記舊的在區域內的存在。
    def reset_tracking(self):
        """Camera stream was restarted: forget stale in-zone presence."""
        with self.lock:
            self.hits = self.misses = 0 # 重置連續在區域內的計數器
            self.active_presence = False # 重置狀態機：目前沒有確認入侵的存在
            self.revision += 1 # 警戒區設定的版本號 +1，避免舊的推論結果影響新的設定

    # --- 公開方法：取得警戒區設定 ---
    def get_zone(self):
        with self.lock:
            return {"enabled": self.zone["enabled"], "points":
                    [point[:] for point in self.zone["points"]],
                    "model_ready": self.model is not None,
                    "model_error": self.model_error}

    # --- 公開方法：儲存警戒區設定 ---
    def save_zone(self, points, enabled=True):
        valid = validate_polygon(points)
        if not isinstance(enabled, bool):
            raise ValueError("enabled 必須是布林值")
        with self.lock:
            self.zone = {"points": valid, "enabled": enabled}
            self._save_config()
            self._reset()
            return self.get_zone()

    # --- 公開方法：啟用或停用警戒區監控 ---
    def enable(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("enabled 必須是布林值")
        with self.lock:
            if enabled and not self.zone["points"]:
                raise ValueError("請先儲存禁止進入區域")
            self.zone["enabled"] = enabled
            self._save_config()
            self._reset()
            return self.get_zone()

    # --- 公開方法：清除警戒區設定 ---
    def clear_zone(self):
        with self.lock:
            self.zone = {"enabled": False, "points": []}
            self._save_config()
            self._reset()
            return self.get_zone()

    # --- 公開方法：更新狀態機，決定是否發送警報 ---
    def update_presence(self, detected_inside, now=None):
        """One call per inference sample; return True for a new alert only."""
        if now is None:
            now = time.monotonic()
        with self.lock:
            if detected_inside:
                self.hits += 1
                self.misses = 0
                # 如果連續幾次推論都在區域內，且目前沒有確認入侵的存在，則將狀態機設為有確認入侵的存在，並檢查是否需要發送警報。
                if not self.active_presence and self.hits >= CONFIRM_HITS:
                    self.active_presence = True
                    if now - self.last_alert_at >= ALERT_COOLDOWN_SECONDS:
                        self.last_alert_at = now
                        return True
            else:
                self.hits = 0
                self.misses += 1
                if self.misses >= RESET_MISSES:
                    self.active_presence = False
        return False

    # --- 內部方法：延遲載入 YOLO 模型 ---
    def _get_model(self):
        with self.model_lock:
            if self.model is None:
                if not MODEL_PATH.is_file():
                    raise FileNotFoundError(f"找不到人員模型：{MODEL_PATH}")
                try:
                    from ultralytics import YOLO
                    self.model = YOLO(str(MODEL_PATH))
                    self.model_error = None
                except Exception as exc:
                    self.model_error = str(exc)
                    raise
            return self.model

    # --- 公開方法：處理影像影格，進行 YOLO 推論，並決定是否發送警報 ---
    def process_frame(self, frame):
        """Returns (frame, alert_payload). Raises only for a missing model/import."""
        with self.lock:
            enabled = self.zone["enabled"]
            points = [pt[:] for pt in self.zone["points"]]
            revision = self.revision
            if not enabled or not points:
                return frame, None
            self.frame_count += 1
            if self.frame_count % DETECT_EVERY_N_FRAMES != 0:
                return frame, None

        model = self._get_model()
        with self.model_lock:
            result = model.predict(source=frame, classes=[0], conf=PERSON_CONFIDENCE,
                                   imgsz=640, verbose=False)[0]
        height, width = frame.shape[:2]
        import cv2
        import numpy as np
        polygon_px = np.asarray([[round(x * width), round(y * height)] for x, y in points],
                                dtype=np.int32)
        inside = False
        max_conf = 0.0
        for box in result.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0].item())
            # The person's foot-center is a better indicator of area entry
            # than bbox overlap (which can trigger from just an arm).
            foot = ((x1 + x2) / (2 * width), min(1., max(0., (y2 - 2) / height)))
            in_zone = point_in_polygon(foot, points)
            color = (0, 0, 255) if in_zone else (0, 180, 0)
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            if in_zone:
                inside = True
                max_conf = max(max_conf, conf)
                cv2.circle(frame, (round(foot[0]*width), round(foot[1]*height)), 5, (0, 0, 255), -1)
        cv2.polylines(frame, [polygon_px], isClosed=True, color=(0, 200, 255), thickness=2)
        with self.lock:
            if revision != self.revision or not self.zone["enabled"]:
                return frame, None
            fired = self.update_presence(inside)
        if fired:
            return frame, {"message": "⚠️ 區域入侵警報：偵測到人員進入禁止區域！",
                           "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           "confidence": round(max_conf, 3)}
        return frame, None

# ===== 事件持久化層 =====
# 將確認發生的入侵警報寫入 SQLite 資料庫，供管理介面查詢歷史紀錄
class IntrusionEventLog:
    def __init__(self, path=EVENT_DB):
        # 建立資料庫檔案與 intrusion_events 資料表，如果不存在則建立。
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS intrusion_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        message TEXT NOT NULL)""")
            
    # --- 內部方法：新增入侵事件紀錄 ---
    # 將確認發生的入侵警報寫入 SQLite 資料庫
    def add(self, payload):
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("INSERT INTO intrusion_events (timestamp, confidence, message) VALUES (?, ?, ?)",
                       (payload["timestamp"], payload["confidence"], payload["message"]))

    # --- 公開方法：查詢最近的入侵事件紀錄 ---
    # 取得最近的入侵事件紀錄，預設最多 30 筆
    def recent(self, limit=30):
        with sqlite3.connect(self.path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT id,timestamp,confidence,message FROM intrusion_events "
                              "ORDER BY id DESC LIMIT ?", (min(max(int(limit), 1), 100),)).fetchall()
            return [dict(r) for r in rows]
