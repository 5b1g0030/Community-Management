# 【辨識紀錄類別】
from .databaseManager import DatabaseManager 
import sqlite3
from datetime import datetime
import logging as log
import asyncio # 【修改 1】匯入 asyncio，用於處理非同步與背景執行緒

# ===== 辨識紀錄類別 =====
class RecognitionLogs:

    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 列出資料庫中的所有辨識紀錄 =====
    # 回傳 字典格式資料
    # =================================== 
    # 【修改 2】將函式改為 async def，以便在 Quart 路由中被 await 呼叫
    async def get_all_recognition_logs(self):
        
        # 【修改 3】建立一個同步的內部函式來處理 sqlite3 的阻塞操作
        def _db_query():
            conn = None # 【修改 4】預先宣告 conn，取代 locals() 檢查，更安全
            try:
                # 【修改 5】修正原本雙重賦值的錯字 (移除了多餘的 conn, cursor =)
                conn, cursor = self.db_manager.get_db_connection() 
                
                cursor.execute('''
                    SELECT rl.id, rl.created_date, rl.event_type, rl.event_message, f.name, rl.confidence, rl.face_id
                    FROM recognition_log rl
                    LEFT JOIN faces f ON rl.face_id = f.id
                    ORDER BY rl.created_date DESC
                ''')
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        'id': row[0],
                        'created_date': row[1],
                        'event_type': row[2],
                        'event_message': row[3],
                        'name': row[4],
                        'confidence': row[5],
                        'face_id': row[6]
                    })
                return logs 
            
            except sqlite3.DatabaseError as e:
                log.error(f"查詢時發生錯誤: {e}")
                return []
            except Exception as e:
                log.error(f"查詢辨識紀錄時發生錯誤: {e}")
                return []
            finally:
                if conn: # 【修改 4】直接檢查 conn 是否有被成功賦值
                    conn.close()

        # 【修改 6】將阻塞的資料庫查詢丟到背景執行緒，不卡死 Quart 非同步迴圈
        return await asyncio.to_thread(_db_query)

    # ===== 辨識紀錄儲存 ======
    # 傳入 事件類型、事件訊息、人臉id(選填)、信心度(選填)
    # 回傳 無 
    # =========================================== 
    # 【修改 7】必須改為 async def，因為內部使用了 await 呼叫 SocketIO
    async def save_recognition_log(self, event_type, event_message, face_id=None, confidence=None):
        
        # 【修改 8】同樣將資料庫寫入操作包裝成同步函式
        def _db_insert():
            conn = None
            try:
                conn, cursor = self.db_manager.get_db_connection() 

                created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute('''
                    INSERT INTO recognition_log (created_date, event_type, event_message, face_id, confidence)
                    VALUES (?, ?, ?, ?, ?)
                ''', (created_date, event_type, event_message, face_id, confidence))
                
                conn.commit() 
                log.info(f"事件紀錄已儲存: {event_type} - {event_message}")
                
            except Exception as e:
                log.error(f"儲存事件紀錄失敗: {e}")
                raise 
            finally:
                if conn: 
                    conn.close()

        # 【修改 9】在背景執行緒完成資料庫寫入，並等待其完成
        await asyncio.to_thread(_db_insert)
        
        # 【修改 10】資料庫寫入完成後，執行非同步的 socket 推送
        try:
            from modules import sio # 延遲匯入
            log.info("事件紀錄已更新: 正在發送更新訊息...")
            
            # 這裡因為外層已經是 async def，所以可以合法使用 await
            await sio.emit('update-log', {'message': f'辨識紀錄資料已更新'})
            
            log.info("事件紀錄已更新: 已發送更新訊息!")
        except Exception as e:
            log.error(f"發送 Socket 更新訊息失敗: {e}")