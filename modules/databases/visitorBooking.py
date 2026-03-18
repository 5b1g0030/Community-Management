# 【訪客預約類別】
from .databaseManager import DatabaseManager # 從同一層資料夾中匯入該模組

class VisitorBooking:
    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 儲存訪客預約記錄 =====
    def save_visitor_booking(self, username, visitor_face_name, visitor_face_id):
        conn, cursor = self.db_manager.get_db_connection()
        pass

    # ===== 根據訪客人臉名稱查詢住戶名稱 =====
    def get_visitor_by_face_name(self, visitor_face_name):
        pass

    # ===== 清除訪客人臉資料 =====
    def clear_visitor_face_data(self, visitor_face_name):
        pass

    