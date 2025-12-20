import sqlite3
import hashlib

class UserManager:
	# 資料庫路徑
	def __init__(self, db_path='face_database/face_database.db'):
		self.db_path = db_path

    # ===== 註冊使用者 =====
    # 回傳 執行結果, 訊息
    # =====================  
	def register_user(self, username, password, role='住戶'):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()

			cursor.execute("SELECT id FROM users WHERE username= ?", (username,))
			if cursor.fetchone():
				conn.close()
				return False, "使用者名稱已被使用 by database"
			
			if role not in ('住戶', '管理員'):
				conn.close()
				return False, "不支援的身分 by database"
			
			password_hash = hashlib.sha256(password.encode()).hexdigest()
			cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
						   (username, password_hash, role))
			
			conn.commit()
			conn.close()
			return True, "註冊成功 by database"
		except Exception as e:
			return False, f"註冊失敗 by database: {str(e)}"

    # ===== 使用者登入 =====
    # 回傳 執行結果
    # ===================== 
	def login_user(self, username, password):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			password_hash = hashlib.sha256(password.encode()).hexdigest()
			cursor.execute("SELECT role FROM users WHERE username = ? AND password_hash = ?",
						   (username, password_hash))
			row = cursor.fetchone()
			conn.close()
			if row:
				return row[0]
			else:
				return None
		except Exception:
			return None

    # ===== 建立訪客預約 =====
    # 輸入 使用者名稱、驗證碼
    # 回傳 執行結果(T,F) 訊息
    # =====================  
	def create_visitor_booking(self, username, booking_code):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT id FROM visitor_bookings WHERE booking_code = ?", (booking_code,))
			if cursor.fetchone():
				conn.close()
				return False, "預約碼已存在，請重新生成"
			cursor.execute("INSERT INTO visitor_bookings (username, booking_code) VALUES (?, ?)",
						   (username, booking_code))
			conn.commit()
			conn.close()
			return True, "預約成功"
		except Exception as e:
			return False, f"預約失敗: {str(e)}"

    # ===== 驗證並使用訪客預約碼 =====
    # 輸入 驗證碼 
    # 回傳 執行結果, 住戶名稱
    # ============================== 
	def verify_visitor_booking(self, booking_code):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT username FROM visitor_bookings WHERE booking_code = ? AND used = FALSE", 
						   (booking_code,))
			row = cursor.fetchone()
			if row:
				username = row[0]
				cursor.execute("UPDATE visitor_bookings SET used = TRUE, used_date = CURRENT_TIMESTAMP WHERE booking_code = ?",
							   (booking_code,))
				conn.commit()
				conn.close()
				return True, username
			else:
				conn.close()
				return False, "無效或已使用的預約碼"
		except Exception as e:
			return False, f"驗證失敗: {str(e)}"

    # ===== 儲存訪客留言 =====
    # 傳入 住戶名稱、訪客照片路徑、預約碼（選填）
    # 回傳 執行結果, 訊息
    # =====================
	def save_visitor_message(self, username, visitor_image_path, booking_code=None):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("""
				INSERT INTO user_message (username, visitor_image_path, booking_code) 
				VALUES (?, ?, ?)
			""", (username, visitor_image_path, booking_code))
			message_id = cursor.lastrowid
			conn.commit()
			conn.close()
			print(f"成功儲存訪客留言 (ID: {message_id}) for {username}")
			return True, f"訪客留言已儲存 (ID: {message_id})"
		except Exception as e:
			print(f"儲存訪客留言失敗: {str(e)}")
			return False, f"儲存失敗: {str(e)}"

    # ===== 取得所有訪客留言 =====
    # 回傳 字典格式資料列表
    # ===========================
	def get_all_visitor_messages(self):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("""
				SELECT id, username, visitor_image_path, created_date, booking_code
				FROM user_message 
				ORDER BY created_date DESC
			""")
			messages = []
			for row in cursor.fetchall():
				messages.append({
					'id': row[0],
					'username': row[1],
					'visitor_image_path': row[2],
					'created_date': row[3],
					'booking_code': row[4]
				})
			conn.close()
			return messages
		except Exception as e:
			print(f"查詢訪客留言失敗: {str(e)}")
			return []

    # ===== 更新訪客留言審核狀態 =====
    # 傳入 留言ID、審核狀態、住戶名稱
    # 回傳 執行結果, 訊息
    # ===============================
	def update_visitor_message_status(self, message_id, status, username):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("SELECT username FROM user_message WHERE id = ?", (message_id,))
			row = cursor.fetchone()
			if not row:
				conn.close()
				return False, "留言不存在"
			if row[0] != username:
				conn.close()
				return False, "無權限審核此留言"
			cursor.execute("""
				UPDATE user_message 
				SET status = ?, reviewed_date = CURRENT_TIMESTAMP 
				WHERE id = ?
			""", (status, message_id))
			conn.commit()
			conn.close()
			return True, f"審核狀態已更新為: {status}"
		except Exception as e:
			return False, f"更新失敗: {str(e)}"

    # ===== 取得特定使用者的訪客留言 =====
    # 傳入 使用者名稱
    # 回傳 字典格式資料列表
    # ===================================
	def get_user_visitor_messages(self, username):
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute("""
				SELECT id, username, visitor_image_path, created_date, booking_code, status, reviewed_date
				FROM user_message 
				WHERE username = ?
				ORDER BY created_date DESC
			""", (username,))
			messages = []
			for row in cursor.fetchall():
				messages.append({
					'id': row[0],
					'username': row[1],
					'visitor_image_path': row[2],
					'created_date': row[3],
					'booking_code': row[4],
					'status': row[5],
					'reviewed_date': row[6]
				})
			conn.close()
			return messages
		except Exception as e:
			print(f"查詢使用者訪客留言失敗: {str(e)}")
			return []
