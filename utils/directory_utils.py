import os


""" ===== 這裡放app.py的共用資料夾函式"""

def make_new_dir(temp_dir):
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)