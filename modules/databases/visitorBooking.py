# 【訪客預約類別】
from .databaseManager import DatabaseManager # 從同一層資料夾中匯入該模組
from datetime import datetime
import logging as log

class VisitorBooking:
    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 儲存訪客預約記錄(註冊訪客人臉在 face_recognition->register_visitor_faces) =====
    # 輸入 使用者名稱、訪客人臉名稱(visitor_...)、訪客人臉id
    # 輸出 狀態(T/F), 訊息
    # 【修改】函式宣告加上 async 轉換為非同步函式
    async def save_visitor_booking(self, username, visitor_face_name, visitor_face_id):
        """
        儲存訪客預約記錄
        
        參數:
            username: 住戶名稱
            visitor_face_name: 訪客人臉識別名稱 (如 visitor_20240101_123456)
            visitor_face_id: 關聯到 face_recognition 表格的 ID
        
        返回:
            tuple: (success, message)
        """
        try:
            # 【修改】呼叫非同步的資料庫連線需加上 await
            conn, cursor = await self.db_manager.get_db_connection() # 連結資料庫
            
            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 紀錄時間
            
            # 加入訪客資料(人臉資訊+id)
            # 【修改】執行 SQL 寫入需加上 await
            await cursor.execute('''
                INSERT INTO visitor_bookings 
                (username, visitor_face_name, visitor_face_id, created_date)
                VALUES (?, ?, ?, ?)
            ''', (username, visitor_face_name, visitor_face_id, created_date))
            
            # 【修改】非同步確認交易 (commit) 加上 await
            await conn.commit()
            # 【修改】關閉連線需加上 await
            await conn.close()
            
            log.info(f"[資料庫] 成功儲存訪客預約: {username} -> {visitor_face_name}")
            return True, f'訪客預約成功，訪客可直接到門口進行人臉辨識'
        
        except Exception as e:
            log.error(f"[資料庫] 儲存訪客預約失敗: {e}")
            return False, f'儲存失敗: {str(e)}'

    # ===== 根據訪客人臉名稱查詢住戶名稱 =====
    # 【修改】函式宣告加上 async 轉換為非同步函式
    async def get_visitor_by_face_name(self, visitor_face_name):
        """
        根據訪客人臉名稱查詢對應的住戶名稱
        預約紀錄（visitor_bookings）會保留，只是標記為已使用（used = TRUE），
        這樣既能保留歷史紀錄，又能確保人臉資料不會被重複使用或濫用
        
        參數:
            visitor_face_name: 訪客人臉識別名稱 (如 visitor_20240101_123456)
        
        返回:
            str: 住戶名稱，若查詢不到則回傳 None
        """
        try:
            # 【修改】加上 await
            conn, cursor = await self.db_manager.get_db_connection()
            
            log.info("查詢對應訪客資料中...")
            # 【修改】執行 SQL 查詢需加上 await
            await cursor.execute('''
                SELECT username FROM visitor_bookings 
                WHERE visitor_face_name = ? AND used = FALSE
            ''', (visitor_face_name,))
            
            # 【修改】取得單筆資料 (fetchone) 在 aiosqlite 中為非同步操作，需加上 await
            result = await cursor.fetchone()
            log.info(f"已查詢到訪客資料{result}")

            # 【修改】加上 await
            await conn.close()
            
            if result:
                return result[0]  # 回傳住戶名稱
            return None
        
        except Exception as e:
            log.error(f"[資料庫] 查詢訪客住戶失敗: {e}")
            return None

    # ===== 清除訪客人臉資料 =====
    # 【修改】函式宣告加上 async 轉換為非同步函式
    async def clear_visitor_face_data(self, visitor_face_name):
        """
        清除訪客的人臉資料（完全刪除，不保留記錄）
        訪客的人臉資料屬於一次性用途，當辨識完成、通行後，為了保護住戶與訪客的隱私
        
        參數:
            visitor_face_name: 訪客人臉識別名稱
        
        返回:
            bool: 是否成功清除
        """
        try:
            # 【修改】加上 await
            conn, cursor = await self.db_manager.get_db_connection()
            
            # 1. 從 face_recognition 表格刪除人臉資料
            # 【修改】執行 SQL 刪除需加上 await
            await cursor.execute('DELETE FROM face_recognition WHERE name = ?', (visitor_face_name,))
            
            # 2. 更新 visitor_bookings 表格，標記為已使用
            used_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 【修改】執行 SQL 更新需加上 await
            await cursor.execute('''
                UPDATE visitor_bookings 
                SET used = TRUE, used_date = ?
                WHERE visitor_face_name = ?
            ''', (used_date, visitor_face_name))
            
            # 【修改】加上 await
            await conn.commit()
            # 【修改】加上 await
            await conn.close()
            
            log.info(f"[資料庫] 成功清除訪客人臉資料: {visitor_face_name}")
            return True
        
        except Exception as e:
            log.error(f"[資料庫] 清除訪客人臉資料失敗: {e}")
            return False