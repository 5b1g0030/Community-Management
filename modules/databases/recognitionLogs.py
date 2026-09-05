# 【辨識紀錄類別】
from .databaseManager import DatabaseManager 
import sqlite3
from datetime import datetime
import logging as log
# 【修改】不再必須依賴 asyncio.to_thread 繞過阻塞，但可保留以防其他非同步排程需求

# ===== 辨識紀錄類別 =====
class RecognitionLogs:

    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 列出資料庫中的所有辨識紀錄 =====
    # 回傳 字典格式資料
    # =================================== 
    # 【修改】完全改為原生非同步流程，移除內部的 _db_query 同步函式
    async def get_all_recognition_logs(self):
        conn = None 
        try:
            # 【修改】呼叫非同步的資料庫連線需加上 await
            conn, cursor = await self.db_manager.get_db_connection() 
            
            # 【修改】執行 SQL 查詢需加上 await
            await cursor.execute('''
                SELECT rl.id, rl.created_date, rl.event_type, rl.event_message, f.name, rl.confidence, rl.face_id
                FROM recognition_log rl
                LEFT JOIN faces f ON rl.face_id = f.id
                ORDER BY rl.created_date DESC
            ''')
            
            logs = []
            # 【修改】fetchall() 在 aiosqlite 中為非同步操作，需加上 await
            rows = await cursor.fetchall()
            for row in rows:
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
            if conn: 
                # 【修改】關閉連線需加上 await
                await conn.close()

    # ===== 辨識紀錄儲存 ======
    # 傳入 事件類型、事件訊息、人臉id(選填)、信心度(選填)
    # 回傳 無 
    # =========================================== 
    async def save_recognition_log(self, event_type, event_message, face_id=None, confidence=None):
        
        conn = None
        try:
            # 【修改】移除 asyncio.to_thread，直接取得非同步連線
            conn, cursor = await self.db_manager.get_db_connection() 

            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 【修改】非同步寫入資料庫加上 await
            await cursor.execute('''
                INSERT INTO recognition_log (created_date, event_type, event_message, face_id, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (created_date, event_type, event_message, face_id, confidence))
            
            # 【修改】非同步確認交易加上 await
            await conn.commit() 
            log.info(f"事件紀錄已儲存: {event_type} - {event_message}")
            
        except Exception as e:
            log.error(f"儲存事件紀錄失敗: {e}")
            raise 
        finally:
            if conn: 
                # 【修改】非同步關閉連線加上 await
                await conn.close()

        # 【維持原樣】資料庫寫入完成後，執行非同步的 socket 推送
        try:
            from modules import sio # 延遲匯入
            log.info("事件紀錄已更新: 正在發送更新訊息...")
            
            await sio.emit('update-log', {'message': f'辨識紀錄資料已更新'})
            
            log.info("事件紀錄已更新: 已發送更新訊息!")
        except Exception as e:
            log.error(f"發送 Socket 更新訊息失敗: {e}")