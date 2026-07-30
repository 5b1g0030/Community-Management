import os
import numpy as np
from PIL import Image
import cv2  
import logging as log
import io
from modules.config import FACE_RECOGNITION_RESIZE_WIDTH
from flask import jsonify


""" ===== 這裡放人臉辨識跟圖片處理有關的函式 ===== """


# ===== 圖片轉RGB三通道 =====
def changeRGB(input_data):
    """
        將圖片轉換為 RGB 格式並確保記憶體連續

        參數:
            input_data: 可以是圖片路徑(str) 或 numpy array (OpenCV frame)

        返回:
            numpy array: RGB 格式的圖片，記憶體連續
    """
    # 判斷輸入類型
    if isinstance(input_data, str):
        log.info("input_data 是字串")
        # 輸入是檔案路徑
        pil_image = Image.open(input_data).convert('RGB')

        # 限制圖片大小
        max_width = 1000
        if pil_image.width > max_width:
            ratio = max_width / float(pil_image.width)
            new_height = int(float(pil_image.height) * ratio)
            pil_image = pil_image.resize(
                (max_width, new_height), Image.Resampling.LANCZOS)

        image = np.array(pil_image)


    elif isinstance(input_data, np.ndarray):
        # 輸入是 numpy array (OpenCV frame, BGR 格式)
        log.info("input_data 非字串")
        image = cv2.cvtColor(input_data, cv2.COLOR_BGR2RGB)

    else:
        raise ValueError(f"不支援的輸入類型: {type(input_data)}")

    # 確保數據類型為 uint8 且記憶體是連續的
    image = np.ascontiguousarray(image, dtype=np.uint8)

    return image

# ===== 獲取資料夾內的圖片檔案 =====
def getFiles(folder_path):
    """掃描資料夾內的圖片檔案"""
    files = []
    for f in os.listdir(folder_path):
        if f.lower().endswith(('.jpg', '.png', '.jpeg')):
             files.append(f)
    return files

# ===== 驗證圖片檔案格式 =====
def validate_image_file(image_file):
    if not image_file:
        log.error("[測試辨識] 錯誤：未提供照片")
        return False, "請提供照片"
    # 驗證檔案類型
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}

    file_ext = os.path.splitext(image_file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        return False, f'不支援的檔案格式：{file_ext}'
    
    return True, None

# ===== 處理上傳的圖片，進行必要的縮放、調整色彩模式 =====
def process_uploaded_image(image_file, temp_path):
    try:       
        # 讀取上傳的圖片（重要：在任何操作前先讀取）
        image_data = image_file.read()
        # print(f"[測試辨識] 讀取圖片資料，大小：{len(image_data)} bytes")
                    
        # 驗證圖片是否有效
        img = Image.open(io.BytesIO(image_data))
        log.info(f"[測試辨識] 圖片資訊 - 格式：{img.format}, 尺寸：{img.size}, 模式：{img.mode}")
                    
        # 轉換為 RGB 模式（如果是 RGBA 或其他格式）
        if img.mode != 'RGB':
            log.info(f"[測試辨識] 轉換圖片模式從 {img.mode} 到 RGB")
            img = img.convert('RGB')
                    
        # ===== 調整圖片大小（重要：避免圖片過大） =====
        max_size = FACE_RECOGNITION_RESIZE_WIDTH  # 最大寬度或高度
        if img.width > max_size or img.height > max_size:
            # 計算縮放比例
            if img.width > img.height:
                new_width = max_size
                new_height = int(img.height * (max_size / img.width))
            else:
                new_height = max_size
                new_width = int(img.width * (max_size / img.height))
                        
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            log.info(f"[測試辨識] 圖片已調整為：{img.size}")

        # 儲存處理後的圖片
        img.save(temp_path, 'JPEG', quality=95)
        log.info(f"[測試辨識] 圖片已儲存到：{temp_path}")

    except Exception as e:
        log.error(f"[測試辨識] 圖片處理失敗：{e}")
        import traceback
        traceback.print_exc()  # 顯示完整的錯誤路徑
        raise

    return img
