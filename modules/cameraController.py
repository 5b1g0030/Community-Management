from modules import config

""" ===== 這裡放此專案專用的相機控制邏輯 ===== """

# ===== 開啟&關閉相機 =====
def set_camera_state(active):
    with config.CAMERA_LOCK:
                config.CAMERA_ACTIVE = active

