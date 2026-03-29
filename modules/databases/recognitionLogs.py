# 【辨識紀錄類別】
from .databaseManager import DatabaseManager # 從同一層資料夾中匯入該模組
import sqlite3
from datetime import datetime

# ===== 辨識紀錄類別 =====
class RecognitionLogs:

    # ===== 初始化 =====
    def __init__(self):
        self.db_manager = DatabaseManager()

    # ===== 列出資料庫中的所有辨識紀錄 =====
    # 回傳 字典格式資料
    # =================================== 
    def get_all_recognition_logs(self):
        try:
            conn, cursor = conn, cursor = self.db_manager.get_db_connection() # 使用統一的連接方法
            
            # 查詢辨識紀錄，並與人臉表格做關聯以取得人名，同時包含face_id和confidence
            cursor.execute('''
                SELECT rl.id, rl.created_date, rl.event_type, rl.event_message, f.name, rl.confidence, rl.face_id
                FROM recognition_log rl
                LEFT JOIN faces f ON rl.face_id = f.id
                ORDER BY rl.created_date DESC
            ''')
            
            # 資料轉換為字典格式
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
            
            conn.close() # 關閉連接
            return logs  # 回傳資料查詢結果
        
        # 查詢資料庫時的例外錯誤(資料庫檔案不存在、權限問題、資料庫鎖定等)
        except sqlite3.DatabaseError as e:
            print(f"查詢時發生錯誤 by database: {e}")
        
        # 查詢辨識紀錄時發生的例外錯誤
        except Exception as e:
            print(f"查詢辨識紀錄時發生錯誤 by database: {e}")
        
        # 一定會執行的部分
        finally:
            if 'conn' in locals(): # 確認 conn 存在
                conn.close()

    # ===== 辨識紀錄儲存 ======
    # 傳入 事件類型、事件訊息、人臉id(選填)、信心度(選填)
    # 回傳 無 
    # =========================================== 
    def save_recognition_log(self, event_type, event_message, face_id=None, confidence=None):
        try:
            conn, cursor = self.db_manager.get_db_connection() # 使用統一的連接方法

            # 記錄事件發生時間
            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # SQL 指令，寫入事件類型、事件訊息、人臉ID、信心度
            cursor.execute('''
                INSERT INTO recognition_log (created_date, event_type, event_message, face_id, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (created_date, event_type, event_message, face_id, confidence))
            
            conn.commit() # 提交變更、確保資料真的儲存到資料庫。
            print(f"事件紀錄已儲存: {event_type} - {event_message} by recognitionLogs") # 成功訊息
            
            # 推送訊息給前端，讓前端自動更新表格
            from modules import socketio # 延遲匯入
            print("事件紀錄已更新: 正在發送更新訊息...  by recognitionLogs")
            socketio.emit('update-log', {'message': f'辨識紀錄資料已更新'})
            print("事件紀錄已更新: 已發送更新訊息!  by recognitionLogs")
        
        # 例外錯誤處理
        except Exception as e:
            print(f"儲存事件紀錄失敗 by recognitionLogs: {e}")
            raise   # 重新拋出相同的例外，讓上層程式碼也能處理
        
        # 無論如何都會執行的程式碼
        finally:
            if 'conn' in locals(): # 檢查 conn 是否存在
                conn.close() # 關閉資料庫



