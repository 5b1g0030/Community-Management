# 【智慧取貨類別】
from .databaseManager import DatabaseManager # 從同一層資料夾中匯入該模組

class PickUp:

    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 取得可用的櫃號（返回最小的空閒櫃號） =====
    def get_available_locker(self):
        conn, cursor = self.db_manager.get_db_connection()
        pass

    # ====== 自動分配櫃號並登記包裹 ======
    def register_package(self, recipient_name):
        pass

    # ===== 根據住戶名稱查詢櫃號 =====
    def get_locker_by_name(self, name):
        pass

    # ===== 清除櫃位資訊 ======
    def clear_locker(self, locker_number):
        pass

    # ===== 取得所有櫃位狀態 =====
    def get_all_lockers_status(self):
        pass
