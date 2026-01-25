# ===== 檢查模型檔案 =====
import face_recognition_models
import os
import sys

# 1. 檢查目前執行的 Python
print(f"目前 Python: {sys.executable}")

# 2. 定位模型套件位置
model_root = os.path.dirname(face_recognition_models.__file__)
print(f"模型套件目錄: {model_root}")

# 3. 檢查關鍵模型檔案是否存在 (這才是程式能不能跑的重點)
required_files = [
    'shape_predictor_68_face_landmarks.dat',
    'dlib_face_recognition_resnet_model_v1.dat',
    'mmod_human_face_detector.dat'
]

print("--- 檔案檢查 ---")
for f in required_files:
    path = os.path.join(model_root, 'models', f) # 核心路徑通常在 models 子目錄下
    exists = os.path.exists(path)
    print(f"檔案 {f}: {'[OK]' if exists else '[缺失 MISSING]'}")