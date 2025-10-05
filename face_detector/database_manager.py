"""
資料庫管理工具
功能：查看、新增、刪除、修改資料庫中的資料
"""

import sqlite3
import os
from tabulate import tabulate
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="face_detector/face_database.db"):
        """初始化資料庫管理器"""
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """連接資料庫"""
        try:
            # 檢查資料庫檔案是否存在
            if not os.path.exists(self.db_path):
                print(f"⚠️ 資料庫檔案不存在: {self.db_path}")
                print(f"📁 當前目錄: {os.getcwd()}")
                print("📋 當前目錄下的檔案:")
                for file in os.listdir('.'):
                    if file.endswith('.db'):
                        print(f"   🗃️ {file}")
                return False

            # 檢查檔案大小
            file_size = os.path.getsize(self.db_path)
            print(f"📊 資料庫檔案大小: {file_size} bytes")

            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # 讓查詢結果可以用欄位名稱存取
            print(f"✅ 成功連接到資料庫: {self.db_path}")
            return True
        except sqlite3.Error as e:
            print(f"❌ 資料庫連接失敗: {e}")
            return False
    
    def disconnect(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            print("✅ 資料庫連接已關閉")
    
    def get_tables(self):
        """取得所有資料表名稱"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except sqlite3.Error as e:
            print(f"❌ 取得資料表失敗: {e}")
            return []
    
    def get_table_structure(self, table_name):
        """取得資料表結構"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            return columns
        except sqlite3.Error as e:
            print(f"❌ 取得資料表結構失敗: {e}")
            return []
    
    def view_table(self, table_name, limit=None):
        """查看資料表內容"""
        try:
            cursor = self.conn.cursor()
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if rows:
                # 取得欄位名稱
                columns = [description[0] for description in cursor.description]
                # 將資料轉換為列表格式
                data = [list(row) for row in rows]
                # 使用 tabulate 美化表格顯示
                print(f"\n📋 資料表: {table_name}")
                print("=" * 50)
                print(tabulate(data, headers=columns, tablefmt="grid"))
                print(f"📊 總共 {len(rows)} 筆資料")
            else:
                print(f"📋 資料表 '{table_name}' 是空的")
                
        except sqlite3.Error as e:
            print(f"❌ 查看資料表失敗: {e}")
    
    def insert_data(self, table_name, data_dict):
        """新增資料"""
        try:
            columns = list(data_dict.keys())
            values = list(data_dict.values())
            placeholders = ', '.join(['?' for _ in values])
            columns_str = ', '.join(columns)
            
            query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            
            print(f"✅ 成功新增資料到 {table_name}")
            return True
            
        except sqlite3.Error as e:
            print(f"❌ 新增資料失敗: {e}")
            return False
    
    def update_data(self, table_name, data_dict, condition_dict):
        """修改資料"""
        try:
            # 建立 SET 子句
            set_clause = ', '.join([f"{col} = ?" for col in data_dict.keys()])
            # 建立 WHERE 子句
            where_clause = ' AND '.join([f"{col} = ?" for col in condition_dict.keys()])
            
            query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
            values = list(data_dict.values()) + list(condition_dict.values())
            
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            
            affected_rows = cursor.rowcount
            if affected_rows > 0:
                print(f"✅ 成功修改 {affected_rows} 筆資料")
                return True
            else:
                print("⚠️ 沒有找到符合條件的資料")
                return False
                
        except sqlite3.Error as e:
            print(f"❌ 修改資料失敗: {e}")
            return False
    
    def delete_data(self, table_name, condition_dict):
        """刪除資料"""
        try:
            where_clause = ' AND '.join([f"{col} = ?" for col in condition_dict.keys()])
            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            values = list(condition_dict.values())
            
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            
            affected_rows = cursor.rowcount
            if affected_rows > 0:
                print(f"✅ 成功刪除 {affected_rows} 筆資料")
                return True
            else:
                print("⚠️ 沒有找到符合條件的資料")
                return False
                
        except sqlite3.Error as e:
            print(f"❌ 刪除資料失敗: {e}")
            return False
    
    def execute_custom_query(self, query):
        """執行自訂 SQL 查詢"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                if rows:
                    columns = [description[0] for description in cursor.description]
                    data = [list(row) for row in rows]
                    print(tabulate(data, headers=columns, tablefmt="grid"))
                    print(f"📊 查詢結果: {len(rows)} 筆資料")
                else:
                    print("📋 查詢結果為空")
            else:
                self.conn.commit()
                print(f"✅ SQL 執行成功，影響 {cursor.rowcount} 筆資料")
                
        except sqlite3.Error as e:
            print(f"❌ SQL 執行失敗: {e}")

def main():
    """主程式"""
    print("🗃️  資料庫管理工具")
    print("=" * 50)
    
    # 初始化資料庫管理器
    db_manager = DatabaseManager()
    
    if not db_manager.connect():
        return
    
    while True:
        print("\n📋 選擇操作:")
        print("1. 查看所有資料表")
        print("2. 查看資料表內容")
        print("3. 查看資料表結構")
        print("4. 新增資料")
        print("5. 修改資料")
        print("6. 刪除資料")
        print("7. 執行自訂 SQL")
        print("0. 離開")
        
        choice = input("\n請輸入選項 (0-7): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            tables = db_manager.get_tables()
            if tables:
                print("\n📋 資料庫中的資料表:")
                for i, table in enumerate(tables, 1):
                    print(f"{i}. {table}")
            else:
                print("❌ 資料庫中沒有資料表")
        
        elif choice == "2":
            tables = db_manager.get_tables()
            if not tables:
                print("❌ 資料庫中沒有資料表")
                continue
                
            print("\n選擇要查看的資料表:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            try:
                table_choice = int(input("請輸入編號: ")) - 1
                if 0 <= table_choice < len(tables):
                    limit = input("限制顯示筆數 (直接按 Enter 顯示全部): ")

                    limit = int(limit) if limit.isdigit() else None
                    db_manager.view_table(tables[table_choice], limit)
                else:
                    print("❌ 無效的選項")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "3":
            tables = db_manager.get_tables()
            if not tables:
                print("❌ 資料庫中沒有資料表")
                continue
                
            print("\n選擇要查看結構的資料表:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            try:
                table_choice = int(input("請輸入編號: ")) - 1
                if 0 <= table_choice < len(tables):
                    table_name = tables[table_choice]
                    structure = db_manager.get_table_structure(table_name)
                    if structure:
                        print(f"\n📋 資料表 '{table_name}' 結構:")
                        headers = ["編號", "欄位名稱", "資料型別", "非空", "預設值", "主鍵"]
                        print(tabulate(structure, headers=headers, tablefmt="grid"))
                else:
                    print("❌ 無效的選項")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "4":
            tables = db_manager.get_tables()
            if not tables:
                print("❌ 資料庫中沒有資料表")
                continue
                
            print("\n選擇要新增資料的資料表:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            try:
                table_choice = int(input("請輸入編號: ")) - 1
                if 0 <= table_choice < len(tables):
                    table_name = tables[table_choice]
                    structure = db_manager.get_table_structure(table_name)
                    
                    print(f"\n新增資料到 '{table_name}':")
                    data_dict = {}
                    
                    for col_info in structure:
                        col_name = col_info[1]
                        col_type = col_info[2]
                        is_nullable = col_info[3] == 0
                        
                        # 跳過自動遞增的主鍵
                        if col_info[5] == 1 and 'INTEGER' in col_type.upper():
                            continue
                            
                        value = input(f"請輸入 {col_name} ({col_type}): ").strip()
                        
                        if value == "" and not is_nullable:
                            print(f"⚠️ {col_name} 是必填欄位")
                            break
                        elif value != "":
                            data_dict[col_name] = value
                    
                    if data_dict:
                        db_manager.insert_data(table_name, data_dict)
                else:
                    print("❌ 無效的選項")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "5":
            tables = db_manager.get_tables()
            if not tables:
                print("❌ 資料庫中沒有資料表")
                continue
                
            print("\n選擇要修改資料的資料表:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            try:
                table_choice = int(input("請輸入編號: ")) - 1
                if 0 <= table_choice < len(tables):
                    table_name = tables[table_choice]
                    
                    # 先顯示資料表內容
                    print(f"\n📋 '{table_name}' 目前的資料:")
                    db_manager.view_table(table_name)
                    
                    structure = db_manager.get_table_structure(table_name)
                    
                    # 設定修改條件
                    print(f"\n🔍 設定要修改的資料條件 (WHERE 子句):")
                    condition_dict = {}
                    
                    for col_info in structure:
                        col_name = col_info[1]
                        col_type = col_info[2]
                        
                        value = input(f"請輸入 {col_name} 的條件值 (留空跳過): ").strip()
                        if value:
                            condition_dict[col_name] = value
                    
                    if not condition_dict:
                        print("⚠️ 沒有設定任何條件，無法執行修改")
                        continue
                    
                    # 設定要修改的欄位
                    print(f"\n📝 設定要修改的欄位值:")
                    data_dict = {}
                    
                    for col_info in structure:
                        col_name = col_info[1]
                        col_type = col_info[2]
                        
                        # 跳過主鍵
                        if col_info[5] == 1:
                            continue
                            
                        value = input(f"修改 {col_name} ({col_type}) 為 (留空跳過): ").strip()
                        if value:
                            data_dict[col_name] = value
                    
                    if not data_dict:
                        print("⚠️ 沒有設定任何要修改的欄位")
                        continue
                    
                    # 確認修改
                    print(f"\n📋 修改摘要:")
                    print(f"資料表: {table_name}")
                    print(f"條件: {condition_dict}")
                    print(f"修改為: {data_dict}")
                    
                    confirm = input("確定要執行修改嗎? (y/N): ").strip().lower()
                    if confirm == 'y':
                        db_manager.update_data(table_name, data_dict, condition_dict)
                    else:
                        print("❌ 已取消修改")
                else:
                    print("❌ 無效的選項")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "6":
            tables = db_manager.get_tables()
            if not tables:
                print("❌ 資料庫中沒有資料表")
                continue
                
            print("\n選擇要刪除資料的資料表:")
            for i, table in enumerate(tables, 1):
                print(f"{i}. {table}")
            
            try:
                table_choice = int(input("請輸入編號: ")) - 1
                if 0 <= table_choice < len(tables):
                    table_name = tables[table_choice]
                    
                    # 先顯示資料表內容
                    print(f"\n📋 '{table_name}' 目前的資料:")
                    db_manager.view_table(table_name)
                    
                    structure = db_manager.get_table_structure(table_name)
                    
                    # 設定刪除條件
                    print(f"\n🗑️ 設定要刪除的資料條件 (WHERE 子句):")
                    print("⚠️ 警告：沒有設定條件會刪除所有資料！")
                    
                    condition_dict = {}
                    
                    for col_info in structure:
                        col_name = col_info[1]
                        col_type = col_info[2]
                        
                        value = input(f"請輸入 {col_name} 的條件值 (留空跳過): ").strip()
                        if value:
                            condition_dict[col_name] = value
                    
                    if not condition_dict:
                        print("❌ 為了安全考量，必須設定至少一個條件")
                        confirm_all = input("🚨 確定要刪除所有資料嗎? 輸入 'DELETE ALL' 確認: ").strip()
                        if confirm_all != "DELETE ALL":
                            print("❌ 已取消刪除")
                            continue
                    
                    # 預覽要刪除的資料
                    if condition_dict:
                        print(f"\n🔍 符合條件的資料預覽:")
                        try:
                            cursor = db_manager.conn.cursor()
                            where_clause = ' AND '.join([f"{col} = ?" for col in condition_dict.keys()])
                            preview_query = f"SELECT * FROM {table_name} WHERE {where_clause}"
                            cursor.execute(preview_query, list(condition_dict.values()))
                            preview_rows = cursor.fetchall()
                            
                            if preview_rows:
                                columns = [description[0] for description in cursor.description]
                                data = [list(row) for row in preview_rows]
                                print(tabulate(data, headers=columns, tablefmt="grid"))
                                print(f"📊 將刪除 {len(preview_rows)} 筆資料")
                            else:
                                print("📋 沒有符合條件的資料")
                                continue
                                
                        except sqlite3.Error as e:
                            print(f"❌ 預覽失敗: {e}")
                            continue
                    
                    # 確認刪除
                    print(f"\n📋 刪除摘要:")
                    print(f"資料表: {table_name}")
                    print(f"條件: {condition_dict if condition_dict else '刪除所有資料'}")
                    
                    confirm = input("🚨 確定要執行刪除嗎? 此操作無法復原! (y/N): ").strip().lower()
                    if confirm == 'y':
                        if condition_dict:
                            db_manager.delete_data(table_name, condition_dict)
                        else:
                            # 刪除所有資料
                            try:
                                cursor = db_manager.conn.cursor()
                                cursor.execute(f"DELETE FROM {table_name}")
                                db_manager.conn.commit()
                                print(f"✅ 成功刪除 {cursor.rowcount} 筆資料")
                            except sqlite3.Error as e:
                                print(f"❌ 刪除失敗: {e}")
                    else:
                        print("❌ 已取消刪除")
                else:
                    print("❌ 無效的選項")
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "7":
            query = input("\n請輸入 SQL 查詢: ").strip()
            if query:
                db_manager.execute_custom_query(query)
            else:
                print("❌ 請輸入有效的 SQL 查詢")
        
        else:
            print("❌ 無效的選項，請重新輸入")
    
    db_manager.disconnect()
    print("👋 感謝使用資料庫管理工具")

if __name__ == "__main__":
    # 安裝所需套件: pip install tabulate
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程式被使用者中斷")
    except Exception as e:
        print(f"\n❌ 程式發生錯誤: {e}")