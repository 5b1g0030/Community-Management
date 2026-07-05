import numpy as np
import cv2
import logging as log

""" ===== 這裡放影像串流顯示畫面邏輯 =====  """

# ===== 在影像上繪製辨識結果 =====
def show_resultFrame(results, frame):
    for result in results:
        x, y, w, h = result['position'] # 人臉座標
        name = result['name'] # 人名
        confidence = result['confidence'] # 信心度

        # 已知=綠色；未知=紅色
        color = (0, 255, 0) if name != '未知' else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

        label = f"{name} ({confidence:.1f})"
        cv2.putText(frame, label, (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

# ===== 如果無法成功編碼時使用，嘗試顯示錯誤畫面 =====
def show_encoding_error_frame():
    log.error("[錯誤] 無法將黑色畫面編碼為 JPEG 格式 by video_streaming")
    # 返回一個簡單的錯誤畫面
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Encoding Error', (150, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    ret, buffer = cv2.imencode('.jpg', frame)
    # 如果編碼再次失敗
    if not ret:
        log.critical("[嚴重錯誤] 無法生成錯誤畫面 by video_streaming")
        buffer = b''

    return buffer

# ===== 顯示一個黑色畫面+填入指定文字 (用來顯示相機未找到等異常畫面) ======
def create_message_frame(text, color=(255,255,255)):
    frame = np.zeros((480, 640, 3), dtype=np.uint8) # 建立一張「黑色影像」當作畫布

    # 填入文字
    cv2.putText(
        frame, # 畫面
        text,  # 文字內容
        (50,240), # 文字起始位置座標 (x, y)，座標原點在左上角，往右 x 增加、往下 y 增加
        cv2.FONT_HERSHEY_SIMPLEX, # 字型樣式(內建的簡單無襯線字型)
        1, # 字體縮放倍率(1 => 1倍大)
        color, # 文字顏色(BGR)
        2 # 字體粗細
    )
    
    # 編碼新的畫面
    ret, buffer = cv2.imencode('.jpg', frame) 
    
    # 如果無法成功編碼時使用，嘗試顯示錯誤畫面
    if not ret:
        return show_encoding_error_frame() 

    return buffer.tobytes() # 包裝成 HTTP 響應的一部分，傳輸到客戶端（例如瀏覽器）

# ===== 顯示「相機已關閉」畫面+提示開啟文字 =====
def show_cameraOff_frame():
    # 返回黑色畫面提示相機已關閉
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, 'Camera is OFF', (180, 240),
       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, 'Click "Start Camera" to begin', (120, 280),
       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    ret, buffer = cv2.imencode('.jpg', frame)
    # 如果編碼失敗
    if not ret:
        buffer = show_encoding_error_frame()
    
    # 包裝成 HTTP 響應的一部分，傳輸到客戶端（例如瀏覽器）
    frame_bytes = buffer.tobytes()

    return frame_bytes
