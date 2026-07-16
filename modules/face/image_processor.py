import os
import numpy as np
from PIL import Image
import cv2  
import logging as log


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

