# 【智慧取貨類別】
from .databaseManager import DatabaseManager # 從同一層資料夾中匯入該模組
from datetime import datetime

class PickUp:

    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 取得可用的櫃號（返回最小的空閒櫃號） =====
    def get_available_locker(self):
        conn, cursor = self.db_manager.get_db_connection() # 連結資料庫
        try:
            # 搜尋尚未被占用的櫃位
            cursor.execute("""
                SELECT locker_number FROM package_lockers 
                WHERE is_occupied = 0 
                ORDER BY locker_number ASC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result[0] if result else None # 有結果回傳資料，沒有則回傳None
        finally:
            conn.close()

    # ====== 自動分配櫃號並登記包裹 ======
    def register_package(self, recipient_name):
        conn, cursor = self.db_manager.get_db_connection()
        try:
            # 取得可用櫃號
            locker_number = self.get_available_locker()
            
            # 檢查是否櫃位已滿
            if locker_number is None:
                return False, None, "所有櫃位已滿，請稍後再試"
            
            # 登記包裹(紀錄時間)
            registered_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新此櫃號(locker_number)的收件人、登記時間、佔用狀態
            cursor.execute("""
                UPDATE package_lockers 
                SET recipient_name = ?, registered_date = ?, is_occupied = 1 
                WHERE locker_number = ?
            """, (recipient_name, registered_date, locker_number))
            conn.commit() # 更新資料庫

            print(f"[資料庫] 包裹已登記至 {locker_number} 號櫃，收件人：{recipient_name} by pickUp")
            return True, locker_number, f"包裹已登記至 {locker_number} 號櫃"
        
        except Exception as e:
            print(f"[資料庫] 登記包裹失敗: {e} by pickUp")
            conn.rollback()
            return False, None, f"登記失敗: {str(e)}"
        finally:
            conn.close()

    # ===== 根據住戶名稱查詢櫃號 =====
    def get_locker_by_name(self, name):
        conn, cursor = self.db_manager.get_db_connection()
        try:
            # 根據名字查詢，且確保是占用狀態
            cursor.execute("""
                SELECT locker_number FROM package_lockers 
                WHERE recipient_name = ? AND is_occupied = 1
            """, (name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    # ===== 清除櫃位資訊 ======
    def clear_locker(self, locker_number):
        conn, cursor = self.db_manager.get_db_connection()
        try:
            # 更新櫃位狀態，重置為「未占用」
            cursor.execute("""
                UPDATE package_lockers 
                SET recipient_name = NULL, registered_date = NULL, is_occupied = 0 
                WHERE locker_number = ?
            """, (locker_number,))
            conn.commit()

            print(f"[資料庫] {locker_number} 號櫃已清除 by pickUp")
            return True, "櫃位已清除"
        except Exception as e:
            print(f"[資料庫] 清除櫃位失敗: {e} by pickUp")
            conn.rollback()
            return False, f"清除失敗: {str(e)}"
        finally:
            conn.close()

    # ===== 取得所有櫃位狀態 =====
    def get_all_lockers_status(self):
        conn, cursor = self.db_manager.get_db_connection()
        try:
            # 搜尋所有櫃位資料
            cursor.execute("""
                SELECT locker_number, recipient_name, registered_date, is_occupied 
                FROM package_lockers 
                ORDER BY locker_number ASC
            """)
            rows = cursor.fetchall()
            
            lockers = []
            for row in rows:
                lockers.append({
                    'locker_number': row[0],
                    'recipient_name': row[1],
                    'registered_date': row[2],
                    'is_occupied': bool(row[3])
                })
            return lockers
        finally:
            conn.close()
