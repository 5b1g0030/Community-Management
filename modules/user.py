import sqlite3
import hashlib
from .config import DATABASE

class UserManager:
	# 資料庫路徑
	def __init__(self, db_path=DATABASE):
		self.db_path = db_path

	# 【使用者類別】
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

	# 【使用者類別】
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
